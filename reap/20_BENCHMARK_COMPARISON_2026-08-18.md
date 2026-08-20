# Benchmark comparison for the post-meeting decision

**Date:** 2026-08-18
**Status:** Exploratory planning record. No benchmark in this document is part of
a frozen REAP schedule, and this document authorizes no provider call.

## Meeting summary

The current archives provide **123 competition-math questions** across four
MathArena datasets and **446 evaluated GPQA science questions** in each of three
HELM model runs. Those counts must not be added and called one statistical sample:
they cover different domains, models, prompts, and measurement systems.

- **MathArena** is the better source for question-level descriptive comparisons:
  it publishes prompts, responses, grades, attempts, and output-token counts. It
  does not publish requested caps or finish reasons, so truncation is inferred.
- **HELM Gemini** is the clean observed termination example: 42 of 446 responses
  have `finish_reason="length"`, and all 42 were scored wrong. Its archived token
  summary is not useful for model-to-model efficiency.
- **HELM Claude and GPT** provide per-question accuracy on exactly the same 446
  instance IDs, but their blank finish reasons mean censoring is unknown, and
  their token fields are not comparable to Gemini or each other.
- **The controlled experiment** is still required for the primary
  matched-performance token question.

## Plain-language definitions

- A **question** is one benchmark item, identified by `problem_idx` in MathArena
  or `instance_id` in HELM.
- A **prompt** is the exact messages and wrapper used to ask that question.
- A **response row** is one model attempt on one prompt.
- **Per-question accuracy** means averaging a model’s attempts within a question,
  then giving every question equal weight.
- `observed` censoring comes from an explicit provider or archive termination
  label. `inferred` censoring comes from a length pattern such as repeated
  round-number maxima. `unknown` means neither is available.

## Meeting-ready comparison table

| Source | Domain and evaluated items | Per-question correctness | Output amount | Requested cap and finish reason | Censoring status | What it can support |
|---|---|---|---|---|---|---|
| MathArena HMMT Feb 2025 | Competition math, 30 questions | Yes, with attempts | `output_tokens` | Neither published | **Inferred** only for predeclared near-round-maximum rows; **unknown** otherwise | Paired descriptive accuracy and length at archived operating points |
| MathArena HMMT Feb 2026 | Competition math, 33 questions | Yes, with attempts | `output_tokens` | Neither published | **Inferred** only for predeclared near-round-maximum rows; **unknown** otherwise | Same, with unresolved provenance for questions 31–33 recorded explicitly |
| MathArena AIME 2026 | Competition math, 30 questions | Yes, with attempts | `output_tokens` | Neither published | **Inferred** only for predeclared near-round-maximum rows; **unknown** otherwise | Paired descriptive accuracy and length |
| MathArena BRUMO 2025 | Competition math, 30 questions | Yes, with attempts | `output_tokens` | Neither published | **Inferred** only for predeclared near-round-maximum rows; **unknown** otherwise | Paired descriptive accuracy and length; cite the pinned source because its card has a naming defect |
| HELM Gemini 3 Pro, GPQA CoT | Graduate-level science, 446 evaluated questions | Yes | Published field is zero-valued and unusable for efficiency | Requested cap 14,096; 42 `length`, 404 `stop` | **Observed** | A real operational length-stop example and question-level accuracy |
| HELM Claude Haiku 4.5, GPQA CoT | Same 446 IDs | Yes | Provider-specific archive field | Requested cap 14,096; all finish labels blank | **Unknown** | Question-level accuracy only |
| HELM GPT-5.1, GPQA CoT | Same 446 IDs | Yes | Provider-specific archive field | Requested cap 14,096; all finish labels blank | **Unknown** | Question-level accuracy only |

## Pinned source ledger

| Dataset | Revision or release | Source rows / usable summary rows | Pinned source |
|---|---|---:|---|
| HMMT Feb 2025 outputs | `bac3e9b78124aa8811c4aae3d590f03b467643f4` | 7,680 / 7,560 | [Hugging Face card at revision](https://huggingface.co/datasets/MathArena/hmmt_feb_2025_outputs/blob/bac3e9b78124aa8811c4aae3d590f03b467643f4/README.md) |
| HMMT Feb 2026 outputs | `1e888131281fc0fca080fd220e8bc6d830937564` | 3,651 / 3,651 | [Hugging Face card at revision](https://huggingface.co/datasets/MathArena/hmmt_feb_2026_outputs/blob/1e888131281fc0fca080fd220e8bc6d830937564/README.md) |
| AIME 2026 outputs | `76ce7a0aa77f0710f3cfb818ff1193e6dea56210` | 3,396 / 3,396 | [Hugging Face card at revision](https://huggingface.co/datasets/MathArena/aime_2026_outputs/blob/76ce7a0aa77f0710f3cfb818ff1193e6dea56210/README.md) |
| BRUMO 2025 outputs | `12ca8f115d73526d25a36b72e4bfefb18b76d6be` | 5,280 / 5,160 | [Hugging Face card at revision](https://huggingface.co/datasets/MathArena/brumo_2025_outputs/blob/12ca8f115d73526d25a36b72e4bfefb18b76d6be/README.md) |
| HELM GPQA CoT | Capabilities v1.15.0 | 446 evaluated rows per archived model | [Release manifest](https://storage.googleapis.com/crfm-helm-public/capabilities/benchmark_output/releases/v1.15.0/runs_to_run_suites.json) |

“Usable summary rows” are the rows represented by the checked-in summary Parquet
after the protected pipeline’s documented token-accounting exclusions. They are
not a claim that the excluded source rows never existed.

The HELM GCS object generations independently observed during this audit were:

- Gemini scenario state: `1781127720792970`
- Claude scenario state: `1781127720763514`
- OpenAI scenario state: `1781127721180954`

## What the row schemas actually provide

### MathArena

The pinned archives expose `problem_idx`, prompt/message fields, attempt identity,
full response text, parsed answer, gold answer, `correct`, and `output_tokens`.
They do not expose the provider-requested output allowance or finish reason.
Published correctness is useful as an archived operational outcome, but it is not
the same as applying REAP’s strict final-answer-marker grader after the fact.

Question-level model comparisons are possible only after reacquiring the pinned
raw Parquets and computing the exact shared `problem_idx` intersection. The
repository currently stores model-level summary Parquets, not the raw response
rows or a byte-verifying acquisition manifest.

HMMT Feb 2026 contains 33 questions. The first 30 align with the three documented
10-question individual rounds; the provenance of rows 31–33 is still unresolved.
Chirag’s willingness to include them is a scope decision, not provenance evidence.

The BRUMO revision’s card has an upstream metadata contradiction: its
`pretty_name` refers to AIME 2025 while its source and summary identify BRUMO 2025.
Always cite the exact revision and record the contradiction.

### HELM

The three archived runs have exactly the same 446 `instance_id` values; pairwise
set differences are zero. GPQA has 448 source instances, so the reason two are
absent from the archived slice must be documented before making population-wide
claims.

The archive provides per-item correctness and request configuration. The stored
predicted text in this slice is an encrypted placeholder, so strict answer presence
cannot be re-audited from it. Only Gemini has usable termination labels. Token
fields reflect provider-specific visible/hidden reasoning behavior and cannot be
treated as one common resource measure.

## Reconciliation of the 15-of-17 headline

The current checked-in summary Parquets reproduce:

- **MathArena:** 16 model-by-dataset groups have `round_cap=true` and
  `n_at_cap>=4`, where `n_at_cap` counts rows at least 99.5% of that group’s
  observed maximum; 14 have zero at-cap accuracy.
- **HELM Gemini:** one observed length-stop group; it has zero length-stop accuracy.
- **Combined:** **15 of 17** selected exploratory groups have zero at-cap or
  length-stop accuracy.

The two nonzero MathArena exceptions are:

| Group | Correct / inferred cap rows | Accuracy |
|---|---:|---:|
| Phi-4-reasoning-plus, HMMT 2025 | 1 / 38 | 2.63% |
| s1.1-32B, HMMT 2025 | 1 / 9 | 11.11% |

`observational/RESULTS.md` in this checkout says 16 of 17. That historical line is
inconsistent with the current summary artifacts. A correction exists on commit
`7204667` in `codex/observational-headline-correction`, but it is not an ancestor
of this checkout. Until that correction is integrated, use this meeting-safe
wording:

> In the current exploratory comparison, 15 of 17 selected groups had zero
> accuracy among inferred cap rows or observed length stops; MathArena’s cap labels
> are inferred, while HELM Gemini’s are observed.

Do not modify `observational/pipeline.py` to reconcile prose. Its statistical logic
is protected.

## Can we say a model was wrong because it hit the cap?

No. Keep these claims separate:

1. **Observed length stop and wrong:** the response was explicitly marked as cut
   off and the archive scored it wrong. This is available for 42 Gemini/HELM rows.
2. **Inferred at-cap and wrong:** the response ended near a repeated round-number
   maximum and was scored wrong. This is the strongest MathArena claim.
3. **Wrong because of the cap:** a causal statement requiring designed cap
   interventions and separately observed larger-cap outcomes.

The first two motivate the experiment. The randomized cap intervention estimates
the average effect of allowance on accuracy and answer presence; it cannot
determine whether a particular truncated trace would have become correct.

## Immediate no-cost acquisition deliverable

Before selecting model pairs from found data:

1. Download the exact pinned MathArena revisions and HELM v1.15 run objects.
2. Record source URL, revision or generation, byte size, and SHA-256 for every
   input.
3. Verify shared question IDs and prompt/config differences for each model pair.
4. Emit response rows with observed, inferred, or unknown cap status kept distinct.
5. Produce per-question accuracy, output summaries, missingness, and model-pair
   coverage.
6. Keep source-native grades separate from any later REAP strict-marker grade.

This requires no model-provider call.
