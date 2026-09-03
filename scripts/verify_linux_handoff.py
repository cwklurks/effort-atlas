#!/usr/bin/env python3
"""Fail-closed verifier for the tracked Linux handoff context.

This script is intentionally stdlib-only so it can run before `uv sync`.  It
verifies the exact files a new Linux checkout must read before working on REAP.
It never downloads data, contacts a model provider, or reads environment secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_RELATIVE_PATH = Path("reap/linux_handoff/COPY_MANIFEST.json")

# Keep this list short enough to read, but sufficient to reconstruct the project's
# safety rules, current research state, and the benchmark-selection decision.
CRITICAL_PATHS: dict[str, str] = {
    "AGENTS.md": "repository and research safeguards",
    "observational/benchmark_question_capabilities.jsonl": "sanitized complete question-by-model capability cells",
    "observational/benchmark_question_capabilities_summary.json": "recomputed benchmark capability summary",
    "observational/benchmark_sources_manifest.json": "immutable public benchmark source pins",
    "observational/INPUT_PROVENANCE.md": "raw-input reproducibility boundary",
    "observational/RESULTS.md": "exploratory findings and caveats",
    "observational/state_manifest.json": "pinned observational source identifiers",
    "pyproject.toml": "Python package and optional dependency definition",
    "reap/01_EXPERIMENT_OUTLINE_v2.md": "draft intervention design",
    "reap/02_BUDGET_AND_COSTS.md": "platform-scoped budget model",
    "reap/04_DATASET_CANDIDATES.md": "dataset scope and risks",
    "reap/08_HYPERPARAMETER_DECISIONS.md": "verified and unresolved parameters",
    "reap/10_PHASE_GATE_PLAN_2026-08-08.md": "phase gates and ownership",
    "reap/18_POST_MEETING_BENCHMARK_AUDIT_2026-08-18.md": "post-meeting benchmark audit",
    "reap/19_METHOD_REVIEW_SYNTHESIS_2026-08-18.md": "review synthesis",
    "reap/20_BENCHMARK_COMPARISON_2026-08-18.md": "benchmark comparison",
    "reap/21_MODEL_PAIR_ELIGIBILITY_2026-08-18.md": "model-pair eligibility gate",
    "reap/22_BENCHMARK_PROVENANCE_AND_CAPABILITY_2026-08-19.md": "plain-language source and capability audit",
    "reap/23_BENCHMARK_SCOPE_DECISION_2026-08-20.md": "exploratory-versus-controlled benchmark scope boundary",
    "reap/CODEX_BRIEFING.md": "canonical project state and mandatory reading order",
    "reap/README.md": "program charter and governance",
    "reap/claude_project/PROJECT_BRIEF.md": "canonical collaboration context",
    "reap/linux_handoff/BOOTSTRAP_LINUX.md": "Linux setup and transfer steps",
    "reap/linux_handoff/CONTEXT_BUILD_RECEIPT.md": "context-bundle security and reproducibility receipt",
    "reap/linux_handoff/CONTEXT_PACK.md": "high-density start context",
    "reap/linux_handoff/REPO_CONTEXT.xml": "secret-scanned tracked repository context bundle",
    "reap/linux_handoff/START_HERE_PROMPT.md": "copy-ready new-session prompt",
    "reap/next_chapter/BUILD_RECEIPT.md": "portable report build and verification receipt",
    "reap/next_chapter/artifact.json": "source-backed next-chapter report input",
    "reap/next_chapter/index.html": "self-contained next-chapter reader",
    "scripts/acquire_benchmark_sources.py": "pinned public benchmark acquisition and verification",
    "scripts/build_linux_context_pack.sh": "reproducible context-bundle builder",
    "scripts/verify_linux_handoff.py": "pre-environment handoff verifier",
    "scripts/verify_offline.sh": "canonical offline verification command",
    "src/effort_atlas/confirmatory.py": "offline ledger and schedule baseline",
    "src/effort_atlas/benchmark_provenance.py": "sanitized benchmark capability builder",
    "src/effort_atlas/graders.py": "answer-extraction implementation",
    "tests/test_linux_handoff.py": "handoff verifier tests",
    "tests/test_benchmark_provenance.py": "benchmark provenance contract tests",
    "tests/test_next_chapter_report.py": "next-chapter report contract tests",
}


class VerificationError(RuntimeError):
    """A handoff safety check failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: str) -> Path:
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or value != candidate.as_posix()
    ):
        raise VerificationError(f"unsafe manifest path: {value!r}")
    return Path(*candidate.parts)


def manifest_path(repo_root: Path) -> Path:
    return repo_root / MANIFEST_RELATIVE_PATH


def make_manifest(repo_root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for relative, purpose in sorted(CRITICAL_PATHS.items()):
        path = repo_root / safe_relative_path(relative)
        if not path.is_file():
            raise VerificationError(f"critical file is missing: {relative}")
        entries.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "purpose": purpose,
            }
        )
    return {
        "schema_version": 1,
        "purpose": (
            "Exact, tracked context required for a Linux REAP handoff. "
            "This is not a data bundle and contains no credentials."
        ),
        "transfer_mode": "git_first",
        "critical_files": entries,
        "excluded_from_transfer": [
            "environment variables and .env files",
            "provider API keys and account credentials",
            "raw benchmark caches and restricted GPQA text",
            "provider responses, receipts, smoke data, and confirmatory data",
            "uncommitted local work not intentionally committed to the branch",
        ],
        "refresh_instruction": (
            "After an intentionally committed benchmark-provenance update, run "
            "python scripts/verify_linux_handoff.py --write and commit this manifest "
            "with the changed tracked context."
        ),
    }


def load_manifest(repo_root: Path) -> dict[str, Any]:
    path = manifest_path(repo_root)
    if not path.is_file():
        raise VerificationError(f"manifest is missing: {MANIFEST_RELATIVE_PATH}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VerificationError(f"manifest is invalid JSON: {error}") from error
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise VerificationError("manifest must be a schema_version 1 object")
    entries = raw.get("critical_files")
    if not isinstance(entries, list) or not entries:
        raise VerificationError("manifest must contain non-empty critical_files")
    return raw


def verify_manifest(repo_root: Path) -> int:
    manifest = load_manifest(repo_root)
    entries = manifest["critical_files"]
    seen: set[str] = set()
    previous = ""

    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError("manifest entry must be an object")
        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise VerificationError("manifest entry has an invalid path or sha256")
        if not isinstance(expected_bytes, int) or expected_bytes < 0:
            raise VerificationError(f"invalid byte count for {relative}")
        if relative in seen:
            raise VerificationError(f"duplicate manifest path: {relative}")
        if relative < previous:
            raise VerificationError("manifest paths must be sorted")
        seen.add(relative)
        previous = relative

        path = repo_root / safe_relative_path(relative)
        if not path.is_file():
            raise VerificationError(f"critical file is missing: {relative}")
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            raise VerificationError(
                f"byte-count mismatch for {relative}: expected {expected_bytes}, got {actual_bytes}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise VerificationError(
                f"sha256 mismatch for {relative}: expected {expected_hash}, got {actual_hash}"
            )

    expected_paths = set(CRITICAL_PATHS)
    if seen != expected_paths:
        missing = sorted(expected_paths - seen)
        unexpected = sorted(seen - expected_paths)
        raise VerificationError(
            f"manifest path set does not match the verifier policy; missing={missing}, "
            f"unexpected={unexpected}"
        )

    _verify_git_tracking(repo_root, sorted(seen))
    print(f"Linux handoff verified: {len(entries)} exact critical files.")
    return 0


def _verify_git_tracking(repo_root: Path, paths: list[str]) -> None:
    """Require a Git checkout so copied loose files cannot masquerade as a handoff."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", "--", *paths],
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError as error:
        raise VerificationError("git is required for the Git-first handoff") from error
    if result.returncode != 0:
        raise VerificationError(
            "one or more critical files are not tracked by Git; use a committed checkout"
        )


def write_manifest(repo_root: Path) -> int:
    payload = make_manifest(repo_root)
    destination = manifest_path(repo_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    print(
        f"Wrote {destination.relative_to(repo_root)} with {len(payload['critical_files'])} files."
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root to verify (default: this script's parent)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="explicitly regenerate the checked-in SHA-256 manifest; never downloads data",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    try:
        return write_manifest(repo_root) if args.write else verify_manifest(repo_root)
    except VerificationError as error:
        print(f"Linux handoff verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
