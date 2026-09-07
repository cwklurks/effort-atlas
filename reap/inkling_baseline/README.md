# Inkling baseline: offline preparation

This prepares the agreed 1,000-item exploratory baseline. It does not collect
research responses and has no live execution path. The remaining Tinker billing
decision is concrete in `ACCOUNTING_PROPOSAL.md`.

## Prepared design

- Existing stratified selection, seed 20260830: exactly 200 questions from each
  of MMLU-Pro, GPQA Main, IFEval, WildBench v2 and Omni-MATH.
- Tinker Anthropic-compatible endpoint, model `thinkingmachines/Inkling`.
- Medium effort first, explicit output cap 32,768. Maximum effort uses identical
  questions, prompts and cap; only its effort field changes. A maximum stage is
  conditional on a complete, valid medium stage showing no reported cap stops.
- Current named medium is not asserted equivalent to the historical numeric
  effort 0.6. The current endpoint and model are not an exact historical replay.
- No tools, no client retries, no redirects. Backend billing behavior remains
  unverified even though the SDK sends once in the offline transport tests.

## Prompt provenance and exact adaptations

HELM source revision `bfa36d33e8b98b36b5f3a8c7d52b9a1b7162eae5` supplies its
actual run-spec functions and prompt constructors. Imports and source hashes must
pass; there is no replacement renderer when upstream cannot be imported.

The wrapper uses zero-shot benchmark templates. MMLU-Pro and GPQA retain HELM's
reasoning instruction and choice formatting, replacing its answer-format
instruction with `Final answer: <letter>`. GPQA reuses the existing recorded,
seeded option permutation. Omni-MATH retains the instruction to give reasoning,
replacing the boxed-answer instruction with `Final answer: <answer>`.

IFEval receives its source prompt verbatim; the adapter-added trailing newline
is suppressed. WildBench retains the original chat turns. HELM's automatic input
truncation is disabled for all templates. Requests above 60,000 serialized message
bytes are rejected; this is an admission rule, not proof of a token-count bound.
Context and input-token admission still need route-specific evidence.

The upstream temperatures are retained: 1.0 for MMLU-Pro/GPQA and 0.0 for the
other three datasets. These remain identical across effort stages. All requests
override upstream output defaults with exactly one output and a 32,768-token cap.
The old custom instruction "Think as much as you need" is not added.

These are adapted HELM templates, not a claim to reproduce published HELM scores.

## Scoring and accounting fields

MMLU-Pro/GPQA import the accepted strict terminator extractor and compare one
case-insensitive answer letter with the recorded gold option. Ambiguous final
fields such as `A or B` are present but invalid, never credited by taking the
first letter. The existing accepted grader module is unchanged.

IFEval imports Google's original strict evaluator at revision
`c7f60c013623e613732a096e2a0c2872491ec912`. It records prompt-level correctness
and every instruction result. Checker exceptions become `grader_error`, not a
wrong answer. Its language detector and checker randomness are seeded.

Omni-MATH records strict-answer presence and stays `pending_official_judge`;
its published evaluator requires additional paid model calls. WildBench quality
judging is deferred. No five-dataset pooled accuracy is produced.

Response parsing keeps thinking separate from answer text, preserving native
stop reason and reported usage. Missing reasoning-token counts stay unknown.
`max_tokens` is recorded as a reported cap stop; it is not empirical proof of
reasoning-inclusive cap semantics. Reported usage is explicitly unreconciled and
billed cost stays null. No dollar receipt is manufactured from token counts.

## Reproduce the offline checks

The main locked environment remains unchanged. The supplemental environment is
limited to the pinned HELM modules, Google evaluator and client transport tested
here; it is not a full installation of HELM's unused GPU/provider plugins.

From the repository root:

```sh
uv sync --python 3.12.8
uv venv --python 3.12.8 .cache/inkling-baseline-env
uv pip sync --python .cache/inkling-baseline-env/bin/python reap/inkling_baseline/requirements.lock
PYTHONPATH=src .venv/bin/python scripts/acquire_benchmark_sources.py \
  --manifest reap/inkling_baseline/upstream_sources.json \
  --root .cache_pilot/inkling_baseline_upstream --download
./scripts/verify_inkling_baseline.sh
```

Dependency/source acquisition contacts public package and source hosts only.
The verification script then denies Python socket access, runs the canonical
suite, runs the actual upstream/SDK tests, and rehearses all 1,000 rows with
synthetic responses. An available private archive can be verified by setting
`GRADER_V2_ARCHIVE_ROOT` to its existing local root.

The box checkout is `/home/connork/code/inkling-baseline-20260906`. Its benchmark
files are private copies of already-present files on the same box; no restricted
question text was transferred from the Mac. Symlinks outside the checkout are
rejected by the existing source-integrity check.

Preparation artifacts are written under
`results_pilot/inkling_tinker_baseline/preparation/<plan_sha256>/`. The public
manifest contains hashes and identifiers. The request and mock-response JSONLs
are private, mode 0600, inside a mode-0700 directory and remain gitignored. Existing
artifacts with different bytes are never overwritten. Do not put the private
JSONLs in a transfer bundle or PR.

## Source references

- [Pinned HELM template definitions](https://github.com/stanford-crfm/helm/blob/bfa36d33e8b98b36b5f3a8c7d52b9a1b7162eae5/src/helm/benchmark/run_specs/capabilities_run_specs.py)
- [Original Google IFEval evaluator](https://github.com/google-research/google-research/blob/c7f60c013623e613732a096e2a0c2872491ec912/instruction_following_eval/evaluation_main.py)
- [Tinker compatible endpoint and effort controls](https://tinker-docs.thinkingmachines.ai/tinker/compatible-apis/anthropic/)
- [Tinker billing export contract](https://tinker-docs.thinkingmachines.ai/tinker/cli/billing/)
