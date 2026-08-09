"""Execute simple-evals' pinned English MGSM extraction and scoring helpers."""
from __future__ import annotations

import importlib
import importlib.machinery
import sys
import types
from pathlib import Path

try:
    from .common import main, serialize
except ImportError:  # Direct script execution.
    from common import main, serialize


_PACKAGE = "_locked_openai_simple_evals"


def import_simple_evals(repo: Path):
    repo = repo.resolve()
    expected = repo / "mgsm_eval.py"
    if not expected.is_file():
        raise FileNotFoundError(f"simple-evals MGSM source not found: {expected}")

    # The upstream repository uses relative imports but has no packaging metadata
    # or __init__.py. Give the locked checkout a private namespace package so Python
    # can execute the source unchanged.
    package = types.ModuleType(_PACKAGE)
    package.__package__ = _PACKAGE
    package.__path__ = [str(repo)]
    package.__spec__ = importlib.machinery.ModuleSpec(_PACKAGE, loader=None, is_package=True)
    sys.modules[_PACKAGE] = package

    module = importlib.import_module(f"{_PACKAGE}.mgsm_eval")
    if Path(module.__file__).resolve() != expected:
        raise ImportError(f"Imported simple-evals MGSM from unexpected path: {module.__file__}")
    return module.parse_answer, module.score_mgsm


def build_pipeline(imported):
    parse_answer, score_mgsm = imported

    def evaluate(row):
        text = str(row.get("text") or "")
        gold = str(row.get("gold_answer") or "")
        extracted = parse_answer(text, "Answer:")
        return {
            "extracted_answer": serialize(extracted),
            "native_correct": bool(score_mgsm(gold, extracted)),
        }

    return evaluate


if __name__ == "__main__":
    main(import_simple_evals, build_pipeline)
