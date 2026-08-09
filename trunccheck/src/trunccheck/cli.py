"""Command-line interface for trunccheck."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys
from typing import Any, Callable, Sequence

from .fixtures import (
    DEFAULT_SEED,
    REAL_CORPUS_COUNT,
    REAL_CORPUS_KIND_COUNTS,
    REAL_CORPUS_SHA256,
    CorpusValidationError,
    generate_synthetic_fixtures,
    load_jsonl_fixtures,
)
from .report import report_to_markdown, write_report
from .runner import run_check


def import_callable(path: str) -> Callable[..., Any]:
    """Import ``module:attribute`` (nested attributes are supported)."""

    if ":" not in path:
        raise ValueError("callable import path must use module:attribute syntax")
    module_name, attribute_path = path.split(":", 1)
    if not module_name or not attribute_path:
        raise ValueError("callable import path must use module:attribute syntax")
    try:
        value: Any = importlib.import_module(module_name)
    except Exception as exc:
        raise ImportError(f"could not import module {module_name!r}: {exc}") from exc
    try:
        for part in attribute_path.split("."):
            value = getattr(value, part)
    except AttributeError as exc:
        raise ImportError(f"could not resolve {path!r}: {exc}") from exc
    if not callable(value):
        raise TypeError(f"imported object {path!r} is not callable")
    return value


def _kind_count(value: str) -> tuple[str, int]:
    try:
        kind, count = value.split("=", 1)
        parsed = int(count)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("expected KIND=COUNT") from exc
    if not kind or parsed < 0:
        raise argparse.ArgumentTypeError("expected a non-empty KIND and non-negative COUNT")
    return kind, parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trunccheck",
        description="Run a local extraction callable on explicitly labeled JSONL fixtures.",
    )
    parser.add_argument("--callable", required=True, dest="callable_path", metavar="MODULE:ATTRIBUTE")
    parser.add_argument("--corpus", required=True, help="input .jsonl or .jsonl.gz path")
    parser.add_argument("--score-callable", metavar="MODULE:ATTRIBUTE")
    parser.add_argument("--escaped-exception-hook", metavar="MODULE:ATTRIBUTE")
    parser.add_argument("--swallowed-error-hook", metavar="MODULE:ATTRIBUTE")
    parser.add_argument("--pipeline", help="stable pipeline label (defaults to --callable)")
    parser.add_argument("--csv", dest="csv_path", help="write per-fixture CSV")
    parser.add_argument("--markdown", dest="markdown_path", help="write metric Markdown")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument(
        "--expected-kind-count", action="append", default=[], type=_kind_count, metavar="KIND=COUNT"
    )
    parser.add_argument(
        "--validate-real",
        action="store_true",
        help="require the fixed REAP real-corpus SHA-256, 195 rows, and 131/64 kind counts",
    )
    parser.add_argument("--include-synthetic", action="store_true", help="append the 100 seeded fixtures")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.expected_count is not None and args.expected_count < 0:
        parser.error("--expected-count must be non-negative")
    if args.validate_real and (
        args.expected_sha256 is not None or args.expected_count is not None or args.expected_kind_count
    ):
        parser.error("--validate-real cannot be combined with custom expected values")
    try:
        extractor = import_callable(args.callable_path)
        scorer = import_callable(args.score_callable) if args.score_callable else None
        escaped = import_callable(args.escaped_exception_hook) if args.escaped_exception_hook else None
        swallowed = import_callable(args.swallowed_error_hook) if args.swallowed_error_hook else None
        expected_hash = REAL_CORPUS_SHA256 if args.validate_real else args.expected_sha256
        expected_count = REAL_CORPUS_COUNT if args.validate_real else args.expected_count
        expected_kinds = (
            REAL_CORPUS_KIND_COUNTS
            if args.validate_real
            else (dict(args.expected_kind_count) if args.expected_kind_count else None)
        )
        fixtures = list(
            load_jsonl_fixtures(
                args.corpus,
                expected_sha256=expected_hash,
                expected_count=expected_count,
                expected_kind_counts=expected_kinds,
                source="real" if args.validate_real else "corpus",
            )
        )
        if args.include_synthetic:
            fixtures.extend(generate_synthetic_fixtures(args.seed))
        report = run_check(
            extractor,
            fixtures,
            scorer=scorer,
            escaped_exception_hook=escaped,
            swallowed_error_hook=swallowed,
            pipeline=args.pipeline or args.callable_path,
        )
        write_report(report, csv_path=args.csv_path, markdown_path=args.markdown_path)
        if not args.markdown_path:
            sys.stdout.write(report_to_markdown(report))
        return 0
    except (CorpusValidationError, ImportError, TypeError, ValueError, OSError) as exc:
        parser.exit(2, f"trunccheck: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
