# Observational run log

## 2026-08-07 — cycle 1 (initial, interactive)
Datasets: 4 MathArena parquets (pinned revisions in state_manifest.json) + 3 HELM GPQA CoT runs (v1.15.0).
Pipeline: initial commit. 166 model-series; 427 at-cap rows; 6 dose-response families; K2-Think excluded (zero token counts).
Verification: 7/7 independent spot-checks PASS (DeepSeek-1.5B at-cap 68 @ acc 0; Opus-4.7 xhigh exact-128k 6 @ all wrong; HELM Gemini finish=length 42 @ acc 0.0; o3-mini(high) median 13759.5).
DELTAS: first cycle — everything is new. Headlines in RESULTS.md.
FLAGS: (1) HELM = labeled-censoring anchor, recommend paper Figure 1. (2) o4-mini(high) p90 38,125 exceeds lm-eval's remediated 32,768 AIME cap. (3) K2-Think missing token accounting — a finding in itself (leaderboard rows with no usage data).
