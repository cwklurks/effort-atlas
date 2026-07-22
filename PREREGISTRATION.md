# Thinking Cut Short

## Separating Token Starvation from Genuine Overthinking in Reasoning Models

**Author:** Connor Klann ([ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670))  
**Preregistration date:** 2026-07-22  
**Status:** Confirmatory protocol, to be committed before any paid call in this study  
**Intended submission:** EACL 2027 Industry Track, deadline 2026-09-11

### One-sentence pitch

Higher reasoning effort sometimes appears to reduce accuracy because models
spend their output allowance thinking and are stopped before answering; we
rerun the same items with more room to measure how much apparent overthinking
is actually token starvation.

## Scope and prior evidence

This is a new confirmatory study. It is separate from the exploratory Tinker
and OpenRouter runs already recorded in `RESEARCH_LOG.md`,
`TRUNCATION_STUDY.md`, and `CAP_SEMANTICS.md`. Those earlier runs motivated the
hypotheses and design, but they will not be pooled into the confirmatory
estimates.

The exploratory Inkling/OpenRouter sweep used a 20,000-token request cap. On
30 AIME items, medium effort scored 25/30 and max effort scored 21/30. Four
medium responses and nine max responses ended with `finish_reason="length"`;
all 13 were graded wrong. Because these are outcome-informed pilot data, they
will be labeled exploratory everywhere.

The earlier cap-semantics audit found that the tested Inkling/Together route
was cap-inclusive at a 2,000-token cap. It also found that cap semantics are
route-specific, so every confirmatory model is pinned to one provider and
must pass an accounting and cap-semantics check before its main block.

## Research question

When a reasoning-effort benchmark shows lower accuracy at a higher effort,
how much of that difference persists after increasing the reasoning-inclusive
output cap?

The estimand is a cap-by-effort interaction. A positive interaction means that
the higher-effort condition benefits more from added output room than the
lower-effort condition. This is evidence that the low-cap effort comparison
was confounded by token starvation. It is not, on its own, evidence that every
rescued response followed the same reasoning path.

## Hypotheses

- **H1, differential censoring:** At the smaller cap, the higher-effort
  condition has a higher `finish_reason="length"` rate than the lower-effort
  condition.
- **H2, cap rescue:** Raising the cap reduces length stops and increases
  conventional accuracy, with a larger change at the higher effort.
- **H3, primary interaction:** The effort slope at the larger cap is more
  positive, or less negative, than the effort slope at the smaller cap.
- **H4, route replication:** The direction of H3 appears in both preregistered
  model/provider routes. The two routes use model-appropriate effort labels
  and cap contrasts, so effect sizes will not be treated as directly
  interchangeable.

Failure to support any hypothesis will be reported without changing the
design, grader, labels, or endpoint definitions.

## Confirmatory experiment

### Shared task and controls

- Domain: all 30 audited AIME-25 items in `data/math.jsonl`.
- Prompts, gold answers, and graders: unchanged from the repository at the
  preregistration commit.
- API: OpenRouter Chat Completions, streamed, with terminal usage requested.
- Temperature and sampling parameters: provider defaults. No unsupported seed
  will be sent.
- Routing: one pinned provider, fallbacks disabled, required-parameter
  enforcement enabled.
- Valid row: expected served provider, positive prompt and completion usage,
  nonmissing finish reason, generation ID, and a matching generation receipt.
- Automatic retries: none. A failed or unaccounted call stays missing. A
  manual rerun is allowed only after confirming that no generation was billed,
  and the event is logged.
- Isolation: each confirmatory route gets a new cache directory and result
  series. No historical cache entry or response row can satisfy a
  confirmatory request.

### Panel A: Inkling

- Model: `thinkingmachines/inkling`.
- Provider: Together, pinned through OpenRouter.
- Effort conditions: `medium` and `max`.
- Requested total-generation caps: 20,000 and 49,152 tokens.
- Design: 30 items x 2 efforts x 2 caps x 1 response = 120 planned calls.

The 20,000-token cap reproduces the exploratory condition. The 49,152-token
cap was selected before confirmatory data because one earlier, explicitly
exploratory max-effort rescue needed 38,603 completion tokens to finish.

### Panel B: GLM 5.2

- Model: `z-ai/glm-5.2`.
- Provider: Together, pinned through OpenRouter.
- Effort conditions: `high` and `xhigh`, the two effort levels documented for
  this model by OpenRouter on 2026-07-22.
- Requested total-generation caps: 4,096 and 32,000 tokens.
- Design: 30 items x 2 efforts x 2 caps x 1 response = 120 planned calls.

This is a directional replication, not a pooled estimate with Inkling. The
caps are lower because the panel must fit the preregistered budget at the
pinned route's worst-case cap-inclusive price. If Together rejects either
effort or cap, returns a route mismatch, or proves cap-exclusive, Panel B is
stopped and reported as missing; another provider will not be substituted
after seeing responses.

### Smoke and route gates

Smoke rows are operational checks and are excluded from confirmatory accuracy.

1. Inkling/Together: one easy extraction item, medium effort, 2,000-token cap.
2. GLM/Together: the same easy item at high effort and hard `math_0003` at
   xhigh effort, each with a 2,000-token cap.

A route passes only if its provider matches, completion tokens are positive,
the generation receipt reconciles, effort is accepted, and a cap collision is
reported as `finish_reason="length"`. Native billed completion must not exceed
the requested cap. A failing route receives no main block.

### Request order

Each panel uses a schedule generated before its first paid call with fixed
seed `20260722`. Item order is randomized. Within every item block, the four
effort-by-cap conditions are randomly permuted. The complete schedule and its
SHA-256 digest are saved before execution. Restarting reproduces that schedule;
it does not generate a new order.

## Outcomes and analysis

### Primary quantities

For every model x cap x effort cell, report:

- conventional accuracy, with every valid length-stopped response retained as
  wrong;
- successful-response denominator `n` and correct count `k`;
- length-stop count and rate;
- empty extracted-answer count;
- mean and median completion and reasoning tokens;
- median and minimum/maximum latency;
- receipt-reported cost; and
- accuracy bounds `[k/n, (k+censored)/n]` showing what censoring alone leaves
  unidentified.

Transport failures, route mismatches, and rows without valid accounting are
reported separately and excluded from `n`; they are not silently scored wrong
or imputed.

For each panel define the effort slope at cap `c` as

`D_c = accuracy(higher effort, c) - accuracy(lower effort, c)`.

The primary interaction is

`I = D_large_cap - D_small_cap`.

H3 predicts `I > 0`. The analogous interaction in length-stop rates is a
mechanism check and is expected to have the opposite sign.

### Uncertainty and tests

- Report 95% Wilson intervals for each cell proportion.
- Report a 95% item-clustered bootstrap interval for each effort slope, cap
  effect, and interaction, using 10,000 resamples and seed `20260722`.
- Report exact paired item comparisons as secondary descriptive checks.
- H3 is the primary confirmatory test. H1 and H2 are prespecified mechanism
  checks. H4 is a directional replication criterion, not a claim of identical
  effect size.
- No result will be called statistically established solely because a
  bootstrap interval narrowly excludes zero with 30 items. Effect sizes,
  denominators, and censoring patterns remain primary.

### Rescue and genuine-overthinking taxonomy

For a given item and effort, a **cap rescue** is a smaller-cap length stop that
is wrong and a larger-cap normal stop that is correct. Because providers do
not guarantee identical sampling across these calls, this is a paired
item-level outcome, not a deterministic continuation of one trace.

A **candidate genuine-overthinking case** requires all of the following:

1. the larger-cap response ends normally rather than by length;
2. the higher-effort response is wrong while the lower-effort response for the
   same item is correct; and
3. neither row has an extraction or accounting failure.

Trace review may describe whether a candidate reached and then abandoned a
correct intermediate conclusion, but trace interpretation is qualitative and
cannot override the automated grade. A completed wrong answer alone is not
proof of overthinking.

## Budget and sequential stopping

- User-reported OpenRouter balance at preregistration: **$30.06**.
- New confirmatory-study hard ceiling: **$27.00**.
- Untouched account margin: **$3.06**.
- Historical spend is reported separately and is not charged again to this
  new-study ceiling.

Prices and balance will be rechecked without a completion immediately before
the first paid call. The 2026-07-22 planning rates are $1.00/M input and
$4.05/M output for Inkling/Together, and $0.583/M input and $4.40/M output for
GLM 5.2/Together. A conservative 2,000 input tokens per call is used for
worst-case gating.

At those rates, the full Inkling block is bounded at approximately $17.04 if
the route remains cap-inclusive. The full GLM block is bounded at
approximately $9.67. The three smoke calls are bounded at approximately $0.04.
The combined preregistered exposure is approximately $26.75.

Execution order is smoke gates, Inkling, spend reconciliation, GLM, spend
reconciliation. Before each main panel, its full remaining worst-case exposure
must fit under `$27.00 - actual_new_study_spend`. If it does not fit, that
panel is skipped in full rather than reduced after observing outcomes. Stop
all paid work immediately if cumulative receipt cost reaches $27.00, token
accounting is missing, or a supposedly cap-inclusive route exceeds its cap.

No extra replicates or knowledge-domain calls are authorized by this
preregistration. Leftover funds remain unspent unless an amendment specifies a
new analysis-independent design and is committed before those calls.

## Reproducibility and reporting

- Store request configuration, schedule, response row, generation ID, native
  token receipt, served provider, finish reason, latency, and cost.
- Record route metadata and advertised precision/quantization before each
  panel. If precision is unavailable, record `unknown` rather than infer it.
- Preserve every error row and every valid length-stopped row.
- Publish sanitized raw rows, receipts, schedules, analysis code, and dataset
  identifiers or hashes, subject to dataset and provider redistribution terms.
- Do not publish secrets or `.env` contents.
- Clearly label all earlier 4,096-cap and 20,000-cap observations as
  exploratory. Earlier accuracy claims that ignored censoring are invalid.

## Amendment rule

Implementation details may be clarified before the first paid confirmatory
call, but each change must be committed as a dated amendment and cannot depend
on new response outcomes. After the first valid paid confirmatory response,
hypotheses, primary outcomes, panel definitions, and stopping rules are fixed.
Any later deviation is labeled and justified in the research log.

## Protocol sources

- OpenRouter reasoning controls and token accounting:
  <https://openrouter.ai/docs/guides/best-practices/reasoning-tokens>
- Inkling route and pricing:
  <https://openrouter.ai/thinkingmachines/inkling>
- GLM 5.2 effort support and pricing:
  <https://openrouter.ai/z-ai/glm-5.2>

