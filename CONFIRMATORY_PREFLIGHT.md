# Confirmatory preflight

`effort_atlas.confirmatory` is offline-only. It never imports the request
client, reads environment variables, or sends API calls. Its schedule contract
uses seed `20260722`, shuffles item blocks, permutes the four effort-by-cap
conditions within each item, and hashes canonical JSON with SHA-256.

The committed protocol fixes one replicate in `config_confirmatory.yaml`.
Two replicates are refused by the preflight code until a preregistration
amendment and budget top-up are made.

`AttemptLedger` appends every execution event (`success`, `error`,
`unaccounted`, `cache`, `replay`, or `manual_rerun`) with an execution ordinal,
UTC timestamp, schedule/job identity, route/accounting fields, and sanitized
accounting metadata. Generated ledger fields cannot be supplied by an event;
raw request/response/header/error payloads are rejected. The file is locked,
flushed, and synced before each append returns. Each row also links to the
previous row's SHA-256 and carries its own event hash; `AttemptLedger.verify()`
checks ordinal continuity and this chain before another event is appended.

`analyze_confirmatory_events` includes only expected-route, fully accounted
successes whose scheduled identity, served provider, native receipt tokens,
receipt generation ID, receipt provider, receipt cost, and normalized receipt
finish reason reconcile. Every valid success must also carry a boolean unchanged-
grader result and a boolean `extracted_answer_present`; a correct row without an
extracted answer is rejected as internally inconsistent. Native finish-reason text is retained as a required
nonempty accounting field but is not required to use the same provider
vocabulary as the normalized row finish reason. Valid observations retain the
full panel, model, provider route, item, effort, cap, and replicate identity;
cell summaries aggregate only over panel, model, provider route, effort, and
cap. Unscheduled or mismatched rows are excluded with a machine-readable
selection audit; reused generation IDs and duplicate valid jobs raise errors.
Native completion usage above the scheduled cap is excluded. Conventional accuracy
follows the unchanged grader even when the finish reason is `length`. Cell summaries
separately count all length stops, unanswered length stops, answer-present length
stops, and empty extracted answers. The simple accuracy upper bound adds only
unanswered length stops. Cell summaries include the reconciled receipt-cost total.
Caps are never deduplicated or
collapsed. This is an offline validator only: it is not wired to a paid
runner, does not make gates execute, and cannot itself authorize paid work.

After committing the preflight code, create the immutable, prompt-free
artifacts for that exact commit with:

```bash
PYTHONPATH=src .venv/bin/python -m effort_atlas.confirmatory \
  --output /path/to/new-artifact-directory \
  --exporter-code-commit <40-character-lowercase-commit-sha>
```

The exporter reads only audited item IDs and domains, writes separate main and
smoke schedules per panel plus a manifest of config/dataset/code hashes, the
configured preregistration commit identifier, and a SHA-256 of the configured
preregistration file and each configured pre-data amendment. These are recorded provenance values, not a claim that
the exporter verifies Git history or commit reachability. It refuses to
overwrite an existing output directory. It does not
run smoke checks or issue requests. Before creating the output directory it
validates every schedule and manifest in memory; the manifest keeps separate
internal schedule digests, emitted-file SHA-256 hashes, and configured code
provenance hashes.

Credential-like keys and common credential-looking strings are redacted as a
defense-in-depth measure before ledger persistence. This is not proof that an
arbitrary secret cannot be encoded in an otherwise innocuous value; callers
must still avoid supplying secrets to the ledger.

Run the offline tests with:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```
