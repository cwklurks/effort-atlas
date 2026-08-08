# Dataset candidates — ranked slate with evidence

Selection criteria: verifiable final answers · hard enough to induce long reasoning · small enough to replicate · licensable · evidence of real-world truncation exposure.

## Core slate

**1. HMMT Feb 2025 + Feb 2026 (MathArena) — core.** 30 items each, integer/closed-form answers, CC BY-NC-SA 4.0 (HF: MathArena/hmmt_feb_2025, hmmt_feb_2026). Decisive evidence, measured from MathArena's own published outputs: multiple models with 10–57% of generations at cap; e.g. GPT-OSS-20B (high): 16.7% at cap scoring **0%** vs **92%** below cap — an independent public replication of Oladri et al.'s AIME finding on a different benchmark. Their outputs also show the effort dose-response for free (o4-mini median tokens low/med/high: 2.2k/5.2k/11.9k; p90 at high = 38k). MathArena documents no token limits or truncation handling on-site. Bonus: the published outputs give us length priors and power analysis at $0.

**2. AIME 2025/2026 — continuity.** 30 items each; integer 0–999 (cleanest extraction in math eval). HF: MathArena/aime_*; math-ai/aime25 (lm-eval's task). Evidence: lm-eval raised AIME's cap to 32,768 as an explicit remediation — while 2026-era model outputs (public parquets) show p90 lengths of 57k–85k, i.e. the remediated cap is already insufficient. Caps rose; lengths rose faster.

**3. GPQA-Diamond — extension 1 (cross-domain, adversarial grader test).** 198 items, 4-way MCQ, CC BY-4.0 but HF-gated (no plaintext redistribution). Evidence: lm-eval's gpqa cot/generative tasks ship with **no max_gen_toks → default 256** on a benchmark where reasoning models emit 5k–30k tokens. Caveat that makes it scientifically interesting: the `group_select: -1` letter-extraction fallback manufactures ~25% fake-correct on truncated rows — biasing the interaction toward null — so strict-vs-flexible dual scoring becomes a publishable diagnostic.

**4. HARP hardest bracket — extension 2 (difficulty axis).** 197 problems in the top difficulty tier of 5,409 (MIT license, github.com/aadityasingh/HARP; deliberately not on HF). Six calibrated difficulty levels → a third dose-response axis: truncation rate should rise with difficulty at fixed cap. Distinguishes the starvation mechanism from genuine overthinking.

**5. GSM8K — negative control + harness-pathology exhibit.** 1,319 items, MIT. Too easy for the main effect — which is the point (short chains, near-zero truncation → the interaction should vanish; if it doesn't, something else is wrong). And the exhibit: lm-eval's gsm8k.yaml inherits the **256-token default** AND ships `flexible-extract` with `group_select: -1` — *take the last number anywhere* — the exact fabricated-extraction defect we found independently, shipping as a default in the ecosystem's most-used harness.

## Excluded, with reasons

FrontierMath (held out; unrunnable) · ARC-AGI-2 (grid output, no extractable final answer; truncation catastrophic-by-construction, doesn't isolate the mechanism) · OlympiadBench TP_* proof splits (no autograder; a truncated proof is unscoreable) · LiveBench math (4,096 default is citable, but contamination-limited and license unconfirmed) · HLE (longest traces but LLM-judge grading confounds truncation with wrongness; revisit later, ≤100 items).

Worth citing though not running: OlympiadBench OE_TO_maths_en_COMP (674 items, Apache-2.0) as the harder-tier option if HARP disappoints.

## Ecosystem-default evidence (for the paper's motivation section)

| Harness | Default output cap | Source |
|---|---|---|
| lm-evaluation-harness | **256** (`DEFAULT_MAX_GEN_TOKS`) | lm_eval/defaults.py |
| — gsm8k, minerva_math, hendrycks_math, gpqa cot/generative | inherit 256 | task yamls (no max_gen_toks key) |
| — leaderboard/math | 1024 | _template_yaml |
| — aime24/25 | 32,768 (remediated; already insufficient) | aime/*.yaml |
| OpenCompass | modal 512 (149 configs) | configs/datasets/** |
| LiveBench | 4,096 | repo README |
| OpenAI simple-evals | 2048 chat / 1024 responses — **but omits the cap entirely for reasoning models** (handled correctly; the asymmetry is the "awareness gap" argument — do not claim they cap reasoning models) | simple_evals.py |

Incident reports to cite: lm-eval #3382 (truncated reasoning parsed as final response), #3044/#3391 (cap-exhaustion crashes extraction), inspect_ai #3582 (UK AISI: reasoning models hit legacy limits, "invisible in logs"), GateScope arXiv:2604.21083 (silent truncation across 10 gateways).

## Grader risks (top-3), for grader v2's test suite

- **MathArena/AIME/HMMT:** lm-eval's `remove_boxed` asserts on truncated-mid-box (`\boxed{29` → swallowed AssertionError → silent fallback to a `$…$` blob). Never infer truncation from grader output; log termination at collection.
- **GPQA:** `group_select: -1` letter-grab = ~25% fake-correct on deletions. Strict-match primary; flexible reported alongside.
- **OlympiadBench (if used):** numeric-tolerance matching can accept a truncated partial number (`3.14` from `3.1415…`). Require terminator-bearing answers; tighten tolerance.
