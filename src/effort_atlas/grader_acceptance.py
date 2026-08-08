"""Build the privacy-preserving grader-v2 archive acceptance projection.

The two exploratory source archives are intentionally not committed.  This
module verifies their exact bytes, selects every 4,096-completion-token row,
and replaces response text with structural placeholders that preserve only
whether a complete ``Final answer:`` line exists.  Gold answers, extracted
answers, prompts, response text, and reasoning text never enter the projection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import TypedDict

from .graders import DEFAULT_FINAL_ANSWER_PATTERN, grade


ACCEPTANCE_COMPLETION_TOKENS = 4096
PROJECTION_SCHEMA_VERSION = "grader-v2-acceptance-v2"


class ArchiveSpec(TypedDict):
    path: str
    sha256: str
    bytes: int
    line_count: int
    domain: str
    grader: str


ARCHIVE_SPECS: tuple[ArchiveSpec, ...] = (
    {
        "path": "results/sweep_real_20260719_154609.jsonl",
        "sha256": "27cd36d5a44dc428baaeb6dfe8479a3574490ba5b4bb6b328cb6f0d3902eb4fa",
        "bytes": 1_337_311,
        "line_count": 150,
        "domain": "math",
        "grader": "numeric",
    },
    {
        "path": "results/sweep_real_20260719_172721.jsonl",
        "sha256": "c72bcf9a90a3d5d545ad9a3b368256c3edb14addcd4c725b5523862d38e3fcad",
        "bytes": 443_856,
        "line_count": 150,
        "domain": "knowledge",
        "grader": "exact_field",
    },
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _response_projection(response: str) -> dict[str, object]:
    """Remove text while retaining the line structure relevant to extraction."""
    lines = response.splitlines()
    terminator_line_numbers = [
        line_number
        for line_number, line in enumerate(lines, start=1)
        if DEFAULT_FINAL_ANSWER_PATTERN.fullmatch(line) is not None
    ]
    return {
        "line_count": len(lines),
        "terminator_line_numbers": terminator_line_numbers,
    }


def render_response_projection(projection: dict[str, object]) -> str:
    """Render a sanitized projection into input suitable for grader reruns."""
    line_count = projection.get("line_count")
    terminator_line_numbers = projection.get("terminator_line_numbers")
    if type(line_count) is not int or line_count < 0:
        raise ValueError("response projection line_count must be a nonnegative integer")
    if not isinstance(terminator_line_numbers, list) or not all(
        type(value) is int and 1 <= value <= line_count
        for value in terminator_line_numbers
    ):
        raise ValueError("response projection has invalid terminator line numbers")
    if len(set(terminator_line_numbers)) != len(terminator_line_numbers):
        raise ValueError("response projection has duplicate terminator line numbers")

    terminators = set(terminator_line_numbers)
    return "\n".join(
        "Final answer: REDACTED" if line_number in terminators else "REDACTED"
        for line_number in range(1, line_count + 1)
    )


def _validate_source(spec: ArchiveSpec, payload: bytes) -> list[bytes]:
    if len(payload) != spec["bytes"]:
        raise ValueError(f"archive byte count mismatch: {spec['path']}")
    if _sha256(payload) != spec["sha256"]:
        raise ValueError(f"archive SHA-256 mismatch: {spec['path']}")
    lines = payload.splitlines()
    if len(lines) != spec["line_count"]:
        raise ValueError(f"archive line count mismatch: {spec['path']}")
    return lines


def build_archive_projection(archive_root: Path) -> dict[str, object]:
    """Return the deterministic sanitized projection of the pinned archives."""
    sources: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []

    for spec in ARCHIVE_SPECS:
        payload = (archive_root / spec["path"]).read_bytes()
        source_lines = _validate_source(spec, payload)
        selected = 0

        for source_line, source_line_bytes in enumerate(source_lines, start=1):
            source_row = json.loads(source_line_bytes)
            if source_row.get("completion_tokens") != ACCEPTANCE_COMPLETION_TOKENS:
                continue
            selected += 1
            if source_row.get("domain") != spec["domain"]:
                raise ValueError(
                    f"archive domain mismatch: {spec['path']}:{source_line}"
                )
            response = source_row.get("response_text")
            gold = source_row.get("gold")
            if not isinstance(response, str) or not isinstance(gold, str):
                raise ValueError(
                    f"archive grading fields malformed: {spec['path']}:{source_line}"
                )

            response_projection = _response_projection(response)
            raw_grade = grade(spec["grader"], response, gold)
            projected_grade = grade(
                spec["grader"],
                render_response_projection(response_projection),
                "sanitized-gold-not-retained",
            )
            if (
                raw_grade["extracted_answer_present"]
                != projected_grade["extracted_answer_present"]
            ):
                raise AssertionError(
                    f"projection changed answer presence: {spec['path']}:{source_line}"
                )

            rows.append(
                {
                    "source_path": spec["path"],
                    "source_line": source_line,
                    "source_row_sha256": _sha256(source_line_bytes),
                    "response_sha256": _sha256(response.encode("utf-8")),
                    "domain": spec["domain"],
                    "grader": spec["grader"],
                    "completion_tokens": ACCEPTANCE_COMPLETION_TOKENS,
                    "response_projection": response_projection,
                    "legacy_extracted_answer_present": bool(
                        source_row.get("extracted")
                    ),
                }
            )

        sources.append(
            {
                **spec,
                "selected_4096_rows": selected,
            }
        )

    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "verification_command": (
            "PYTHONPATH=src python -m effort_atlas.grader_acceptance "
            "--archive-root <archive-root> "
            "--check tests/fixtures/grader_v2_acceptance.json"
        ),
        "derivation": (
            "Verify the two pinned exploratory archive files by byte count, "
            "line count, and SHA-256; select every row with completion_tokens "
            "equal to 4096; replace every non-terminator response line with a "
            "constant and every complete Final answer line with a canonical "
            "redacted terminator; confirm raw and projected grader-v2 answer "
            "presence agree. No prompt, response, reasoning, gold-answer, or "
            "extracted-answer text is retained."
        ),
        "sources": sources,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify or print the sanitized grader-v2 archive projection."
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        required=True,
        help="Repository root containing the ignored results/ source archives.",
    )
    parser.add_argument(
        "--check",
        type=Path,
        help="Compare against a committed projection instead of printing JSON.",
    )
    args = parser.parse_args()
    projection = build_archive_projection(args.archive_root)
    if args.check is None:
        print(json.dumps(projection, indent=2))
        return
    if projection != json.loads(args.check.read_text()):
        raise SystemExit("grader-v2 acceptance projection mismatch")
    print("grader-v2 acceptance projection verified")


if __name__ == "__main__":
    main()
