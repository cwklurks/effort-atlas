"""Audit paired output-cap rescues without treating missing rows as wrong.

Example:
  python -m effort_atlas.rescue_analysis \
    --old-dir results_openrouter --rescue-dir results_openrouter_rescue \
    --domain math --effort max --old-cap 20000
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from . import ROOT


def read_real_rows(directory: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(directory.glob("sweep_real_*.jsonl")):
        with path.open() as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def classify_pairs(
    old_rows: list[dict],
    rescue_rows: list[dict],
    domain: str,
    effort: str | float,
    old_cap: int,
) -> list[dict]:
    candidates: dict[str, dict] = {}
    for row in old_rows:
        if (
            row.get("error") is None
            and row.get("domain") == domain
            and str(row.get("effort")) == str(effort)
            and row.get("finish_reason") == "length"
            and row.get("completion_tokens") == old_cap
        ):
            candidates[row["item_id"]] = row

    attempts: dict[str, list[dict]] = {}
    for row in rescue_rows:
        if (
            row.get("domain") == domain
            and str(row.get("effort")) == str(effort)
            and row.get("item_id") in candidates
        ):
            attempts.setdefault(row["item_id"], []).append(row)

    pairs = []
    for item_id, old in sorted(candidates.items()):
        item_attempts = attempts.get(item_id, [])
        valid = [
            row
            for row in item_attempts
            if row.get("error") is None
            and row.get("completion_tokens", -1) >= 0
            and row.get("prompt_tokens", -1) >= 0
            and bool(row.get("finish_reason"))
        ]
        new = valid[-1] if valid else None
        if new is None:
            status = (
                "unaccounted_stream"
                if any(
                    row.get("completion_tokens", -1) < 0
                    or row.get("prompt_tokens", -1) < 0
                    for row in item_attempts
                )
                else "missing"
            )
        elif new.get("finish_reason") == "length":
            status = "still_censored"
        elif bool(new.get("correct")):
            status = "rescued"
        elif new.get("finish_reason") == "stop":
            status = "completed_wrong"
        else:
            status = "other_terminal"
        pairs.append(
            {
                "item_id": item_id,
                "status": status,
                "old_correct": bool(old.get("correct")),
                "old_completion_tokens": old.get("completion_tokens"),
                "new_correct": None if new is None else bool(new.get("correct")),
                "new_completion_tokens": (
                    None if new is None else new.get("completion_tokens")
                ),
                "new_finish_reason": (
                    None if new is None else new.get("finish_reason")
                ),
                "reported_cost_usd": (
                    None if new is None else new.get("reported_cost_usd")
                ),
                "attempt_rows": len(item_attempts),
            }
        )
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-dir", required=True)
    ap.add_argument("--rescue-dir", required=True)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--effort", required=True)
    ap.add_argument("--old-cap", required=True, type=int)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    old_dir = ROOT / args.old_dir
    rescue_dir = ROOT / args.rescue_dir
    pairs = classify_pairs(
        read_real_rows(old_dir),
        read_real_rows(rescue_dir),
        args.domain,
        args.effort,
        args.old_cap,
    )
    counts = Counter(pair["status"] for pair in pairs)
    paired = len(pairs) - counts["missing"] - counts["unaccounted_stream"]
    rescued = counts["rescued"]

    print(f"historically capped={len(pairs)}")
    for status in [
        "rescued",
        "completed_wrong",
        "still_censored",
        "other_terminal",
        "unaccounted_stream",
        "missing",
    ]:
        print(f"{status}={counts[status]}")
    print(
        "cap_rescue_rate="
        + (f"{rescued}/{paired} ({rescued / paired:.1%})" if paired else "missing")
    )
    known_cost = sum(
        float(pair["reported_cost_usd"] or 0)
        for pair in pairs
        if pair["reported_cost_usd"] is not None
    )
    print(f"known_reported_rescue_cost=${known_cost:.6f}")

    if args.output:
        output = ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(pairs[0]) if pairs else [])
            if pairs:
                writer.writeheader()
                writer.writerows(pairs)
        print(f"pairs_csv={output}")


if __name__ == "__main__":
    main()
