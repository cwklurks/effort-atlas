# What the public omni_math HELM archives can actually tell us

**Date:** 2026-08-24
**Status:** Exploratory source audit of the HELM Capabilities v1.15.0 `omni_math`
run archives, following the format of
`reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md`. This document freezes
no experiment choice and authorizes no provider, smoke, or confirmatory call.
**No provider calls were made during this audit.** All reads were anonymous HTTPS
GETs of public Google Cloud Storage objects in `crfm-helm-public`.

## Bottom line

This audit tests the 2026-08-23 meeting claim that omni_math has **"fewer models
and no censoring."** The archives say the opposite on both counts:

1. **Not fewer models.** The v1.15.0 release manifest lists **68 omni_math runs** —
   the identical 68-model roster as `gpqa` (and `mmlu_pro`, `ifeval`, `wildbench`;
   each scenario has exactly 68 run keys). The GPQA number "3" from reap/22 was the
   count of models *audited there* (the three v1.15.0-suite runs), never the count
   of models archived.
2. **Heavily censored, and visibly so.** Among the 65 runs whose
   `scenario_state.json` is retrievable, **18 runs contain ≥1
   `finish_reason="length"` row, totaling 2,320 length-stops** out of 1,000
   instances per run. The worst: xai_grok-3-mini-beta **548/1,000**,
   xai_grok-3-beta **495/1,000**, google_gemini-3-pro-preview **392/1,000**,
   xai_grok-4-0709 **312/1,000**, openai_gpt-4.1-mini **168/1,000**, openai_gpt-4.1
   **150/1,000**, openai_o3 **106/1,000**.
3. **The requested output allowance is not one number.** Unlike the GPQA CoT runs
   (uniform 14,096), omni_math runs request four different `max_tokens` values
   depending on when the model was added: **2,048** (5 olmo/marin runs, encoded in
   the run key as `num_output_tokens=2048`), **4,096** (33 runs), **14,096** (25
   runs), **24,096** (2 runs: openai_o3, openai_o4-mini). Cross-model omni_math
   comparisons therefore mix four different censoring regimes.
4. **41 of 65 runs have all-blank finish reasons** — censoring status unknown, the
   same defect as HELM's Claude/GPT GPQA runs. Only 24 runs label termination at
   all, and two providers (Amazon, Mistral-large/small) use an `"endoftext"`
   vocabulary instead of `"stop"`.
5. **Token fields remain unusable as one cross-model axis.** 13 runs report
   `num_output_tokens = 0` on every row (all Gemini runs, both DeepSeek runs,
   qwen3-next-80b-thinking, palmyra-med/x5). Many others clip the reported count
   exactly at the requested cap. o3 reports a max of 1,450 "output tokens" while
   requesting 24,096 and recording 106 length-stops — plainly not the same unit as
   its actual generation.
6. **Three runs are missing `scenario_state.json` in the public bucket** (HTTP 404:
   meta_llama-3.1-8b-instruct-turbo, mistralai_mixtral-8x22b-instruct-v0.1,
   qwen_qwen2.5-72b-instruct-turbo; the mixtral run is missing
   `display_predictions.json` too). Their termination data is unrecoverable from
   the public archive.

One genuine difference from GPQA: omni_math `predicted_text` is **plaintext**, not
the encrypted placeholder GPQA uses, so a strict `Final answer:` regrade of
archived responses is possible in principle for omni_math (not done here).

## Direct parallel to the REAP thesis

- **Length-stops score near zero, but not exactly zero.** Joining
  `finish_reason="length"` rows to `omni_math_accuracy` in the same run's
  `display_predictions.json`: **189 of 2,320 length-stopped rows (8.1%) were scored
  correct**. Unlike HELM-GPQA-Gemini's clean 0/42, omni_math's LLM-annotated grader
  sometimes awards credit to a truncated response (largest case: grok-3-beta
  122/495 = 24.6% at-length accuracy vs 46.4% overall; but gemini-3-pro-preview
  17/392 = 4.3% vs 55.5% overall, and o3 0/106 vs 71.4% overall).
- **Truncation eats the visible answer of reasoning models.** For
  gemini-3-pro-preview, 332 of its 392 length-stop rows have an **empty
  `predicted_text`** (all 332 empty-text rows in the run are length-stops); for o3,
  all 106 length-stops have empty visible text. The budget is exhausted before any
  visible answer appears — exactly the mechanism REAP is about.
- The HELM Capabilities launch post's own error analysis flagged this on
  omni_math for DeepSeek v3 ("exceed output token limit",
  https://crfm.stanford.edu/2025/03/20/helm-capabilities.html); the archive shows
  the DeepSeek runs' finish labels are blank, so their censoring cannot be counted
  publicly — but Grok/Gemini/GPT-4.1/o3 can be, and are large.

## Per-run record (all 68 archived models)

`n` = evaluated instances in `scenario_state.json` (1,000 everywhere present —
HELM downsamples Omni-MATH's 4,428 source items to 1,000; the same 1,000
`instance_id`s across every run checked). `max_tok` = requested `max_tokens`,
identical on all 1,000 requests within each run. Finish-reason columns count first
completions. `tok0`/`tok_max` = zero-count and maximum of `num_output_tokens` in
`display_predictions.json`. `len_acc` = scored-correct / length-stop rows.
`acc` = mean `omni_math_accuracy` over 1,000 rows. Machine-readable copy with
exact per-file URLs, GCS generations, byte sizes, and SHA-256:
`reap/24_omni_math_run_ledger.json` and `reap/24_omni_math_analysis.json`.

| Run (omni_math:…) | max_tok | length | stop | endoftext | blank | len_acc | tok0 | tok_max | acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| amazon_nova-lite-v1:0 | 4096 | 4 | 0 | 996 | 0 | 0/4 | 0 | 4096 | .233 |
| amazon_nova-micro-v1:0 | 4096 | 3 | 0 | 997 | 0 | 0/3 | 0 | 4096 | .214 |
| amazon_nova-premier-v1:0 | 4096 | 0 | 0 | 1000 | 0 | — | 0 | 3757 | .350 |
| amazon_nova-pro-v1:0 | 4096 | 1 | 0 | 999 | 0 | 0/1 | 0 | 4096 | .242 |
| anthropic_claude-3-5-haiku-20241022 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 871 | .224 |
| anthropic_claude-3-5-sonnet-20241022 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 708 | .276 |
| anthropic_claude-3-7-sonnet-20250219 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 3874 | .330 |
| anthropic_claude-haiku-4-5-20251001 | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 12640 | .561 |
| anthropic_claude-opus-4-20250514 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 3523 | .511 |
| anthropic_claude-opus-4-…-thinking-10k | 14096 | 0 | 0 | 0 | 1000 | — | 37 | 1584 | .616 |
| anthropic_claude-sonnet-4-20250514 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 3456 | .512 |
| anthropic_claude-sonnet-4-…-thinking-10k | 14096 | 0 | 0 | 0 | 1000 | — | 46 | 1640 | .602 |
| anthropic_claude-sonnet-4-5-20250929 | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 10966 | .553 |
| deepseek-ai_deepseek-r1-0528 | 14096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .424 |
| deepseek-ai_deepseek-v3 | 4096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .403 |
| google_gemini-1.5-flash-002 | 4096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .304 |
| google_gemini-1.5-pro-002 | 4096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .364 |
| google_gemini-2.0-flash-001 | 4096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .459 |
| google_gemini-2.0-flash-lite-preview-02-05 | 4096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .374 |
| google_gemini-2.5-flash-lite | 14096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .480 |
| google_gemini-2.5-flash-preview-04-17 | 14096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .385 |
| google_gemini-2.5-pro-preview-03-25 | 14096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .416 |
| **google_gemini-3-pro-preview** | 14096 | **392** | 608 | 0 | 0 | 17/392 | 1000 | 0 | .555 |
| ibm_granite-3.3-8b-instruct | 4096 | 42 | 958 | 0 | 0 | 1/42 | 0 | 4096 | .176 |
| ibm_granite-4.0-h-small | 14096 | 1 | 990 | 0 | 9 | 0/1 | 0 | 14096 | .296 |
| ibm_granite-4.0-micro | 14096 | 6 | 972 | 0 | 22 | 0/6 | 0 | 14096 | .209 |
| meta_llama-3.1-405b-instruct-turbo | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 4096 | .249 |
| meta_llama-3.1-70b-instruct-turbo | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 4096 | .210 |
| meta_llama-3.1-8b-instruct-turbo | **scenario_state.json 404** | | | | | | 0 | 4096 | .137 |
| meta_llama-4-maverick-17b-128e-instruct-fp8 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 2512 | .422 |
| meta_llama-4-scout-17b-16e-instruct | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 4096 | .373 |
| mistralai_mistral-7b-instruct-v0.3 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 4096 | .072 |
| mistralai_mistral-large-2411 | 4096 | 1 | 0 | 999 | 0 | 0/1 | 0 | 4096 | .281 |
| mistralai_mistral-small-2503 | 4096 | 0 | 0 | 1000 | 0 | — | 0 | 4096 | .248 |
| mistralai_mixtral-8x22b-instruct-v0.1 | **both files 404** | | | | | | | | |
| mistralai_mixtral-8x7b-instruct-v0.1 | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 4096 | .105 |
| moonshotai_kimi-k2-instruct | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 14096 | .654 |
| openai_gpt-4.1-2025-04-14 | 4096 | **150** | 850 | 0 | 0 | 15/150 | 0 | 4096 | .471 |
| openai_gpt-4.1-mini-2025-04-14 | 4096 | **168** | 832 | 0 | 0 | 26/168 | 0 | 4096 | .491 |
| openai_gpt-4.1-nano-2025-04-14 | 4096 | 60 | 940 | 0 | 0 | 3/60 | 0 | 4096 | .367 |
| openai_gpt-4o-2024-11-20 | 4096 | 0 | 1000 | 0 | 0 | — | 0 | 2856 | .293 |
| openai_gpt-4o-mini-2024-07-18 | 4096 | 13 | 987 | 0 | 0 | 1/13 | 0 | 4096 | .280 |
| openai_gpt-5-2025-08-07 | 14096 | 0 | 0 | 0 | 1000 | — | 236 | 921 | .647 |
| openai_gpt-5-mini-2025-08-07 | 14096 | 0 | 0 | 0 | 1000 | — | 45 | 1331 | .722 |
| openai_gpt-5-nano-2025-08-07 | 14096 | 0 | 0 | 0 | 1000 | — | 326 | 1254 | .546 |
| openai_gpt-5.1-2025-11-13 | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 5913 | .464 |
| openai_gpt-oss-120b | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 14096 | .688 |
| openai_gpt-oss-20b | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 14096 | .565 |
| **openai_o3-2025-04-16** | **24096** | **106** | 894 | 0 | 0 | 0/106 | 107 | 1450 | .714 |
| openai_o4-mini-2025-04-16 | 24096 | 3 | 997 | 0 | 0 | 0/3 | 3 | 1363 | .720 |
| qwen_qwen2.5-72b-instruct-turbo | **scenario_state.json 404** | | | | | | 0 | 4096 | .330 |
| qwen_qwen2.5-7b-instruct-turbo | 4096 | 0 | 0 | 0 | 1000 | — | 0 | 4096 | .294 |
| qwen_qwen3-235b-a22b-fp8-tput | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 14096 | .548 |
| qwen_qwen3-235b-a22b-instruct-2507-fp8 | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 14096 | .718 |
| qwen_qwen3-next-80b-a3b-thinking | 14096 | 0 | 0 | 0 | 1000 | — | 1000 | 0 | .467 |
| writer_palmyra-fin | 4096 | 0 | 1000 | 0 | 0 | — | 0 | 4095 | .295 |
| writer_palmyra-med | 14096 | 0 | 1000 | 0 | 0 | — | 1000 | 0 | .156 |
| writer_palmyra-x-004 | 4096 | 15 | 985 | 0 | 0 | 1/15 | 0 | 4096 | .320 |
| writer_palmyra-x5 | 14096 | 0 | 1000 | 0 | 0 | — | 1000 | 0 | .414 |
| **xai_grok-3-beta** | 4096 | **495** | 503 | 0 | 2 | 122/495 | 0 | 4096 | .464 |
| **xai_grok-3-mini-beta** | 4096 | **548** | 452 | 0 | 0 | 2/548 | 499 | 980 | .318 |
| **xai_grok-4-0709** | 14096 | **312** | 688 | 0 | 0 | 1/312 | 304 | 471 | .603 |
| zai-org_glm-4.5-air-fp8 | 14096 | 0 | 0 | 0 | 1000 | — | 0 | 14096 | .391 |
| num_output_tokens=2048,…olmo-2-0325-32b-instruct | 2048 | 0 | 0 | 0 | 1000 | — | 0 | 2048 | .161 |
| num_output_tokens=2048,…olmo-2-1124-13b-instruct | 2048 | 0 | 0 | 0 | 1000 | — | 0 | 2048 | .156 |
| num_output_tokens=2048,…olmo-2-1124-7b-instruct | 2048 | 0 | 0 | 0 | 1000 | — | 0 | 2048 | .116 |
| num_output_tokens=2048,…olmoe-1b-7b-0125-instruct | 2048 | 0 | 0 | 0 | 1000 | — | 0 | 2048 | .093 |
| num_output_tokens=2048,…marin-8b-instruct | 2048 | 0 | 0 | 0 | 1000 | — | 0 | 2048 | .160 |

Additional per-run facts recorded in `reap/24_omni_math_analysis.json`:

- `prompt_truncated=true` appears on exactly **1 of 1,000** rows in 8 runs (the
  three xai runs and the five 2,048-cap runs) and nowhere else — input-side
  trimming, unrelated to output censoring, consistent with reap/23 correction 4.
- `result.success=false` rows exist in 4 runs (claude-opus-4-thinking-10k: 37,
  claude-sonnet-4-thinking-10k: 46, gemini-1.5-flash: 1, gemini-2.5-flash-preview:
  1) — archived failed requests, matching their `num_output_tokens=0` counts.
- The five `num_output_tokens=2048` olmo/marin runs report a hard ceiling of
  exactly 2,048 reported tokens with **zero** length labels (all-blank finish
  reasons) — capped runs whose censoring is invisible in the labels.

## What this changes for the project

1. **Do not repeat "omni_math has fewer models and no censoring."** The safe
   sentence is: *"The v1.15.0 archive evaluates the same 68 models on omni_math as
   on GPQA; 18 of the 65 retrievable runs record explicit length-stops — 2,320
   rows in total, up to 54.8% of a single model's run — and 41 runs have blank
   finish labels, so their censoring is unknown."*
2. omni_math is the **richer** censoring archive, not the cleaner one: more
   labeled length-stops (2,320 vs 42), plaintext responses (strict regrade
   possible), per-item LLM-judged accuracy — but four different requested caps
   across models and the same blank-label and token-field defects as GPQA.
3. The mixed caps (2,048 / 4,096 / 14,096 / 24,096) mean any cross-model omni_math
   accuracy comparison silently compares different censoring regimes — an
   independent, citable instance of the paper's core complaint.
4. The 8.1% nonzero at-length accuracy shows the "length-stop ⇒ scored wrong"
   pattern is grader-dependent: judge-graded omni_math occasionally rescues a
   truncated response, strict-extraction GPQA CoT does not. Keep the claims
   separate per grader, exactly as reap/20's three-claim hierarchy requires.

## Exact evidence locations

- Release manifest (pinned, matches the byte-identical pin in
  `observational/benchmark_sources_manifest.json`):
  https://storage.googleapis.com/crfm-helm-public/capabilities/benchmark_output/releases/v1.15.0/runs_to_run_suites.json
  — generation `1781127687715219`, 29,389 bytes, SHA-256
  `92635e3d7973b8b3602d928c831957cc69a6669758e7620a123c3ecc5c02cee2`. It maps each
  of the 68 omni_math run keys to its run suite (v1.0.0 … v1.15.0).
- Per-run objects follow
  `https://storage.googleapis.com/crfm-helm-public/capabilities/benchmark_output/runs/<suite>/<run_key>/scenario_state.json`
  (and `display_predictions.json`) — the same pattern as the GPQA entries in
  `observational/benchmark_sources_manifest.json` with the gpqa run key replaced.
  **Every file's exact URL, GCS generation, byte size, and SHA-256** (132 files
  retrieved; 4 objects 404) is recorded in `reap/24_omni_math_run_ledger.json`.
  Byte sizes and hashes are of the served response body: GCS decompressive
  transcoding applies to gzip-stored objects (e.g. the gemini-3-pro-preview
  scenario_state stores 857,809 bytes but serves 7,218,175), so a verifier must
  hash the decoded download, not the stored object. The generation pins the
  immutable stored object either way. All derived counts were identical across
  two independent full downloads on 2026-08-24.
- Per-run derived counts: `reap/24_omni_math_analysis.json` (written by the
  streaming analyzer; counts and hashes only).
- Analyzer provenance: fields read were `request.max_tokens`,
  `result.completions[0].finish_reason.reason`, `result.success`,
  `prompt_truncated`, `instance.id` from `scenario_state.json`, and
  `stats.num_output_tokens`, `stats.omni_math_accuracy`, `predicted_text`
  emptiness from `display_predictions.json`. `finish_reason` semantics per HELM
  `request_state.py` as pinned in reap/23 correction 4.

## Caveats and handling rules

- These are exploratory public archives, not REAP confirmatory observations.
  Nothing here enters any confirmatory estimate or denominator.
- `omni_math_accuracy` is HELM's source-native, LLM-annotated grade — not REAP's
  strict final-answer-marker grader. The 189/2,320 at-length correct count is a
  property of that grader.
- Blank finish labels mean **unknown**, not "no truncation": 41 runs, including
  every Anthropic, Meta, DeepSeek, GPT-5-family, qwen (except 2.5-72b, 404) and
  glm run, cannot be assessed for censoring from the public archive.
- Reported `num_output_tokens` values clipping exactly at the requested cap
  (llama, mistral-7b, gpt-oss, kimi, qwen3, glm, olmo at 2,048 …) suggest those
  runs also hit their allowance without a `length` label, but that is an
  **inference from clustering**, exactly the MathArena situation — never convert
  it into an observed termination reason.
- Instance downsampling: 1,000 evaluated instance IDs per run (identical set
  across the runs checked), out of 4,428 Omni-MATH source items
  (`capabilities/omni_math.jsonl`); per the HELM Capabilities blog, Omni-MATH is
  downsampled to 1,000 in the leaderboard runs.
- No question text, response text, or prompt text is reproduced in this document
  or the committed JSONs. Omni-MATH is Apache-2.0 (not access-restricted), but the
  audit works with counts, IDs, and hashes only.
- **No provider, smoke, or confirmatory calls were made during this audit.**
