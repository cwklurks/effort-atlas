# capabilities/ — original-source prompt sets for the five HELM-Capabilities benchmarks

**Created:** 2026-08-23 · **Status:** exploratory acquisition artifact. No model was called,
paid or free. Nothing here is a preregistration or a run schedule.

This directory answers one question completely: **"where is this coming from?"**
Every row in every JSONL traces to a pinned public revision of the original benchmark,
with byte sizes and SHA-256 recorded in `sources_manifest.json`, and every row carries
its own recomputable hash.

## The five files

| File | Rows | Original source (pinned) | Grading target |
|---|---:|---|---|
| `mmlu_pro.jsonl` | 12,102 (12,032 test + 70 validation) | [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) @ `b189ec76…` | `gold_choice` (letter A–J + index, 10 options) |
| `gpqa_main.jsonl` | 448 (**sanitized** — see below) | [idavidrein/gpqa](https://github.com/idavidrein/gpqa) @ `d46dc8d5…` (`dataset.zip`, sha256 `461ae732…` — same pin as `observational/benchmark_sources_manifest.json`) | `gold_choice` (nulled in committed copy) |
| `ifeval.jsonl` | 541 | [google/IFEval](https://huggingface.co/datasets/google/IFEval) @ `966cd895…` | `verifiable_instructions` — **IFEval has no gold answer**; it is graded by code from `instruction_id_list` + `kwargs` |
| `wildbench_v2.jsonl` | 1,024 | [allenai/WildBench](https://huggingface.co/datasets/allenai/WildBench) config `v2` @ `26c49eb3…` | `judge_checklist` — **WildBench has no gold answer**; LLM-judge checklist. Rows are multi-turn: exact `conversation_input` is stored unserialized |
| `omni_math.jsonl` | 4,428 | [KbsdJames/Omni-MATH](https://huggingface.co/datasets/KbsdJames/Omni-MATH) @ `40ba231d…` | `gold_answer` (string). **9 rows have an empty gold** — listed in `validation_report.json`, kept and flagged, not hidden |

Full revision SHAs, per-file URLs (in immutable `/resolve/<sha>/` form), byte sizes, and
SHA-256 digests: `sources_manifest.json`. Where Hugging Face publishes an LFS sha256 for a
file, the download was verified against it.

Count notes: MMLU-Pro "~12,000" from the meeting = 12,032 test rows (the 70-row validation
split is included and labeled, since the instruction was "get ALL the prompts"). Omni-MATH's
card says 4,428 and the actual file has 4,428; the HF viewer's 4,430 is wrong.

## Row schema (`source-item-v1`)

One row per source item: `dataset, split, source_url, source_revision, source_row_index,
source_item_id, prompt_text (exact source text, verbatim), prompt_sha256, choices,
grading{kind,…}, license_policy, meta, full_row_sha256`.

- `prompt_text` is the **source item only** — no instructions, no `Final answer:` demand,
  no choice lettering. The model-facing wrapper is a later, separately versioned artifact.
  This keeps "the exact prompt to the last T" unambiguous.
- `grading.kind` is a tagged union because two of the five benchmarks have no gold answer
  (IFEval, WildBench). Pretending otherwise would have meant inventing fake golds.
- `full_row_sha256` = SHA-256 of the canonical row (sorted keys, no spaces) minus itself.
  The validator recomputes every one.

## GPQA: restricted content rules

GPQA's access conditions require not publishing question text online (the dataset even
embeds a canary string to detect leaks). Therefore:

- **`gpqa_main.jsonl` (committed):** `prompt_text`, `choices`, `gold` are all `null`.
  Only IDs, domains, and hashes remain.
- **`restricted_local/gpqa_main.RESTRICTED.jsonl` (gitignored, local only):** the full
  448 rows. Never commit, never paste into the Google Doc, never upload.
- The two files carry identical `full_row_sha256` values, so the committed skeleton
  provably corresponds to the withheld text. The validator confirms the committed file
  contains neither the canary string nor any content.
- On a fresh checkout the restricted file is absent; re-running `acquire.py` regenerates
  it from the pinned zip.
- GPQA `choices` are stored in source order `[correct, incorrect1..3]` with
  `gold_index: 0`; answer-option shuffling is a wrapper-time decision with a recorded seed.

## Reproduce and verify (this is the part to be able to say out loud)

```bash
pip install huggingface_hub pandas pyarrow
python3 capabilities/acquire.py      # re-downloads pinned revisions, verifies hashes, rebuilds JSONLs
python3 capabilities/validate.py     # recounts, recomputes every row hash, writes validation_report.json
```

Two independent `acquire.py` runs produce **byte-identical** JSONLs (verified 2026-08-23).
`validate.py` exits nonzero on any count, hash, grading, or GPQA-privacy failure.

Sixty-second narration for the next meeting: *"Each JSONL row is one original benchmark
item. The manifest pins the exact revision and hash of every downloaded file; the
acquire script refuses mismatched bytes; the validate script recomputes every row hash
and the published counts (12,032 / 448 / 541 / 1,024 / 4,428). GPQA text exists only in a
gitignored local file, hash-linked to the sanitized committed one. Run both scripts and
you get byte-identical results."*

## Finding that affects the pilot: "first 200" is one category

MMLU-Pro's test split is **category-grouped**: the first 200 rows are 100% `business`
(of 14 categories total — see `mmlu_pro_first200_categories` in
`validation_report.json`). A literal first-200 pilot would measure business-question
length, not MMLU-Pro length. Decision for Chirag: literal first-200 vs a seeded
stratified 200. Either is one line of code; the selection file will record rule, seed,
revision, and row indices.

## What is deliberately NOT here

- No model-facing wrapper, no rendered prompts (separate artifact, separate decision).
- No pilot selection file (waiting on the first-200 vs stratified decision).
- No API calls of any kind — acquisition and verification only.
