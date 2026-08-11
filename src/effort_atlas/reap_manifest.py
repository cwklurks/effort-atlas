"""Versioned, offline-only manifest contract for REAP Phase 3 artifacts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from .confirmatory import sha256_json

MANIFEST_VERSION = 2
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
TOP_LEVEL_FIELDS = frozenset(
    {
        "manifest_version",
        "state",
        "dataset",
        "prompt_renderer_grader",
        "route_price",
        "schedule",
        "analysis",
        "activation",
    }
)
SEALED_FIELDS = TOP_LEVEL_FIELDS | {"manifest_sha256"}
REFERENCE_FIELDS = frozenset({"path", "sha256"})
SCHEDULE_FIELDS = REFERENCE_FIELDS | {
    "dataset_sha256",
    "prompt_renderer_grader_sha256",
    "route_price_sha256",
}
ANALYSIS_FIELDS = REFERENCE_FIELDS | {"schedule_sha256"}
ACTIVATION_FIELDS = REFERENCE_FIELDS | {
    "schedule_sha256",
    "route_price_sha256",
}
PLACEHOLDER_PATTERN = re.compile(
    r"(?:\bTBD\b|\bPENDING\b|\[__+\]|\[DECIDE\])", re.IGNORECASE
)


def _require_exact_fields(
    value: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unknown:
            details.append(f"unknown {', '.join(unknown)}")
        raise ValueError(f"{label} fields are invalid: {'; '.join(details)}")


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or ".." in path.parts:
        raise ValueError(f"{label} must be a normalized relative POSIX path")
    return value


def _require_mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be an object with string keys")
    return value


def _validate_reference(
    value: object, *, fields: frozenset[str], label: str
) -> Mapping[str, Any]:
    section = _require_mapping(value, label=label)
    _require_exact_fields(section, fields, label=label)
    _require_relative_path(section["path"], label=f"{label}.path")
    for key in fields - {"path"}:
        _require_sha256(section[key], label=f"{label}.{key}")
    return section


def _contains_placeholder(value: object) -> bool:
    if isinstance(value, str):
        return PLACEHOLDER_PATTERN.search(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_placeholder(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_placeholder(child) for child in value)
    return False


def _validate_unsigned(manifest: Mapping[str, Any]) -> None:
    _require_exact_fields(manifest, TOP_LEVEL_FIELDS, label="manifest")
    if (
        type(manifest["manifest_version"]) is not int
        or manifest["manifest_version"] != MANIFEST_VERSION
    ):
        raise ValueError(f"manifest_version must be the integer {MANIFEST_VERSION}")
    if manifest["state"] not in {"draft", "frozen"}:
        raise ValueError("state must be draft or frozen")

    dataset = _validate_reference(
        manifest["dataset"], fields=REFERENCE_FIELDS, label="dataset"
    )
    prompt = _validate_reference(
        manifest["prompt_renderer_grader"],
        fields=REFERENCE_FIELDS,
        label="prompt_renderer_grader",
    )
    routes = _validate_reference(
        manifest["route_price"], fields=REFERENCE_FIELDS, label="route_price"
    )
    schedule = _validate_reference(
        manifest["schedule"], fields=SCHEDULE_FIELDS, label="schedule"
    )
    analysis = _validate_reference(
        manifest["analysis"], fields=ANALYSIS_FIELDS, label="analysis"
    )
    activation = _validate_reference(
        manifest["activation"], fields=ACTIVATION_FIELDS, label="activation"
    )

    expected_links = {
        "schedule.dataset_sha256": (schedule["dataset_sha256"], dataset["sha256"]),
        "schedule.prompt_renderer_grader_sha256": (
            schedule["prompt_renderer_grader_sha256"],
            prompt["sha256"],
        ),
        "schedule.route_price_sha256": (
            schedule["route_price_sha256"],
            routes["sha256"],
        ),
        "analysis.schedule_sha256": (analysis["schedule_sha256"], schedule["sha256"]),
        "activation.schedule_sha256": (
            activation["schedule_sha256"],
            schedule["sha256"],
        ),
        "activation.route_price_sha256": (
            activation["route_price_sha256"],
            routes["sha256"],
        ),
    }
    mismatches = [
        label
        for label, (actual, expected) in expected_links.items()
        if actual != expected
    ]
    if mismatches:
        raise ValueError(
            f"manifest cross-artifact hash mismatch: {', '.join(mismatches)}"
        )
    if manifest["state"] == "frozen" and _contains_placeholder(manifest):
        raise ValueError("frozen manifest contains a decision placeholder")


def seal_manifest(unsigned_manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and seal a manifest without reading files or making calls."""

    if not isinstance(unsigned_manifest, Mapping):
        raise TypeError("manifest must be an object")
    unsigned = dict(unsigned_manifest)
    _validate_unsigned(unsigned)
    return {**unsigned, "manifest_sha256": sha256_json(unsigned)}


def validate_manifest(
    manifest: Mapping[str, Any], *, require_frozen: bool = False
) -> dict[str, Any]:
    """Return a validated copy or fail on shape, link, state, or digest drift."""

    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be an object")
    _require_exact_fields(manifest, SEALED_FIELDS, label="sealed manifest")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    _validate_unsigned(unsigned)
    supplied = _require_sha256(manifest["manifest_sha256"], label="manifest_sha256")
    if supplied != sha256_json(unsigned):
        raise ValueError("manifest_sha256 does not match the canonical manifest")
    if require_frozen and manifest["state"] != "frozen":
        raise ValueError("a frozen manifest is required")
    return dict(manifest)
