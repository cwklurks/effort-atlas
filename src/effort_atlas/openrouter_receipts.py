"""Fetch OpenRouter generation-stat receipts for completed result rows.

The receipt endpoint is read-only. This module never creates a completion and
does not alter result rows; it appends OpenRouter's response verbatim alongside
the minimum fields needed to link it back to a JSONL row.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from . import ROOT, load_config


def build_receipt(source_result: str, row: dict, payload: dict) -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_result": source_result,
        "item_id": row.get("item_id"),
        "effort": row.get("effort"),
        "max_tokens_requested": row.get("max_tokens_requested"),
        "generation_id": row["generation_id"],
        "openrouter_response": payload,
    }


def _fetch_generation(base_url: str, api_key: str, generation_id: str) -> dict:
    url = f"{base_url.rstrip('/')}/generation?{urlencode({'id': generation_id})}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def _source_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _load_completed_rows(paths: list[Path]) -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for path in paths:
        with path.open() as fh:
            for line in fh:
                row = json.loads(line)
                generation_id = row.get("generation_id")
                if not generation_id or row.get("error") is not None:
                    continue
                if generation_id in seen:
                    continue
                seen.add(generation_id)
                rows.append((_source_label(path), row))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--results", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    pcfg = cfg["provider"]
    load_dotenv(
        ROOT / ".env",
        override=bool(pcfg.get("env_file_override", False)),
    )
    api_key = os.environ.get(pcfg["api_key_env"])
    if not api_key:
        raise SystemExit(f"Set {pcfg['api_key_env']} before fetching receipts.")
    base_url = (
        os.environ.get(pcfg["base_url_env"])
        or pcfg["default_base_url"]
    )

    result_paths = [Path(value) for value in args.results]
    rows = _load_completed_rows(result_paths)
    if not rows:
        raise SystemExit("No completed rows with generation IDs were found.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if output.exists():
        with output.open() as fh:
            for line in fh:
                receipt = json.loads(line)
                if receipt.get("generation_id"):
                    existing.add(receipt["generation_id"])

    fetched = 0
    with output.open("a") as fh:
        for source, row in rows:
            generation_id = row["generation_id"]
            if generation_id in existing:
                continue
            payload = _fetch_generation(base_url, api_key, generation_id)
            receipt = build_receipt(source, row, payload)
            fh.write(json.dumps(receipt) + "\n")
            fh.flush()
            fetched += 1
            print(f"receipt {generation_id}: recorded")

    print(f"receipts_fetched={fetched} output={output}")


if __name__ == "__main__":
    main()
