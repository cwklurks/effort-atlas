"""Locked lm-evaluation-harness GSM8K flexible-extraction adapter."""
from __future__ import annotations

import sys
import types
from pathlib import Path

from common import main, serialize


_PATTERN = r"(-?[$0-9.,]{2,})|(-?[0-9]+)"
_METRIC_KWARGS = {
    "ignore_case": True,
    "ignore_punctuation": False,
    "regexes_to_ignore": [",", r"\$", "(?s).*#### ", r"\.$"],
}


def _locked_namespace(name: str, path: Path) -> None:
    """Create a package namespace without executing unrelated package startup."""
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name
    module.__path__ = [str(path)]
    sys.modules[name] = module


def importer(repo: Path):
    """Import the real filter classes and, separately, the native metric."""
    package = repo.resolve() / "lm_eval"
    if not package.is_dir():
        raise FileNotFoundError(f"locked lm_eval package not found at {package}")

    # lm_eval.__init__ only obtains installed distribution metadata.  This
    # isolated source audit needs the locked utility modules, not package CLI
    # startup, so namespace packages keep every invoked callable source-backed.
    _locked_namespace("lm_eval", package)
    _locked_namespace("lm_eval.filters", package / "filters")

    from lm_eval.filters import extraction as extraction_module
    from lm_eval.filters import selection as selection_module

    for module in (extraction_module, selection_module):
        imported_from = Path(module.__file__).resolve()
        if package not in imported_from.parents:
            raise ImportError(f"lm_eval module imported outside locked checkout: {imported_from}")

    scorer = None
    scorer_error = ""
    try:
        from lm_eval.api import metrics as metrics_module

        imported_from = Path(metrics_module.__file__).resolve()
        if package not in imported_from.parents:
            raise ImportError(
                f"lm_eval metric imported outside locked checkout: {imported_from}"
            )
        scorer = metrics_module.exact_match_fn
    except Exception as exc:  # optional downstream path, reported per row
        scorer_error = f"{type(exc).__name__}: {exc}"

    return (
        extraction_module.RegexFilter,
        selection_module.TakeFirstFilter,
        scorer,
        scorer_error,
    )


def function_builder(imported):
    RegexFilter, TakeFirstFilter, scorer, scorer_error = imported
    extractor = RegexFilter(regex_pattern=_PATTERN, group_select=-1)
    take_first = TakeFirstFilter()

    def run(row):
        docs = [{}]
        filtered = extractor.apply([[row["text"]]], docs)
        extracted = list(take_first.apply(filtered, docs))[0]
        result = {
            "extracted_answer": None if extracted == "[invalid]" else serialize(extracted),
            "native_correct": None,
            "swallowed_error_observed": None,
        }
        if scorer is None:
            result["status_reason"] = (
                "not_measured: native exact_match scorer import failed: "
                + scorer_error
            )
            return result

        score = scorer(
            predictions=[extracted],
            references=[str(row["gold_answer"])],
            **_METRIC_KWARGS,
        )
        result["native_correct"] = bool(score["exact_match"])
        return result

    return run


if __name__ == "__main__":
    main(importer, function_builder)
