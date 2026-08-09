"""Locked Inspect Evals AIME scorer adapter (no model calls)."""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from typing import Any

from common import main, serialize

_INTEGER_GOLD = re.compile(r"^[+-]?\d+$")


def _integer_gold(value: Any) -> bool:
    return (
        value is not None
        and not isinstance(value, bool)
        and _INTEGER_GOLD.fullmatch(str(value).strip()) is not None
    )


def importer(repo: Path) -> dict[str, Any]:
    # inspect_evals is a separate locked repository. Import its locked Inspect AI
    # sibling first rather than resolving an arbitrary installed framework copy.
    inspect_ai_repo = repo.parent / "inspect_ai"
    sys.path.insert(0, str(inspect_ai_repo / "src"))
    sys.path.insert(0, str(repo / "src"))

    from inspect_ai.model import ModelName, ModelOutput
    from inspect_ai.scorer import CORRECT, Target
    from inspect_ai.solver import TaskState
    from inspect_evals.utils.aime_common import aime_scorer

    return {
        "CORRECT": CORRECT,
        "ModelName": ModelName,
        "ModelOutput": ModelOutput,
        "Target": Target,
        "TaskState": TaskState,
        "aime_scorer": aime_scorer,
    }


def function_builder(imported: dict[str, Any]):
    scorer = imported["aime_scorer"]()

    async def score(row: dict[str, Any]) -> dict[str, Any]:
        gold = row.get("gold_answer")
        if row.get("stratum") == "real_truncated" and row.get("dataset") != "aime_2026_outputs":
            return {
                "adapter_status": "not_applicable",
                "status_reason": "real fixture is not from the frozen AIME 2026 dataset",
            }
        if not _integer_gold(gold):
            return {
                "adapter_status": "not_applicable",
                "status_reason": "gold_answer is not an integer (AIME scorer schema)",
            }

        model_name = imported["ModelName"]("mockllm/fixture")
        state = imported["TaskState"](
            model=model_name,
            sample_id=row["fixture_id"],
            epoch=0,
            input="offline AIME-style fixture",
            messages=[],
            output=imported["ModelOutput"].from_content(
                str(model_name), row.get("text") or ""
            ),
        )
        result = await scorer(state, imported["Target"](str(gold).strip()))
        return {
            "extracted_answer": serialize(result.answer),
            "native_correct": result.text == imported["CORRECT"],
        }

    def run(row: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(score(row))

    return run


if __name__ == "__main__":
    main(importer, function_builder)
