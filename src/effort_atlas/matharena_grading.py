"""Fail-closed boundary for a future pinned MathArena symbolic scorer.

This module does not import MathArena, select a revision, or parse answers.  A
caller must supply an already imported parser module plus its observed package
version and exact source-file pin.  Only the two deterministic parser callables
needed after grader-v2 extraction cross this boundary.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TypedDict

ParseAnswer = Callable[[str], tuple[object, object]]
CheckAnswers = Callable[[object, object], bool]


class MathArenaGradeResult(TypedDict):
    correct: bool
    extracted_answer_present: bool
    extracted_answer: str | None
    grader_status: str


class MathArenaImportFailed(RuntimeError):
    """A machine-readable failure to establish the exact upstream boundary."""

    status = "import_failed"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"MathArena scorer boundary import_failed: {reason}")


@dataclass(frozen=True, slots=True)
class MathArenaPin:
    """Caller-selected identity for an upstream parser module."""

    module_name: str
    distribution_version: str
    source_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.module_name, str)
            or not self.module_name.strip()
            or not isinstance(self.distribution_version, str)
            or not self.distribution_version.strip()
        ):
            raise MathArenaImportFailed("pin_missing")
        if (
            not isinstance(self.source_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) is None
        ):
            raise MathArenaImportFailed("pin_invalid")


_VALIDATED_BINDING = object()


@dataclass(frozen=True, slots=True, init=False)
class PinnedMathArenaScorer:
    """Validated handles to the two permitted deterministic upstream calls."""

    pin: MathArenaPin
    _parse_answer: ParseAnswer
    _check_answers: CheckAnswers

    def __init__(
        self,
        pin: MathArenaPin,
        parse_answer: ParseAnswer,
        check_answers: CheckAnswers,
        *,
        _binding_token: object | None = None,
    ) -> None:
        if _binding_token is not _VALIDATED_BINDING:
            raise MathArenaImportFailed("binding_required")
        object.__setattr__(self, "pin", pin)
        object.__setattr__(self, "_parse_answer", parse_answer)
        object.__setattr__(self, "_check_answers", check_answers)

    def _parse(self, value: str) -> object:
        parsed = self._parse_answer(value)
        if not isinstance(parsed, tuple) or len(parsed) != 2:
            raise ValueError("Pinned parse_answer returned an invalid result shape.")
        return parsed[0]

    def grade(
        self,
        extracted_answer: str | None,
        gold: str,
    ) -> MathArenaGradeResult:
        """Compare only grader-v2's extracted field with the gold field."""
        if not isinstance(gold, str) or not gold.strip():
            raise ValueError("gold must be a nonempty string.")
        if extracted_answer is None:
            return {
                "correct": False,
                "extracted_answer_present": False,
                "extracted_answer": None,
                "grader_status": "unanswered",
            }
        if not isinstance(extracted_answer, str) or not extracted_answer.strip():
            raise ValueError("extracted_answer must be None or a nonempty string.")

        parsed_answer = self._parse(extracted_answer)
        parsed_gold = self._parse(gold)
        correct = self._check_answers(parsed_answer, parsed_gold)
        if type(correct) is not bool:
            raise ValueError("Pinned check_answers returned a non-boolean result.")
        return {
            "correct": correct,
            "extracted_answer_present": True,
            "extracted_answer": extracted_answer,
            "grader_status": "ok",
        }


def _source_sha256(module: ModuleType) -> str:
    source_file = getattr(module, "__file__", None)
    if not isinstance(source_file, str) or not source_file:
        raise MathArenaImportFailed("source_unavailable")
    try:
        source = Path(source_file).read_bytes()
    except OSError as error:
        raise MathArenaImportFailed("source_unavailable") from error
    return hashlib.sha256(source).hexdigest()


def _callable_matches_source(
    function: object,
    *,
    name: str,
    module_name: str,
    source_file: Path,
) -> bool:
    code = getattr(function, "__code__", None)
    code_file = getattr(code, "co_filename", None)
    return (
        getattr(function, "__name__", None) == name
        and getattr(function, "__module__", None) == module_name
        and isinstance(code_file, str)
        and Path(code_file).resolve() == source_file.resolve()
    )


def bind_matharena_scorer(
    module: ModuleType | None,
    *,
    observed_version: str | None,
    pin: MathArenaPin | None,
) -> PinnedMathArenaScorer:
    """Validate exact caller-supplied provenance before exposing scoring."""
    if pin is None:
        raise MathArenaImportFailed("pin_missing")
    if module is None:
        raise MathArenaImportFailed("module_missing")
    if getattr(module, "__name__", None) != pin.module_name:
        raise MathArenaImportFailed("module_name_mismatch")
    if not isinstance(observed_version, str) or not observed_version:
        raise MathArenaImportFailed("version_missing")
    if observed_version != pin.distribution_version:
        raise MathArenaImportFailed("version_mismatch")
    if _source_sha256(module) != pin.source_sha256:
        raise MathArenaImportFailed("source_hash_mismatch")
    source_file = Path(module.__file__)

    parse_answer = getattr(module, "parse_answer", None)
    check_answers = getattr(module, "check_answers", None)
    if not callable(parse_answer) or not callable(check_answers):
        raise MathArenaImportFailed("callable_missing")
    permitted = (("parse_answer", parse_answer), ("check_answers", check_answers))
    if any(
        not _callable_matches_source(
            function,
            name=name,
            module_name=pin.module_name,
            source_file=source_file,
        )
        for name, function in permitted
    ):
        raise MathArenaImportFailed("callable_provenance_mismatch")
    return PinnedMathArenaScorer(
        pin,
        parse_answer,
        check_answers,
        _binding_token=_VALIDATED_BINDING,
    )
