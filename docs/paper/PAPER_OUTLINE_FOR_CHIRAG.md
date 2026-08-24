# Thinking Cut Short

## Working outline for a combined paper

**Connor Klann and Chirag Nagpal**  
**Status:** Working draft for discussion. No confirmatory API calls have been
made, and confirmatory spend is still $0.

Hi Chirag,

Thanks again for sharing your draft. This is my first attempt at showing how I
think the censoring work and the reasoning-effort experiments could fit into one
paper. I have tried to separate the parts that already seem solid from the
questions we should decide together. Please edit this directly wherever you
disagree or see a cleaner way to formulate the statistics.

The basic idea is that an output limit creates two related measurement problems.
First, a truncated response gives us incomplete information about its natural
length. Second, if the response was stopped before it produced an answer, the
benchmark records a failure without telling us what would have happened under a
larger allowance. Your work gives us a principled way to handle the first
problem. My proposed experiment addresses the second.

## 1. The question I think the paper should answer

When accuracy falls as a model's native reasoning effort increases, how much of
that decline comes from completed responses giving worse answers, and how much
comes from longer high-effort responses reaching an output limit before they can
answer?

I would keep the two quantities distinct throughout the paper:

- **Generation length:** a cut-off response is a right-censored observation of
  how long the generation would naturally have continued.
- **Accuracy at a given allowance:** a cut-off response with no final answer is
  wrong under the benchmark as run, but its correctness under a larger allowance
  is unknown.

Kaplan-Meier and related survival methods can estimate the length distribution
under stated censoring assumptions. They cannot recover an answer that was never
written. For correctness, we need to vary the allowance and rerun the model.

## 2. Working title and claim

### Working title

**Thinking Cut Short: Censoring-Aware Evaluation of Reasoning Effort Under
Output Limits**

### Possible subtitle

**Separating Token Starvation from Completed Negative Scaling in Reasoning
Models**

I like “genuine overthinking” as an accessible phrase, but I would use
“completed negative scaling” in the technical claims. A normally completed
high-effort error shows that the decline cannot be blamed on truncation; it does
not by itself show that the model reached a correct answer and then reasoned
itself away from it.

### Claim in one paragraph

Output limits create right-censored length observations and can distort
reasoning-model accuracy curves. We propose combining censoring-aware length
estimation with an effort-by-allowance experiment on pinned provider routes. The
experiment asks whether a negative effort slope is accompanied by more
unanswered length stops at a smaller allowance, and whether that slope changes
when the model has more room to finish.

All live-model findings would be scoped to the exact model, provider route,
request settings, and date tested. If version or precision information is not
available, we should say that it is unknown rather than infer it.

## 3. What the combined paper would contribute

I see four contributions.

1. **A clean separation of estimands.** We distinguish latent generation
   length, observed capped length, accuracy at the tested allowance, and
   unobserved correctness under a different allowance.

2. **A corrected censoring analysis for generation length.** We retain the
   central Kaplan-Meier argument and the semi-synthetic Helpfulness experiment,
   while stating the censoring assumptions and the identifiable range more
   carefully.

3. **An effort-by-allowance experiment.** On the same AIME items, we cross two
   native effort settings with two output allowances. The interaction tells us
   whether the effort curve changes when the model has more room.

4. **A route-level measurement audit.** We record provider identity, native
   usage, finish reasons, and billing receipts because the same nominal token
   parameter does not have the same measured behavior on every route.

The broad distinction between incomplete and completed failures is not itself a
new claim. Kaiser et al. (*Beyond Accuracy*, arXiv:2602.09805) study a related
decomposition at a fixed budget, and *Broken Chains* (arXiv:2602.14444) varies
budget without the native-effort interaction proposed here. The narrower gap we
can reasonably claim, to our knowledge, is the combination of effort variation,
allowance variation, censoring-aware length accounting, larger-cap reruns, and
route verification.

## 4. Possible paper structure

### 1. Introduction

I would open with the failure that motivated the project. On one Tinker route, a
hidden 4,096-token endpoint limit cut off 78 responses without reporting a
length finish reason. Grading those rows normally produced what looked like an
“accuracy declines with effort” curve. Once the hidden cap was found, those
accuracy numbers were treated as invalid rather than repaired.

That example motivates a broader point: before interpreting a decline as harmful
additional reasoning, we need to know whether the model was allowed to finish.
The introduction can then state the central question, the two estimands, and the
paper's contributions. It should also be explicit that completed negative
scaling exists in other settings; the goal is to measure the contribution of
token starvation, not explain every overthinking result away.

### 2. Background and related work

This section could cover:

- test-time reasoning and native effort controls;
- output-budget interventions, underthinking, and completed negative scaling;
- prior decompositions of incomplete versus completed failures;
- survival analysis for right-censored observations; and
- provider and gateway behavior as part of evaluation validity.

If space is tight, some of this can be folded into the introduction.

### 3. Censoring framework for generation length

For generation \(i\), let:

- \(T_i\) be the latent length to the natural stopping event;
- \(C_i\) be the effective generation allowance;
- \(Y_i = \min(T_i, C_i)\) be the observed length; and
- \(\delta_i = 1[T_i \leq C_i]\) indicate an observed completion.

At each distinct observed completion length \(t_k\), let \(d_k\) be the number
of completions and \(n_k\) the number of responses still at risk. Then

\[
\widehat S(t) = \prod_{k:t_k \leq t}\left(1-\frac{d_k}{n_k}\right),
\qquad
\widehat F(t)=1-\widehat S(t).
\]

We should state the tie convention explicitly: a response censored at length
\(c\) remains in the risk set at \(c\). This formulation reproduces the 0.453
value in the current toy example.

The section should also make four limits clear:

- the estimator requires independent or conditionally independent censoring;
- an unrestricted mean is not identified if the estimated survival curve has a
  nonzero tail, so we should report a restricted mean through a prespecified
  horizon;
- the median is only identified if the estimated curve crosses 0.5; and
- this framework estimates length, not correctness under a larger cap.

For hosted reasoning APIs, a requested allowance might change the model's policy
from the beginning. A larger-cap response therefore should not be described as
the literal continuation of a smaller-cap trace.

### 4. Semi-synthetic validation

I would retain the Helpfulness experiment because it gives us known uncensored
lengths against which to compare the estimators. I would describe it explicitly
as a semi-synthetic censoring study: the assistant responses already exist, and
we impose a window after the fact.

The current cap, \(C_i = 512 - \text{prompt length}_i\), depends on prompt
length. That makes marginal independent censoring questionable if prompt length
and response length are related. My suggestion is to keep the existing result
but strengthen it with one or more of the following:

- stratify or condition on prompt length;
- add an independently generated censoring mechanism as a comparison;
- report restricted mean error and curve-level error over the identified range,
  rather than relying on one point at length 256; and
- add assumption-light Peterson bounds as a sensitivity check.

We should also report the sample sizes, censoring rates, tokenizer, preprocessing,
and how the uncertainty bands are computed. I would be interested in your view
on the simplest version of this extension that is still statistically sound.

### 5. From censored lengths to distorted accuracy curves

For effort \(e\) and allowance \(c\), define operational accuracy as \(A(e,c)\).
Every valid response receives the unchanged benchmark grade. Finish reason and
answer availability are recorded separately.

We can define a **token-starved, unanswered response** as one that:

1. stops because it reached the length allowance; and
2. contains no explicit final answer.

If a cell has \(n\) valid responses, \(k\) correct answers, and \(u\)
unanswered length stops, the interval

\[
[k/n,\,(k+u)/n]
\]

is a useful descriptive summary of the uncertainty attributable specifically to
those unanswered stops. It is not a counterfactual accuracy bound, because a
fresh larger-cap call can follow a different trajectory.

At cap \(c\), define the effort slope as

\[
D_c = A(\text{higher effort}, c)-A(\text{lower effort}, c).
\]

The main comparison is the interaction

\[
I = D_{\text{large cap}}-D_{\text{small cap}}.
\]

A positive interaction, together with a larger reduction in high-effort
unanswered stops, would be evidence consistent with token starvation affecting
the small-cap curve. If the negative slope remains at the larger allowance, we
would report the residual as completed negative scaling rather than assume that
the model “overthought.”

### 6. Live-model experiment

The current plan uses the same 30 audited AIME-25 items in every condition.
Prompts, gold answers, and the numeric grader stay fixed. Item order and condition
order are frozen in the existing schedules.

| Panel | Pinned route | Effort settings | Output allowances | Main calls |
|---|---|---|---|---:|
| Inkling | OpenRouter to Together | medium, max | 20,000 and 49,152 | 120 |
| GLM 5.2 | OpenRouter to Together | high, xhigh | 4,096 and 32,000 | 120 |

There are also three excluded smoke calls, for 243 planned calls in total. The
second model is a directional replication; we should report it separately rather
than pool the model effects.

For each cell, I propose reporting:

- correct count, denominator, accuracy, and a Wilson interval;
- all length stops, unanswered length stops, and answer-present length stops;
- mean and median completion and reasoning tokens;
- latency, missingness, route mismatches, and failures; and
- receipt-reported cost.

Primary inference would report both effort slopes and their interaction, with a
10,000-draw item-clustered bootstrap interval. Secondary tables would show paired
item transitions and the outcomes of independent larger-cap reruns. These reruns
are “rescues” only in an operational sense; they are not continuations of the
smaller-cap responses.

Before any confirmatory call, we still need to:

- make the final-answer rule robust to a response ending mid-calculation;
- probe both experimental routes near the caps we will actually use;
- finish and test the paid runner, route pinning, and cumulative cost gate; and
- implement and freeze the confirmatory analysis.

The current design uses one generation per item and cell under a $27 ceiling.
That supports a narrow fixed-benchmark route audit, not a general estimate of
run-to-run variability. Repeating every condition would roughly double the
worst-case budget, so I think this is a decision we should make together before
we change the preregistration.

### 7. Results

I would order the eventual results as follows:

1. semi-synthetic validation of the length estimator;
2. the route and cap-semantics checks needed to interpret the experiment;
3. per-cell accuracy, termination, token, latency, and cost summaries;
4. the effort-by-allowance interactions;
5. paired larger-cap outcomes and completed negative-scaling candidates; and
6. missingness and sensitivity analyses.

This section should be generated from the frozen analysis after data collection.
Missing cells remain missing, and null or contradictory results stay in the
paper.

### 8. Discussion and limitations

The discussion can return to two questions: how much of the small-cap effort
slope was associated with unanswered truncation, and what negative slope, if
any, remained when the model had more room?

Important limitations include one stochastic generation per cell, only 30 AIME
items, reuse of the same benchmark in exploratory and confirmatory work,
provider-specific behavior, possible length-related transport failures, and the
fact that changing the allowance can change the generation policy rather than
simply reveal a hidden continuation.

### 9. Conclusion

I would end with a practical recommendation rather than a universal claim about
overthinking. Evaluations of reasoning models should report the effective output
allowance, finish reason, answer availability, provider route, native usage, and
cap sensitivity before interpreting an accuracy decline as harmful additional
reasoning.

## 5. Figures and tables

The core figures could be:

1. a censoring schematic showing prompt, reasoning, final answer, EOS, and cap;
2. the semi-synthetic true CDF alongside naive and censoring-aware estimates;
3. the 2 × 2 effort-by-allowance design;
4. accuracy by effort with one line per allowance and one panel per model; and
5. unanswered length-stop rate by effort and allowance.

The main table would combine per-cell accuracy, termination categories, token
use, latency, missingness, and cost. Detailed receipt reconciliation and the
four-route cap-semantics audit could move to an appendix if space is tight.

## 6. Changes I suggest for the current note

The central idea survives these changes. I reproduced the headline toy value of
0.453, and it is correct under the standard Kaplan-Meier estimator with the tie
convention stated above. Most of the work here is making the notation produce the
same answer as the code and making the assumptions visible to a reviewer.

The changes I think matter most are:

1. **Restate the estimator.** Define the observed lengths, completion indicators,
   event times, risk sets, and tie convention explicitly so Equation 1 reproduces
   the toy calculation unambiguously.

2. **Use a restricted mean.** The unrestricted mean and, in the toy example, the
   median are not identified while the estimated survival curve retains a
   censored tail. We can report restricted mean generation length through a fixed
   horizon and state the crossing condition for the median.

3. **Address the censoring mechanism.** Since the available response allowance
   is determined by prompt length, I would add a prompt-length-stratified or
   conditional analysis and clearly state the range that remains identified.

4. **Call the experiment semi-synthetic.** No model is decoded during this
   experiment; the window is imposed on existing corpus responses. Saying this
   directly makes the validation easier to understand and distinguishes it from
   the live API experiment.

5. **Tighten the empirical claim.** Replace “robust” or “unbiased” with wording
   scoped to the stated censoring assumptions and the identified range. Add
   curve-level or restricted-mean error rather than relying only on the value at
   256.

There are also a few straightforward consistency edits: the toy figure has three
completed trajectories rather than four; the text refers to a nonexistent Figure
3; the displayed error is an absolute error at 256 rather than squared error or
an integrated \(L_1\) distance; “density” should be replaced by CDF or survival
function; and the Glivenko-Cantelli theorem supports uniform consistency, not a
generic optimality claim.

I am happy to make a line-by-line pass in the LaTeX once we agree on the combined
structure. None of these points changes the central censoring insight.

## 7. Questions I hope we can decide together

1. Should the current note be folded fully into the combined paper, posted first
   and cited, or developed in parallel?
2. Do we want the title to retain the accessible phrase “genuine overthinking,”
   or use “completed negative scaling” throughout?
3. Should Kaplan-Meier summaries of the live-model lengths remain descriptive,
   with the main use of the method in the semi-synthetic section?
4. For Helpfulness, would you prefer prompt-length stratification, an independent
   censoring arm, or both?
5. Is one generation per item and cell acceptable for a narrow route audit, or
   should we seek enough budget for repeats?
6. Are the two model panels the right scope for the first paper?
7. Should we aim for ARR or another venue, and what timeline is realistic?

I would also like to confirm any affiliation or internal-review requirements on
your side, as well as the Overleaf workflow and final division of writing.

## 8. Tentative division of work

This is only a starting point.

**Connor**

- confirmatory harness, route checks, accounting, and reproducibility artifacts;
- API execution and budget controls; and
- effort-by-allowance analysis, figures, and empirical sections.

**Chirag**

- censoring framework and survival-analysis formulation;
- revision and extension of the Helpfulness experiment; and
- statistical review of the length estimands and assumptions.

**Joint**

- final hypotheses and experimental scope;
- related work and claim language;
- abstract, introduction, discussion, and limitations; and
- final manuscript review.

## 9. Immediate next steps

If this overall structure makes sense, my proposed order is:

1. agree on the paper's central claim and how the current note fits;
2. revise the censoring notation and decide on the Helpfulness extensions;
3. make and freeze the remaining pre-data protocol corrections;
4. finish and test the confirmatory runner and analysis; and
5. run the route probes, review their accounting, and only then begin the main
   paid experiment.

I have not started the confirmatory run because the scoring rule and route-cap
checks should be settled while the pre-data amendment window is still open.

## Supporting material

- [Methods brief](METHODS_BRIEF.md)
- [Preregistration](PREREGISTRATION.md)
- [Pre-data amendment](PREREGISTRATION_AMENDMENT_2026-07-22.md)
- [Cap-semantics audit](CAP_SEMANTICS.md)
- [Experiment repository](https://github.com/cwklurks/effort-atlas)

