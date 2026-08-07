"""Execute extraction functions and calculate truncation diagnostics."""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Iterable, Protocol

from .schemas import Fixture, Metric, Report, Result


class Extractor(Protocol):
    def __call__(self, text: str) -> Any: ...


class Scorer(Protocol):
    def __call__(self, extracted_answer: str | None, gold_answer: str | None) -> bool: ...


class EscapedExceptionHook(Protocol):
    def __call__(self, fixture: Fixture, exception: Exception) -> None: ...


class SwallowedErrorHook(Protocol):
    def __call__(self, fixture: Fixture, extracted_answer: str | None) -> bool: ...


def _answer_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _returned(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _metric(name: str, values: Iterable[bool]) -> Metric:
    sequence = tuple(values)
    numerator = sum(sequence)
    denominator = len(sequence)
    percent = None if denominator == 0 else numerator * 100.0 / denominator
    return Metric(name, numerator, denominator, percent)


def _not_measured(name: str) -> Metric:
    return Metric(name, None, None, None, "not_measured")


def _metric_group(
    results: tuple[Result, ...],
    *,
    suffix: str,
    scorer_measured: bool,
    swallowed_measured: bool,
) -> list[Metric]:
    tail = f"_{suffix}" if suffix else ""
    metrics = [
        _metric(f"answer_returned_after_truncation_pct{tail}", (r.answer_returned for r in results)),
        _metric(f"fabrication_pct{tail}", (r.answer_returned for r in results)),
        _metric(f"crash_pct{tail}", (r.crashed for r in results)),
    ]
    metrics.append(
        _metric(f"swallowed_error_pct{tail}", (r.swallowed_error is True for r in results))
        if swallowed_measured
        else _not_measured(f"swallowed_error_pct{tail}")
    )
    metrics.append(
        _metric(f"accidental_correct_pct{tail}", (r.scored_correct is True for r in results))
        if scorer_measured
        else _not_measured(f"accidental_correct_pct{tail}")
    )
    return metrics


def run_check(
    extractor: Extractor,
    fixtures: Iterable[Fixture],
    *,
    scorer: Scorer | None = None,
    escaped_exception_hook: EscapedExceptionHook | None = None,
    swallowed_error_hook: SwallowedErrorHook | None = None,
    pipeline: str | None = None,
) -> Report:
    """Run ``extractor(text)`` on labeled fixtures and return a report.

    The package catches ordinary ``Exception`` instances from the extractor and
    records them as escaped extraction exceptions. ``KeyboardInterrupt`` and
    other ``BaseException`` subclasses are intentionally not caught.

    A swallowed error cannot be inferred from a sentinel value. Supply
    ``swallowed_error_hook`` only when the harness exposes a concrete observable
    event (for example a captured warning or instrumented fallback). Without it,
    swallowed-error metrics are ``not_measured``.
    """

    if not callable(extractor):
        raise TypeError("extractor must be callable")
    if scorer is not None and not callable(scorer):
        raise TypeError("scorer must be callable or None")
    if escaped_exception_hook is not None and not callable(escaped_exception_hook):
        raise TypeError("escaped_exception_hook must be callable or None")
    if swallowed_error_hook is not None and not callable(swallowed_error_hook):
        raise TypeError("swallowed_error_hook must be callable or None")
    fixture_tuple = tuple(fixtures)
    if not all(isinstance(item, Fixture) for item in fixture_tuple):
        raise TypeError("fixtures must contain Fixture instances")
    fixture_ids = [item.fixture_id for item in fixture_tuple]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("fixture IDs must be unique; duplicate rows need unique ordinal IDs")

    results: list[Result] = []
    for fixture in fixture_tuple:
        answer: str | None = None
        escaped_class: str | None = None
        escaped_message: str | None = None
        swallowed: bool | None = None
        scored: bool | None = None
        score_class: str | None = None
        score_message: str | None = None
        try:
            answer = _answer_string(extractor(fixture.text))
        except Exception as exc:
            escaped_class = type(exc).__name__
            escaped_message = str(exc)
            if escaped_exception_hook is not None:
                escaped_exception_hook(fixture, exc)
        else:
            if swallowed_error_hook is not None:
                observed = swallowed_error_hook(fixture, answer)
                if type(observed) is not bool:
                    raise TypeError("swallowed_error_hook must return bool")
                swallowed = observed
            if scorer is not None:
                try:
                    score_value = scorer(answer, fixture.gold_answer)
                    if type(score_value) is not bool:
                        raise TypeError("scorer must return bool")
                    scored = score_value
                except Exception as exc:
                    score_class = type(exc).__name__
                    score_message = str(exc)
        results.append(
            Result(
                fixture_id=fixture.fixture_id,
                kind=fixture.kind,
                stratum=fixture.stratum,
                extracted_answer=answer,
                answer_returned=_returned(answer),
                escaped_exception_class=escaped_class,
                escaped_exception_message=escaped_message,
                swallowed_error=swallowed,
                scored_correct=scored,
                scoring_exception_class=score_class,
                scoring_exception_message=score_message,
            )
        )

    result_tuple = tuple(results)
    truncated = tuple(result for result in result_tuple if result.kind == "truncated")
    metrics = _metric_group(
        truncated, suffix="", scorer_measured=scorer is not None,
        swallowed_measured=swallowed_error_hook is not None,
    )
    for stratum in ("real_truncated", "synthetic_truncated"):
        selected = tuple(result for result in truncated if result.stratum == stratum)
        if selected:
            metrics.extend(
                _metric_group(
                    selected, suffix=stratum, scorer_measured=scorer is not None,
                    swallowed_measured=swallowed_error_hook is not None,
                )
            )
    controls = tuple(result for result in result_tuple if result.kind == "control_correct")
    metrics.append(_metric("control_answer_returned_pct", (r.answer_returned for r in controls)))
    metrics.append(
        _metric("control_pass_pct", (r.scored_correct is True for r in controls))
        if scorer is not None
        else _not_measured("control_pass_pct")
    )
    disqualified = scorer is not None and any(result.scored_correct is not True for result in controls)
    name = pipeline or getattr(extractor, "__qualname__", getattr(extractor, "__name__", "extractor"))
    return Report(
        pipeline=str(name),
        status="control_disqualified" if disqualified else "ok",
        metrics=tuple(metrics),
        results=result_tuple,
    )
