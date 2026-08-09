"""Locked math-verify adapter using the package's public parser and verifier."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from common import main, marshal_math_gold, serialize


class _Capture(logging.Handler):
    """Capture only concrete errors that math-verify itself suppresses."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.events: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        labels = (
            "Error parsing:",
            "Timeout during parsing:",
            "Error during comparison",
            "Timeout during comparison",
        )
        label = next((item.rstrip(":") for item in labels if message.startswith(item)), None)
        if label is None:
            return
        detail = label
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            rendered = str(exc).replace("\n", "\\n").replace("\r", "\\r")
            detail += f" ({type(exc).__name__}: {rendered[:300]})"
        self.events.append(detail)


def importer(repo: Path):
    source = (repo / "src").resolve()
    sys.path.insert(0, str(source))
    import math_verify

    imported_from = Path(math_verify.__file__).resolve()
    if source not in imported_from.parents:
        raise ImportError(f"math_verify imported outside locked checkout: {imported_from}")
    return math_verify


def function_builder(math_verify):
    parser_logger = logging.getLogger("math_verify.parser")
    grader_logger = logging.getLogger("math_verify.grader")

    def evaluate(row):
        capture = _Capture()
        loggers = (parser_logger, grader_logger)
        old_levels = [logger.level for logger in loggers]
        for logger in loggers:
            logger.addHandler(capture)
            logger.setLevel(logging.DEBUG)
        try:
            prediction = math_verify.parse(row["text"])
            gold_text = marshal_math_gold(row["gold_answer"])
            gold = math_verify.parse(gold_text)
            if not gold:
                result = {
                    "adapter_status": "not_applicable",
                    "status_reason": "gold parse produced no target with public default Latex+Expr parser",
                    "extracted_answer": serialize(prediction) if prediction else None,
                    "native_correct": None,
                }
            else:
                result = {
                    "extracted_answer": serialize(prediction) if prediction else None,
                    "native_correct": bool(math_verify.verify(gold, prediction)),
                }
        finally:
            for logger, old_level in zip(loggers, old_levels):
                logger.removeHandler(capture)
                logger.setLevel(old_level)

        if capture.events:
            result["swallowed_error_observed"] = True
            result["swallowed_error_detail"] = "; ".join(capture.events)
        return result

    return evaluate


if __name__ == "__main__":
    main(importer, function_builder)
