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
import os
import re
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

MANIFEST_SCHEMA = "benchmark-source-manifest-v1"
CAPABILITY_SCHEMA = "benchmark-question-capability-v1"
SUMMARY_SCHEMA = "benchmark-question-capability-summary-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_ALLOWED_HOSTS = {
    "huggingface.co",
    "storage.googleapis.com",
    "raw.githubusercontent.com",
}
_FORBIDDEN_ROW_FIELDS = {
    "answer",
    "all_messages",
    "completion",
    "gold",
    "problem",
    "prompt",
    "response",
    "response_text",
    "user_message",
}


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
    if parsed.netloc == "huggingface.co" and "/resolve/" not in parsed.path:
        raise ProvenanceError(f"Hugging Face URL must pin a resolve revision: {url}")
    if parsed.netloc == "huggingface.co" and not _COMMIT.search(
        parsed.path.split("/resolve/", 1)[1].split("/", 1)[0]
    ):
        raise ProvenanceError(
            f"Hugging Face URL must use a 40-character revision: {url}"
        )
    if parsed.netloc == "raw.githubusercontent.com" and not _COMMIT.search(parsed.path):
        raise ProvenanceError(
            f"GitHub URL must contain a 40-character immutable commit: {url}"
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
        required = ("source_id", "role", "url", "path", "bytes", "sha256")
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


def build_matharena_capability_rows(
    *,
    benchmark: str,
    source_records: Iterable[Mapping[str, Any]],
    output_records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build sanitized source-native rows without copying source problem content."""

    source_text_fingerprints: dict[str, str | None] = {}
    for record in source_records:
        if "problem_idx" not in record:
            raise ProvenanceError(f"{benchmark} source row lacks problem_idx")
        question_id = str(record["problem_idx"])
        if question_id in source_text_fingerprints:
            raise ProvenanceError(
                f"{benchmark} source archive repeats question {question_id}"
            )
        source_text_fingerprints[question_id] = _content_fingerprint(
            record.get("problem")
        )
    source_ids = set(source_text_fingerprints)
    if not source_text_fingerprints:
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

    rows: list[dict[str, Any]] = []
    for (model, question_id), attempts in sorted(grouped.items()):
        correct_values = [_normalise_bool(record.get("correct")) for record in attempts]
        if any(value is None for value in correct_values):
            raise ProvenanceError(
                f"{benchmark} {model} question {question_id} lacks source-native grade"
            )
        output_tokens: list[int | float] = []
        invalid_output_token_count = 0
        output_text_fingerprints: set[str] = set()
        for record in attempts:
            value = record.get("output_tokens")
            if value is not None:
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or value < 0
                ):
                    invalid_output_token_count += 1
                else:
                    output_tokens.append(value)
            output_fingerprint = _content_fingerprint(record.get("problem"))
            if output_fingerprint is not None:
                output_text_fingerprints.add(output_fingerprint)
        source_fingerprint = source_text_fingerprints[question_id]
        if source_fingerprint is None or not output_text_fingerprints:
            text_match_status = "not_comparable"
        elif output_text_fingerprints == {source_fingerprint}:
            text_match_status = "matches_source"
        else:
            text_match_status = "mismatch_source"
        rows.append(
            {
                "schema_version": CAPABILITY_SCHEMA,
                "benchmark": benchmark,
                "model": model,
                "question_id": question_id,
                "source_question_available": True,
                "archived_response_available": True,
                "attempt_count": len(attempts),
                "source_native_correct_count": int(
                    sum(bool(value) for value in correct_values)
                ),
                "source_native_accuracy": float(
                    sum(bool(value) for value in correct_values) / len(attempts)
                ),
                "source_native_grade_semantics": "MathArena archived correct field",
                "source_output_text_match_status": text_match_status,
                "output_tokens_available": bool(output_tokens),
                "output_tokens_mean": _mean(output_tokens),
                "output_tokens_invalid_count": invalid_output_token_count,
                "output_tokens_status": (
                    "partial_invalid_values"
                    if invalid_output_token_count and output_tokens
                    else "invalid_values_only"
                    if invalid_output_token_count
                    else "available"
                    if output_tokens
                    else "not_published"
                ),
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
        output_tokens = stats.get("num_output_tokens")
        if output_tokens is not None and (
            not isinstance(output_tokens, (int, float))
            or isinstance(output_tokens, bool)
            or output_tokens < 0
        ):
            raise ProvenanceError(
                f"HELM output tokens are invalid for {instance_id}: {output_tokens!r}"
            )
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
                "source_output_text_match_status": "not_compared_restricted_source",
                "output_tokens_available": output_tokens is not None,
                "output_tokens_mean": float(output_tokens)
                if output_tokens is not None
                else None,
                "output_tokens_invalid_count": 0,
                "output_tokens_status": "available"
                if output_tokens is not None
                else "not_published",
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

    for model_key, model_name in (
        ("google_gemini-3-pro-preview", "google_gemini-3-pro-preview"),
        ("anthropic_claude-haiku-4-5-20251001", "anthropic_claude-haiku-4-5-20251001"),
        ("openai_gpt-5.1-2025-11-13", "openai_gpt-5.1-2025-11-13"),
    ):
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
        # HELM's pinned GPQA scenario marks two of the 448 source rows as train
        # examples, leaving the 446 published test requests in this run.
        source_question_counts["helm_gpqa_main_cot_v1.15.0"] = 448
        all_rows.extend(helm_rows)

    all_rows.sort(key=lambda row: (row["benchmark"], row["model"], row["question_id"]))
    summary = summarize_capability_rows(all_rows, source_question_counts)
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
            "missing_question_by_model_rows": len(question_ids) * len(models)
            - len(group),
            "source_native_correctness_rows": sum(
                row.get("source_native_correct_count") is not None for row in group
            ),
            "output_token_rows": sum(
                bool(row.get("output_tokens_available")) for row in group
            ),
            "output_token_invalid_values": sum(
                int(row.get("output_tokens_invalid_count", 0)) for row in group
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
        }
        if benchmark == "helm_gpqa_main_cot_v1.15.0":
            benchmark_summary["source_rows_excluded_by_pinned_helm_split"] = 2
        benchmarks.append(benchmark_summary)
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
    }


def _validate_output_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        forbidden = _FORBIDDEN_ROW_FIELDS & set(row)
        if forbidden:
            raise ProvenanceError(
                f"forbidden raw content field(s) in capability row {index}: {sorted(forbidden)}"
            )
        if row.get("schema_version") != CAPABILITY_SCHEMA:
            raise ProvenanceError(f"capability row {index} has wrong schema version")


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
