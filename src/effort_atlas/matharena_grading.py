"""Fail-closed boundary for a future pinned MathArena symbolic scorer.

This module does not import MathArena, select a revision, or extract answers.  A
caller supplies an already imported parser module plus its observed package
version and exact source-file pin to :func:`grade_with_matharena`.  That sole
public grading call revalidates provenance before every comparison and passes
only grader-v2's extracted field to the two permitted deterministic callables.
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

__all__ = [
    "MathArenaGradeResult",
    "MathArenaImportFailed",
    "MathArenaPin",
    "grade_with_matharena",
]


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


def _source_bytes(module: ModuleType) -> tuple[Path, bytes]:
    source_file = getattr(module, "__file__", None)
    if not isinstance(source_file, str) or not source_file:
        raise MathArenaImportFailed("source_unavailable")
    source_path = Path(source_file)
    try:
        source = source_path.read_bytes()
    except OSError as error:
        raise MathArenaImportFailed("source_unavailable") from error
    return source_path, source


def _load_verified_namespace(
    source: bytes,
    *,
    source_file: Path,
    module_name: str,
) -> dict[str, object]:
    namespace: dict[str, object] = {
        "__file__": str(source_file),
        "__name__": module_name,
        "__package__": module_name.rpartition(".")[0],
    }
    try:
        exec(  # noqa: S102 - execute only the caller's exact hash-pinned source
            compile(source, str(source_file), "exec"),
            namespace,
        )
    except Exception as error:
        raise MathArenaImportFailed("source_execution_failed") from error
    return namespace


def _callable_matches_verified_definition(
    function: object,
    *,
    verified_function: object,
    name: str,
    module_name: str,
) -> bool:
    code = getattr(function, "__code__", None)
    verified_code = getattr(verified_function, "__code__", None)
    return (
        callable(function)
        and callable(verified_function)
        and getattr(function, "__name__", None) == name
        and getattr(function, "__module__", None) == module_name
        and code is not None
        and code == verified_code
    )


def _validated_callables(
    module: ModuleType | None,
    *,
    observed_version: str | None,
    pin: MathArenaPin | None,
) -> tuple[ParseAnswer, CheckAnswers]:
    """Validate exact caller-supplied provenance for one grade operation."""
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
    source_file, source = _source_bytes(module)
    if hashlib.sha256(source).hexdigest() != pin.source_sha256:
        raise MathArenaImportFailed("source_hash_mismatch")

    verified_namespace = _load_verified_namespace(
        source,
        source_file=source_file,
        module_name=pin.module_name,
    )

    parse_answer = getattr(module, "parse_answer", None)
    check_answers = getattr(module, "check_answers", None)
    verified_parse_answer = verified_namespace.get("parse_answer")
    verified_check_answers = verified_namespace.get("check_answers")
    if not all(
        callable(function)
        for function in (
            parse_answer,
            check_answers,
            verified_parse_answer,
            verified_check_answers,
        )
    ):
        raise MathArenaImportFailed("callable_missing")
    permitted = (
        ("parse_answer", parse_answer, verified_parse_answer),
        ("check_answers", check_answers, verified_check_answers),
    )
    if any(
        not _callable_matches_verified_definition(
            function,
            verified_function=verified_function,
            name=name,
            module_name=pin.module_name,
        )
        for name, function, verified_function in permitted
    ):
        raise MathArenaImportFailed("callable_provenance_mismatch")
    return verified_parse_answer, verified_check_answers


def _parse(parse_answer: ParseAnswer, value: str) -> object:
    parsed = parse_answer(value)
    if not isinstance(parsed, tuple) or len(parsed) != 2:
        raise ValueError("Pinned parse_answer returned an invalid result shape.")
    return parsed[0]


def grade_with_matharena(
    module: ModuleType | None,
    *,
    observed_version: str | None,
    pin: MathArenaPin | None,
    extracted_answer: str | None,
    gold: str,
) -> MathArenaGradeResult:
    """Verify the upstream boundary, then grade only grader-v2's extracted field."""
    if not isinstance(gold, str) or not gold.strip():
        raise ValueError("gold must be a nonempty string.")
    if extracted_answer is not None and (
        not isinstance(extracted_answer, str) or not extracted_answer.strip()
    ):
        raise ValueError("extracted_answer must be None or a nonempty string.")

    parse_answer, check_answers = _validated_callables(
        module,
        observed_version=observed_version,
        pin=pin,
    )
    if extracted_answer is None:
        return {
            "correct": False,
            "extracted_answer_present": False,
            "extracted_answer": None,
            "grader_status": "unanswered",
        }

    parsed_answer = _parse(parse_answer, extracted_answer)
    parsed_gold = _parse(parse_answer, gold)
    correct = check_answers(parsed_answer, parsed_gold)
    if type(correct) is not bool:
        raise ValueError("Pinned check_answers returned a non-boolean result.")
    return {
        "correct": correct,
        "extracted_answer_present": True,
        "extracted_answer": extracted_answer,
        "grader_status": "ok",
    }
