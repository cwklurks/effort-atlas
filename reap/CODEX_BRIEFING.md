# Codex briefing — effort-atlas / REAP

Point any new Codex session at this file first: **"Read reap/CODEX_BRIEFING.md and report what you understand the project state to be before doing anything."** A session that can't summarize the state correctly should not be given a task.

---

## 1. Read these, in this order

| # | File | Why |
|---|---|---|
| 1 | `AGENTS.md` (repo root) | The laws. Frozen files, no paid study calls, explicit max_tokens, no fallback extraction. |
| 2 | `reap/README.md` | Program charter and governance. |
| 3 | `reap/claude_project/PROJECT_BRIEF.md` | Canonical state: people, history, funding, positioning. |
| 4 | `reap/01_EXPERIMENT_OUTLINE_v2.md` | The experiment design under review by the supervisor. |
| 5 | `reap/08_HYPERPARAMETER_DECISIONS.md` | Every knob, its verified facts, what's UNVERIFIED and must be probed. |
| 6 | `reap/11_PHASE3_DECISION_PACKET_2026-08-08.md` | Independently reviewed Phase-3 recommendations and D01-D15 approval form. Every choice is advisory and human-pending. |
| 7 | `reap/12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md` | Non-frozen record of Connor's current positions, every alternative, current dataset/model research, and the questions still open for Chirag. It authorizes no call. |
| 8 | `reap/13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md` + `reap/prompts/PHASE3_EXTERNAL_REVIEW_PROMPT_2026-08-10.md` | Non-frozen opinionated proposal and self-contained prompt for Connor's separate-model review. They expose the symbolic-grader and current route blockers and authorize no call. |
| 9 | `reap/14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md` + `reap/prompts/PHASE3_ADVERSARIAL_LOOP_OBJECTIVE_2026-08-10.md` | Preserved external review plus the C01-C07 objective used by the completed bounded Claude/Codex development relay. The relay is non-authoritative and does not close human decisions. |
| 10 | `reap/15_PHASE3_ADVERSARIAL_SYNTHESIS_2026-08-10.md` | Current non-frozen synthesis: model roles, planning prices, dataset recommendation, D01-D15 working answers, implemented safeguards, and remaining human decisions. It authorizes no call or freeze. |
| 11 | `PREREGISTRATION.md` + `PREREGISTRATION_AMENDMENT_2026-07-22.md` | **FROZEN. Never edit.** Read to understand what is already committed. |
| 12 | `reap/REVIEW_PR1_ECOSYSTEM_AUDIT.md` | Red-team review of PR #1 and its 8 blocking fixes. |
| 13 | `observational/RESULTS.md` + `observational/pipeline.py` + `observational/INPUT_PROVENANCE.md` | The free observational study (done, verified). Pipeline is pinned — agents run it, never rewrite its statistics. Input acquisition is not yet clean-checkout reproducible. |
| 14 | `src/effort_atlas/` + `tests/` | Existing code. `confirmatory.py`, strict grader v2, and the independently approved pre-data analysis layer are merged. Phase 3 methodology and preregistration are now the active gate. |
| 15 | `reap/18_POST_MEETING_BENCHMARK_AUDIT_2026-08-18.md` through `reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md` | Post-meeting research question, cross-model method review, model-pair eligibility rules, and the exact public-source capability audit. The self-contained plain-language view is `reap/next_chapter/index.html`. |

## 2. Project state, in one screen

**The paper:** output-token walls truncate reasoning responses before a final answer exists; graders score deletions as wrong; higher effort writes longer and hits walls more — so a wall can masquerade as "thinking makes models worse." Two halves: censored-length analysis (supervisor's) + effort×allowance interventions (ours). Merged paper, Connor first author.

**What exists and works:** the frozen Phase-I preregistration + one dated amendment ($0 confirmatory spend, ever); the offline confirmatory preflight (hash-chained AttemptLedger, seeded/hashed schedules, receipt reconciliation); the cap-semantics and observational studies; and independently reviewed Phase-1 implementations for the ecosystem audit, strict grader v2, and fail-closed Tinker probe. Grader v2 reproducibly identifies all 78 archived 4,096-token rows as unanswered with no raw response text committed. The ecosystem audit's real-only table, uniform control gate, receipts, and synthetic separation are independently recomputed. The Tinker probe's dry-run plan is safe, but pinned SDK 0.25.0 is proven to resubmit and its live path therefore blocks before client construction.

**What is integrated and independently approved:** the Phase-2 grader + analysis baseline is merged. It preserves strict terminator-only grading, replaces replicate-index transition pairing with item-level sufficient statistics and independent-draw expected mass, includes every valid large-cap completion length in cap-calibration references, validates rescue rows through grader v2, and requires separate ordinary and exact-lock Tinker verification environments. Initial review blockers were remediated and the final adversarial re-review passed.

**What does NOT exist yet:** a paid runner; executable budget gates; a frozen REAP preregistration; or settled live Tinker/OpenAI smoke facts. Nothing confirmatory can run until those gates close. No current Tinker SDK path satisfies the zero-resubmission rule, so human smoke is blocked rather than merely unscheduled.

**Current Phase-3 checkpoint:** the advisory packet at
`reap/11_PHASE3_DECISION_PACKET_2026-08-08.md` passed independent review at
`2b9b161`, including independent cost recomputation and 19/19 killed contract
mutations. Connor's 2026-08-10 positions and the researched alternatives are in the
non-frozen `reap/12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md`. He accepts the
scientific-freeze-then-smoke sequence, separate arms, standard 32K GPT-OSS,
descriptive-first D07/D08/D10 choices, and a planned shared 30-of-33 HMMT-2026
subset. Dataset scope,
Inkling scope, Terra/model roster, H6, prompt, batching, Tinker portfolio, and the
DeepSeek gate remain open or conditional. The worksheet authorizes no call.

The integrated recommendation at
`reap/13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md` proposes a balanced
Inkling/GPT-OSS/Nemotron/Qwen/Terra portfolio and a conditional same-model
OpenRouter anchor for Connor to challenge with an outside model. Its companion
prompt is self-contained. The proposal also corrects an important dataset
assumption: the 33-row HMMT-2026 source contains symbolic fractions and radicals,
so the planned 30-item core cannot freeze until a pinned upstream MathArena scorer
and the exact source-defined selection rule pass. No recommendation is an approval.

The external response is preserved at
`reap/14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md`. A bounded Claude/Codex relay at
`scripts/adversarial_review_loop.py`, with the objective in
`reap/prompts/PHASE3_ADVERSARIAL_LOOP_OBJECTIVE_2026-08-10.md`, completed a
two-round challenge. This completed development relay ran between
`claude-fable-5` on eligible regular-plan
usage and Sol XHigh. It operated on a tracked-file snapshot, preserved every
prompt and response, and used zero relay-level subprocess retries. API and gateway
billing variables were rejected; Connor confirmed usage credits and automatic
model switching were disabled. The completed run predated the final clean-session
and Codex user-configuration isolation hardening, and internal CLI request counts
remain unverified. It is therefore non-authoritative and not freeze-eligible. The
current synthesis is in `reap/15_PHASE3_ADVERSARIAL_SYNTHESIS_2026-08-10.md`.
The current checkpoint is 273 ordinary tests plus 26 exact-lock Tinker tests. The
decision-independent implementation passed final adversarial review at `f9aef0b`
with no critical or warning findings. All study-call and spend counters remain
zero. Model agreement cannot authorize spending, provider activation,
preregistration freeze, or choices owned by Connor or Chirag.

Decision-independent Phase-3 safeguards now exist offline for arm- and phase-aware
schedules, sealed manifests, manifest-bound activation, strict list-rate planning
budget arithmetic,
the deterministic symbolic-scoring boundary, simulation provenance, and dataset
provenance. The executable budget gate is still a Phase-4 runner deliverable because
the current planning rows and rates are not exact-byte-bound freeze authority.
These safeguards remain non-frozen prerequisites; they are not a runner and
authorize no execution.

**Post-meeting benchmark checkpoint (2026-08-19):** Connor and Chirag reframed the
comparison around matched performance and token efficiency on the same questions,
with the effort-by-allowance intervention still needed to identify censoring. A
pinned public-source audit now covers MathArena HMMT 2025/2026 and HELM GPQA. It
verifies 20 exact source files and materializes 4,248 sanitized
benchmark-model-question cells without exporting GPQA content. HMMT-2026 item 25
has a text-version mismatch affecting 106 attempts from 28 models, Qwen3.5-4B has
11 explicit missing HMMT-2026 cells, and HELM's 446 evaluated GPQA rows are a
deliberate test split from 448 source rows. Only HELM Gemini publishes complete
termination labels here (42 length, 404 stop), while its token field is all zero;
the HELM provider token fields are not one comparable unit. These findings narrow
the design but do not freeze a dataset, model roster, or analysis and authorize no
call.

**Funding:** $5,000 Tinker credits + ~$200 OpenAI (supervisor) + <$100 OpenRouter. Platform-scoped pools, never mixed. Cost model and gates in `reap/02_BUDGET_AND_COSTS.md`.

**Development model routing:** a direct Fireworks ZDR DeepSeek V4 Flash lane is
proposed for bounded mechanical development work only. It remains disabled and not
authorized until Connor approves the exact configuration, `store=False`/Chat
Completions behavior, served-route/fallback assertions, separate ledger, and a $10
cumulative ceiling. It never receives research data or supplies scientific or
financial verification.

**Corrected route and budget bounds:** standard Tinker GPT-OSS-120B has a 32K
context; its 128K PEFT route is distinct and more expensive. Standard Inkling has a
64K context, so 64K cannot be treated as an output allowance on a nonempty prompt.
The earlier 90-item Tinker and n=28 OpenAI plans are expected-cost sketches, not
safe worst-case ceilings. The reviewed packet's original pre-smoke maxima include
$1,492.1761 for 60-item Inkling P1 and $125.8291 for 30-item Terra P3. The current
20,480-token GPT-OSS planning shape is $187.8000 at its captured list rates.
Official OpenAI pages retrieved 2026-08-10 list Luna at $0.20/$0.02/$1.20 and
Terra at $2.00/$0.20/$12.00 per 1M input/cached/output tokens. At the declared
30-item maximum-token shape, Luna is $12.582912 and Terra is $125.829120, or
$138.412032 together before smoke. These are mutable planning facts, not price
guarantees or route activation. Connor has reopened the Inkling scope and Tinker allocation;
the worksheet compares a 30-item Inkling design, GPT-OSS, Qwen, and Nemotron
portfolio options. Every value remains planning-only until approval and a frozen
schedule/price/route manifest.

**Branch / PR state as of 2026-08-19:**

| Work | State | Blocking issue |
|---|---|---|
| Phase 0 — `codex/reap-governance`, PR #4 | merged to main; generated status dashboard and canonical verifier | complete |
| A — `codex/ecosystem-audit`, PR #1 | merged at accepted `303263e` implementation | headline limitations remain mandatory reporting context |
| B — `codex/grader-v2`, PR #2 | merged at accepted `9a54f17`; 78-row archive verifier passes | integrated with D without weakening extraction semantics |
| C — `codex/tinker-probe`, PR #5 | merged at accepted `3331dc1`; dry-run safe | live intentionally blocked because Tinker 0.25.0 cannot guarantee one submission; no empirical fact is settled |
| D — `codex/analysis-layer`, PR #3 | independently approved after remediation and merged at `7c83085` | complete; Phase 3 methodology decisions are now active |
| E — `codex/runner` | not implemented | waits on accepted grader interfaces, frozen design inputs, and corrected budget math |
| Phase 3 — `codex/prereg-v2`, draft PR #6 | external review, completed non-authoritative development relay, current synthesis, and offline safeguards preserved | D03/D04/D06/D09/D11/D12/D13/D15 and Chirag scientific signoff remain open; no call authorized |
| Post-meeting benchmark provenance — `codex/benchmark-provenance-linux` | exact-source audit and sanitized capability table are independently approved; plain-language HTML and verified Linux handoff are complete | publish the reviewed branch, then clone and re-verify it on Linux; no call authorized |

The current phase-gate and model-routing plan is in
`reap/10_PHASE_GATE_PLAN_2026-08-08.md`; the current human decision surface is
`reap/11_PHASE3_DECISION_PACKET_2026-08-08.md`, with Connor's current non-frozen
working record in `reap/12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md`.

## 3. The laws (repeated because they are load-bearing)

1. **Never edit frozen artifacts:** `PREREGISTRATION*.md`, `confirmatory_artifacts/**`, anything headed FROZEN, `observational/pipeline.py` statistics logic. Propose changes as new dated files.
2. **Never make paid study-generation, smoke, or provider-probe calls.** Every script defaults to `--dry-run`; live execution is human-initiated. Secrets from env vars only; fail loudly if unset. The proposed Fireworks ZDR development lane remains disabled until Connor approves and commits its route configuration and hard dollar ceiling. The distinct Kimi path remains user-triggered only under `AGENTS.md`.
3. **Explicit `max_tokens` on every request template.** This project exists because an endpoint silently defaulted to 4096.
4. **No fallback answer extraction.** A "last number anywhere" fallback already corrupted a study here.
5. **Log termination reason + token usage at collection time** on every row. It is unrecoverable afterward.
6. **Import upstream code; never reimplement it.** If an import fails, fix the environment or report `import_failed` — do not re-code the logic (this rule was violated in PR #1 and produced a wrong headline).
7. Branch + PR, checkpoint commit per unit of work, never merge. PR description states: what changed, what was verified, what was assumed.

---

## 4. Task queue

Phases 1 and 2 are merged. Current gate order: **resolve the open Connor/Chirag
decisions → freeze the scientific design and activation-or-omission rules → E
runner → human smoke under frozen ceilings → activate an unchanged panel or omit
it → confirmatory collection**. No smoke occurs merely because Connor proposed a
$2 Tinker ceiling; the one-submission runner gate still blocks it. The original task
specifications remain below as historical acceptance contracts.

Rationale: B, C, D, E are the critical path to the study being *allowed to run*; A is a parallel paper contribution whose Phase-1 half is already citable.

### Task A — ecosystem audit, round 2 (branch: `codex/ecosystem-audit`, existing PR #1)

```
Read reap/REVIEW_PR1_ECOSYSTEM_AUDIT.md. Implement the 8 blocking fixes exactly as
listed, on the same branch, checkpoint commit per fix. Rules unchanged: import
harness code (never reimplement), pin every environment, no paid calls, do not
merge. Deliver: (a) a real-data-only results table with explicit n per cell and an
insufficient_power status where n is too small; (b) a corrected control-eligibility
table computed on ONE frozen gold schema applied uniformly to every pipeline;
(c) synthetic results reported in a separate clearly-labeled table, never blended
with real; (d) a PR comment summarizing what changed per fix number, including any
fix you could not complete and why.
```

### Task B — grader v2 (branch: `codex/grader-v2`) — **highest priority**

```
Rewrite answer extraction in src/effort_atlas/graders.py as grader v2.

SPEC: A response counts as answered ONLY if it contains an explicit terminator line
matching a configurable "Final answer: <answer>" regex. Delete every fallback
(no last-number-anywhere, no first/last-$ span, no bare-boxed scavenging without a
closing brace). Emit per response: {extracted_answer_present: bool,
extracted_answer: str|None}. Grade by comparing extracted_answer to gold with the
existing numeric comparator. Termination/finish_reason is NEVER an input to
extraction or grading — it is recorded alongside, never mixed in.

TESTS (tests/test_grader_v2.py, all must pass):
- answer present, then truncation afterwards      => answered=True
- truncated mid-reasoning with stray numbers      => answered=False
- truncated mid-box "\boxed{29"                   => answered=False, no exception
- MCQ letter mid-enumeration "consider (C), which"=> answered=False
- well-formed "Final answer: 42"                  => answered=True, "42"
- correct=true with answered=false                => flagged internally inconsistent

INTEGRATION ACCEPTANCE: rerun grader v2 over the archived exploratory Tinker log in
this repo. It must report exactly 78 rows with a 4096-token finish and
extracted_answer_present=false, where the old grader reported zero parse failures.
Assert that count in an integration test.

The archived acceptance corpus is the union of
`results/sweep_real_20260719_154609.jsonl` (68 affected math rows) and
`results/sweep_real_20260719_172721.jsonl` (10 affected knowledge rows). Do not use
`results/combined_real.jsonl` for the 78-row assertion; it contains other historical
runs and has 177 rows at 4096 tokens. At assignment time, the pre-v2 baseline
command was `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 40 tests
passed, while `tests/test_rescue_analysis.py` still used an uncollected bare
function.

Both acceptance-corpus paths are currently ignored by the broad `results/` rule in
`.gitignore`. A Task B integration test must not depend on those local-only files in
a clean clone. Preserve their provenance and either commit a minimal sanitized
fixture with hashes/counts or deliberately unignore the required archives; disclose
which choice was made in the PR.

ALSO: fix tests/test_rescue_analysis.py so `unittest discover` actually collects it
(currently a bare pytest-style function, silently skipped — zero tests collected).
```

### Task C — Tinker probe + smoke script (branch: `codex/tinker-probe`)

```
Write scripts/tinker_probe.py using the tinker SDK. SamplingParams exposes
max_tokens, seed, temperature, top_p, top_k, stop; the sampling client exposes
num_samples. Everything defaults to --dry-run; --live requires TINKER_API_KEY from
env and prints a cost projection before each call.

It must settle these four UNVERIFIED facts (from reap/08_HYPERPARAMETER_DECISIONS.md)
and write them to a report file:
1. What default max_tokens applies when the parameter is OMITTED? (probe deliberately
   — this is the Phase-I bug, reproduced on purpose under controlled conditions)
2. What is the exact stop_reason vocabulary, and is a cap collision reported honestly?
3. Does num_samples>1 produce genuinely independent samples? (one item, n=8, compare
   outputs; report distinct-output count)
4. Cap semantics at the caps we will actually use (4096 / 16384 / 32768 / 65536):
   do billed/native completion tokens ever exceed the requested cap?

Cheapest model for smoke (GPT-OSS-20B); target models for cap probes: Inkling and
GPT-OSS-120B. Record per call: request params, response text hash, token usage,
stop reason, latency, timestamp — JSONL, append-only. Zero retries on any billed
call. Print a summary table at the end.

SPEC COORDINATION NOTE: the four-fact summary at the bottom of
`08_HYPERPARAMETER_DECISIONS.md` names OpenAI usage-accounting sanity as its fourth
smoke fact, while this Task C prompt names Tinker cap semantics instead. Do not
silently discard either requirement. Task C must deliver the Tinker cap probes
specified above; OpenAI accounting remains an explicit preregistration blocker
unless it is separately assigned or deliberately added to the smoke scope.
```

### Task D — analysis layer, frozen pre-data (branch: `codex/analysis-layer`)

```
Implement the preregistered analysis so it can be frozen BEFORE data exists (this
is a preregistration requirement, not a preference).

Required, per PREREGISTRATION.md "Outcomes and analysis" and the 2026-07-22
amendment:
- Wilson intervals in the confirmatory path (port from analyze.py, don't duplicate)
- item-clustered bootstrap: 10,000 resamples, seed 20260722, percentile intervals,
  for each effort slope, cap effect, and the interaction
- replicate-level variance components (REAP adds n>1 per cell; report within-item
  vs between-item variance)
- paired item-level transition tables (smaller-cap outcome × larger-cap outcome)
- answer-rescue counts per the AMENDED definitions: rewrite rescue_analysis.py,
  which currently implements the pre-amendment rule and never reads
  extracted_answer_present
- cross-cell missingness with prespecified worst-case sensitivity bounds
  (all-missing-correct / all-missing-wrong per cell)
- dose-response summaries over the effort × cap grid
- cap-invariance calibration: given a length distribution fitted at a large cap,
  predict truncation rate at each smaller cap; report predicted vs observed and a
  calibration error. (Metric choice is a supervisor decision — implement it behind a
  strategy interface with KS-on-common-support as the default, so it can be swapped
  without touching callers.)

ALSO: guard analyze.py against confirmatory rows — its dedup key omits `cap` and
would silently collapse the 2x2 into garbage. It must refuse, loudly, rather than
dedup across caps.

Tests: fixtures with known answers for every statistic; a fixed-seed bootstrap
reproducibility test; a test that the analyze.py guard actually raises.
```

### Task E — runner + executable budget gates (branch: `codex/runner`, after B merges)

```
Implement the REAP runner per reap/01_EXPERIMENT_OUTLINE_v2.md and
reap/02_BUDGET_AND_COSTS.md.

- reads a frozen schedule JSON; refuses to run on any schedule/manifest mismatch
- explicit max_tokens AND explicit effort on every call, always
- fresh cache + results directories per panel; explicit max_tokens participates in
  the cache key (a cache-replay trap exists today: max_tokens=None falls out of the
  key, so an exploratory row could replay as a confirmatory result)
- provider pinning: only=[...], allow_fallbacks=false, require_parameters=true
- max_retries: 0 on billed calls; receipt-fetch retry/backoff so a receipt race
  cannot turn a paid call into a permanently excluded row
- per-panel worst-case cost check BEFORE the block starts; cumulative receipt-cost
  polling between blocks; hard kill at the panel ceiling
- every attempt appended to the existing AttemptLedger with termination + usage
- --dry-run (default) simulates cost from the length model in 02_BUDGET_AND_COSTS.md

Tests: gate triggers exactly at ceiling; ledger hash chain verifies; dry-run cost
within 5% of a hand-computed fixture; schedule mismatch refuses; cache key includes
max_tokens.
```

---

## 5. Review contract

Every PR gets an adversarial review before merge (see `reap/REVIEW_PR1_ECOSYSTEM_AUDIT.md` for what that looks like: independent recomputation of headline numbers, permalink verification, mutation-testing the tests, classification of every failure as harness-fault vs agent-fault). Assume your numbers will be recomputed from raw data by a hostile reviewer. Report what you *assumed* as loudly as what you verified — an assumption disclosed is a finding; an assumption hidden is a defect.
