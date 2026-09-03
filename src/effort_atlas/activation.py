"""Pure fail-closed activation decision for a frozen REAP panel."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .reap_manifest import verify_manifest_files

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ACTIVATION_POLICY_VERSION = 1
TERMINAL_ACTIONS = ("activate", "omit")
EVIDENCE_FIELDS = frozenset(
    {
        "manifest_sha256",
        "activation_policy_sha256",
        "generation_retry_count",
        "receipt_reconciled",
        "budget_within_bound",
        "schedule_manifest_match",
        "served_route_match",
        "predicates",
    }
)
PREDICATE_FIELDS = frozenset({"id", "status", "evidence_sha256"})
ACTIVATION_ARTIFACT_FIELDS = frozenset(
    {
        "activation_policy_version",
        "predicate_ids",
        "substitution_allowed",
        "terminal_actions",
    }
)


@dataclass(frozen=True)
class ActivationDecision:
    action: Literal["activate", "omit"]
    failed_predicates: tuple[str, ...]


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class _ActivationRequirements:
    """Parsed requirements used only inside the manifest-verifying boundary."""

    predicate_ids: tuple[str, ...]
    expected_manifest_sha256: str
    policy_sha256: str


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError(f"activation artifact has duplicate field: {key}")
        value[key] = child
    return value


def _parse_activation_artifact(contents: bytes) -> tuple[str, ...]:
    try:
        value = json.loads(
            contents.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("activation artifact must be valid UTF-8 JSON") from error
    if not isinstance(value, Mapping):
        raise TypeError("activation artifact must be a JSON object")
    actual_fields = frozenset(value)
    if actual_fields != ACTIVATION_ARTIFACT_FIELDS:
        raise ValueError("activation artifact fields are invalid")
    if (
        type(value["activation_policy_version"]) is not int
        or value["activation_policy_version"] != ACTIVATION_POLICY_VERSION
    ):
        raise ValueError(
            f"activation_policy_version must be {ACTIVATION_POLICY_VERSION}"
        )
    if value["substitution_allowed"] is not False:
        raise ValueError("activation artifact must forbid substitution")
    if value["terminal_actions"] != list(TERMINAL_ACTIONS):
        raise ValueError("activation artifact terminal_actions are invalid")
    raw_predicates = value["predicate_ids"]
    if not isinstance(raw_predicates, list):
        raise TypeError("activation artifact predicate_ids must be a list")
    predicate_ids = tuple(raw_predicates)
    if (
        not predicate_ids
        or any(
            not isinstance(predicate_id, str) or not predicate_id.strip()
            for predicate_id in predicate_ids
        )
        or len(set(predicate_ids)) != len(predicate_ids)
    ):
        raise ValueError("activation artifact predicate_ids are invalid")
    return predicate_ids


def _load_activation_requirements(
    *, manifest: Mapping[str, Any], approved_root: str | Path
) -> _ActivationRequirements:
    """Read requirements only after exact-file verification of the frozen root."""

    verified = verify_manifest_files(manifest, approved_root=approved_root)
    validated_manifest = verified["manifest"]
    evidence = verified["evidence"]
    activation_reference = validated_manifest["activation"]
    activation_path = (
        Path(evidence["approved_root"]) / activation_reference["path"]
    )
    try:
        contents = activation_path.read_bytes()
    except OSError as error:
        raise ValueError("verified activation artifact became unreadable") from error
    actual_sha256 = hashlib.sha256(contents).hexdigest()
    if actual_sha256 != activation_reference["sha256"]:
        raise ValueError("activation artifact changed after manifest verification")
    predicate_ids = _parse_activation_artifact(contents)
    return _ActivationRequirements(
        predicate_ids=predicate_ids,
        expected_manifest_sha256=validated_manifest["manifest_sha256"],
        policy_sha256=activation_reference["sha256"],
    )


def _structural_failures(
    evidence: Mapping[str, Any], requirements: _ActivationRequirements
) -> list[str]:
    failures: list[str] = []
    actual_fields = frozenset(evidence)
    if actual_fields != EVIDENCE_FIELDS:
        for key in sorted(EVIDENCE_FIELDS - actual_fields):
            failures.append(f"{key}:missing")
        for key in sorted(actual_fields - EVIDENCE_FIELDS, key=repr):
            failures.append(f"{key}:unexpected")

    manifest_sha256 = evidence.get("manifest_sha256")
    if (
        not _valid_sha256(manifest_sha256)
        or manifest_sha256 != requirements.expected_manifest_sha256
    ):
        failures.append("manifest_mismatch")
    policy_sha256 = evidence.get("activation_policy_sha256")
    if (
        not _valid_sha256(policy_sha256)
        or policy_sha256 != requirements.policy_sha256
    ):
        failures.append("activation_policy_mismatch")

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


def _predicate_failures(predicate_ids: tuple[str, ...], value: object) -> list[str]:
    failures: list[str] = []
    required = predicate_ids
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
            label = (
                status
                if isinstance(status, str) and status in {"fail", "unknown"}
                else "invalid_status"
            )
            failures.append(f"predicate:{predicate_id}:{label}")
        if not _valid_sha256(result["evidence_sha256"]):
            failures.append(f"predicate:{predicate_id}:missing_evidence")
    return failures


def evaluate_activation(
    *,
    manifest: Mapping[str, Any] | object,
    approved_root: str | Path,
    evidence: Mapping[str, Any] | object,
) -> ActivationDecision:
    """Verify frozen artifact bytes, then apply every activation predicate.

    Manifest verification is deliberately inside this public boundary.  Callers
    cannot supply a pre-verified policy, token, or digest in place of the frozen
    root and its exact referenced files.
    """

    if not isinstance(evidence, Mapping):
        return ActivationDecision("omit", ("evidence:malformed",))
    if not isinstance(manifest, Mapping):
        return ActivationDecision("omit", ("activation_manifest:invalid",))
    try:
        requirements = _load_activation_requirements(
            manifest=manifest,
            approved_root=approved_root,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return ActivationDecision("omit", ("activation_manifest:invalid",))
    failures = _structural_failures(evidence, requirements)
    failures.extend(
        _predicate_failures(requirements.predicate_ids, evidence.get("predicates"))
    )
    deduplicated = tuple(dict.fromkeys(failures))
    return ActivationDecision("omit" if deduplicated else "activate", deduplicated)
