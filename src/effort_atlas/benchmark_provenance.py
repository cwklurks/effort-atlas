"""Fail-closed provenance checks for public benchmark archives.

This module verifies the *bytes* used by the exploratory benchmark-capability
audit.  It deliberately does not rerun ``observational/pipeline.py`` or make
any model-provider request.  The exported capability table contains only
question identifiers and aggregate source-native metadata; it never exports a
prompt, gold answer, model response, or GPQA content.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import zipfile
from ast import Assign, Name, literal_eval, parse
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from csv import reader
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

MANIFEST_SCHEMA = "benchmark-source-manifest-v1"
CAPABILITY_SCHEMA = "benchmark-question-capability-v1"
SUMMARY_SCHEMA = "benchmark-question-capability-summary-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_HOSTS = {
    "huggingface.co",
    "storage.googleapis.com",
    "raw.githubusercontent.com",
}
_CAPABILITY_FIELDS = frozenset(
    {
        "schema_version",
        "benchmark",
        "model",
        "question_id",
        "source_question_available",
        "archived_response_available",
        "attempt_count",
        "source_native_correct_count",
        "source_native_accuracy",
        "source_native_grade_semantics",
        "source_native_grade_status",
        "source_output_text_match_status",
        "source_output_gold_match_status",
        "prompt_fingerprint_set_digest",
        "prompt_fingerprint_count",
        "output_tokens_available",
        "output_tokens_mean",
        "output_tokens_invalid_count",
        "output_tokens_zero_count",
        "output_tokens_negative_count",
        "output_tokens_nonfinite_count",
        "output_tokens_status",
        "requested_max_tokens",
        "requested_cap_status",
        "finish_reason",
        "termination_status",
        "censoring_status",
        "strict_marker_regrade_status",
    }
)
_GPQA_HF_REVISION = re.compile(r"revision\s*=\s*[\"']([0-9a-f]{40})[\"']")
_GPQA_PASSWORD = re.compile(r"Password for dataset\.zip[^`]*`([^`]+)`", re.IGNORECASE)


class ProvenanceError(ValueError):
    """Raised when a source cannot be proven identical to its manifest entry."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProvenanceError(f"manifest is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ProvenanceError("manifest root must be an object")
    return value


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in _ALLOWED_HOSTS:
        raise ProvenanceError(f"source URL must be HTTPS on an allowlisted host: {url}")
    if parsed.username or parsed.password:
        raise ProvenanceError("source URL must not contain credentials")
    if parsed.netloc == "huggingface.co":
        match = re.fullmatch(
            r"/datasets/[^/]+/[^/]+/resolve/([0-9a-f]{40})/.+", parsed.path
        )
        if match is None or not _COMMIT.fullmatch(match.group(1)):
            raise ProvenanceError(
                f"Hugging Face URL must pin exactly one 40-character revision: {url}"
            )
    if parsed.netloc == "raw.githubusercontent.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 4 or not _COMMIT.fullmatch(parts[2]):
            raise ProvenanceError(
                f"GitHub URL must pin exactly one 40-character immutable commit: {url}"
            )
    if parsed.netloc == "storage.googleapis.com":
        generation = parse_qs(parsed.query).get("generation", [])
        if len(generation) != 1 or not generation[0].isdigit():
            raise ProvenanceError(f"GCS URL must pin an object generation: {url}")


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ProvenanceError(
            f"unsupported manifest schema: {manifest.get('schema_version')!r}"
        )
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ProvenanceError("manifest entries must be a non-empty list")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ProvenanceError(f"manifest entry {index} must be an object")
        required = ("source_id", "role", "url", "path", "bytes", "sha256", "policy")
        missing = [name for name in required if name not in entry]
        if missing:
            raise ProvenanceError(
                f"manifest entry {index} missing {', '.join(missing)}"
            )
        source_id = entry["source_id"]
        path = entry["path"]
        if not isinstance(source_id, str) or not source_id or source_id in seen_ids:
            raise ProvenanceError(
                f"manifest source_id must be unique and non-empty: {source_id!r}"
            )
        if (
            not isinstance(path, str)
            or not path
            or Path(path).is_absolute()
            or ".." in Path(path).parts
        ):
            raise ProvenanceError(f"manifest path must be safe and relative: {path!r}")
        if path in seen_paths:
            raise ProvenanceError(f"manifest path must be unique: {path}")
        if not isinstance(entry["bytes"], int) or entry["bytes"] < 0:
            raise ProvenanceError(
                f"manifest bytes must be a non-negative integer: {source_id}"
            )
        if not isinstance(entry["sha256"], str) or not _SHA256.fullmatch(
            entry["sha256"]
        ):
            raise ProvenanceError(
                f"manifest sha256 must be a lowercase SHA-256: {source_id}"
            )
        if not isinstance(entry["url"], str):
            raise ProvenanceError(f"manifest URL must be a string: {source_id}")
        _validate_url(entry["url"])
        seen_ids.add(source_id)
        seen_paths.add(path)
    policies = manifest.get("source_policies")
    if not isinstance(policies, Mapping) or not policies:
        raise ProvenanceError("manifest source_policies must be a non-empty object")
    for policy_id, policy in policies.items():
        if not isinstance(policy_id, str) or not isinstance(policy, Mapping):
            raise ProvenanceError("manifest source policies must be named objects")
        if not isinstance(policy.get("license"), str) or not isinstance(
            policy.get("redistribution"), str
        ):
            raise ProvenanceError(
                f"source policy {policy_id!r} needs license and redistribution rules"
            )
    unknown_policies = {entry["policy"] for entry in entries} - set(policies)
    if unknown_policies:
        raise ProvenanceError(
            f"manifest entry names unknown policy: {sorted(unknown_policies)}"
        )


def _source_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ProvenanceError(f"source path escapes root: {relative_path}") from exc
    return candidate


def verify_download_root(
    manifest: Mapping[str, Any], root: Path
) -> list[dict[str, Any]]:
    """Verify every local source, failing before any analysis on the first mismatch."""

    validate_manifest(manifest)
    verified: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        path = _source_path(root, entry["path"])
        if not path.is_file():
            raise ProvenanceError(
                f"missing pinned source: {entry['source_id']} ({path})"
            )
        observed_size = path.stat().st_size
        if observed_size != entry["bytes"]:
            raise ProvenanceError(
                f"size mismatch for {entry['source_id']}: expected {entry['bytes']}, got {observed_size}"
            )
        observed_hash = sha256_file(path)
        if observed_hash != entry["sha256"]:
            raise ProvenanceError(
                f"sha256 mismatch for {entry['source_id']}: expected {entry['sha256']}, got {observed_hash}"
            )
        verified.append(
            {
                "source_id": entry["source_id"],
                "role": entry["role"],
                "path": entry["path"],
                "bytes": observed_size,
                "sha256": observed_hash,
            }
        )
    return verified


def _normalise_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ProvenanceError(f"source-native correctness is not boolean-like: {value!r}")


def _mean(values: Sequence[int | float]) -> float | None:
    return float(sum(values) / len(values)) if values else None


def _content_fingerprint(value: Any) -> str | None:
    """Return a non-reversible audit fingerprint without exporting source content."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ProvenanceError(f"question text is not a string: {type(value).__name__}")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fingerprint_set_digest(fingerprints: Iterable[str]) -> str | None:
    values = sorted(set(fingerprints))
    if not values:
        return None
    return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()


def _output_token_summary(values: Iterable[Any]) -> dict[str, Any]:
    """Treat only finite, strictly-positive lengths as usable token measurements."""

    usable: list[float] = []
    zero_count = negative_count = nonfinite_count = 0
    for value in values:
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            nonfinite_count += 1
        elif value == 0:
            zero_count += 1
        elif value < 0:
            negative_count += 1
        else:
            usable.append(float(value))
    invalid_count = zero_count + negative_count + nonfinite_count
    if usable and invalid_count:
        status = "partial_invalid_values"
    elif usable:
        status = "available"
    elif zero_count and not negative_count and not nonfinite_count:
        status = "zero_values_only"
    elif negative_count and not zero_count and not nonfinite_count:
        status = "negative_values_only"
    elif nonfinite_count and not zero_count and not negative_count:
        status = "nonfinite_values_only"
    elif invalid_count:
        status = "invalid_values_only"
    else:
        status = "not_published"
    return {
        "output_tokens_available": bool(usable),
        "output_tokens_mean": _mean(usable),
        "output_tokens_invalid_count": invalid_count,
        "output_tokens_zero_count": zero_count,
        "output_tokens_negative_count": negative_count,
        "output_tokens_nonfinite_count": nonfinite_count,
        "output_tokens_status": status,
    }


def _match_status(source: str | None, observed: set[str]) -> str:
    if source is None or not observed:
        return "not_comparable"
    return "matches_source" if observed == {source} else "mismatch_source"


def build_matharena_capability_rows(
    *,
    benchmark: str,
    source_records: Iterable[Mapping[str, Any]],
    output_records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build sanitized source-native rows without copying source problem content."""

    source_fingerprints: dict[str, tuple[str | None, str | None]] = {}
    for record in source_records:
        if "problem_idx" not in record:
            raise ProvenanceError(f"{benchmark} source row lacks problem_idx")
        question_id = str(record["problem_idx"])
        if question_id in source_fingerprints:
            raise ProvenanceError(
                f"{benchmark} source archive repeats question {question_id}"
            )
        source_fingerprints[question_id] = (
            _content_fingerprint(record.get("problem")),
            _content_fingerprint(record.get("answer")),
        )
    source_ids = set(source_fingerprints)
    if not source_fingerprints:
        raise ProvenanceError(f"{benchmark} source archive has no questions")

    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for record in output_records:
        if "problem_idx" not in record or "model_name" not in record:
            raise ProvenanceError(
                f"{benchmark} output row lacks problem_idx or model_name"
            )
        question_id = str(record["problem_idx"])
        if question_id not in source_ids:
            raise ProvenanceError(
                f"{benchmark} output refers to unknown question {question_id}"
            )
        grouped[(str(record["model_name"]), question_id)].append(record)

    models = sorted({model for model, _ in grouped})
    if not models:
        raise ProvenanceError(f"{benchmark} output archive has no models")
    rows: list[dict[str, Any]] = []
    for model in models:
        for question_id in sorted(
            source_ids, key=lambda value: int(value) if value.isdigit() else value
        ):
            attempts = grouped.get((model, question_id), [])
            source_text, source_gold = source_fingerprints[question_id]
            if attempts:
                correct_values = [
                    _normalise_bool(record.get("correct")) for record in attempts
                ]
                if any(value is None for value in correct_values):
                    raise ProvenanceError(
                        f"{benchmark} {model} question {question_id} lacks source-native grade"
                    )
                output_text_fingerprints = {
                    fingerprint
                    for record in attempts
                    if (fingerprint := _content_fingerprint(record.get("problem")))
                    is not None
                }
                output_gold_fingerprints = {
                    fingerprint
                    for record in attempts
                    if (fingerprint := _content_fingerprint(record.get("gold_answer")))
                    is not None
                }
                prompt_fingerprints = {
                    fingerprint
                    for record in attempts
                    if (
                        fingerprint := _content_fingerprint(
                            record.get("user_message", record.get("problem"))
                        )
                    )
                    is not None
                }
                grade_count: int | None = int(
                    sum(bool(value) for value in correct_values)
                )
                accuracy: float | None = float(grade_count / len(attempts))
                grade_status = "available"
            else:
                output_text_fingerprints = set()
                output_gold_fingerprints = set()
                prompt_fingerprints = set()
                grade_count = None
                accuracy = None
                grade_status = "not_archived"
            token_summary = _output_token_summary(
                record.get("output_tokens") for record in attempts
            )
            rows.append(
                {
                    "schema_version": CAPABILITY_SCHEMA,
                    "benchmark": benchmark,
                    "model": model,
                    "question_id": question_id,
                    "source_question_available": True,
                    "archived_response_available": bool(attempts),
                    "attempt_count": len(attempts),
                    "source_native_correct_count": grade_count,
                    "source_native_accuracy": accuracy,
                    "source_native_grade_semantics": "MathArena archived correct field",
                    "source_native_grade_status": grade_status,
                    "source_output_text_match_status": _match_status(
                        source_text, output_text_fingerprints
                    ),
                    "source_output_gold_match_status": _match_status(
                        source_gold, output_gold_fingerprints
                    ),
                    "prompt_fingerprint_set_digest": _fingerprint_set_digest(
                        prompt_fingerprints
                    ),
                    "prompt_fingerprint_count": len(prompt_fingerprints),
                    **token_summary,
                    "requested_max_tokens": None,
                    "requested_cap_status": "not_published",
                    "finish_reason": None,
                    "termination_status": "not_published",
                    "censoring_status": "not_observed_in_archive",
                    "strict_marker_regrade_status": "not_applied",
                }
            )
    return rows


def _finish_reason(completion: Mapping[str, Any]) -> str | None:
    value = completion.get("finish_reason")
    if isinstance(value, Mapping):
        value = value.get("reason")
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ProvenanceError(f"HELM finish reason is not a string: {value!r}")
    return value


def build_helm_capability_rows(
    *,
    model: str,
    request_states: Iterable[Mapping[str, Any]],
    display_predictions: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build sanitized HELM GPQA rows.  Do not export plaintext GPQA content."""

    display_by_id: dict[str, Mapping[str, Any]] = {}
    for prediction in display_predictions:
        instance_id = prediction.get("instance_id")
        if not isinstance(instance_id, str) or instance_id in display_by_id:
            raise ProvenanceError(
                "HELM display predictions need unique string instance_id values"
            )
        display_by_id[instance_id] = prediction

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for state in request_states:
        instance = state.get("instance")
        request = state.get("request")
        result = state.get("result")
        if (
            not isinstance(instance, Mapping)
            or not isinstance(request, Mapping)
            or not isinstance(result, Mapping)
        ):
            raise ProvenanceError("HELM scenario state has malformed request state")
        instance_id = instance.get("id")
        if not isinstance(instance_id, str) or instance_id in seen_ids:
            raise ProvenanceError("HELM request states need unique string instance ids")
        prediction = display_by_id.get(instance_id)
        if prediction is None:
            raise ProvenanceError(
                f"HELM request {instance_id} has no display prediction"
            )
        completions = result.get("completions")
        if (
            not isinstance(completions, list)
            or len(completions) != 1
            or not isinstance(completions[0], Mapping)
        ):
            raise ProvenanceError(
                f"HELM request {instance_id} must have one completion"
            )
        max_tokens = request.get("max_tokens")
        if (
            not isinstance(max_tokens, int)
            or isinstance(max_tokens, bool)
            or max_tokens <= 0
        ):
            raise ProvenanceError(
                f"HELM request {instance_id} lacks a positive integer max_tokens"
            )
        stats = prediction.get("stats")
        if not isinstance(stats, Mapping):
            raise ProvenanceError(f"HELM display prediction {instance_id} lacks stats")
        correct = _normalise_bool(stats.get("chain_of_thought_correctness"))
        if correct is None:
            raise ProvenanceError(
                f"HELM display prediction {instance_id} lacks source-native correctness"
            )
        output_tokens = stats.get("num_output_tokens")
        finish = _finish_reason(completions[0])
        rows.append(
            {
                "schema_version": CAPABILITY_SCHEMA,
                "benchmark": "helm_gpqa_main_cot_v1.15.0",
                "model": model,
                "question_id": instance_id,
                "source_question_available": True,
                "archived_response_available": True,
                "attempt_count": 1,
                "source_native_correct_count": int(bool(correct)),
                "source_native_accuracy": float(bool(correct)),
                "source_native_grade_semantics": "HELM chain_of_thought_correctness",
                "source_native_grade_status": "available",
                "source_output_text_match_status": "not_compared_restricted_source",
                "source_output_gold_match_status": "not_compared_restricted_source",
                "prompt_fingerprint_set_digest": None,
                "prompt_fingerprint_count": 0,
                **_output_token_summary([output_tokens]),
                "requested_max_tokens": max_tokens,
                "requested_cap_status": "available",
                "finish_reason": finish,
                "termination_status": "observed"
                if finish is not None
                else "not_published",
                "censoring_status": "observed_length"
                if finish == "length"
                else "unknown"
                if finish is None
                else "observed_nonlength",
                "strict_marker_regrade_status": "not_available_archived_output_is_not_plaintext",
            }
        )
        seen_ids.add(instance_id)
    if seen_ids != set(display_by_id):
        unexpected = sorted(set(display_by_id) - seen_ids)
        raise ProvenanceError(
            f"HELM display predictions have no matching request state: {unexpected[:3]}"
        )
    return rows


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProvenanceError(f"source JSON is invalid: {path}") from exc


def _pandas_records(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ProvenanceError(
            "import_failed: pandas with parquet support is required"
        ) from exc
    try:
        return pd.read_parquet(path).to_dict(orient="records")
    except Exception as exc:  # pandas reports parquet backend details
        raise ProvenanceError(f"could not read parquet {path}: {exc}") from exc


def _parse_helm_gpqa_contract(
    archive_path: Path, scenario_source: str, gpqa_readme: str
) -> dict[str, Any]:
    """Read only GPQA row count; never return or print restricted CSV contents."""

    try:
        tree = parse(scenario_source)
    except SyntaxError as exc:
        raise ProvenanceError(
            "pinned HELM GPQA scenario source is not parseable"
        ) from exc
    train_indices: list[int] | None = None
    for node in tree.body:
        if isinstance(node, Assign) and any(
            isinstance(target, Name) and target.id == "TRAIN_EXAMPLE_INDICES"
            for target in node.targets
        ):
            try:
                mapping = literal_eval(node.value)
            except ValueError as exc:
                raise ProvenanceError(
                    "HELM train-index mapping is not a literal"
                ) from exc
            indices = mapping.get("gpqa_main") if isinstance(mapping, dict) else None
            if not isinstance(indices, list) or not all(
                isinstance(value, int) for value in indices
            ):
                raise ProvenanceError("HELM GPQA main train indices are malformed")
            train_indices = sorted(indices)
            break
    revision_match = _GPQA_HF_REVISION.search(scenario_source)
    if train_indices is None or revision_match is None:
        raise ProvenanceError(
            "HELM GPQA scenario lacks train indices or pinned Hugging Face revision"
        )
    password_match = _GPQA_PASSWORD.search(gpqa_readme)
    if password_match is None:
        raise ProvenanceError(
            "pinned GPQA README does not provide the archive password"
        )
    try:
        with zipfile.ZipFile(archive_path) as archive:
            raw = archive.read(
                "dataset/gpqa_main.csv", pwd=password_match.group(1).encode("utf-8")
            )
    except (KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ProvenanceError("could not read pinned restricted GPQA main CSV") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProvenanceError("restricted GPQA main CSV is not UTF-8") from exc
    # Parse solely to count CSV records.  No row content escapes this function.
    csv_reader = reader(StringIO(text))
    try:
        next(csv_reader)
    except StopIteration as exc:
        raise ProvenanceError("restricted GPQA main CSV has no header") from exc
    source_row_count = sum(1 for _ in csv_reader)
    if any(index < 0 or index >= source_row_count for index in train_indices):
        raise ProvenanceError("HELM GPQA train indices fall outside pinned source rows")
    return {
        "source_row_count": source_row_count,
        "train_indices": train_indices,
        "hf_revision": revision_match.group(1),
    }


def _validate_helm_release_manifest(release: Any, model_keys: Sequence[str]) -> None:
    if not isinstance(release, Mapping):
        raise ProvenanceError("HELM release manifest must be an object")
    prefix = "gpqa:subset=gpqa_main,use_chain_of_thought=true,use_few_shot=false,model="
    for model_key in model_keys:
        if release.get(prefix + model_key) != "v1.15.0":
            raise ProvenanceError(
                f"HELM release manifest does not map {model_key} to v1.15.0"
            )


def build_capability_table(
    manifest: Mapping[str, Any], root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify all bytes and derive a deterministic, sanitized capability table."""

    verify_download_root(manifest, root)
    entries = {entry["source_id"]: entry for entry in manifest["entries"]}

    def path(source_id: str) -> Path:
        try:
            return _source_path(root, entries[source_id]["path"])
        except KeyError as exc:
            raise ProvenanceError(
                f"manifest lacks required source {source_id}"
            ) from exc

    all_rows: list[dict[str, Any]] = []
    source_question_counts: dict[str, int] = {}
    for year in ("2025", "2026"):
        benchmark = f"hmmt_feb_{year}"
        source_records = _pandas_records(path(f"{benchmark}-source-parquet"))
        output_records = _pandas_records(path(f"{benchmark}-outputs-parquet"))
        source_question_counts[benchmark] = len(source_records)
        all_rows.extend(
            build_matharena_capability_rows(
                benchmark=benchmark,
                source_records=source_records,
                output_records=output_records,
            )
        )

    helm_models = (
        ("google_gemini-3-pro-preview", "google_gemini-3-pro-preview"),
        ("anthropic_claude-haiku-4-5-20251001", "anthropic_claude-haiku-4-5-20251001"),
        ("openai_gpt-5.1-2025-11-13", "openai_gpt-5.1-2025-11-13"),
    )
    contract = _parse_helm_gpqa_contract(
        path("gpqa-main-source-archive"),
        path("helm-gpqa-scenario-code").read_text(encoding="utf-8"),
        path("gpqa-readme").read_text(encoding="utf-8"),
    )
    _validate_helm_release_manifest(
        _read_json(path("helm-release-manifest")),
        [model_key for model_key, _ in helm_models],
    )
    expected_helm_ids = {
        f"id{index}"
        for index in range(contract["source_row_count"])
        if index not in set(contract["train_indices"])
    }
    for model_key, model_name in helm_models:
        scenario = _read_json(path(f"helm-{model_key}-scenario"))
        display = _read_json(path(f"helm-{model_key}-display"))
        if not isinstance(scenario, Mapping) or not isinstance(
            scenario.get("request_states"), list
        ):
            raise ProvenanceError(f"HELM scenario state is malformed for {model_name}")
        if not isinstance(display, list):
            raise ProvenanceError(
                f"HELM display predictions are malformed for {model_name}"
            )
        helm_rows = build_helm_capability_rows(
            model=model_name,
            request_states=scenario["request_states"],
            display_predictions=display,
        )
        observed_ids = {row["question_id"] for row in helm_rows}
        if observed_ids != expected_helm_ids:
            raise ProvenanceError(
                f"HELM request ids for {model_name} do not equal the pinned GPQA test split"
            )
        source_question_counts["helm_gpqa_main_cot_v1.15.0"] = contract[
            "source_row_count"
        ]
        all_rows.extend(helm_rows)

    all_rows.sort(key=lambda row: (row["benchmark"], row["model"], row["question_id"]))
    summary = summarize_capability_rows(all_rows, source_question_counts)
    summary["helm_gpqa_contract"] = {
        **contract,
        "evaluated_question_count": len(expected_helm_ids),
        "release_version": "v1.15.0",
    }
    return all_rows, summary


def summarize_capability_rows(
    rows: Sequence[Mapping[str, Any]],
    source_question_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["benchmark"])].append(row)
    benchmarks: list[dict[str, Any]] = []
    for benchmark, group in sorted(grouped.items()):
        question_ids = {str(row["question_id"]) for row in group}
        models = {str(row["model"]) for row in group}
        observed_termination = sum(
            row.get("termination_status") == "observed" for row in group
        )
        benchmark_summary = {
            "benchmark": benchmark,
            "source_question_count": (
                source_question_counts.get(benchmark, len(question_ids))
                if source_question_counts
                else len(question_ids)
            ),
            "archived_question_count": len(question_ids),
            "model_count": len(models),
            "question_by_model_rows": len(group),
            "expected_question_by_model_rows": len(question_ids) * len(models),
            "unmaterialized_question_by_model_rows": len(question_ids) * len(models)
            - len(group),
            "archived_response_missing_rows": sum(
                not bool(row.get("archived_response_available")) for row in group
            ),
            "source_native_correctness_rows": sum(
                row.get("source_native_correct_count") is not None for row in group
            ),
            "output_token_rows": sum(
                bool(row.get("output_tokens_available")) for row in group
            ),
            "output_token_unusable_rows": sum(
                not bool(row.get("output_tokens_available")) for row in group
            ),
            "output_token_invalid_values": sum(
                int(row.get("output_tokens_invalid_count", 0)) for row in group
            ),
            "output_token_zero_values": sum(
                int(row.get("output_tokens_zero_count", 0)) for row in group
            ),
            "output_token_negative_values": sum(
                int(row.get("output_tokens_negative_count", 0)) for row in group
            ),
            "output_token_nonfinite_values": sum(
                int(row.get("output_tokens_nonfinite_count", 0)) for row in group
            ),
            "requested_cap_rows": sum(
                row.get("requested_cap_status") == "available" for row in group
            ),
            "termination_observed_rows": observed_termination,
            "termination_not_published_rows": len(group) - observed_termination,
            "strict_marker_regrade_statuses": sorted(
                {str(row["strict_marker_regrade_status"]) for row in group}
            ),
            "source_output_text_match_rows": sum(
                row.get("source_output_text_match_status") == "matches_source"
                for row in group
            ),
            "source_output_text_mismatch_rows": sum(
                row.get("source_output_text_match_status") == "mismatch_source"
                for row in group
            ),
            "source_output_text_mismatch_attempts": sum(
                int(row.get("attempt_count", 0))
                for row in group
                if row.get("source_output_text_match_status") == "mismatch_source"
            ),
            "source_output_gold_match_rows": sum(
                row.get("source_output_gold_match_status") == "matches_source"
                for row in group
            ),
            "source_output_gold_mismatch_rows": sum(
                row.get("source_output_gold_match_status") == "mismatch_source"
                for row in group
            ),
            "prompt_fingerprint_variant_rows": sum(
                int(row.get("prompt_fingerprint_count", 0)) > 1 for row in group
            ),
        }
        if benchmark == "helm_gpqa_main_cot_v1.15.0":
            benchmark_summary["source_rows_excluded_by_pinned_helm_split"] = 2
        benchmarks.append(benchmark_summary)
    ordered_rows = sorted(
        rows,
        key=lambda row: (
            str(row["benchmark"]),
            str(row["model"]),
            str(row["question_id"]),
        ),
    )
    table_bytes = "".join(_canonical_json(row) + "\n" for row in ordered_rows).encode(
        "utf-8"
    )
    return {
        "schema_version": SUMMARY_SCHEMA,
        "row_schema_version": CAPABILITY_SCHEMA,
        "privacy": {
            "raw_question_text": "excluded",
            "gold_answers": "excluded",
            "model_responses": "excluded",
            "gpqa_content": "excluded",
        },
        "benchmarks": benchmarks,
        "integrity": {
            "capability_rows_sha256": hashlib.sha256(table_bytes).hexdigest()
        },
    }


def _validate_output_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        fields = set(row)
        if fields != _CAPABILITY_FIELDS:
            missing = sorted(_CAPABILITY_FIELDS - fields)
            extra = sorted(fields - _CAPABILITY_FIELDS)
            raise ProvenanceError(
                f"capability row {index} must use exact schema; missing={missing}, extra={extra}"
            )
        if row.get("schema_version") != CAPABILITY_SCHEMA:
            raise ProvenanceError(f"capability row {index} has wrong schema version")
        if (
            not isinstance(row["benchmark"], str)
            or not isinstance(row["model"], str)
            or not isinstance(row["question_id"], str)
        ):
            raise ProvenanceError(f"capability row {index} has invalid identity fields")
        if not isinstance(row["attempt_count"], int) or row["attempt_count"] < 0:
            raise ProvenanceError(f"capability row {index} has invalid attempt count")
        for field in (
            "source_question_available",
            "archived_response_available",
            "output_tokens_available",
        ):
            if not isinstance(row[field], bool):
                raise ProvenanceError(f"capability row {index} has non-boolean {field}")
        for field in (
            "source_native_grade_semantics",
            "source_native_grade_status",
            "source_output_text_match_status",
            "source_output_gold_match_status",
            "output_tokens_status",
            "requested_cap_status",
            "termination_status",
            "censoring_status",
            "strict_marker_regrade_status",
        ):
            if not isinstance(row[field], str):
                raise ProvenanceError(f"capability row {index} has non-string {field}")
        allowed_statuses = {
            "source_native_grade_semantics": {
                "MathArena archived correct field",
                "HELM chain_of_thought_correctness",
            },
            "source_output_text_match_status": {
                "matches_source",
                "mismatch_source",
                "not_comparable",
                "not_compared_restricted_source",
            },
            "source_output_gold_match_status": {
                "matches_source",
                "mismatch_source",
                "not_comparable",
                "not_compared_restricted_source",
            },
            "requested_cap_status": {"available", "not_published"},
            "termination_status": {"observed", "not_published"},
            "censoring_status": {
                "observed_length",
                "observed_nonlength",
                "unknown",
                "not_observed_in_archive",
            },
            "strict_marker_regrade_status": {
                "not_applied",
                "not_available_archived_output_is_not_plaintext",
            },
        }
        for field, allowed in allowed_statuses.items():
            if row[field] not in allowed:
                raise ProvenanceError(f"capability row {index} has unsupported {field}")
        for field in (
            "output_tokens_invalid_count",
            "output_tokens_zero_count",
            "output_tokens_negative_count",
            "output_tokens_nonfinite_count",
            "prompt_fingerprint_count",
        ):
            if not isinstance(row[field], int) or row[field] < 0:
                raise ProvenanceError(f"capability row {index} has invalid {field}")
        digest = row["prompt_fingerprint_set_digest"]
        if digest is not None and (
            not isinstance(digest, str) or not _SHA256.fullmatch(digest)
        ):
            raise ProvenanceError(
                f"capability row {index} has invalid prompt_fingerprint_set_digest"
            )
        if (row["prompt_fingerprint_count"] == 0) != (digest is None):
            raise ProvenanceError(
                f"capability row {index} has inconsistent prompt fingerprint count/digest"
            )
        if row["archived_response_available"] != (row["attempt_count"] > 0):
            raise ProvenanceError(
                f"capability row {index} violates archived response invariants"
            )
        if row["source_native_correct_count"] is not None and (
            not isinstance(row["source_native_correct_count"], int)
            or row["source_native_correct_count"] < 0
        ):
            raise ProvenanceError(f"capability row {index} has invalid correct count")
        for field in ("output_tokens_mean", "source_native_accuracy"):
            value = row[field]
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ProvenanceError(f"capability row {index} has invalid {field}")
        if row["output_tokens_mean"] is not None and row["output_tokens_mean"] <= 0:
            raise ProvenanceError(
                f"capability row {index} has non-positive usable output tokens"
            )
        if (
            row["source_native_accuracy"] is not None
            and not 0 <= row["source_native_accuracy"] <= 1
        ):
            raise ProvenanceError(
                f"capability row {index} has out-of-range source-native accuracy"
            )
        if row["source_native_grade_status"] == "available":
            if (
                not row["archived_response_available"]
                or row["source_native_correct_count"] is None
                or row["source_native_accuracy"] is None
                or row["source_native_correct_count"] > row["attempt_count"]
                or not math.isclose(
                    row["source_native_accuracy"],
                    row["source_native_correct_count"] / row["attempt_count"],
                )
            ):
                raise ProvenanceError(
                    f"capability row {index} violates source-native grade invariants"
                )
        elif row["source_native_grade_status"] == "not_archived":
            if (
                row["archived_response_available"]
                or row["source_native_correct_count"] is not None
                or row["source_native_accuracy"] is not None
            ):
                raise ProvenanceError(
                    f"capability row {index} violates source-native grade invariants"
                )
        else:
            raise ProvenanceError(
                f"capability row {index} has unknown source-native grade status"
            )
        invalid_subcount = (
            row["output_tokens_zero_count"]
            + row["output_tokens_negative_count"]
            + row["output_tokens_nonfinite_count"]
        )
        if invalid_subcount != row["output_tokens_invalid_count"]:
            raise ProvenanceError(
                f"capability row {index} has inconsistent output invalid subcounts"
            )
        output_status = row["output_tokens_status"]
        allowed_output_statuses = {
            "available",
            "partial_invalid_values",
            "not_published",
            "zero_values_only",
            "negative_values_only",
            "nonfinite_values_only",
            "invalid_values_only",
        }
        unavailable_output_statuses = allowed_output_statuses - {
            "available",
            "partial_invalid_values",
        }
        if output_status not in allowed_output_statuses:
            raise ProvenanceError(
                f"capability row {index} has unsupported output-token status"
            )
        if row["output_tokens_available"]:
            if row["output_tokens_mean"] is None or output_status not in {
                "available",
                "partial_invalid_values",
            }:
                raise ProvenanceError(
                    f"capability row {index} violates usable output-token invariants"
                )
            if (output_status == "available") != (invalid_subcount == 0):
                raise ProvenanceError(
                    f"capability row {index} has inconsistent output-token status"
                )
        elif output_status not in unavailable_output_statuses:
            raise ProvenanceError(
                f"capability row {index} has unsupported output-token status"
            )
        elif row["output_tokens_mean"] is not None:
            raise ProvenanceError(
                f"capability row {index} has mean without usable output tokens"
            )
        elif output_status == "zero_values_only" and not (
            row["output_tokens_zero_count"] > 0
            and invalid_subcount == row["output_tokens_zero_count"]
        ):
            raise ProvenanceError(
                f"capability row {index} has inconsistent zero-token status"
            )
        elif output_status == "not_published" and invalid_subcount != 0:
            raise ProvenanceError(
                f"capability row {index} has inconsistent unreported-token status"
            )
        elif output_status == "negative_values_only" and not (
            row["output_tokens_negative_count"] > 0
            and invalid_subcount == row["output_tokens_negative_count"]
        ):
            raise ProvenanceError(
                f"capability row {index} has inconsistent negative-token status"
            )
        elif output_status == "nonfinite_values_only" and not (
            row["output_tokens_nonfinite_count"] > 0
            and invalid_subcount == row["output_tokens_nonfinite_count"]
        ):
            raise ProvenanceError(
                f"capability row {index} has inconsistent nonfinite-token status"
            )
        elif output_status == "invalid_values_only" and not (
            invalid_subcount > 0
            and sum(
                count > 0
                for count in (
                    row["output_tokens_zero_count"],
                    row["output_tokens_negative_count"],
                    row["output_tokens_nonfinite_count"],
                )
            )
            > 1
        ):
            raise ProvenanceError(
                f"capability row {index} has inconsistent invalid-token status"
            )
        if row["requested_max_tokens"] is not None and (
            isinstance(row["requested_max_tokens"], bool)
            or not isinstance(row["requested_max_tokens"], int)
            or row["requested_max_tokens"] <= 0
        ):
            raise ProvenanceError(
                f"capability row {index} has invalid requested_max_tokens"
            )
        for field in ("prompt_fingerprint_set_digest", "finish_reason"):
            if row[field] is not None and not isinstance(row[field], str):
                raise ProvenanceError(f"capability row {index} has invalid {field}")
        if row["finish_reason"] not in {None, "length", "stop"}:
            raise ProvenanceError(
                f"capability row {index} has unsupported finish_reason"
            )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_capability_outputs(
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    table_path: Path,
    summary_path: Path,
) -> None:
    _validate_output_rows(rows)
    if summary.get("schema_version") != SUMMARY_SCHEMA:
        raise ProvenanceError("capability summary has wrong schema version")
    ordered_rows = sorted(
        rows,
        key=lambda row: (
            str(row["benchmark"]),
            str(row["model"]),
            str(row["question_id"]),
        ),
    )
    table_text = "".join(_canonical_json(row) + "\n" for row in ordered_rows)
    _atomic_write(table_path, table_text)
    _atomic_write(summary_path, _canonical_json(summary) + "\n")
