"""Execute HELM's pinned MATH answer extraction and equivalence helpers."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

try:
    from .common import main, serialize
except ImportError:  # Direct script execution.
    from common import main, serialize


def import_helm(repo: Path):
    source_root = (repo / "src").resolve()
    expected = source_root / "helm/benchmark/scenarios/math_scenario.py"
    if not expected.is_file():
        raise FileNotFoundError(f"HELM MATH source not found: {expected}")
    sys.path.insert(0, str(source_root))
    module = importlib.import_module("helm.benchmark.scenarios.math_scenario")
    if Path(module.__file__).resolve() != expected:
        raise ImportError(f"Imported HELM MATH from unexpected path: {module.__file__}")
    return module.get_answer, module.is_equiv


def build_pipeline(imported):
    get_answer, is_equiv = imported

    def evaluate(row):
        text = str(row.get("text") or "")
        gold = str(row.get("gold_answer") or "")
        extracted = get_answer(text)
        return {
            "extracted_answer": serialize(extracted),
            "native_correct": bool(is_equiv(gold, extracted)),
        }

    return evaluate


if __name__ == "__main__":
    main(import_helm, build_pipeline)
