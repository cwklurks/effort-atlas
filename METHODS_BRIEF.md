# Thinking Cut Short

## Separating token starvation from completed negative scaling in reasoning models

**Connor Klann, Independent Researcher**  
[ORCID 0009-0002-5056-6670](https://orcid.org/0009-0002-5056-6670)  
**Protocol status:** Preregistered draft; no confirmatory API response collected and
new-study spend is $0.00 as of 2026-07-22.

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

Every valid response remains in one of three operational categories:

1. correct normal completion;
2. completed but wrong; or
3. cap-hit/no final answer.

Cap-hit rows remain wrong for conventional accuracy under that endpoint
configuration. Their generation length is right-censored, while their
counterfactual correctness with more output room is unobserved. Completed-only
accuracy is reported only as a selected descriptive quantity, never as a replacement
for conventional accuracy.

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

## Open methods decision before spending

The current $30.06 balance supports two model panels with one stochastic generation
per item and cell under a $27.00 study ceiling. That design supports a narrow,
single-sample fixed-benchmark route audit, but it does not estimate within-item
generation variability.

Adding a second generation to both panels raises conservative worst-case exposure to
about $53.50. Preserving the existing $3.06 margin would require a balance of about
$56.56. The alternative is to keep the current budget and trade model breadth or
item coverage for repeats. This choice will be committed before any paid response.

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
