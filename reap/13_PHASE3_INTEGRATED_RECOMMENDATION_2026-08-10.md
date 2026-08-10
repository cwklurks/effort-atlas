# REAP Phase 3 integrated recommendation

**Dated:** 2026-08-10

**Status:** NON-FROZEN RECOMMENDATION - NO CALL AUTHORIZATION

**Purpose:** give Connor and Chirag one opinionated proposal to review before the
new REAP preregistration is drafted. This document is not an approval record, a
frozen protocol, a route activation, or permission to spend.

## Safety state

```text
CONFIRMATORY_CALLS=0
PAID_STUDY_GENERATION_CALLS=0
SMOKE_CALLS=0
PROVIDER_PROBE_CALLS=0
DEEPSEEK_DEVELOPMENT_CALLS=0
```

The pinned Tinker SDK 0.25.0 cannot currently guarantee **one and only one billed submission**.
No Tinker smoke or scientific call may run until a supported
one-submission path exists, the runner enforces it, and an independent review
passes. The proposed $2 reliability smoke is a future maximum, not authorization.

## Executive recommendation

REAP should be a staged, mechanism-first study rather than an attempt to spend all
available credits or include every interesting model at once.

The first pass should have five scientific roles:

1. **Mechanism panel:** standard Inkling on the shared HMMT-2026 core, with a
   detailed effort-by-cap grid and a large-cap reference. This is the one panel
   that directly studies a continuous effort control.
2. **Cheap replicated panel:** standard 32K GPT-OSS-120B on Tinker, with the full
   discrete effort-by-cap design and the optional HMMT-2025 extension.
3. **Large open-model breadth panels:** Nemotron Ultra 550B and Qwen3.5 397B on the
   shared core, using a smaller two-effort, two-cap design. These test whether the
   direction survives in more frontier-like open models without pretending their
   effort controls are the same as Inkling's.
4. **Closed-model replication:** GPT-5.6 Terra direct from OpenAI on the shared
   core. Terra is the current cost/capability compromise; Luna and Sol are
   informative alternatives, not fallbacks.
5. **Same-model hosting anchor:** GPT-OSS-120B on Tinker and, only if separately
   qualified, GPT-OSS-120B through one pinned OpenRouter provider. This isolates
   hosting and cap semantics from model-weight differences.

The design should use the same shared HMMT-2026 item IDs and 4K/16K caps wherever
the route supports them. Panel effects are shown side by side and never pooled.

The primary statistics should remain simple: Wilson intervals, item-clustered
bootstrap intervals, independent-draw transition summaries, explicit missingness,
and calibration error. A hierarchical model may be a secondary analysis only if
it is implemented and simulation-tested before data. It should never become a
reason to delay or reinterpret the primary analysis.

## Recommended scientific design

### Common Arm A

Every scientific panel that can support the comparison should run:

- the same frozen HMMT-2026 core;
- two route-specific effort endpoints;
- output caps 4,096 and 16,384;
- `n=8` independent scheduled outputs per item, effort, and cap for breadth and
  cross-platform panels;
- a larger `n` only for the two detailed Tinker mechanism panels when justified by
  power simulation and the frozen budget.

The effort labels are route-specific. Inkling 0.7 versus 0.99, GPT-OSS low versus
high, Terra medium versus xhigh, Nemotron off versus full, and Qwen thinking-off
versus thinking-on are directional contrasts. They are not a common numerical
dose and must not be pooled.

### Detailed panels

#### Inkling

Use the standard `thinkingmachines/Inkling` 64K route, not the separate 256K PEFT
route. The recommended first-pass scope is the shared 30-item HMMT-2026 core rather
than 60 items:

- Arm A: efforts 0.7/0.99, caps 4K/16K, `n=20`;
- Arm B: efforts 0.1/0.4/0.7/0.99, caps 2K/4K/8K/16K/32K, `n=8`;
- Arm C: the same four efforts, 49,152-token large-cap reference, `n=8`;
- prompt plus wrapper bound: 8,192 tokens;
- hard refusal when prompt plus output could exceed the 65,536-token context.

This keeps the distinctive continuous-effort experiment while cutting its
conservative planning maximum from about $1,492.18 to about $746.09. If Chirag's
power analysis says 30 item clusters are inadequate, add HMMT-2025 through a
pre-data amendment or increase item scope before any call. Do not automatically
switch to the PEFT route after smoke.

#### GPT-OSS-120B on Tinker

Use `openai/gpt-oss-120b`, the standard 32K route:

- Arm A: low/high, 4K/16K, `n=20`;
- Arm B: no-sysprompt/low/medium/high, 2K/4K/8K/12K/16K, `n=8`;
- Arm C: the same four renderer conditions, 20K reference, `n=8`;
- prompt plus wrapper bound: 8,192 tokens;
- hard refusal above 32,768 total tokens.

The recommended scope is 60 items if the HMMT-2025 manifest and grading path pass.
Only the shared HMMT-2026 core contributes to cross-model comparisons. The 2025
extension strengthens within-model item-level precision and is reported separately.

### Breadth panels

Use a smaller schedule for Nemotron Ultra and Qwen3.5 397B:

```text
30 items * 2 effort endpoints * 2 caps * n=8 = 960 outputs per model
prompt bound = 7,864,320 tokens
output bound = 9,830,400 tokens
```

- Nemotron Ultra 550B: off versus full, approximately $80.78 maximum at the
  2026-08-10 Tinker rates.
- Qwen3.5 397B: thinking off versus on, approximately $97.32 maximum.

These are breadth replications, not dose-response panels. Qwen is intentionally
included, but its documented control is binary thinking on/off. It cannot replace
Inkling or GPT-OSS in the claim about graded effort.

### Direct OpenAI panel

Use `gpt-5.6-terra` on the shared core:

- medium versus xhigh;
- 4K/16K caps;
- `n=8`;
- 4,096-token prompt bound;
- five-call accounting smoke included inside the same $200 pool.

The direct Terra page retrieved on 2026-08-10 lists $2/M input and $12/M output,
1.05M context, and 128K maximum output. Under the conservative schedule bounds,
the 30-item panel is about $125.83 before smoke. This is a dated planning fact, not
a permanent price or an observed accounting result.

Luna would cost about $12.58 under the rates recorded in the earlier worksheet and
is useful as a separate low-cost scale point. Sol would cost about $314.57 and does
not fit the current $200 pool at this schedule. Neither may silently replace Terra.

### OpenRouter same-model anchor

The same-model provider comparison should use `openai/gpt-oss-120b`, not DeepSeek.
It would use the shared core, 4K/16K caps, two verified effort endpoints, and `n=8`.

The current OpenRouter provider page does **not** list Fireworks for GPT-OSS-120B.
It lists, among others, Baseten, Groq, and Cerebras. On the 2026-08-10 page:

- Baseten was about 354 tokens/s at $0.10/M input and $0.50/M output;
- Groq was about 377 tokens/s at $0.15/M input and $0.60/M output;
- Cerebras was about 527 tokens/s at $0.35/M input and $0.75/M output.

Baseten is the tentative speed/price recommendation; Groq is the small-premium
speed alternative; Cerebras is the maximum-throughput alternative. At the declared
prompt/output bounds, Baseten is roughly $5.70 and Groq roughly $7.08 before smoke.
Throughput, price, quantization, context, endpoint policy, and availability are
mutable. The route must therefore remain omitted until one exact provider is
selected and shown, without a generation, to satisfy the required parameters and
ZDR policy. A later smoke may only activate that exact route or omit it.

The request must pin one provider, set `allow_fallbacks=false`, require supported
parameters, request ZDR, deny provider data collection, disable response caching,
set explicit effort and `max_tokens`, use zero generation retries, and record the
served provider plus receipt. If the chosen endpoint is unavailable under ZDR, the
panel is omitted. It does not fall through to the next provider.

## Recommended model portfolio

### First-pass portfolio

| Scientific role | Route | Scope | Conservative planning maximum |
|---|---|---|---:|
| Continuous mechanism | Inkling standard | Full A/B/C, 30 shared items | $746.09 |
| Cheap detailed replication | GPT-OSS-120B standard | Full A/B/C, up to 60 HMMT items | $187.03 |
| Large open breadth | Nemotron Ultra 550B | Arm A-style, 30 items, n=8 | $80.78 |
| Large open breadth | Qwen3.5 397B | Arm A-style, 30 items, n=8 | $97.32 |
| Closed frontier-family | GPT-5.6 Terra direct | Arm A-style, 30 items, n=8 | $125.83 |
| Same-model provider anchor | GPT-OSS-120B on OpenRouter | Conditional, 30 items, n=8 | about $5.70-$7.08 |

The first four Tinker panels total approximately $1,111.21 before smoke, leaving a
large inaccessible reserve inside a $2,000 first-pass ceiling and an even larger
reserve in the $5,000 credit award. The goal is evidence, not credit exhaustion.

### Models not recommended for the first frozen pass

- **Inkling PEFT 256K:** a different, more expensive route. Keep as a later study
  or separately frozen alternative, never a fallback.
- **GPT-OSS-120B PEFT 128K:** useful only if the standard-route cap grid cannot
  answer the scientific question. It changes the route and price.
- **Nemotron Super and Qwen3.6 35B:** excellent cheap follow-up scale points, but
  less important than the Ultra/397B breadth anchors in the first pass.
- **GPT-5.6 Luna:** attractive later low-cost scale point, not a substitute for
  Terra.
- **GPT-5.6 Sol:** scientifically attractive but above the current OpenAI pool at
  the proposed size.
- **Fable 5 and Claude Opus:** not Tinker routes. Current retention/fallback or
  funding constraints require a separately designed provider study.
- **DeepSeek V4 Flash:** development assistant only under D15. It is not a
  scientific panel in this proposal.

## Dataset and grader recommendation

### Shared core

Keep the planned 30-of-33 HMMT-2026 core, but define it transparently. The simplest
candidate is the fixed `problem_idx` 1-30 slice, not a hand-picked set based on
observed model performance. Before freeze, confirm from the source provenance that
this corresponds to the intended short-answer competition set.

The current source contains 33 rows and many of the proposed first 30 gold answers
are fractions or radicals. Therefore the phrase “30 clean integer items” is wrong,
and the repository's simple numeric comparator is not sufficient. The required
grader design is:

1. answer presence is determined only by grader v2's complete `Final answer:` line;
2. mathematical correctness is determined by a pinned upstream MathArena grading
   path imported from a fixed revision;
3. the upstream scorer must pass frozen tests for each answer schema in the selected
   set, including equivalent fractions, radicals, signs, and formatting;
4. if the upstream import or equivalence tests fail, report `import_failed` and stop
   the dataset freeze; do not write a local fallback parser;
5. freeze item IDs, prompt bytes, gold strings/hashes, source revision, license,
   scorer revision, and per-item grader type.

If `problem_idx` 1-30 is not a coherent source-defined subset or the symbolic
scorer cannot be made reliable, the alternative is a smaller, predeclared
grader-eligible subset selected solely from gold schema before any model output.
That changes the power calculation and must be discussed with Chirag.

### Optional HMMT-2025 extension

Use all 30 HMMT-2025 items only on detailed Tinker panels whose schedule and budget
justify it. Mark the extension with a distinct dataset cohort field. Shared
cross-platform estimates use only the 2026 core; 2025 results are never silently
mixed into the Terra/OpenRouter anchor denominator.

### Deferred datasets

- AIME 2025/2026: valuable continuity set, but defer until exact license, item, and
  grader manifests are ready.
- GPQA Diamond: useful cross-domain extension, but gated access and MCQ guessing
  require a separate protocol.
- HARP hardest bracket: attractive difficulty study, but the candidate subset needs
  a reproducible revision and selection query.
- GSM8K: useful negative control and grader-pathology demonstration, not a core
  high-difficulty panel.

## Statistical recommendation

### Primary analysis

Keep the merged, low-assumption analysis as primary:

- cell accuracy and unanswered-stop rates with Wilson intervals;
- effort slopes, cap effects, and effort-by-cap interactions;
- 10,000-resample item-clustered percentile bootstrap, seed `20260722`;
- item-level independent-draw expected transition mass;
- item-level independent-draw rescue evidence;
- descriptive within-item and between-item variance components;
- paired item summaries where pairing is scientifically valid;
- cross-cell missingness with all-missing-correct and all-missing-wrong bounds;
- separate panel estimates, with no pooled cross-model effect.

Replicate indices are not trace identities. Never pair replicate 1 at 4K with
replicate 1 at 16K and describe the result as a continued or rescued trace.

### Optional hierarchical secondary model

If time permits before data, implement one minimal secondary model:

```text
logit P(correct) = panel-specific effort + log2(cap) + interaction
                   + random item intercept
```

One random item slope may be considered only if simulation shows stable recovery
with 30-60 item clusters. Freeze priors or optimizer, convergence rules, singular
fit behavior, interval method, and sensitivity checks. If the model fails its
pre-data simulations or later convergence diagnostics, report it unavailable. It
must not replace the bootstrap or alter primary claims.

My recommendation is to keep this secondary and non-gating. The main paper does not
need a complicated model to make the central intervention clear.

### H5 monotonicity

Treat H5 as a prespecified descriptive pattern. Report every neighboring effort and
cap contrast, every violation, endpoint directions, and missingness bounds. Do not
attach a confirmatory p-value or say the pattern is “supported.” A formal ordered
test can be a later methods contribution after its null, multiplicity, and
randomization are specified.

### H6 cap-invariance calibration

Use absolute truncation-rate error as the main calibration quantity and KS on
common support as a distribution diagnostic. Report signed error, absolute error,
maximum absolute error, mean absolute error, denominators, and reference-cap length
stops.

Before freezing a binary H6 claim, simulate the planned item counts. Preferred
decision rule if power is adequate:

1. jointly resample items across reference and dose arms;
2. compute the maximum absolute error across required cells;
3. form a one-sided 95% upper confidence bound;
4. call calibration within tolerance only if every cell is evaluable and the upper
   bound is at most 0.10;
5. otherwise report `inconclusive` or `outside_tolerance`, never a forced pass.

If simulations show 30-60 items cannot reasonably certify 0.10, keep H6 descriptive
rather than changing the threshold after data.

## Operational and budget recommendation

### Frozen sequence

1. Connor and Chirag settle the remaining D decisions without confirmatory data.
2. Freeze the scientific design, exact routes, manifests, schedules, analysis,
   ceilings, and binary activation predicates.
3. Implement and adversarially review the runner and budget gates offline.
4. Human-run the exact smoke schedule.
5. Activate an unchanged route or omit it. **NO SUBSTITUTION**.
6. Open confirmatory collection only after all hashes and ceilings match.

### Sampling unit

Prefer Tinker `num_samples=n` only if the exact-route smoke verifies one submission,
return count, per-sample mapping, usage, termination, and receipt semantics. Analyze
replicates with item clustering rather than assuming perfect independence.

If batching fails, omit the route under this design. Do not silently switch to
individual calls after response content exists. An individual-call design is valid,
but it must be chosen and fully scheduled before smoke.

### Hard ceilings

- Tinker first-pass ceiling: $2,000, with exact subceilings derived from frozen
  schedules. The recommended schedules currently total about $1,111.21 before a
  proposed $2 smoke. Unused funds remain inaccessible reserve.
- Direct OpenAI ceiling: $200 including every P3 smoke and study call.
- OpenRouter scientific/debug ceiling: $50, never borrowed from other pools.
- Proposed Fireworks development ceiling: $10 cumulative only if D15 is explicitly
  approved and implemented. It is not research spend.

Worst-case prompt plus cap-bounded output exposure must fit before a panel starts.
Expected response length is never a safety gate. Poll receipts between blocks and
stop at the exact ceiling.

### Development-only DeepSeek scope

DeepSeek V4 Flash may later help with bounded mechanical Markdown, boilerplate, test
scaffolding, and formatting through direct Fireworks. It receives no benchmark
items, golds, raw model responses, secrets, scientific decisions, or financial
verification. Require Chat Completions or `store=False`, served-route verification,
fallbacks off, no automatic tools, a separate ledger, per-task bounds, and Codex
review. Until that configuration and the $10 ceiling are explicitly approved,
`DEEPSEEK_DEVELOPMENT_CALLS` remains zero.

## D01-D15 recommended answers

### D01 - Freeze and smoke order

Choose scientific freeze, reviewed runner, tiny human smoke, then unchanged
activation or omission. Cap the future Tinker reliability smoke at $2.

### D02 - Arm architecture

Use independently sampled A/B/C arms and require `arm_key` everywhere. Never reuse
rows across arms.

### D03 - Dataset scope

Use the fixed, source-justified 30-of-33 HMMT-2026 core everywhere. Add HMMT-2025
only to detailed Tinker panels if Chirag's power review justifies it. Resolve the
symbolic grading blocker before freeze.

### D04 - Inkling design

Use standard 64K Inkling with the recommended effort/cap grid on 30 core items.
Keep PEFT and alternative settings as later or separately frozen designs, never
fallbacks.

### D05 - GPT-OSS Tinker design

Use standard 32K GPT-OSS-120B with the smaller cap grid and hard context refusal.
Use up to 60 HMMT items if the 2025 cohort passes provenance and grading gates.

### D06 - Direct OpenAI model

Use Terra on the shared 30 items at `n=8`, medium/xhigh, 4K/16K. Keep Luna and Sol
as separate future panels, not substitutes.

### D07 - Transition and rescue

Use independent-draw expected transition mass and item-level independent-draw
rescue evidence. Do not claim observed continuations.

### D08 - Replicate variance

Keep item bootstrap primary and method-of-moments descriptive. Permit a minimal,
simulation-tested hierarchical model as secondary only.

### D09 - Calibration and H6

Use maximum absolute truncation-rate error with an item-bootstrap uncertainty bound
if simulations show adequate power. Otherwise make H6 descriptive.

### D10 - Monotonicity

Use a prespecified descriptive pattern and show every adjacent violation. Do not
promote it to a formal test in the first pass.

### D11 - Prompt and grader

Use one short no-few-shot prompt with a complete `Final answer: <answer>` line.
Freeze exact rendered bytes, wrappers, effort delivery, grader-v2 extraction, and
the pinned upstream mathematical comparator.

### D12 - Seeds and batching

Use master seed `20260722`, arm-aware deterministic identities, and item-block
randomization. Prefer batching only if the exact smoke passes; otherwise omit under
this design.

### D13 - Portfolio and ceilings

Use the balanced five-role portfolio above. Keep a $2,000 Tinker first-pass ceiling
but schedule only about $1,111 before smoke, leaving the rest as reserve.

### D14 - Cross-platform anchors

Use the same frozen HMMT-2026 core and 4K/16K caps across panels, with route-specific
effort endpoints and separate reporting. Add a conditional same-model GPT-OSS
Tinker/OpenRouter comparison if one OpenRouter endpoint passes all gates.

### D15 - DeepSeek development gate

Leave DeepSeek disabled until direct Fireworks configuration, ZDR behavior,
fallback controls, ledger, per-task limits, and a $10 cumulative ceiling receive
explicit approval. Never use it for study data or scientific review.

## Questions for Chirag

1. Are 30 HMMT-2026 item clusters enough for Inkling and H6, or is the HMMT-2025
   extension required for statistical power?
2. Is the proposed first-30 source rule scientifically defensible once source
   provenance and the symbolic scorer are verified?
3. Should the hierarchical model be included as a frozen secondary analysis, or
   should REAP stay bootstrap/descriptive only?
4. Can the item-bootstrap calibration rule certify a 0.10 maximum error with the
   proposed item counts? If not, should H6 be descriptive?
5. Does the standard Inkling 30-item full A/B/C panel retain enough mechanism
   evidence to justify its cost?
6. Does Chirag agree that H5 is a descriptive pattern, not a confirmatory test?
7. Are the independent-draw transition and rescue names precise enough for the
   paper?

## Decisions Connor can make before the call

- approve or revise the exact shared prompt wording;
- choose batching as the proposed request unit or prefer individual calls from the
  start;
- select the balanced portfolio as the proposal to bring to Chirag;
- decide whether the OpenRouter same-model anchor should be scientific or remain
  debug-only;
- choose Baseten versus Groq as the endpoint to qualify, subject to ZDR and
  parameter evidence;
- leave DeepSeek disabled or approve development of its configuration without
  authorizing a call.

## Evidence and mutable facts

Facts below were checked on 2026-08-10 and must be snapshotted again before freeze:

- [Tinker models and pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
- [OpenAI GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [OpenRouter GPT-OSS-120B providers](https://openrouter.ai/openai/gpt-oss-120b/providers)
- [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [OpenRouter ZDR](https://openrouter.ai/docs/guides/features/zdr)
- [MathArena HMMT February 2026](https://huggingface.co/datasets/MathArena/hmmt_feb_2026)
- [Fireworks DeepSeek V4 Flash](https://fireworks.ai/models/fireworks/deepseek-v4-flash)
- [Fireworks data handling](https://docs.fireworks.ai/guides/security_compliance/data_handling)

Provider throughput is observational service metadata, not a guaranteed contract.
Provider pages do not prove account access, effort delivery, cap inclusiveness,
one-submission behavior, receipt correctness, or ZDR for the exact endpoint. Those
remain frozen activation gates.

## What would change this recommendation

This plan should be revised before freeze if any of the following occurs:

- Chirag's simulations show 30 item clusters are inadequate for the primary
  interaction or H6;
- the first-30 HMMT source rule is not coherent or the upstream symbolic grader
  cannot pass frozen equivalence tests;
- any proposed model lacks a verifiable effort control at the exact route;
- current price/context evidence makes a schedule exceed its pool;
- the runner cannot guarantee one billed submission and complete attempt logging;
- an OpenRouter endpoint cannot satisfy provider pinning, ZDR, required parameters,
  and receipt reconciliation together.

Any change must happen before confirmatory data and be recorded in a new dated
artifact. Smoke failure may omit a frozen panel; it may not redesign one.
