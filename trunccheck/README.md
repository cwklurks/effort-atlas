# trunccheck

`trunccheck` is a small, dependency-free diagnostic for post-generation answer
extractors. Maintainers can run it in CI against their real extraction function
to detect when explicitly labeled truncated responses are converted into
apparently valid answers.

`trunccheck` **does not detect truncation from response text**. A fixture's
metadata supplies the truncation label. The tool runs no model, makes no network
request, and does not decide whether arbitrary text "looks truncated."

## Install

From this repository:

```bash
python -m pip install ./trunccheck
```

For development without installation:

```bash
PYTHONPATH=trunccheck/src python -m unittest discover -s trunccheck/tests -v
```

Python 3.10 or newer is required. Runtime dependencies are standard-library
only.

## Python API

An extractor receives one response string. The optional scorer is the real
pipeline's downstream scorer and receives `(extracted_answer, gold_answer)`.
Without a scorer, correctness and control-pass metrics are `not_measured`; the
tool does not substitute string equality.

```python
from trunccheck import Fixture, run_check, results_to_csv, report_to_markdown

# Local dummy functions only: no model or network calls.
def extract_final(text):
    marker = "Final answer:"
    return text.split(marker, 1)[1].strip() if marker in text else None

def exact_dummy_score(extracted, gold):
    return extracted == gold

fixtures = [
    Fixture(
        fixture_id="cut-001",
        kind="truncated",
        stratum="real_truncated",
        text="work stops before an answer",
        gold_answer="7",
        truncated=True,
    ),
    Fixture(
        fixture_id="control-001",
        kind="control_correct",
        stratum="finished_control",
        text="Final answer: 7",
        gold_answer="7",
        truncated=False,
    ),
]

report = run_check(extract_final, fixtures, scorer=exact_dummy_score, pipeline="demo")
print(report_to_markdown(report))
print(results_to_csv(report))
```

For a committed adapter ledger, `summarize_results(...)` accepts validated `Result` records and applies the identical metric/control-disqualification contract without rerunning the external callable. The ecosystem audit uses this API as an independent metric check.

The report includes:

- `answer_returned_after_truncation_pct`, with `fabrication_pct` as an explicitly
  operational alias;
- `crash_pct` for exceptions escaping the extractor;
- `swallowed_error_pct` only when an observable hook is supplied;
- `accidental_correct_pct` only when a scorer is supplied;
- `control_pass_pct` when a scorer is supplied and
  `control_answer_returned_pct` in all runs;
- separate real and synthetic truncated strata when present.

A failed applicable control sets report status to `control_disqualified`. The
per-fixture results remain available for auditability.

### Escaped and swallowed errors

The two signals are deliberately separate. An ordinary exception from the
extractor is recorded and can be observed with `escaped_exception_hook`:

```python
def record_escape(fixture, exception):
    print(fixture.fixture_id, type(exception).__name__)  # local example
```

A swallowed error is not inferred from an empty answer, `None`, or another
sentinel. If the real harness makes suppression observable (for example through
a captured warning or instrumented fallback), provide a hook that returns a
strict Boolean after each successful extraction:

```python
observed_warnings = set()

def observed_swallow(fixture, extracted):
    return fixture.fixture_id in observed_warnings

report = run_check(
    extract_final,
    fixtures,
    escaped_exception_hook=record_escape,
    swallowed_error_hook=observed_swallow,
)
```

Without the swallowed hook the metric is `not_measured`, never an inferred zero.

## CLI

Import paths use `module:attribute` syntax. The module must be importable in the
current Python environment. Input can be plain JSONL or gzip-compressed JSONL.

```bash
trunccheck \
  --callable my_local_package.extractors:extract_answer \
  --score-callable my_local_package.scoring:score_answer \
  --corpus fixtures.jsonl.gz \
  --expected-sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
  --expected-count 20 \
  --expected-kind-count truncated=10 \
  --expected-kind-count control_correct=10 \
  --csv fixture_results.csv \
  --markdown report.md
```

This command imports and executes local code only. `--escaped-exception-hook`
and `--swallowed-error-hook` accept the hook signatures documented above.
`--include-synthetic --seed 1729` appends the generated 100-fixture corpus.
When `--markdown` is omitted, the Markdown report is written to stdout.

For the fixed REAP corpus, `--validate-real` requires its compressed-byte
SHA-256, exactly 195 rows, and kind counts of 131 truncated and 64 controls:

```bash
trunccheck \
  --callable my_local_package.extractors:extract_answer \
  --corpus observational/real_truncated_fixtures.jsonl.gz \
  --validate-real
```

## Fixture formats and validation

### Generic source JSONL

Each line is a JSON object with these required fields:

```json
{"kind":"truncated","text":"reasoning cut here","gold_answer":"42"}
```

`kind` is `truncated` or `control_correct`; `text` must be a string, including
the empty string. `gold_answer` is optional. Extra source fields are retained in
fixture metadata. Duplicate rows are never dropped. Stable generated IDs contain
the raw JSONL-line SHA-256 prefix and a duplicate ordinal.

`load_jsonl_fixtures` accepts optional expected compressed-file SHA-256, row
count, and exact kind counts. `load_real_fixtures` applies the fixed REAP values:

```python
from trunccheck import load_real_fixtures
fixtures = load_real_fixtures("observational/real_truncated_fixtures.jsonl.gz")
```

Malformed UTF-8/JSON, blank lines, invalid gzip data, schema errors, hash
mismatches, and count mismatches fail closed with `CorpusValidationError`.

### Native stable schema

`Fixture.to_dict()` emits schema version 1. Its fixed fields are:

- `fixture_id`, `kind`, `stratum`, `text`, `gold_answer`, and `truncated`;
- optional `shape`, `seed`, and `truncation_marker`;
- `generation_parameters` and `metadata` objects.

`Fixture.from_dict()` rejects unknown fields, unsupported schema versions, and
inconsistent kind/stratum/truncation combinations. Results use the versioned
`Result`, `Metric`, and `Report` dataclasses. CSV columns are exported as
`trunccheck.CSV_COLUMNS` and remain in a fixed order.

## Seeded synthetic fixtures

```python
from trunccheck import generate_synthetic_fixtures, write_fixtures_jsonl
write_fixtures_jsonl("synthetic.jsonl", generate_synthetic_fixtures(seed=1729))
```

The generator always emits exactly 100 fixtures in a stable order: 20 each for
mid-`\\boxed{`, mid-multiple-choice enumeration, immediately after a correct
`Final answer:` line, degeneration loops ending in a plausible number, and
mid-LaTeX expression. The default seed is 1729. Canonical JSONL serialization is
UTF-8, sorted-key compact JSON with LF line endings and one trailing newline.

CSV and Markdown serializers use fixed ordering and formatting and omit timing
measurements, making identical inputs and callable behavior byte-for-byte
reproducible.
