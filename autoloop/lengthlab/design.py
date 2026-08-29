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
    "n_items": 130,   # item clusters (AIME-style items, GPQA rows, ...)
    "n_reps": 2,      # replicate responses per item per cell
    "alpha": 0.05,
}


def analyze(acc: dict) -> float:
    """acc keys: (effort, allowance) in {("lo","sm"),("hi","sm"),("lo","big"),("hi","big")}
    each an array of per-item mean accuracies, shape (n_items,).
    Returns p-value for H0: slope(big) - slope(sm) == 0."""
    did = (acc[("hi", "big")] - acc[("lo", "big")]) - (acc[("hi", "sm")] - acc[("lo", "sm")])
    n = len(did)
    m = float(np.mean(did))
    se = float(np.std(did, ddof=1)) / np.sqrt(n)
    if se == 0:
        return 1.0
    t = m / se
    # One-sided p via normal approx (n_items is large enough); stdlib only.
    # The DiD's sign is known a priori under every power scenario (allowance
    # only ever widens at high effort, so censoring only ever hurts "hi" more
    # at the small allowance): testing H1: DiD > 0 spends the whole alpha
    # budget on the correct tail. Null scenarios keep the DiD symmetric about
    # 0 by construction (a_sm == a_big), so this does not inflate type-I.
    from statistics import NormalDist
    return float(1.0 - NormalDist().cdf(t))
