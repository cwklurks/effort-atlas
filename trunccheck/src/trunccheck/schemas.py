"""Stable, dependency-free schemas used by :mod:`trunccheck`."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

KINDS = frozenset({"truncated", "control_correct"})
STRATA = frozenset({"real_truncated", "synthetic_truncated", "finished_control"})
REPORT_STATUSES = frozenset({"ok", "control_disqualified"})
SCHEMA_VERSION = 1


def _immutable_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    clean: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{name} keys must be strings")
        clean[key] = item
    return MappingProxyType(clean)


@dataclass(frozen=True, slots=True)
class Fixture:
    """One explicitly labeled response presented to an extractor.

    ``truncated`` is metadata, not a classification inferred from ``text``.
    """

    fixture_id: str
    kind: str
    stratum: str
    text: str
    gold_answer: str | None = None
    truncated: bool = True
    shape: str | None = None
    seed: int | None = None
    truncation_marker: str | None = None
    generation_parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, str) or not self.fixture_id:
            raise ValueError("fixture_id must be a non-empty string")
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        if self.stratum not in STRATA:
            raise ValueError(f"stratum must be one of {sorted(STRATA)}")
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        if self.gold_answer is not None and not isinstance(self.gold_answer, str):
            raise TypeError("gold_answer must be a string or None")
        if type(self.truncated) is not bool:
            raise TypeError("truncated must be a bool")
        expected_truncated = self.kind == "truncated"
        if self.truncated != expected_truncated:
            raise ValueError("truncated must agree with kind")
        expected_strata = (
            {"real_truncated", "synthetic_truncated"}
            if self.truncated
            else {"finished_control"}
        )
        if self.stratum not in expected_strata:
            raise ValueError("stratum must agree with kind/truncated")
        if self.seed is not None and (type(self.seed) is not int or self.seed < 0):
            raise ValueError("seed must be a non-negative integer or None")
        if self.shape is not None and (not isinstance(self.shape, str) or not self.shape):
            raise ValueError("shape must be a non-empty string or None")
        if self.truncation_marker is not None and not isinstance(self.truncation_marker, str):
            raise TypeError("truncation_marker must be a string or None")
        object.__setattr__(
            self, "generation_parameters", _immutable_mapping(self.generation_parameters, "generation_parameters")
        )
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "fixture_id": self.fixture_id,
            "kind": self.kind,
            "stratum": self.stratum,
            "text": self.text,
            "gold_answer": self.gold_answer,
            "truncated": self.truncated,
            "shape": self.shape,
            "seed": self.seed,
            "truncation_marker": self.truncation_marker,
            "generation_parameters": dict(self.generation_parameters),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Fixture":
        if not isinstance(value, Mapping):
            raise TypeError("fixture must be a mapping")
        version = value.get("schema_version", SCHEMA_VERSION)
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported fixture schema_version: {version!r}")
        allowed = {
            "schema_version", "fixture_id", "kind", "stratum", "text", "gold_answer",
            "truncated", "shape", "seed", "truncation_marker", "generation_parameters", "metadata",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown fixture fields: {sorted(unknown)}")
        try:
            return cls(
                fixture_id=value["fixture_id"],
                kind=value["kind"],
                stratum=value["stratum"],
                text=value["text"],
                gold_answer=value.get("gold_answer"),
                truncated=value.get("truncated", value.get("kind") == "truncated"),
                shape=value.get("shape"),
                seed=value.get("seed"),
                truncation_marker=value.get("truncation_marker"),
                generation_parameters=value.get("generation_parameters", {}),
                metadata=value.get("metadata", {}),
            )
        except KeyError as exc:
            raise ValueError(f"missing fixture field: {exc.args[0]}") from exc


@dataclass(frozen=True, slots=True)
class Result:
    fixture_id: str
    kind: str
    stratum: str
    extracted_answer: str | None
    answer_returned: bool
    escaped_exception_class: str | None = None
    escaped_exception_message: str | None = None
    swallowed_error: bool | None = None
    scored_correct: bool | None = None
    scoring_exception_class: str | None = None
    scoring_exception_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, str) or not self.fixture_id:
            raise ValueError("fixture_id must be a non-empty string")
        if self.kind not in KINDS or self.stratum not in STRATA:
            raise ValueError("invalid result kind or stratum")
        if self.extracted_answer is not None and not isinstance(self.extracted_answer, str):
            raise TypeError("extracted_answer must be a string or None")
        for name in ("answer_returned",):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a bool")
        for name in ("swallowed_error", "scored_correct"):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a bool or None")
        escaped = self.escaped_exception_class is not None
        if escaped != (self.escaped_exception_message is not None):
            raise ValueError("escaped exception class and message must be set together")
        if escaped and (self.extracted_answer is not None or self.answer_returned):
            raise ValueError("an escaped extraction exception cannot return an answer")
        scoring = self.scoring_exception_class is not None
        if scoring != (self.scoring_exception_message is not None):
            raise ValueError("scoring exception class and message must be set together")
        if scoring and self.scored_correct is not None:
            raise ValueError("a scoring exception cannot also have a score")

    @property
    def crashed(self) -> bool:
        return self.escaped_exception_class is not None


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    numerator: int | None
    denominator: int | None
    percent: float | None
    status: str = "ok"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("metric name must be non-empty")
        if self.status not in {"ok", "not_measured"}:
            raise ValueError("metric status must be ok or not_measured")
        if self.status == "not_measured":
            if any(value is not None for value in (self.numerator, self.denominator, self.percent)):
                raise ValueError("not_measured metrics have no numeric values")
            return
        if type(self.numerator) is not int or type(self.denominator) is not int:
            raise TypeError("measured metric counts must be integers")
        if self.numerator < 0 or self.denominator < 0 or self.numerator > self.denominator:
            raise ValueError("invalid metric counts")
        expected = None if self.denominator == 0 else self.numerator * 100.0 / self.denominator
        if self.percent != expected:
            raise ValueError("metric percent does not match counts")


@dataclass(frozen=True, slots=True)
class Report:
    pipeline: str
    status: str
    metrics: tuple[Metric, ...]
    results: tuple[Result, ...]
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.pipeline, str) or not self.pipeline:
            raise ValueError("pipeline must be a non-empty string")
        if self.status not in REPORT_STATUSES:
            raise ValueError(f"status must be one of {sorted(REPORT_STATUSES)}")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported report schema version")
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("metric names must be unique")
        ids = [result.fixture_id for result in self.results]
        if len(ids) != len(set(ids)):
            raise ValueError("result fixture IDs must be unique")

    def metric(self, name: str) -> Metric:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        raise KeyError(name)
