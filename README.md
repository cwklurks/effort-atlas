# effort-atlas

**How much is thinking actually worth?** Per-domain effort/performance curves for
[Inkling](https://thinkingmachines.ai/news/introducing-inkling/), the first open-weights
model with a continuous thinking-effort dial — plus (Phase 2) a learned controller that
sets the dial automatically per query.

## The question

Inkling exposes a thinking-effort setting (0.2 → 0.99). Thinking Machines published
effort/performance curves for exactly three benchmarks. Nobody knows:

1. Where the knee of the curve is per *task type* (math vs extraction vs knowledge vs code)
2. Whether effort helps *perception* tasks (audio, charts) at all — Phase 2
3. Whether the minimum sufficient effort per query is *predictable* — Phase 3

## Pipeline

```
generate data  →  dry-run (cost estimate)  →  sweep  →  analyze
```

```bash
python -m pip install -e .
# Optional Hugging Face dataset fetcher:
# python -m pip install -e ".[data]"

# 1. Build the local question sets (synthetic extraction is fully offline;
#    math/knowledge fetch small fixed subsets from Hugging Face)
python -m effort_atlas.data_gen
python -m effort_atlas.fetch_data          # optional, needs `datasets`

# 2. See what the sweep will cost BEFORE spending anything
python -m effort_atlas.sweep --dry-run

# 3. Test the entire pipeline with zero API calls
python -m effort_atlas.sweep --mock
python -m effort_atlas.analyze

# 4. The real thing (needs TINKER_API_KEY in .env)
python -m effort_atlas.sweep
python -m effort_atlas.analyze
```

Everything is configured in `config.yaml`: endpoint, model path, effort levels,
items per domain, and pricing for the estimator.

## Running against Tinker (verified 2026-07-15)

The harness targets Tinker's [OpenAI-compatible endpoint](https://tinker-docs.thinkingmachines.ai/tinker/compatible-apis/openai/) (beta):

- **Base URL** (already the default): `https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1`
- **Auth**: your `TINKER_API_KEY`, in `.env`
- **Effort**: `reasoning_effort` as a raw float in [0.0, 1.0] via `extra_body` —
  confirmed in the docs. Strings map to floats: minimal=0.01, low=0.3, medium=0.6, high=0.9.
- **Reasoning separation**: `separate_reasoning: true` puts chain-of-thought in
  `reasoning_content`; we grade only the final `content` and log the trace length.

## ⚠ Remaining day-1 TODO

- [ ] **Get an Inkling sampler checkpoint path** (`tinker://…/sampler_weights/…`)
      and set it as `provider.model` in `config.yaml`. The OAI endpoint takes
      sampler paths, not plain model names — grab one from the Tinker console or
      create one via the SDK quickstart against the Inkling base model.
- [ ] Confirm Inkling's **sample/prefill price** in the Tinker console and update
      `pricing:`. **Prices rise ~50% on July 17, 2026 — run the sweep before then.**
- [ ] Verify the HF dataset ids in `fetch_data.py` still resolve; swap subsets if needed.
- [ ] The endpoint is beta/low-throughput: keep `concurrency` at 2 and expect
      variable latency.

## Honest-claims policy

- Accuracy is reported with 95% Wilson intervals; n per point is always shown.
- Token counts are **provider-reported completion tokens**, not estimates.
- Every result JSONL row stores the full request config for reproduction.
- We claim "first public effort curves for Inkling across domains" — NOT
  "we invented adaptive test-time compute" (see prior art in RESEARCH_LOG.md).

## Layout

```
config.yaml                 all knobs
src/effort_atlas/
  client.py                 OpenAI-compatible client, effort injection, disk cache, retries
  data_gen.py               synthetic extraction tasks (offline, deterministic)
  fetch_data.py             small fixed HF subsets → data/*.jsonl
  graders.py                numeric / multiple-choice / exact-field graders
  sweep.py                  runner: domains × efforts × items → results/*.jsonl
  analyze.py                curves, summary table, knee detection → reports/
data/                       question sets (JSONL, standard schema)
results/                    raw sweep output (one JSONL per run)
reports/                    charts + summary
```
