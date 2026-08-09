"""Locked LightEval math extraction and native scoring adapter."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from common import main, marshal_math_gold, serialize


def importer(repo: Path) -> dict[str, Any]:
    """Import the pinned checkout's real math extractor and task metric."""
    adapter_dir = Path(__file__).resolve().parent
    sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != adapter_dir]
    sys.path.insert(0, str(repo / "src"))

    from lighteval.metrics.metrics import Metrics
    from lighteval.metrics.utils.extractive_match_utils import (
        ExprExtractionConfig,
        LatexExtractionConfig,
        extract_target_from_pred,
        get_extraction_regexes_inspect,
    )
    from lighteval.models.model_output import ModelResponse
    from lighteval.tasks.requests import Doc
    from lighteval.utils.language import Language

    prediction_targets = (
        ExprExtractionConfig(),
        LatexExtractionConfig(boxed_match_priority=0),
    )
    prediction_regexes = get_extraction_regexes_inspect(
        prediction_targets,
        Language.ENGLISH,
        len_choices=1,
    )
    return {
        "Doc": Doc,
        "Metrics": Metrics,
        "ModelResponse": ModelResponse,
        "extract_target_from_pred": extract_target_from_pred,
        "prediction_regexes": prediction_regexes,
    }


def function_builder(imported: dict[str, Any]):
    Doc = imported["Doc"]
    ModelResponse = imported["ModelResponse"]
    metric = imported["Metrics"].expr_gold_metric.value
    extract_target_from_pred = imported["extract_target_from_pred"]
    prediction_regexes = imported["prediction_regexes"]

    def evaluate(row: dict[str, Any]) -> dict[str, Any]:
        text = row["text"]
        gold = marshal_math_gold(row["gold_answer"])

        # These arguments are the ones bound by Metrics.expr_gold_metric.
        extracted = extract_target_from_pred(
            text,
            prediction_regexes,
            fallback_mode="first_match",
            extraction_mode="any_match",
            timeout_seconds=5,
        )

        doc = Doc(query="", choices=[gold], gold_index=0)
        response = ModelResponse(text=[text])
        native_result = metric.compute_sample(doc=doc, model_response=response)
        score = native_result[metric.metric_name]

        return {
            "extracted_answer": serialize(extracted) if extracted else None,
            "native_correct": bool(score == 1 or score == 1.0),
        }

    return evaluate


if __name__ == "__main__":
    main(importer, function_builder)
