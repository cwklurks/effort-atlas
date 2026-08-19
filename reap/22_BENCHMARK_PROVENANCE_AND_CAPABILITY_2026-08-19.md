# What the public benchmark files can actually tell us

**Date:** 2026-08-19  
**Status:** Exploratory source audit. This document freezes no experiment choice
and authorizes no provider, smoke, or confirmatory call.

## Bottom line

The public files can answer Connor's first post-meeting question at the
**question-by-model** level, but with important limits:

- MathArena records whether each archived attempt was scored correct and how many
  output tokens it reports. It does **not** record the requested output allowance
  or why the response stopped.
- HELM records correctness for the same 446 GPQA test questions across three
  archived models. It also records a requested allowance of 14,096 tokens, but
  only the Gemini run has useful stop labels.
- The token fields are not one shared unit across the HELM providers. They cannot
  support a fair cross-model token-efficiency curve.
- Neither archive can tell us that a particular response was wrong *because* it
  ran out of tokens. The controlled effort-by-allowance experiment is still needed
  for that causal question.

The safe working question remains:

> On the same benchmark questions and across native reasoning-effort settings,
> at accuracy levels both models actually attain, how many comparably measured
> output tokens does each use, and when the output allowance is raised, how do
> scored accuracy and unanswered length stops change?

In simple language: when two reasoning models answer the same questions, how much
output does each use at accuracy levels both can actually reach, and what changes
when they get more room to finish?

## Direct answers to the questions from the meeting

| Meeting question | MathArena HMMT | HELM GPQA | Safe answer |
|---|---|---|---|
| Can we tell whether a model got each question right? | Yes, using MathArena's archived grade | Yes, using HELM's archived `chain_of_thought_correctness` grade | **Yes**, but these are source-native grades, not REAP's stricter final-answer grader |
| Can we measure output for each question? | `output_tokens` is present, with quality problems described below | Provider-specific token fields are present | **Yes within a pinned route after quality checks**; not as a universal cross-provider unit |
| Can we tell whether a response exhausted its allowance? | No requested allowance or finish reason is published | Gemini: yes; Claude and GPT: no because labels are blank | **Gemini labels all 446 rows: 42 exhausted the allowance and 404 stopped normally** |
| Can we say the cap caused a wrong answer? | No | No | **No.** A stop label describes what happened, not the answer that would have appeared with more room |
| Can we compare two models on the same questions? | Yes after checking the exact shared IDs, prompt variants, and missing rows | Yes on the same 446 test IDs | **Descriptively yes**; a token-efficiency claim additionally needs comparable measurement |

## The verified source sets

### MathArena HMMT 2025

- The pinned source has 30 question IDs.
- The pinned output archive has 7,680 attempts: 64 models, all 30 questions, and
  exactly four attempts for every model-question pair.
- Source and output question IDs, question text, and gold answers match for all 30
  questions.
- Matching a question ID does not mean every model received identical serialized
  prompt bytes. Each question has three or four `user_message` variants across the
  archived models.
- The output-token field needs quality flags: one model has 120 zero-token rows,
  and seven other rows have negative values. These rows cannot silently enter a
  token-efficiency estimate.

### MathArena HMMT 2026

- The pinned source has 33 MathArena items. Call them **MathArena HMMT-2026
  items**, not 33 official individual-round problems: the official-round source
  of items 31–33 remains unverified.
- The pinned output archive has 3,651 attempts from 30 models. Twenty-nine models
  cover all 33 IDs. Qwen3.5-4B covers 22 and is missing 11.
- All 33 source IDs and gold answers appear in the archive.
- **Question 25 has a material text mismatch.** Of its 108 archived attempts, 106
  attempts from 28 models use a different question-text fingerprint from the
  current pinned source. Only the two GLM 5.2 attempts match the source text. The
  gold answer still matches.
- Therefore the 33 IDs cannot be described as one identical-question panel until
  question 25 is resolved or excluded by an explicit rule.
- One output row reports zero output tokens. It requires a quality flag.

### HELM GPQA

- The official GPQA source archive contains 448 `gpqa_main` rows.
- HELM's pinned scenario code assigns source indices 105 and 339 to its training
  split. The no-few-shot benchmark runs evaluate the remaining 446 test rows.
  Therefore 446 is a deliberate evaluation split, not evidence that two output
  rows went missing.
- The Gemini 3 Pro Preview, Claude Haiku 4.5, and GPT-5.1 archives contain exactly
  the same 446 test IDs with one completion for each model-question pair.
- Every request records `max_tokens=14096`, temperature 1, and top-p 1.
- Gemini records 404 `stop` labels and 42 `length` labels. Claude and GPT have 446
  blank finish labels each.
- All three runs contain per-question correctness. Their archived output-token
  fields are plainly different measurement systems: Gemini is zero throughout,
  Claude ranges from 235 to 4,707, and GPT ranges from 5 to 7.
- The serialized request prompt hashes differ across all 446 shared questions for
  every pair of models. The source questions are shared; the exact model-facing
  wrapper bytes are not.
- The archived predicted text is not available as normal plaintext for a strict
  `Final answer:` regrade. Keep HELM's source-native grade labeled as such.

## Coverage at a glance

| Source | Source question IDs | Archived/evaluated IDs | Exact source-text status | Model coverage |
|---|---:|---:|---|---|
| HMMT 2025 | 30 | 30 | 30/30 match | 64/64 models complete |
| HMMT 2026 | 33 | 33 | 32 match; question 25 is mixed | 29/30 models complete; one has 22/33 |
| GPQA / HELM | 448 | 446 | Two fixed source rows are HELM train examples | Three archived models share all 446 test IDs |

These counts describe **ID coverage**, not automatic eligibility for a pooled
analysis. Prompt bytes, grade rules, termination fields, and token meanings still
matter.

## What the reproducible capability table records

The companion question-level table is deliberately sanitized. It records one row
per benchmark, archived model, and question, including:

- source and archived question identity;
- number of archived attempts and source-native correct count;
- whether output-token data are present and pass the required finite, strictly
  positive checks;
- requested allowance and finish-label availability where the source provides it;
- source/output question-text fingerprint agreement without exposing question
  text;
- serialized prompt fingerprint agreement without exposing prompt text;
- whether strict REAP final-answer regrading is possible.

It contains 4,248 benchmark-model-question cells, including 11 explicit archive
gaps for Qwen3.5-4B rather than silently dropping them. It does not contain GPQA
question text, answer choices, gold answers, or plaintext prompts. It never
converts a missing finish label into a normal stop and never turns MathArena's
length clustering into a provider-observed termination reason.

## Decisions this audit changes

1. **HMMT 2025 is the cleanest archived math panel for ID and source-text
   matching.** Prompt variants and token-quality flags still prevent a casual
   cross-model efficiency claim.
2. **HMMT 2026 needs two separate decisions.** Resolve or exclude question 25's
   text mismatch, and separately decide whether items 31–33 belong in the planned
   scope despite unresolved official-round provenance.
3. **HELM's 446 rows are usable question-level outcomes, not 448 rows with two
   unexplained failures.** The two omitted source rows are fixed training examples.
4. **Only HELM Gemini supports the observed statement “this archived response
   stopped for length.”** MathArena remains inferred and Claude/GPT remain unknown.
5. **The main matched-performance token question still requires new controlled
   data.** Existing token fields cannot be placed on one honest cross-provider
   y-axis.

## Recommended next steps

1. Have Connor and Chirag choose the exact question set, with question 25 and
   HMMT-2026 items 31–33 listed explicitly rather than hidden in a count.
2. Pin and test the upstream symbolic scorer on the selected gold-answer schemas.
3. Re-run power analysis using the verified question count and real archived
   response-length distribution before fixing caps and replicates.
4. Select the smallest model portfolio that supplies a useful within-route effort
   intervention; keep cross-provider token plots directional unless measurement
   equivalence is proved.
5. Finish the zero-retry runner, receipt-linked budget gate, and frozen manifest
   before any human smoke call.

## Caveats and handling rules

- The files checked here are exploratory public archives. They are not REAP
  confirmatory observations.
- Archived correctness is the benchmark publisher's grade. It is not evidence that
  REAP's explicit final-answer-marker grader would produce the same result.
- A token count is useful only with its exact route and accounting definition.
  “Output token” does not automatically mean visible text, hidden reasoning, billed
  output, or a unit comparable between providers.
- GPQA source text should not be committed or copied into a general Linux handoff.
  The acquisition verifier uses hashes, IDs, counts, and sanitized derived rows.
- The historical `observational/RESULTS.md` says 16 of 17 selected groups had zero
  at-cap accuracy. The current recomputation documented in
  `reap/20_BENCHMARK_COMPARISON_2026-08-18.md` is **15 of 17**. Do not repeat the
  historical number without reconciling that dated record.
- No provider, smoke, or confirmatory call was made during this audit.

## Exact evidence locations

The machine-readable source of truth is
`observational/benchmark_sources_manifest.json`. It pins immutable revisions or
object generations, expected byte sizes, SHA-256 values, roles, and redistribution
rules. The acquisition tool verifies those exact bytes before building the
sanitized question-level table.

Primary source identities used here:

- MathArena HMMT 2025 source revision
  `6fdc4277120810ff75aa22d2d5489b91f7a262a1` and output revision
  `bac3e9b78124aa8811c4aae3d590f03b467643f4`.
- MathArena HMMT 2026 source revision
  `02fba4f74d8e68e73e66a02d540fd979c05c274c` and output revision
  `1e888131281fc0fca080fd220e8bc6d830937564`.
- HELM Capabilities release `v1.15.0`, with exact GCS object generations recorded
  in the manifest.
- HELM GPQA scenario source commit
  `bfa36d33e8b98b36b5f3a8c7d52b9a1b7162eae5`, which pins GPQA revision
  `90b8e5be2b1d3d2dbfe016cdab47981150600c4a` and train indices 339 and 105.
- Original GPQA repository archive commit
  `d46dc8d5e01b40bcde0bed6bee68a5de953a58f8`.
