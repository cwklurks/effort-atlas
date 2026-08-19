#!/usr/bin/env python3
"""Verify or explicitly download pinned public benchmark inputs.

The default action is local verification only.  ``--download`` is an explicit
network opt-in, performs no retries, uses no credentials, and rejects a
pre-existing mismatched file rather than overwriting it.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from effort_atlas.benchmark_provenance import (
    ProvenanceError,
    build_capability_table,
    load_manifest,
    sha256_file,
    validate_manifest,
    verify_download_root,
    write_capability_outputs,
)


def _target(root: Path, relative_path: str) -> Path:
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ProvenanceError(f"manifest path escapes root: {relative_path}") from exc
    return target


def download_missing_or_verified(manifest: dict, root: Path) -> None:
    """Download each immutable entry once, refusing to replace mismatched bytes."""

    for entry in manifest["entries"]:
        target = _target(root, entry["path"])
        if target.is_file():
            if (
                target.stat().st_size == entry["bytes"]
                and sha256_file(target) == entry["sha256"]
            ):
                print(f"verified existing {entry['source_id']}")
                continue
            raise ProvenanceError(f"refusing to overwrite mismatched source: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", dir=target.parent
        )
        temporary = Path(temporary_name)
        try:
            request = Request(
                entry["url"],
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": "effort-atlas-provenance/1",
                },
            )
            with (
                os.fdopen(descriptor, "wb") as output,
                urlopen(request, timeout=60) as response,
            ):
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            observed_size = temporary.stat().st_size
            observed_hash = sha256_file(temporary)
            if observed_size != entry["bytes"] or observed_hash != entry["sha256"]:
                raise ProvenanceError(
                    f"download did not match pinned bytes for {entry['source_id']}: "
                    f"size={observed_size}, sha256={observed_hash}"
                )
            temporary.replace(target)
            print(f"downloaded and verified {entry['source_id']}")
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("observational/benchmark_sources_manifest.json"),
    )
    parser.add_argument("--root", type=Path, default=Path("benchmark_sources"))
    parser.add_argument(
        "--download",
        action="store_true",
        help="explicitly download missing immutable public files; zero retries",
    )
    parser.add_argument(
        "--write-capabilities",
        action="store_true",
        help="derive the sanitized table after verification",
    )
    parser.add_argument(
        "--table",
        type=Path,
        default=Path("observational/benchmark_question_capabilities.jsonl"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("observational/benchmark_question_capabilities_summary.json"),
    )
    arguments = parser.parse_args()

    manifest = load_manifest(arguments.manifest)
    validate_manifest(manifest)
    if arguments.download:
        download_missing_or_verified(manifest, arguments.root)
    verified = verify_download_root(manifest, arguments.root)
    print(f"verified {len(verified)} pinned public files")
    if arguments.write_capabilities:
        rows, summary = build_capability_table(manifest, arguments.root)
        write_capability_outputs(rows, summary, arguments.table, arguments.summary)
        print(
            f"wrote {len(rows)} sanitized question-by-model rows to {arguments.table}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProvenanceError as exc:
        raise SystemExit(f"provenance check failed: {exc}")
