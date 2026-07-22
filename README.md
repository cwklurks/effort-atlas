# Thinking Cut Short

## Separating token starvation from genuine overthinking in reasoning models

Higher reasoning effort can appear to reduce accuracy when a model uses its output
allowance for reasoning and is stopped before producing an answer. This project
crosses native reasoning effort with output allowance on the same math items to
measure how much of a negative effort slope is associated with no-answer length
stops, and how much remains among completed responses.

## Study status

As of 2026-07-22:

- Earlier Tinker and OpenRouter measurements are exploratory only.
- The confirmatory hypotheses and design were frozen in
  [PREREGISTRATION.md](PREREGISTRATION.md) before any confirmatory response.
- A [pre-data scoring amendment](PREREGISTRATION_AMENDMENT_2026-07-22.md) fixes an
  audit-detected implementation error: finish reason cannot override the unchanged
  grader. No confirmatory response existed when it was corrected.
- The prompt-free execution order and provenance hashes are under
  [confirmatory_artifacts/](confirmatory_artifacts/).
- No confirmatory result has been collected and confirmatory-study spend is $0.00.
- The confirmatory validator is offline-only. It is not yet connected to a paid
  runner, so no command in the confirmatory artifact path can initiate model calls.

The intended submission is the EACL 2027 Industry Track. That is an intention, not
an acceptance or affiliation.

## Confirmatory question

For each pinned model/provider route, the same 30 audited AIME-25 items are evaluated
in a blocked 2x2 design:

| | Smaller output allowance | Larger output allowance |
|---|---:|---:|
| Lower native effort | same items and prompts | same items and prompts |
| Higher native effort | same items and prompts | same items and prompts |

The primary quantity is the change in the effort slope when allowance increases.
Conventional accuracy always follows the unchanged grader. Termination and answer
availability are reported separately:

- all `finish_reason="length"` responses;
- unanswered length stops, defined as a length stop with no extractable final answer;
- answer-present length stops; and
- normally completed correct and wrong responses.

A completed high-effort error is not automatically called overthinking. Stronger
mechanistic language requires additional evidence described in the protocol.

## Research artifacts

- [METHODS_BRIEF.md](METHODS_BRIEF.md): short design and estimand summary.
- [PREREGISTRATION.md](PREREGISTRATION.md): original frozen confirmatory protocol.
- [PREREGISTRATION_AMENDMENT_2026-07-22.md](PREREGISTRATION_AMENDMENT_2026-07-22.md):
  pre-data correction to length-stop scoring and bounds.
- [CONFIRMATORY_PREFLIGHT.md](CONFIRMATORY_PREFLIGHT.md): schedule, ledger, and
  validation contract.
- [CAP_SEMANTICS.md](CAP_SEMANTICS.md): exploratory audit of what provider routes
  actually bound with `max_tokens`-family parameters.
- [TRUNCATION_STUDY.md](TRUNCATION_STUDY.md): exploratory 4,096-token artifact and
  rerun record.
- [public_artifacts/](public_artifacts/): sanitized exploratory metadata and billing
  receipts. Prompts, gold labels, visible responses, and reasoning traces are omitted.
- [OUTREACH_RESEARCH.md](OUTREACH_RESEARCH.md): literature and reviewer-selection
  dossier. It is not evidence of endorsement.

Exploratory and confirmatory rows are never pooled. Earlier accuracy numbers that
treated hidden output caps as ordinary completed errors are explicitly invalidated in
the research log.

## Offline verification

Install the package and run the full offline suite:

```bash
python -m pip install -e .
PYTHONPATH=src python -m unittest discover -s tests -v
```

The confirmatory schedule exporter is also offline. It reads audited item IDs,
creates deterministic schedules, and hashes protocol, amendment, configuration,
dataset, and code inputs. See [CONFIRMATORY_PREFLIGHT.md](CONFIRMATORY_PREFLIGHT.md)
before regenerating anything.

## Legacy evaluation harness

The repository began as `effort-atlas`, a harness for measuring Inkling's continuous
Tinker `reasoning_effort` setting and later gained an isolated categorical-effort
OpenRouter path. These components remain for reproducing the exploratory history:

```text
src/effort_atlas/client.py       provider client, streaming, cache identity
src/effort_atlas/sweep.py        domains x efforts x items runner
src/effort_atlas/analyze.py      exploratory curves and summary tables
src/effort_atlas/confirmatory.py offline schedule, ledger, and validator
```

Provider configurations keep caches and result directories isolated. The raw local
datasets, caches, results, reports, and `.env` files are ignored by Git. Real model
calls require an explicitly configured provider key and are outside the offline
verification workflow above.

## Evidence and licensing

Provider-reported usage and receipt fields are retained where needed for accounting.
Missing observations remain missing; no row is fabricated, repaired, interpolated,
or silently retried. Public evidence exporters use explicit field allowlists.

The MIT license applies to project code. It does not claim ownership or a
redistribution license for benchmark content or model outputs. Dataset identifiers
and cryptographic hashes are published when source text cannot be redistributed.
