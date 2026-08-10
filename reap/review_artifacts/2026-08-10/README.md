# Phase 3 external review artifacts — 2026-08-10

Supporting scripts and outputs for `reap/14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md`
(independent external review of `13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md`,
reviewer: Claude Fable 5).

## Provenance

Both scripts were **transferred verbatim** from the review session's scratchpad —
they are the exact files that produced the numbers in the review's tables, not
post-hoc reconstructions (transfer verified by SHA-256 at copy time;
`reap_sims.py` = `0ab92e474e69bd76ebaa956724128010218d2a2a06662e9643dde2870bcd772b`).
The `.out.txt` files are a rerun in this worktree; the rerun reproduced the
originally reported numbers exactly.

## Contents

- `reap_sims.py` — the two review simulations. Deterministic: one
  `numpy.random.default_rng(20260722)` consumed sequentially.
  - Sim 1: one-sided H3 interaction power (α=0.05), 3,000 Monte Carlo reps per
    cell over m∈{30,60} items × n∈{8,20} replicates × three mechanism scenarios.
    Generative assumptions (stated in the review): item solve-prob ~ Beta(2,2);
    high effort +0.08 absolute solve; shared item verbosity offset
    N(0, 0.5²) on the truncation logit; cell-mean truncation rates per scenario;
    item-clustered z-test approximating the item-bootstrap.
  - Sim 2: H6 certification feasibility under PERFECT calibration, 400 outer
    reps × 800 item-bootstrap resamples, m∈{30,60} × cells∈{4,8,20}; one-sided
    95% upper bound on max absolute cell error vs the 0.10 tolerance.
- `reap_sims.out.txt` — rerun output (matches the review's two tables).
- `reap_costs.py` — independent recomputation of every panel's generation count,
  token bounds, and conservative cost maximum. Reproduces Terra/Luna/Sol and
  OpenRouter figures from doc-stated rates; demonstrates that no repository-recorded
  Tinker rate reproduces the Phase 3 Tinker maxima (they require the live page's
  2026-08-10 rates, two of them at a 50% limited-time discount — see the review's
  budget section).
- `reap_costs.out.txt` — rerun output.

## Status

These are **review evidence**, not the frozen power analysis. The frozen power
analysis is Chirag's, to be rerun with data-derived length priors
(`results_matharena.parquet`). Numbers count as independently verified only after
a third-party rerun (Codex audit step).

No provider or model-generation calls are made by either script.
