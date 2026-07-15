"""Deterministic graders. Each returns (correct: bool, extracted: str).

All prompts instruct the model to end with 'Final answer: <value>'; graders
parse that line first and fall back to lenient extraction so a model that
ignores the format isn't scored zero for formatting alone.
"""

from __future__ import annotations

import re


def _final_answer_line(text: str) -> str | None:
    matches = re.findall(r"final answer\s*:\s*(.+)", text, flags=re.IGNORECASE)
    return matches[-1].strip() if matches else None


def grade_numeric(response: str, gold: str) -> tuple[bool, str]:
    line = _final_answer_line(response)
    candidates: list[str] = []
    if line:
        candidates += re.findall(r"-?\d[\d,]*\.?\d*", line)
    if not candidates:  # fallback: last number anywhere
        candidates = re.findall(r"-?\d[\d,]*\.?\d*", response)
    if not candidates:
        return False, ""
    extracted = candidates[-1].replace(",", "")
    try:
        return float(extracted) == float(gold.replace(",", "")), extracted
    except ValueError:
        return extracted == gold, extracted


def grade_multiple_choice(response: str, gold: str) -> tuple[bool, str]:
    line = _final_answer_line(response)
    if line:
        m = re.search(r"\b([A-J])\b", line.upper())
        if m:
            return m.group(1) == gold.upper(), m.group(1)
    # fallback: last standalone letter-like token in the response
    tokens = re.findall(r"\b([A-J])[).\s]", response.upper() + " ")
    if tokens:
        return tokens[-1] == gold.upper(), tokens[-1]
    return False, ""


def grade_exact_field(response: str, gold: str) -> tuple[bool, str]:
    line = _final_answer_line(response)
    extracted = (line if line is not None else response.strip().splitlines()[-1]).strip()
    norm = lambda s: re.sub(r"[\s$]", "", s).strip(".").lower()  # noqa: E731
    if norm(extracted) == norm(gold):
        return True, extracted
    # numeric golds: allow 42 == 42.00
    try:
        return float(norm(extracted)) == float(norm(gold)), extracted
    except ValueError:
        return False, extracted


GRADERS = {
    "numeric": grade_numeric,
    "multiple_choice": grade_multiple_choice,
    "exact_field": grade_exact_field,
}


def grade(grader: str, response: str, gold: str) -> tuple[bool, str]:
    return GRADERS[grader](response, gold)
