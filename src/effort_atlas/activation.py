"""Pure fail-closed activation decision for a frozen REAP panel."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
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
_VERIFIED_POLICY_ROOT = object()


@dataclass(frozen=True)
class ActivationDecision:
    action: Literal["activate", "omit"]
    failed_predicates: tuple[str, ...]


class ActivationPolicyInvalid(ValueError):
    """Raised when supplied policy content does not match its frozen digest."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Invalid activation policy: {reason}")


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _activation_policy_digest(
    predicate_ids: tuple[str, ...], expected_manifest_sha256: str
) -> str:
    payload = {
        "expected_manifest_sha256": expected_manifest_sha256,
        "policy_version": ACTIVATION_POLICY_VERSION,
        "predicate_ids": list(predicate_ids),
        "substitution_allowed": False,
        "terminal_actions": list(TERMINAL_ACTIONS),
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class ActivationPolicy:
    """Activation predicates, trusted only when loaded from verified frozen files."""

    predicate_ids: tuple[str, ...]
    expected_manifest_sha256: str
    policy_sha256: str
    _verified_root: object = field(default=None, repr=False, compare=False)

    def __init__(
        self,
        predicate_ids: tuple[str, ...],
        expected_manifest_sha256: str,
        policy_sha256: str,
    ) -> None:
        object.__setattr__(self, "predicate_ids", predicate_ids)
        object.__setattr__(self, "expected_manifest_sha256", expected_manifest_sha256)
        object.__setattr__(self, "policy_sha256", policy_sha256)
        object.__setattr__(self, "_verified_root", None)
        self.__post_init__()

    @classmethod
    def _from_verified_root(
        cls,
        *,
        predicate_ids: tuple[str, ...],
        expected_manifest_sha256: str,
        policy_sha256: str,
    ) -> ActivationPolicy:
        policy = object.__new__(cls)
        object.__setattr__(policy, "predicate_ids", predicate_ids)
        object.__setattr__(
            policy, "expected_manifest_sha256", expected_manifest_sha256
        )
        object.__setattr__(policy, "policy_sha256", policy_sha256)
        object.__setattr__(policy, "_verified_root", _VERIFIED_POLICY_ROOT)
        policy.__post_init__()
        return policy

    def __post_init__(self) -> None:
        if (
            not isinstance(self.predicate_ids, tuple)
            or not self.predicate_ids
            or any(
                not isinstance(predicate_id, str) or not predicate_id.strip()
                for predicate_id in self.predicate_ids
            )
            or len(set(self.predicate_ids)) != len(self.predicate_ids)
        ):
            raise ActivationPolicyInvalid("predicate_ids_invalid")
        if not _valid_sha256(self.expected_manifest_sha256):
            raise ActivationPolicyInvalid("manifest_sha256_invalid")
        if not _valid_sha256(self.policy_sha256):
            raise ActivationPolicyInvalid("policy_sha256_invalid")
        expected_digest = _activation_policy_digest(
            self.predicate_ids, self.expected_manifest_sha256
        )
        if (
            self._verified_root is not _VERIFIED_POLICY_ROOT
            and self.policy_sha256 != expected_digest
        ):
            raise ActivationPolicyInvalid("policy_digest_mismatch")


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


def load_activation_policy(
    *, manifest: Mapping[str, Any], approved_root: str | Path
) -> ActivationPolicy:
    """Load policy authority only from an exact-file-verified frozen manifest root."""

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
    return ActivationPolicy._from_verified_root(
        predicate_ids=predicate_ids,
        expected_manifest_sha256=validated_manifest["manifest_sha256"],
        policy_sha256=activation_reference["sha256"],
    )


def _structural_failures(
    evidence: Mapping[str, Any], policy: ActivationPolicy
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
        or manifest_sha256 != policy.expected_manifest_sha256
    ):
        failures.append("manifest_mismatch")
    policy_sha256 = evidence.get("activation_policy_sha256")
    if not _valid_sha256(policy_sha256) or policy_sha256 != policy.policy_sha256:
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
    policy: ActivationPolicy | object,
    evidence: Mapping[str, Any] | object,
) -> ActivationDecision:
    """Activate only when every immutable and operational check passes."""

    if not isinstance(policy, ActivationPolicy):
        return ActivationDecision("omit", ("activation_policy:invalid",))
    if not isinstance(evidence, Mapping):
        return ActivationDecision("omit", ("evidence:malformed",))
    failures = []
    if policy._verified_root is not _VERIFIED_POLICY_ROOT:
        failures.append("activation_policy:unverified_root")
    failures.extend(_structural_failures(evidence, policy))
    failures.extend(
        _predicate_failures(policy.predicate_ids, evidence.get("predicates"))
    )
    deduplicated = tuple(dict.fromkeys(failures))
    return ActivationDecision("omit" if deduplicated else "activate", deduplicated)
