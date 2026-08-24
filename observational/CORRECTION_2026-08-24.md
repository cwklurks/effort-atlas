# Correction: the at-cap zero-accuracy headline is 15 of 17, not 16 of 17

**Date:** 2026-08-24
**Status:** Additive correction note. `observational/RESULTS.md` is protected and is
not edited; this file supersedes its headline sentence. No provider, smoke, or
confirmatory call was made in producing this correction.

## What is corrected

`observational/RESULTS.md` (line 11) states that in **16 of the 17** affected
model×dataset series with ≥4 capped rows, accuracy at the cap is exactly 0%. The
committed figure inputs support **15 of 17**, with **two** nonzero exceptions, not one.

## Canonical corrected sentence (use this everywhere)

> In the current exploratory comparison, 15 of 17 selected groups had zero
> accuracy among inferred cap rows or observed length stops; MathArena's cap labels
> are inferred, while HELM Gemini's are observed.

## Recomputation (2026-08-24, this machine)

Recomputed directly from the committed summary artifacts, byte-pinned here:

| Input | SHA-256 |
|---|---|
| `observational/results_matharena.parquet` | `15e2ed23be4a895d236e9b4270d5fafd63033172a06131d47b6ea910e14511d3` |
| `observational/results_helm.parquet` | `5b9b0613f11d68e3ff453df7daf192cdeadc7c7f6574d8e83dd1cc973013266c` |

Selection rule (unchanged from `RESULTS.md`): MathArena groups with
`round_cap == true` and `n_at_cap >= 4`, plus the HELM group with labeled finish
reasons.

- MathArena: **16** selected groups; **14** have `acc_at_cap == 0`; **2** do not:

  | Group | Correct / inferred cap rows | Accuracy |
  |---|---:|---:|
  | Phi-4-reasoning-plus, `hmmt_feb_2025_outputs` | 1 / 38 | 2.63% |
  | s1.1-32B, `hmmt_feb_2025_outputs` | 1 / 9 | 11.11% |

- HELM: **1** finish-labeled group (`google_gemini-3-pro-preview`, GPQA CoT,
  v1.15.0): 42 `finish_reason="length"` rows, 0 correct.

- Combined: **15 of 17** groups with zero at-cap or length-stop accuracy.

Reproduce with: load the two parquets above, filter MathArena rows on
`round_cap & (n_at_cap >= 4)`, count `acc_at_cap == 0`; take the HELM row with
`finish_labeled == true` and check `acc_finish_length`. This recomputation matches
the reconciliation already recorded in
`reap/20_BENCHMARK_COMPARISON_2026-08-18.md` ("Reconciliation of the 15-of-17
headline").

## Relationship to the earlier, unavailable correction

`reap/23_POST_MEETING_REVIEW_2026-08-23.md` (item 13) records that a correction
note `observational/CORRECTION_2026-08-13.md` exists as commit `6b2e69d` on branch
`codex/observational-headline-correction`. As of 2026-08-24, that branch and that
commit are **not present on `origin` (github.com/cwklurks/effort-atlas)** and could
not be fetched or merged from this machine — the branch apparently was never
pushed. Its content is therefore UNVERIFIED here. This file independently
establishes the same corrected headline from the committed artifacts. If the
original branch is later pushed, the two notes should agree; any disagreement is a
new finding to reconcile, not to silently overwrite.

## Handling rule

Never repeat the 16-of-17 figure. The historical line in
`observational/RESULTS.md` stays as written (protected file); every downstream
document must use the canonical sentence above.
