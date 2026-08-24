# Review prompt for the combined-paper outline

Copy the prompt below into a fresh research-review session. Attach or provide
access to the listed files. The review should be completed before any
confirmatory API call.

---

You are reviewing an early collaborative research outline for a paper tentatively
titled **“Thinking Cut Short: Censoring-Aware Evaluation of Reasoning Effort
Under Output Limits.”**

The two collaborators are:

- Chirag Nagpal, whose existing note studies right-censored language-model
  generation lengths using Kaplan-Meier estimation; and
- Connor Klann, whose effort-atlas project studies how native reasoning effort
  interacts with output allowances, accuracy, truncation, provider routing, and
  token accounting.

The immediate goal is not to polish prose or run experiments. It is to determine
whether the combined paper is scientifically coherent, accurately positioned,
and safe to freeze before the first confirmatory paid call.

## Materials to review

Read all of the following before reaching a conclusion:

1. `PAPER_OUTLINE_FOR_CHIRAG.md` — the document being reviewed.
2. Chirag's current manuscript, supplied as `llm_length.pdf`.
3. `METHODS_BRIEF.md`.
4. `PREREGISTRATION.md`.
5. `PREREGISTRATION_AMENDMENT_2026-07-22.md`.
6. `CAP_SEMANTICS.md`.
7. `review-2026-07-26/03_MANUSCRIPT_MODIFICATIONS.md`.
8. `review-2026-07-26/05_PREDATA_DECISIONS.md`.

Use current primary sources for related-work and technical claims. In particular,
compare the outline against Kaiser et al., *Beyond Accuracy*
(arXiv:2602.09805), *Broken Chains* (arXiv:2602.14444), the original
Kaplan-Meier literature or a standard survival-analysis reference, and the
provider documentation relevant to the named routes. Distinguish a documented
fact, an observed route-specific measurement, an inference, and a proposal.

## Questions the review must answer

### 1. Is there one coherent paper here?

Explain whether the right-censored length analysis and the
effort-by-allowance accuracy experiment support one central question. Flag any
place where the outline incorrectly treats length estimation as if it identified
correctness under a larger cap.

### 2. Is the novelty claim defensible?

Identify exactly what prior work already establishes and what, if anything,
remains novel in the combination of:

- native reasoning-effort variation;
- output-allowance variation;
- censoring-aware length analysis;
- independent larger-cap reruns; and
- provider-route and billing verification.

Reject unsupported “first” claims. Recommend one contribution sentence using “to
our knowledge” only if the literature search supports it.

### 3. Is the censoring mathematics correct?

Check the notation, Kaplan-Meier estimator, risk sets, tie convention,
independent or conditional censoring assumption, identified range, restricted
mean proposal, and median claim. Recompute the toy value 0.453 from the source
manuscript. Evaluate whether prompt-length stratification, conditional
estimation, Peterson bounds, or an independent censoring arm is needed for the
Helpfulness experiment.

### 4. Does the experiment identify the stated quantity?

Evaluate the two-by-two effort × allowance design, per-item blocking, one-sample
per cell limitation, model-panel separation, interaction estimand, unanswered
length-stop definition, rescue terminology, and item-clustered bootstrap. State
what conclusions the design can and cannot support.

Pay particular attention to the fact that a larger allowance can change the
generation policy from the beginning. A larger-cap call is an independent
intervention, not the continuation of the smaller-cap trace.

### 5. Is the study ready for paid data collection?

Cross-check the outline against the preregistration and readiness documents.
Separate:

- changes required before the first confirmatory response;
- decisions the collaborators must make together;
- implementation work that can be verified offline; and
- optional improvements that should not block the paper.

Confirm whether the final-answer-presence rule, near-cap route probes, provider
pinning, zero-retry policy, cumulative budget gate, Wilson intervals, clustered
bootstrap, transition tables, and missingness analysis are actually implemented
or merely proposed. Do not infer readiness from prose.

### 6. Does the document answer Chirag's request?

Chirag asked for a working document containing:

1. a proposed section outline;
2. additional experiments and their details; and
3. suggested modifications to his existing sections.

Assess whether all three are present at an appropriate level for a collaborator
to edit. Also review the tone: it should sound like a serious early-career
researcher sharing a thoughtful working draft, not a referee report, sales pitch,
or generic AI-generated proposal.

## Required output

Begin with one of four verdicts:

- **Ready to share**
- **Ready to share with minor edits**
- **Revise before sharing**
- **Scientifically incoherent in its current form**

Then provide:

1. a five-sentence summary of the paper as you understand it;
2. a table of findings with severity (`blocking`, `important`, or `optional`),
   the exact section affected, the problem, and a concrete revision;
3. an explicit check of Chirag's three requested deliverables;
4. a list of claims that must not appear in the paper;
5. the strongest defensible contribution sentence;
6. the five decisions Connor and Chirag should make in their meeting; and
7. a final pre-data checklist ordered by dependency.

Be direct and specific. Quote short phrases from the outline when useful, but do
not rewrite the entire document. Do not fabricate citations, results, missing
metadata, or implementation status. Do not recommend running paid calls until
all blocking pre-data issues are resolved.

---
