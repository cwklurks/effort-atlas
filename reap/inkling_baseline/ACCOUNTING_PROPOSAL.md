# Tinker accounting decision — 2026-09-06

Status: proposal only. No accounting rule, spending approval or live switch is
changed by this document. A human decision is needed before implementing the
different settlement policy described below.

## The concrete incompatibility

The current OpenRouter pilot joins every completed response to a per-generation
dollar receipt before sending the next request. See the runtime behavior in
`reap/29_PILOT_SAFETY_REMEDIATION_2026-09-03.md` and `src/effort_atlas/pilot.py`.

[Tinker's documented export](https://tinker-docs.thinkingmachines.ai/tinker/cli/billing/)
provides hourly token quantities by model/session/user. It can lag by hours and
does not include dollar amounts. Its documented
[billing event](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/types/billingusageevent/)
has hourly/session attribution rather than a generation receipt identifier.

Consequently, the existing per-request receipt resolver cannot be relabeled as
a Tinker resolver. SDK tests demonstrating one POST do not establish a dollar
charge, a unique backend sample, or receipt reconciliation.

## Recommended policy to decide

For this exploratory baseline only, approve a separately capped batch with
deferred aggregate reconciliation:

1. Verify the exact endpoint/model's credit eligibility, dated prices, cap and
   input accounting before collection. Establish an unambiguous billing group:
   a dedicated session if this endpoint supports it, otherwise an isolated
   model/user/time window with no competing usage. If neither can be established,
   this proposal cannot support a run.
2. Reserve the entire maximum cost of the approved stage before its first
   request, rather than freeing money as individual usage reports arrive.
3. Preserve one append-only entry for every attempt, its request/response IDs,
   reported usage and native stop reason. Keep usage-based cost estimates clearly
   separate from actual account deductions. Do not claim per-response actual costs.
4. Stop immediately on an unknown request outcome, missing/invalid usage, a cap or
   input-allowance breach, or an exhausted reservation. Do not automatically retry
   or resume an uncertain attempt. Keep all unresolved exposure reserved.
5. After the billing export is complete, reconcile its token totals with the
   attempt records and check the account's credit deduction against the approved
   rates. Discrepancies retain the reservation and stop further stages. A second
   maximum-effort stage cannot begin while medium remains unreconciled.

This would replace immediate per-request receipt settlement with a documented
batch-level evidence standard. It requires a new implementation and tests after
the policy is accepted; it is not present in the offline preparation command.

## Concrete proposed ceiling

For the currently selected `thinkingmachines/Inkling` model,
[published discounted rates](https://tinker-docs.thinkingmachines.ai/tinker/models/)
read September 6 are $1.87 per million input tokens and $4.68 per million output
tokens. Those rates have not been verified against this account or compatible
endpoint. Different Inkling variants have different prices.

Conditional on those rates applying, all billed output being bounded by 32,768
tokens, and an approved maximum of 32,768 input tokens per request:

| Quantity for 1,000 requests | Calculation | USD |
|---|---|---:|
| All output at cap | 1,000 × 32,768 × 4.68 / 1,000,000 | 153.35424 |
| Full proposed input allowance | 1,000 × 32,768 × 1.87 / 1,000,000 | 61.27616 |
| Conditional stage reservation | Input + output | 214.63040 |

Propose **a $250 ceiling for medium and a separate $250 ceiling for a later max
stage**, $500 combined. These are proposals, not approved spending. The input
allowance must fit the served model's actual context window alongside the output
cap; 60,000 message bytes does not prove that condition.

This excludes paid Omni-MATH/WildBench judging and other experiments. It preserves
the existing $3,000 research reserve from the reported $5,000 pool. If the route,
discount, token semantics or available credit differs, recompute the bound and
obtain a concrete revised ceiling before any call. No automatic funding increase
is proposed.

## Alternative

Keep per-request dollar receipts mandatory and use Tinker only if it supplies an
additional receipt mechanism meeting that contract. Another platform with such
receipts would require its own funding; Tinker credits cannot be moved there by
changing a configuration label.
