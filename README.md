# Thinking Cut Short

## Separating token starvation from genuine overthinking in reasoning models

Higher reasoning effort can appear to reduce accuracy when a model uses its output
allowance for reasoning and is stopped before producing an answer. This project
crosses native reasoning effort with output allowance on the same math items to
measure how much of a negative effort slope is associated with no-answer length
stops, and how much remains among completed responses.

## Study status

As of 2026-08-08:

- Earlier Tinker and OpenRouter measurements are exploratory only.
- The confirmatory hypotheses and design were frozen in
  [PREREGISTRATION.md](PREREGISTRATION.md) before any confirmatory response.
- A [pre-data scoring amendment](PREREGISTRATION_AMENDMENT_2026-07-22.md) fixes an
  audit-detected implementation error: finish reason cannot override the unchanged
  grader. No confirmatory response existed when it was corrected.
- The current prompt-free execution order and provenance hashes are in the
  [amended preflight artifact](confirmatory_artifacts/preflight-2026-07-22-amended/).
  The first frozen artifact remains available as superseded provenance.
- No confirmatory result has been collected and confirmatory-study spend is $0.00.
- The confirmatory validator is offline-only. It is not yet connected to a paid
  runner, so no command in the confirmatory artifact path can initiate model calls.
- The funded REAP Phase-II design is in implementation. Grader v2, probe tooling,
  and the pre-data analysis layer exist on separate branches but are not yet an
  accepted integrated baseline. The runner and executable budget gates do not yet
  exist. See [the Codex briefing](reap/CODEX_BRIEFING.md) and
  [dated phase-gate plan](reap/10_PHASE_GATE_PLAN_2026-08-08.md).

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

Use Python 3.12 (or another supported Python >=3.10), install the package, and run
the canonical offline suite:

```bash
uv sync --python 3.12.8
uv venv --no-project --python 3.12.8 .venv/tinker-probe
uv pip sync --python .venv/tinker-probe/bin/python \
  --require-hashes --strict scripts/tinker_probe_requirements.lock
./scripts/verify_offline.sh
```

The canonical verifier runs two mandatory, structurally separate lanes: ordinary
project tests in `.venv`, then the Tinker probe suite in the exact 42-distribution
SDK environment at `.venv/tinker-probe`. It fails if the second interpreter is
missing, is the project interpreter, or differs from the hash-locked manifest.
Set `TINKER_PYTHON` only to select another independently provisioned exact-lock
interpreter.

For the pinned observational pipeline, install its locked optional dependencies
with `uv sync --python 3.12.8 --extra observational`.

The current canonical verifier collects 273 ordinary project tests and 26 exact-lock
Tinker tests. The ordinary lane includes collected rescue-analysis tests enforcing
the amended answer-rescue definition and shared grader-v2 state validation. One
archive-backed grader test requires `GRADER_V2_ARCHIVE_ROOT`; the committed
sanitized 78-row acceptance fixture remains covered when that private source path
is unavailable. A green suite means reproducible current behavior, not complete
coverage.

The legacy local `.venv` found before the 2026-08-08 governance pass used Python
3.9 and is not valid verification evidence. No offline verification command should
require a provider credential or make a model call.

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
