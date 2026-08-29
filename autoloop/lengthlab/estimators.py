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
    return float(1.0 - NormalDist(mu, sigma).cdf(np.log(c)))


def estimate(observed: np.ndarray, is_censored: np.ndarray, cap: int,
             caps=(4096, 8000, 14096, 16000, 20000, 32000)) -> dict:
    cen_frac = float(np.mean(is_censored))
    mu, sigma = _lognormal_mle_censored(observed, is_censored)

    # Median: empirical if identified (less than half the mass censored),
    # else parametric.
    if cen_frac < 0.5:
        median = float(np.median(np.where(is_censored, cap, observed)))
    else:
        median = _lognormal_q(mu, sigma, 0.5)

    # q90: empirical if identified, else parametric tail.
    if cen_frac < 0.10:
        q90 = float(np.quantile(np.where(is_censored, cap, observed), 0.90))
    else:
        q90 = _lognormal_q(mu, sigma, 0.90)

    p_ge = {}
    for c in caps:
        if c <= cap:
            p_ge[c] = _p_ge_empirical(observed, is_censored, cap, c)
        else:
            p_ge[c] = _lognormal_sf(mu, sigma, c)
    return {"median": median, "q90": q90, "p_ge": p_ge}
