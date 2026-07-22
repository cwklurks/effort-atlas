# Cap Semantics Probe

## Preregistered protocol

Status: preregistered on 2026-07-21 before any paid Cap Semantics Probe call.
This section is the fixed pre-call record. Later measurements will be appended
below it; they will not replace the predictions or decision rules.

### Hypothesis

H-CAP: providers fall into at least two behavioral classes:

- **Cap-inclusive:** reasoning tokens count against the requested generation
  cap.
- **Cap-exclusive:** reasoning can be generated and billed beyond the requested
  generation cap.

We predict that class membership is undocumented or under-documented for at
least one tested provider. This is a claim about the exact model, host, API,
and request shape tested, not every endpoint operated by a vendor.

### Fixed protocol

- API: OpenRouter Chat Completions, streaming enabled with final usage
  requested.
- Requested cap: `max_tokens=2000`.
- Items, in this order: easy `extraction_0000`, then hard `math_0003`.
- Reasoning: `medium` where the routed endpoint advertises effort control.
  Kimi K2.6 does not advertise `reasoning_effort` on the selected Moonshot
  route, so it will use its provider-native default reasoning with reasoning
  explicitly enabled. This is labeled `default`, not silently relabeled as
  medium.
- Each provider has its own cache and results directory. Tinker, the original
  OpenRouter replication, and prior Grok rows are never copied into a probe
  result series.
- One exact provider route is pinned with fallbacks disabled. A response from a
  different provider invalidates that call for classification and stops that
  target.
- No retry is allowed for a completed/billed generation. A transport failure
  may be retried only when OpenRouter shows that no generation was billed.

The two calls provide a targeted semantics probe, not a population estimate.
"Definitive" below means definitive for the observed endpoint and request
shape. Contradictory calls are classified as `mixed/indeterminate`.

### Targets and pre-call predictions

| Order | Model and pinned provider | Served precision | Requested reasoning | Pre-call prediction | Pre-call price ceiling |
|---:|---|---|---|---|---:|
| 1 | `openai/gpt-oss-120b` via DeepInfra | BF16 | medium | cap-inclusive | $0.40 |
| 2 | `thinkingmachines/inkling` via Together | provider metadata reports unknown | medium | cap-inclusive | $0.40 |
| 3 | `moonshotai/kimi-k2.6` via Moonshot AI | INT4 | provider-native default | cap-inclusive | $0.40 |
| 4 | `x-ai/grok-4.5` via xAI | provider metadata reports unknown | prior request was `max`, although xAI documents only low/medium/high | cap-exclusive, already observed at 20k | $0.40 only if a new 2k probe is affordable |

OpenAI documents configurable low/medium/high effort for GPT-OSS, but the
DeepInfra-hosted Chat Completions cap behavior remains a measurement question.
Moonshot's Kimi K2.6 documentation predicts that reasoning plus content is at
most `max_tokens`. OpenRouter's approximately 95% allocation applies to
`max`/`xhigh` effort in its generic reasoning normalization; it is not a
Moonshot K2.6 statement and is not the condition in this protocol.

### Recorded fields and receipts

Every successful row must contain:

- requested cap and requested reasoning setting;
- API-reported prompt, completion, and reasoning-token counts;
- visible response and extracted answer;
- `finish_reason`, wall-clock latency, served provider, and generation ID;
- streamed API cost when present; and
- the corresponding OpenRouter generation-stat receipt, including native
  prompt/completion/reasoning tokens and reported cost when available.

Raw response rows and generation receipts remain in the private, Git-ignored
`results_cap_semantics/<target>/` directories. The results table links a
deterministic public derivative containing the audit-critical route, usage,
finish, latency, cost, and opaque linkage fields. Prompts, labels, answers,
visible responses, reasoning traces, and unstructured error messages are not
redistributed. The public manifest records SHA-256 digests of every private
source. Missing fields stay missing; no row is estimated, reconstructed,
deduplicated, or repaired during export.

### Classification rules fixed before measurement

Let `C=2000`, `N` be OpenRouter's native billed completion-token count, `R` be
the API-reported reasoning-token count, and `V` be the gateway-normalized
completion count where OpenRouter reports it.

- **Cap bounds total generation:** `N <= C`, including reasoning and visible
  answer. A cap collision must be reported as `finish_reason="length"`.
- **Cap bounds visible output only:** `V <= C` but `N > C`, with the excess
  attributable to native reasoning.
- **Cap bounds nothing observed:** both the visible/gateway count and native
  billed completion exceed `C`, or the provider otherwise ignores the cap in a
  way not explained by a separate reasoning stream.
- **Billing bounded by cap, yes:** native billed completion tokens are at most
  `C`. Input tokens and their separate charge do not affect this classification.
- **Billing bounded by cap, no:** native billed completion tokens exceed `C`.
- **Truncation signaled honestly, yes:** whenever the cap prevents a final
  answer, the response reports `finish_reason="length"`.
- **Truncation signaled honestly, no:** the cap prevents a final answer but the
  response reports `stop` or another non-length reason.
- If neither item reaches the cap, truncation signaling is `not exercised` and
  cap class is `not demonstrated`, even when counts are consistent with the
  prediction.
- Missing or internally inconsistent accounting yields `indeterminate`, not an
  inferred class.

"Visible answer truncated" means the answer required by the unchanged task
prompt is absent or incomplete at the end of the returned visible content. A
wrong but syntactically complete answer is not called truncated.

### Budget and stop rules

- Historical spend before this probe: **$8.91055695** across Tinker and prior
  OpenRouter work.
- Existing all-provider ceiling: **$10.00**.
- Maximum remaining spend at preregistration: **$1.08944305**.
- Per-target hard ceiling: **$0.40**, checked after each call.
- Before every paid call, current route pricing and OpenRouter key status are
  checked without making a completion.
- After every target, actual cost is summed from OpenRouter generation receipts.
- Stop before a call if its conservative projected cost would breach either the
  target ceiling or the global ceiling. A 2,000-token output at the route's
  current price plus observed prompt cost is the projection only for targets
  still predicted cap-inclusive.
- Stop a target immediately for missing/negative usage, missing finish reason,
  missing generation receipt, route mismatch, or evidence that native billing
  has crossed its $0.40 limit.
- Grok 4.5 receives a new 2k probe only if targets 1-3 leave enough balance for
  a cap-exclusive worst-case call. Otherwise its two existing 20k receipts are
  reused and labeled **20k probe only**.
- GPT-5.6 and other closed-model targets remain pending until the user tops up.

For any measured cap-exclusive route, future budget gates must use twice the
observed p95 reasoning length as the per-call worst case. Such sweeps also
require per-call receipt logging and a kill threshold; `max_tokens` alone is
not accepted as a financial bound.

## Measurements

The preregistered 2,000-token probes were run after commit `ea022cd`. Results
below are scoped to the exact model, provider route, API, and request shape
shown. Counts are OpenRouter generation-receipt native counts unless explicitly
labeled as gateway-normalized counts.

| Model, provider, and served precision | Observations: native completion / reasoning tokens; finish; visible answer; latency; cost | Documented versus measured | What the cap bounded | Billing bounded by cap | Truncation signaled honestly | Sanitized rows and billing receipts |
|---|---|---|---|---|---|---|
| `openai/gpt-oss-120b` / DeepInfra / BF16 | Easy: 44 / 23; `stop`; complete and correct; 2.32s; $0.000012808. Hard: 2,000 / 2,066; `length`; truncated, no extracted answer; 57.62s; $0.000345180. | OpenAI's Responses API documents an inclusive cap, but that is not a DeepInfra Chat Completions guarantee. The native billed count stopped exactly at 2,000. The 2,066 reasoning detail is larger than the 2,000 completion total, so the two receipt fields are not arithmetically comparable and were not repaired. | Total generation in native/billed accounting; reasoning split has a tokenizer/accounting anomaly. | Yes, in both observations. | Yes, on the hard cap collision. | [sanitized rows](public_artifacts/cap-semantics-2026-07-21/results.jsonl); [sanitized receipts](public_artifacts/cap-semantics-2026-07-21/receipts.jsonl); [manifest](public_artifacts/cap-semantics-2026-07-21/manifest.json) |
| `thinkingmachines/inkling` / Together / unknown | Easy: 39 / 25; `stop`; complete and correct; 2.06s; $0.000262950. Hard: 2,000 / 1,999; `length`; truncated, no extracted answer; 70.44s; $0.008201000. | No provider-specific cap-inclusion statement was found. Measurement was cap-inclusive in native/billed accounting. | Total generation. | Yes, in both observations. | Yes, on the hard cap collision. | [sanitized rows](public_artifacts/cap-semantics-2026-07-21/results.jsonl); [sanitized receipts](public_artifacts/cap-semantics-2026-07-21/receipts.jsonl); [source map](public_artifacts/cap-semantics-2026-07-21/README.md) |
| `moonshotai/kimi-k2.6` / Moonshot AI / INT4 | Easy: 401 / 391; `stop`; complete and correct; 11.69s; $0.001695200. Hard: 2,000 / 1,999; `length`; truncated, no extracted answer; 52.56s; $0.008083600. | Moonshot says reasoning plus content is at most `max_tokens`. The measured native counts and finish reason agree. | Total generation. | Yes, in both observations. | Yes, on the hard cap collision. | [sanitized rows](public_artifacts/cap-semantics-2026-07-21/results.jsonl); [sanitized receipts](public_artifacts/cap-semantics-2026-07-21/receipts.jsonl); [source map](public_artifacts/cap-semantics-2026-07-21/README.md) |
| `x-ai/grok-4.5` / xAI / unknown | **20k probe only.** `math_0009`: 5,429 / 4,727; `stop`; complete and correct; 64.72s; $0.032990400. Hard `math_0003`: 54,969 / 53,883; `stop`; complete and correct; 895.40s; $0.330182400. Gateway-normalized completion counts were 958 and 6,302. | xAI maps Chat `max_tokens` to `max_output_tokens` as maximum tokens to generate and bills reasoning at the completion rate. On this OpenRouter/xAI route, native reasoning and billing continued beyond the requested 20,000 cap. | Visible/gateway-normalized completion only in the decisive hard observation. | No; hard native completion was 2.75 times the request. | Not exercised: neither retained row lost its visible answer. | [sanitized rows](public_artifacts/cap-semantics-2026-07-21/results.jsonl); [sanitized receipts](public_artifacts/cap-semantics-2026-07-21/receipts.jsonl); [source map](public_artifacts/cap-semantics-2026-07-21/README.md) |

The observed routes therefore occupy at least two classes under the fixed
rules: three cap-inclusive routes and one cap-exclusive route. H-CAP is
supported for these endpoints. The Inkling/Together class was not stated in
provider-specific documentation found for this audit, satisfying the
under-documented portion of the prediction. This does not establish behavior
for other hosts or API surfaces serving the same model names.

The three new two-call targets cost **$0.018600738** in total: $0.000357988
for GPT-OSS, $0.008463950 for Inkling, and $0.009778800 for Kimi. Adding that
to the preregistered historical spend gives **$8.929157688** against the
**$10.00** project ceiling, leaving **$1.070842312**. The Grok receipt total of
$0.363172800 was already included in historical spend and was not added again.

Inkling and Kimi each returned one HTTP 429 for the hard request after the easy
call. Both failures had no generation ID or generation receipt. One retry was
made for each under the preregistered no-billed-generation rule, and both
retries completed. GPT-OSS required no retry. No response, grade, usage count,
or receipt was interpolated or edited.

No new Grok call was made. With only two historical reasoning counts, a
conservative nearest-rank p95 is the larger observation, 53,883 tokens. Twice
that value is 107,766 output tokens, which would cost about $0.65 at $6 per
million before input charges and therefore violates the $0.40 target ceiling.
GPT-5.6 and other closed-model probes remain pending a user-approved top-up.

Going forward, the measured Grok/xAI route is treated as cap-exclusive. Its
budget gate uses at least 107,766 completion tokens per call until a larger
sample supports a different p95. Every call on it requires a generation
receipt and a kill threshold; `max_tokens` is not treated as a cost bound.
