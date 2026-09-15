# Exploratory Inkling accounting approval — 2026-09-07

Connor approved the September 6 accounting proposal in the current task on
September 7, after being asked explicitly about both the settlement policy and
ceilings. The reply was: "I approve this".

Approved scope:

- One 1,000-item medium-effort stage, maximum $250.
- One conditional 1,000-item max-effort stage, maximum $250; $500 combined.
- Both use the same selected items, prompts and 32,768-token output cap.
- Reserve the entire stage's validated worst-case cost before its first request.
  Retain the reservation until delayed aggregate billing is reconciled.
- Max requires complete, valid medium results, zero reported cap stops and
  reconciled medium billing. Unknown attempts cannot be retried automatically.
- Preserve the $3,000 research reserve. Paid Omni-MATH/WildBench judging and all
  other experiments are excluded.

This approves implementing the policy and conditional spending ceilings. It does
not verify the reported account balance, endpoint credit eligibility, applicable
prices, input bounds, cap semantics or billing attribution. The human launch
remains conditional on that evidence and independent implementation review.
Codex does not run paid generation or provider probes. This is exploratory work;
frozen preregistrations and confirmatory gates remain unchanged.

The original reasoning and conditional price arithmetic remain in
`ACCOUNTING_PROPOSAL.md` as the historical proposal. This dated decision supersedes
its "proposal only" status for the policy and ceilings, not its unverified facts.
