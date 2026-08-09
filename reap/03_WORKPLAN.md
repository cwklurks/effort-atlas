# REAP workplan — concrete next steps

**Planning snapshot from 2026-08-04.** Preserve the week-by-week items below as
history; use `CODEX_BRIEFING.md` and `10_PHASE_GATE_PLAN_2026-08-08.md` for current
implementation state and gate order.

Owners: **C** = Connor, **CN** = Chirag. Weeks from 2026-08-04. Chirag's high-availability month is now — front-load everything needing his judgment.

## Week 1 (now) — decisions and free work

- [ ] **C:** Send Chirag the grant message + the Coupling Tax alert (`05_RELATED_WORK_ALERT.md`). The repositioning conversation happens before any more math is written. *(Highest priority.)*
- [ ] **C:** Email tinker@thinkingmachines.ai: grant expiry? rate limits? acknowledgment requirements?
- [ ] **C:** Tinker access smoke test: create sampling client, 2 calls on GPT-OSS-20B with explicit max_tokens, verify `stop_reason` and token accounting appear as documented. (~$0.01)
- [ ] **C:** **MathArena free-data study ($0):** download hmmt_feb_2025/2026 + aime_2026 output parquets; fit per-effort length distributions; compute truncation rates and at-cap vs below-cap accuracy per model. This is the length prior for power analysis AND an independent public replication of the thesis — before spending a dollar.
- [ ] **CN:** react to `01_EXPERIMENT_OUTLINE_v2.md` (arm sizes, effort anchors, GPQA in/out, random-effects formulation).
- [ ] **CN:** Slack channel + weekly slot; send OpenAI key.

## Week 2 — instruments calibrated, protocol frozen

- [ ] **C:** Grader v2: strict `Final answer:` terminator rule, no fallbacks; unit tests incl. truncated-mid-box cases; strict-vs-flexible dual scoring for MCQ.
- [ ] **C:** Cap-semantics probes on Tinker (both models, at 4k/16k/32k/64k) and OpenAI Responses (documented-inclusive — verify empirically anyway). Receipts/usage reconciliation per platform.
- [ ] **C:** Pilot rerun with updated parameters on cheap models (GPT-OSS-20B on Tinker; P0 sanity on OpenRouter) — the "confirm setup before scaling" action item from the call.
- [ ] **C + CN:** Freeze **PREREG v2** (from `06_PREREG_V2_SKELETON.md`) + analysis code (bootstrap w/ replicate variance components, dose-response surfaces, calibration metric for cap-invariance). Commit with hashes.

## Weeks 3–4 — confirmatory core

- [ ] **C:** Run Arm A (replicated 2×2) on P1 + P2; usage reconciliation between blocks. Run P3 (OpenAI, batched).
- [ ] **CN:** Manuscript §§3–4 revisions with the Coupling Tax repositioning; Helpfulness extension per his chosen method.

## Weeks 5–6 — surfaces and validation

- [ ] **C:** Arms B + C on P1 + P2; cap-invariance predicted-vs-observed analysis.
- [ ] **CN:** bridge subsection ("scope of the formalism"); statistical review of the validation metric.

## Weeks 7–8 — extensions and analysis

- [ ] **C:** dataset extensions as scoped (GPQA-Diamond and/or HARP hardest); GSM8K negative-control block; full frozen analysis + figures.
- [ ] **C + CN:** results reading; decide what the data supports.

## Weeks 9–10 — writing

- [ ] Draft per agreed section ownership; venue call (ACL/NAACL/EMNLP cycle) locked by actual results timing; Meta review filed if required.

## Standing rules

Weekly 30-min call; notes within 24h; every paid block preceded by a written scope line in Slack; exploratory vs confirmatory labeled in every artifact; the reserve ($3,000) untouched without a dated scope note.
