# Phase 3 external review artifacts — 2026-08-10

Supporting scripts and outputs for `reap/14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md`
(independent external review of `13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md`,
reviewer: Claude Fable 5).

## Provenance

The committed scripts reproduce the review tables, and the `.out.txt` files are a
fresh deterministic rerun in this worktree. The claim that these bytes originated
as an exact scratchpad transfer was made by the external reviewer, but that origin
claim was not independently verified by Codex. The reviewable repository facts
are the committed bytes, their hashes, and the reproduced outputs:

- `reap_sims.py` SHA-256:
  `0ab92e474e69bd76ebaa956724128010218d2a2a06662e9643dde2870bcd772b`
- `reap_costs.py` SHA-256:
  `84c1f07b52ca99f4c470594341df1b1ffcf4c8ad775d0358b610f4aaf15d484c`

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
  OpenRouter figures from rates stated in the reviewed document. Its Tinker-rate
  diagnostic reflects the repository state at review time. The later dated route
  artifact at `reap/phase3_evidence/route_prices_2026-08-10.json` is the current
  advisory planning source; freeze-day evidence and exact schedules remain
  required.
- `reap_costs.out.txt` — rerun output.

## Status

These are **review evidence**, not the frozen power analysis. The frozen power
analysis is Chirag's, to be rerun with data-derived length priors
(`results_matharena.parquet`). Codex reran the committed scripts and confirmed
their deterministic outputs; that verifies code-to-table reproduction, not the
scientific assumptions or scratchpad-origin claim.

No provider or model-generation calls are made by either script.
