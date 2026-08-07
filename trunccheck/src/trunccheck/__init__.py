"""Offline truncation-response extraction diagnostics."""

from .fixtures import (
    DEFAULT_SEED, REAL_CORPUS_COUNT, REAL_CORPUS_KIND_COUNTS, REAL_CORPUS_SHA256,
    SYNTHETIC_SHAPES, CorpusValidationError, fixtures_to_jsonl,
    generate_synthetic_fixtures, load_jsonl_fixtures, load_real_fixtures,
    write_fixtures_jsonl,
)
from .report import CSV_COLUMNS, report_to_markdown, results_to_csv, write_report
from .runner import run_check
from .schemas import Fixture, Metric, Report, Result, SCHEMA_VERSION

__all__ = [
    "CSV_COLUMNS", "DEFAULT_SEED", "REAL_CORPUS_COUNT", "REAL_CORPUS_KIND_COUNTS",
    "REAL_CORPUS_SHA256", "SYNTHETIC_SHAPES", "CorpusValidationError", "Fixture",
    "Metric", "Report", "Result", "SCHEMA_VERSION", "fixtures_to_jsonl",
    "generate_synthetic_fixtures", "load_jsonl_fixtures", "load_real_fixtures",
    "report_to_markdown", "results_to_csv", "run_check", "write_fixtures_jsonl",
    "write_report",
]
