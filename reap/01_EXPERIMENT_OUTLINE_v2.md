# REAP experiment outline v2 — for Chirag's review

**Status:** draft for discussion; becomes preregistration content once agreed. Nothing here has run.
**Estimand language unchanged from Phase I:** effort slope D_c = A(high effort, c) − A(low effort, c); primary interaction I = D_large − D_small; token-starved/no-answer row = length termination ∧ no extractable answer; larger-cap runs are independent draws, never continuations.

## Panels (platform × model)

| Panel | Platform | Model | Effort control | Why it's in |
|---|---|---|---|---|
| P1 | Tinker | **Inkling** | continuous scalar [0.0–1.0), 6 presets (none→xhigh) | the only continuous effort knob anywhere; dose-response |
| P2 | Tinker | **GPT-OSS-120B** | 3 discrete renderer levels + no-sysprompt arm | cheap ($0.84/M out), discrete-effort contrast, "Reasoning"-typed |
| P3 | OpenAI | **gpt-5.6-terra** | `reasoning.effort` enum, Responses API | closed-model replication where cap-inclusiveness is *documented*; uses Chirag's $200 |
| P0 | OpenRouter | gpt-oss-120b | native `reasoning_effort` | pipeline debugging + cross-provider sanity vs P2 ($0.67 per 300-gen cell) |

Panels are reported separately (directional replications), never pooled.

## Arms (within each Tinker panel)

- **Arm A — confirmatory replicated factorial:** 2 effort levels × 2 caps × n=20 per item. The Phase I 2×2, now with real variance estimates. Caps chosen per panel to straddle the truncation transition (from the pilot length model: ~4k and ~16k for high-effort regimes).
- **Arm B — dose-response grid:** 4 effort levels × 5 caps (2k, 4k, 8k, 16k, 32k) × n=8. Traces the full starvation surface; the mechanism becomes a curve, not a contrast.
- **Arm C — uncapped reference:** all effort levels at 64k, n=8. Near-uncensored length distributions per effort level.
- **Cap-invariance validation (the novel piece):** fit the length distribution per effort from Arm C, *predict* the truncation rate at each Arm B cap, compare predicted vs observed. This directly tests the transfer assumption Coupling Tax assumes and never checks — and is the live-model validation of the paper's censoring framework. (KS test on common support, per the July review's recommendation.)
- P3 (OpenAI, $200): Arm A only, n=28 sync / up to 56 batched at ~13k tokens.

## Datasets

Core: **HMMT Feb 2025 + Feb 2026** (MathArena; 60 items, integer answers, CC BY-NC-SA) — chosen because MathArena's *published outputs* already show the effect (e.g., GPT-OSS-20B high: 16.7% of generations at cap scoring 0% vs 92% below cap) and give free length priors before we spend a dollar. Continuity: **AIME 2025/2026**. Extensions (scope with Chirag): **GPQA-Diamond** (cross-domain, MCQ — adversarial grader test), **HARP hardest bracket** (difficulty × effort × cap axis, MIT). Negative control: **GSM8K** (easy; also the harness-pathology exhibit — shipped 256-token default + last-number extraction). Details and risks: `04_DATASET_CANDIDATES.md`.

## Measurement discipline (Phase I machinery, extended)

- `max_tokens` explicit on every call (Tinker SDK default is None; server default undocumented; the cookbook's own effort script sets caps *as a function of* effort — the confound we must never inherit).
- Effort on Tinker is a system-prompt intervention → renderer/prompt held fixed within panel; effort explicitly pinned on the OpenAI-compat route (silent default 0.9).
- Termination captured at collection: `stop_reason` / `incomplete_details.reason` / `finish_reason`+receipts. Grading: strict `Final answer:` terminator rule; strict vs flexible extraction reported side-by-side on MCQ.
- `num_samples` batching on Tinker shares prefill billing — draw all n replicates per item in one call.
- Pre-run cap-semantics probes on every platform surface at the caps we will use.

## Analysis (frozen before data)

Per cell: accuracy + Wilson; all/unanswered/answered length stops; completion & reasoning token distributions; [k/n, (k+u)/n]. Primary: effort slopes and interactions per panel with item-clustered bootstrap (now with replicate-level variance components). Dose-response: accuracy and unanswered-stop surfaces over effort × cap. Validation: predicted-vs-observed truncation rates per cap with calibration error. Missingness and sensitivity per Phase I amendment discipline.

## Open questions for Chirag

1. Arm sizes: n=20/8/8 as sketched, or rebalance? (Budget allows 3× this.)
2. Which two effort levels anchor Arm A on Inkling's continuous scale (0.2 vs 0.99? presets only?)
3. GPQA-Diamond in or out of the first paper? (Gated license, MCQ guessing floor.)
4. Does the cap-invariance validation live in the main text as the third contribution?
5. Random-effects model for replicates (item × generation) — your call on the formulation.
