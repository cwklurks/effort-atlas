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
| 6 | `PREREGISTRATION.md` + `PREREGISTRATION_AMENDMENT_2026-07-22.md` | **FROZEN. Never edit.** Read to understand what is already committed. |
| 7 | `reap/REVIEW_PR1_ECOSYSTEM_AUDIT.md` | Red-team review of PR #1 and its 8 blocking fixes. |
| 8 | `observational/RESULTS.md` + `observational/pipeline.py` + `observational/INPUT_PROVENANCE.md` | The free observational study (done, verified). Pipeline is pinned — agents run it, never rewrite its statistics. Input acquisition is not yet clean-checkout reproducible. |
| 9 | `src/effort_atlas/` + `tests/` | Existing code. Note `confirmatory.py` (offline preflight, ledger, schedules) is solid; `graders.py` is defective (see Task B). |

## 2. Project state, in one screen

**The paper:** output-token walls truncate reasoning responses before a final answer exists; graders score deletions as wrong; higher effort writes longer and hits walls more — so a wall can masquerade as "thinking makes models worse." Two halves: censored-length analysis (supervisor's) + effort×allowance interventions (ours). Merged paper, Connor first author.

**What exists and works:** the frozen Phase-I preregistration + one dated amendment ($0 confirmatory spend, ever); the offline confirmatory preflight (hash-chained AttemptLedger, seeded/hashed schedules, receipt reconciliation) with tests passing; the cap-semantics audit (4 routes, receipts, one route billed 2.75× its requested cap); the observational study (427 at-cap generations found in public data; 0% accuracy at cap vs up to 99% below; verified by 7 independent spot-checks). Grader v2, the Tinker probe, and the pre-data analysis layer now have separate implementation branches that pass independently under supported Python when their fixtures are present.

**What does NOT exist yet:** an integrated grader + analysis baseline; a paid runner; executable budget gates; a frozen REAP preregistration; settled live Tinker/OpenAI smoke facts. Nothing confirmatory can run until those gates close. Task A's ecosystem-audit fixes and Task E's runner are not complete.

**Funding:** $5,000 Tinker credits + ~$200 OpenAI (supervisor) + <$100 OpenRouter. Platform-scoped pools, never mixed. Cost model and gates in `reap/02_BUDGET_AND_COSTS.md`.

**Branch / PR state as of 2026-08-08:**

| Work | State | Blocking issue |
|---|---|---|
| Phase 0 — `codex/reap-governance`, PR #4 | clean-archive green; independently approved | awaiting human review/merge; later phases must branch from the accepted governance baseline |
| A — `codex/ecosystem-audit`, PR #1 | open at reviewed commit `5c31b53` | all 8 blocking fixes remain; rejected headlines are still present |
| B — `codex/grader-v2`, draft PR #2 | implemented at `fa38093`; independently green | the 78-row test trusts a precomputed empty projection instead of rerunning a defensible archive-derived fixture |
| C — `codex/tinker-probe` | local implementation at `31d5fb3`; no PR/upstream | 65,536 changes model routes; omitted-cap cost bound is unknown; no live facts are settled |
| D — `codex/analysis-layer`, PR #3 | implemented at `28e78aa`; independently green | conflicts with B in 3 files; transition table pairs item×replicate rather than the specified item-level unit |
| E — `codex/runner` | not implemented | waits on accepted grader interfaces, frozen design inputs, and corrected budget math |

The current phase-gate and model-routing plan is in
`reap/10_PHASE_GATE_PLAN_2026-08-08.md`.

## 3. The laws (repeated because they are load-bearing)

1. **Never edit frozen artifacts:** `PREREGISTRATION*.md`, `confirmatory_artifacts/**`, anything headed FROZEN, `observational/pipeline.py` statistics logic. Propose changes as new dated files.
2. **Never make paid study-generation, smoke, or provider-probe calls.** Every script defaults to `--dry-run`; live execution is human-initiated. Secrets from env vars only; fail loudly if unset. Explicitly user-authorized OpenCode Go development calls are allowed only under the bounded, no-secrets, no-`--auto`, independently-reviewed exception in `AGENTS.md`.
3. **Explicit `max_tokens` on every request template.** This project exists because an endpoint silently defaulted to 4096.
4. **No fallback answer extraction.** A "last number anywhere" fallback already corrupted a study here.
5. **Log termination reason + token usage at collection time** on every row. It is unrecoverable afterward.
6. **Import upstream code; never reimplement it.** If an import fails, fix the environment or report `import_failed` — do not re-code the logic (this rule was violated in PR #1 and produced a wrong headline).
7. Branch + PR, checkpoint commit per unit of work, never merge. PR description states: what changed, what was verified, what was assumed.

---

## 4. Task queue

Current gate order: **Phase 0 governance → B acceptance → B/D integration → preregistration freeze → E runner → human smoke → confirmatory collection**. A and the dry-run-only C repair may proceed in parallel where their file ownership is isolated. The original task specifications remain below as acceptance contracts.

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
runs and has 177 rows at 4096 tokens. The current pre-v2 baseline command is
`PYTHONPATH=src python3 -m unittest discover -s tests -v`: 40 tests pass, while the
bare function in `tests/test_rescue_analysis.py` is not collected.

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
