# REAP 28: Multi-model phase-2 candidates (GLM-5.3-Flash, Qwen3.8-27B)

Date: 2026-08-29
Status: PROPOSED. Requires written sign-off at the 2026-08-30 meeting before
either config is enabled. This entry authorizes no spend. The Inkling pilot
(reap/26, reap/27) is unchanged and runs first.

## Summary

Two open-weight releases from the last two weeks are added as phase-2 pilot
candidates, each as a self-contained config sharing the Inkling pilot's
selection, wrapper, 32k cap, gates, and ledger discipline:

1. config_pilot_glm53flash.yaml: z-ai/glm-5.3-flash (revealed 2026-08-27 as
   the anonymous "Ox Alpha"; 320B-A18B, open weights, 16 OpenRouter hosts).
   Listing $0.075/$0.25 per Mtok. Reasoning always on, ladder low/high/max,
   therefore no zero-effort baseline.
2. config_pilot_qwen38_27b.yaml: qwen/qwen3.8-27b (weights 2026-08-14,
   Apache-2, dense 27B, 11 hosts, first party Alibaba Cloud). Listing
   $0.35/$2.75 per Mtok. Ladder low/medium/xhigh, xhigh is the model default
   and is publicly documented as a severe overthinker (Willison 2026-08-16:
   22,276 reasoning tokens for 3,223 output tokens; hit its own context
   limit on mundane tasks). This is the closest known public instance of the
   phenomenon this project measures.

## What changed in the repo

Configs only, plus tests. No harness code changed:

- the runner already iterates effort.levels from config, the client already
  implements effort.mode openrouter_reasoning generically, and the wrapper
  renders identical prompts regardless of model, so pilot-wrapper-v1 stands.
- tests/test_pilot.py gains MultiModelConfigTests: every shipped config must
  refuse live with gates closed, share the 32k cap and pin discipline, keep
  ordinal and expected_output_tokens aligned with its ladder, keep max_price
  equal to the budgeted prices, and agree on the selection file; plus a
  ladder-iteration test (n items x k levels, ledger records each rung) and a
  mock ordinal-scaling test.

## Budget (config prices, UNVERIFIED against the pinned hosts; 3,000 calls
each = 1,000 items x 3 levels at the 32k cap)

| model            | expected | worst case | per-dataset ceiling | total ceiling |
|------------------|----------|------------|---------------------|---------------|
| glm-5.3-flash    | ~$4.87   | ~$24.12    | $6.00               | $30.00        |
| qwen3.8-27b      | ~$80.33  | ~$264.58   | $55.00              | $270.00       |

The Qwen worst case is roughly twice the Inkling pilot's scale. Trim options
for the meeting: drop the medium rung (2,000 calls, worst ~$177), run fewer
datasets first, or approve as budgeted. Note the Qwen xhigh rung is expected
to sit near worst case by design; that is the measurement, not a bug.

## Gated probe (2-3 calls per model, needs the same written approval as live)

1. reasoning.effort accepted and echoed for each native level
2. reasoning tokens reported separately in usage
3. finish_reason marks truncation at the output cap
4. provider pin honored, no silent fallback (verify together actually hosts
   glm-5.3-flash; verify the exact alibaba provider slug)
5. Qwen only: does a hosted thinking-off mode exist? If yes it becomes rung 0
6. Qwen only: note any hosted-vs-local variant differences (1M vs 262k ctx)

A model failing 1, 2, or 3 is dropped regardless of price.

## Zero-spend track (optional, separate from these configs)

Qwen3.8-27B runs on consumer hardware (17GB quantized). A local run on the
Linux box would need a separate runner emitting the same ledger schema, with
backend and quantization recorded, since a quantized local build is not the
hosted model. Not designed here; candidate for its own REAP entry if pursued.

## Decisions required 2026-08-30

(a) add each model or not; (b) full native ladders vs trimmed; (c) probe
approval and budget; (d) per-model ceilings; (e) interaction with existing
decisions 2 (selection rule, all configs flip together), 3 (WildBench), and
4 (Inkling second effort level).
