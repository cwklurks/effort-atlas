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

Raw response rows and generation receipts will be JSONL files under
`results_cap_semantics/<target>/`. The results table will link those files.
Missing fields stay missing; they are never estimated or reconstructed.

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

No Cap Semantics Probe calls had been made when the protocol above was written.
Results will be appended here after the preregistration commit.
