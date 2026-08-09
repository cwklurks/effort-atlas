# REAP preregistration v2 — SKELETON (to be completed with Chirag, then frozen)

**Rule:** this document supersedes the 2026-07-22 preregistration for all REAP confirmatory work. It must be completed, committed, and hashed BEFORE the first confirmatory paid call under REAP. The 2026-07-22 document remains the unaltered record of the pre-funding design. Until this freezes, all paid calls are labeled exploratory/smoke.

## 1. Question and estimands  *(carry from Phase I; add)*

- D_c, I, token-starved/no-answer definition: unchanged.
- NEW — dose-response estimands: accuracy surface A(e, c) and unanswered-stop surface U(e, c) over the effort × cap grid.
- NEW — cap-invariance estimand: calibration error between truncation rates predicted from Arm C length distributions and observed rates in Arm B, per cap and effort. [METRIC TBD WITH CHIRAG: KS on common support / calibration curve / both]

## 2. Hypotheses

- H1–H4: carry from Phase I (differential censoring; cap rescue; interaction; cross-panel direction).
- H5 [NEW]: unanswered-stop rate rises monotonically with effort at fixed cap and falls monotonically with cap at fixed effort.
- H6 [NEW]: truncation rates at cap c are predicted by the length distribution measured at the reference cap within [TBD] calibration tolerance (cap-invariance).
- [DECIDE]: directional prediction for completed-only accuracy across effort at the reference cap.

## 3. Design  *(fill from 01_EXPERIMENT_OUTLINE_v2 once Chirag signs off)*

- Panels: P1 Inkling/Tinker, P2 GPT-OSS-120B/Tinker, P3 gpt-5.6-terra/OpenAI. P0 = debugging, never confirmatory.
- Arms and n per cell: A [n=__], B [n=__], C [n=__]. Effort anchors: [__]. Cap grid: [__].
- Datasets: [core: HMMT 2025+2026 + AIME __ ; extensions: __]. Item lists frozen with hashes.
- Sampling params per platform (explicit max_tokens ALWAYS; temperature/seed policy: [__]).
- Schedules: seeded, hashed, committed before execution (Phase I machinery, re-exported for v2).

## 4. Measurement and validity rules

- Termination logged at collection (stop_reason / incomplete_details / finish_reason+receipt). Row validity rules per platform: [adapt Phase I list].
- Grader v2 (terminator-required extraction) frozen at commit [__]; strict primary, flexible secondary on MCQ.
- Cap-semantics probe results per platform surface attached as appendix before main blocks.
- Effort delivery verification per platform (renderer/system-message on Tinker; enum on OpenAI) — evidence that effort and cap are independently set.

## 5. Analysis  *(freeze code before data)*

- Per-cell reporting: Phase I list + replicate-level variance decomposition [MODEL TBD WITH CHIRAG: item random effects / hierarchical binomial].
- Primary tests: I per panel (item-clustered bootstrap, 10k draws, seed [__]); H5 monotonicity [method __]; H6 calibration [metric __].
- Interpretation guards: carried verbatim — no result called established solely on a narrowly zero-excluding interval; zero-spanning intervals not read as absence; panels never pooled.
- Missingness and sensitivity: prespecified worst-case bounds per cell.

## 6. Budget and stopping

- Pools and ceilings per 02_BUDGET_AND_COSTS: Tinker committed ceiling $[__]; OpenAI $[__]; kill thresholds; usage reconciliation cadence.
- Stop rules: [carry Phase I: accounting failure, cap-semantics violation, ceiling] + truncation-prediction deviation >15pp mid-run → pause.

## 7. Exploratory registry

Everything already run or free (MathArena public-output analyses, pilots, smoke, P0) is exploratory and listed here with dates, never pooled into confirmatory estimates: [running list].

## 8. Amendment rule

Pre-data: dated committed amendments only. Post-first-valid-response: hypotheses, arms, grading, and stopping rules frozen; deviations logged and labeled.
