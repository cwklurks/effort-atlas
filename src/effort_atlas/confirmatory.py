"""Offline-only contracts for the preregistered confirmatory study.

This module deliberately does not import the API client.  It creates a
deterministic schedule, records execution attempts in an append-only ledger,
and summarizes only accounted, expected-route observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import fcntl

from . import ROOT, load_config


SCHEDULE_SEED = 20260722
LEDGER_VERSION = 1
EVENT_TYPES = frozenset({
    "success", "error", "unaccounted", "cache", "replay", "manual_rerun",
})
SENSITIVE_MARKERS = (
    "api_key", "apikey", "authorization", "secret", "password", "token",
    "credential", "cookie", "session", "private_key",
)
ACCOUNTING_KEYS = frozenset({
    "max_tokens", "max_tokens_requested", "prompt_tokens", "completion_tokens",
    "reasoning_tokens",
})
RESERVED_LEDGER_KEYS = frozenset({
    "ledger_version", "timestamp", "attempt_ordinal", "previous_event_sha256",
    "event_sha256",
})
LEDGER_GENESIS_SHA256 = "0" * 64
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?:\bbearer\s+|\bsk-(?:or-)?|\bapi[_-]?key\s*=|\btoken\s*=|\bauthorization\s*=)",
    re.IGNORECASE,
)
SCHEDULE_FIELDS = frozenset({
    "job_id", "schedule_ordinal", "panel", "model", "requested_provider",
    "provider_route", "item_id", "effort", "cap", "replicate", "phase",
    "domain", "item_block",
})
EVENT_FIELDS = SCHEDULE_FIELDS | frozenset({
    "event_type", "route_status", "accounting_status", "request_config",
    "served_provider", "generation_id", "receipt_generation_id", "receipt_cost_usd",
    "receipt_provider", "receipt_finish_reason",
    "native_prompt_tokens", "native_completion_tokens", "native_reasoning_tokens",
    "native_finish_reason", "prompt_tokens", "completion_tokens", "reasoning_tokens",
    "finish_reason", "correct", "reported_cost_usd", "error_class", "error_code",
    "max_tokens", "max_tokens_requested",
    "request_started_at", "request_ended_at", "request_id", "upstream_id",
    "provider_response_id", "endpoint_id", "receipt_created_at", "receipt_fetched_at",
    "cached", "replayed", "latency_s", "extracted_answer_present", "billed_status",
    "manual_rerun_reason",
})


class ReplicateDecisionRequired(ValueError):
    """Raised when a panel violates the preregistered one-replicate design."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sanitize_request_config(value: Any) -> Any:
    """Return a serializable config with credentials removed, recursively."""
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(str(key))
            else sanitize_request_config(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [sanitize_request_config(child) for child in value]
    if isinstance(value, tuple):
        return [sanitize_request_config(child) for child in value]
    if isinstance(value, str) and SENSITIVE_VALUE_PATTERN.search(value):
        return "[REDACTED]"
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in ACCOUNTING_KEYS:
        return False
    return any(marker in normalized for marker in SENSITIVE_MARKERS)


def _require_replicates(panel: dict[str, Any]) -> int:
    replicates = panel.get("replicates")
    if replicates != 1:
        raise ReplicateDecisionRequired(
            "This preregistration fixes one replicate; two require an amendment and budget top-up."
        )
    return int(replicates)


def build_schedule(panel: dict[str, Any], items: Iterable[dict[str, Any]], *, seed: int = SCHEDULE_SEED) -> dict[str, Any]:
    """Create the fixed item-block schedule and its digest without making calls."""
    replicates = _require_replicates(panel)
    required = ("name", "model", "requested_provider", "efforts", "caps")
    missing = [key for key in required if not panel.get(key)]
    if missing:
        raise ValueError(f"Panel missing required fields: {', '.join(missing)}")
    efforts, caps = list(panel["efforts"]), list(panel["caps"])
    if len(efforts) != 2 or len(caps) != 2:
        raise ValueError("Confirmatory panels require exactly two efforts and two caps.")
    item_rows = [{"item_id": str(row["id"] if "id" in row else row["item_id"]), "domain": row.get("domain", "math")} for row in items]
    if len({row["item_id"] for row in item_rows}) != len(item_rows):
        raise ValueError("Schedule items must have unique item ids.")

    rng = random.Random(seed)
    rng.shuffle(item_rows)
    jobs: list[dict[str, Any]] = []
    ordinal = 1
    for item_block, item in enumerate(item_rows, start=1):
        conditions = [(effort, cap) for effort in efforts for cap in caps]
        rng.shuffle(conditions)
        for replicate in range(1, replicates + 1):
            for effort, cap in conditions:
                identity = {
                    "panel": panel["name"], "model": panel["model"],
                    "requested_provider": panel["requested_provider"],
                    "provider_route": panel["requested_provider"],
                    "item_id": item["item_id"], "effort": effort, "cap": cap,
                    "replicate": replicate, "phase": "main",
                }
                jobs.append({
                    **identity, "domain": item["domain"], "schedule_ordinal": ordinal,
                    "item_block": item_block, "job_id": sha256_json(identity),
                })
                ordinal += 1
    unsigned = {"schedule_version": 1, "seed": seed, "panel": panel["name"], "jobs": jobs}
    return {**unsigned, "sha256": sha256_json(unsigned)}


def build_smoke_schedule(
    panel: dict[str, Any], items_by_id: dict[str, dict[str, Any]], smoke_jobs: Iterable[dict[str, Any]], *, seed: int = SCHEDULE_SEED,
) -> dict[str, Any]:
    """Build a distinct, deterministic operational smoke artifact with no prompts."""
    jobs: list[dict[str, Any]] = []
    for ordinal, spec in enumerate(smoke_jobs, start=1):
        item = items_by_id.get(str(spec["item_id"]))
        if item is None:
            raise ValueError(f"Smoke item is absent from audited datasets: {spec['item_id']}")
        identity = {
            "panel": panel["name"], "model": panel["model"],
            "requested_provider": panel["requested_provider"],
            "provider_route": panel["requested_provider"], "item_id": item["item_id"],
            "effort": spec["effort"], "cap": spec["cap"], "replicate": 1,
            "phase": "smoke",
        }
        jobs.append({
            **identity, "domain": item["domain"], "item_block": ordinal,
            "schedule_ordinal": ordinal, "job_id": sha256_json(identity),
        })
    unsigned = {"schedule_version": 1, "seed": seed, "panel": panel["name"], "phase": "smoke", "jobs": jobs}
    return {**unsigned, "sha256": sha256_json(unsigned)}


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audited_items(paths: Iterable[Path]) -> dict[str, dict[str, str]]:
    items: dict[str, dict[str, str]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                item_id = str(row["id"])
                if item_id in items:
                    raise ValueError(f"Duplicate audited item id: {item_id}")
                items[item_id] = {"item_id": item_id, "domain": str(row.get("domain", "math"))}
    return items


def export_schedule_artifacts(
    config_path: str | Path, output_dir: str | Path, *, exporter_code_commit: str,
) -> dict[str, Any]:
    """Export deterministic, prompt-free schedules; this function makes no calls."""
    if not re.fullmatch(r"[0-9a-f]{40}", exporter_code_commit):
        raise ValueError("exporter_code_commit must be a 40-character lowercase hexadecimal commit.")
    config_file = Path(config_path)
    if not config_file.is_absolute():
        config_file = ROOT / config_file
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing schedule artifact directory: {output}")
    cfg = load_config(config_file)
    study = cfg["study"]
    dataset_paths = [ROOT / value for value in study["audited_dataset_paths"]]
    all_items = _audited_items(dataset_paths)
    main_path = ROOT / study["main_dataset_path"]
    main_items = list(_audited_items([main_path]).values())
    if len(main_items) != int(study["main_item_count"]):
        raise ValueError("Audited main item count does not match config_confirmatory.yaml.")

    panels: dict[str, dict[str, str]] = {}
    rendered: dict[str, bytes] = {}
    for panel in cfg["panels"]:
        main = build_schedule(panel, main_items, seed=int(study["seed"]))
        smoke = build_smoke_schedule(
            panel, all_items, panel["smoke_jobs"], seed=int(study["seed"]),
        )
        main_file = f"{panel['name']}_main_schedule.json"
        smoke_file = f"{panel['name']}_smoke_schedule.json"
        rendered[main_file] = (canonical_json(main) + "\n").encode("utf-8")
        rendered[smoke_file] = (canonical_json(smoke) + "\n").encode("utf-8")
        panels[panel["name"]] = {
            "main_file": main_file, "main_schedule_sha256": main["sha256"],
            "main_file_sha256": hashlib.sha256(rendered[main_file]).hexdigest(),
            "smoke_file": smoke_file, "smoke_schedule_sha256": smoke["sha256"],
            "smoke_file_sha256": hashlib.sha256(rendered[smoke_file]).hexdigest(),
        }
    provenance_paths = [ROOT / value for value in study["code_provenance_paths"]]
    manifest = {
        "artifact_version": 1, "seed": int(study["seed"]),
        "preregistration_commit": study["preregistration_commit"],
        "preregistration_file_sha256": _hash_file(ROOT / study["preregistration_path"]),
        "exporter_code_commit": exporter_code_commit,
        "config_sha256": _hash_file(config_file),
        "dataset_sha256": {str(path.relative_to(ROOT)): _hash_file(path) for path in dataset_paths},
        "code_provenance_sha256": {
            str(path.relative_to(ROOT)): _hash_file(path) for path in provenance_paths
        },
        "panels": panels,
    }
    rendered["schedule_manifest.json"] = (canonical_json(manifest) + "\n").encode("utf-8")
    output.mkdir(parents=True)
    for filename, content in rendered.items():
        (output / filename).write_bytes(content)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Offline confirmatory schedule artifact exporter")
    parser.add_argument("--config", default="config_confirmatory.yaml")
    parser.add_argument("--output", required=True)
    parser.add_argument("--exporter-code-commit", required=True)
    args = parser.parse_args(argv)
    manifest = export_schedule_artifacts(
        args.config, args.output, exporter_code_commit=args.exporter_code_commit,
    )
    print(canonical_json(manifest))


if __name__ == "__main__":
    main()


class AttemptLedger:
    """Append-only JSONL attempt ledger; it contains no API or cache behavior."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        protected = RESERVED_LEDGER_KEYS.intersection(event)
        if protected:
            raise ValueError(f"Event cannot override reserved ledger fields: {sorted(protected)!r}")
        disallowed = [
            key for key in event
            if key not in EVENT_FIELDS and not _is_sensitive_key(str(key))
        ]
        if disallowed:
            raise ValueError(f"Event contains non-allowlisted fields: {sorted(disallowed)!r}")
        kind = event.get("event_type")
        if kind not in EVENT_TYPES:
            raise ValueError(f"Unknown event_type: {kind!r}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.seek(0)
                rows = [json.loads(line) for line in fh if line.strip()]
                previous = self._verify_rows(rows)
                ordinal = len(rows) + 1
                row = {
                    **sanitize_request_config(event),
                    "ledger_version": LEDGER_VERSION,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attempt_ordinal": ordinal,
                    "previous_event_sha256": previous,
                }
                row["request_config"] = sanitize_request_config(row.get("request_config", {}))
                row["event_sha256"] = sha256_json({
                    key: value for key, value in row.items() if key != "event_sha256"
                })
                fh.seek(0, 2)
                fh.write(canonical_json(row) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return row

    def verify(self) -> bool:
        """Verify ordinal continuity and the tamper-evident SHA-256 chain."""
        if not self.path.exists():
            return True
        with self.path.open(encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                self._verify_rows([json.loads(line) for line in fh if line.strip()])
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return True

    @staticmethod
    def _verify_rows(rows: list[dict[str, Any]]) -> str:
        previous = LEDGER_GENESIS_SHA256
        for ordinal, row in enumerate(rows, start=1):
            if row.get("attempt_ordinal") != ordinal or row.get("previous_event_sha256") != previous:
                raise ValueError("Ledger hash chain or ordinal verification failed.")
            expected = sha256_json({key: value for key, value in row.items() if key != "event_sha256"})
            if row.get("event_sha256") != expected:
                raise ValueError("Ledger hash chain or event hash verification failed.")
            previous = expected
        return previous


CELL_KEYS = ("panel", "model", "provider_route", "item_id", "effort", "cap", "replicate")
EFFORT_ORDER = {"minimal": 1, "low": 2, "medium": 3, "high": 4, "max": 5, "xhigh": 6}


def _ineligibility_reason(row: dict[str, Any]) -> str | None:
    if row.get("event_type") != "success":
        return "not_success"
    if row.get("accounting_status") != "valid" or row.get("route_status") != "expected":
        return "route_or_accounting_not_expected"
    if not row.get("provider_route") or row.get("served_provider") != row.get("requested_provider"):
        return "served_provider_mismatch"
    if not row.get("request_id"):
        return "request_id_invalid"
    if (
        not row.get("generation_id")
        or row.get("receipt_generation_id") != row.get("generation_id")
        or not _is_numeric(row.get("receipt_cost_usd"))
        or row["receipt_cost_usd"] < 0
    ):
        return "receipt_linkage_invalid"
    if row.get("receipt_provider") != row.get("requested_provider") or row.get("receipt_provider") != row.get("served_provider"):
        return "receipt_provider_mismatch"
    if _normalize_finish_reason(row.get("receipt_finish_reason")) != _normalize_finish_reason(row.get("finish_reason")):
        return "receipt_finish_reason_invalid"
    if not _is_positive_int(row.get("native_completion_tokens")) or not _is_positive_int(row.get("native_prompt_tokens")):
        return "native_usage_invalid"
    if not _is_positive_int(row.get("cap")) or row["native_completion_tokens"] > row["cap"]:
        return "native_cap_exceeded"
    if not row.get("native_finish_reason"):
        return "native_finish_reason_invalid"
    if not _is_positive_int(row.get("completion_tokens")) or not _is_positive_int(row.get("prompt_tokens")) or not row.get("finish_reason"):
        return "terminal_usage_invalid"
    if any(
        key in row and not _is_nonnegative_int(row[key])
        for key in ("reasoning_tokens", "native_reasoning_tokens")
    ):
        return "reasoning_tokens_invalid"
    if type(row.get("correct")) is not bool:
        return "malformed_correct"
    return None


def _normalize_finish_reason(value: object) -> str:
    """Normalize public finish-reason vocabulary for receipt reconciliation."""
    normalized = str(value or "").strip().lower()
    return {"completed": "stop", "complete": "stop"}.get(normalized, normalized)


def _is_positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _is_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_numeric(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def analyze_confirmatory_events(
    events: Iterable[dict[str, Any]], schedule: dict[str, Any],
) -> dict[str, Any]:
    """Report the 2x2 cells and cap-by-effort interaction without cap deduping."""
    unsigned_schedule = {key: value for key, value in schedule.items() if key != "sha256"}
    if schedule.get("sha256") != sha256_json(unsigned_schedule):
        raise ValueError("Schedule SHA-256 does not match its contents.")
    scheduled = {job.get("job_id"): job for job in schedule.get("jobs", [])}
    if len(scheduled) != len(schedule.get("jobs", [])) or None in scheduled:
        raise ValueError("Schedule contains missing or duplicate job ids.")
    accepted: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    excluded: defaultdict[str, int] = defaultdict(int)
    audit_excluded: list[dict[str, Any]] = []
    scheduled_fields = tuple(SCHEDULE_FIELDS - {"domain", "item_block"})
    generation_ids: set[str] = set()
    for event_index, row in enumerate(events, start=1):
        reason = _ineligibility_reason(row)
        if reason is not None:
            excluded[str(row.get("event_type", "unknown"))] += 1
            audit_excluded.append({"event_index": event_index, "job_id": row.get("job_id"), "reason": reason})
            continue
        if not row.get("job_id") or row.get("schedule_ordinal") is None:
            excluded["missing_schedule_identity"] += 1
            audit_excluded.append({"event_index": event_index, "job_id": row.get("job_id"), "reason": "missing_schedule_identity"})
            continue
        scheduled_job = scheduled.get(row["job_id"])
        if scheduled_job is None:
            excluded["job_id_not_in_schedule"] += 1
            audit_excluded.append({"event_index": event_index, "job_id": row["job_id"], "reason": "job_id_not_in_schedule"})
            continue
        if any(row.get(field) != scheduled_job.get(field) for field in scheduled_fields):
            excluded["schedule_identity_mismatch"] += 1
            audit_excluded.append({"event_index": event_index, "job_id": row["job_id"], "reason": "schedule_identity_mismatch"})
            continue
        key = tuple(row.get(name) for name in CELL_KEYS)
        if None in key:
            raise ValueError("Valid success row is missing a confirmatory key field.")
        if key in seen:
            raise ValueError(f"Duplicate valid result for immutable job: {key!r}")
        if row["generation_id"] in generation_ids:
            raise ValueError(f"Receipt generation ID reused across jobs: {row['generation_id']!r}")
        seen.add(key)
        generation_ids.add(row["generation_id"])
        accepted.append(row)

    grouped: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        grouped[(row["panel"], row["model"], row["provider_route"], row["effort"], row["cap"])].append(row)
    cells = []
    for key, rows in sorted(grouped.items(), key=lambda value: tuple(map(str, value[0]))):
        n, k = len(rows), sum(
            row["correct"] is True and row.get("finish_reason") != "length"
            for row in rows
        )
        censored = sum(
            row.get("finish_reason") == "length"
            for row in rows
        )
        cells.append({
            "panel": key[0], "model": key[1], "provider_route": key[2],
            "effort": key[3], "cap": key[4], "n": n, "k": k,
            "accuracy": k / n, "length_stops": censored,
            "length_stop_rate": censored / n,
            "accuracy_bound_lo": k / n, "accuracy_bound_hi": (k + censored) / n,
            "receipt_cost_usd_total": sum(float(row["receipt_cost_usd"]) for row in rows),
        })
    interactions = []
    by_panel: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        by_panel[(cell["panel"], cell["model"], cell["provider_route"])].append(cell)
    for key, panel_cells in by_panel.items():
        efforts = sorted(
            {cell["effort"] for cell in panel_cells},
            key=lambda effort: (EFFORT_ORDER.get(str(effort), float("inf")), str(effort)),
        )
        caps = sorted({cell["cap"] for cell in panel_cells})
        lookup = {(cell["effort"], cell["cap"]): cell for cell in panel_cells}
        if len(efforts) == 2 and len(caps) == 2 and all((e, c) in lookup for e in efforts for c in caps):
            small, large = caps
            low, high = efforts
            d_small = lookup[(high, small)]["accuracy"] - lookup[(low, small)]["accuracy"]
            d_large = lookup[(high, large)]["accuracy"] - lookup[(low, large)]["accuracy"]
            interactions.append({
                "panel": key[0], "model": key[1], "provider_route": key[2],
                "lower_effort": low, "higher_effort": high, "small_cap": small,
                "large_cap": large, "slope_small_cap": d_small,
                "slope_large_cap": d_large, "interaction": d_large - d_small,
            })
    return {
        "cells": cells,
        "interactions": interactions,
        "excluded_events": dict(sorted(excluded.items())),
        "selection_audit": {
            "schedule_sha256": schedule["sha256"],
            "scheduled_jobs": len(scheduled),
            "accepted_job_ids": [row["job_id"] for row in accepted],
            "excluded": audit_excluded,
        },
    }
