# Inkling baseline preparation — 2026-09-06

Status: offline preparation implemented; live accounting decision outstanding. No paid calls made by Codex;
all live switches and machine-verifiable approval fields remain disabled/unset.
This dated note records the current decision without changing frozen history.

## Accepted direction

Connor reported advisor agreement after the September 6 meeting and accepted
these recommendations in the current task:

- Keep the existing seeded stratified selection: 200 items from each of five
  datasets, 1,000 total. The allocation is not 13 per category.
- Use Inkling through Tinker; Connor reports $5,000 of Tinker credits. This is a
  reported pool balance, not a verified account receipt or a run spending ceiling.
- Start at explicit medium effort with an explicit 32,768-token output cap.
  If no capped responses occur, the proposed next stage uses the same questions,
  prompts and cap at maximum effort; retain and report both stages separately.
- Start from original evaluation templates; adapt only the final-answer format
  where strict extraction requires it. Preserve IFEval instructions and WildBench
  conversations. Remove the custom "Think as much as you need" addition.
  The prepared prompts import pinned HELM constructors. The adaptations are
  documented in `reap/inkling_baseline/README.md`; this is not an exact HELM replay.
- Score MMLU-Pro/GPQA by the recorded option mapping, IFEval by imported official
  checks. Omni-MATH scoring remains pending its official paid evaluator; defer
  WildBench quality judging.
  No pooled five-dataset gold-answer accuracy is justified.

## Box and implementation checkpoint

SSH to `box` works. Linux has Python 3.12.8 available through uv, Git and tmux.
Existing pilot checkouts are on older governance code; preserve them and prepare
an isolated checkout from the local safety branch.

The September 4 receipt-settlement finding is reproduced by two new offline
regressions, including the actual runner path and journal reload. Settlement now
compares the billed amount with the original reservation, not subsequently raised
known exposure. A breach remains unresolved and prevents a second submission.
The focused accounting/runner suite passes 22 tests using synthetic transport only.
The canonical offline suite passes on Python 3.12.8: 205 run, 204 passed, one
optional exact-root source rebuild skipped. Archived grader verification passes;
a process-wide socket guard blocks network access during verification. The Linux
handoff digest was regenerated after the briefing change.

## Offline implementation checkpoint

`python -m effort_atlas.inkling_baseline` defaults to dry-run preparation and has
no live path. It prepares medium/max request hashes for the same 1,000 source
items, pinned model, explicit cap, temperatures and prompts. Private request and
synthetic response files stay local and gitignored. Missing inputs, changed
source hashes or failed imports refuse preparation; upstream renderers and the
Google IFEval evaluator are imported, not reconstructed.

The pinned Anthropic-compatible client serializes one POST in offline transport
tests, including failure, timeout and redirect cases. This is client-level test
evidence only. It does not establish backend billing, retry or cap semantics.
The legacy Tinker 0.25.0 probe remains blocked and unchanged.

The OpenRouter pilot now reports dataset-by-effort cells, with response and error
denominators separate. Historical pooled dataset summaries are explicitly labeled.
Termination reasons remain separate from strict extraction and dataset scoring.

## Verification on Mac and box

Python 3.12.8 canonical suite: 210 run, 209 passed, one optional exact-root source
rebuild skipped. The archived 78-row grader acceptance passes. Nine supplemental
tests exercise actual pinned upstream imports and the Anthropic SDK's offline
transport. A 1,000-item synthetic rehearsal passes on both hosts with identical
plan hash `5b4688415f8da85c7d32c75903978b68192dbab7558aeef6ec90bfd0f0c74d37`.
Python socket access is denied during all verification; model calls are zero.

The isolated box checkout is `/home/connork/code/inkling-baseline-20260906`.
Source validation correctly rejected dataset symlinks outside that checkout;
private copies from existing files on the same box satisfy the original boundary.
No restricted question text, private responses or credentials were transferred
from the Mac. The original box checkout and source files were preserved.

## Remaining human/accounting gates

Tinker's documented hourly billing export has token quantities and can lag by
hours; it does not supply the existing runner's per-generation dollar receipts.
`reap/inkling_baseline/ACCOUNTING_PROPOSAL.md` proposes reserving a whole stage
upfront, then reconciling aggregate usage and account deductions before any next
stage. Proposed ceilings are $250 medium and $250 conditional max, subject to
verified route-specific rates, token allowances and credit eligibility. No ceiling
or change to settlement policy is approved by this note.

After a human policy decision, implement and independently review the accounting
path and human launch gates. Account access, prices, cap semantics, input admission,
billing attribution and available credits remain unverified. A second stage needs
complete, valid medium results and reconciled billing. No confirmatory execution
or change to frozen research artifacts is included.

Primary references consulted September 6:

- https://tinker-docs.thinkingmachines.ai/tinker/compatible-apis/anthropic/
- https://tinker-docs.thinkingmachines.ai/tinker/models/
- https://tinker-docs.thinkingmachines.ai/tinker/cli/billing/

These are documentation, not empirical account or provider evidence.
