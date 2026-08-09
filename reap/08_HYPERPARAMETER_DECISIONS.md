# Hyperparameter decision matrix

Every knob in REAP, its options, the current recommendation, who/what decides it, and verification status. Facts marked VERIFIED cite Tinker/OpenAI docs (2026-08); UNVERIFIED items get resolved in the smoke tests, never assumed.

| # | Knob | Facts | Recommendation | Decided by |
|---|---|---|---|---|
| 1 | **Effort axis (Inkling)** | VERIFIED: effort is a renderer **API parameter**, continuous scalar in **[0.0, 1.0)**; presets none=0.0, minimal=0.1, low=0.2, medium=0.7, high=0.9 (default), xhigh=0.99. Docs explicitly warn NOT to write the system message manually. | Arm A anchors: 0.7 vs 0.99 (matches pilot's medium/max contrast). Arm B: 4 points spanning the range (e.g. 0.1 / 0.4 / 0.7 / 0.99). **Opportunity: a continuous-effort dose-response no closed model permits — consider a 6–8 point sweep in Arm B.** | Chirag + MathArena dose-response fit |
| 2 | **Effort axis (GPT-OSS, OpenAI)** | VERIFIED: OpenAI `reasoning.effort` takes named levels only (none…xhigh, max; model-dependent); numeric values UNVERIFIED — use enum. GPT-OSS on Tinker: discrete renderer levels. | Two-level contrast on P2/P3 mirroring Arm A. | fixed |
| 3 | **Cap grid** | Straddle the truncation transition per effort. Priors come free from MathArena + HELM length fits before any spend. | B: 2k / 4k / 8k / 16k / 32k; C reference 64k; refine placement after the length-prior study; freeze in prereg. | length priors → prereg |
| 4 | **n per cell** | Replication is the grant's gift; cost model says 3× headroom. | A n=20, B n=8, C n=8, power-checked against prior-derived effect sizes. | Chirag (power analysis) |
| 5 | **Sampling params (Tinker)** | VERIFIED SamplingParams: max_tokens, **seed**, stop, temperature, top_k, top_p. `num_samples` = "independent samples" (VERIFIED wording; verify empirically). | Temperature: model-recommended default, fixed and recorded per panel. Seeds: preregistered seed schedule per generation (reproducibility gift — use it). Replicates via num_samples per item (shares prefill billing); confirm sample-independence in smoke. | fixed after smoke |
| 6 | **max_tokens** | Explicit on every call, every platform (Phase I law). Tinker per-request maximum undocumented (UNVERIFIED — probe). OpenAI: gpt-5.6 family max output **128K**, context 1.05M (VERIFIED). | Probe the undocumented Tinker default AND ceiling in smoke; record both. | smoke |
| 7 | **Truncation labels** | Tinker: stop_reason (verify vocabulary in smoke). OpenAI VERIFIED: `status="incomplete"` + `incomplete_details.reason="max_output_tokens"` — and it **can fire before any visible output token** (reasoning ate the whole budget). | Capture labels at collection on every row; the OpenAI zero-visible-output case is a distinct category — count it separately (pure-starvation row). | fixed |
| 8 | **OpenAI budget validation** | UNVERIFIED community report: gpt-5.6 `usage.output_tokens` inflated ~9× vs actual generation. With only $200 in this pool, an accounting bug is fatal. | First OpenAI block: 5 small calls, reconcile usage-vs-billing-vs-retokenized-text **before** any batch. Measure lengths from returned text as primary, usage as secondary. | smoke, week 2 |
| 9 | **Prompt template** | One fixed template across all cells; includes the `Final answer:` terminator instruction (grader v2's contract); no few-shot. Inkling: never hand-write the effort system message. | Freeze exact template text + hash in prereg. | prereg |
| 10 | **Order & schedules** | Phase I machinery: seeded item order, permuted conditions within item, SHA-256'd schedules committed pre-execution. | Re-export for REAP arms; seed recorded in prereg. | fixed |
| 11 | **Grading** | Strict terminator extraction (grader v2). MCQ (GPQA if adopted): strict primary, flexible secondary — the divergence is itself a diagnostic. Non-math arms: execution-based (LiveCodeBench) / deterministic grid check (ZebraLogic) if adopted. | Grader frozen at commit hash before data; tested on the 78-row Tinker log (must report 78 unanswered truncations). | grader v2 + prereg |
| 12 | **Reserve triggers** | $3,000 Tinker reserve untouchable without a written scope note; mid-run pause if observed truncation deviates >15pp from prediction. | unchanged from 02_BUDGET | fixed |

## The three decisions that need Chirag specifically

1. Arm sizes + power formulation (knob 4) and the replicate variance model.
2. Continuous-effort sweep on Inkling (knob 1): scientific upgrade vs analysis complexity — his call on whether the dose-response modeling stays simple (discrete levels) or exploits continuity.
3. Whether the observational arm (HELM/MathArena found-data analyses) is a paper section or supporting material.

## The four facts smoke tests must settle before prereg freeze

Tinker's undocumented default max_tokens; Tinker's stop_reason vocabulary; num_samples independence; OpenAI usage-accounting sanity on gpt-5.6-terra.
