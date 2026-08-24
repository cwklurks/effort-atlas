# Benchmark table for Chirag

**Prepared:** 2026-08-21

**Purpose:** Meeting material for choosing the next benchmark set and analysis.

**Status:** Exploratory planning only. This document freezes no experiment choice and authorizes no provider call.

## The one-sentence takeaway

The public archives let us compare models question by question, but they do not all tell us whether a response stopped because it ran out of tokens, and their token counts cannot be treated as one common unit across providers.

## Quick definitions

- **MathArena:** A public archive of model attempts on recent math competitions.
- **HMMT:** The Harvard-MIT Mathematics Tournament.
- **AIME:** The American Invitational Mathematics Examination.
- **HELM:** Stanford's Holistic Evaluation of Language Models project.
- **GPQA:** A difficult graduate-level science question set.
- **Per-question statistics:** For each question, we can see whether a model was marked correct and, when available, how much output it used.
- **Observed token exhaustion:** The archive explicitly says the response stopped because it reached the output limit.
- **Inferred token exhaustion:** The response ended at or near a repeated round-number maximum, but the archive does not provide a stop label.

## Comparison table

| Public archive | Domain and questions | Per-question correctness | Output amount | Can we identify token exhaustion? | What it can honestly support | Main limitation | Source |
|---|---|---|---|---|---|---|---|
| **MathArena HMMT 2025** | Competition math, **30** questions | **Yes.** The exact-source audit found 64 models, all 30 questions, and four attempts per model-question pair. | **Yes, with quality checks.** The archive reports `output_tokens`; 120 zero values and 7 negative values must be flagged. | **No confirmed label.** Requested caps and finish reasons are not published. Near-cap rows can only be called inferred. | Question-level accuracy and route-specific output comparisons after quality checks. This is the cleanest audited math archive for question IDs and source text. | Models used several prompt wrappers, so matching question IDs do not guarantee identical prompt bytes. | [Pinned HMMT 2025 outputs](https://huggingface.co/datasets/MathArena/hmmt_feb_2025_outputs/tree/bac3e9b78124aa8811c4aae3d590f03b467643f4) |
| **MathArena HMMT 2026** | Competition math, **33 MathArena items** | **Yes.** Twenty-nine of 30 archived models cover all 33 items; Qwen3.5-4B covers 22. | **Yes, with quality checks.** One row has an unusable zero-token value. | **No confirmed label.** Requested caps and finish reasons are not published. | Question-level accuracy and route-specific output comparisons after the listed source and missingness issues are handled. | Item 25 has two text versions in the archive. Items 31 to 33 are valid MathArena source items, but their status as official HMMT individual-round problems is unverified. | [Pinned HMMT 2026 outputs](https://huggingface.co/datasets/MathArena/hmmt_feb_2026_outputs/tree/1e888131281fc0fca080fd220e8bc6d830937564) |
| **MathArena AIME 2026** | Competition math, **30** questions | **Yes in the archive.** | **Yes in the archive.** | **No confirmed label.** Requested caps and finish reasons are not published. | A larger descriptive math comparison and response-length priors. | The exact question-source, prompt, and missing-cell audit has not yet been extended to this archive. | [Pinned AIME 2026 outputs](https://huggingface.co/datasets/MathArena/aime_2026_outputs/tree/76ce7a0aa77f0710f3cfb818ff1193e6dea56210) |
| **MathArena BRUMO 2025** | Competition math, **30** questions | **Yes in the archive.** | **Yes in the archive.** | **No confirmed label.** Requested caps and finish reasons are not published. | Another descriptive math comparison and response-length priors. | The exact-source audit has not yet been extended to this archive. Its dataset card also has a naming inconsistency, so the pinned revision must be cited. | [Pinned BRUMO 2025 outputs](https://huggingface.co/datasets/MathArena/brumo_2025_outputs/tree/12ca8f115d73526d25a36b72e4bfefb18b76d6be) |
| **HELM GPQA** | Graduate-level science, **446 evaluated questions** from 448 source rows | **Yes.** Gemini 3 Pro Preview, Claude Haiku 4.5, and GPT-5.1 cover the same 446 test IDs. The other two source rows are fixed training examples, not missing results. | **Not comparable across the three providers.** Gemini is all zero in the archived token field; Claude ranges from 235 to 4,707; GPT ranges from 5 to 7. | **Only for Gemini.** Every request used a 14,096-token cap. Gemini has 42 `length` and 404 `stop` labels. Claude and GPT have blank finish labels. | Question-level accuracy across a non-math domain. Gemini also gives a clean example of observed length stops: all 42 length-stopped rows were scored wrong. | The provider token fields use visibly different accounting systems, and the archived response text cannot be regraded with REAP's strict final-answer rule. | [HELM Capabilities v1.15.0](https://crfm.stanford.edu/helm/capabilities/latest/) |

The four MathArena archives contain **123 competition-math questions** in total. HELM evaluates **446 GPQA science questions**. These numbers should not be added and presented as one sample because the domains, models, prompts, grades, and token measurements differ.

## What this answers from the meeting

1. **Can we tell whether each model got each question right?** Yes. Both MathArena and HELM publish a grade for each archived question attempt. These are the benchmark publishers' grades, not yet REAP's stricter grader.

2. **Can we see how much output each response used?** Usually, but only within a clearly defined route and accounting system. The HELM provider fields cannot be put on one fair cross-provider token axis.

3. **Can we tell whether the response ran out of tokens?** Only for the HELM Gemini run. MathArena has no requested-cap or finish-reason field, so its near-cap classifications are inferred. HELM Claude and GPT have blank stop labels.

4. **Can we say a response was wrong because it ran out of tokens?** No. A stop label tells us that a response was cut off, but it does not reveal the answer that would have appeared with more room. That causal question requires the controlled effort-by-allowance experiment.

5. **Can we compare Model A and Model B on the same questions?** Yes for accuracy after verifying shared questions and prompt versions. A fair token-efficiency comparison also requires comparable token accounting. The new controlled experiment is the cleanest way to obtain that.

## A two-minute explanation

> I built the benchmark table you asked for. The good news is that all five public archives let us see whether a model got each question right. The four MathArena sets give us 123 math questions and reported output-token counts. HELM gives us 446 science questions answered by the same three archived models.
>
> The main limitation is that the archives do not measure token exhaustion in the same way. MathArena does not publish the requested cap or the reason a response stopped, so a response near a round-number maximum can only suggest truncation. HELM is stronger for one model: Gemini has 42 responses explicitly labeled as stopping for length, and all 42 were scored wrong. But HELM's token fields are not comparable across its three providers.
>
> So the public data can show that the pattern exists, help us choose questions, and give us response-length estimates for planning. It cannot tell us what a particular cut-off response would have answered with more room, and it cannot yet support one honest cross-provider token-efficiency curve. That is why the controlled experiment still matters: we run the same questions with fixed prompts, known output limits, recorded stop reasons, and repeated samples.

## If the observational result comes up

Say:

> In the current exploratory comparison, 427 MathArena generations ended at or near an apparent cap. After combining the predeclared MathArena comparison with the observed HELM Gemini group, 15 of 17 selected model-dataset groups had zero accuracy among inferred cap rows or observed length stops. The other two were below 12 percent. I treat MathArena's cap status as inferred and HELM Gemini's as observed.

This wording follows the current recomputation. An older line in `observational/RESULTS.md` says 16 of 17 and should not be repeated until that dated record is reconciled.

## Decisions to ask Chirag for

1. **Public-data scope:** Should the descriptive section use all 123 MathArena questions, while the controlled experiment uses a smaller fixed set?
2. **HMMT 2026 item 25:** Should historical cross-model comparisons exclude this item or report its two text versions separately?
3. **HMMT 2026 items 31 to 33:** Is it acceptable to include them as MathArena HMMT-2026 source items while clearly stating that their official-round provenance is unverified?
4. **Primary result:** Should the within-model effort-by-allowance interaction remain primary, with matched-performance comparisons between models kept secondary and directional?
5. **Power analysis:** Should we rerun it using the verified question counts and archived response-length distributions before fixing caps and repeat counts?

## Recommended position

Use the public archives as transparent descriptive evidence and planning data. Use the controlled experiment for causal claims. Keep token comparisons within a pinned route unless the accounting units are proved comparable. For the cleanest first controlled math panel, start from HMMT 2025, then add HMMT 2026 only under an explicit rule for item 25 and items 31 to 33.

## Local evidence behind this page

- `reap/20_BENCHMARK_COMPARISON_2026-08-18.md`
- `reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md`
- `observational/benchmark_sources_manifest.json`
- `observational/benchmark_question_capabilities_summary.json`
