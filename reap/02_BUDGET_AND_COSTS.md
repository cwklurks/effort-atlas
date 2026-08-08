# REAP budget and cost model

**Pools (platform-scoped, never mixed):**

| Pool | Amount | Platform | Use |
|---|---|---|---|
| Tinker Research Grant | $5,000.00 | Tinker (Thinking Machines) | Panels P1 (Inkling), P2 (GPT-OSS-120B) — all arms |
| Chirag OpenAI key | ~$200.00 | OpenAI API | Panel P3 closed-model replication (gpt-5.6-terra, Responses API, batch where possible) |
| Personal | <$100.00 | OpenRouter | P0 debugging + cross-provider sanity only |

**Unknowns to resolve with Thinking Machines before scheduling (email tinker@thinkingmachines.ai):** grant expiry; rate/concurrency limits; publication acknowledgment requirements.

## Verified prices (2026-08; sample/output $ per 1M tokens)

Tinker: GPT-OSS-20B $0.45 · GPT-OSS-120B $0.84 · Qwen3.6-35B-A3B $1.335 · Inkling-Small $1.44 · Inkling $4.68 · DeepSeek-V3.1 $4.215. Cached prefill −80%; `num_samples>1` shares prefill billing.
OpenAI: gpt-5.6-luna $0.20/$1.20 · terra $2.00/$12.00 · sol $5.00/$30.00 (in/out per M); batch −50%; reasoning tokens bill as output; `max_output_tokens` documented inclusive.
OpenRouter: gpt-oss-120b $0.037/$0.170 (native `reasoning_effort`).

## Cost model

The following is a **conditional planning model, not an executable budget gate**.
Only after a route is empirically verified cap-inclusive may expected cell cost use

`items × n × (T_in·p_in + E[min(L, cap)]·p_out) / 10⁶`.

`E[min(L, cap)]` can never exceed `cap`; the earlier rough note of 4.1k at a
4k cap was invalid and must not enter runner code. Exact values must be recomputed
from frozen fitted parameters and checked against hand-calculated fixtures before
the dry-run model is accepted.

Until smoke evidence establishes cap and billing semantics for the exact route,
no billed call is authorized unless a model-specific maximum billable output or a
platform hard-spend control supplies a finite fail-closed upper bound. Requested
tokens alone are not a safe accounting bound: the exploratory route audit already
observed billing above a requested cap.

**Conditional planning estimates** (per 30-item dataset-equivalent, arms A+B+C =
~24,480 generations/model at 90 items; not runner gates):

| Panel | Est. cost |
|---|---|
| P1 Inkling (90 items, A+B+C) | ≈ $702 |
| P2 GPT-OSS-120B (same) | ≈ $125 |
| (optional third Tinker model, Qwen3.6-35B) | ≈ $200 |
| **Tinker total** | **≈ $1,030 = 21% of pool** |
| P3 terra, Arm A n=28 sync (or 56 batched) | ≈ $190 of $200 |
| P0 debugging allowance | ≤ $50 |

Reserve policy: Tinker committed ceiling **$2,000** for the first full pass (design fits ~2× inside it); remaining $3,000 held for (a) follow-up decided *after* analysis via dated amendment, (b) reruns forced by infrastructure failures, (c) dataset extensions. Nothing in reserve is spent without a written scope note.

## Gates (per Phase I discipline)

- Per-panel worst-case fit check before start; cumulative usage polled from the Tinker console / OpenAI usage API between blocks; hard kill at panel ceiling.
- Every call: explicit `max_tokens`, explicit effort, logged `stop_reason`/termination + token usage at collection time.
- Smoke block per platform (cheap model, 2 items) must reconcile usage-vs-billing before any panel.
- Truncation-rate sanity: if observed truncation at a cap deviates >15pp from the length-model prediction mid-run, pause and investigate before continuing (either the length model or the platform semantics is wrong — both matter).
