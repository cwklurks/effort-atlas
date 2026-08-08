# Gaps and amendments

## 2026-08-07 Phase 0 contract

- Worktree was clean on `codex/ecosystem-audit`; task start commit: `da183fc9cba84fb866be757ec0158c79ed28571c`; merge base: `7451f1c0bd650201bb59cbf2ad90a8d2c4adffdd`.
- Base origin, GitHub access, authentication, dry-run push permission, and unoccupied remote head were verified.
- Python is 3.12.8. Root requirement imports pass when `MPLBACKEND=Agg` overrides the parent notebook's non-project inline backend.
- The real fixture SHA-256 is `b84adb85eccd6b628829cdadb71c29fa25eb4dc0a37d387f554464b312d96f43`; 195 rows decode: 131 truncated, 64 controls, and 12 empty truncated texts.
- All ten named components were cloned with full default-branch history and frozen in `repos.lock.json`. Tags were intentionally not fetched. `inspect_ai` and `math-verify` declare uninitialized submodules; no selected executable candidate needs those gitlinks because the package dependency path is used.
- Applicability was frozen before any executable measurement. A candidate that proves unimportable remains in results with its concrete status; no measured rate will be substituted.
- No paid key or model/dataset call is needed or permitted.

## 2026-08-07 Phase 1 search gaps

- `lm-evaluation-harness`: `not found at <lm_eval/**/*.py paths searched>` for `finish_reason`, `stop_reason`, or `incomplete_details` capture/persistence/scorer use; search: `rg -n 'finish_reason|stop_reason|incomplete_details' lm_eval`.
- `lm-evaluation-harness`: the earlier AIME `not found` statement is retracted. The pinned tree contains `lm_eval/tasks/aime/aime.yaml` with `max_gen_toks: 32768` and `utils.py` with the task's dollar-span/boxed extraction path; see F068-F069 and the executable `aime_process_results` pipeline.
- `opencompass`: scorer logic using captured finish reason to distinguish truncation from wrong was `not found at <opencompass/evaluator, opencompass/datasets, opencompass/tasks paths searched>`; search pattern `finish_reason|stop_reason|incomplete_details`.
- `helm`: AIME task `not found at <src/helm paths searched>` using `rg -ni '\baime\b' src/helm`. A correctness scorer condition on finish reason was `not found at <src/helm/benchmark/metrics/gpqa_chain_of_thought_metric.py, src/helm/benchmark/metrics/evaluate_reference_metrics.py paths searched>`.
- `inspect_ai` / `inspect_evals`: AIME scorer use of `stop_reason` was `not found at <src/inspect_evals/utils/aime_common.py and src/inspect_ai/scorer paths searched>`; the signal remains present on ModelOutput but is not a scorer input in this path.
- `simple-evals`: AIME and GSM8K exact tasks were `not found at <*.py paths searched>` with `rg -ni '\baime\b|gsm8k' .`; MGSM is the closest GSM path. Any captured/persisted finish signal was `not found at <sampler/*.py, *_eval.py, types.py, simple_evals.py paths searched>` using `finish_reason|stop_reason|incomplete_details`.
- `lighteval`: output `finish_reason`, `stop_reason`, and `incomplete_details` were `not found at <src/lighteval paths searched>`; the inspected LiteLLM conversion explicitly reduces choices to content/reasoning. `truncated_tokens_count` is input truncation, not completion termination.
- `livebench`: GSM8K and GPQA were `not found at <livebench tracked paths searched>`; closest math/reasoning tasks were audited. Task-specific cap fields were `not found at <livebench/process_results and ground-truth dispatch paths searched>`; tasks inherit the global CLI/model configuration.
- `math-verify`: generation finish fields were `not found at <tracked checkout paths searched>` using `git grep -n -E 'finish_reason|stop_reason|incomplete_details'`; this package accepts post-generation text.
- `matharena`: literal `finish_reason` and `stop_reason` were `not found at <src, configs, scripts, app paths searched>`. Provider raw response logs may contain a signal, but the semantic result drops it and the scorer uses only a token-count heuristic.
- Issue discovery used the requested combined terms against every locked repository and preserved the search result metadata in `issue_searches.json`. The four mandated anchors were fetched directly and independently into `issue_receipts.json`.

## 2026-08-07 pre-execution applicability amendment

Before any measured execution, candidate callables were narrowed to task-traced functions found during Phase 1. No rates had been observed. The amended `applicability.csv` preserves all ten named targets. Registered no-answer sentinels `[invalid]` (lm-eval) and `NULL` (OpenCompass) are classified as empty/no answer before measurement because the harnesses themselves use them for failed extraction. MathArena uses each real row's named competition config with `strict_parsing=false`; Inspect Evals is scoped to AIME real rows plus numeric synthetic rows; nonapplicable fixture rows remain explicit.

## 2026-08-07 Phase 2 execution statuses (historical, superseded by round 2)

- At reviewed commit `5c31b53`, OpenCompass remained `import_failed`: importing the real registered dataset module through the pinned package ended at `ModuleNotFoundError: No module named 'rouge_score'`. Round 2 fixes and reruns this audit-owned environment defect.
- At reviewed commit `5c31b53`, the Inspect Evals AIME and LiveBench olympiad rows were incorrectly treated as headline-eligible. Round 2 marks Inspect Evals `insufficient_power`, dispatches LiveBench AIME data through its real AIME scorer, demotes the olympiad path, and recomputes every control under the uniform frozen schema.
- Swallowed-error rates are `not_measured` except where the adapter manifest declares concrete logger/sentinel instrumentation. Per-fixture wall time is captured in ephemeral adapter timing logs; timing is excluded from committed deterministic result bytes.
- The isolated environments and exact frozen package sets are under `ecosystem_audit/environments/`; install commands and dependency-lock hashes are in `adapter_manifest.json`.

## 2026-08-07 Phase 3 archaeology limits

- `timeline.csv` records commit author timestamps (`%aI`), not merge or release dates. `validate_timeline.py` verifies each traced commit is in the pinned snapshot ancestry and the historical blob contains the cited setting.
- OpenCompass AIME and GPQA task-local numeric caps are `not_traceable` in the pinned configuration tree. Exact zero-result `git grep` commands are preserved in `timeline_evidence.json`; no model/provider default is guessed.
- A setting's presence in history does not establish that every downstream invocation used it. Each timeline scope distinguishes shared defaults, provider defaults, and task-local caps.

## 2026-08-08 round-2 corrections

- Real and constructed synthetic rows are now reported in separate tables and metric strata; no combined denominator remains.
- Control eligibility is frozen uniformly to the 28 finished-correct rows with base-10 integer golds (`^[+-]?\d+$`), representing four unique dataset/problem/gold items. Task-specific applicability still scopes the real truncated result, not the control gate.
- `inspect_evals/aime_last_line_numeric` has only seven applicable real truncated rows, five empty texts, and one unique problem. It is `insufficient_power` and is not headline-eligible.
- LiveBench's `olympiad_expression` result is retained only as a wrong-dispatch diagnostic. AIME-shaped rows execute `aime_process_results`, the scorer selected by the pinned dispatch site.
- OpenCompass's prior `import_failed` status was caused by the audit environment omitting `rouge-score`; round 2 pins that dependency and reruns the actual registered task module.
- The 26/105 `pre_truncation_answer_present` split is a frozen syntactic marker stratification, not a claim that the marker contains the correct answer.
