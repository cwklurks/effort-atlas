# External review prompt for the REAP Phase 3 recommendation

Copy this prompt into a new model conversation and attach or paste both
`13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md` and `CODEX_BRIEFING.md`. If the
second file cannot be attached, use the repository-state summary below and label
those claims as supplied rather than independently verified. The reviewer should
not need access to the original Codex chat.

---

You are an independent scientific and systems reviewer. Review the attached REAP
Phase 3 integrated recommendation for a paper tentatively titled *Thinking Cut
Short*.

Do not assume the proposed recommendation is correct. Your job is to challenge it,
check its internal arithmetic and scientific logic, identify hidden assumptions,
and return a better final plan where warranted.

## Project context

The research question is whether apparent accuracy declines at higher reasoning
effort are partly caused by output-token limits. Higher effort often produces longer
reasoning. If the output allowance stops the response before a final answer, an
ordinary benchmark records it as wrong. The experiment varies effort and output
allowance and measures their interaction.

For each panel, define:

```text
D_c = accuracy(high effort, c) - accuracy(low effort, c)
I = D_large - D_small
```

H3 is the primary scientific question and predicts `I > 0`. H1 and H2 are
mechanism checks involving differential length stops and cap rescue. Panels are
directional replications with route-specific effort controls; their effects are
reported separately and not pooled.

The Coupling Tax already applies survival methods to censored reasoning lengths
and uses cap sweeps for prediction. Do not treat Kaplan-Meier analysis of reasoning
length as REAP's novelty. The proposed additions are a controlled native-effort
axis, independent replication and item-level variation, a direct cap-invariance
test, and current route/receipt verification.

Use this priority order when resolving tradeoffs:

```text
scientific validity > reliable collection > budget safety > model breadth > speed
```

Supplied repository facts:

- No REAP confirmatory, paid study-generation, smoke, provider-probe, or DeepSeek
  development call has occurred.
- A previous exploratory run was invalidated after 78 responses hit an implicit
  4,096-token limit and a permissive grader fabricated answer extractions.
- The new grader accepts an answer only from a complete line matching
  `Final answer: <answer>`. Termination metadata is recorded separately and never
  determines correctness.
- The primary analysis code already supports Wilson intervals, a 10,000-resample
  item-clustered bootstrap, item-level independent-draw transition mass, rescue
  evidence, missingness bounds, variance summaries, dose-response tables, and
  cap-invariance calibration.
- The full arm-aware A/B/C schedule exporter, paid runner, and executable budget
  gates do not exist. The review must not describe the proposed study as ready to
  collect data.
- Replicates at different caps are independent generations, not continuations of
  one trace.
- Tinker SDK 0.25.0 is known to resubmit internally. The live path is blocked until
  a supported one-submission path is pinned and reviewed.
- Funding pools are separate: $5,000 Tinker credits, about $200 direct OpenAI, and
  less than $100 OpenRouter. Unused money need not be spent.
- The current proposal keeps a $2,000 first-pass Tinker ceiling, $200 OpenAI
  ceiling, $50 OpenRouter ceiling, and a possible $10 development-only Fireworks
  ceiling.
- Existing Phase-I preregistration files are frozen and cannot be edited. REAP needs
  a new dated preregistration.

Treat these as supplied repository facts unless you can inspect the attached
repository artifacts. You may test their internal consistency, but do not claim that you independently verified repository code, tests, hashes, or historical
counts that you were not given. Distinguish four evidence types in your answer:

- **Supplied repository fact:** a project claim that needs repository evidence for
  independent verification.
- **Current external fact:** a dated statement verified from a primary provider or
  dataset source.
- **Proposed design choice:** advice with no approval or call authority.
- **Unresolved human decision:** a choice Connor, Chirag, or both must record before
  freeze.

## Non-negotiable safeguards

1. No provider or model-generation calls through the project during this review.
   Documentation research is allowed.
2. Every ordinary request must set an explicit output cap and effort where the
   route supports effort.
3. Zero automatic retries on billed generation calls.
4. Pin the exact model and provider, disable fallbacks, require supported
   parameters, and reconcile receipts.
5. Record termination reason and native token usage at collection time.
6. Import upstream grading or harness logic. Do not invent a local fallback when an
   import fails.
7. Keep exploratory, smoke, synthetic, and confirmatory data separate.
8. Smoke may activate an unchanged frozen route or omit it. **NO SUBSTITUTION**.
9. Preserve every attempt in an append-only ledger.
10. Treat every price, throughput, context, ZDR, and provider-capability statement
    as dated and mutable.

## Review tasks

1. Evaluate whether the proposed model portfolio answers the paper's scientific
   question efficiently:
   - Inkling standard, detailed 30-item A/B/C mechanism panel;
   - GPT-OSS-120B standard on Tinker, detailed up-to-60-item panel;
   - Nemotron Ultra 550B and Qwen3.5 397B smaller breadth panels;
   - GPT-5.6 Terra direct OpenAI panel;
   - conditional GPT-OSS-120B Tinker/OpenRouter same-model anchor.
2. Decide whether Inkling should use 30 or 60 items and whether its detailed grid
   is worth roughly $746 for 30 items.
3. Decide whether GPT-OSS should use 30 or 60 items and whether the additional
   HMMT-2025 cohort helps enough to justify the extra complexity.
4. Check the provider recommendation for the OpenRouter GPT-OSS anchor. The current
   proposal says Fireworks is not currently listed for this model and tentatively
   prefers Baseten over Groq and Cerebras on speed/price. Verify only with current
   primary sources and distinguish provider-page measurements from guarantees.
5. Review the dataset plan. HMMT-2026 currently has 33 rows; the proposal suggests a
   fixed 30-of-33 core, tentatively `problem_idx` 1-30. Many golds are fractions or
   radicals, so the simple numeric comparator is insufficient. Assess the proposed
   pinned upstream MathArena scoring gate and whether the subset rule is defensible.
6. Review the statistical plan:
   - item-clustered bootstrap primary;
   - independent-draw transition/rescue language;
   - optional hierarchical logistic secondary model;
   - descriptive H5 monotonicity;
   - H6 maximum absolute calibration error with a one-sided item-bootstrap upper
     bound and tentative 0.10 tolerance.
7. Recompute all displayed generation counts and conservative cost maxima. State
   every rate and assumption used. Flag any total that cannot be reproduced.
8. Review batching versus individual calls. Recommend one frozen request unit and
   explain how it affects independence, failures, seeds, receipts, and cost.
9. Review whether direct Fireworks DeepSeek V4 Flash should remain development-only
   and disabled. It must never receive research data or provide scientific or
   financial verification.
10. Map your final answer to D01-D15. For every D, say: accept, modify, reject, or
    blocked; give a short reason and identify the human owner.
11. Evaluate power and multiplicity using the correct unit of evidence. The
    effective sample size is driven mainly by 30 or 60 independent item clusters,
    not the number of generated responses. State which H3 result is primary per
    panel and how multiple comparisons across panels, mechanism checks, dose cells,
    and adjacent contrasts should be reported or controlled.
12. Evaluate measurement and dataset-exposure risks. Keep strict terminator-based
    grading primary, but require marker compliance as a separate outcome by effort,
    cap, panel, and model. Assess whether HMMT-2026's recency creates unequal
    training-data contamination or benchmark-exposure risk across models, and say
    what can be documented without claiming exposure can be proved absent.
13. Decide whether the proposed Tinker/OpenRouter GPT-OSS comparison supports a
    hosting claim. A shared slug is insufficient unless the team can pin or record
    quantization or numerical precision, tokenizer, renderer and prompt wrapper,
    model revision, context policy, effort semantics, and served route. If these
    differ or remain unknown, provide narrower interpretation language.

If you have internet access, use primary sources only for mutable technical facts:
official provider documentation, official model catalogs, the first-party dataset
card, and the repository artifacts if supplied. Cite each mutable claim close to
the sentence it supports. Do not rely on search-result snippets when the live page
disagrees.

Do not optimize for agreement with Connor, Codex, or the attached document. Prefer
a smaller defensible study over a larger fragile one. Clearly separate scientific
choices from platform qualification and from spending authorization.

Classify every material finding with exactly one of these severities:

- **Preregistration freeze blocker:** the scientific protocol cannot be frozen
  truthfully until resolved.
- **Panel activation blocker:** the design may freeze, but the affected route may
  not collect confirmatory data until the gate passes.
- **Recommended improvement:** useful before collection but not required for a
  defensible freeze or safe activation.
- **Later-study idea:** valuable extension that should not expand the first pass.

## Required output format

Return Markdown with exactly these top-level sections:

1. `# Independent review verdict`
2. `## Most important corrections`
3. `## Final recommended plan`
4. `## Model portfolio and budget table`
5. `## Dataset and grader decision`
6. `## Statistical decision`
7. `## Operational gates and batching`
8. `## D01-D15 disposition`
9. `## Questions requiring Connor or Chirag`
10. `## Assumptions, evidence, and confidence`

Within `## Final recommended plan`, give one concrete plan rather than a menu. In
the D01-D15 table, include columns for decision, disposition, final choice, owner,
freeze blocker, and finding severity. List disagreements with the attached
recommendation explicitly. Assign confidence as high, medium, or low for each
consequential recommendation. In `## Assumptions, evidence, and confidence`, label
each consequential input with one of the four evidence types above and identify
anything you could not verify.

End with a short block titled `### Final answer for the research team` that states,
in plain language, what the team should freeze, what it should postpone, and what
must happen before the first smoke call.

---

After receiving the review, preserve the full response and return it to Codex for a
claim-by-claim audit. Do not treat the other model's answer as approval or call
authorization. If a decision cannot be resolved from the supplied evidence, leave
it open for its human owner instead of inventing certainty.
