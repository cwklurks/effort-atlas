"""Arm-aware entry guards for the offline REAP Phase 3 analysis path."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .analysis import validate_analysis_rows


def validate_single_arm_rows(
    rows: Iterable[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Validate one arm while refusing absent or cross-arm analysis input."""

    materialized = list(rows)
    if not materialized:
        raise ValueError("REAP analysis requires at least one row")

    arm_keys: set[str] = set()
    for index, row in enumerate(materialized, start=1):
        if "arm_key" not in row:
            raise ValueError(f"REAP analysis row {index} is missing arm_key")
        arm_key = row["arm_key"]
        if not isinstance(arm_key, str) or not arm_key.strip():
            raise ValueError(f"REAP analysis row {index} has an invalid arm_key")
        arm_keys.add(arm_key)
    if len(arm_keys) != 1:
        raise ValueError("REAP analysis requires exactly one arm_key per call")

    validated = validate_analysis_rows(materialized)
    return next(iter(arm_keys)), validated
