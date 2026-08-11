"""Fail-closed provenance manifests for pre-data dataset selection.

The schema records a caller-supplied selection rule and provenance evidence.  It
does not identify a preferred dataset, choose item counts, or assess model results.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

MANIFEST_VERSION = 1
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_PLACEHOLDER_VALUES = frozenset({"", "tbd", "pending", "unknown", "[__]", "__"})
_OUTCOME_DERIVED_PATTERN = re.compile(
    r"\b(?:response|outcomes?|model[ _-]?output|accuracy|performance|score|correct(?:ness)?)\b",
    re.IGNORECASE,
)
_OUTCOME_DERIVED_STATEMENT_PATTERN = re.compile(
    r"\b(?:based\s+on|derived\s+from|using)\b[^.]*"
    r"\b(?:response|outcomes?|model[ _-]?output|accuracy|performance|score|correct(?:ness)?)\b",
    re.IGNORECASE,
)
_FIRST_THIRTY_PATTERN = re.compile(r"\bfirst\s+30\b", re.IGNORECASE)
_SOURCE_DEFINED_PATTERN = re.compile(r"\bsource[- ]defined\b", re.IGNORECASE)
_TOP_LEVEL_FIELDS = frozenset(
    {
        "manifest_version",
        "dataset_identifier",
        "source",
        "items",
        "scorer",
        "selection",
        "manifest_sha256",
    }
)
_SOURCE_FIELDS = frozenset({"url", "revision", "license"})
_ITEM_FIELDS = frozenset({"item_id", "gold_sha256", "schema_sha256"})
_SCORER_FIELDS = frozenset({"mode_reference", "mode_sha256"})
_SELECTION_FIELDS = frozenset({"rule", "provenance_statement", "evidence_sha256"})


class DatasetManifestError(ValueError):
    """Raised when dataset selection cannot be audited before collection."""


def canonical_json(value: object) -> str:
    """Return a stable JSON representation after checking serializability."""
    _validate_json_value(value, path="value")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_dataset_manifest(
    *,
    dataset_identifier: str,
    source: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    scorer: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate declared provenance and return a canonical, hash-sealed manifest."""
    unsigned = {
        "manifest_version": MANIFEST_VERSION,
        "dataset_identifier": dataset_identifier,
        "source": dict(source),
        "items": [dict(item) for item in items],
        "scorer": dict(scorer),
        "selection": dict(selection),
    }
    _validate_unsigned(unsigned)
    return {**unsigned, "manifest_sha256": _sha256_json(unsigned)}


def validate_dataset_manifest(manifest: Mapping[str, Any]) -> str:
    """Validate a sealed manifest and return its verified digest."""
    if not isinstance(manifest, Mapping):
        raise DatasetManifestError("Dataset manifest must be an object.")
    _require_exact_fields(manifest, _TOP_LEVEL_FIELDS, label="manifest")
    supplied = manifest["manifest_sha256"]
    _require_sha256(supplied, label="manifest.manifest_sha256")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    _validate_unsigned(unsigned)
    actual = _sha256_json(unsigned)
    if supplied != actual:
        raise DatasetManifestError("manifest_sha256 does not match manifest contents.")
    return actual


def _validate_unsigned(manifest: Mapping[str, Any]) -> None:
    _require_exact_fields(
        manifest,
        _TOP_LEVEL_FIELDS - {"manifest_sha256"},
        label="unsigned manifest",
    )
    if type(manifest["manifest_version"]) is not int or manifest["manifest_version"] != MANIFEST_VERSION:
        raise DatasetManifestError(f"manifest_version must be the integer {MANIFEST_VERSION}.")
    _require_explicit_string(manifest["dataset_identifier"], label="dataset_identifier")
    _validate_source(manifest["source"])
    _validate_items(manifest["items"])
    _validate_scorer(manifest["scorer"])
    _validate_selection(manifest["selection"])


def _validate_source(source: object) -> None:
    _require_mapping(source, label="source")
    _require_exact_fields(source, _SOURCE_FIELDS, label="source")
    url = _require_explicit_string(source["url"], label="source.url")
    if not url.startswith(("https://", "http://")):
        raise DatasetManifestError("source.url must be an HTTP(S) URL.")
    _require_explicit_string(source["revision"], label="source.revision")
    _require_explicit_string(source["license"], label="source.license")


def _validate_items(items: object) -> None:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or not items:
        raise DatasetManifestError("items must be a nonempty array.")
    item_ids: set[str] = set()
    for index, item in enumerate(items):
        _require_mapping(item, label=f"items[{index}]")
        _require_exact_fields(item, _ITEM_FIELDS, label=f"items[{index}]")
        item_id = item["item_id"]
        if not isinstance(item_id, str) or _is_placeholder(item_id):
            raise DatasetManifestError(f"items[{index}].item_id must be an explicit nonempty string.")
        if item_id in item_ids:
            raise DatasetManifestError(f"items[{index}].item_id is duplicated.")
        item_ids.add(item_id)
        _require_sha256(item["gold_sha256"], label=f"items[{index}].gold_sha256")
        _require_sha256(item["schema_sha256"], label=f"items[{index}].schema_sha256")


def _validate_scorer(scorer: object) -> None:
    _require_mapping(scorer, label="scorer")
    _require_exact_fields(scorer, _SCORER_FIELDS, label="scorer")
    _require_explicit_string(scorer["mode_reference"], label="scorer.mode_reference")
    _require_sha256(scorer["mode_sha256"], label="scorer.mode_sha256")


def _validate_selection(selection: object) -> None:
    _require_mapping(selection, label="selection")
    _require_exact_fields(selection, _SELECTION_FIELDS, label="selection")
    rule = _require_explicit_string(selection["rule"], label="selection.rule")
    statement = _require_explicit_string(
        selection["provenance_statement"], label="selection.provenance_statement"
    )
    _require_sha256(selection["evidence_sha256"], label="selection.evidence_sha256")
    if _OUTCOME_DERIVED_PATTERN.search(rule) or _OUTCOME_DERIVED_STATEMENT_PATTERN.search(statement):
        raise DatasetManifestError("Selection rule cannot be response- or outcome-derived.")
    if _FIRST_THIRTY_PATTERN.search(rule) and not _SOURCE_DEFINED_PATTERN.search(statement):
        raise DatasetManifestError(
            "A positional first 30 selection requires a source-defined provenance statement."
        )


def _require_mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise DatasetManifestError(f"{label} must be an object with string keys.")
    return value


def _require_exact_fields(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = frozenset(value)
    if actual == expected:
        return
    details = []
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        details.append(f"missing {', '.join(missing)}")
    if unknown:
        details.append(f"unknown {', '.join(unknown)}")
    raise DatasetManifestError(f"{label} fields are invalid: {'; '.join(details)}.")


def _require_explicit_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _is_placeholder(value):
        raise DatasetManifestError(f"{label} must be an explicit non-placeholder string.")
    return value


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise DatasetManifestError(f"{label} must be a lowercase SHA-256 digest.")
    return value


def _sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _validate_json_value(value: object, *, path: str) -> None:
    if value is None or isinstance(value, (bool, int, float, str)):
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise DatasetManifestError(f"{path} contains a non-string object key.")
            _validate_json_value(child, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_json_value(child, path=f"{path}[{index}]")
        return
    raise DatasetManifestError(f"{path} is not JSON-serializable.")


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDER_VALUES
