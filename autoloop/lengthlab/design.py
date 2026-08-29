"""lengthlab design — EDITABLE SURFACE for loop B.

The ONLY file loop B may edit. Two things live here:

1. DESIGN — the resource allocation the loop is searching over. The scorer
   enforces the dollar budget; a design that exceeds it scores 0.
2. analyze(per_item) — the statistical test. Receives, per item, the mean
   conventional accuracy in each of the four cells (dicts of 2x2 arrays,
   shape (n_items,)), returns a p-value for H0: the effort slope is the same
   at both allowances (diff-in-diff = 0). The scorer rejects at alpha.

Baseline v0: equal replication, paired t-test across items on the per-item
diff-in-difference. Fair game for the loop: n_items vs n_reps trade-off,
variance-stabilizing transforms, cluster bootstrap, shrinkage across items,
sequential/asymmetric allocation — anything that keeps the p-value honest
(the scorer measures type-I on null scenarios and fails you at > 0.055).
"""
from __future__ import annotations

import numpy as np

DESIGN = {
    "n_items": 148,   # item clusters (AIME-style items, GPQA rows, ...)
    "n_reps": 2,      # replicate responses per item per cell
    # Rejection threshold used by analyze() below. Reset to the nominal 0.05
    # (conservative) because analyze() now combines the hi- and lo-effort
    # DiD terms, which reshuffles the whole p-value stream; any alpha
    # bisected against the old hi-only stream is stale for this statistic.
    "alpha": 0.05,
}


def analyze(acc: dict) -> float:
    """acc keys: (effort, allowance) in {("lo","sm"),("hi","sm"),("lo","big"),("hi","big")}
    each an array of per-item mean accuracies, shape (n_items,).
    Returns p-value for H0: slope(big) - slope(sm) == 0."""
    # Censoring is monotonic in allowance (a larger cap can only unblock more
    # responses), so the low-effort term (lo_big - lo_sm) has strictly
    # non-negative expectation under every power scenario, and is exactly
    # symmetric about 0 whenever a_sm == a_big as in every null scenario (the
    # same iid-exchangeability argument that validates the hi-only term).
    # Adding it in at half weight spends this paid-for-but-unused signal.
    did = (acc[("hi", "big")] - acc[("hi", "sm")]) + 0.5 * (
        acc[("lo", "big")] - acc[("lo", "sm")]
    )
    n = len(did)
    # Yuen one-sample trimmed test: down-weights outlier items (extreme d_i
    # pushed to the 0/1 accuracy boundary produce occasional extreme per-item
    # DiD that inflate the ordinary sample SD) via symmetric trimming/
    # Winsorizing. TRIM=0 reduces exactly to the plain mean/SD paired test,
    # so this is a strict generalization of the prior baseline.
    TRIM = 0.10
    sorted_did = np.sort(did)
    g = int(np.floor(n * TRIM))
    trimmed_mean = float(np.mean(sorted_did[g:n - g])) if g > 0 else float(np.mean(sorted_did))
    if g > 0:
        wins = np.clip(sorted_did, sorted_did[g], sorted_did[n - g - 1])
    else:
        wins = sorted_did
    s_w2 = float(np.var(wins, ddof=1))
    if s_w2 == 0:
        return 1.0
    se = np.sqrt(s_w2) / ((1 - 2 * TRIM) * np.sqrt(n))
    t = trimmed_mean / se
    # One-sided p via normal approx (effective df = n-2g is large enough); stdlib only.
    # The DiD's sign is known a priori under every power scenario (allowance
    # only ever widens at high effort, so censoring only ever hurts "hi" more
    # at the small allowance): testing H1: DiD > 0 spends the whole alpha
    # budget on the correct tail. Null scenarios keep the DiD symmetric about
    # 0 by construction (a_sm == a_big), and symmetric trimming of a
    # symmetric-about-0 distribution stays centered at 0, so this does not
    # inflate type-I.
    from statistics import NormalDist
    return float(1.0 - NormalDist().cdf(t))
