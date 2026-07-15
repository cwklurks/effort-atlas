"""Sweep runner: domains × effort levels × items → results/sweep_*.jsonl

  python -m effort_atlas.sweep --dry-run   cost estimate, zero API calls
  python -m effort_atlas.sweep --mock      full pipeline, fake responses
  python -m effort_atlas.sweep             the real thing (needs .env)

Rows are appended after every completion, so an interrupted sweep loses nothing;
re-running skips completed (item, effort) pairs via the response cache.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import ROOT, load_config
from .client import InklingClient
from .graders import grade


def load_items(data_dir: Path, domains: list[str], limit: int) -> list[dict]:
    items = []
    for domain in domains:
        path = data_dir / f"{domain}.jsonl"
        if not path.exists():
            raise SystemExit(f"Missing {path} — run data_gen/fetch_data first.")
        with path.open() as fh:
            rows = [json.loads(line) for line in fh]
        items.extend(rows[:limit])
    return items


def dry_run(cfg: dict, items: list[dict]) -> None:
    pr, levels = cfg["pricing"], cfg["effort"]["levels"]
    total_calls, total_cost = 0, 0.0
    print(f"{'effort':>8} {'calls':>7} {'est. out tok':>14} {'est. cost':>10}")
    for effort in levels:
        calls = len(items)
        out_tok = pr["expected_output_tokens"][str(effort)] * calls
        in_tok = pr["expected_input_tokens"] * calls
        cost = (out_tok * pr["output_per_mtok"] + in_tok * pr["input_per_mtok"]) / 1e6
        total_calls += calls
        total_cost += cost
        print(f"{effort:>8} {calls:>7} {out_tok:>14,} {cost:>9.2f}$")
    print("-" * 44)
    print(f"{'TOTAL':>8} {total_calls:>7} {'':>14} {total_cost:>9.2f}$")
    print("\nEstimates only — verify pricing in config.yaml against your provider.")


def run(mock: bool) -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["paths"]["data"]
    results_dir = ROOT / cfg["paths"]["results"]
    results_dir.mkdir(parents=True, exist_ok=True)

    items = load_items(data_dir, cfg["sweep"]["domains"], cfg["sweep"]["items_per_domain"])
    client = InklingClient(cfg, ROOT, mock=mock)
    levels = cfg["effort"]["levels"]

    tag = "mock" if mock else "real"
    out_path = results_dir / f"sweep_{tag}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    print(f"{len(items)} items × {len(levels)} effort levels → {out_path}\n")

    n_done = 0
    with out_path.open("w") as fh:
        for effort in levels:
            correct_by_domain: dict[str, list[bool]] = {}
            for item in items:
                prompt = item["prompt"]
                if mock:  # let the mock fabricate right/wrong answers — never sent for real
                    prompt = f"{prompt}\n\nMOCK_GOLD: {item['answer']}"
                comp = client.complete(prompt, effort, item["id"])
                ok, extracted = grade(item["grader"], comp.text, item["answer"])
                row = {
                    "item_id": item["id"], "domain": item["domain"], "effort": effort,
                    "correct": ok, "extracted": extracted, "gold": item["answer"],
                    "completion_tokens": comp.completion_tokens,
                    "prompt_tokens": comp.prompt_tokens,
                    "latency_s": comp.latency_s, "cached": comp.cached, "mock": mock,
                    "model": cfg["provider"]["model"],
                    "effort_mode": cfg["effort"]["mode"],
                    "response_text": comp.text,
                    "reasoning_chars": len(comp.reasoning_text),
                    "reasoning_text": comp.reasoning_text,
                }
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                correct_by_domain.setdefault(item["domain"], []).append(ok)
                n_done += 1
                if n_done % 25 == 0:
                    print(f"  {n_done}/{len(items) * len(levels)} calls done")
            summary = "  ".join(
                f"{d}: {sum(v)}/{len(v)}" for d, v in sorted(correct_by_domain.items())
            )
            print(f"effort={effort}: {summary}")

    print(f"\nDone → {out_path}\nNext: python -m effort_atlas.analyze")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="cost estimate only")
    ap.add_argument("--mock", action="store_true", help="fake responses, no API")
    args = ap.parse_args()

    if args.dry_run:
        cfg = load_config()
        items = load_items(ROOT / cfg["paths"]["data"], cfg["sweep"]["domains"],
                           cfg["sweep"]["items_per_domain"])
        dry_run(cfg, items)
    else:
        run(mock=args.mock)


if __name__ == "__main__":
    main()
