# Tinker probe report format

**Status:** pre-confirmatory tooling contract. A report row is evidence only when
`status="ok"` and it came from a human-authorized `--live` execution. Dry runs do
not write report rows. Nothing in this format settles a scientific or platform
fact without live evidence.

`scripts/tinker_probe.py` validates the evidence sink before constructing any
client, then appends JSON objects under an exclusive file lock. Every append is
flushed and fsynced, and raw response text is not stored. Before a possible
billed call, an `attempt_started` row must be durable. Multiple samples from one
Tinker request share `call_id` and have distinct `sample_index` values. A failed
logical call appends one error row.

## Schema version 3

Schema v3 preserves every v1/v2 result field, adds record types, billing-join
identifiers, a prompt-token projection bound, and control records for sink,
environment, and live-capability decisions. Existing rows remain valid historical
records and are never rewritten.

Every `result` row contains:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `3` for new rows; historical rows remain untouched. |
| `record_type` | `result` for response/error rows; control rows use `sink_preflight`, `environment_verified`, `environment_validation_failed`, `live_blocked`, or `attempt_started`. |
| `record_id` | Unique UUID for this row. |
| `call_id` | UUID shared by all samples from one logical SDK call. |
| `probe_name`, `probe_kind` | Stable probe identity and category. |
| `classification` | `smoke` or `exploratory`; the default-cap omission is always exploratory. |
| `status` | `ok` or `error`. |
| `timestamp` | UTC ISO-8601 collection timestamp. |
| `model` | Exact configured Tinker target model ID; cap probes never alter it. |
| `requested_cap` | Requested `max_tokens`, or null only for the isolated default-cap diagnostic. |
| `deliberately_omits_max_tokens` | True only for the labeled exploratory default-cap diagnostic. |
| `request_params` | The fields passed to `SamplingParams`; ordinary requests include `max_tokens`. |
| `num_samples` | Client-level sample count passed to `SamplingClient.sample`. |
| `sampling_session_id` | SDK sampling-session identifier when available, retained for later billing-export joins. |
| `request_id` | Provider/SDK request identifier when available, including on structured errors. |
| `billing_join_id` | Billing-export join identifier when available, including on structured errors. |
| `sample_index` | Zero-based index within `num_samples`, or null for an error. |
| `response_text_sha256` | SHA-256 of UTF-8 response text; null for an error. Raw text is not recorded. |
| `usage.prompt_tokens` | Locally tokenized prompt length. |
| `usage.completion_tokens` | Count of token IDs returned by Tinker for this sample. |
| `usage.prompt_cache_hit_tokens` | SDK-reported prompt cache-hit count. |
| `usage.billed_completion_tokens` | Reserved for per-call billing evidence; null because `SampleResponse` does not provide it. |
| `stop_reason` | Exact SDK value collected with the response. |
| `latency_seconds` | Wall-clock latency for the logical call. |
| `returned_tokens_exceed_requested_cap` | Returned-token cap comparison; null when no cap was requested or the call failed. |
| `projected_cost_usd` | Finite pre-call upper-bound projection for every logical call, including the deliberate omission. |
| `cost_projection_output_token_bound` | Finite output-token quantity used only to bound projected cost. It equals requested `max_tokens` for ordinary probes and 32,768 for the deliberate omission. |
| `cost_projection_prompt_token_bound` | Published model context length charged as a conservative full-prompt upper bound; for multi-sample requests, remaining prompt passes are additionally bounded at the cached-prefill rate. |
| `cost_authorization_usd` | Human-supplied authorization for the deliberate omission; null for ordinary probes. |
| `pricing_source`, `pricing_as_of` | Provenance for the cost projection. |
| `sdk_version` | Tinker SDK version observed at collection. |
| `python_version` | Python runtime observed at collection. |
| `environment_lock_sha256` | SHA-256 of the hash-locked probe requirements used for the run. |
| `error` | Null on success; otherwise an object with exception type and message. |

Control records are deliberately smaller. All carry `schema_version`,
`record_type`, `record_id`, `timestamp`, and a status or reason appropriate to
the decision. `environment_verified` embeds the complete locked-environment
manifest. `live_blocked` embeds the inspected SDK capability and upstream-source
digests. `attempt_started` carries the exact model, request parameters, cap,
sample count, both cost bounds, authorization, and any identifiers known before
submission.

## Interpretation boundaries

- Default-cap evidence is interpretable only if the deliberately uncapped response
  ends with a length stop; its returned completion count is then an observed
  candidate for the server default, not documentation of a permanent guarantee.
- The default-cap request still omits `max_tokens`. Its cost projection uses
  GPT-OSS-20B's published 32K maximum sequence length as both a conservative
  32,768-token prompt bound and a 32,768-token output bound. A live run must
  explicitly pass
  `--authorize-default-cap-cost-usd`; the amount must cover the projection and
  cannot exceed $0.03. This is a financial authorization bound, not a substitute
  request parameter and not evidence of the server default.
- Distinct hashes among `num_samples=8` are a sanity check, not proof of statistical
  independence. Identical hashes do not by themselves prove dependence.
- `stop_reason` values are reported exactly as observed. The inspected Tinker 0.25.0
  type currently declares `"length"` and `"stop"`; the live report, not the type
  declaration, is the empirical vocabulary result.
- `returned_tokens_exceed_requested_cap=false` is not evidence that billed tokens
  respected the cap. The SDK response has no per-call billing receipt, so billing
  reconciliation remains outstanding.
- Every cap, including 65,536, is sent to the same exact target ID within a panel:
  `thinkingmachines/Inkling` or `openai/gpt-oss-120b`. The tool never substitutes
  an extended-context or PEFT model. A rejection is appended as an error for that
  exact model/cap, the remaining independent cap probes continue, and the process
  exits nonzero after printing the complete summary.
- `reap/08_HYPERPARAMETER_DECISIONS.md` separately requires OpenAI
  gpt-5.6-terra usage-accounting sanity. This Tinker-only report does not address
  or clear that preregistration blocker.

## SDK contract inspected

The implementation is pinned to CPython 3.12.8 and the official Tinker Python SDK
0.25.0. `scripts/tinker_probe_requirements.lock` pins all 42 resolved packages and
their artifact hashes; new report rows record that lock's SHA-256. Create the
environment without making any provider call:

```sh
uv venv --python 3.12.8 .venv-tinker-probe
uv pip sync --python .venv-tinker-probe/bin/python \
  --require-hashes scripts/tinker_probe_requirements.lock
```

Before live client construction, the tool verifies CPython plus the exact set of
42 installed distribution versions against the lock (missing, changed, and
unexpected distributions all fail closed) and fsyncs the complete verified
manifest to the evidence sink.

Pinned Tinker 0.25.0 is **not live-usable by this tool**. Inspection and an
integration challenge against its actual internals establish that
`SamplingClient._sample_async_impl` resubmits after the SDK's HTTP-429 sentinel,
and that it wraps submission in `InternalClientHolder.execute_with_retries`.
`RetryConfig(enable_retry_logic=False)` controls only a separate outer retry
handler and cannot guarantee one billed submission. The SDK exposes no
documented one-attempt mechanism that disables both inner paths. Consequently,
`--live` fsyncs `sink_preflight`, `environment_verified`, and `live_blocked`, then
exits before `ServiceClient` or any injected adapter factory can be constructed.
No Tinker fact is settled until a later pinned SDK provides an upstream-supported,
verified zero-resubmission mechanism and a human authorizes execution.
