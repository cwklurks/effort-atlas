# REAP Phase 3 supervisor decision packet

**Dated:** 2026-08-08

**Status: HUMAN DECISIONS REQUIRED**

**Purpose:** decision aid for Connor Klann and Chirag Nagpal; not a preregistration,
approval record, route activation, spending authorization, or claim that a gate has
passed.

Recommended defaults are not approvals. Every D01-D15 row remains HUMAN DECISION
REQUIRED until its human owner records a choice in call notes or Slack and that
choice is transferred into the new dated REAP preregistration and its frozen
manifests. No confirmatory outcome exists to inform these choices.

## Safety snapshot

These counters describe REAP as of this packet's date:

```text
CONFIRMATORY_CALLS=0
PAID_STUDY_GENERATION_CALLS=0
SMOKE_CALLS=0
PROVIDER_PROBE_CALLS=0
DEEPSEEK_DEVELOPMENT_CALLS=0
```

No number, recommendation, or approval in this packet authorizes a call. Connor is
the only person who may initiate a paid call, and all smoke and confirmatory calls
remain blocked by the gates below.

Protected-path statement: this packet does not edit or authorize edits to
`PREREGISTRATION*.md`, `confirmatory_artifacts/**`, `observational/pipeline.py`,
`reap/status/`, or `reap/CODEX_BRIEFING.md`. A new dated REAP preregistration must
preserve the frozen Phase-I record.

## How to read the evidence

- **VERIFIED** means a first-party provider page was retrieved and supports the
  narrow route, context, parameter, or price statement. It does not establish
  observed runtime semantics, account access, billing correctness, or route
  availability for this project.
- **REPO FACT** means the statement is directly visible in the current repository's
  documents, tests, or merged code.
- **INFERENCE** means the statement follows from identified facts but is not itself
  an observed provider result.
- **RECOMMENDATION** is a conservative proposed choice. It remains undecided until
  the named human owner approves it.

Retrieval date for all route facts: 2026-08-08. Provider catalogs and prices are
mutable planning inputs, not permanent facts. They must be snapshotted again into
the frozen route and budget manifests and rechecked without a generation before
execution.

## Audit synthesis

### Audit 1: preregistration completeness and sequencing

- **REPO FACT:** `reap/06_PREREG_V2_SKELETON.md` is not freeze-ready. It leaves the
  calibration metric and tolerance, H5 method, variance model, arms, sample sizes,
  effort anchors, caps, datasets, sampling policy, grader hash, bootstrap seed, and
  ceilings unresolved.
- **REPO FACT:** the skeleton says smoke facts must be attached before main blocks,
  while `reap/08_HYPERPARAMETER_DECISIONS.md` says four smoke facts must be settled
  before preregistration freeze. In contrast, `reap/10_PHASE_GATE_PLAN_2026-08-08.md`
  orders scientific freeze, runner construction, then human smoke.
- **INFERENCE:** freezing after smoke could expose the design to outcome-informed
  choices, but freezing a route unconditionally before its semantics are known could
  authorize an unsafe route. That is the sequencing contradiction.
- **RECOMMENDATION:** freeze scientific design and exact fail-closed activation
  criteria first; build and independently review the runner second; human smoke
  occurs only after the runner; then permit activation or omission of each frozen
  route. A smoke failure means **NO SUBSTITUTION**, no cap change, no effort change,
  no reduced sample, and no replacement provider after seeing response content.

### Audit 2: merged analysis and schedule capabilities

- **REPO FACT:** analysis rows have no arm identity. Feeding A, B, and C together
  under one panel/model/route would silently treat them as one effort-by-cap grid.
- **REPO FACT:** `src/effort_atlas/confirmatory.py` currently refuses
  `replicates != 1` and requires exactly two efforts and two caps. It cannot export
  the proposed replicated A/B/C schedules.
- **REPO FACT:** the implemented cap transition is item-level empirical-marginal
  expected mass. It uses the outer product of small-cap and large-cap item accuracy
  marginals, not replicate-index pairing and not observed trace continuation.
- **REPO FACT:** the implemented rescue summary is item-level independent-draw
  rescue evidence: an item has at least one smaller-cap unanswered length stop and
  at least one independently drawn larger-cap normal correct response.
- **REPO FACT:** method-of-moments variance components are descriptive. The merged
  code does not implement a hierarchical inferential model.
- **REPO FACT:** KS on common support and absolute truncation-rate error are
  implemented. H6 tolerance is not implemented, and H5 monotonicity is not
  implemented.
- **REPO FACT:** every valid large-cap completion length is included in the empirical
  calibration reference. Any reference-cap length stops remain censored floors;
  they are not completed latent lengths and the arm must be called a large-cap
  reference, not uncapped.

### Audit 3: route feasibility and budgets

- **VERIFIED:** Tinker's official catalog lists `openai/gpt-oss-120b` as a
  32K-context route at $0.84 per million sampled tokens. The 128K PEFT route is a
  distinct `openai/gpt-oss-120b:peft:131072` route at $1.94 per million sampled
  tokens. The standard GPT-OSS-120B route is 32K context; the 128K PEFT route is a
  distinct, higher-priced route, not a free extension of the standard route.
  [Tinker models and pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
- **VERIFIED:** the same Tinker catalog lists `thinkingmachines/Inkling` as a
  64K-context route at the then-current $4.68 per million sampled-token promotional
  price. The Inkling standard route is 64K context, so a literal 64K output
  allowance plus a prompt is unsafe. The 256K route is distinct and higher-priced.
  [Tinker models and pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
- **VERIFIED:** OpenAI's official model page lists `gpt-5.6-terra`, the Responses API,
  a 1,050,000-token context window, a 128,000-token maximum output, and the
  then-current $2/$12 per-million input/output prices. These facts do not settle the
  project's usage-accounting concern. [GPT-5.6 Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- **VERIFIED:** Fireworks' official model page lists the exact model path
  `accounts/fireworks/models/deepseek-v4-flash`, serverless availability, and the
  then-current $0.14/$0.28 per-million input/output prices. This does not verify ZDR,
  the intended account configuration, or any brokered route.
  [Fireworks DeepSeek V4 Flash](https://fireworks.ai/models/fireworks/deepseek-v4-flash)
- **INFERENCE:** at current official Tinker rates and total-context limits, the
  existing 90-item worst-case grid exceeds the $2,000 Tinker ceiling once every
  scheduled row is bounded at its requested cap rather than by an expected-length
  estimate. The ceiling therefore cannot be justified by the existing approximate
  $1,030 expectation.
- **INFERENCE:** at the repository's planning rate and design, P3 n=28 exceeds the
  approximately $200 OpenAI pool. The claim that it fits depends on an invalid or
  incomplete generation-count calculation.
- **REPO FACT:** the DeepSeek V4 Flash development lane is disabled. The exact
  OpenRouter+Fireworks route still requires verification, as do ZDR, provider
  identity, fallback behavior, and account-level spending controls.
- **REPO FACT:** the pinned Tinker SDK 0.25.0 path is known to resubmit. Human
  Tinker smoke therefore remains blocked until the runner can guarantee one and
  only one billed submission; a scheduled smoke date is not enough.
- **RECOMMENDATION:** if humans enable that development-only lane, isolate it from
  research data and keys, pin the exact served route with fallbacks disabled, and
  impose a cumulative hard ceiling of $10. This requires explicit human approval and
  committed configuration; it supplies no scientific or financial verification.

## Recommended sequencing resolution

The contradiction is resolved by separating a **scientific freeze** from a
**predeclared operational activation**:

1. Connor and Chirag decide D01-D15 without confirmatory responses.
2. Freeze the question, datasets, item lists, arms, identities, routes, caps,
   efforts, sample sizes, prompts, seeds, schedules, estimands, tests, tolerances,
   omission rules, and per-pool ceilings. Route activation criteria must be exact
   and binary.
3. Implement and adversarially review the runner and executable budget gates against
   those frozen artifacts. No call occurs in this step.
4. Connor human-runs the frozen smoke schedule. Smoke evidence is operational and
   excluded from confirmatory estimates.
5. Apply the frozen predicate only. Passing routes activate unchanged; failing or
   indeterminate routes are omitted unchanged. The only allowed post-smoke action is
   activation or omission. **NO SUBSTITUTION** applies.
6. Human-open the confirmatory gate only when every activated route, schedule,
   manifest, budget, and analysis hash matches the frozen record.

This makes smoke informative about whether a route may run, not about what study to
run.

## Numbered decision matrix

The defaults below are intentionally conservative and concrete enough to implement.
They are proposals, not decisions. “Freeze blocker” states what cannot be frozen or
built safely until the human owner acts.

| ID | Decision and options | Recommended conservative default | Human owner | Status / freeze blocker | Implementation consequence |
|---|---|---|---|---|---|
| D01 | **Freeze versus smoke sequencing.** A: smoke then design freeze; B: unconditional design freeze then smoke; C: scientific freeze plus predeclared activation predicate, then runner, then smoke. | C. A route may only activate unchanged or be omitted; NO SUBSTITUTION. | both | HUMAN DECISION REQUIRED; preregistration order and route gates cannot freeze. | Split scientific manifests from a smoke evidence appendix; runner evaluates a frozen pass/fail predicate. |
| D02 | **Arm architecture and identity.** A: one nested grid with reused rows; B: independently sampled A/B/C arms; C: hybrid reuse with prespecified covariance. | B, with mandatory `arm_key` in schedule, job ID, cache key, ledger row, analysis identity, and report. No row is reused across arms. | both | HUMAN DECISION REQUIRED; current rows lack arm identity and otherwise mix A/B/C. | Version schedule and analysis schemas; reject absent/unknown arm keys and cross-arm pooling. |
| D03 | **Dataset first-pass scope.** A: all 90 math items; B: 60 HMMT 2025+2026 items on Tinker and the overlapping 30 HMMT-2026 items on P3; C: add AIME, GPQA, HARP, or GSM8K now. | B. Hold AIME, GPQA, HARP, and GSM8K for a dated later scope decision; do not spend reserve on them in the first pass. | both | HUMAN DECISION REQUIRED; item count drives power, licensing, schedule hashes, and worst-case exposure. | Freeze exact item IDs, revisions, licenses, golds, and hashes per panel; budget from scheduled rows. |
| D04 | **P1 Inkling/Tinker exact design.** Options: standard 64K route or distinct 256K route; discrete presets or denser continuous effort; retain or reduce proposed n. | Standard `thinkingmachines/Inkling`; A: efforts 0.7/0.99, caps 4096/16384, n=20; B: efforts 0.1/0.4/0.7/0.99, caps 2048/4096/8192/16384/32768, n=8; C: same four efforts, 49152 large-cap reference, n=8. Freeze prompt+overhead ceiling at 8192 and fail if total context could exceed 65536. | Chirag | HUMAN DECISION REQUIRED; effort grid, n, reference label, and finite context bound are unset. | Route manifest pins standard ID; schedule exporter handles three arm shapes; runtime refuses total-context overflow. |
| D05 | **P2 GPT-OSS-120B/Tinker exact design.** Options: standard 32K route with smaller grid, or distinct 128K PEFT route and new costs; choose discrete renderer levels and n. | Standard `openai/gpt-oss-120b`; A: low/high, caps 4096/16384, n=20; B: no-sysprompt/low/medium/high, caps 2048/4096/8192/12288/16384, n=8; C: same four efforts, 20000 large-cap reference, n=8. Freeze prompt+overhead ceiling at 8192 and fail above 32768 total context. | Chirag | HUMAN DECISION REQUIRED; the proposed 32K output and 64K reference do not fit the standard route. | Exclude 32768/65536 output caps; choosing PEFT instead creates a separately pinned route, budget, and cross-route interpretation. |
| D06 | **P3 gpt-5.6-terra/OpenAI exact design.** Options: omit; 30- or 60-item anchor; n from a fresh worst-case calculation; effort pair and caps. | Responses API, exact `gpt-5.6-terra`; HMMT-2026 30-item anchor only; medium/xhigh; caps 4096/16384; n=8 per item/cell; prompt bound 4096 tokens; five-call accounting smoke charged inside the same $200 ceiling. | both | HUMAN DECISION REQUIRED; P3 n=28 does not fit and usage accounting remains unverified. | Export a P3-only A schedule; runner requires explicit `max_output_tokens` and `reasoning.effort`, captures incomplete reason and usage, and omits P3 if accounting fails. |
| D07 | **Transition and rescue estimands/terms.** A: pretend replicate-index pairing; B: freeze current item-marginal summaries; C: add a different model before freeze. | B. Name outputs “independent-draw expected transition mass” and “item-level independent-draw rescue evidence”; never call either an observed continuation or a rescued trace. | Chirag | HUMAN DECISION REQUIRED; scientific interpretation and reporting names are not frozen. | Keep the merged outer-product sufficient-statistic implementation; update schemas and prose to reject continuation language. |
| D08 | **Replicate variance analysis.** A: descriptive method of moments only; B: prespecified hierarchical binomial model; C: both with a primary/secondary order. | C: item-clustered bootstrap remains primary; current method-of-moments components are descriptive; a fully specified hierarchical model may be secondary only if implemented, simulation-tested, and frozen before data. | Chirag | HUMAN DECISION REQUIRED; the skeleton promises a model that does not exist. | Either relabel existing MoM output only or add a separately tested hierarchical estimator without changing primary endpoints. |
| D09 | **Calibration metric and H6.** Options: KS only; absolute error only; both; choose aggregation and tolerance. | Absolute truncation-rate error is the H6 decision metric: require error no greater than 0.10 in every evaluable prespecified effort×cap cell; report maximum and mean absolute error. KS on common support is a descriptive distribution diagnostic. A cell with missing reference/observed data is non-evaluable, not a pass. | Chirag | HUMAN DECISION REQUIRED; H6 tolerance is not implemented and the skeleton has no pass rule. | Add a tolerance evaluator and edge-case tests; preserve raw predicted/observed rates, signed error, absolute error, KS, denominators, and reference-stop count. |
| D10 | **H5 monotonicity.** A: formal ordered hypothesis with a named test; B: prespecified descriptive pattern; C: remove H5. | B for the first pass: report every adjacent violation and endpoint direction with no p-value or “supported” label. Promote to a test only after Chirag specifies multiplicity, missingness, statistic, and null randomization before freeze. | Chirag | HUMAN DECISION REQUIRED; H5 monotonicity is not implemented. | Descriptive checker is required; a formal choice additionally requires code, simulation fixtures, and multiplicity language. |
| D11 | **Prompt, effort delivery, and grader freeze.** Options: shared math prompt or panel-specific prompts; strict-only or add secondary MCQ extraction. | One no-few-shot math template across P1/P2/P3 with the exact `Final answer: <answer>` instruction; hash exact rendered bytes and grader-v2 commit; strict terminator extraction only for first-pass math. Tinker effort is renderer/API-delivered, never hand-written into the prompt. | Connor | HUMAN DECISION REQUIRED; exact prompt bytes, renderer versions, stop strings, and hashes are absent. | Add prompt and renderer manifests; runner refuses hash drift; no fallback extraction. |
| D12 | **Seeds, replicates, schedule, and batching.** Options: one master seed or panel seeds; individual calls or Tinker `num_samples`; row order and restart policy. | Master seed 20260722; derive each request seed from SHA-256 of canonical panel/arm/item/effort/cap identity; predeclare sample indices; deterministic item-block randomization; append-only attempts; `num_samples=n` activates only if frozen independence smoke passes, otherwise omit that Tinker panel. | Connor | HUMAN DECISION REQUIRED; current exporter is 2x2 with one replicate and cannot represent A/B/C. | Build schedule schema v2, arm-aware job IDs, n>1 exporter, manifest hashes, deterministic restart, and zero generation retries. |
| D13 | **Ceilings and accounting.** Options: reduce scope/n or raise written ceilings; choose panel subceilings and reconciliation cadence. | Keep the first-pass Tinker hard ceiling at $2,000: P1 $1,650, P2 $250, all Tinker smoke/probes $100; OpenAI P3 including smoke $200; P0 $50; reserve inaccessible. Recalculate every subceiling from exact frozen schedules, current snapshotted prices, full prompt bounds, and cap-bounded output before freeze. | Connor | HUMAN DECISION REQUIRED; existing expected-cost notes are not executable worst-case gates. | Runner rejects any panel whose remaining worst-case exposure does not fit, polls receipts between blocks, and hard-stops at each pool ceiling. |
| D14 | **Cross-platform anchors.** Options: no shared anchor; shared dataset only; shared items, caps, and endpoint contrast where controls permit. | Use the same 30 HMMT-2026 items and 4096/16384 caps in P1 A, P2 A, and P3 A. Use each model's frozen low/high endpoint effort pair; report directional replication separately and never pool effect sizes. | both | HUMAN DECISION REQUIRED; the meaning and limits of “replication” are not frozen. | Add shared item-manifest hash and cap labels; reports show panels side by side with route-specific effort semantics. |
| D15 | **DeepSeek V4 Flash development gate.** Options: leave disabled; enable direct Fireworks; enable a verified brokered OpenRouter+Fireworks route. | Leave disabled until exact requested and served route IDs, Fireworks ZDR, fallbacks-off behavior, receipt fields, and a cumulative $10 development hard ceiling are committed and receive human confirmation. Never send secrets or research data; never use this lane for scientific or financial verification. | Connor | HUMAN DECISION REQUIRED; exact route, ZDR, and spend-control configuration remain unverified. | A separate development-only config and ledger are required; any mismatch disables the lane, and any alternate lane requires a new human decision. |

## Why these defaults are conservative

- Separate arm sampling costs more than row reuse but prevents accidental double use
  and keeps the arm-specific estimands auditable.
- The 60-item Tinker scope retains both HMMT years while removing extensions that
  would otherwise consume the first-pass ceiling. P3 uses only the 30-item shared
  anchor because its pool is much smaller.
- P1's 49,152 reference leaves room inside the 64K standard route for the frozen
  prompt and overhead bound. P2's 20,000 reference leaves room inside its 32K
  standard route. Neither is described as uncapped.
- P3 n=8 and the 4K/16K grid preserve replication and a shared cap contrast while
  leaving a finite margin for its accounting smoke. The executable preflight, not
  this prose estimate, decides whether the schedule fits.
- H5 stays descriptive because no ordered test is implemented. H6 gets a proposed
  falsifiable tolerance, while KS remains available as a diagnostic rather than
  being misrepresented as a rate-error threshold.

## Auditable schedule and cost derivation

This table expands the D03-D06 recommended defaults. Each output bound charges every
generation at its requested cap. Each prompt bound charges the full per-generation
prompt allowance even though verified batching could later share prefill. Formulas
use multiplication before addition; commas in displayed integers are separators.

| Panel | Arm | Items | Efforts | Caps | n | Prompt bound | Generation/output formulas | Generations | Prompt token bound | Output token bound |
|---|---|---:|---:|---|---:|---:|---|---:|---:|---:|
| P1 | A | 60 | 2 | 4096,16384 | 20 | 8192 | `g=60*2*2*20; out=60*2*20*(4096+16384)` | 4,800 | 39,321,600 | 49,152,000 |
| P1 | B | 60 | 4 | 2048,4096,8192,16384,32768 | 8 | 8192 | `g=60*4*5*8; out=60*4*8*(2048+4096+8192+16384+32768)` | 9,600 | 78,643,200 | 121,896,960 |
| P1 | C | 60 | 4 | 49152 | 8 | 8192 | `g=60*4*1*8; out=60*4*8*49152` | 1,920 | 15,728,640 | 94,371,840 |
| P2 | A | 60 | 2 | 4096,16384 | 20 | 8192 | `g=60*2*2*20; out=60*2*20*(4096+16384)` | 4,800 | 39,321,600 | 49,152,000 |
| P2 | B | 60 | 4 | 2048,4096,8192,12288,16384 | 8 | 8192 | `g=60*4*5*8; out=60*4*8*(2048+4096+8192+12288+16384)` | 9,600 | 78,643,200 | 82,575,360 |
| P2 | C | 60 | 4 | 20000 | 8 | 8192 | `g=60*4*1*8; out=60*4*8*20000` | 1,920 | 15,728,640 | 38,400,000 |
| P3 | A | 30 | 2 | 4096,16384 | 8 | 4096 | `g=30*2*2*8; out=30*2*8*(4096+16384)` | 960 | 3,932,160 | 9,830,400 |

Rates are USD per million tokens as retrieved on 2026-08-08. Tinker uses
prefill/sample rates; OpenAI P3 uses input/output rates in the same two columns.

| Panel | Total generations | Prompt token bound | Output token bound | Prefill/input rate | Sample/output rate | Exact cost formula | Total | Stage |
|---|---:|---:|---:|---:|---:|---|---:|---|
| P1 | 16,320 | 133,693,440 | 265,420,800 | 1.87 | 4.68 | `((133693440*1.87)+(265420800*4.68))/1000000` | $1,492.1761 | before smoke |
| P2 | 16,320 | 133,693,440 | 170,127,360 | 0.33 | 0.84 | `((133693440*0.33)+(170127360*0.84))/1000000` | $187.0258 | before smoke |
| P3 | 960 | 3,932,160 | 9,830,400 | 2 | 12 | `((3932160*2)+(9830400*12))/1000000` | $125.8291 | before smoke |

The exact totals are **INFERENCES**, not executable authority. They must be
reproduced from frozen schedule rows. The Tinker figures remain unusable for paid
activation until exact-route cap/billing semantics and one-submission behavior pass
the frozen smoke gate. P3's total is before its five-call smoke, which must fit
inside the same $200 pool.

## Proposed exact first-pass prompt

This is the **RECOMMENDATION** for D11. The selected text must be stored as exact
UTF-8 bytes and hashed; `problem_text` is the only render variable.

```text
Solve the following problem. Show your reasoning, then end with exactly one line in
the form "Final answer: <answer>". Do not write anything after that line.

Problem:
{{ problem_text }}
```

No few-shot examples, provider-specific effort instructions, or fallback answer
formats are added. If a route requires wrapper tokens or a renderer, those exact
bytes and versions belong in the prompt/renderer manifest and count against the
panel's frozen prompt bound.

## Frozen activation predicates to write after decisions

Each route predicate must be executable and return only `activate`, `omit`, or
`indeterminate`; `indeterminate` is treated as `omit`.

At minimum, activation requires all of the following on the exact frozen smoke
schedule:

1. requested model, account, endpoint, renderer, and served route match the frozen
   manifest;
2. no fallback and no automatic generation retry occurred;
3. every attempt is in the append-only ledger, including errors;
4. explicit cap and effort were accepted and echoed or otherwise verifiably applied;
5. termination reason and native token usage were captured at collection time;
6. native billed output did not exceed the frozen finite upper bound;
7. provider usage, receipts, and account spend reconcile within a frozen monetary
   tolerance;
8. Tinker `num_samples` meets the frozen independence diagnostic if batching is part
   of the design;
9. cumulative worst-case remaining exposure fits below the pool and panel ceilings;
10. prompt, grader, schedule, route, dataset, and analysis hashes match exactly.

Failure of any predicate causes omission of that entire frozen panel. **NO SUBSTITUTION**
means the project must not lower n, change a cap, replace a provider, switch standard
and PEFT routes, or use a different effort pair after inspecting smoke response
content.

## Required artifacts and code after decisions

The following work starts only after the relevant human choices are recorded:

1. **New dated REAP preregistration:** complete hypotheses, arms, route activation
   and omission rules, estimands, H5/H6 status, missingness, multiplicity, ceilings,
   and amendment rule. Preserve all Phase-I frozen files.
2. **Dataset/item manifest:** exact source revisions, licenses, item IDs, gold-answer
   hashes, first-pass membership, and the shared HMMT-2026 anchor hash.
3. **Prompt/renderer/grader manifest:** exact bytes and SHA-256 hashes, terminator
   contract, renderer versions, effort encodings, stop sequences, and accepted
   grader/analysis commits.
4. **Route and price manifest:** exact API, model and served-route IDs, standard
   versus PEFT status, context and prompt bounds, supported caps/efforts, retrieved
   official pages, retrieval timestamp, and snapshotted rates.
5. **Schedule schema and exporter v2:** `arm_key`, n>1, distinct arm sampling,
   canonical identities, per-request seeds, item-block randomization, smoke phase,
   deterministic restart, and manifest mismatch refusal. Replace neither the old
   frozen schedule nor Phase-I history.
6. **Analysis acceptance update:** require arm filtering/identity; freeze transition
   and rescue names; label MoM descriptive; add the selected H5 checker/test and H6
   tolerance evaluator; preserve reference-stop floors and all denominators.
7. **Executable budget model:** compute prompt plus cap-bounded output exposure from
   every scheduled row at snapshotted prices; include smoke inside ceilings; unit-test
   exact-boundary stops and receipt races.
8. **Runner:** default dry-run, explicit cap and effort, provider pinning, fallbacks
   disabled, required parameters, zero billed-generation retries, arm-aware cache
   keys, append-only ledger, receipt reconciliation, and hard panel/pool kills.
9. **Human smoke packet:** frozen schedule, least-cost ordering, predicted maximum
   spend, collection fields, activation predicate output, signed human execution
   record, and dated evidence appendix. Smoke rows remain non-confirmatory.
10. **Independent review evidence:** recompute all schedule counts and worst-case
    costs, mutation-test arm mixing and gates, verify hashes, and confirm zero
    provider calls occurred during offline verification.

After a true Phase 3 checkpoint, the integration owner may separately update the
canonical briefing and generated status artifacts together. This packet deliberately
does not do so.

## Copyable approval form

Copy this block into Slack or call notes. Replace `PENDING` only with an explicit
human choice; retain rejected options and rationale. A message that does not cover
all D01-D15 entries is not full Phase 3 approval.

```text
REAP PHASE 3 DECISION RECORD
Decision meeting date: PENDING
Attendees: PENDING
Evidence cutoff: 2026-08-08
Confirmatory responses available when deciding: 0

D01 sequencing | owner both | choice: PENDING | rationale: PENDING
D02 arm architecture/arm_key | owner both | choice: PENDING | rationale: PENDING
D03 first-pass datasets | owner both | choice: PENDING | rationale: PENDING
D04 P1 route/efforts/caps/n | owner Chirag | choice: PENDING | rationale: PENDING
D05 P2 route/efforts/caps/n | owner Chirag | choice: PENDING | rationale: PENDING
D06 P3 route/efforts/caps/n | owner both | choice: PENDING | rationale: PENDING
D07 transition/rescue estimands and names | owner Chirag | choice: PENDING | rationale: PENDING
D08 MoM/hierarchical variance plan | owner Chirag | choice: PENDING | rationale: PENDING
D09 KS/absolute error/H6 tolerance | owner Chirag | choice: PENDING | rationale: PENDING
D10 H5 descriptive or formal test | owner Chirag | choice: PENDING | rationale: PENDING
D11 prompt/renderer/grader freeze | owner Connor | choice: PENDING | rationale: PENDING
D12 seeds/replicates/schedule/batching | owner Connor | choice: PENDING | rationale: PENDING
D13 ceilings/accounting | owner Connor | choice: PENDING | rationale: PENDING
D14 cross-platform anchors | owner both | choice: PENDING | rationale: PENDING
D15 DeepSeek development gate | owner Connor | choice: PENDING | rationale: PENDING

Explicit confirmations:
- Recommended defaults were treated as proposals, not prior decisions: PENDING
- Exact activation predicates freeze before smoke: PENDING
- Human smoke occurs only after runner review: PENDING
- Smoke failure action is whole-panel omission with NO SUBSTITUTION: PENDING
- Tinker first-pass hard ceiling and subceilings selected: PENDING
- OpenAI ceiling includes all P3 smoke and confirmatory rows: PENDING
- Phase-I frozen artifacts remain untouched: PENDING
- New dated REAP preregistration may now be drafted: PENDING

Connor sign-off and timestamp: PENDING
Chirag sign-off and timestamp: PENDING
```

This packet is advisory only. It does not authorize drafting, offline implementation, smoke, confirmatory collection, a paid provider probe, or spending.
