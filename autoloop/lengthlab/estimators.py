"""lengthlab estimators — EDITABLE SURFACE for loop A.

This is the ONLY file loop A may edit. Contract:

    estimate(observed, is_censored, cap) -> {"median": float,
                                             "q90": float,
                                             "p_ge": {c: float for c in caps}}

`observed` are token lengths right-censored at `cap`; `is_censored` marks rows
that hit the cap. `caps` to report are passed via the `caps` argument.
Return finite floats; probabilities in [0, 1]. If a quantity is not
identifiable (e.g. q90 when >10% of mass is censored), return the best
defensible bound-respecting value — the scorer penalizes error against truth,
so unidentifiable-and-honest beats confident-and-wrong only if it is closer.

Baseline v0 below: censoring-aware empirical rule + lognormal MLE with
right-censoring (Tobit-style), picked per sample by censored fraction.
"""
from __future__ import annotations

import math

import numpy as np


def _p_ge_empirical(observed, is_censored, cap, c):
    # For c <= cap, P(X >= c) is exactly identified: censored rows count as >= c.
    if c <= cap:
        return float(np.mean((observed >= c) | is_censored))
    # Beyond the cap nothing is identified empirically; fall back to the
    # parametric fit's tail (handled by caller) or the censored fraction.
    return float(np.mean(is_censored))


def _lognormal_mle_censored(observed, is_censored, tol=1e-6, iters=200):
    """EM-style MLE for lognormal(mu, sigma) under right-censoring."""
    y = np.log(np.maximum(observed, 1.0))
    cen = is_censored.astype(bool)
    mu, sigma = float(np.mean(y)), float(np.std(y) + 1e-6)
    if not cen.any():
        return mu, sigma
    yc = y[~cen]
    L = y[cen]  # log cap for censored rows
    for _ in range(iters):
        z = (L - mu) / sigma
        # E[Y | Y > L] for normal via inverse Mills ratio
        from math import erf, exp, pi, sqrt
        pdf = np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)
        sf = 0.5 * (1 - np.vectorize(erf)(z / np.sqrt(2)))
        sf = np.maximum(sf, 1e-12)
        lam = pdf / sf
        ey = mu + sigma * lam
        ey2 = mu**2 + sigma**2 + sigma * (L + mu) * lam
        n = len(y)
        mu_new = (yc.sum() + ey.sum()) / n
        var_new = (np.sum(yc**2) + ey2.sum()) / n - mu_new**2
        sigma_new = float(np.sqrt(max(var_new, 1e-8)))
        if abs(mu_new - mu) < tol and abs(sigma_new - sigma) < tol:
            mu, sigma = mu_new, sigma_new
            break
        mu, sigma = float(mu_new), sigma_new
    return mu, sigma


def _lognormal_q(mu, sigma, q):
    # quantile of lognormal via normal quantile (Acklam-free: use erfinv approx)
    from statistics import NormalDist
    return float(np.exp(NormalDist(mu, sigma).inv_cdf(q)))


def _lognormal_sf(mu, sigma, c):
    from statistics import NormalDist
    if c <= 0:
        return 1.0
    return float(1.0 - NormalDist(mu, sigma).cdf(np.log(c)))


def _isotonic_nonincreasing(values):
    """Pool-adjacent-violators projection onto a nonincreasing sequence."""
    neg = [-v for v in values]
    level_vals = []
    level_weights = []
    for x in neg:
        level_vals.append(x)
        level_weights.append(1.0)
        while len(level_vals) > 1 and level_vals[-2] > level_vals[-1]:
            w2_, v2_ = level_weights.pop(), level_vals.pop()
            w1_, v1_ = level_weights.pop(), level_vals.pop()
            nw = w1_ + w2_
            nv = (v1_ * w1_ + v2_ * w2_) / nw
            level_vals.append(nv)
            level_weights.append(nw)
    out = []
    for v_, w_ in zip(level_vals, level_weights):
        out.extend([v_] * int(round(w_)))
    return [-x for x in out]


def _bisect_sf(sf_func, target, hi_start, iters=100):
    """Find x >= 0 with sf_func(x) == target, assuming sf_func is nonincreasing."""
    lo, hi = 0.0, float(hi_start)
    # Grow hi until sf_func(hi) < target (or give up after a bounded number of doublings).
    grow = 0
    while sf_func(hi) > target and grow < 60:
        hi *= 2.0
        grow += 1
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if sf_func(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def estimate(observed: np.ndarray, is_censored: np.ndarray, cap: int,
             caps=(4096, 8000, 14096, 16000, 20000, 32000)) -> dict:
    from statistics import NormalDist

    is_censored = is_censored.astype(bool)
    n = len(observed)
    cen_frac = float(np.mean(is_censored))
    n_uncensored = int(n - is_censored.sum())

    mu, sigma_raw = _lognormal_mle_censored(observed, is_censored)
    k = 10
    sigma = (k * 0.85 + n_uncensored * sigma_raw) / (k + n_uncensored)

    clamped = np.where(is_censored, cap, observed)
    log_clamped = np.log(np.maximum(clamped, 1.0))
    median_q = float(np.exp(np.quantile(log_clamped, 0.5, method="median_unbiased")))
    q90_q = float(np.exp(np.quantile(log_clamped, 0.9, method="median_unbiased")))

    # Median: empirical (log-space median-unbiased quantile) if identified,
    # else parametric floored at the clamped-data quantile (a valid lower bound).
    if cen_frac < 0.5:
        median = median_q
    else:
        median = max(_lognormal_q(mu, sigma, 0.5), median_q)

    # q90: empirical if identified, else parametric floored the same way.
    if cen_frac < 0.10:
        q90 = q90_q
    else:
        q90 = max(_lognormal_q(mu, sigma, 0.90), q90_q)

    # Identified p_ge(c <= cap): raw empirical proportions, then isotonic
    # (nonincreasing-in-c) projection since P(X >= c) must not increase with c.
    identified_caps = sorted(c for c in caps if c <= cap)
    raw_p_emp = {c: _p_ge_empirical(observed, is_censored, cap, c) for c in identified_caps}
    if identified_caps:
        projected = _isotonic_nonincreasing([raw_p_emp[c] for c in identified_caps])
        p_ge = {c: float(v) for c, v in zip(identified_caps, projected)}
    else:
        p_ge = {}

    unidentified_caps = sorted(c for c in caps if c > cap)
    for c in unidentified_caps:
        p_ge[c] = _lognormal_sf(mu, sigma, c)

    # Pinned two-component mixture correction for the unidentified branches,
    # gated on evidence that the single-lognormal fit is materially misspecified.
    if cen_frac >= 0.10 and identified_caps:
        d = float(np.mean([abs(_lognormal_sf(mu, sigma, c) - raw_p_emp[c]) for c in identified_caps]))
        if d > 0.02:
            s = math.sqrt(median_q * cap)
            below_s_mask = (~is_censored) & (observed < s)
            below_s = observed[below_s_mask]
            if below_s.size >= 10:
                log_below = np.log(np.maximum(below_s, 1.0))
                mu1 = float(np.mean(log_below))
                sigma1 = float(np.std(log_below) + 1e-6)
                p_emp_s = float(np.mean((observed >= s) | is_censored))
                S1s = _lognormal_sf(mu1, sigma1, s)
                if (1.0 - S1s) > 1e-6:
                    w2_corr = (p_emp_s - S1s) / (1.0 - S1s)
                else:
                    w2_corr = float("nan")
                if math.isfinite(w2_corr):
                    w2 = min(max(w2_corr, 0.02), 0.98)
                else:
                    w2 = min(max(p_emp_s, 0.02), 0.98)

                S1cap = _lognormal_sf(mu1, sigma1, cap)
                sigma2 = 0.6
                S2cap = min(max((cen_frac - (1.0 - w2) * S1cap) / w2, 0.001), 0.999)
                mu2 = math.log(cap) - sigma2 * NormalDist().inv_cdf(1.0 - S2cap)

                if math.isfinite(mu2):
                    def mixture_sf(x, mu1=mu1, sigma1=sigma1, mu2=mu2, sigma2=sigma2, w2=w2):
                        return (1.0 - w2) * _lognormal_sf(mu1, sigma1, x) + w2 * _lognormal_sf(mu2, sigma2, x)

                    q90_mix = _bisect_sf(mixture_sf, 0.10, hi_start=max(cap, math.exp(mu2 + 5 * sigma2)))
                    if math.isfinite(q90_mix) and q90_mix > 0:
                        q90 = max(q90_mix, q90_q)

                    for c in unidentified_caps:
                        val = mixture_sf(c)
                        if math.isfinite(val):
                            p_ge[c] = val

    # Final safety clamp: beyond-cap tail can never exceed the exactly-known
    # censored fraction, and must be nonincreasing in c.
    running_max = cen_frac
    for c in unidentified_caps:
        v = min(max(p_ge[c], 0.0), running_max)
        p_ge[c] = v
        running_max = v

    return {"median": median, "q90": q90, "p_ge": p_ge}
