# Thinking Cut Short

## Separating token starvation from completed negative scaling in reasoning models

**Connor Klann, Independent Researcher**  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)  
**Protocol status:** Preregistered in commit
[`bc941bf`](https://github.com/cwklurks/effort-atlas/commit/bc941bf118516cddafc671fcb9acc4607fd7ea33);
no confirmatory API response has been collected and new-study spend is $0.00
as of 2026-07-22.

The original preregistration is supplemented by the pre-data scoring amendment in
[`PREREGISTRATION_AMENDMENT_2026-07-22.md`](PREREGISTRATION_AMENDMENT_2026-07-22.md).
No confirmatory response existed when the amendment was made.

## Question

When higher native reasoning effort appears to reduce accuracy, how much of the
decline is caused by the model reaching an output limit before giving an answer,
rather than by a normally completed response giving a worse answer?

## Exploratory motivation, not confirmatory evidence

On one pinned OpenRouter-to-Together route for `thinkingmachines/inkling`, a
30-item AIME-25 pilot produced:

| Requested effort | Correct | Accuracy | `finish_reason="length"` |
|---|---:|---:|---:|
| medium | 25/30 | 83.3% (n=30) | 4/30 |
| max | 21/30 | 70.0% (n=30) | 9/30 |

All 13 length-stopped responses were graded wrong because they contained no
extractable final answer. In a separate exploratory rerun, one max-effort item
changed from a wrong 20,000-token length stop with no answer to a correct normal
stop after 38,603 completion tokens. This is one independent stochastic rerun, not a
continuation and not proof of a general rescue effect.

## Proposed confirmatory intervention

For each model route, run the same audited AIME items in a blocked 2×2 factorial:

| | Smaller output allowance | Larger output allowance |
|---|---:|---:|
| Lower native effort | same items and prompts | same items and prompts |
| Higher native effort | same items and prompts | same items and prompts |

The preregistered Inkling conditions are medium versus max effort and 20,000 versus
49,152 requested total-generation tokens. A second model route is a directional
replication, not a pooled effect. Providers are pinned, fallbacks are disabled, and
served-provider identity, request ID, finish reason, normalized and native usage,
billing receipt, latency, and cost must be recorded for every valid row.

## Outcomes and estimand

Every valid response receives an unchanged-grader result and a separate termination
status. The main operational categories are:

1. an extractable answer graded correct, whether normally or length-stopped;
2. an extractable answer graded wrong, whether normally or length-stopped; or
3. no extractable answer, with length-stopped and other finish reasons separated.

A token-starved/no-answer row specifically has `finish_reason="length"` and no
extractable final answer. It remains wrong because the unchanged grader found no
answer, not merely because generation hit the cap. A length-stopped row that already
contains an answer retains its grader result and is reported separately.

For `n` valid rows, `k` graded correct, and `u` unanswered length stops, the narrow
descriptive bound is `[k/n, (k+u)/n]`. It describes only uncertainty attributable to
no-answer cap terminations. It is not a bound on every counterfactual change an
independent larger-cap generation could make. Completed-only accuracy is a selected
descriptive quantity, never a replacement for conventional accuracy.

At allowance `c`, define the effort slope as:

`D_c = accuracy(higher effort, c) - accuracy(lower effort, c)`

The primary interaction is:

`I = D_large - D_small`

A positive interaction, accompanied by a disproportionate reduction in high-effort
cap hits, is evidence consistent with token starvation contributing to the smaller-
cap effort curve. It does not prove that the larger-cap response followed the same
reasoning path.

## What would count as genuine overthinking?

A normally completed high-effort error is only a candidate completed
negative-scaling case. Stronger language requires evidence that a correct conclusion
was subsequently abandoned, a forced-stop or forced-continuation intervention, or
repeated correct-to-wrong transitions. Visible reasoning-text interpretation is
qualitative and cannot override the automated final-answer grade.

## Committed sampling design and limitation

The committed design uses two model panels with one stochastic generation per
item and cell under a $27.00 study ceiling. The current $30.06 balance supports
that design while retaining a $3.06 margin. This supports a narrow,
single-sample fixed-benchmark route audit, but it does not estimate within-item
generation variability.

Adding a second generation to both panels would raise conservative worst-case
exposure to about $53.50. Preserving the existing $3.06 margin would require a
balance of about $56.56 and a preregistration amendment before any paid
response. No such amendment has been made.

## Requested pre-data feedback

The most useful short review would address one of these questions:

1. Does the native-effort × output-allowance interaction isolate a meaningful gap
   not covered by existing completion/efficiency decompositions?
2. Is “right-censored generation length with unobserved high-cap correctness” the
   correct statistical description?
3. Is one generation per item and cell defensible for the narrow fixed-benchmark
   estimand, or are repeat generations necessary before interpreting the interaction?
4. In a black-box API setting, what evidence is sufficient to distinguish harmful
   overthinking from an ordinary completed error?

The full preregistration is in [PREREGISTRATION.md](PREREGISTRATION.md). Exploratory
results will never be pooled with confirmatory estimates, and any pre-data protocol
change will be recorded as a dated committed amendment.
