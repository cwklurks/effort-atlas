# Chirag meeting decision notes

**Meeting date:** ____________________

**Start time:** ______________________

**Next meeting:** ____________________

## Four outcomes

| Decision | Agreed answer | Owner | Due date |
|---|---|---|---|
| Does the benchmark table satisfy the assignment? |  |  |  |
| Which archives can support the censoring analysis? |  |  |  |
| How should the adjusted and unadjusted efficiency graph be defined? |  |  |  |
| What exact artifact should Connor build next? |  |  |  |

## One-sentence problem statement

Proposed wording:

> When two models reach similar accuracy on the same questions, how many output tokens does each need, and how does accounting for responses cut off by a token limit change that comparison?

Chirag's edits:

Final wording:

## Corrections acknowledged

- [ ] HELM means Stanford's Holistic Evaluation of Language Models; this slice is GPQA chain-of-thought.
- [ ] MathArena publishes question and prompt fields but no requested cap or finish reason.
- [ ] HELM uses a 14,096-token cap in the three reviewed runs.
- [ ] Only HELM Gemini has usable finish labels: 42 `length`, 404 `stop`.
- [ ] We can observe wrong and length-stopped; causal wording requires a cap intervention.

## Benchmark eligibility

| Archive | Include now? | Role | Main limitation |
|---|---|---|---|
| MathArena HMMT 2025 |  |  |  |
| MathArena HMMT 2026 |  |  |  |
| MathArena AIME 2026 |  |  |  |
| MathArena BRUMO 2025 |  |  |  |
| HELM GPQA |  |  |  |

## HMMT rules

- Items 31 to 33: Chirag previously approved their experimental scope; provenance caveat remains.
- Item 25 historical text-version rule:
- Can MathArena cohorts be pooled for the length estimator?
- AIME and BRUMO audit needed before use?

## Censoring estimator

- Definition of unadjusted length:
- Definition of censoring-adjusted length:
- Kaplan-Meier or other estimator:
- Restricted-mean horizon:
- If estimating beyond the largest observed cap, tail model and assumptions:
- Tie convention:
- Required assumptions:
- Minimum number of questions:
- Minimum or expected censoring events:
- Question clustering or stratification:
- Uncertainty interval:

## Proposed graph

- Exact x-axis:
- Exact y-axis:
- Output unit:
- Is performance measured across regimes or difficulty groups?
- Model-pair eligibility rule:
- Shared-performance rule:
- Extrapolation rule:
- What appears as separate panels?

## Claims and boundaries

- [ ] Censoring adjusts response length, not missing correctness.
- [ ] Grade, termination, and output length stay separate.
- [ ] MathArena censoring stays labeled inferred.
- [ ] HELM Gemini censoring is observed.
- [ ] HELM provider token fields aren't pooled without comparable accounting.
- [ ] The four MathArena competitions aren't automatically one 123-question sample.
- [ ] Larger-cap runs are independent observations, not continued traces.

## Next deliverable

Choose one or record another:

- [ ] HELM Gemini identification check: observed summaries and the unidentified tail
- [ ] Exact-source capability audit for AIME 2026 and BRUMO 2025
- [ ] Controlled Model A versus Model B collection schema
- [ ] Other:

Required format:

Required inputs:

Connor owns:

Chirag owns:

Review date:

## Logistics

- Slack workspace:
- Benchmark document shared:
- Parent communication:
- Course-credit follow-up:
- Written-update cadence:
- Next call:

## Parking lot

- Model portfolio:
- Provider and route choices:
- Caps and repeats:
- Power analysis:
- Runner and budget gates:
- Preregistration:

## Final read-back

- [ ] I read each decision back to Chirag.
- [ ] I separated decisions from open questions.
- [ ] Every immediate task has one owner.
- [ ] Every immediate task has a date.
- [ ] We scheduled the next review.

## Follow-up message outline

Hi Chirag,

Thanks for the call. I recorded the following:

1. We will use [archives] for [purpose].
2. We will define the censoring-adjusted length summary as [method].
3. The proposed graph will use [x-axis] and [y-axis].
4. My next deliverable is [artifact] by [date].

The remaining open questions are:

- [question]

Your next task is [task] by [date]. My next task is [task] by [date]. Our next review is [date and time].

Please correct anything I captured incorrectly.

Best,
Connor
