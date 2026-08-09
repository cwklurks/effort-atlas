"""Deterministic report serialization."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterable

from .schemas import Report, Result

CSV_COLUMNS = (
    "schema_version",
    "pipeline",
    "pipeline_status",
    "fixture_id",
    "kind",
    "stratum",
    "extracted_answer",
    "answer_returned",
    "escaped_exception_class",
    "escaped_exception_message",
    "swallowed_error",
    "scored_correct",
    "scoring_exception_class",
    "scoring_exception_message",
)


def _optional_bool(value: bool | None) -> str:
    return "" if value is None else ("true" if value else "false")


def results_to_csv(report: Report) -> str:
    """Return RFC-4180-style CSV with fixed columns and LF line endings."""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for result in report.results:
        writer.writerow(
            {
                "schema_version": report.schema_version,
                "pipeline": report.pipeline,
                "pipeline_status": report.status,
                "fixture_id": result.fixture_id,
                "kind": result.kind,
                "stratum": result.stratum,
                "extracted_answer": "" if result.extracted_answer is None else result.extracted_answer,
                "answer_returned": _optional_bool(result.answer_returned),
                "escaped_exception_class": result.escaped_exception_class or "",
                "escaped_exception_message": result.escaped_exception_message or "",
                "swallowed_error": _optional_bool(result.swallowed_error),
                "scored_correct": _optional_bool(result.scored_correct),
                "scoring_exception_class": result.scoring_exception_class or "",
                "scoring_exception_message": result.scoring_exception_message or "",
            }
        )
    return output.getvalue()


def report_to_markdown(report: Report) -> str:
    """Return a deterministic human-readable metric report."""

    lines = [
        "# trunccheck report",
        "",
        f"- Schema version: `{report.schema_version}`",
        f"- Pipeline: `{report.pipeline}`",
        f"- Status: `{report.status}`",
        f"- Fixture results: {len(report.results)}",
        "",
        "`fabrication_pct` is an operational alias for answers returned after truncation; it is not proof that answer text was invented.",
        "",
        "| Metric | Status | Numerator | Denominator | Percent |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in report.metrics:
        if metric.status == "not_measured":
            lines.append(f"| `{metric.name}` | `not_measured` | - | - | - |")
        else:
            percent = "not_applicable" if metric.percent is None else f"{metric.percent:.6f}%"
            lines.append(
                f"| `{metric.name}` | `ok` | {metric.numerator} | {metric.denominator} | {percent} |"
            )
    if report.status == "control_disqualified":
        lines.extend(
            [
                "",
                "This pipeline failed at least one applicable finished-correct control and is disqualified from headline comparison.",
            ]
        )
    return "\n".join(lines) + "\n"


def write_report(
    report: Report,
    *,
    csv_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> None:
    if csv_path is not None:
        Path(csv_path).write_text(results_to_csv(report), encoding="utf-8", newline="")
    if markdown_path is not None:
        Path(markdown_path).write_text(report_to_markdown(report), encoding="utf-8", newline="")
