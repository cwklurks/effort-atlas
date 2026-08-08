"""Deterministic grader v2 with explicit-terminator answer extraction.

A response is answered only when one complete line matches the configured
terminator pattern. Termination metadata is deliberately absent from this API.
"""

from __future__ import annotations

import re
from typing import Callable, TypedDict


DEFAULT_FINAL_ANSWER_PATTERN = re.compile(
    r"[ \t]*Final answer[ \t]*:[ \t]*(?P<answer>\S(?:[^\r\n]*\S)?)[ \t]*",
    flags=re.IGNORECASE,
)

TerminatorPattern = str | re.Pattern[str]
Comparator = Callable[[str, str], bool]


class GradeResult(TypedDict):
    correct: bool
    extracted_answer_present: bool
    extracted_answer: str | None


def _compile_pattern(pattern: TerminatorPattern) -> re.Pattern[str]:
    if isinstance(pattern, str):
        return re.compile(pattern, flags=re.IGNORECASE)
    return pattern


def extract_final_answer(
    response: str,
    *,
    pattern: TerminatorPattern = DEFAULT_FINAL_ANSWER_PATTERN,
) -> str | None:
    """Return the last non-empty answer from a complete matching line.

    ``fullmatch`` makes line anchoring part of the extraction contract even for
    a caller-supplied pattern. The pattern must expose the answer as a named
    ``answer`` group or as its first capture group.
    """
    compiled = _compile_pattern(pattern)
    extracted: str | None = None
    for line in response.splitlines():
        match = compiled.fullmatch(line)
        if match is None:
            continue
        if "answer" in compiled.groupindex:
            candidate = match.group("answer")
        elif match.lastindex:
            candidate = match.group(1)
        else:
            raise ValueError(
                "terminator pattern must capture the answer in group 'answer' "
                "or its first capture group"
            )
        candidate = candidate.strip()
        if candidate:
            extracted = candidate
    return extracted


def _compare_numeric(extracted: str, gold: str) -> bool:
    """Compare the final-answer field using the pre-v2 numeric comparator."""
    candidates = re.findall(r"-?\d[\d,]*\.?\d*", extracted)
    if not candidates:
        return False
    normalized = candidates[-1].replace(",", "")
    try:
        return float(normalized) == float(gold.replace(",", ""))
    except ValueError:
        return normalized == gold


def _compare_multiple_choice(extracted: str, gold: str) -> bool:
    match = re.search(r"\b([A-J])\b", extracted.upper())
    return match is not None and match.group(1) == gold.upper()


def _compare_exact_field(extracted: str, gold: str) -> bool:
    norm = lambda value: re.sub(r"[\s$]", "", value).strip(".").lower()  # noqa: E731
    if norm(extracted) == norm(gold):
        return True
    try:
        return float(norm(extracted)) == float(norm(gold))
    except ValueError:
        return False


def _grade_with_comparator(
    comparator: Comparator,
    response: str,
    gold: str,
    *,
    pattern: TerminatorPattern = DEFAULT_FINAL_ANSWER_PATTERN,
) -> GradeResult:
    extracted = extract_final_answer(response, pattern=pattern)
    present = extracted is not None
    return {
        "correct": present and comparator(extracted, gold),
        "extracted_answer_present": present,
        "extracted_answer": extracted,
    }


def grade_numeric(
    response: str,
    gold: str,
    *,
    pattern: TerminatorPattern = DEFAULT_FINAL_ANSWER_PATTERN,
) -> GradeResult:
    return _grade_with_comparator(_compare_numeric, response, gold, pattern=pattern)


def grade_multiple_choice(
    response: str,
    gold: str,
    *,
    pattern: TerminatorPattern = DEFAULT_FINAL_ANSWER_PATTERN,
) -> GradeResult:
    return _grade_with_comparator(
        _compare_multiple_choice, response, gold, pattern=pattern
    )


def grade_exact_field(
    response: str,
    gold: str,
    *,
    pattern: TerminatorPattern = DEFAULT_FINAL_ANSWER_PATTERN,
) -> GradeResult:
    return _grade_with_comparator(
        _compare_exact_field, response, gold, pattern=pattern
    )


GRADERS = {
    "numeric": grade_numeric,
    "multiple_choice": grade_multiple_choice,
    "exact_field": grade_exact_field,
}


def grade(
    grader: str,
    response: str,
    gold: str,
    *,
    pattern: TerminatorPattern = DEFAULT_FINAL_ANSWER_PATTERN,
) -> GradeResult:
    return GRADERS[grader](response, gold, pattern=pattern)


def validate_grade_state(
    *,
    correct: object,
    extracted_answer_present: object,
    extracted_answer: object,
) -> str | None:
    """Return a machine-readable validation reason, or ``None`` if consistent."""
    if type(correct) is not bool:
        return "malformed_correct"
    if type(extracted_answer_present) is not bool:
        return "malformed_extracted_answer_presence"
    if correct and not extracted_answer_present:
        return "grade_extraction_inconsistent"
    if extracted_answer_present:
        if not isinstance(extracted_answer, str) or not extracted_answer:
            return "grade_extraction_inconsistent"
    elif extracted_answer is not None:
        return "grade_extraction_inconsistent"
    return None
