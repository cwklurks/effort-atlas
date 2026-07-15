# Research log — effort-atlas

## Hypothesis

Inkling's thinking-effort dial buys accuracy at very different exchange rates per
task type. Specifically: reasoning-heavy tasks (competition math) improve
monotonically with effort, while retrieval/extraction tasks plateau at low effort —
meaning a fixed high-effort default wastes most of its tokens on most real queries.

## Hard invariants

- Token counts are provider-reported, never estimated, in any published figure
- Every published accuracy has n and a 95% Wilson interval
- Fixed question sets, fixed seed, full request config stored per row
- Prior art cited; claim is "first public per-domain effort curves for Inkling",
  not "invented adaptive test-time compute"

## Prior art (cite these, don't compete with them)

- s1: Simple test-time scaling / budget forcing — https://arxiv.org/abs/2501.19393
- L1: length-controlled reasoning via RL — https://arxiv.org/abs/2503.04697
- RouteLLM (routing between models; we route one model's native dial) —
  https://arxiv.org/abs/2406.18665
- TML's own effort/performance curves (Terminal Bench 2.1, HLE, IFBench only) —
  https://thinkingmachines.ai/news/introducing-inkling/

## Plan

- **Phase 1 (this week):** text-domain effort curves — math, knowledge, extraction.
  ~50 items × 3 domains × 5 effort levels ≈ 750 calls.
- **Phase 2:** audio (MMAU-style) + charts (CharXiv-style) — does effort help
  perception, or only inference-over-perception?
- **Phase 3:** effort autopilot — small classifier trained on Phase 1/2 rows
  predicts minimum sufficient effort per prompt. Target claim: iso-accuracy with
  the max-effort setting at a fraction of the tokens.

## Status

- 2026-07-15: Repo scaffolded. Pipeline verified end-to-end in mock mode.
- 2026-07-15: Confirmed against Tinker docs — OpenAI-compatible endpoint (beta),
  `reasoning_effort` accepts raw floats in [0,1] via extra_body, and
  `separate_reasoning` isolates CoT into `reasoning_content` (bonus: we can study
  CoT length/style vs effort directly). Harness updated.
  Remaining blockers: Inkling sampler checkpoint path + confirmed pricing.
  Deadline pressure: Tinker sample prices rise ~50% July 17 → sweep by July 16.
- 2026-07-15: Completed the 45-run free Playground pilot with exact efforts
  0.2/0.6/0.99, isolated chats, and web search disabled. Accuracy was 45/45 at
  every setting: easy math and extraction were saturated at effort 0.2, while
  rough UI latency increased at 0.99. This is a ceiling-effect result, not proof
  that effort is generally useless. The Playground raw view exposes no token
  usage, and its image/audio input controls are currently disabled (“coming
  soon”), so publishable token curves and multimodal tests still require API
  access.

## Next falsification test

Run genuinely difficult competition-math items through the API at multiple
effort values while collecting provider-reported token counts. The Playground
pilot established the easy-task ceiling; the next test must be hard enough for
accuracy to vary before an effort knee can be estimated.
