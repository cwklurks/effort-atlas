# Tinker probe report format

**Status:** pre-confirmatory tooling contract. A report row is evidence only when
`status="ok"` and it came from a human-authorized `--live` execution. Dry runs do
not write report rows. Nothing in this format settles a scientific or platform
fact without live evidence.

`scripts/tinker_probe.py` appends one JSON object per returned sample to a JSONL
file. It opens the file only in append mode, flushes each row, and does not store
raw response text. Multiple samples from one Tinker request share `call_id` and
have distinct `sample_index` values. A failed logical call appends one error row.

## Schema version 1

Every row contains:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1`. |
| `record_id` | Unique UUID for this row. |
| `call_id` | UUID shared by all samples from one logical SDK call. |
| `probe_name`, `probe_kind` | Stable probe identity and category. |
| `classification` | `smoke` or `exploratory`; the default-cap omission is always exploratory. |
| `status` | `ok` or `error`. |
| `timestamp` | UTC ISO-8601 collection timestamp. |
| `model` | Exact Tinker model ID, including extended-context suffixes. |
| `requested_cap` | Requested `max_tokens`, or null only for the isolated default-cap diagnostic. |
| `deliberately_omits_max_tokens` | True only for the labeled exploratory default-cap diagnostic. |
| `request_params` | The fields passed to `SamplingParams`; ordinary requests include `max_tokens`. |
| `sample_index` | Zero-based index within `num_samples`, or null for an error. |
| `response_text_sha256` | SHA-256 of UTF-8 response text; null for an error. Raw text is not recorded. |
| `usage.prompt_tokens` | Locally tokenized prompt length. |
| `usage.completion_tokens` | Count of token IDs returned by Tinker for this sample. |
| `usage.prompt_cache_hit_tokens` | SDK-reported prompt cache-hit count. |
| `usage.billed_completion_tokens` | Reserved for per-call billing evidence; null because `SampleResponse` does not provide it. |
| `stop_reason` | Exact SDK value collected with the response. |
| `latency_seconds` | Wall-clock latency for the logical call. |
| `returned_tokens_exceed_requested_cap` | Returned-token cap comparison; null when no cap was requested or the call failed. |
| `projected_cost_usd` | Pre-call upper-bound projection; null for the diagnostic with an unknown server default. |
| `pricing_source`, `pricing_as_of` | Provenance for the cost projection. |
| `sdk_version` | Tinker SDK version observed at collection. |
| `error` | Null on success; otherwise an object with exception type and message. |

## Interpretation boundaries

- Default-cap evidence is interpretable only if the deliberately uncapped response
  ends with a length stop; its returned completion count is then an observed
  candidate for the server default, not documentation of a permanent guarantee.
- Distinct hashes among `num_samples=8` are a sanity check, not proof of statistical
  independence. Identical hashes do not by themselves prove dependence.
- `stop_reason` values are reported exactly as observed. The inspected Tinker 0.25.0
  type currently declares `"length"` and `"stop"`; the live report, not the type
  declaration, is the empirical vocabulary result.
- `returned_tokens_exceed_requested_cap=false` is not evidence that billed tokens
  respected the cap. The SDK response has no per-call billing receipt, so billing
  reconciliation remains outstanding.
- The 65,536-token probes use extended-context model IDs. Smaller caps use the
  intended standard routes. Results are route-specific and must not silently be
  pooled across those IDs; the route change itself must be resolved in the REAP
  panel design before preregistration freezes.
- `reap/08_HYPERPARAMETER_DECISIONS.md` separately requires OpenAI
  gpt-5.6-terra usage-accounting sanity. This Tinker-only report does not address
  or clear that preregistration blocker.

## SDK contract inspected

The implementation was checked against the official Tinker Python SDK 0.25.0
wheel and first-party API reference on 2026-08-08. The execution environment used
for development did not have Tinker installed, so live execution deliberately
fails with an installation error rather than falling back to a reimplementation.
The human live environment must install and review a compatible SDK before use.
