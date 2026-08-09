"""Locked LiveBench AIME task-path scorer adapter."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from common import main


INTEGER_GOLD = re.compile(r"^[+-]?\d+$")


def importer(repo: Path):
    sys.path.insert(0, str(repo.resolve()))
    from livebench.process_results.math.math_competitions.utils import aime_process_results

    return aime_process_results


def function_builder(aime_process_results):
    def evaluate(row):
        gold = str(row.get("gold_answer", "")).strip()
        if INTEGER_GOLD.fullmatch(gold) is None:
            return {
                "adapter_status": "not_applicable",
                "status_reason": "gold_answer is not an integer (AIME task schema)",
            }
        score = aime_process_results(gold, str(row.get("text") or ""), debug=False)
        return {
            "extracted_answer": None,
            "answer_returned": None,
            "native_correct": bool(score == 1),
            "status_reason": "answer_returned not measured: upstream AIME task path returns only a score",
        }

    return evaluate


if __name__ == "__main__":
    main(importer, function_builder)
