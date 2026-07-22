"""Export deterministic, metadata-only evidence bundles for publication.

Raw result rows contain prompts, answers, model responses, reasoning traces,
and unstructured errors. Raw OpenRouter receipts also contain account and
client metadata. This module uses explicit allowlists and never copies unknown
fields into a public bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from . import ROOT


SCHEMA_VERSION = "public-artifact-v1"
_BUNDLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

_RESULT_FIELDS = (
    "item_id",
    "domain",
    "effort",
    "seed",
    "max_tokens_requested",
    "correct",
    "completion_tokens",
    "reasoning_tokens",
    "prompt_tokens",
    "latency_s",
    "cached",
    "mock",
    "model",
    "effort_mode",
    "finish_reason",
    "served_provider",
    "generation_id",
    "reported_cost_usd",
)

_SCHEDULE_FIELDS = (
    "schedule_index",
    "job_id",
    "panel_id",
    "phase",
    "item_id",
    "model",
    "requested_provider",
    "effort",
    "max_tokens_requested",
    "replicate",
    "seed",
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_source(workspace: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute():
        raise ValueError(f"source paths must be workspace-relative: {relative_path}")
    resolved = (workspace / relative_path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise ValueError(
            f"source paths must remain inside the workspace: {relative_path}"
        ) from exc
    if not resolved.is_file():
        raise FileNotFoundError(relative_path)
    return resolved


def _read_jsonl(path: Path) -> tuple[bytes, list[dict]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"JSONL is not UTF-8: {path}") from exc
    rows: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line at {path}:{line_number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"expected a JSON object at {path}:{line_number}")
        rows.append(row)
    return raw, rows


def _source_metadata(
    *, role: str, source_id: str, relative_path: Path, raw: bytes, line_count: int
) -> dict:
    return {
        "source_id": source_id,
        "role": role,
        "path": relative_path.as_posix(),
        "bytes": len(raw),
        "line_count": line_count,
        "sha256": _sha256(raw),
    }


def _public_result(source_id: str, source_line: int, row: dict) -> dict:
    public = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "source_line": source_line,
    }
    public.update({field: row.get(field) for field in _RESULT_FIELDS})
    public["error_present"] = "error" in row and row.get("error") is not None
    extracted = row.get("extracted")
    public["extracted_answer_present"] = extracted is not None and extracted != ""
    return public


def _first_provider_response(data: dict) -> dict:
    responses = data.get("provider_responses")
    if not isinstance(responses, list) or not responses:
        return {}
    response = responses[0]
    return response if isinstance(response, dict) else {}


def _public_receipt(source_id: str, source_line: int, row: dict) -> dict:
    response = row.get("openrouter_response")
    data = response.get("data", {}) if isinstance(response, dict) else {}
    if not isinstance(data, dict):
        data = {}
    provider_response = _first_provider_response(data)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "source_line": source_line,
        "item_id": row.get("item_id"),
        "effort": row.get("effort"),
        "max_tokens_requested": row.get("max_tokens_requested"),
        "generation_id": row.get("generation_id"),
        "receipt_generation_id": data.get("id"),
        "request_id": data.get("request_id"),
        "upstream_id": data.get("upstream_id"),
        "provider_response_id": provider_response.get("id"),
        "endpoint_id": provider_response.get("endpoint_id"),
        "created_at": data.get("created_at"),
        "fetched_at": row.get("fetched_at"),
        "api_type": data.get("api_type"),
        "data_region": data.get("data_region"),
        "model": data.get("model"),
        "provider_name": data.get("provider_name"),
        "provider_response_name": provider_response.get("provider_name"),
        "model_permaslug": provider_response.get("model_permaslug"),
        "provider_response_status": provider_response.get("status"),
        "gateway_finish_reason": data.get("finish_reason"),
        "native_finish_reason": data.get("native_finish_reason"),
        "normalized_prompt_tokens": data.get("tokens_prompt"),
        "normalized_completion_tokens": data.get("tokens_completion"),
        "native_prompt_tokens": data.get("native_tokens_prompt"),
        "native_completion_tokens": data.get("native_tokens_completion"),
        "native_reasoning_tokens": data.get("native_tokens_reasoning"),
        "native_cached_tokens": data.get("native_tokens_cached"),
        "receipt_latency": data.get("latency"),
        "generation_time": data.get("generation_time"),
        "streamed": data.get("streamed"),
        "receipt_total_cost_usd": data.get("total_cost"),
        "upstream_inference_cost_usd": data.get("upstream_inference_cost"),
    }


def _public_schedule(source_id: str, source_line: int, row: dict) -> dict:
    public = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "source_line": source_line,
    }
    public.update({field: row.get(field) for field in _SCHEDULE_FIELDS})
    return public


def _jsonl_bytes(rows: Iterable[dict]) -> bytes:
    text = "".join(_canonical_json(row) + "\n" for row in rows)
    return text.encode("utf-8")


def _json_bytes(value: object) -> bytes:
    return (_canonical_json(value) + "\n").encode("utf-8")


def export_bundle(
    *,
    workspace: Path,
    output_root: Path,
    bundle_id: str,
    result_paths: list[Path],
    receipt_paths: list[Path],
    dataset_paths: list[Path],
    code_commit: str,
    schedule_paths: list[Path] | None = None,
    config_paths: list[Path] | None = None,
) -> Path:
    """Create a deterministic metadata-only artifact bundle.

    Input order and physical one-based line order are preserved. Rows are not
    deduplicated, reconciled, repaired, or inferred.
    """

    workspace = workspace.resolve()
    output_root = output_root.resolve()
    if not _BUNDLE_ID.fullmatch(bundle_id):
        raise ValueError(f"invalid bundle ID: {bundle_id!r}")
    if not _COMMIT.fullmatch(code_commit):
        raise ValueError("code_commit must be a full lowercase 40-character SHA-1")
    try:
        output_root.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("output_root must remain inside the workspace") from exc
    destination = output_root / bundle_id
    if destination.exists():
        raise FileExistsError(f"output bundle already exists: {destination}")

    schedule_paths = schedule_paths or []
    config_paths = config_paths or []
    sources: list[dict] = []
    public_results: list[dict] = []
    public_receipts: list[dict] = []
    public_schedule: list[dict] = []
    public_datasets: list[dict] = []

    def load_sources(role: str, paths: list[Path]) -> list[tuple[str, Path, bytes, list[dict]]]:
        loaded: list[tuple[str, Path, bytes, list[dict]]] = []
        for index, relative_path in enumerate(paths, start=1):
            if not isinstance(relative_path, Path):
                relative_path = Path(relative_path)
            source_id = f"{role}-{index:04d}"
            resolved = _resolve_source(workspace, relative_path)
            raw, rows = _read_jsonl(resolved)
            sources.append(
                _source_metadata(
                    role=role,
                    source_id=source_id,
                    relative_path=relative_path,
                    raw=raw,
                    line_count=len(rows),
                )
            )
            loaded.append((source_id, relative_path, raw, rows))
        return loaded

    def load_blob_sources(role: str, paths: list[Path]) -> None:
        for index, relative_path in enumerate(paths, start=1):
            if not isinstance(relative_path, Path):
                relative_path = Path(relative_path)
            source_id = f"{role}-{index:04d}"
            resolved = _resolve_source(workspace, relative_path)
            raw = resolved.read_bytes()
            sources.append(
                _source_metadata(
                    role=role,
                    source_id=source_id,
                    relative_path=relative_path,
                    raw=raw,
                    line_count=len(raw.splitlines()),
                )
            )

    for source_id, _, _, rows in load_sources("result", result_paths):
        public_results.extend(
            _public_result(source_id, line_number, row)
            for line_number, row in enumerate(rows, start=1)
        )
    for source_id, _, _, rows in load_sources("receipt", receipt_paths):
        public_receipts.extend(
            _public_receipt(source_id, line_number, row)
            for line_number, row in enumerate(rows, start=1)
        )
    for source_id, _, _, rows in load_sources("schedule", schedule_paths):
        public_schedule.extend(
            _public_schedule(source_id, line_number, row)
            for line_number, row in enumerate(rows, start=1)
        )
    for source_id, relative_path, raw, rows in load_sources("dataset", dataset_paths):
        public_datasets.append(
            {
                "source_id": source_id,
                "path": relative_path.as_posix(),
                "bytes": len(raw),
                "line_count": len(rows),
                "sha256": _sha256(raw),
            }
        )
    load_blob_sources("config", config_paths)

    emitted = {
        "results.jsonl": _jsonl_bytes(public_results),
        "receipts.jsonl": _jsonl_bytes(public_receipts),
        "schedule.jsonl": _jsonl_bytes(public_schedule),
        "dataset_manifest.json": _json_bytes(
            {"schema_version": SCHEMA_VERSION, "datasets": public_datasets}
        ),
    }
    outputs = []
    for name, raw in emitted.items():
        if name.endswith(".jsonl"):
            record_count = len(raw.decode("utf-8").splitlines())
        else:
            record_count = len(public_datasets)
        outputs.append(
            {
                "path": name,
                "bytes": len(raw),
                "record_count": record_count,
                "sha256": _sha256(raw),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "code_commit": code_commit,
        "policies": {
            "source_order": "CLI input-list order, then physical one-based JSONL line order",
            "deduplication": "none",
            "repair": "none",
            "missing_values": "preserved as null; no inference or reconciliation",
            "raw_content": "prompts, labels, answers, responses, reasoning traces, and error messages excluded",
        },
        "sources": sources,
        "outputs": outputs,
    }
    emitted["manifest.json"] = _json_bytes(manifest)

    destination.mkdir(parents=True)
    for name, raw in emitted.items():
        (destination / name).write_bytes(raw)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a deterministic metadata-only public evidence bundle."
    )
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--output-root", default="public_artifacts")
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--results", nargs="*", default=[])
    parser.add_argument("--receipts", nargs="*", default=[])
    parser.add_argument("--schedules", nargs="*", default=[])
    parser.add_argument("--datasets", nargs="*", default=[])
    parser.add_argument("--configs", nargs="*", default=[])
    args = parser.parse_args()

    destination = export_bundle(
        workspace=ROOT,
        output_root=ROOT / args.output_root,
        bundle_id=args.bundle_id,
        result_paths=[Path(value) for value in args.results],
        receipt_paths=[Path(value) for value in args.receipts],
        schedule_paths=[Path(value) for value in args.schedules],
        dataset_paths=[Path(value) for value in args.datasets],
        config_paths=[Path(value) for value in args.configs],
        code_commit=args.code_commit,
    )
    print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
