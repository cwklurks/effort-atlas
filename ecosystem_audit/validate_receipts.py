#!/usr/bin/env python3
"""Offline validator for commit-pinned static code receipts."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

def fail(message: str) -> None:
    raise AssertionError(message)

def main() -> int:
    lock = json.loads((ROOT / "repos.lock.json").read_text(encoding="utf-8"))
    locked = {row["name"]: row for row in lock["repositories"]}
    index = json.loads((ROOT / "receipt_index.json").read_text(encoding="utf-8"))
    seen: set[str] = set()
    for receipt in index["receipts"]:
        fid = receipt["finding_id"]
        fail(f"duplicate finding_id {fid}") if fid in seen else seen.add(fid)
        target = receipt["target"]
        fail(f"unknown target {target}") if target not in locked else None
        entry = locked[target]
        sha = receipt["sha"]
        fail(f"{fid}: non-full SHA") if not FULL_SHA.fullmatch(sha) else None
        fail(f"{fid}: SHA differs from lock") if sha != entry["sha"] else None
        posix = PurePosixPath(receipt["path"])
        fail(f"{fid}: unsafe path") if posix.is_absolute() or ".." in posix.parts or str(posix) != receipt["path"] else None
        start, end = int(receipt["line_start"]), int(receipt["line_end"])
        fail(f"{fid}: invalid inclusive range") if start < 1 or end < start else None
        remote = entry["canonical_remote"].removesuffix(".git")
        expected_url = f"{remote}/blob/{sha}/{receipt['path']}#L{start}-L{end}"
        fail(f"{fid}: malformed permalink") if receipt["permalink"] != expected_url else None
        source = ROOT / "_repos" / target / receipt["path"]
        fail(f"{fid}: source missing: {source}") if not source.is_file() else None
        raw_lines = source.read_bytes().splitlines(keepends=True)
        fail(f"{fid}: range past EOF") if end > len(raw_lines) else None
        actual = b"".join(raw_lines[start - 1:end]).decode("utf-8")
        fail(f"{fid}: quote mismatch") if actual != receipt["quote"] else None
        ending = "CRLF" if b"\r\n" in b"".join(raw_lines[start - 1:end]) else "LF"
        fail(f"{fid}: line-ending declaration mismatch") if ending != receipt["line_ending"] else None
        fail(f"{fid}: generated source unsupported") if receipt["generated_file"] is not False else None
    print(f"validated {len(seen)} exact code receipts")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError, UnicodeDecodeError) as exc:
        print(f"receipt validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
