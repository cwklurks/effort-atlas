# Methodology-review synthesis

**Date:** 2026-08-18
**Status:** Non-frozen planning record. This document does not authorize a
provider, smoke, or confirmatory call.

## Recommended research question

> On the same benchmark questions and across native reasoning-effort settings,
> at accuracy levels both models actually attain, how many comparably measured
> output tokens does each use, and when the output allowance is raised, how do
> scored accuracy and unanswered length stops change?

In simpler meeting language:

> When two reasoning models answer the same questions, how much output does each
> use at accuracy levels both can actually reach, and what changes when they get
> more room to finish?

The second sentence is easier to say aloud. The first is the precise version for
the design record. Neither promises that a truncated response would have become
correct.

## Review batch and provenance

The review set contains three responses from each of three model families: Claude
Fable 5, Grok 4.6, and Gemini 3.1 Pro Preview. Seven full responses were available
to this synthesis; two earlier responses are represented only by preceding-session
summaries. The findings below are a cross-review synthesis, not independently
auditable nine-way unanimity. This document preserves that synthesis and recorded
execution evidence, not the full proprietary response texts.

The retained prompt is
`reap/prompts/POST_MEETING_METHODOLOGY_REVIEW_PROMPT_2026-08-18.md`; its SHA-256 is
`e1bbc4714e5c3f74e9300b3b922f32aefc58748cafc98fa138aa958477eb688c`.

| Review lane | Recorded execution evidence | Cost treatment |
|---|---|---:|
| Fable, three total | `claude-fable-5`; first-party `claude.ai` Max subscription; no Anthropic API key; two added responses completed successfully | Regular subscription usage, not API credits |
| Grok 1 | `x-ai/grok-4.6-20260810`, xAI, receipt `gen-1787077791-e7MV8VrOMCGDx5btGcOF` | $0.033586 |
| Grok 2 | `x-ai/grok-4.6-20260810`, xAI, receipt `gen-1787078859-hX976iuJnPw3Q5kwLs9b` | $0.042184 |
| Grok 3 | `x-ai/grok-4.6-20260810`, xAI, receipt `gen-1787079041-nVsFZ4F2zFdwekcwZ8f4` | $0.026932 |
| Gemini 1 | `google/gemini-3.1-pro-preview-20260219`, Google, receipt `gen-1787079152-4RmfWjaBs4fhiMDnSbrs` | $0.045896 |
| Gemini 2 | same exact snapshot and provider, receipt `gen-1787079212-4S734ui1V8It9IeesFDv` | $0.044312 |
| Gemini 3 | same exact snapshot and provider, receipt `gen-1787079279-F99UN2VZj8reFSbrOaw6` | $0.046436 |

The five newly authorized OpenRouter calls cost **$0.205760** against a new
$0.30 ceiling. Including the earlier Grok review, all OpenRouter methodology
reviews cost **$0.239346**. Requests used ZDR-only routing, disabled fallbacks,
required parameter support, explicit `max_tokens`, and zero generation retries.
Two free receipt lookups were repeated after temporary publication-race 404s;
no generation was resubmitted.

These were development methodology reviews, not research observations. They are
not included in any study denominator.

## Cross-review findings

| Claim | Consensus consequence |
|---|---|
| Censoring does not reveal missing correctness | Never create a “censoring-adjusted accuracy.” A length stop says how the response ended, not what answer it would have produced. |
| Matched-performance comparisons are conditional | Compare token use only at accuracy levels both models attain in the tested grid. Otherwise report `not_estimable`; do not extrapolate. |
| Found data cannot identify the headline frontier | MathArena and HELM motivate the mechanism and support limited descriptive analyses. They do not provide the designed effort-by-cap curve required for `T_m(p)`. |
| A controlled experiment is necessary | Use common questions, known caps, captured termination, independent replicates, and frozen grading. |
| Large-cap runs are separate observations | They estimate performance under a more generous regime. They are not continuations of, or imputations for, the smaller-cap response. |
| MathArena cap status is inferred | Repeated round-number maxima support an `inferred` label only. They are not provider-reported length stops. |
| Current HELM token fields are not cross-provider comparable | Gemini zeros, Claude hundreds, and GPT single digits cannot share a token-efficiency axis. |
| Native tokens are not automatically interchangeable | Different tokenizers and hidden-reasoning accounting make an unqualified cross-provider token ratio unsafe. |
| Questions are the top-level unit | Average attempts within each question, then weight questions equally. Resampling and uncertainty must preserve question-level pairing. |

## Outcomes that must remain separate

For every fully collected response, preserve three separate facts:

1. **Grade:** whether the configured explicit final answer is correct.
2. **Termination:** whether the response ended normally, hit a length allowance,
   or has an unknown/provider-specific termination.
3. **Length:** the observed or censored output amount under the preregistered
   output measure.

A valid length-stopped response is not automatically wrong. If it already contains
the complete configured final-answer line, it retains its grader result. A
**token-starved/no-answer row** is specifically a length stop with
`extracted_answer_present=false`. System, route, or accounting failures are
missing attempts and must be reported through the prespecified missingness
analysis rather than silently scored wrong.

## Technical formulation

For model `m`, tested regime `g = (effort, cap)`, question `q`, and replicate `r`,
let `V=1` mark a valid collected and accounted attempt, `C` its strict grade, and
`Y` the preregistered output-use measure. Define:

```text
A_m(g) = mean over questions of [correct valid attempts / valid attempts]
B_m(g) = mean over questions of [mean Y over valid attempts]
```

Call `Y` billed output tokens only where a complete per-response billing join is
proved. Otherwise use the frozen route-native measure and do not calculate a
cross-route token contrast unless the measures are commensurate.

No-answer attempts remain in the accuracy denominator. Define the discrete
operational frontier:

```text
T_m(p) = minimum B_m(g) among tested regimes with A_m(g) >= p
```

Report `T_A(p) - T_B(p)` or `T_A(p) / T_B(p)` only for preregistered `p` in
the overlap of empirically attained accuracy ranges and only when `Y` is
commensurate across the compared models. Otherwise report `not_estimable`.

Separately report the all-length-stop rate and the unanswered-length-stop rate.
Use survival or restricted-mean analysis for response length only through a
preregistered common-support horizon. Do not use it to move the accuracy axis.

The existing REAP effort slope and effort-by-cap interaction remain the direct
mechanism estimands. The new matched-performance frontier is an additional
operational comparison unless Connor and Chirag explicitly change the paper’s
primary target.

## Where the reviewers differed

- Five of the seven retained full responses replaced both candidate questions;
  two kept and tightened Q2. Their scientific recommendations were otherwise
  aligned.
- “Adjusted” was used to mean large-cap reference points, endpoint bounds,
  censored-length analysis, or combinations. Because those are different
  analyses, the word should be removed from the headline figure. Show as-scored
  operating points, observed large-cap points, and censored-length results
  separately.
- Some reviewers proposed monotone or isotonic interpolation. That would impose
  monotonicity where negative scaling is a possible result. Use a discrete
  empirical frontier unless a particular interpolation is preregistered.
- Suggested cross-provider units included native tokens, dollars, characters,
  and reference-tokenizer counts. These measure different things and must not be
  presented as interchangeable solutions.

## Repeated suggestions we should not adopt as written

- Character counts or a reference tokenizer describe visible text; they do not
  recover hidden reasoning or billed computation.
- Dollars measure route-specific economic cost under current prices, not intrinsic
  reasoning efficiency.
- An unrestricted Kaplan-Meier mean “to infinity” is not identified when the tail
  remains censored. Use restricted means on common support or empirical large-cap
  lengths.
- Dropping every question with any model-system failure creates a selected
  complete-case sample. Preserve missingness and apply the frozen sensitivity
  analysis instead.
- Treating only terminator-bearing responses as valid would remove the principal
  starvation outcome from the denominator.

## Decisions still required from Connor and Chirag

1. Is the primary paper target still the within-model effort-by-cap interaction,
   with matched-performance model comparison as an additional estimand?
2. Which planned model comparisons have a commensurate primary output measure?
   If none do, should cross-provider plots remain directional and separate?
3. Should `T_m(p)` use the discrete minimum among tested regimes, or a specific
   preregistered interpolation model?
4. Should the presentation use large-cap reference points plus a separate
   restricted-mean length analysis in place of an “adjusted” curve?
5. Which questions, effort levels, caps, and replicates provide adequate shared
   coverage, likely accuracy overlap, and a useful large-cap reference?
6. Does the found-data analysis belong in the main paper as motivation or in the
   supporting material?

## Recommended decision now

Adopt the question at the top of this document provisionally. Keep the existing
effort-by-cap interaction primary until Connor and Chirag explicitly agree to
replace it. Treat cross-provider matched-performance comparisons as directional
unless the model-pair eligibility audit establishes a commensurate output unit.
