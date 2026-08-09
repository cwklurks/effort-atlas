"""Locked Inspect AI numeric-match adapter (no model calls)."""
from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path
from typing import Any

from common import main, serialize


def _numeric_gold(value: Any) -> bool:
    """Return whether fixture gold is a finite numeric scalar."""
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def importer(repo: Path) -> dict[str, Any]:
    sys.path.insert(0, str(repo / "src"))
    from inspect_ai.model import ModelName, ModelOutput
    from inspect_ai.scorer import CORRECT, Target, match
    from inspect_ai.solver import TaskState

    return {
        "CORRECT": CORRECT,
        "ModelName": ModelName,
        "ModelOutput": ModelOutput,
        "Target": Target,
        "TaskState": TaskState,
        "match": match,
    }


def function_builder(imported: dict[str, Any]):
    scorer = imported["match"](numeric=True)

    async def score(row: dict[str, Any]) -> dict[str, Any]:
        gold = row.get("gold_answer")
        if not _numeric_gold(gold):
            return {
                "adapter_status": "not_applicable",
                "status_reason": "gold_answer is not a finite numeric scalar",
            }

        model_name = imported["ModelName"]("mockllm/fixture")
        state = imported["TaskState"](
            model=model_name,
            sample_id=row["fixture_id"],
            epoch=0,
            input="offline truncation fixture",
            messages=[],
            output=imported["ModelOutput"].from_content(
                str(model_name), row.get("text") or ""
            ),
        )
        result = await scorer(state, imported["Target"](str(gold)))
        return {
            "extracted_answer": serialize(result.answer),
            "native_correct": result.text == imported["CORRECT"],
        }

    def run(row: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(score(row))

    return run


if __name__ == "__main__":
    main(importer, function_builder)
