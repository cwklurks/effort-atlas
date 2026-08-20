# Post-meeting benchmark audit

**Date:** 2026-08-18
**Status:** Planning document. It does not freeze a design or authorize any model call.

Companion records: `19_METHOD_REVIEW_SYNTHESIS_2026-08-18.md` preserves the
nine-response methodology synthesis; `20_BENCHMARK_COMPARISON_2026-08-18.md`
contains the source-pinned meeting table; and
`21_MODEL_PAIR_ELIGIBILITY_2026-08-18.md` records which comparisons remain
conditional or descriptive-only.

## One-sentence research question

On the same benchmark questions and across native reasoning-effort settings, at
accuracy levels both models actually attain, how many comparably measured output
tokens does each use, and when the output allowance is raised, how do scored
accuracy and unanswered length stops change?

## What “per prompt” and “per question” mean

- A **question** is one benchmark item, identified by `problem_idx` in MathArena or
  `instance_id` in HELM.
- A **prompt** is the exact message sent to a model for that question. It includes
  the problem, instructions, answer format, and any model-specific wrapper.
- A **response row** is one model attempt on one prompt. If a model has multiple
  attempts on one question, question-level accuracy is the fraction of those
  attempts that were correct.

The comparison should begin with response rows and then aggregate them so that each
question receives equal weight. Otherwise, a question or model with more attempts
would influence the result more heavily.

For model `m`, question `q`, and attempt `r`, the minimum useful row is:

```text
benchmark_id, question_id, prompt_hash, model_id, model_config,
attempt_id, correct, output_tokens, requested_output_cap,
finish_reason, cap_status, answer_present
```

`cap_status` must distinguish `observed`, `inferred`, and `unknown` rather than
turning every long response into a confirmed token-limit stop.

## Benchmark comparison

| Source | Domain and evaluated questions | Exact prompt / question ID | Per-response correctness | Per-response token count | Direct token-limit label | What can be said honestly | URL |
|---|---:|---|---|---|---|---|---|
| HELM Capabilities v1.15 GPQA CoT | Graduate-level science; 446 evaluated items in each archived project run (GPQA contains 448 source instances) | Yes: HELM stores the request with an instance ID | Yes | Present in the archive, but current provider/tokenizer accounting is not comparable across all three models | **Gemini 3 Pro only** in the archived slice; 42 rows have `finish_reason="length"`. The Claude and OpenAI finish-reason fields are empty | Per-question accuracy is available for all three archived models. Confirmed length stopping is available only for Gemini. Do not claim a fair cross-model reasoning-token comparison from the current HELM token fields alone | [HELM Capabilities](https://crfm.stanford.edu/helm/capabilities/latest/) |
| MathArena HMMT Feb 2025 | Competition math; 30 questions | Yes: `problem_idx`, `user_message`, and `all_messages` | Yes: `correct` | Yes: `output_tokens` | No | Per-question correctness and length are available. A row can be flagged as near an apparent cap, but the source does not prove its finish reason | [outputs](https://huggingface.co/datasets/MathArena/hmmt_feb_2025_outputs) |
| MathArena HMMT Feb 2026 | Competition math; 33 questions | Yes | Yes | Yes | No | Same as HMMT 2025. Chirag accepted using all 33; the provenance of rows 31–33 should still be documented in the paper | [outputs](https://huggingface.co/datasets/MathArena/hmmt_feb_2026_outputs) |
| MathArena AIME 2026 | Competition math; 30 questions | Yes | Yes | Yes | No | Per-question accuracy and length are available; token exhaustion remains inferred rather than provider-labeled | [outputs](https://huggingface.co/datasets/MathArena/aime_2026_outputs) |
| MathArena BRUMO 2025 | Competition math; 30 questions | Yes | Yes | Yes | No | Per-question accuracy and length are available; token exhaustion remains inferred rather than provider-labeled | [outputs](https://huggingface.co/datasets/MathArena/brumo_2025_outputs) |

The meeting transcription says MathArena combines “AMC and HMMT.” The repository’s
completed observational study instead uses HMMT 2025, HMMT 2026, AIME 2026, and
BRUMO 2025. The transcript should be corrected unless a separate AMC source is
later added.

## Can we compare Model A and Model B question by question?

**Yes, when both models answered the same question under documented prompt and
sampling conditions.** For each shared question, report:

| Question | Model A correct / attempts | Model A token summary | Model A cap status | Model B correct / attempts | Model B token summary | Model B cap status |
|---|---:|---:|---|---:|---:|---|

This permits paired questions such as “Model A was correct and Model B was wrong”
or “both were correct, but Model A used fewer output tokens.” It does not make
provider token counts perfectly interchangeable: different tokenizers and hidden
reasoning accounting can measure tokens differently. Comparisons should therefore
be reported within a platform/configuration first, with cross-provider comparisons
clearly qualified.

The checked-in observational parquets contain model-level summaries, not the
question-level source rows. The public archives contain the needed rows, but the
repository does not yet have a clean-checkout acquisition process that downloads
and byte-verifies them. A reproducible question-level comparison therefore first
requires reacquiring the exact pinned revisions and recording file hashes.

## Can we say a model was wrong because it exhausted the limit?

Not from correctness and length alone.

1. **Observed length stop and wrong:** the response was cut off and was scored
   wrong. This is directly available for the 42 Gemini/HELM rows.
2. **Inferred at-cap and wrong:** the response ended at a repeated round-number
   maximum and was scored wrong, but the provider did not publish a finish reason.
   This is the strongest honest MathArena label.
3. **Wrong because of the cap:** this is a causal claim. It requires evidence that
   the question becomes answerable when the allowance is raised, ideally through
   the preregistered effort-by-cap experiment. A length stop is a termination fact,
   not a grade and not proof of a counterfactual correct answer.

The first two labels support the observational motivation. The third is what the
new controlled experiment is designed to estimate.

## Proposed performance-efficiency comparison

Use one point for each model × effort × output-cap condition:

- **x-axis:** accuracy, weighting each benchmark question equally;
- **y-axis:** the preregistered route-native output-use measure per question; call
  it billed output tokens only where per-response billing attribution is proved;
- **label:** model, effort, cap, and provider;
- **supporting values:** completion rate, unanswered length-stop rate, and number
  of questions/attempts.

At a common target accuracy `p`, compare the estimated token requirements
`T_A(p)` and `T_B(p)` using both the token difference and ratio:

```text
token difference = T_A(p) - T_B(p)
token ratio      = T_A(p) / T_B(p)
```

If the compared routes do not share a commensurate output measure, report the
cross-route token contrast as `not_estimable` rather than forcing a ratio.

The found-data archives alone do not identify the full accuracy-versus-allowance
curve. In particular, survival analysis can repair the distribution of completion
lengths under censoring, but it cannot invent the unobserved answer a truncated
response would eventually have produced. The planned larger-cap reruns supply that
missing performance evidence.

## Immediate next deliverable

Create a pinned, question-level audit table for every selected model/benchmark
pair:

1. acquire the exact MathArena revisions and HELM v1.15 run JSON;
2. record source URL, revision/run ID, size, and SHA-256 for every input;
3. verify that the selected models share the same question IDs;
4. verify prompt equality or record the exact prompt/config differences;
5. emit per-response rows using the minimum schema above;
6. summarize per-question accuracy, tokens, and observed/inferred cap status; and
7. show Chirag the paired coverage and missing fields before choosing the final
   model comparison or claiming token-efficiency differences.

No provider calls are required for this deliverable.
