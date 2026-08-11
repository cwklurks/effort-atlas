"""Pure fail-closed activation decision for a frozen REAP panel."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
EVIDENCE_FIELDS = frozenset(
    {
        "manifest_sha256",
        "generation_retry_count",
        "receipt_reconciled",
        "budget_within_bound",
        "schedule_manifest_match",
        "served_route_match",
        "predicates",
    }
)
PREDICATE_FIELDS = frozenset({"id", "status", "evidence_sha256"})


@dataclass(frozen=True)
class ActivationDecision:
    action: Literal["activate", "omit"]
    failed_predicates: tuple[str, ...]


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _structural_failures(
    evidence: Mapping[str, Any], expected_manifest_sha256: str
) -> list[str]:
    failures: list[str] = []
    actual_fields = frozenset(evidence)
    if actual_fields != EVIDENCE_FIELDS:
        for key in sorted(EVIDENCE_FIELDS - actual_fields):
            failures.append(f"{key}:missing")
        for key in sorted(actual_fields - EVIDENCE_FIELDS):
            failures.append(f"{key}:unexpected")

    manifest_sha256 = evidence.get("manifest_sha256")
    if not _valid_sha256(expected_manifest_sha256):
        failures.append("expected_manifest_sha256:invalid")
    if (
        not _valid_sha256(manifest_sha256)
        or manifest_sha256 != expected_manifest_sha256
    ):
        failures.append("manifest_mismatch")

    retry_count = evidence.get("generation_retry_count")
    if type(retry_count) is not int or retry_count != 0:
        failures.append("generation_retry_count")
    for key in (
        "receipt_reconciled",
        "budget_within_bound",
        "schedule_manifest_match",
        "served_route_match",
    ):
        if evidence.get(key) is not True:
            failures.append(key)
    return failures


def _predicate_failures(
    required_predicate_ids: Sequence[str], value: object
) -> list[str]:
    failures: list[str] = []
    required = tuple(required_predicate_ids)
    if (
        not required
        or any(not isinstance(item, str) or not item.strip() for item in required)
        or len(set(required)) != len(required)
    ):
        return ["required_predicates:invalid"]
    if not isinstance(value, list):
        return ["predicates:malformed"]

    results: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping) or frozenset(raw) != PREDICATE_FIELDS:
            failures.append(f"predicates:malformed:{index}")
            continue
        predicate_id = raw.get("id")
        if not isinstance(predicate_id, str) or not predicate_id.strip():
            failures.append(f"predicates:malformed:{index}")
            continue
        if predicate_id in results:
            failures.append(f"predicate:{predicate_id}:duplicate")
            continue
        results[predicate_id] = raw

    for predicate_id in sorted(set(results) - set(required)):
        failures.append(f"predicate:{predicate_id}:unexpected")
    for predicate_id in required:
        result = results.get(predicate_id)
        if result is None:
            failures.append(f"predicate:{predicate_id}:missing")
            continue
        status = result["status"]
        if status != "pass":
            label = status if status in {"fail", "unknown"} else "invalid_status"
            failures.append(f"predicate:{predicate_id}:{label}")
        if not _valid_sha256(result["evidence_sha256"]):
            failures.append(f"predicate:{predicate_id}:missing_evidence")
    return failures


def evaluate_activation(
    *,
    required_predicate_ids: Sequence[str],
    expected_manifest_sha256: str,
    evidence: Mapping[str, Any] | object,
) -> ActivationDecision:
    """Activate only when every immutable and operational check passes."""

    if not isinstance(evidence, Mapping):
        return ActivationDecision("omit", ("evidence:malformed",))
    failures = _structural_failures(evidence, expected_manifest_sha256)
    failures.extend(
        _predicate_failures(required_predicate_ids, evidence.get("predicates"))
    )
    deduplicated = tuple(dict.fromkeys(failures))
    return ActivationDecision("omit" if deduplicated else "activate", deduplicated)
