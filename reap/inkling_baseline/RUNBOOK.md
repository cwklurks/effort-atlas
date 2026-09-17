# Inkling exploratory stages: human runbook

The September 7 decision approves a $250 ceiling for medium and a separate $250
ceiling for conditional max. The $3,000 research reserve stays protected. This is
not permission to skip route/account evidence or to run confirmatory collection.
The September 15 first-five decision permits explicitly assumed pricing, credit eligibility and cap/usage semantics for the initial medium observations. Codex runs only the offline and synthetic commands below.

## Box checkout and offline preflight

Use `/home/connork/code/inkling-baseline-20260906`. Commands below use a POSIX shell;
run `bash` first if the box opens fish. No GPU service is required.

```sh
cd /home/connork/code/inkling-baseline-20260906
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --dry-run --first-five --write-evidence-template results_pilot/inkling-stage-evidence/launch-first-five-template.json
```

The command prints the exact preparation and execution hashes. The first-five template's
account fields are empty and checks false. Its three provider assumptions are explicit. Regenerating changed code or prompts
invalidates earlier execution approval. Keep credentials out of every JSON file.

`./scripts/verify_inkling_baseline.sh` runs the canonical offline suite, supplemental
upstream/SDK checks and synthetic rehearsals with Python socket access denied.
Synthetic records stay separate from collection and never count as observations.

## Evidence needed before a human launch

Set `TINKER_API_KEY` locally in the launching shell. It was absent from the SSH
environment checked September 7. Do not paste it into the task or commit it.
The key must be exported in the same terminal that runs the command; a new
terminal does not inherit an earlier shell export. `api_key_missing` means that
this launching shell has no key, not that Tinker rejected the credential.

The initial medium launch uses `inkling-first-five-evidence-v1`. Preserve the
explicit assumptions for pricing, credit eligibility and cap semantics and leave
those three checks **false**. Bind the public prices and available provider
correspondence as supporting artifacts, without claiming account-specific
verification. This is the exception Connor accepted on September 15, not a
confirmatory approval. No email is mandatory.

The balance, billing attribution, independent code review and input-count checks
still require real evidence. The launch binds the account, host, current execution,
question plan and dated first-five decision. Review the launch record before
running it. Set its approval/expiry at launch time (at most 24 hours), inside an
explicit whole-hour UTC billing window. An old blank or populated September 10/11
record is not a valid launch for the changed code.

The full-stage reservation uses the documented **assumed** rates. It must remain
within $250 and protect the $3,000 reserve. This is a local exposure calculation,
not a provider-enforced dollar ceiling if the assumptions turn out to be wrong.
All 1,000 counts are required; the maximum input allowance is 32,768 and input plus
output must fit the documented context window.

The documented token-count endpoint uses the real tokenizer without sampling.
This is a separate human-initiated provider operation; Codex does not execute it
or assert it is free. After reviewing the operation and preparing the key:

```sh
export EFFORT_ATLAS_INKLING_COUNT_ACK=I_APPROVE_INPUT_TOKEN_COUNTING
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --stage medium --count-inputs results_pilot/inkling-stage-evidence/input-counts-medium.json
```

Reference that file and its hash in `artifacts.input_counts`. Other evidence
artifacts document the independently checked facts, not a fabricated receipt.
The code requires every non-assumed human check; it cannot verify the truth of a signed
account statement or a reviewer's attestation by reading its hash.

## Human collection

Only after the evidence record is complete and the exact execution reviewed:

```sh
export EFFORT_ATLAS_INKLING_LIVE_ACK=I_ACCEPT_THE_FIRST_FIVE_ASSUMPTIONS
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --stage medium --evidence results_pilot/inkling-stage-evidence/launch-first-five.json \
  --live
```

This sends at most the first five questions of the same 1,000-item medium plan,
**cumulatively across invocations**. The journal enforces the limit even if a caller
omits `--max-new-requests`, restarts, or supplies another launch record. Optional
`--max-new-requests N` may pause sooner but cannot extend this initial authority.
The five remain ordinary exploratory baseline observations; the full reservation
stays held. Unknown attempts stop without retries.

After five complete responses, the command prints `invocation_status:
"paused_for_review"` and the path of a **blank** continuation-review template.
A repeated launch sends nothing and does not construct a provider client. A cap
stop leaves continuation blocked and requires scientific review.

Inspect all five raw responses, reported usage and stop reasons, plus the extracted
answers and grades. Record the available billing evidence and its limitations.
Five normal completions do not verify what happens at the cap. Do not change the
question plan based on these answers or invent exact dollar receipts.

Complete the generated review template only after a separate human decision to
continue. It binds all five response hashes, the account, plan and current execution;
requires review notes and a billing-evidence artifact; and explicitly records
acceptance of any residual provider assumptions. Review time must follow the saved
responses and be within 24 hours. The initial first-five approval does not approve
this future review. Keep `authorize_remaining` false until that decision is made.
A separately authorized continuation uses the same current launch evidence:

```sh
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --stage medium --evidence results_pilot/inkling-stage-evidence/launch-first-five.json \
  --review-first-five results_pilot/inkling-stage-evidence/review-first-five.json --live
```

The review releases the request limit, not the financial reservation. Saved rows
are authenticated and skipped. Once the review is recorded, subsequent restarts
omit `--review-first-five`; reapplying a review refuses. Expired launch evidence
must be renewed for the same account, rates, allowance and billing window.
Keep the reviewed execution unchanged: a code change after continuation review refuses further collection and needs an explicitly reviewed migration. Pre-existing unrestricted medium reservations also refuse under this runner; never erase the ledger to bypass that check. Reconciliation and the separate max-stage conditions below remain in force. Max
requires fully verified ordinary launch evidence and cannot use this exception.

Run in a persistent terminal session such as tmux. The process holds a host-wide
account lock and keeps its journal in
`~/.local/state/effort-atlas/tinker/inkling-stages.jsonl`. A fresh checkout does not
reset this journal. Do not delete, replace or copy it to bypass a held reservation.
The host lock cannot stop unrelated users or programs spending the account's
credits; the billing-isolation evidence must cover that operational requirement.

Each request gets a durable local submission ID before transmission. A private
response envelope preserves the exact response bytes, the returned request header
when present, timestamps and execution/evidence hashes. Its SHA-256 is bound into
the ledger. Visible answers and reasoning are kept separate; only visible answer
text is graded. No per-response actual dollar cost is invented.

A clean restart skips already-recorded responses only when their private hashes
match. Changed stage rates, input allowance or billing window refuse continuation.
An uncertain, interrupted, malformed or over-bound attempt blocks the stage and
keeps its reservation. No automatic retry or uncertain-attempt recovery is included.

## Reconcile before considering max

Wait for the billing window to close and the delayed export to be complete. Export
the official JSON usage response for the exact window; preserve it unedited.
The reader sums sampling token quantities from those rows. It rejects duplicated,
malformed, cached or unrelated usage instead of guessing a rate or hiding a charge.

Copy `reconciliation.template.json` and `account-deduction.template.json` from
this folder into the private evidence directory, then complete them from the
actual export and the human-reviewed account statement. Bind the original statement files and raw export by SHA-256.
The statement reading provides the actual account deduction; it is not calculated
from reported generation usage. The accounting journal compares the exported
input/output totals and actual deduction with the attempts and approved rates.
Missing or mismatched evidence retains the reservation. The v1 implementation
requires an exact, unrounded account deduction; a display rounded to cents alone
is insufficient. It admits exports observed at least four hours after the window
ends, with a current human completeness review. That buffer is a project rule,
not proof that the provider has finished reporting.

```sh
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --stage medium --evidence results_pilot/inkling-stage-evidence/launch-medium.json \
  --reconcile results_pilot/inkling-stage-evidence/reconciliation-medium.json
```

Max requires all 1,000 medium responses valid, zero reported cap stops and completed
billing reconciliation. Prepare a fresh max-stage launch record and input counts,
using the same question plan and a later isolated billing window. A max launch can
reserve at most another $250. Paid Omni-MATH/WildBench judging is excluded.
