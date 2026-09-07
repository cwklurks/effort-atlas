# Inkling exploratory stages: human runbook

The September 7 decision approves a $250 ceiling for medium and a separate $250
ceiling for conditional max. The $3,000 research reserve stays protected. This is
not permission to skip route/account evidence or to run confirmatory collection.
Codex runs only the offline and synthetic commands below.

## Box checkout and offline preflight

Use `/home/connork/code/inkling-baseline-20260906`. Commands below use a POSIX shell;
run `bash` first if the box opens fish. No GPU service is required.

```sh
cd /home/connork/code/inkling-baseline-20260906
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --dry-run --write-evidence-template results_pilot/inkling-stage-evidence/launch-medium.json
```

The command prints the exact preparation and execution hashes. The template's
account fields are empty and checks false. Regenerating changed code or prompts
invalidates earlier execution approval. Keep credentials out of every JSON file.

`./scripts/verify_inkling_baseline.sh` runs the canonical offline suite, supplemental
upstream/SDK checks and synthetic rehearsals with Python socket access denied.
Synthetic records stay separate from collection and never count as observations.

## Evidence needed before a human launch

Set `TINKER_API_KEY` locally in the launching shell. It was absent from the SSH
environment checked September 7. Do not paste it into the task or commit it.

Verify the exact compatible endpoint and model's eligibility for the account's
credits, dated input/output rates, available balance, reasoning-inclusive output
cap, served context size, and isolated billing attribution. The documented prices
are not evidence of this account's applied rate. No automatic price increase is
allowed if the whole-stage worst-case bound exceeds $250.

The launch record binds those facts to local evidence files by SHA-256, the
current code, question plan, stage, host and account. It must be human-reviewed,
currently valid, and within an explicit UTC billing window aligned to whole hours.
The v1 record lasts at most 24 hours. It requires actual input counts for every
stage request, within an input allowance no larger than 32,768 and a context size
large enough for that allowance plus the output cap.

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
The code requires every named human check; it cannot verify the truth of a signed
account statement or a reviewer's attestation by reading its hash.

## Human collection

Only after the evidence record is complete and the exact execution reviewed:

```sh
export EFFORT_ATLAS_INKLING_LIVE_ACK=I_HAVE_VERIFIED_THE_STAGE_EVIDENCE
PYTHONPATH=src .cache/inkling-baseline-env/bin/python -m effort_atlas.inkling_stage \
  --stage medium --evidence results_pilot/inkling-stage-evidence/launch-medium.json --live
```

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
