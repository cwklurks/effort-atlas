# Approved Inkling stage accounting — 2026-09-07

Connor approved whole-stage reservation with deferred aggregate reconciliation,
$250 for medium and $250 for conditional max ($500 combined). The dated approval
record is `reap/inkling_baseline/ACCOUNTING_APPROVAL_2026-09-07.md`; the machine-readable
policy is `reap/inkling_baseline/approved_policy.json`. Preserve the $3,000 reserve.

## Implemented scope

The separate Tinker stage command defaults to offline preflight. Its human live
path binds the exact plan, code, policy, host, account, billing group, input counts,
rates, balance and current launch evidence before creating a client. The original
OpenRouter pilot settlement remains unchanged. No confirmatory path or frozen
artifact is changed.

An account-wide journal reuses the existing append/fsync/hash-chain ledger and a
transaction lock. It reserves the full worst-case stage cost before any attempt,
retains exposure between responses, blocks uncertain outcomes and refuses duplicate
submissions. An independent process lock covers the collection session. A new
checkout cannot reset the account journal. The lock does not police unrelated
account users or other hosts; dedicated billing isolation remains an operational
requirement supported by human evidence.

Raw response envelopes bind exact bytes, returned request metadata, execution and
launch-evidence hashes. Private writes use owned 0700 directories, owned regular
0600 files, descriptor-relative operations and no-follow path traversal. Completed
responses are authenticated before resume; missing grade files are deterministically
restored from authenticated raw data, while altered grades refuse continuation.

The billing reader accepts the documented official JSON response shape only and
computes token sums directly. It refuses mixed attribution, duplicate buckets,
cached input, unsupported usage, changed schemas and incomplete/future evidence.
A separately reviewed account deduction is compared with the exported token totals,
the attempt totals, the exact approved rates and the original reservation. No
per-response actual dollar cost is invented. A four-hour post-window buffer is a
conservative project admission rule; completeness and the account statement reading
remain human attestations, not cryptographic provider proof.

Max must use the same plan and accounting rates, follow a non-overlapping billing
window, and have complete reconciled medium results with zero reported cap stops.
Unknown requests have no automatic retry or recovery path.

## Verification

Mac and box Python 3.12.8: canonical 251 run, 250 passed, one optional exact-root source
rebuild skipped; archived grader acceptance passed. Twelve supplemental tests pass,
including actual pinned upstream prompts, SDK one-request transport, successful
collection/resume, missing-grade restoration and error/restart behavior. Both the
1,000-item synthetic grading rehearsal and 1,000-item stage-accounting rehearsal
pass with Python networking denied. Independent Sol XHigh review is clean after the repairs below, with 41 focused
tests passing. The full box verification completed in 80 seconds with zero model
calls and the same preparation hash:
`345e5727528d8af0ea208e2a0b266d33093f241fdf2744423e444bc49abc6320`.

Independent review discovered and regression-tested omitted billing-code binding,
a direct-call input-counting bypass, missing grade validation on restart, private
file/path weaknesses, and future-dated billing evidence. These were repaired before
handoff. Detailed operational steps and blank evidence templates are in
`reap/inkling_baseline/RUNBOOK.md`.

## Facts still needed for human execution

SSH to `box` works. `TINKER_API_KEY` was absent from its SSH environment when
checked September 7; its value was never read or printed. Account credit eligibility,
current balance, applied prices, input counts/context bounds, inclusive cap semantics
and isolated billing attribution remain unverified. The approval is recorded; these
are evidence requirements, not another request to approve the same ceilings.

No generation, tokenizer, billing-provider or smoke call was made by Codex. The
only network operations were public documentation reads and code/checkpoint work
on the user's box and repository. All model call counters remain zero.
