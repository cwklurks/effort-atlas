# Phase 3 adversarial synthesis — 2026-08-10

**Status:** non-frozen working record. This document records evidence,
recommendations, and unresolved human decisions. It does not authorize a model
call, smoke test, provider probe, spend, route activation, preregistration freeze,
or confirmatory collection.

```text
CONFIRMATORY_CALLS=0
PAID_STUDY_GENERATION_CALLS=0
PAID_SMOKE_CALLS=0
PROVIDER_PROBE_CALLS=0
DEEPSEEK_DEVELOPMENT_CALLS=0
```

## Bottom line

The study structure is worth continuing, but it is not ready to freeze. The best
current first-pass design has two detailed Tinker models, two cheaper Tinker
breadth models, a direct OpenAI pair, and a conditional same-model OpenRouter
replication. The direct OpenAI pair should be **Terra as the main closed-model
anchor plus Luna as a cheap GPT-5.6 family sensitivity panel**. At the current
official prices, both declared 30-item maximum-token shapes fit together inside
the $200 OpenAI pool before smoke.

The most important remaining scientific decision is the number and provenance of
independent items. Rows 31–33 of the current 33-row HMMT-2026 source still lack a
settled first-party round mapping. The planning default remains items 1–30 until
that provenance is resolved. Chirag still needs to rerun the power and calibration
simulations with the actual length priors and the estimator's nested cap structure.

The largest engineering risks found during review were real: arm mixing, seed
collisions, caller-controlled activation gates, manifest aliasing, discount-only
budget approval, and an unpinned symbolic scorer path. Decision-independent
offline guards now exist for each of those classes, but the integrated branch must
pass a fresh independent review and canonical offline suite before any Phase 3
implementation claim is accepted.

## What the model loop established

A bounded development relay exchanged two rounds between Claude Fable 5 on
Connor's regular Claude subscription and GPT-5.6 Sol at XHigh. It used a tracked,
read-only repository snapshot and made no research-generation or provider-study
call. Fable and Sol converged on the following C01–C07 verdicts:

| Claim | Agreed verdict | Current consequence |
|---|---|---|
| C01 — dataset scope | Partially confirmed | Repository documents conflict on 30 versus 33. Keep 30 as a planning default; Connor and Chirag must settle the provenance rule. |
| C02 — Terra effort semantics | Resolved by a later primary-source check | Current OpenAI guidance lists `none`, `low`, `medium`, `high`, `xhigh`, `max`; it does not list `minimal`. Exact route delivery still needs the frozen smoke. |
| C03 — cost provenance | Partially confirmed, then materially improved | Arithmetic was correct conditional on quoted rates. A dated advisory price artifact and strict list/discount planning validator now exist. They are not freeze authority; the executable exact-artifact budget gate remains a Phase-4 runner requirement. |
| C04 — simulation fidelity | Partially confirmed | Scratchpad numbers reproduce their code, but the H6 simulation does not reproduce the estimator's shared nested length draws. Chirag's rerun remains authoritative. |
| C05 — scorer boundary | Initially prose-only; implementation added afterward | A fail-closed boundary now accepts only grader-v2's extracted field and caller-supplied, version/hash-pinned `parse_answer` and `check_answers`. The real MathArena revision is still a human freeze input. |
| C06 — durable state | Partially confirmed | Safety was preserved, but the dashboard/test count and relay state were stale. They must be regenerated from the final verified branch. |
| C07 — scratchpad provenance | Origin claim unverified | The defensible statement is that the committed scripts reproduce the review tables. “Transferred verbatim” should not be treated as independently proven. |

This completed relay is useful development evidence, not freeze-authoritative
evidence. The first completed run predated the relay hardening that enforces a
clean Claude session, first-party Claude subscription authentication reported as
`claude.ai`, and Codex
`--ignore-user-config`. Internal CLI request counts also remain unverified. Model
agreement does not close a decision owned by Connor or Chirag.

## Recommended model roles

| Role | Model and route | Recommendation | Why | Status before freeze |
|---|---|---|---|---|
| Detailed continuous-effort mechanism | Standard `thinkingmachines/Inkling` on Tinker | Keep, but do not reserve the old full amount automatically | It is the clearest graded-effort model. Its 30-versus-60 item scope and n require Chirag's power result and a list-rate-safe ceiling. | Scope and ceiling open; PEFT is a separate later design, never fallback. |
| Detailed inexpensive open-model replication | Standard `openai/gpt-oss-120b` on Tinker | Keep | It is cheap and provides a discrete-effort detailed panel. Use the standard 32K route and explicit context refusal. | Recommend exact Arm-C cap 20,480, pending Connor/Chirag sign-off. |
| Large open-model breadth | Qwen3.5 397B on Tinker | Keep as a smaller breadth panel | Qwen was intentionally requested; binary thinking off/on broadens model coverage without pretending to be a continuous dose. | Exact renderer support and route must be qualified. |
| Large open-model breadth | Nemotron Ultra 550B on Tinker | Keep only if its list-rate subceiling fits | It adds a different large open-model family. Both list and promotion rates are now represented. | A promotion may reduce spend but may not define the hard freeze ceiling by itself. |
| Main direct closed-model anchor | `gpt-5.6-terra` through OpenAI direct | Keep | It balances capability and cost and supports the family-level medium/xhigh contrast. | Exact route effort delivery and accounting smoke required; record possible HMMT-2026 exposure. |
| Cheap closed-family sensitivity | `gpt-5.6-luna` through OpenAI direct | **Add beside Terra, not instead of it** | It is unusually cheap and gives a useful same-family lower-capability scale point with almost no pressure on the $200 pool. | Treat as a separately reported replication; exact route smoke required. |
| Frontier upper endpoint | `gpt-5.6-sol` through OpenAI direct | Postpone at the current n/items | It is the strongest GPT-5.6 tier, but the declared shape exceeds the $200 OpenAI pool. | A later smaller, separately powered design could revisit it. |
| Same-model cross-platform replication | `openai/gpt-oss-120b` through one pinned OpenRouter provider | Keep conditional | It isolates an operational route replication better than comparing unrelated models. | Pin one provider, no fallback, ZDR, precision, tokenizer/wrapper, supported parameters, receipt identity; otherwise omit. |
| Cheap development assistance | DeepSeek V4 Flash through direct Fireworks ZDR | Leave disabled | It could do bounded mechanical development cheaply, but it is not scientific evidence and no concrete task currently requires it. | Needs explicit configuration, ledger, served-route assertions, and hard dollar ceiling approved by Connor. |
| Future closed-provider extension | Fable 5, Claude Opus, and later GPT models | Later study | They are scientifically interesting frontier endpoints but require distinct providers, budgets, retention rules, and route semantics. | Do not add them silently to the first freeze. |

The route-specific effort endpoints are not a shared numerical dose. Inkling
0.7/0.99, GPT-OSS low/high, Terra or Luna medium/xhigh, Qwen thinking off/on, and
Nemotron off/full must be analyzed and reported separately.

## Current direct OpenAI price comparison

The official model pages retrieved on 2026-08-10 currently state:

| Model | Input / cached / output per 1M tokens | Declared 30-item maximum before smoke |
|---|---:|---:|
| GPT-5.6 Luna | $0.20 / $0.02 / $1.20 | $12.582912 |
| GPT-5.6 Terra | $2.00 / $0.20 / $12.00 | $125.829120 |
| Luna + Terra | — | $138.412032 |
| GPT-5.6 Sol | $5.00 / $0.50 / $30.00 | $314.572800 |

The maximum uses 3,932,160 prompt tokens plus 9,830,400 output tokens per model,
not expected response length. These are mutable planning prices, not a quote or
spending authority. The freeze package must capture a new dated source artifact,
recompute exact schedules, include smoke rows, and fail if pool or panel exposure
does not fit.

Primary pages:

- <https://developers.openai.com/api/docs/models/gpt-5.6-luna>
- <https://developers.openai.com/api/docs/models/gpt-5.6-terra>
- <https://developers.openai.com/api/docs/models/gpt-5.6-sol>
- <https://developers.openai.com/api/docs/guides/latest-model>

## Dataset recommendation

Use HMMT-2026 short-answer math as the shared cross-model core because it gives a
recent, difficult, compact item set with structured gold answers. The source now
contains 33 rows:

- rows 1–10 map to Algebra/Number Theory;
- rows 11–20 map to Combinatorics;
- rows 21–30 map to Geometry;
- rows 31–33 are not yet tied to a settled first-party round label.

Therefore:

1. Planning and cost comparison may use the fixed 1–30 core.
2. The freeze must not call 1–30 a “clean integer” set; the golds include LaTeX
   fractions, radicals, powers, and a degree sign.
3. The final item manifest must state the exact source revision, license, IDs,
   selection rule, gold/schema hashes, scorer mode, and provenance evidence.
4. If rows 31–33 are documented as legitimate individual-round items, Connor and
   Chirag may freeze all 33 instead. The choice must happen before outputs exist.
5. HMMT-2025 is a possible additional 30-item cohort for detailed Tinker panels,
   not an automatic extension. Its value is more independent clusters; its cost is
   extra grading, power, cohort, and budget complexity.

AIME, GPQA Diamond, HARP, and GSM8K remain later extensions. They do not solve the
first-pass provenance and power questions as cleanly as finishing HMMT correctly.

## Decision record after the review

| ID | Recommended working answer | What remains human-owned |
|---|---|---|
| D01 | Freeze science and exact activation rules, review runner, then human-start a Tinker reliability smoke capped at $2; unchanged route activates or is omitted. | Connor and Chirag sign the scientific freeze; Connor alone starts any smoke. Current Tinker SDK path remains blocked. |
| D02 | Independent A/B/C arms with `arm_key` in schedule, cache, ledger, and analysis identity. | Scientific sign-off. Generic code now enforces the structural rule. |
| D03 | Plan on HMMT-2026 items 1–30 until rows 31–33 provenance resolves; add HMMT-2025 only if power justifies it. | Connor + Chirag choose 30/33 and 2025 extension. |
| D04 | Standard Inkling and the proposed scientific direction; never auto-switch to PEFT. | Chirag chooses scope/n/grid; Connor chooses a list-rate-safe ceiling. |
| D05 | Standard 32K GPT-OSS-120B; recommend exact 20,480 reference cap and hard context refusal. | Connor records exact cap; Chirag signs the design. |
| D06 | Terra main anchor plus Luna cheap family sensitivity; Sol later. | Connor freezes roster and OpenAI ceiling; route accounting/delivery smoke must pass. |
| D07 | Independent-draw transition/rescue summaries primary; no continuation language. | Chirag confirms estimand names and any secondary model. |
| D08 | Item bootstrap primary; method-of-moments descriptive; hierarchical model only as frozen, simulation-tested secondary. | Chirag decides whether the secondary model is worth including. |
| D09 | H6 descriptive for the first pass unless Chirag's estimator-faithful simulation shows a supportable uncertainty rule. | Chirag specifies cells, tolerance, estimator, and inconclusive behavior. |
| D10 | Descriptive monotonicity and all adjacent violations; formal ordered test later. | Chirag confirms H5 wording. |
| D11 | Exact `Final answer:` extraction followed by a pinned deterministic MathArena parse/check boundary; freeze prompt bytes and renderer. | Connor selects exact prompt and MathArena revision/mode after schema tests. |
| D12 | One independently scheduled call per output is the conservative first-pass unit; master seed 20260722 and full arm/phase identity derive seeds. | Connor freezes request unit. Batching remains omitted unless separately proven safe before freeze. |
| D13 | Diversified Tinker portfolio, with Inkling scope reduced if its list-rate maximum crowds out breadth or reserve. | Connor + Chirag choose exact schedules, panel ceilings, and real reserve. |
| D14 | Shared core and 4K/16K caps, separate reports, conditional same-model Tinker/OpenRouter route replication. | Connor selects and qualifies one exact OpenRouter provider or omits the panel. |
| D15 | Keep DeepSeek disabled until a concrete development task justifies the narrow Fireworks ZDR gate. | Connor approves configuration and ceiling before any use. |

## Offline implementation completed in this phase

The branch now contains decision-independent building blocks, not a frozen study:

- arm- and phase-aware schedule identity with an explicit master seed, canonical job
  IDs, deterministic provider seeds, and provider-seed collision refusal;
- production analysis refusal for mixed or partially labeled arm-aware inputs;
- a sealed manifest contract with cross-artifact hashes, detached data, and exact
  byte verification beneath an approved root;
- manifest-bound activation policy with only `activate` or `omit` outcomes;
- non-authoritative exact Decimal planning projection, list-rate default, proposed
  pool and panel ceilings, and an explicit receipt-policy requirement for discount
  planning;
- a fail-closed MathArena boundary that never imports upstream answer extraction or
  falls back to local parsing;
- generic dataset and simulation provenance manifests;
- a bounded relay that requires first-party Claude subscription authentication
  reported as `claude.ai`, a clean session for a freeze review, and Codex
  user-configuration isolation;
- an end-to-end offline test that separately exercises strict planning-budget
  arithmetic and exact-byte schedule, manifest, and activation boundaries without
  presenting the planning inputs as freeze authority.

The integrated branch passes the canonical offline suite (250 ordinary tests plus
26 exact-lock Tinker tests). Final adversarial review approved exact head `f9aef0b`
with no critical or warning findings. These components are prerequisites for the
future runner, not the runner itself.

## Questions for the supervisor call

1. Are 30 independent HMMT-2026 items enough for the Inkling interaction and
   detailed mechanism claims, or should HMMT-2025 be added before freeze?
2. Given the unresolved rows 31–33 provenance, should the frozen burden of proof be
   “use 30 unless 33 is documented” or “use 33 unless 30 is documented”?
3. Does the proposed Inkling A/B/C grid retain adequate power at a budget that does
   not crowd out GPT-OSS, Qwen, Nemotron, and reserve?
4. Should H6 be purely descriptive in the first paper, given that the current
   scratch simulation does not match the estimator's nested cap dependence?
5. Is the item-clustered bootstrap plus descriptive variance decomposition enough,
   or should a small hierarchical secondary model be frozen and simulation-tested?
6. Are H5 monotonicity and transition/rescue correctly described as patterns and
   independent-draw summaries rather than paired causal continuations?

## Stop condition

Phase 3 remains open until the dataset/item rule, exact model roster and routes,
caps, effort values, n, prompt bytes, scorer revision/mode, request unit, analysis
rules, price snapshots, and hard ceilings are recorded in a new REAP v2 freeze
package and signed by the appropriate humans. Until then, the next work is offline
implementation, review, and decision preparation only.
