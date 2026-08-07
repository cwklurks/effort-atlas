"""Locked LiveBench olympiad extraction and native scoring adapter."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from common import main, serialize


def importer(repo: Path) -> dict[str, Any]:
    """Import the pinned checkout's real olympiad extractor and scorer."""
    sys.path.insert(0, str(repo))

    from livebench.process_results.math.olympiad.utils import (
        extract_expression_completions_from_generation,
        proof_rearrangement_process_results,
    )

    return {
        "extract": extract_expression_completions_from_generation,
        "score": proof_rearrangement_process_results,
    }


def _integer_gold(value: Any) -> str | None:
    """Validate only the schema that the native scorer itself requires."""
    gold = str(value).strip()
    parts = gold.split(",")
    if not parts or any(not part.strip() for part in parts):
        return None
    try:
        for part in parts:
            int(part.strip())
    except (TypeError, ValueError):
        return None
    return gold


def function_builder(imported: dict[str, Any]):
    extract = imported["extract"]
    score = imported["score"]

    def evaluate(row: dict[str, Any]) -> dict[str, Any]:
        gold = _integer_gold(row.get("gold_answer"))
        if gold is None:
            return {
                "adapter_status": "not_applicable",
                "status_reason": "non-integer gold_answer",
            }

        text = row["text"]
        extracted = extract(text, False)
        native_score = score(
            gold,
            text,
            edit_distance=True,
            debug=False,
        )
        swallowed = bool(extracted and "NO ANSWER" in extracted)
        return {
            "extracted_answer": serialize(extracted) if extracted else None,
            "native_correct": bool(native_score == 1 or native_score == 1.0),
            "swallowed_error_observed": swallowed,
            "swallowed_error_detail": (
                "native extractor emitted NO ANSWER after a suppressed integer conversion error"
                if swallowed
                else ""
            ),
        }

    return evaluate


if __name__ == "__main__":
    main(importer, function_builder)
