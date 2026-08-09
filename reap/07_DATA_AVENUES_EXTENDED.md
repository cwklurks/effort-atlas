# Extended data avenues — public raw-output archives + non-math domains

**Date: 2026-08. All ★ items verified by actually downloading and computing, not by reading docs.**

## Headline finding — a free observational arm for the paper

**★ HELM's public GCS bucket already contains our thesis, measured, with labels.** Stanford's HELM publishes complete per-request/per-response run data (no auth; ~1MB per run fetch): request `max_tokens` + full sampling settings, per-instance `num_output_tokens`, correctness, and — on Gemini runs — explicit `finish_reason`. Verified example (capabilities v1.15.0, GPQA CoT, Gemini-3-Pro, max_tokens=14,096): **42 of 446 instances hit `finish_reason="length"`; those 42 score 0.000 vs 0.886 for the rest — an 8.4-point published-score deficit caused purely by the output cap.** That is a paper figure from someone else's infrastructure, at $0.

This creates a new component for the paper: an **observational arm** (found data: HELM + MathArena + leaderboard archives) complementing the experimental arms — directly strengthening the "this happens in the real world" claim Chirag asked for.

## Ranked archive list

1. **HELM GCS bucket** (`crfm-helm-public`, per-run JSON, HTTPS, no auth) — full request settings + lengths + correctness + (Gemini) finish reasons. Caveats: stop-reason field empty on OpenAI/Anthropic runs (use `num_output_tokens` + retokenize); some newer runs encrypted — check per release. **Adopt.**
2. **★ MathArena output datasets (37 repos, CC BY-NC-SA)** — schema includes `output_tokens`, `correct`, effort levels in `model_name` (e.g. "GPT-5.5 (xhigh)"). No finish_reason, but exact-cap clustering works: verified Claude-Opus-4.7(xhigh) rows at exactly 128,000 tokens, all unparsed and wrong (98.4% accuracy excluding them vs 93.9% reported); `brumo_2025_outputs` holds **137 capped rows** with open models clustered at exactly 32,000. **Recast MathArena's role:** its caps are mostly generous → use it as the *near-uncensored reference length distribution* for survival-curve fitting, with the 128k/32k clusters as labelled-censoring validation pockets. Dose-response already visible: accuracy by output-token quartile 97.8/97.6/87.9/63.7%.
3. **Epoch AI Inspect logs** — ideal schema (`stop_reason` incl. "max_tokens", `reasoning_tokens`) but behind AWS WAF bot protection; manual browser fetches only. Small-N supplement.
4. **OpenCompass `compass_academic_predictions`** (26GB, HF, gated, schema unverified) — one exploratory access request; not a dependency.
5. lm-eval `--log_samples` — a tool, not an archive: use it to make our own runs HELM-comparable.
6. Open LLM Leaderboard details / vendor repos / LMArena dumps / Kaggle mirrors — low value (short generations, no lengths/labels, or aggregate-only).
7. Paper artifacts: Coupling Tax, Kaiser, Oladri — none verifiably release generations; email authors. **Read Kaiser et al. (2602.09805) in full before finalizing contribution claims** (completion-rate × correctness-given-completion × length decomposition, 14 models — closest framing after Coupling Tax).

## Non-math domain candidates (generality arms)

**Top-2 recommended:**

- **LiveCodeBench** (hard tier, date-windowed to ≤150 items): execution-based ground truth in the highest-value real domain; contest dates = contamination control for free. License ambiguous ("cc" — resolve before publishing).
- **ZebraLogic** (stratified 2×2 → 6×6 grids, 40/size, ~200 items): a **deterministic difficulty dial** — grid size scales required reasoning length while holding domain/format/verifier constant. The cleanest instrument an effort × cap factorial can ask for. License undeclared — resolve; fallback below.

Backups: **BigCodeBench** (1,140 tasks, Apache-2.0 — cleanest license; shorter reasoning), OlympicArena (science calculation; filter multimodal), Natural Plan (constraint-count dial; failure modes may not be length-driven), SciBench (weakest).

## Actions this creates

1. Add the **HELM observational study** to the Week-1 free-work list alongside MathArena (same skills, same $0).
2. Email Coupling Tax + Kaiser + Oladri authors asking whether generations are released.
3. Resolve ZebraLogic + LiveCodeBench licenses before they enter the prereg.
4. Update `01_EXPERIMENT_OUTLINE_v2.md` and the prereg skeleton with the observational arm and (if adopted) the generality datasets — as a dated revision, since Chirag has the current version.
