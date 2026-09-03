# Model-pair eligibility for the matched-performance question

**Date:** 2026-08-18
**Status:** Non-frozen planning record. No candidate is activated by this table,
and this document authorizes no provider call.

## Bottom line

No planned model comparison is scientifically and operationally eligible today.
The questions, prompts, routes, caps, sampling settings, and price evidence are not
frozen; the paid runner is not complete; and the pinned Tinker SDK path is already
known to resubmit on an internal retry path. The honest current statuses are
`conditional`, `descriptive_only`, or an explicit `ineligible_for_*` claim tag.

`Y` means documented. `C` means conditional on a frozen artifact plus operational
proof. `N` means not established or currently blocked.

## Eligibility matrix

| Comparison or role | Same frozen questions | Complete output accounting | Comparable token unit | Effort control | Explicit cap and termination | Exact route | One-submission proof | Current status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Inkling/Tinker, 0.7 vs 0.99 plus dose response | C | N | C, within exact route only | Y, continuous `[0,1)` | C | C | **N** | **`conditional` mechanism panel** |
| GPT-OSS-120B/Tinker, low vs high plus A/B/C | C | N | C, within exact route only | Y, discrete renderer | C | C | **N** | **`conditional` detailed replication** |
| Nemotron-3-Ultra-550B/Tinker, off vs full | C | N | C, within exact route only | Y, renderer endpoints | C | C | **N** | **`conditional` breadth replication** |
| Qwen3.5-397B/Tinker, thinking off vs on | C | N | C, within exact route only | Y, renderer endpoints | C | C | **N** | **`conditional` breadth replication** |
| GPT-5.6 Terra/direct OpenAI, medium vs xhigh | C | C after accounting gate | C, within exact route only | C: medium/xhigh are family-documented; Terra acceptance and delivery remain unverified | Y in docs, C operationally | C | N, runner absent | **`conditional` closed-family replication** |
| GPT-OSS-120B on Tinker vs one pinned OpenRouter endpoint | C | N | **N** for interchangeable native tokens | C | C | **N** until endpoint chosen | N | **`conditional` operational replication; `ineligible_for_causal_hosting`** |
| Any cross-model pair among Inkling, GPT-OSS, Nemotron, Qwen, and Terra | C | N/C | **N** as a universal raw-token unit | Route-specific only | C | C | N | **`conditional` directional only; `ineligible_for_pooled_native_token_ratio`** |
| HELM GPQA archived model pairs | Y at archive level | Archive fields only | **N** | Not controlled | Gemini termination only | Historical archive | Not applicable | **`descriptive_only`** |
| MathArena archived model pairs | Y at archive level | `output_tokens` only | Not yet proven across models | Observational labels | Cap inferred; no finish reason | Pinned revisions need byte reacquisition | Not applicable | **`descriptive_only`** |

Per-response correctness in the planned HMMT panels is also conditional on pinning
and testing the deterministic upstream MathArena symbolic comparator. The current
numeric-only comparison path is not sufficient for every real HMMT gold form.

## What “comparable” means here

Using the same questions is necessary but not sufficient. A direct model-to-model
token ratio also requires the output measure to have the same meaning. Different
models use different tokenizers, and different routes may include, hide, or bill
reasoning tokens differently.

Therefore:

- Within one exact model-route, report the preregistered route-native output-use
  measure per question alongside accuracy, effort, and cap. Call it billed output
  tokens only where per-response billing attribution is proved.
- Across model-routes, show paired-question curves as **directional operational
  comparisons**, with route and accounting semantics printed beside every point.
- Do not pool native-token counts or call one token a universal unit of reasoning.
- A cost comparison is allowed only if the named outcome is API cost efficiency;
  it does not become a model-intrinsic result.
- Visible characters or reference-tokenizer counts may be sensitivity outcomes,
  but they omit hidden reasoning and cannot replace billed-output accounting.

## Minimal first-pass recommendation

The smallest portfolio that preserves the paper’s core mechanism and adds two
distinct replications is:

1. **Inkling/Tinker:** full A/B/C mechanism panel, because continuous native effort
   is the distinctive intervention.
2. **GPT-OSS-120B/Tinker:** full A/B/C discrete-effort replication on the same
   platform.
3. **GPT-5.6 Terra/direct OpenAI:** a smaller 2×2 closed-family directional
   replication.

Defer Nemotron, Qwen, and the OpenRouter GPT-OSS anchor until the first three clear
their gates. This reduces breadth and cannot be adopted silently: Connor and Chirag
must decide whether the first paper needs breadth panels or whether the simpler
portfolio is more defensible and executable.

## Route facts currently documented

- Tinker lists the standard Inkling, GPT-OSS-120B, Nemotron Ultra, and Qwen3.5
  routes, contexts, and current prices. Inkling and Nemotron pricing remains tied
  to a limited-time advertised discount, so freeze-day gates must use list-rate
  exposure or an explicit discount-loss stop rule. See [Tinker models and
  pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/).
- Tinker documents Inkling’s continuous effort renderer and discrete renderer
  controls for the other planned models. Documentation establishes an available
  control, not successful delivery on a frozen route. See the [Inkling renderer
  guide](https://tinker-docs.thinkingmachines.ai/cookbook/inkling/tml-renderers/)
  and [renderer catalog](https://tinker-docs.thinkingmachines.ai/cookbook/api-reference/renderers/get_renderer/).
- Tinker exposes generated token IDs and `stop_reason`, but its documented billing
  usage is aggregated rather than a complete dollar receipt for each response.
  The experiment must prove the request-to-response-to-billing join before
  activation. See [SampleResponse](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/types/sampleresponse/)
  and [billing usage](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/restclient/).
- Current OpenAI documentation lists medium and xhigh in the GPT-5.6 family value
  set, plus Terra’s 128K maximum output and 1.05M context. Exact Terra acceptance,
  effort delivery, and billing remain unverified pending the five-call human gate.
  See [GPT-5.6
  Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) and the
  [latest-model guide](https://developers.openai.com/api/docs/guides/latest-model).
- OpenRouter supports provider pinning, fallback control, parameter enforcement,
  data-collection policy, and endpoint-specific ZDR routing. Those controls do not
  prove that an unselected endpoint satisfies every REAP requirement. See
  [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection),
  [ZDR](https://openrouter.ai/docs/guides/features/zdr), and the [current GPT-OSS
  provider page](https://openrouter.ai/openai/gpt-oss-120b/providers).

## Shared freeze blockers

- Choose and freeze the HMMT core, exact item IDs, source revisions and hashes,
  prompt bytes and wrappers, answer schema, and deterministic upstream scorer.
- Freeze every route-specific effort value, sampling parameter, cap integer,
  schedule, seed, and context-refusal rule before outcome collection.
- Build and adversarially test the runner: zero generation retries, fresh cache
  identity, append-only attempt ledger, captured termination and usage, receipt
  reconciliation, and platform-scoped hard budget ceilings.
- Snapshot list and discounted prices, model identifiers, served precision and
  revision when available, tokenizer/accounting semantics, and retention policy.

## Tinker activation blockers

- Replace or bypass the disqualified `tinker==0.25.0` request path with a reviewed
  implementation that proves one billed submission per scheduled call.
- Prove per-response linkage among request identity, generated token IDs,
  termination, and billed usage.
- Human smoke must verify effort delivery, final stop vocabulary, exact-cap
  behavior, accounting bounds, and retention/account policy on each frozen route.
- Resolve the current batching-versus-individual-call design before freeze. Neither
  approach is allowed until the one-submission invariant is enforced.

## Terra activation blockers

- Freeze an exact snapshot or an explicit alias/snapshot policy.
- Human-run the prespecified five-call accounting check for effort delivery,
  `usage.output_tokens`, billing, visible text, and incomplete-reason mapping.
- Record the direct-OpenAI retention policy and the possible HMMT-2026 exposure
  caveat in the manifest and paper.

## OpenRouter anchor blockers

- Select one provider before smoke and set `only`, `allow_fallbacks:false`,
  `require_parameters:true`, `data_collection:"deny"`, and `zdr:true`.
- Pin and verify price, ZDR status, effort support, cap support, served provider,
  precision, model revision, tokenizer/wrapper, receipt fields, and zero-retry
  behavior.
- Match the OpenRouter precision to Tinker’s served GPT-OSS precision where
  possible. Even after qualification, describe the result as a replication under
  a separately operated deployment, not the causal effect of hosting.

## Human decision prompted by this matrix

Decide whether the first paper values a smaller, better-qualified three-model
portfolio or a broader five-role portfolio. Whichever choice is made, keep each
route’s results separate and do not let additional panels create additional
headline hypothesis opportunities.
