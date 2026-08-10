# REAP Phase 3 Connor decision worksheet

**Dated:** 2026-08-10

**Status: NON-FROZEN WORKING RECORD — NO CALL AUTHORIZATION**

This records Connor's current choices, questions, and alternatives after reviewing
the D01-D15 packet. It is a discussion sheet, not the REAP preregistration, a route
activation, a spending approval, or Chirag's scientific signoff. A choice marked
"accepted" means Connor supports that direction; it does not authorize code to call
a provider.

## Safety snapshot

```text
CONFIRMATORY_CALLS=0
PAID_STUDY_GENERATION_CALLS=0
SMOKE_CALLS=0
PROVIDER_PROBE_CALLS=0
DEEPSEEK_DEVELOPMENT_CALLS=0
```

DeepSeek is not authorized yet. Tinker live execution remains blocked because the
pinned SDK cannot currently guarantee one and only one billed submission. The
proposed Tinker reliability smoke has a **$2 total hard ceiling**, but it may occur
only after the exact smoke schedule, runner, route, and stop rules are frozen and
independently reviewed. Connor must start it manually.

## Decision record

| ID | Connor's current position | Current status | Needed before freeze |
|---|---|---|---|
| D01 | Freeze the exact science first, then run a tiny, human-started Tinker reliability smoke under a proposed $2 hard ceiling. Passing activates the unchanged route; failure omits it. | DIRECTION ACCEPTED | Exact smoke rows and pass/fail rules; safe one-submission runner; joint signoff. |
| D02 | Keep A, B, and C as independently sampled arms with a mandatory `arm_key`; never reuse rows. | ACCEPTED BY CONNOR | Scientific signoff and schema implementation. |
| D03 | Keep a planned shared 30-of-33 HMMT-2026 subset, but revisit whether Tinker should also use all 30 HMMT-2025 items after reviewing power and cost. | OPEN | Outcome-blind selection, exact item/licence manifest, and Chirag's view on 30 versus 60 item clusters. |
| D04 | Accept standard Inkling and the recommended scientific effort/cap direction. D13 reopens how large the Inkling panel should be and how much budget it receives. The expensive route/settings remain a pre-data alternative or later-study note, never an automatic fallback. | DIRECTION ACCEPTED; SCOPE OPEN | Chirag signs off the grid; choose 30 versus 60 items, n, and panel ceiling with D13. |
| D05 | Use standard 32K `openai/gpt-oss-120b` with caps that fit its total context. | ACCEPTED BY CONNOR | Chirag signoff and exact renderer/cap smoke predicate. |
| D06 | Include Terra in principle, but review it beside Sol, Luna, and the full portfolio before freezing. | OPEN | Final model roster, OpenAI accounting gate, and exact P3 budget. |
| D07 | Use the simple independent-draw summaries as primary; keep a more complex rescue model as a possible secondary analysis. | PROVISIONAL RECOMMENDATION ACCEPTED | Chirag confirms estimand names and whether any secondary model is worth implementing. |
| D08 | Keep the item bootstrap primary; a small hierarchical model is interesting only as a frozen, simulation-tested secondary analysis. | PROVISIONAL RECOMMENDATION ACCEPTED | Chirag chooses descriptive-only versus secondary model. |
| D09 | Absolute calibration error makes sense, but the `0.10 in every cell` rule needs an uncertainty-aware version and power simulation. | OPEN | Chirag chooses the tolerance and support/inconclusive rule. |
| D10 | Use descriptive monotonicity for the first pass; keep formal ordered testing as a possible later method. | PROVISIONAL RECOMMENDATION ACCEPTED | Chirag confirms that H5 is a pattern, not a confirmatory test. |
| D11 | Shared prompt and strict final-answer marker look right; exact wording and delivery details remain open. | OPEN | Connor freezes exact bytes, renderer versions, stop strings, and grader hash. |
| D12 | Deterministic arm-aware scheduling is accepted in principle; batching versus individual calls remains open. | OPEN | Connor chooses the request unit and its exact activation test. |
| D13 | Do not reserve about $1,650 for Inkling. Rebuild the Tinker portfolio across Inkling, GPT-OSS, Qwen, and Nemotron candidates while retaining a real reserve. | REOPENED | Exact per-panel schedules, current price snapshot, and hard subceilings. |
| D14 | Use the same planned 30-item subset of HMMT-2026 and 4K/16K caps as a directional cross-platform anchor; report panels separately. | ACCEPTED BY CONNOR | Freeze the 30-of-33 selection rule, shared item hash, and route-specific effort endpoints. |
| D15 | Fireworks DeepSeek V4 Flash may be used only for cheap development work under the narrow ZDR scope below. It remains disabled and not authorized yet. | CONDITIONAL | Connor approves exact configuration and ceiling after review. |

## Detailed decisions

### D01 — When to freeze the design and when to test Tinker

**Plain meaning:** write down the experiment before seeing any model output, but do
not trust Tinker blindly. After the rules and runner are fixed, run a very small
technical check to learn whether the exact route behaves safely enough to use.

**Recommended implementation:**

1. Freeze the questions, models, routes, caps, effort values, sample counts,
   analysis, and an exact pass/fail rule.
2. Build and independently test a runner that cannot retry a paid generation.
3. Reserve at most **$2** for a human-started Tinker reliability smoke. The frozen
   rows should cover a forced cap stop, an easy normal stop, receipt/token
   reconciliation, exact served route, and whichever batching mode D12 chooses.
4. If every rule passes, activate that route unchanged. If any rule fails or is
   unclear, omit the route. Do not tune it after reading outputs.

This matches Connor's wish to test reliability without letting the test redesign
the science. The current Tinker SDK fails step 2, so the $2 is a future ceiling, not
permission to spend now.

**Alternatives:**

- A: smoke first, then design the study. Rejected because observed behavior could
  influence the scientific design.
- B: freeze the design and run without any smoke. Rejected because Tinker's runtime
  and billing behavior are not reliable enough to assume.
- C: scientific freeze, reviewed runner, tiny smoke, then unchanged activation or
  omission. This is Connor's choice.
- D: preregister two complete routes and choose between them using a purely
  technical, outcome-blind predicate. Possible, but much more complex than C and
  must be written down before either route returns content.

**Connor's position:** choose C with a proposed $2 Tinker smoke ceiling.

**What remains open:** the exact number and caps of smoke rows, a supported
one-submission SDK path, and joint signoff that the activation rule cannot be
influenced by response quality.

### D02 — Separate experiment arms

**Plain meaning:** Arms A, B, and C answer different questions, so each gets fresh
model generations. A row collected for one arm cannot secretly count again in
another.

**Recommended implementation:** put `arm_key` in every schedule row, request/job
ID, cache key, ledger entry, analysis group, and report. Reject missing or unknown
arm keys.

**Alternatives:**

- A: one large grid and reuse rows across arms. Cheaper, but creates hidden
  dependence and double use.
- B: independent samples for every arm. Clearer and easier to audit. Chosen.
- C: reuse some rows and explicitly model covariance. More efficient, but much
  harder to preregister and review correctly.

**Connor's position:** accept B.

**What remains open:** only implementation details and Chirag's final scientific
signoff.

### D03 — Which problems to use

**Plain meaning:** the proposed cross-platform comparison does **not** use different
problems. P1, P2, and P3 would use the same planned 30-item subset of HMMT-2026 at
the shared 4K/16K caps. The current first-party `hmmt_feb_2026` source revision has
33 rows, so the exact 30 IDs and pre-data selection rule are still open. Tinker was
proposed to receive all 30 HMMT-2025 items because its credit pool is much larger.

Why consider the additional year? The analysis resamples whole items. Sixty
different items give more information about how results vary across math problems
than 30 items do. Repeating the same 30 items more often estimates each item's
success rate more precisely, but it does not replace 30 new independent item
clusters.

That is the reason for the original 60-item Tinker scope: a 30-item shared core
plus 30 more independent items, not a different cross-platform benchmark.

Why only 30 on Terra? The 30-item P3 plan has a pre-smoke worst-case estimate of
about $125.83. Using 60 would be about $251.66, already above the roughly $200
OpenAI pool. The same 30-item core makes the side-by-side comparison fair; the
extra Tinker year increases Tinker's within-platform evidence and is never pooled
with Terra.

#### Dataset research summary

| Set | Proposed role | Why it is useful | Why include or defer |
|---|---|---|---|
| HMMT Feb 2026, planned 30-of-33 subset | Shared core | Hard, clean integer math; already central to the observational work; exact same selected items can run on every scientific panel. | Freeze the source revision, licence record, outcome-blind 30-row selection rule, item IDs, gold hashes, and shared-anchor hash. |
| HMMT Feb 2025, 30 items | Optional Tinker extension | Adds independent item clusters without changing task type. | Decide 30 versus 60 after power/cost discussion; no cross-platform mismatch is claimed because shared estimates use only the 2026 core. |
| AIME 2025+2026, 60 items | Continuity extension | Familiar integer-answer benchmark. | Defer: exact licences/revisions/item manifest unresolved and first-pass budget is better spent on the core. |
| GPQA-Diamond, 198 items | Cross-domain multiple choice | Tests whether the wall effect extends beyond math. | Defer: gated access, redistribution limits, and MCQ guessing/fallback risks require a separate strict protocol. |
| HARP hardest tier, candidate 197-item derived subset | Difficulty extension | Provides a deliberate difficulty axis. | Defer; the 197 count is derived and needs an exact repository revision, query/selection rule, selected IDs, golds, and licence evidence. |
| GSM8K, 1,319 items | Negative control/pathology | Shows how short/easy tasks and old last-number graders can hide the problem. | Defer as a primary panel; use only as a separately designed negative control. |

The observational output revisions are length/truncation priors, not a confirmatory
item manifest. A clean REAP dataset manifest does not exist yet. It must record
source revision, licence evidence, item IDs, gold hashes, per-panel membership, and
the common 30-item hash.

**Alternatives:**

- A: all 90 previously discussed math items. More item diversity, but the exact
  collection and worst-case budget do not fit the first pass.
- B1: 60 HMMT items on Tinker and the same 30-item 2026 subset on Terra. Original
  recommendation; stronger Tinker item-level precision.
- B2: the same selected 30 HMMT-2026 items on every panel. Cheaper and simplest, but only 30
  item clusters.
- B3: freeze a 30-item shared core plus an outcome-independent 30-item Tinker
  extension that activates only if its panel budget fits before any call. A useful
  compromise, but more complex.
- C: add AIME, GPQA, HARP, or GSM8K now. Broader, but creates licence, grading,
  power, and budget work before the main result exists.

**Connor's position:** keep a common planned 30-item HMMT-2026 subset; review B1
versus B2/B3 after Chirag weighs the value of 60 item clusters.

**What remains open:** exact HMMT source files and licences, item manifest, and the
power tradeoff between 30 and 60 independent items.

### D04 — Inkling design and the more expensive route

**Plain meaning:** Inkling is scientifically special because it offers a continuous
effort control, but that does not justify spending most of the Tinker pool on it.
Standard Inkling has 64K total context. Its 256K PEFT route is a different, roughly
twice-as-expensive route, not a hidden extension of the standard one.

The original 60-item full A/B/C proposal costs at most about $1,492.18 before smoke,
not $1,650, when calculated from the declared conservative prompt and output
bounds. A 30-item version would be about $746.09. An Arm-A-only 30-item Inkling
panel at the packet's n=20 would cost 2.5 times as much as the separate n=8 breadth
anchor described in D13; that n=8 anchor would be about $60.71,
but would no longer study the full dose-response and large-cap-reference mechanism.

If the standard route has a technical problem, the expensive route or different
settings may remain a **research note**. They cannot become an automatic fallback
after outputs are visible. To use them in this study, we would have to freeze them
before data as a separate route/panel with its own schedule, interpretation,
activation predicate, and ceiling.

**Alternatives:**

- A: standard Inkling, full 60-item A/B/C design. Most continuous-effort evidence;
  greatest budget concentration.
- B: standard Inkling, full 30-item shared-core design. Preserves the mechanism
  study at roughly half the cost, but halves item clusters.
- C: standard Inkling, smaller n=8 breadth anchor only. Cheap directional evidence,
  but it is not the packet's n=20 Arm A and loses the detailed cap/dose study that
  makes Inkling distinctive.
- D: 256K PEFT Inkling as a separately frozen panel. More context, roughly double
  the token rates, and a different route interpretation.
- E: predeclare both standard and PEFT schedules with an outcome-blind technical
  choice rule. Possible but operationally and statistically more complex.
- F: omit Inkling and spend across several other Tinker models. Broader, but loses
  the cleanest continuous effort axis.

**Connor's position:** accept standard Inkling and the recommended effort/cap
scientific direction. D13 reopens panel size, n, and budget; it does not turn the
PEFT route or different settings into an automatic fallback. Keep those only as a
future or separately predeclared alternative.

**What remains open:** whether Inkling is full 60, full 30, Arm A only, or omitted
from the first funded pass; the final n and ceiling; Chirag's signoff on the
recommended grid; and whether any PEFT alternative is worth preregistering.

### D05 — GPT-OSS-120B on Tinker

**Plain meaning:** the normal `openai/gpt-oss-120b` Tinker route has 32K total
context. We can use it cheaply, but the prompt plus requested output must stay below
that total. It cannot honestly run a 32K or 64K output cap with a nonempty prompt.

**Recommended implementation:** standard 32K route; low/high Arm A at 4K/16K;
four renderer conditions in the dose arm; a 20K large-cap reference; exact prompt
and wrapper bound of 8,192; hard refusal over 32,768 total tokens.

**Alternatives:**

- A: standard 32K route and smaller caps. Selected.
- B: the distinct `openai/gpt-oss-120b:peft:131072` 128K route at higher token
  prices. Useful only as a separately budgeted design.
- C: GPT-OSS-20B as a cheaper scale comparison. It is not equivalent to 120B and
  would need its own panel.
- D: omit GPT-OSS. Saves money but removes the cheapest verified graded-effort
  Tinker anchor.

**Connor's position:** choose A.

**What remains open:** the final sample count and exact renderer smoke evidence;
Chirag should confirm the scientific grid.

### D06 — Terra and the full planned model list

**Plain meaning:** Terra gives a direct OpenAI frontier-family replication with a
large context window and six documented effort settings. It is scientifically
useful because it is not a Tinker-hosted open model. Its proposed 30-item Arm A
costs at most about $125.83 before a five-call accounting smoke, leaving some room
inside the separate $200 OpenAI pool.

The current **proposed**, not frozen, scientific roster is:

1. Inkling on Tinker: continuous-effort mechanism panel, scope reopened.
2. GPT-OSS-120B on Tinker: cheap, discrete graded-effort panel.
3. GPT-5.6 Terra direct from OpenAI: closed/frontier-family replication.
4. A possible Tinker breadth panel using Nemotron Ultra and/or Qwen 3.5 397B in a
   smaller Arm-A design; not yet selected.
5. The same planned 30-of-33 HMMT-2026 subset and 4K/16K caps anchor the comparable Arm A rows.

Routes outside the scientific roster:

- OpenRouter GPT-OSS remains debug-only unless separately promoted and frozen.
- Fireworks DeepSeek V4 Flash is proposed only for development assistance, not
  study data.
- Fable 5 and Claude Opus are future separate-provider possibilities, not Tinker
  panels and not funded in the current platform pools.

OpenAI frontier alternatives from the current official catalog:

| Direct OpenAI route | Context / max output | Input / output $ per M | Same 30-item Arm-A planning maximum | Interpretation |
|---|---:|---:|---:|---|
| `gpt-5.6-sol` | 1.05M / 128K | $5 / $30 | about $314.57 | Flagship, but over the current $200 pool. |
| `gpt-5.6-terra` | 1.05M / 128K | $2 / $12 | about $125.83 | Balanced route and present recommendation. |
| `gpt-5.6-luna` | 1.05M / 128K | $0.20 / $1.20 | about $12.58 | Very cheap, but a materially different smaller model, not a fallback for Terra. |

All three document effort values `none`, `low`, `medium`, `high`, `xhigh`, and
`max`. The project must still verify the exact usage/receipt accounting before P3
can activate. See the [official OpenAI model catalog](https://developers.openai.com/api/docs/models).

**Alternatives:**

- A: omit direct OpenAI. Simplest, but loses the most direct closed frontier-family
  replication.
- B: Terra on the 30 shared items at n=8. Current recommendation.
- C: Luna as its own cheap panel. Valuable scale point, but cannot be silently
  substituted for Terra.
- D: Sol as its own flagship panel. Scientifically attractive, but the current
  design exceeds the OpenAI pool unless scope or funding changes before freeze.
- E: run multiple OpenAI family members. Stronger scaling evidence, but requires
  new funds or sharply smaller predeclared panels.

**Connor's position:** include Terra in principle, but review the complete roster
and budget before freezing it.

**What remains open:** Terra alone versus an explicitly funded family comparison,
the final model roster, and the exact five-call accounting pass rule.

### D07 — What “transition” and “rescue” mean

**Plain meaning:** the small-cap and large-cap answers are separate generations. We
can estimate whether a wrong or unfinished draw is more often replaced by a correct
independent draw at a larger cap. We cannot claim that the exact same truncated
reasoning trace would have become correct.

The recommended result is called **independent-draw expected transition mass**.
For each item, it combines the observed small-cap correctness rate with the
large-cap correctness rate, then averages across items. Rescue evidence similarly
asks whether an item produced at least one small-cap length stop and at least one
independent large-cap normal correct response.

A more complicated statistical model could estimate an item-specific probability
of small-cap unanswered stops and a separate probability of large-cap correct
answers, with correlated item difficulty and partial pooling. This would stabilize
noisy results such as 0/8 or 8/8. It could estimate an independent-draw rescue rate,
but still could not identify a same-trace counterfactual without a strong,
untestable coupling assumption.

**Alternatives:**

- A: pair replicate 1 with replicate 1 and call changes observed transitions.
  Invalid because replicate indices do not link the same underlying trace.
- B: use current item-marginal summaries and careful names. Recommended primary.
- C: add a correlated logistic-normal or Bayesian item model as a prespecified
  secondary sensitivity analysis. More stable, but introduces priors,
  distributional assumptions, convergence risk, and communication risk.
- D: report only simple small-cap and large-cap rates with no transition summary.
  Safest interpretation, but discards a useful independent-draw estimand.

**Connor's position:** choose B as primary; C is an interesting secondary research
note if Chirag believes the added assumptions are worthwhile.

**What remains open:** Chirag's approval of the names and whether the secondary
model adds enough value to justify implementation and simulation tests.

### D08 — Replicate variation and a hierarchical model

**Plain meaning:** repeated generations can differ because some problems are much
harder than others and because the same model can give different answers on the
same problem. The primary bootstrap handles this by resampling entire items.

A minimal secondary hierarchical logistic model would write the probability of a
correct answer as a function of effort, cap, and their interaction, plus a **random
item intercept** representing item difficulty. One carefully chosen item-specific
effort or `log2(cap)` slope might be added. A full random slope for every effort and
cap combination is too ambitious with only 30-60 items.

The model could report:

- fixed average effort, cap, and interaction effects;
- between-item difficulty variance;
- within-item generation variance on the probability scale;
- a latent-scale item correlation/ICC;
- partially pooled item probabilities instead of raw 0/8 or 8/8 rates.

A Bayesian version handles separation better but requires frozen priors, chains,
diagnostics, and sensitivity checks. A frequentist GLMM avoids priors but needs
frozen optimizer, convergence, singular-fit, and interval rules. Neither should
replace the primary analysis: the **item-clustered bootstrap remains primary**
because it directly targets the preregistered effects while making fewer model
assumptions.

**Alternatives:**

- A: bootstrap primary plus descriptive method-of-moments variance only. Simple
  and transparent.
- B: hierarchical model as the primary analysis. Not recommended for the first
  pass because results become more assumption-dependent.
- C: bootstrap primary, descriptive components, and a minimal frozen hierarchical
  secondary. Recommended only if implemented and simulation-tested before data.
- D: beta-binomial secondary model. Captures extra variation but does not prove
  whether it comes from batching, items, or another source.

**Connor's position:** keep the recommended primary; remain interested in C as a
secondary analysis.

**What remains open:** Chirag chooses A versus C and, if C, the exact frequentist
or Bayesian specification and failure behavior.

### D09 — Does the large-cap length model predict smaller-cap truncation?

**Plain meaning:** use the completion lengths observed at the large cap to predict
how often those answers would hit each smaller cap. Then compare that prediction
with what actually happened at the smaller cap.

Example: if the large-cap lengths predict 35% truncation at 4K and the observed 4K
rate is 42%, the absolute calibration error is 7 percentage points. A well-calibrated
length model should have small errors across the prespecified grid.

The packet proposed passing H6 only when absolute error is at most 0.10 in every
evaluable cell. That is clear, but it can be too loose near zero, too strict when
one of many cells is noisy, and it ignores that the effective sample size is closer
to the number of items than the number of generations.

A stronger formal version would use an equivalence-style item bootstrap:

1. jointly resample items across the dose and reference arms;
2. calculate the maximum absolute error across required cells;
3. form a **one-sided 95% upper confidence bound**;
4. support H6 only if every cell is evaluable and the upper bound is at most 0.10;
5. if the point estimate is below 0.10 but the bound crosses 0.10, report
   `inconclusive`, not pass;
6. apply prespecified worst-case bounds to missing rows.

Before freezing 0.10, simulate plausible item correlations and truncation rates to
see whether 30 or 60 items can realistically certify it. If not, increase the
reference replication before data or downgrade H6 to a descriptive validation.

**Alternatives:**

- A: KS distance only. Compares distribution shapes but does not directly answer
  the truncation-rate prediction question.
- B: point absolute error with `max <= 0.10`. Simple packet recommendation.
- C: maximum absolute error plus the uncertainty-aware equivalence rule above.
  Stronger and more honest, but may be underpowered.
- D: mean absolute error or RMSE. Stable summaries, but can hide one badly
  calibrated cell.
- E: report calibration descriptively with no pass/fail claim.

**Connor's position:** absolute error is sensible, but decide between B, C, and E
after Chirag reviews simulations.

**What remains open:** the tolerance, whether it is a point or confidence-bound
rule, and what missing/non-evaluable cells do to the H6 claim.

### D10 — Monotonicity across effort and caps

**Plain meaning:** H5 asks whether unanswered length stops consistently rise as
effort increases and consistently fall as the cap becomes larger. The simplest
version lists every neighboring difference and every violation.

In a 4-effort by 5-cap grid there are **31 adjacent comparisons**: 15 between
neighboring effort settings and 16 between neighboring caps. A formal “every edge
goes the expected way” claim is strict, sensitive to one noisy cell, and needs
missingness and multiplicity rules.

Possible formal tests include an intersection-union test requiring every oriented
contrast to be positive, an isotonic order-constrained goodness-of-fit test, or a
clustered ordered-trend/randomization test. The first is hard to pass, the second
can detect non-monotonicity but cannot prove monotonicity, and the third tests an
overall trend rather than every edge. Individual edge claims would need Holm or a
joint max-statistic item bootstrap.

**Alternatives:**

- A: formal ordered confirmatory test, fully specifying statistic, multiplicity,
  missingness, and randomization. Stronger-sounding, but complex and potentially
  weak.
- B: prespecified descriptive pattern: show every adjacent estimate, violation,
  missingness bound, and endpoint direction, with no p-value or “supported” label.
  Recommended first pass.
- C: remove H5. Simplest, but loses an interpretable mechanism check.
- D: formal test only as an explicitly secondary exploratory analysis. Useful
  research note if clearly separated from confirmatory claims.

**Connor's position:** choose B for the first pass; keep A/D as later methodological
work.

**What remains open:** Chirag confirms that the preregistration calls H5 a
prespecified pattern rather than a confirmatory hypothesis test.

### D11 — Exact prompt and strict grader

**Plain meaning:** every model receives the same short instruction. A response
counts as answered only if it contains a complete line matching the required
final-answer marker. The prompt asks the model to put that line at the end, but
grader v2 still accepts a complete matching line if later text follows it.

Proposed template:

```text
Solve the following problem. Show your reasoning, then end with exactly one line in
the form "Final answer: <answer>". Do not write anything after that line.

Problem:
{{ problem_text }}
```

Why this helps: no examples consume context; no provider-specific effort wording is
put in the prompt; the same task instruction is used across panels; and it matches
grader v2. A mathematically correct number without the marker remains unanswered.
That strictness is deliberate because permissive fallbacks caused the original
measurement problem. Marker compliance can be reported separately without
changing the primary grade.

Freezing a “same prompt” requires more than saving the text. Save the **exact UTF-8
template bytes**, line endings, substitution rules, every rendered item hash,
provider wrapper and renderer versions, effort encoding, stop-string list, grader
commit/hash, and terminator regex. Do not use the answer marker itself as a provider
stop string because some APIs remove the matched stop text.

**Alternatives:**

- A: one shared no-few-shot math prompt and strict terminator. Recommended.
- B: panel-specific prompts optimized for each model. May improve performance but
  weakens cross-panel comparability.
- C: add few-shot formatting examples. May improve compliance, but changes
  behavior, increases prompt cost, and must be identical and frozen.
- D: strict primary grade plus flexible secondary extraction. Not needed for the
  first-pass integer math; useful only in a separately frozen MCQ extension.
- E: allow any final number. Rejected because it recreates the fallback bug.

**Connor's position:** shared/strict looks right; exact wording remains open for
final review.

**What remains open:** template wording, whether “show your reasoning” should be
kept, exact stop strings, and all renderer/wrapper hashes.

### D12 — Seeds, replicates, order, and batching

**Plain meaning:** the schedule should be reproducible even if jobs restart or run
in a different order. Every intended sample has its own identity.

Use master seed `20260722`. Every scheduled output job identity contains panel,
`arm_key`, item, effort, cap, `sample_index`, and phase. For an individual call,
derive its request seed from that full identity. For `num_samples=n`, derive one
batch request seed from panel, arm, item, effort, cap, phase, and batch identity;
then map returned outputs to predeclared sample indices and immutable per-sample job
IDs. One batched request cannot have n different request seeds. Freeze canonical
serialization, SHA-256 conversion, byte order, integer range, and collision checks.
Randomize condition order within deterministic item blocks so time or load does not
line up with one condition. Resume only jobs that have never been attempted.

There are two ways to request replicates:

- `num_samples=n`: about 1,680 requests rather than 16,320 for a full panel. It
  shares prefill and reduces network/rate-limit exposure, but outputs may share
  hidden batch behavior and one request failure removes the whole item-cell.
- individual calls: each sample gets its own request and seed, and failures are
  smaller. It creates roughly ten times more requests, more temporal drift, more
  rate-limit exposure, and more operational load.

Eight distinct outputs do not prove independence. A batching smoke must verify
return count, per-sample mapping and IDs, usage/termination metadata, exact route,
and absence of resubmission. If `num_samples` is the frozen design and that test
fails, the panel is omitted. Switching to individual calls afterward changes the
sampling and missingness process.

**Alternatives:**

- A: freeze `num_samples=n`, activate only if its exact-route diagnostic passes,
  otherwise omit. Current recommendation for operational efficiency.
- B: freeze individual calls from the start. Cleaner per-sample identity, but many
  more requests and does not by itself fix the SDK retry problem.
- C: preregister both complete schedules and choose using an outcome-blind
  operational predicate. Flexible but substantially more complex.
- D: use the same seed for all replicates. Rejected because it can duplicate draws.

**Connor's position:** deterministic arm-aware scheduling is accepted; decide A,
B, or C after the one-submission route and receipt shapes are known from non-billed
inspection or a later frozen smoke.

**What remains open:** request unit, exact seed support by route, item-block order,
batch mapping, and whether D08 assumes independent requests or only item-clustered
dependence.

### D13 — Model portfolio, ceilings, and accounting

**Plain meaning:** every panel gets a hard worst-case dollar ceiling calculated
from its exact schedule. Expected answer length is not a safety gate. Provider
pools stay separate, and unused reserve cannot silently move between them.

Connor rejects the original approximate P1 $1,650 allocation. The Tinker portfolio
must be rebuilt before a preregistration freeze.

#### What Tinker actually exposes now

The official [Tinker Models & Pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
page listed **24 base routes** on 2026-08-10. Prices below are input/sample dollars
per million tokens; context is total sequence length.

| Family / exact route | Context | Input / output $M | Documented reasoning control | Likely REAP role |
|---|---:|---:|---|---|
| `thinkingmachines/Inkling` | 64K | 1.87 / 4.68 | Continuous effort `[0,1)` | Best mechanism panel; scope reopened. |
| `thinkingmachines/Inkling:peft:262144` | 256K | 3.74 / 9.36 | Continuous; distinct route | Expensive alternative, not fallback. |
| `thinkingmachines/Inkling-Small` | 64K | .58 / 1.44 | Not fully verified model-by-model | Cheap candidate, needs qualification. |
| `thinkingmachines/Inkling-Small:peft:262144` | 256K | 1.16 / 2.89 | Not fully verified | Distinct long-context candidate. |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16` | 64K | 2.49 / 6.225 | off / medium / full | Large open-frontier-like Arm A candidate. |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16:peft:262144` | 256K | 3.32 / 8.30 | off / medium / full | Separate expensive route. |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | 64K | .57 / 1.44 | off / low / full | Cheap graded secondary candidate. |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16:peft:262144` | 256K | .76 / 1.92 | off / low / full | Separate route. |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | 64K | .195 / .495 | No verified graded control | Scale/control candidate only. |
| `moonshotai/Kimi-K2.6` | 32K | 2.205 / 5.49 | thinking on/off | Binary anchor, not dose panel. |
| `moonshotai/Kimi-K2.6:peft:131072` | 128K | 5.15 / 12.81 | thinking on/off | Expensive separate route. |
| `Qwen/Qwen3.6-35B-A3B` | 64K | .54 / 1.335 | thinking on/off | Cheap Qwen Arm A candidate. |
| `Qwen/Qwen3.6-27B` | 64K | 1.86 / 5.595 | thinking on/off | Less attractive price/scale point. |
| `Qwen/Qwen3.5-397B-A17B` | 64K | 3.00 / 7.50 | thinking on/off | Largest Qwen, frontier-like Arm A candidate. |
| `Qwen/Qwen3.5-397B-A17B:peft:262144` | 256K | 4.00 / 10.00 | thinking on/off | Separate expensive route. |
| `Qwen/Qwen3.5-35B-A3B-Base` | 64K | .54 / 1.335 | base model | Not a native effort panel. |
| `Qwen/Qwen3.5-9B` | 64K | .66 / 1.995 | thinking on/off | Small scale comparison. |
| `Qwen/Qwen3.5-9B-Base` | 64K | .66 / 1.995 | base model | Not a native effort panel. |
| `Qwen/Qwen3.5-4B` | 64K | .33 / 1.005 | thinking on/off | Small scale comparison. |
| `Qwen/Qwen3-8B` | 32K | .195 / .60 | thinking on/off | Older small comparison. |
| `openai/gpt-oss-120b` | 32K | .33 / .84 | no-sysprompt / low / medium / high | Strong cheap graded panel. |
| `openai/gpt-oss-120b:peft:131072` | 128K | .78 / 1.94 | same discrete renderers | Separate long-context route. |
| `openai/gpt-oss-20b` | 32K | .18 / .45 | conditional | Very cheap scale/control candidate. |
| `deepseek-ai/DeepSeek-V3.1` | 32K | 1.695 / 4.215 | thinking on/off | Binary scientific candidate, not V4 Flash dev lane. |

Two beta serverless Inkling variants also exist:
`thinkingmachines/Inkling-Small:peft:262144:sampling-nvfp4` and
`thinkingmachines/Inkling:peft:262144:sampling-nvfp4`. Tinker says serverless is
not recommended for intensive production; they are not counted as base routes here.

Qwen was not forgotten. **Qwen is documented as thinking on/off**, not as a clean
four- or six-level effort axis. It therefore cannot replace Inkling or GPT-OSS in a
multi-level dose-response claim. The large `Qwen/Qwen3.5-397B-A17B` could still be
an excellent two-condition Arm A frontier-like anchor; the cheap Qwen3.6 35B could
be a scale/control panel.

Tinker contains no closed Claude or GPT-5.6 routes. **Fable 5 is not a Tinker route**,
and there is no current official model named Claude Opus 5. Anthropic's current
official Opus is Claude Opus 4.8. Fable 5 also documents mandatory 30-day retention
and automatic fallback to a less capable model for some queries, which conflicts
with the study's fixed-route/no-substitution rule. See [Claude Fable 5](https://www.anthropic.com/claude/fable)
and [Claude Opus](https://www.anthropic.com/claude/opus). They belong in a future
separately funded/provider-pinned study unless those problems are resolved.

#### Candidate Tinker portfolio shapes

These are cap-bounded planning estimates, not approvals:

The Nemotron/Qwen rows below use a deliberately smaller **breadth-anchor candidate**,
not the packet's n=20 Arm A: 30 items × 2 endpoint efforts × 2 caps (4,096 and
16,384) × n=8 = 960 generations, with a full 8,192-token prompt bound on every
generation. That is 7,864,320 prompt tokens and 9,830,400 output tokens at the
requested caps. At n=20, each listed breadth-anchor cost would be 2.5 times larger.

| Portfolio | Approximate Tinker maximum before final smoke | What it buys | Main tradeoff |
|---|---:|---|---|
| Original mechanism-heavy | Inkling full 60: $1,492.18; GPT-OSS full 60: $187.03 | Strongest two detailed panels | About 89% of these panel dollars go to Inkling. |
| Balanced discussion default | Inkling full 30: $746.09; GPT-OSS full 60: $187.03; Nemotron Ultra n=8 breadth anchor: $80.78; Qwen397 n=8 breadth anchor: $97.32; smoke ≤$2 | Continuous mechanism, cheap full discrete panel, two large open-model anchors, large reserve | Inkling has only 30 item clusters; binary/three-level anchors do not support the same dose claim. |
| Cheap breadth | Inkling n=8 breadth anchor: $60.71; GPT-OSS full 60: $187.03; Nemotron Super n=8 breadth anchor: $18.64; Qwen3.6 n=8 breadth anchor: $17.37; smoke ≤$2 | Many inexpensive directional comparisons | Greatly weakens Inkling's main mechanism/dose evidence. |
| Frontier-heavy Tinker | Inkling scope chosen separately; add Nemotron Ultra and Qwen397 n=8 breadth anchors | Better open-frontier breadth | Higher rates and only limited documented effort ladders. |

The balanced row is a useful discussion starting point, not yet the recommendation
to freeze. It leaves hundreds of Tinker dollars uncommitted for true reserve or a
power-motivated extension instead of treating the full $2,000 as a spending target.

**Alternatives:**

- A: keep original P1/P2 allocations. Statistically simple, but too concentrated
  for Connor's preference.
- B: balanced portfolio above. Best current breadth/mechanism compromise.
- C: cheap breadth. Maximizes models and reserve, weakens detailed Inkling evidence.
- D: frontier-heavy Tinker plus Terra. Strong relevance, but more route-specific
  semantics and fewer multi-level effort axes.
- E: raise ceilings or add external funds for Sol/Claude/Fable. Requires a new
  written funding and provider decision; never borrow between pools.
- F: spend only on Inkling/GPT-OSS now and save all remaining credit for a dated
  second study after the first result. Strong staged-learning option.

**Connor's position:** reopen D13 and use the catalog to build a more diverse plan;
do not allocate about $1,600 to Inkling by default.

**What remains open:** choose the exact portfolio, run item-cluster power/simulation
comparisons, freeze current rate snapshots, and calculate each hard subceiling from
the actual schedule.

### D14 — Cross-platform anchor

**Plain meaning:** run the same selected 30-of-33 HMMT-2026 questions at 4K and 16K
on each chosen scientific model, using that model's own frozen lower/higher effort endpoints. Put
the panel results side by side; do not combine them into one average effect.

**Alternatives:**

- A: no common anchor. Makes provider comparisons mostly qualitative.
- B: same dataset but different items or caps. Some comparability, but weaker.
- C: same items and caps with route-specific effort endpoints, reported separately.
  Chosen.
- D: force identical effort labels across providers. Misleading because “high” is
  not the same computational control on every platform.

**Connor's position:** choose C.

**What remains open:** which model panels join the anchor, exact shared item hash,
and each route's two verified effort endpoints.

### D15 — Fireworks DeepSeek V4 Flash development scope

**Plain meaning:** DeepSeek V4 Flash can cheaply help with mechanical repository
work, but it is not a research participant or trusted reviewer. It receives no
benchmark content, secrets, raw responses, or decisions that only the research
team can make.

Proposed exact route:
`accounts/fireworks/models/deepseek-v4-flash`. Fireworks lists 1.04M context and
$0.14/$0.28 per million input/output tokens on its [model page](https://fireworks.ai/models/fireworks/deepseek-v4-flash).

The [Fireworks data-handling policy](https://docs.fireworks.ai/guides/security_compliance/data_handling)
says open-model prompts/generations are not persistently logged by default, but
there are important conditions: token metadata is logged; prompt/KV caches may
remain in volatile memory for minutes; opt-in tools can log content; and the
Responses API defaults to storing conversations for 30 days. The allowed config
must use **Chat Completions** or explicitly set `store=False`, disable content-
logging features and fallbacks, pin/verify the served model, and use direct
Fireworks rather than a broker initially.

Allowed scope after explicit approval:

- mechanical Markdown/table drafting from non-sensitive instructions;
- bounded boilerplate and test scaffolding with named file ownership;
- formatting and small refactors with measurable checks;
- a separate ledger, per-task token/output bounds, and a **$10 cumulative hard
  ceiling** (a smaller per-task cap should also be set);
- Codex reviews every diff and reruns every claimed test locally.

Forbidden scope:

- **No research data**, benchmark items or gold answers, exploratory or
  confirmatory responses, or provider secrets;
- no paid experiment, smoke, or provider probe;
- no final scientific interpretation, model choice, statistical conclusion,
  adversarial approval, or budget/receipt decision;
- **No scientific or financial verification**;
- no automatic tool access or `--auto` mode.

**Alternatives:**

- A: leave DeepSeek disabled. Safest and current state.
- B: direct Fireworks development-only lane under the controls above. Preferred if
  Connor explicitly approves it later.
- C: OpenRouter pinned to Fireworks. Adds broker metadata and fallback/receipt risk;
  use only after separate verification.
- D: use DeepSeek as a scientific model. Not part of this decision and would
  require a separate frozen research panel.
- E: use DeepSeek for scientific or financial review. Prohibited.

**Connor's position:** conditional interest if the exact lane is genuinely ZDR and
cheap; review this scope before enabling it. It is not authorized yet.

**What remains open:** explicit approval, exact API/config file, fallback and served-
route assertions, content-logging audit, per-task ceiling, and independent review of
the development-only gate.

## Recommended next conversation with Chirag

Connor can settle D11, D12, and the preferred D13 portfolio proposal before the
call. Chirag's highest-value scientific input is narrower:

1. Is 30 shared HMMT items enough, or is the extra 2025 cohort worth the cost and
   complexity?
2. How much Inkling mechanism evidence is necessary: full 60, full 30, or Arm A
   only?
3. Should D08 include a minimal hierarchical secondary model, or remain
   descriptive?
4. Should H6 use the uncertainty-aware equivalence rule, and can simulations show
   that `0.10` is certifiable?
5. Confirm H5 as a descriptive pattern rather than a formal confirmatory test.

The call does not need to revisit provider implementation details unless a
scientific choice depends on them. After the call, choices should be recorded in a
new dated approval record, then transferred into the new REAP preregistration and
frozen manifests. Nothing in this worksheet opens Phase 4 or authorizes a call.

## Primary mutable sources checked

- [MathArena HMMT Feb 2026 source card at `ea21409`](https://huggingface.co/datasets/MathArena/hmmt_feb_2026/blob/ea21409b2e8362f71205985277b4c084f30c92cc/README.md)
- [Tinker Models & Pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
- [Tinker renderer registry](https://tinker-docs.thinkingmachines.ai/cookbook/api-reference/renderers/get_renderer/)
- [Tinker OpenAI-compatible effort behavior](https://tinker-docs.thinkingmachines.ai/tinker/compatible-apis/openai/)
- [OpenAI model catalog](https://developers.openai.com/api/docs/models)
- [Claude Fable 5](https://www.anthropic.com/claude/fable)
- [Claude Opus](https://www.anthropic.com/claude/opus)
- [Fireworks DeepSeek V4 Flash](https://fireworks.ai/models/fireworks/deepseek-v4-flash)
- [Fireworks ZDR and retention](https://docs.fireworks.ai/guides/security_compliance/data_handling)

Provider catalogs and prices were retrieved on 2026-08-10. They are planning facts,
not runtime evidence. Before freeze, the exact route, price, and documentation
snapshots must be hashed. Before activation, the frozen human-run smoke must still
pass.
