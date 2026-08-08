# Related-work alert — read before any design or writing decision

**Date found:** 2026-08 (post-funding search). **Action owner:** Connor to brief Chirag in Slack/next call.

## The finding

**Nie et al., "The Coupling Tax: How Shared Token Budgets Undermine Visible Chain-of-Thought Under Fixed Output Limits" (arXiv:2605.07686, NTU)** substantially overlaps the censoring half of our paper:

- Sweeps output budgets b ∈ {128 … 4096} on GSM8K, MATH-500, BIG-Bench Hard (Qwen3/Qwen3.5, DeepSeek-R1-Distill, local vLLM).
- **Uses Kaplan-Meier estimation for right-censored chain lengths** (Fig. 5 caption: "Kaplan-Meier estimation accounts for right-censored chains that hit the budget ceiling").
- Predicts accuracy from the chain-length CDF: Acc(b) = α_c·F_L(b) + α_t·(1−F_L(b)), validated held-out.
- Headline: think@512 = 56.9% vs no-think@512 = 93.1% on GSM8K.

**Consequence: "KM applied to censored LLM generation lengths" cannot be claimed as novel.** They must be cited and credited as the closest prior work.

## What they did NOT do — our surviving contributions

1. **No native effort axis.** They compare binary `enable_thinking` on/off only. Graded native effort (Inkling's continuous scalar; GPT-OSS/OpenAI's low→xhigh enums) × allowance is unexplored — and public MathArena data already shows ~5× median-length dynamic range across effort levels, which binary modes cannot resolve.
2. **No replication.** Greedy decoding throughout ("to isolate truncation from sampling variance"); their temperature pilot is single-sample. Our replicated factorial (n=8–20) estimates run-to-run variance and per-item effects they cannot.
3. **No cap-invariance validation.** They *assume* the length CDF measured at one budget transfers to others; no experiment tests it. Our design measures F_L at large caps, predicts truncation at small caps, and verifies — this validates the assumption their entire predictive formula rests on, and is our cleanest novel contribution.
4. **No API reasoning models.** Local open-weight only; no billed black-box effort parameters, no route/receipt verification.

## Recommended repositioning (for the meeting)

- Cite Coupling Tax as closest prior; credit KM-on-CoT to them explicitly.
- Our claim: **the effort-axis generalization + replication-based variance decomposition + the missing cap-invariance validation, on both open and API reasoning models, with route-level verification.**
- Chirag's Sections 3–4 remain fully valuable: the corrected estimator, the identified range, the semi-synthetic ground-truth validation are all things Coupling Tax does not do carefully — but the framing "we introduce survival analysis to LLM lengths" must soften to "we give the censoring analysis its correct statistical footing and validate its transfer assumption."

## Supporting near-misses (cite, none scooping)

- arXiv:2506.09250 — "Comment on The Illusion of Thinking": a famous "reasoning collapse" shown to be an output-limit artifact. Best rhetorical anchor.
- arXiv:2506.04210 — "Mirage of Test-Time Scaling": live overthinking claim that does not control truncation — a direct target our mechanism may explain.
- arXiv:2605.16938 — effort behaves as a ceiling (supports the interaction hypothesis; no cap variation).
- arXiv:2602.14444 (Broken Chains), arXiv:2602.09805 (Kaiser), arXiv:2607.21433 (Oladri) — existing anchors.
- **Tinker's own cookbook** (`scripts/inkling/sample_reasoning.py`): `_default_max_tokens(effort)` returns 4096/8192/16384 by effort tier, default prompt AIME 2025 — the vendor reference implementation confounds effort with allowance by construction. Citable motivating evidence.
- lm-evaluation-harness `DEFAULT_MAX_GEN_TOKS = 256` + `group_select: -1` last-number extraction shipped as defaults; UK AISI inspect_ai issue #3582 ("token limits… invisible in logs"). The pathology is ecosystem-default, not anecdote.

## Before submission

Run a citation-graph forward search on 2605.07686 and 2602.09805 — the KM overlap was found only by lateral search; assume 1–2 more partial overlaps exist.
