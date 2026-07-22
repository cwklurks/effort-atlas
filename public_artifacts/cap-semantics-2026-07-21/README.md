# Cap Semantics Probe evidence bundle

This bundle is the public evidence derivative for the exploratory Cap
Semantics Probe recorded in `CAP_SEMANTICS.md`. It contains 13 result/error
rows and eight OpenRouter billing-receipt excerpts. It includes the two 2,000-
token observations for each newly probed route, their recorded 429 attempts,
and the earlier Grok/xAI 20,000-token observations and recorded failed attempt.

## Files

- `results.jsonl`: sanitized response and error-row metadata in original source
  and line order.
- `receipts.jsonl`: the usage, route, finish, latency, cost, and opaque linkage
  fields needed to audit the result-to-receipt relationship.
- `manifest.json`: private-source hashes, public-output hashes, source IDs,
  record counts, and the exporter commit.
- `dataset_manifest.json`: source-level hashes for the audited math and
  extraction datasets, without prompts or labels.
- `schedule.jsonl`: empty. This exploratory audit predated the confirmatory
  study's fixed-schedule protocol.

## Source map

| Source ID | Route or event |
|---|---|
| `result-0001`, `receipt-0001` | GPT-OSS 120B through DeepInfra |
| `result-0002` | Inkling/Together first attempt, including the 429 row |
| `result-0003`, `receipt-0002` | Inkling/Together successful rows and receipts |
| `result-0004` | Kimi K2.6/Moonshot first attempt, including the 429 row |
| `result-0005`, `receipt-0003` | Kimi K2.6/Moonshot successful rows and receipts |
| `result-0006` | Earlier Grok/xAI failed attempt |
| `result-0007`, `result-0008`, `receipt-0004` | Earlier Grok/xAI 20,000-token rows and receipts |

No row was deduplicated, repaired, interpolated, or reconciled during export.
Missing fields remain JSON `null`. Raw source files remain local and ignored by
Git; their exact SHA-256 digests are recorded in `manifest.json`.

