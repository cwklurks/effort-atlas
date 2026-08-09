# Executable truncation diagnostic

This executes pinned post-generation callables in isolation. It is not end-to-end harness evaluation and performs no generation. Real and constructed synthetic rows are reported in separate tables and never share a denominator.

## Limitations

The public corpus is found data, not a probability sample. Pipelines with identical applicable fixture sets and identical outputs are one repeated measurement through equivalent fallback behavior, not independent replications. A returned answer is an operational extraction event, not proof that the harness invented text. `insufficient_power` means fewer than 20 applicable real truncated rows; it is descriptive and not headline-eligible.

The frozen control gate uses exactly the 28 finished-correct rows whose gold matches `^[+-]?\d+$` (four unique dataset/problem/gold items) for every runnable pipeline. Task-specific applicability is used only for truncated-result reporting.

For `inspect_evals/aime_last_line_numeric`, the task-matched real control subset is six replicates of one AIME problem (`n_eff=1`); its real truncated result has n=7, five empty texts, and three unique problems. The uniform 28-row cross-pipeline control table does not cure that power limitation.

The real corpus has 131 truncated generations: 26 contain the frozen nonempty `\boxed{...}` marker before the cut and 105 do not.

For lm-eval GSM8K flexible extraction, six of the 111 returned real values contain no digit: `$$` (3), `$.` (2), and `$,` (1). The per-row `answer_is_numeric` field keeps these operational sentinel-like strings visible.

## Real truncated generations

| Target | Pipeline | Status | n | n_eff | Empty | Answer returned | Numeric among returned | Accidental correct | Marker present | Marker absent | Uniform controls |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lm-evaluation-harness | gsm8k_flexible_extract | control_disqualified | 131 | 48 | 12 | 111/131 (84.732824%) | 105/111 (94.594595%) | 0/131 (0.000000%) | 26/26 (100.000000%) | 85/105 (80.952381%) | 24/28 (85.714286%) |
| lm-evaluation-harness | aime_process_results | ok | 48 | 24 | 11 | `not_measured` | `not_measured` | 1/48 (2.083333%) | `not_measured` | `not_measured` | 28/28 (100.000000%) |
| opencompass | gsm8k_last_number | ok | 48 | 24 | 11 | 37/48 (77.083333%) | 37/37 (100.000000%) | 0/48 (0.000000%) | 6/6 (100.000000%) | 31/42 (73.809524%) | 28/28 (100.000000%) |
| helm | math_chain_of_thought | ok | 131 | 48 | 12 | 23/131 (17.557252%) | 20/23 (86.956522%) | 1/131 (0.763359%) | 23/26 (88.461538%) | 0/105 (0.000000%) | 28/28 (100.000000%) |
| inspect_ai | gsm8k_numeric_match | control_disqualified | 48 | 24 | 11 | 37/48 (77.083333%) | 37/37 (100.000000%) | 0/48 (0.000000%) | 6/6 (100.000000%) | 31/42 (73.809524%) | 24/28 (85.714286%) |
| inspect_evals | aime_last_line_numeric | insufficient_power | 7 | 3 | 5 | 0/7 (0.000000%) | `not_applicable` | 0/7 (0.000000%) | `not_measured` | 0/7 (0.000000%) | 15/28 (53.571429%) |
| simple-evals | mgsm_answer_prefix | control_disqualified | 131 | 48 | 12 | 2/131 (1.526718%) | 2/2 (100.000000%) | 0/131 (0.000000%) | 2/26 (7.692308%) | 0/105 (0.000000%) | 1/28 (3.571429%) |
| lighteval | math_extractive_match | ok | 131 | 48 | 12 | 111/131 (84.732824%) | 109/111 (98.198198%) | 2/131 (1.526718%) | 26/26 (100.000000%) | 85/105 (80.952381%) | 28/28 (100.000000%) |
| livebench | aime_last50 | ok | 48 | 24 | 11 | `not_measured` | `not_measured` | 0/48 (0.000000%) | `not_measured` | `not_measured` | 28/28 (100.000000%) |
| matharena | competition_extract_and_grade | ok | 131 | 48 | 12 | 111/131 (84.732824%) | 110/111 (99.099099%) | 3/131 (2.290076%) | 26/26 (100.000000%) | 85/105 (80.952381%) | 28/28 (100.000000%) |

Rows marked `control_disqualified`, `insufficient_power`, or non-runnable are retained with explicit real denominators but excluded from headline comparison. `not_measured` means the upstream task path does not expose an extracted-answer value.

## Constructed synthetic probes

**Constructed probes only. These strings were authored to exercise parser shapes and are not model generations, prevalence estimates, or evidence of real-world correctness.**

| Target | Pipeline | n | Answer returned | Accidental correct | Crash |
|---|---|---:|---:|---:|---:|
| lm-evaluation-harness | gsm8k_flexible_extract | 100 | 100/100 (100.000000%) | 40/100 (40.000000%) | 0/100 (0.000000%) |
| lm-evaluation-harness | aime_process_results | 100 | `not_measured` | 0/100 (0.000000%) | 0/100 (0.000000%) |
| opencompass | gsm8k_last_number | 100 | 100/100 (100.000000%) | 40/100 (40.000000%) | 0/100 (0.000000%) |
| helm | math_chain_of_thought | 100 | 0/100 (0.000000%) | 0/100 (0.000000%) | 0/100 (0.000000%) |
| inspect_ai | gsm8k_numeric_match | 100 | 100/100 (100.000000%) | 40/100 (40.000000%) | 0/100 (0.000000%) |
| inspect_evals | aime_last_line_numeric | 100 | 40/100 (40.000000%) | 20/100 (20.000000%) | 0/100 (0.000000%) |
| simple-evals | mgsm_answer_prefix | 100 | 0/100 (0.000000%) | 0/100 (0.000000%) | 0/100 (0.000000%) |
| lighteval | math_extractive_match | 100 | 100/100 (100.000000%) | 40/100 (40.000000%) | 0/100 (0.000000%) |
| livebench | aime_last50 | 100 | `not_measured` | 40/100 (40.000000%) | 0/100 (0.000000%) |
| matharena | competition_extract_and_grade | 100 | 100/100 (100.000000%) | 40/100 (40.000000%) | 0/100 (0.000000%) |

## Demoted non-headline diagnostics

- `olympiad_expression` is retained for audit history but is `wrong_task_dispatch`: wrong task dispatch for AIME-shaped data; IMO/USAMO only
- `default_parse_verify` is retained for audit history but is `generic_utility_only`: generic utility only; no task registration was imported or executed

## Headline-eligible real-data pipeline rows

| Target | Pipeline | Answer returned after truncation |
|---|---|---:|
| lm-evaluation-harness | aime_process_results | `not_measured` |
| opencompass | gsm8k_last_number | 37/48 (77.083333%) |
| helm | math_chain_of_thought | 23/131 (17.557252%) |
| lighteval | math_extractive_match | 111/131 (84.732824%) |
| livebench | aime_last50 | `not_measured` |
| matharena | competition_extract_and_grade | 111/131 (84.732824%) |

## Locked repositories

- `lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`; `lm_eval.filters.extraction:RegexFilter.apply + lm_eval.api.metrics:exact_match_hf_evaluate`
- `lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`; `lm_eval.tasks.aime.utils:process_results`
- `opencompass` at `96263b1a16899260586c8e945eea06934c43c225`; `opencompass.datasets.gsm8k:gsm8k_postprocess + Gsm8kEvaluator.score`
- `helm` at `63754d05db6f874e41a395880fb573890a13e791`; `helm.benchmark.scenarios.math_scenario:get_answer + is_equiv`
- `inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`; `inspect_ai.scorer:match(numeric=True)`
- `inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`; `inspect_evals.utils.aime_common:aime_scorer`
- `simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`; `mgsm_eval:parse_answer + score_mgsm`
- `lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`; `lighteval.metrics.metrics:Metrics.expr_gold_metric.value.compute_sample + lighteval.metrics.utils.extractive_match_utils:extract_target_from_pred`
- `livebench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`; `livebench.process_results.math.math_competitions.utils:aime_process_results`
- `livebench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`; `livebench.process_results.math.olympiad.utils:extract_expression_completions_from_generation + proof_rearrangement_process_results`
- `math-verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`; `math_verify:parse + verify`
- `matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`; `matharena.grader:extract_and_grade`
