# Agent playbook — running parallel agents on REAP without wrecking it

**Principle: parallel lanes, serial gates.** Agents work branches and open PRs; nothing merges without tests green + one cross-review; Connor is the only merger. No agent touches frozen artifacts (PREREGISTRATION.md, amendments, committed schedules, frozen grader/analysis commits). No agent makes paid study or provider-probe calls. Explicitly user-authorized OpenCode Go development calls follow the bounded exception in `AGENTS.md`. No keys in prompts — env vars only.

## Lane map

| Lane | Tool | Work |
|---|---|---|
| Harness engineering | Codex | grader v2, smoke/probe scripts, runner + budget gates, tests |
| Mechanical support | DeepSeek V4 Flash / Fireworks ZDR | selected but disabled pending committed development-only config and hard ceiling; never final verification |
| Data studies | Claude (Cowork) | MathArena/HELM analyses, length priors, power calc, figures |
| Research & lit | Claude Project / subagents | license checks, author emails, weekly arXiv monitor, citation forward-search |
| Red-team | Claude (Cowork) | adversarial review of every PR/doc/analysis before it counts as done |
| Docs & PM | Claude Project | brief updates, meeting notes, prereg drafting support |

## The universal header (paste at the top of EVERY agent prompt)

```
CONTEXT: You are working on REAP (repo: effort-atlas), the experimental program
behind the paper "Thinking Cut Short" (output-token walls truncate LLM reasoning;
graders score deletions as wrong; we separate token starvation from real declines).
Read reap/README.md and reap/08_HYPERPARAMETER_DECISIONS.md before acting.

RULES: (1) Never fabricate — mark everything as verified / assumed / TODO.
(2) Never edit PREREGISTRATION*.md, committed schedules, or any file marked frozen.
(3) Never make paid study-generation, smoke, or provider-probe calls; write scripts
with a --dry-run default and explicit max_tokens on every request template. A
user-authorized OpenCode Go call may only assist development under AGENTS.md.
(4) Work on a branch; open a PR; do not merge.
(5) All secrets via environment variables; fail loudly if unset.
(6) End your work with a report: what you did, what you verified, what you assumed,
what needs human review.
```

## Prompt 1 — Codex: grader v2 (highest priority engineering task)

```
[universal header]
TASK: Rewrite answer extraction in src/effort_atlas/graders.py as grader v2.
SPEC: A response counts as answered ONLY if it contains an explicit final-answer
terminator line matching "Final answer: <answer>" (configurable regex). Remove all
fallback extraction (no "last number anywhere", no first/last-$ spans). Output per
response: {extracted_answer_present: bool, extracted_answer: str|None}. Grading
compares extracted_answer to gold via the existing numeric comparator; termination
(finish_reason) is NEVER an input to extraction or grading.
TESTS (tests/test_grader_v2.py, must all pass):
- answer then truncation afterwards => answered=True (cap hit AFTER answering)
- truncated mid-reasoning with stray numbers => answered=False
- truncated mid-box "\boxed{29" => answered=False, no exception
- MCQ letter mid-enumeration ("consider (C), which...") => answered=False
- well-formed "Final answer: 42" => answered=True, extracted "42"
ACCEPTANCE: rerun v2 over the archived Tinker exploratory log; it must report
exactly 78 rows with finish at 4096 and extracted_answer_present=False, where the
old grader reported zero parse failures. Include this as an integration test with
the count asserted.
```

## Prompt 2 — Codex: Tinker smoke + cap-semantics probe script

```
[universal header]
TASK: Write scripts/tinker_probe.py using the tinker SDK (SamplingParams: max_tokens,
seed, temperature, top_p, top_k, stop; num_samples on the sampling client).
BEHAVIOR (all --dry-run by default; --live requires TINKER_API_KEY env var):
1. smoke: 2 calls on GPT-OSS-20B — one generous max_tokens easy prompt, one tiny
   max_tokens forcing truncation. Record full response metadata.
2. default-probe: one call OMITTING max_tokens deliberately — record what default
   the platform applies (this is the Phase I bug, probed on purpose).
3. cap-probe: per target model {Inkling, GPT-OSS-120B}, hard item at caps
   {4096, 16384, 32768, 65536}: record stop_reason vocabulary, token counts,
   whether billed/usage tokens ≤ requested cap.
4. samples-probe: one item, num_samples=8, temperature default, distinct seeds —
   verify the 8 outputs differ (independence sanity).
OUTPUT: JSONL per call: request params, response text hash, token usage, stop
reason, timestamp. Summary table printed at end. No retries on billed calls.
```

## Prompt 3 — Claude: MathArena/HELM data study

```
[universal header]
TASK: Free-data observational study. (a) Download MathArena output parquets
(hmmt_feb_2025/2026, aime_2026, brumo_2025) and selected HELM runs (capabilities
GPQA CoT). (b) Per model×effort: fit length distributions (report lognormal fit +
empirical quantiles); compute exact-cap clustering (rows at >=99.5% of model max);
accuracy at-cap vs below-cap; effort dose-response of median/p90 length.
(c) For HELM Gemini runs use finish_reason="length" as ground-truth censoring labels.
(d) Produce: results parquet, a figures notebook (follow the repo's dataviz
conventions), and a one-page RESULTS.md with every number traceable to code.
LABEL everything exploratory. Do not extrapolate beyond observed supports.
```

## Prompt 4 — Claude: red-team review (run on every finished artifact)

```
[universal header]
TASK: Adversarially review <artifact>. You are trying to find reasons it is WRONG,
not to summarize it. For code: hunt silent-failure paths (swallowed exceptions,
fallback extractions, unset max_tokens, retry-on-billed-call), test the tests
(mutate the code; do the tests catch it?). For analyses: recompute 3 headline
numbers from raw data independently; check labels (exploratory vs confirmatory);
check every claim against its cited source. Output: findings ranked by severity
with file:line, each with a concrete failure scenario. Empty findings list is an
acceptable answer only after you state what you tried.
```

## Prompt 5 — Claude Project: weekly lit monitor

```
TASK: Search arXiv (last 14 days) for: effort/budget × truncation × evaluation;
Kaplan-Meier or censoring + language models; overthinking/test-time scaling
declines; benchmark truncation artifacts. Also run forward-citation checks on
2605.07686 and 2602.09805. Report: new papers with 2-line relevance verdicts;
anything that overlaps our claims gets a red flag + which claim it touches.
Never summarize a paper you could not open; mark abstract-only reads.
```

## Prompt 6 — Codex: runner + budget gates (after grader v2 merges)

```
[universal header]
TASK: Implement the REAP runner per reap/01_EXPERIMENT_OUTLINE_v2.md §measurement
and reap/02_BUDGET_AND_COSTS.md §gates: reads frozen schedule JSON; explicit
max_tokens + effort on every call; per-panel ceiling check before start; cumulative
usage polling between blocks; hard kill at ceiling; termination + usage logged per
row at collection; append-only attempt ledger (reuse Phase I AttemptLedger);
zero automatic retries on billed calls. --dry-run simulates from the length model
in 02_BUDGET_AND_COSTS.md and prints projected cost per block.
TESTS: gate triggers at ceiling; ledger chain verifies; dry-run cost within 5% of
hand-computed fixture; a schedule mismatch refuses to run.
```

## Root agent instructions

`AGENTS.md` at the repository root is the only canonical Codex instruction file.
Never reconstruct or overwrite it from an embedded template. New worktrees must
receive that tracked file and follow its mandatory briefing, frozen boundaries,
development-tool exception, model routing, and canonical verification command.

## Cadence

Weekly rhythm: Monday — assign lane tasks (one prompt each); midweek — red-team pass on whatever finished; Friday — merge what survived review, update PROJECT_BRIEF.md, post the week's artifact to Slack for Chirag. Sheer volume is fine; unreviewed volume is how hidden walls happen.
