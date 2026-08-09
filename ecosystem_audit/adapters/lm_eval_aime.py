"""Locked lm-evaluation-harness AIME task process_results adapter."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from common import main


INTEGER_GOLD = re.compile(r"^[+-]?\d+$")


def importer(repo: Path):
    source = (repo / "lm_eval/tasks/aime/utils.py").resolve()
    spec = importlib.util.spec_from_file_location("_locked_lm_eval_aime_utils", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load locked AIME task module: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != source:
        raise ImportError(f"lm-eval AIME module imported outside locked checkout: {module.__file__}")
    return module.process_results


def function_builder(process_results):
    def evaluate(row):
        gold = str(row.get("gold_answer", "")).strip()
        if INTEGER_GOLD.fullmatch(gold) is None:
            return {
                "adapter_status": "not_applicable",
                "status_reason": "gold_answer is not an integer (AIME task schema)",
            }
        score = process_results({"Answer": gold}, [str(row.get("text") or "")])
        return {
            "extracted_answer": None,
            "answer_returned": None,
            "native_correct": bool(score["exact_match"]),
            "status_reason": "answer_returned not measured: upstream process_results returns only a score",
        }

    return evaluate


if __name__ == "__main__":
    main(importer, function_builder)
