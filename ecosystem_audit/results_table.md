# Executable truncation diagnostic

This executes pinned post-generation callables in isolation. It is not end-to-end harness evaluation and performs no generation. `fabrication_pct` is only an operational alias for a nonempty answer returned after labeled truncation; it is not proof that text was invented.

| Target | Pipeline | Status | Answer returned combined | Real | Synthetic | Accidental correct | Crash | Swallowed error | Control pass |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| lm-evaluation-harness | gsm8k_flexible_extract | control_disqualified | 211/231 (91.341991%) | 111/131 (84.732824%) | 100/100 (100.000000%) | 40/231 (17.316017%) | 0/231 (0.000000%) | `not_measured` | 24/64 (37.500000%) |
| opencompass | gsm8k_last_number | import_failed | `not_applicable` | `not_applicable` | `not_applicable` | `not_measured` | `not_applicable` | `not_measured` | `not_measured` |
| helm | math_chain_of_thought | control_disqualified | 23/231 (9.956710%) | 23/131 (17.557252%) | 0/100 (0.000000%) | 1/231 (0.432900%) | 0/231 (0.000000%) | `not_measured` | 51/64 (79.687500%) |
| inspect_ai | gsm8k_numeric_match | control_disqualified | 137/148 (92.567568%) | 37/48 (77.083333%) | 100/100 (100.000000%) | 40/148 (27.027027%) | 0/148 (0.000000%) | `not_measured` | 24/28 (85.714286%) |
| inspect_evals | aime_last_line_numeric | ok | 40/107 (37.383178%) | 0/7 (0.000000%) | 40/100 (40.000000%) | 20/107 (18.691589%) | 0/107 (0.000000%) | `not_measured` | 6/6 (100.000000%) |
| simple-evals | mgsm_answer_prefix | control_disqualified | 2/231 (0.865801%) | 2/131 (1.526718%) | 0/100 (0.000000%) | 0/231 (0.000000%) | 0/231 (0.000000%) | `not_measured` | 1/64 (1.562500%) |
| lighteval | math_extractive_match | control_disqualified | 211/231 (91.341991%) | 111/131 (84.732824%) | 100/100 (100.000000%) | 42/231 (18.181818%) | 0/231 (0.000000%) | `not_measured` | 38/64 (59.375000%) |
| livebench | olympiad_expression | ok | 135/148 (91.216216%) | 35/48 (72.916667%) | 100/100 (100.000000%) | 21/148 (14.189189%) | 0/148 (0.000000%) | 1/148 (0.675676%) | 28/28 (100.000000%) |
| math-verify | default_parse_verify | control_disqualified | 211/231 (91.341991%) | 111/131 (84.732824%) | 100/100 (100.000000%) | 43/231 (18.614719%) | 0/231 (0.000000%) | `not_measured` | 61/64 (95.312500%) |
| matharena | competition_extract_and_grade | control_disqualified | 211/231 (91.341991%) | 111/131 (84.732824%) | 100/100 (100.000000%) | 43/231 (18.614719%) | 0/231 (0.000000%) | `not_measured` | 63/64 (98.437500%) |

Rows marked `control_disqualified` retain all measurements but are excluded from headline comparison. Non-runnable/status rows have no fabricated percentage denominator. Empty real texts remain applicable where the callable accepts them.

## Headline-eligible pipeline rows

| Target | Pipeline | Answer returned after truncation |
|---|---|---:|
| inspect_evals | aime_last_line_numeric | 40/107 (37.383178%) |
| livebench | olympiad_expression | 135/148 (91.216216%) |

## Locked repositories

- `lm-evaluation-harness` at `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`; `lm_eval.filters.extraction:RegexFilter.apply + lm_eval.api.metrics:exact_match_hf_evaluate`
- `opencompass` at `96263b1a16899260586c8e945eea06934c43c225`; `opencompass.datasets.gsm8k:gsm8k_postprocess + Gsm8kEvaluator.score`
- `helm` at `63754d05db6f874e41a395880fb573890a13e791`; `helm.benchmark.scenarios.math_scenario:get_answer + is_equiv`
- `inspect_ai` at `f10dc46f20df0738a9acbfb4c4be0bd3d60601ed`; `inspect_ai.scorer:match(numeric=True)`
- `inspect_evals` at `b31daf3f6f74ce48cb905d185a4c2afc524205b2`; `inspect_evals.utils.aime_common:aime_scorer`
- `simple-evals` at `652c89d0ca9df547706735883097e9537d40dc47`; `mgsm_eval:parse_answer + score_mgsm`
- `lighteval` at `64f4f5ae173626509fad6e477ca4ee56ebb26129`; `lighteval.metrics.utils.extractive_match_utils:extract_target_from_pred`
- `livebench` at `00eae856aa1c1a9e9d058a65a9a94d85884034c4`; `livebench.process_results.math.olympiad.utils:extract_expression_completions_from_generation + proof_rearrangement_process_results`
- `math-verify` at `ba3d3aaff23b3f4cac7a14672b4f6e293d97c98b`; `math_verify:parse + verify`
- `matharena` at `a11194deff8c67a232974a383795e8a2776b4c6f`; `matharena.grader:extract_and_grade`
