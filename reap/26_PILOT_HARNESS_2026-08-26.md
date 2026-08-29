# Exploratory Inkling length pilot: offline harness

**Date:** 2026-08-26
**Status:** Exploratory tooling, dry-run and mock only. `pilot.enabled: false`.
No provider, smoke, or paid call was made in building or testing this. Nothing
here authorizes one. This harness is separate from Task E (confirmatory runner
and budget gates): it reuses `confirmatory.AttemptLedger` for its ledger but
freezes no confirmatory choice and produces only data labeled exploratory.

## What was built

| File | Purpose |
|---|---|
| `src/effort_atlas/pilot_select.py` | Emits both candidate selection rules per dataset, so Chirag's decision 2 is a config switch. Content-free output. |
| `capabilities/selections/selection_first200_v1.json` | Literal first 200 rows of each pilot split, by `source_row_index`. |
| `capabilities/selections/selection_stratified200_seed20260830_v1.json` | Seeded, proportional across a per-dataset stratum (largest-remainder rounding), exactly 200. |
| `src/effort_atlas/wrapper.py` | `pilot-wrapper-v1`: source-item-v1 row to model-facing request. Lettered options (source order; GPQA shuffled with a recorded seeded permutation), strict `Final answer:` terminator where a gold exists, IFEval verbatim with no terminator, WildBench turns as chat messages. `strict_terminator_present()` checks the last non-empty line only. |
| `src/effort_atlas/pilot.py` | Runner. `--dry-run` (default) prints the cost table; `--mock` runs the full pipeline with cap-aware fabricated responses; `--live` refuses unless every human gate is open. Hash-chained content-free ledger, gitignored response file, per-dataset and total ceilings checked **before** each call against the worst case of that call, circuit breaker, summary with P(length >= c). |
| `config_pilot_inkling.yaml` | OpenRouter to Together, pinned, `max_retries: 0`, `max_tokens 32000` explicit, one effort level, ceilings, and null budget fields that must be filled from the account page. |
| `src/effort_atlas/client.py` | One additive change: `complete(..., messages=)` sends a multi-turn history; single-turn behavior and cache keys unchanged. |
| `tests/test_pilot.py` | 18 offline tests, green on a clean checkout (synthetic rows; the committed selection files are integrity-checked). |

## Run it

```bash
uv run python -m effort_atlas.pilot_select --rule both          # regenerates both selections (deterministic)
uv run python -m effort_atlas.pilot                              # dry run: cost table, zero calls
uv run python -m effort_atlas.pilot --mock                       # 1,000 fabricated responses, full ledger
uv run python -m effort_atlas.pilot --selection capabilities/selections/selection_stratified200_seed20260830_v1.json --mock
```

The mock and live paths need the four reacquirable JSONLs and, for GPQA, the
local `restricted_local/` file (`capabilities/acquire.py`). GPQA text is loaded
only from that file, verified against the committed skeleton's
`full_row_sha256`, and never written anywhere outside `results_pilot/`
response files, which are gitignored.

## Gate 5 evidence (ledger and ceiling enforcement tested offline)

`tests/test_pilot.py::CeilingTests::test_run_halts_on_simulated_overrun_and_ledger_verifies`:
with a $0.40 per-dataset ceiling and a fake client that bills a full 32,000
tokens per call (about $0.128), the runner makes exactly three calls and halts
**before** the fourth, exits with code 3, writes the halt into the summary, and
the hash-chained ledger verifies. The full 1,000-item mock run on 2026-08-26
(fabricated lengths, not evidence about Inkling) finished with 1,000 ledger
events, `ledger_verified: true`, no prompt or response text in the ledger or
the rendered manifest, and $20.59 of fabricated spend against the dry-run
expectation of $20.80.

## Dry-run cost table (config prices, unverified since July)

| Dataset | Items | Expected $ | Worst case $ |
|---|---:|---:|---:|
| mmlu_pro | 200 | 4.09 | 25.96 |
| gpqa_main | 200 | 4.10 | 25.97 |
| ifeval | 200 | 4.06 | 25.93 |
| wildbench_v2 | 200 | 4.47 | 26.34 |
| omni_math | 200 | 4.08 | 25.95 |
| **Total** | 1,000 | **20.80** | **130.15** |

Worst case per dataset sits under the $30 per-dataset ceiling; the $130 total
worst case exceeds the placeholder $60 total ceiling, which is what the staged,
per-dataset run with pre-call ceiling checks is for.

## New evidence for decision 2 (selection rule), from the committed selection files

The literal first-200 rule is category-skewed on three of five datasets, not one:

- **MMLU-Pro:** 200 of 200 are `business` (14 categories exist).
- **WildBench v2:** the first 200 contain **zero** `Coding & Debugging` and **zero**
  `Creative Writing` rows; the proportional allocation gives them 33 and 28.
- **Omni-MATH:** `Applied Mathematics` gets 4 rows in the first 200 versus 33
  proportional; Number Theory 47 versus 27.
- GPQA and IFEval are effectively unordered; both rules give similar strata.

## Still blocked before any live call

Gate 2 (preflight document approved in writing), gate 3 (balance read from the
account page, prices re-pinned with a date, mock dry-run of the config against
the provider done by a human), gate 4 (selection rule frozen by Chirag). The
`--live` path enumerates exactly which of these is still open and exits 2.
