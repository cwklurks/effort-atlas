"""Surgically invalidate poisoned cache entries so a re-run regenerates ONLY them.

Finds every (item, effort) pair in the combined results whose response hit the
accidental 4,096-token cap (completion_tokens >= 4090), recomputes each pair's
cache key exactly as client.py does, and deletes those cache files. All clean
rows keep their cache entries and replay for free on the next sweep.

Run locally from the repo root:
    PYTHONPATH=src python -m effort_atlas.invalidate_capped
"""

from __future__ import annotations

import hashlib
import json

from . import ROOT, load_config

CAP_THRESHOLD = 4090
RESULTS = ROOT / "results" / "combined_real.jsonl"


def cache_key(prompt: str, effort: float, model: str) -> str:
    blob = json.dumps(
        {"prompt": prompt, "effort": effort, "model": model, "mock": False},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def main() -> None:
    cfg = load_config()
    model = cfg["provider"]["model"]
    cache_dir = ROOT / cfg["paths"]["cache"]

    prompts: dict[str, str] = {}
    for domain in ["math", "knowledge", "extraction"]:
        path = ROOT / cfg["paths"]["data"] / f"{domain}.jsonl"
        if path.exists():
            for line in path.open():
                item = json.loads(line)
                prompts[item["id"]] = item["prompt"]

    capped: set[tuple[str, float]] = set()
    for line in RESULTS.open():
        r = json.loads(line)
        if r.get("error") is None and r.get("completion_tokens", 0) >= CAP_THRESHOLD:
            capped.add((r["item_id"], r["effort"]))

    deleted, missing = 0, 0
    for item_id, effort in sorted(capped):
        if item_id not in prompts:
            print(f"  WARNING: no prompt found for {item_id}, skipping")
            continue
        f = cache_dir / f"{cache_key(prompts[item_id], effort, model)}.json"
        if f.exists():
            f.unlink()
            deleted += 1
        else:
            missing += 1

    print(f"capped pairs found: {len(capped)}")
    print(f"cache entries deleted: {deleted}  (already absent: {missing})")
    print("\nNext: re-run the sweep for math + knowledge. Clean rows replay free;")
    print("only the deleted pairs (plus any never-completed ones) hit the API.")


if __name__ == "__main__":
    main()
