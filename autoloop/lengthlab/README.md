# lengthlab — autoresearch scaffold for the synthetic length lab

**Date:** 2026-08-28 · **Status:** EXPLORATORY TOOLING. Not part of any
confirmatory path; freezes nothing; makes no provider call anywhere (nothing
here imports `effort_atlas.client`, and the loop configs forbid network).
Everything an optimization loop produces here is design-phase input to REAP
preregistration v2 and the paper's censoring-estimation section — it becomes
citable only after human review, as a new dated `reap/` doc.

## What this is

One frozen synthetic generator, two independent optimization loops:

| Loop | Editable file | Metric (one float) | Direction | Feeds |
|---|---|---|---|---|
| A | `estimators.py` | recovery error of median / q90 / P(len ≥ c) vs generator truth, across visible regimes × caps × seeds | min | paper: censoring-aware length estimation |
| B | `design.py` | worst-case detection power of the 2×2 effort×allowance design at fixed budget, hard-gated on type-I calibration | max | prereg v2: knob 4 (n per cell, test choice) |

Frozen surface (never edited by a loop): `generator.py`, `score_recovery.py`,
`score_power.py`, `final_eval.py`, both `metric_*.sh`, both `loop*.json`.
The loop configs also copy the repo-level protected paths (AGENTS.md
safeguards 1, 2, 5) verbatim.

## Baselines (measured 2026-08-28, container Python 3, numpy 2.4.4)

- Loop A: `0.026611 ± 0.001470` over 5 runs → `min_delta = 0.003`.
- Loop B: `0.074500 ± 0.002915` over 5 runs → `min_delta = 0.006`.
  Baseline design: 130 items × 2 reps × 4 cells, paired t on per-item
  diff-in-diff; cost $35.05 of the $40 budget; type-I at nominal.
  The binding scenario is `mix_bimodal` (power ~0.07): bimodal length
  distributions are where the baseline design is nearly blind. That gap is
  the loop's job.

Both scorers are deterministic given `--base-seed` and run in under a second,
so an overnight session is hundreds of iterations, not dozens.

## Run it (Linux box)

```bash
# from the repo root, after pulling the branch
python3 autoloop/lengthlab/score_recovery.py            # loop A metric
python3 autoloop/lengthlab/score_power.py               # loop B metric
python3 autoloop/lengthlab/score_power.py --json        # why a 0.0 happened
python3 autoloop/lengthlab/score_recovery.py --repeat 5 # re-measure spread
```

Dependencies: python3 + numpy, stdlib otherwise (`uv run --with numpy` works
if the environment lacks it). Run the loop with whatever proposer you like —
pi-autoresearch (`loopA.json` / `loopB.json` carry metric cmd, direction,
`min_delta`, editable and protected lists; adapt key names to the harness
schema if it differs), or a Claude Code / Codex session following the same
contract: one hypothesis written down per iteration, edit only the editable
file, run the metric, keep the change only if it beats the incumbent by
`min_delta`, revert otherwise, commit each kept step on a `codex/autoloop-*`
branch.

## Holdout protocol (the honesty mechanism)

1. Pick a secret integer seed. Do NOT reuse `424242` (it appears in the chat
   transcript that built this scaffold) and do not commit or paste yours.
2. After a loop session:
   `LENGTHLAB_HOLDOUT_SEED=<seed> python3 autoloop/lengthlab/final_eval.py`
3. Report the holdout numbers next to the visible numbers, always as a pair.
   A large gap = the loop overfit the visible regimes; say so.

Known behavior worth keeping: holdout regimes can make the incumbent design
exceed the budget (observed with a test seed: $43.53 > $40 → power score 0).
That is a finding, not a bug — a design whose feasibility depends on assumed
length distributions is budget-fragile, and the loop should be pushed toward
designs that stay feasible under length misspecification.

## Assumptions to review with Chirag (before trusting loop-B output)

The accuracy DGP in `score_power.py` (logistic item difficulty, effort
benefit `b_hi = 0.35`, length multiplier `2.0` at high effort, unanswered
length stops scored 0 under the unchanged conventional grader, null built by
equalizing allowances) is a set of assumptions, not measurements. The Inkling
pilot's real length data should re-anchor `VISIBLE_REGIMES` (new dated
decision + rerun), and Chirag should bless or amend the DGP before any loop-B
result is used in prereg v2.

## What goes to Chirag after a run

The kept-hypothesis chain (one line per kept iteration: hypothesis → visible
score), the final visible-vs-holdout pair for each loop, and the diff of the
editable file — nothing else. Five-minute review, full provenance.
