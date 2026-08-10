"""Power and H6-feasibility simulations for the REAP Phase 3 external review.

Sim 1: power for the one-sided H3 interaction test with m item clusters, n replicates.
Sim 2: feasibility of certifying H6 max-abs calibration error <= 0.10 via a
       one-sided 95% item-bootstrap upper bound, under PERFECT calibration
       (best case: any real misfit only makes it harder).
"""
import numpy as np

rng = np.random.default_rng(20260722)


def inv_logit(x):
    return 1.0 / (1.0 + np.exp(-x))


def logit(p):
    return np.log(p / (1.0 - p))


# ---------------- Sim 1: H3 interaction power ----------------
# Cells: (effort in {lo, hi}) x (cap in {4K, 16K}).
# Per item: solve prob s_i ~ Beta(2,2); high effort adds delta_solve (capped at 1).
# Truncation prob per cell mean, with shared item verbosity offset u_i on logit scale.
# Observed P(correct) = (1 - t) * s.  Estimator: mean over items of per-item
# interaction from n replicates per cell; one-sided z-test on item-level values
# (approximates the item-clustered percentile bootstrap for a mean).

def sim1_power(m, n, t_hi4, t_lo4=0.10, t_hi16=0.05, t_lo16=0.02,
               delta_solve=0.08, u_sd=0.5, reps=3000):
    rejections = 0
    true_Is = []
    ses = []
    for _ in range(reps):
        s_lo = rng.beta(2, 2, size=m)
        s_hi = np.minimum(1.0, s_lo + delta_solve)
        u = rng.normal(0, u_sd, size=m)
        t = {}
        for name, tm in [("lo4", t_lo4), ("hi4", t_hi4), ("lo16", t_lo16), ("hi16", t_hi16)]:
            t[name] = inv_logit(logit(tm) + u)
        p_lo4 = (1 - t["lo4"]) * s_lo
        p_hi4 = (1 - t["hi4"]) * s_hi
        p_lo16 = (1 - t["lo16"]) * s_lo
        p_hi16 = (1 - t["hi16"]) * s_hi
        true_I = np.mean((p_hi16 - p_lo16) - (p_hi4 - p_lo4))
        true_Is.append(true_I)
        # replicate draws
        e_i = (
            (rng.binomial(n, p_hi16) - rng.binomial(n, p_lo16))
            - (rng.binomial(n, p_hi4) - rng.binomial(n, p_lo4))
        ) / n
        Ihat = e_i.mean()
        se = e_i.std(ddof=1) / np.sqrt(m)
        ses.append(se)
        if se > 0 and Ihat / se > 1.645:
            rejections += 1
    return np.mean(true_Is), np.mean(ses), rejections / reps


print("=== Sim 1: H3 one-sided power (alpha=0.05), delta_solve=+0.08 ===")
print(f"{'scenario':<28}{'m':>4}{'n':>4}{'true I':>9}{'mean SE':>9}{'power':>8}")
for label, t_hi4 in [("strong (hi@4K trunc 45%)", 0.45),
                     ("moderate (hi@4K trunc 30%)", 0.30),
                     ("weak (hi@4K trunc 20%)", 0.20)]:
    for m in (30, 60):
        for n in (8, 20):
            tI, se, pw = sim1_power(m, n, t_hi4)
            print(f"{label:<28}{m:>4}{n:>4}{tI:>9.3f}{se:>9.3f}{pw:>8.2f}")

# ---------------- Sim 2: H6 certification feasibility ----------------
# Perfect calibration: predicted and observed truncation share the same per-item
# q_i per cell. Reference arm gives n_ref draws/item; dose arm n_obs draws/item.
# Error per cell = |obs_rate - pred_rate| (item-paired). M = max over cells.
# Bootstrap items (jointly across all cells + reference), 95th pct of M = upper bound.
# Certify if upper bound <= 0.10.

def sim2_h6(m, n_cells, n_obs=8, n_ref=8, v_sd=0.7, reps=400, boot=800):
    # cell mean truncation rates spread over a realistic range
    cell_means = np.linspace(0.03, 0.65, n_cells)
    cert = 0
    bounds = []
    for _ in range(reps):
        v = rng.normal(0, v_sd, size=m)
        q = inv_logit(logit(cell_means)[None, :] + v[:, None])  # m x cells
        obs = rng.binomial(n_obs, q) / n_obs
        pred = rng.binomial(n_ref, q) / n_ref
        err_items = obs - pred  # m x cells
        # bootstrap over items
        maxes = np.empty(boot)
        for b in range(boot):
            idx = rng.integers(0, m, size=m)
            maxes[b] = np.abs(err_items[idx].mean(axis=0)).max()
        ub = np.quantile(maxes, 0.95)
        bounds.append(ub)
        if ub <= 0.10:
            cert += 1
    return np.mean(bounds), cert / reps


print("\n=== Sim 2: H6 upper-bound certification under PERFECT calibration ===")
print(f"{'m':>4}{'cells':>7}{'mean 95% UB':>13}{'P(certify @0.10)':>18}")
for m in (30, 60):
    for n_cells in (4, 8, 20):
        ub, p = sim2_h6(m, n_cells)
        print(f"{m:>4}{n_cells:>7}{ub:>13.3f}{p:>18.2f}")
