# REAP benchmark-scope decision

**Date:** 2026-08-20  
**Status:** NON-FROZEN SCOPE BOUNDARY - NO CALL AUTHORIZATION

This record separates the public-archive benchmark work from the future controlled
REAP experiment. It is a decision about evidence lanes, admissible claims, and the
order of the remaining decisions. It does not select a final controlled item list,
freeze D03, approve a model route, authorize spending, or permit a provider,
smoke, probe, or confirmatory call.

```text
CONFIRMATORY_CALLS=0
PAID_STUDY_GENERATION_CALLS=0
PAID_SMOKE_CALLS=0
PROVIDER_PROBE_CALLS=0
DEEPSEEK_DEVELOPMENT_CALLS=0
```

## Decision

REAP will keep two non-pooling benchmark scopes.

| Boundary | Exploratory public-archive scope | Controlled experiment scope |
|---|---|---|
| Data origin | Already-published, revision-pinned MathArena and HELM archives | New responses collected only after a dated REAP preregistration, exact manifests, reviewed runner, executable budget gates, and human activation |
| Current benchmark coverage | The verified question-level audit covers MathArena HMMT 2025, MathArena HMMT 2026, and HELM GPQA; the protected historical observational study separately includes AIME 2026 and BRUMO 2025 summaries | A compact HMMT short-answer experiment is the current candidate; the exact cohort and question IDs remain a separate human decision |
| Scientific role | Motivate the mechanism, audit provenance and measurement capability, describe archived question-level accuracy and route-native output fields, and provide pre-data design inputs | Estimate the within-route effort-by-allowance interaction, unanswered length-stop response, large-cap reference behavior, and any prespecified matched-performance operating frontier |
| Grade | Source-native archived grade, labeled as such | Strict `Final answer: <answer>` presence followed by the frozen deterministic upstream mathematical comparator |
| Termination | MathArena is `inferred` or `unknown`; HELM Gemini is `observed`; HELM Claude and GPT are `unknown` | Captured at collection time from the exact route and kept separate from grading |
| Output measure | Route/archive-native and quality-flagged; no universal cross-provider token unit | Frozen per route, with per-response usage and accounting linkage required before activation |
| Unit and uncertainty | Average attempts within question, weight questions equally, preserve paired-question coverage and explicit missing cells | Independently scheduled attempts with item-clustered analysis and the frozen arm, seed, missingness, and multiplicity rules |
| Permitted claim | Descriptive archived association, capability, provenance, and operational examples | Prespecified intervention estimates under the frozen questions, prompts, routes, effort values, caps, and analysis |
| Denominator | Exploratory only | Controlled rows only |

No archived response row, grade, token count, or termination field may enter a
controlled-effect denominator. No controlled response may be appended to an
exploratory archive table and presented as one sample. The two scopes may share
question identifiers only when the controlled manifest independently freezes those
identifiers; shared IDs do not turn archived attempts into controlled observations.

## Exploratory public-archive scope

The pinned public-source audit remains the authority for what the archived files
can support:

- HMMT 2025 has 30 source IDs and complete ID coverage for 64 archived models, but
  prompt variants and unusable token values require explicit quality flags.
- HMMT 2026 has 33 MathArena item IDs. Question 25 has mixed text versions, items
  31-33 lack settled official-round provenance, and Qwen3.5-4B has 11 explicit
  missing model-question cells.
- HELM evaluates a fixed 446-question GPQA test split. All three archived models
  share those IDs, but their prompt wrappers and token fields are not one common
  measurement system. Only Gemini has complete stop labels: 42 `length` and 404
  `stop`.
- AIME 2026 and BRUMO 2025 remain part of the earlier protected exploratory
  observational record. They are not silently promoted into this question-level
  capability audit or into the controlled experiment.

Allowed exploratory outputs are question-level source-native accuracy, coverage,
missingness, prompt/version differences, route-native output summaries after
quality control, and observed/inferred/unknown termination summaries. These
outputs must remain dataset- and route-labeled.

The exploratory lane must not report:

- a causal claim that a particular answer was wrong because of a cap;
- a censoring-adjusted or imputed accuracy;
- a pooled native-token ratio across providers or tokenizers;
- a strict-REAP regrade where the complete response text and frozen extraction
  contract are unavailable; or
- any estimate presented as confirmatory REAP evidence.

## Controlled experiment scope

The controlled lane will collect new, independently scheduled responses on one
frozen short-answer benchmark scope. Its minimum design contract is:

1. exact source revision, licence record, question IDs, question-text hashes, gold
   hashes, and a source-defined, outcome-blind inclusion rule;
2. one exact prompt template plus recorded route wrappers/renderers;
3. explicit effort and exact integer output allowance on every ordinary request;
4. strict final-answer-marker extraction and a pinned deterministic upstream
   scorer that fails closed on import or schema mismatch;
5. termination reason, route-native usage, request identity, and accounting linkage
   captured for every attempt;
6. independent exploratory, smoke, and controlled ledgers and artifact roots; and
7. item-clustered analysis with no cross-panel pooling of route-specific effort or
   token units.

The existing effort slope and effort-by-allowance interaction remain the primary
controlled mechanism target unless Connor and Chirag explicitly replace them in
the new preregistration. The matched-performance frontier is an additional
controlled estimand: it is defined only over tested regimes and accuracy levels
both compared models attain. A cross-route token difference or ratio is
`not_estimable` unless the frozen eligibility record establishes a commensurate
output measure.

The public archives may inform pre-data power work, cap placement, quality checks,
and candidate-item review. Any such use must cite the pinned inputs, occur before
the scientific freeze, and be recorded as design evidence. It does not move an
archived outcome into the controlled analysis.

## What this phase decides

This phase decides all of the following:

1. Public archives and newly collected experiment rows are separate evidence
   layers with separate denominators and claims.
2. The public-source benchmark audit remains exploratory even when it uses the same
   question IDs later selected for the experiment.
3. The first controlled pass stays within a compact HMMT short-answer scope. GPQA,
   AIME, BRUMO, HARP, and GSM8K are not part of the first controlled schedule
   unless Connor and Chirag make a new pre-data scope decision.
4. Cross-provider native-token ratios are not a default controlled endpoint.
   Within-route output-use results come first; cross-route matched-performance
   contrasts require an explicit commensurability gate.
5. This boundary is fixed before choosing the exact controlled questions so
   archival performance cannot decide which outcomes enter the experiment.

## What this phase deliberately does not decide

The next benchmark-scope phase must resolve, without provider output:

- HMMT 2025, HMMT 2026, or a predeclared cohort relationship for the controlled
  first pass;
- the disposition of HMMT-2026 question 25;
- whether HMMT-2026 MathArena items 31-33 are eligible and how they are described;
- the exact item count, IDs, scorer schemas, and prompt bytes;
- whether archived length distributions may enter the power/cap-placement inputs
  and, if so, the exact frozen transformation;
- the primary model panels, replication counts, caps, large-cap references, and
  multiplicity family; and
- whether the matched-performance frontier remains secondary or replaces any
  current paper target.

Those choices remain owned by Connor and Chirag under D03-D14. They require a new
dated record and, ultimately, the new REAP preregistration. This document cannot
be cited as their approval.

## Gate to the next phase

Proceed to exact controlled-question selection only after this separation is
accepted as the working boundary. The next artifact should compare the eligible
HMMT cohort rules using provenance, grading coverage, clustered power, and budget
consequences without using archived accuracy to hand-pick questions.

Nothing in this decision changes the zero-call state or opens Phase 4. No provider
call was made to prepare it.
