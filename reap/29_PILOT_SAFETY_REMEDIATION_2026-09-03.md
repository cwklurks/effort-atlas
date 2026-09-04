# Exploratory pilot safety remediation — 2026-09-03

Status: implemented and verified offline on `codex/pilot-safety`.
This is not a preregistration, a Task E runner, or permission to spend money.

The September 3 audit identified request, accounting, integrity, and grading
failures on governance commit `7b2e1f750d55eb0459fca12da549accbc4b7dade`.
The user authorized repairing them and using independent subagents. No network,
provider, smoke, or confirmatory calls are part of this work.

## Scope and checks

| Audit | Repair | Acceptance check |
|---|---|---|
| F01, F06 | Dry default; disable legacy paid sweep; strict pilot approval bound to actual configuration and rendered selection | No SDK construction for missing, malformed, or stale approval |
| F02, F03 | One durable account ledger, locked reservation before submission, unresolved charges stop the pool | Restarts, stages, concurrent reservations, and failures cannot reset exposure |
| F04, F07 | Protected request fields, one response, zero retries, sanitized typed errors | Inspect actual serialized request and interrupted/error streams offline |
| F05, F10 | Validate route, cap, usage and IDs; reconcile receipts; inclusive output accounting | Mismatched or unavailable receipts stop; reasoning tokens charged once |
| F08, F09 | Scope cache by run and item; recompute source and selection hashes | Cache creates no fresh charge or independent replicate; tampering refuses |
| F11, F12 | Import accepted strict grader; correct even-sample median | Archived 78-row acceptance and explicit median fixtures |
| S01 | Separate heuristic forecasts from an approved input allowance | Reserve the allowance; refuse oversize requests and accounting breaches |

The integration owner maintains the spending and runner changes. Independent Sol
XHigh workers own request safety, source integrity, and importing the already
accepted grader. A separate review follows integration. Verification uses the
existing Python 3.12.8 environment and synthetic/offline inputs only.

All shipped live switches remain false and approval values unset. Human route,
price, balance, input allowance, selection, and mock-review evidence is still
required. The Inkling ceiling stays at $60. Frozen artifacts and observational
statistics remain unchanged. Unknown billing is retained conservatively; a
missing generation ID cannot be cleared by automatically resubmitting a request.

## Runtime behavior

The legacy sweep defaults to dry-run and refuses its paid path. Pilot CLI and
direct `run()` calls validate the same configuration, source bytes, rendered
requests, and human approval before constructing a real client. The client
enforces one response, explicit cap and effort, zero retries, no redirects, and
protected request fields. Credentials come from environment variables; custom
authorization headers and unknown pilot configuration fields are rejected.

The authoritative live account ledger is
`~/.local/state/effort-atlas/openrouter/attempts.jsonl`, shared by checkouts on the
same host. It is not selected through the config or output directory. A locked
read/check/reserve transaction writes and fsyncs the reservation before every
submission. Model and dataset ceilings persist across stages and labels. A
changed ceiling requires explicit reconciliation, not another automatically
created budget. Mock ledgers stay in their own output directories.

Completed job identities are skipped on resume; a different provider spelling
does not create a new job. An unjournaled cache entry stops execution rather than
creating a second observation or pretending to be free new work. Response files
have unique invocation IDs; approval manifests are immutable and content-free.
Response/cache files can contain echoed restricted text and remain gitignored.

Each live response is checked against the requested provider, cap and input
allowance, then joined to its receipt before the next submission. Receipt cost
must agree within 20% with the approved rates applied to actual usage and, when
present, streamed cost. Reasoning usage is a subset of completion usage. A length
stop below the requested cap or a filtered response does not enter the natural
length summaries. Even-sample uncensored medians use both middle observations.

Receipt fetches retry up to three times, using the same generation ID; generation
requests never retry. Unresolved attempts retain at least the reserved amount,
increased when a larger same-generation charge is known. Interrupts, unavailable
receipts, malformed accounting and identity conflicts stop the account. A human
must reconcile these before further collection. There is intentionally no
automatic reset or retry command for an unknown charge.

## Human evidence contract

The dry run writes `rendered_manifest_<digest>.json`. Fill actual balance and
price values/dates before generating the manifest for review. Its digest binds
the configuration, selection, rendered inputs, execution hostname and ledger
path. The following fields remain unset in shipped configs:

- `pricing.verified_on`
- `budget.balance_verified_usd` and `balance_verified_on`
- `budget.preflight_approved_by` and `approved_run_sha256`
- `budget.approval_evidence`, an object with `path` and `sha256`

The evidence file is JSON with `run_sha256`, `approved_by`, `approved_on`, `checks`
and `artifacts`. Both latter objects must contain `balance`, `pricing`, `route`,
`input_allowance`, `human_mock` and `data_spotcheck`. Each check must be the boolean
`true`; each artifact must identify a nonempty file by `path` and `sha256`.
Evidence files are confined to `reap/` or `results_pilot/`. Whitespace files,
changed bytes, malformed dates and stale manifest hashes fail closed.

Hashes establish which records were reviewed; the truth and authorship of the
human evidence remain a human responsibility. A new host/account requires
explicit ledger migration and reconciliation before approval. A hostname-bound
approval cannot simply be copied to another machine.

The input reservation is 65,536 tokens per request, with a 60,000-byte serialized
message admission limit. These are conservative proposed allowances requiring
route evidence, not a claim that characters divided by three bounds tokens.
The old heuristic remains only an expected-cost forecast. With current unverified
prices, all-at-cap reservation totals are $195.136 for Inkling, $38.7456 for GLM,
and $332.8128 for Qwen. The ceilings remain $60, $30 and $270, so staged collection
can halt before finishing the selection. No funding increase was made.

## Verification and remaining boundaries

- Canonical `./scripts/verify_offline.sh` passed on Python 3.12.8 with a
  process-wide network-denial hook: 203 tests ran, 202 passed, one optional
  exact-root benchmark-source rebuild skipped because its source root is unset.
  The archived grader test was enabled and passed. Source validation, dashboard
  freshness and the Linux handoff manifest checks passed.
- Imported grader implementation, acceptance verifier, fixture and tests are
  byte-identical to accepted commit `9a54f1743477cd55335ccf6523580e01a517d2be`.
  Actual archived verification reproduced 78 unanswered clipped rows.
- A network-blocked full Inkling mock produced 1,000 observations and a verified
  ledger, with simulated cost $20.5850747. Resume produced zero new observations
  and preserved spending. Ledger/manifest content checks found no rendered prompts.
- All three real selections/config combinations were dry-run offline. Both
  alternative 1,000-item selections passed source and restricted-row integrity
  verification in the independent integrity workstream.
- Independent reviews covered client, source integrity, receipts, grading,
  accounting and approval gates. Review-discovered redirect, conflicting-identity,
  checkout-reset, empty-evidence, authorization-header and provider-case bugs were
  repaired and regression-tested.

The installed SDK discards top-level usage carried only on an SSE error event
before yielding it. An actual-SDK test records this limitation: previously seen
IDs survive, unavailable usage stays unknown, and the full reservation is kept.
No substitute upstream stream parser was introduced.

This branch imports the accepted strict grader for the legacy sweep. It does not
merge the separate analysis branch, freeze REAP, implement Task E, or establish
current provider, pricing or balance facts. Historical main/PR status elsewhere
in the dashboard must not be mistaken for what this checkout has integrated.
