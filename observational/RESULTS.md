# Observational study — cycle 1 results (EXPLORATORY)

**Run date:** 2026-08-07 · **Pipeline:** `pipeline.py` (all statistics computed by code; verified by 7 independent spot-checks, all passing — see RUN_LOG.md) · **Status:** exploratory found-data analysis; never pooled with confirmatory estimates.

## Data (pinned)

MathArena output parquets (HF, CC BY-NC-SA 4.0): `hmmt_feb_2025_outputs` @ bac3e9b, `hmmt_feb_2026_outputs` @ 1e88813, `aime_2026_outputs` @ 76ce7a0, `brumo_2025_outputs` @ 12ca8f1 — 166 model-series with usable token accounting (K2-Think excluded: token counts all zero). HELM `capabilities` v1.15.0 GPQA chain-of-thought runs (public GCS): Gemini-3-Pro (finish reasons labeled), Claude-Haiku-4.5, GPT-5.1.

## Headline 1 — truncation zeroes scores, everywhere we can measure it

Across the four MathArena competitions, **427 generations sit at a token cap**. In 16 of the 17 affected model×dataset series with ≥4 capped rows, **accuracy at the cap is exactly 0%**, while the same model's below-cap accuracy runs as high as 99%:

| Model · dataset | below cap | at cap | n@cap |
|---|---|---|---|
| Claude-Opus-4.7 (xhigh) · aime_2026 | 99.1% | 0% | 4 (all at exactly 128,000) |
| Claude-Opus-4.7 (xhigh) · hmmt_feb_2026 | 98.4% | 0% | 6 |
| **Gemini-3-Pro · HELM GPQA (labeled `finish_reason="length"`)** | **88.6%** | **0%** | **42 of 446** |
| o4-mini (high) · hmmt_feb_2025 | 87.7% | 0% | 6 (cap 64,000) |
| Qwen3-30B-A3B · brumo_2025 | 81.6% | 0% | 6 |
| Phi-4-reasoning-plus · hmmt_feb_2025 | 67.1% | 2.6% | 38 (32% of all rows) |
| DeepSeek-R1-Distill-1.5B · hmmt_feb_2025 | 26.9% | 0% | 68 (57% of all rows) |

The HELM row is the cleanest evidence in the study: explicit provider-reported censoring labels, and an **8.4-point deficit in a published leaderboard score** (0.802 reported ≈ 0.886 × 404/446) attributable purely to the cap.

## Headline 2 — effort is a length dial (the mechanism's first half)

Six model families expose graded effort in public data. Median generation length rises monotonically with effort in **all six**; the low→high multiple ranges from ~1.8× (Grok 3 Mini, brumo) to **5.7×** (o3-mini, hmmt: 2,426 → 13,760 median; p90 35,802). o4-mini (high) reaches p90 = 38,125 — above lm-eval's remediated 32,768 AIME cap. Note: at MathArena's generous caps, accuracy *rises* with effort in these families — the decline story only appears where walls bind, which is precisely the paper's claim.

## What this feeds

1. **Paper (observational arm):** Figure-1 candidate (`fig1_at_cap_vs_below.png`) — real-world prevalence, someone else's infrastructure, censoring labels included.
2. **REAP design:** length priors per effort level → Arm B cap placement (the interesting transition for high-effort frontier models sits ~8k–48k) and power analysis inputs (lognormal fits in `results_matharena.parquet`).
3. **Recurring cycle:** `state_manifest.json` initialized; next cycle diffs against it.

## Caveats (stated, not buried)

Cap detection on MathArena is inferential (≥99.5% of per-model max + round-value check) — no finish reasons published; HELM Gemini is the labeled anchor. At-cap accuracy 0% partly reflects graders scoring absent answers wrong — which is the paper's point, not a bug, but it means "at-cap accuracy" measures the *operational* penalty, not model ability. Effort labels come from MathArena's model naming; their exact request parameters are not published. All results scoped to these datasets, revisions, and dates.
