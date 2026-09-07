# Inkling baseline preparation — 2026-09-06

Status: exploratory preparation in progress. No paid calls made by Codex;
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
  Template provenance and implementation still need verification; do not label
  the current custom wrapper as an exact or completed HELM adaptation.
- Score MMLU-Pro/GPQA by the recorded option mapping, IFEval by imported official
  checks, and Omni-MATH by its official evaluator. Defer WildBench quality judging.
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

## Remaining preparation

1. Verify/import original benchmark prompt logic and document exact adaptations.
2. Prepare Tinker-specific request serialization and offline verification. The
   old OpenRouter config cannot spend Tinker credits and must not be relabeled.
3. Establish Tinker route, credit eligibility, reasoning-inclusive cap semantics,
   token accounting and billing joins. Current documentation is not empirical
   evidence that the earlier pinned SDK retry blocker is resolved.
4. Add per-effort summaries and validated dataset-specific scoring.
5. Validate source bytes, request manifests, budget projections and the canonical
   offline suite on the isolated box checkout before a human launch.

Tinker primary references consulted September 6:

- https://tinker-docs.thinkingmachines.ai/tinker/compatible-apis/anthropic/
- https://tinker-docs.thinkingmachines.ai/tinker/models/

These describe a compatible inference API and route-dependent prices. They do
not establish account credit eligibility or settle this project's receipt gates.
