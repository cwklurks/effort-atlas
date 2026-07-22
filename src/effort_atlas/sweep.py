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


def load_items(
    data_dir: Path,
    domains: list[str],
    limit: int,
    item_ids: list[str] | None = None,
) -> list[dict]:
    items = []
    for domain in domains:
        path = data_dir / f"{domain}.jsonl"
        if not path.exists():
            raise SystemExit(f"Missing {path} — run data_gen/fetch_data first.")
        with path.open() as fh:
            rows = [json.loads(line) for line in fh]
        items.extend(rows if item_ids else rows[:limit])
    if item_ids:
        by_id = {item["id"]: item for item in items}
        missing = [item_id for item_id in item_ids if item_id not in by_id]
        if missing:
            raise SystemExit(f"Missing requested item ids: {', '.join(missing)}")
        items = [by_id[item_id] for item_id in item_ids]
    return items


def dry_run(cfg: dict, items: list[dict]) -> None:
    pr, levels = cfg["pricing"], cfg["effort"]["levels"]
    budgets = cfg["sweep"].get("budgets") or [
        cfg["provider"]["max_completion_tokens"]
    ]
    seeds = cfg["sweep"].get("seeds") or [None]
    cap_bounds_billable = pr.get("cap_bounds_billable_tokens", True)
    total_calls, total_out, total_cost = 0, 0, 0.0
    worst_out, worst_cost = 0, 0.0
    print(
        f"{'effort':>8} {'cap':>8} {'calls':>7} "
        f"{'est. out tok':>14} {'est. cost':>10}"
    )
    for budget in budgets:
        for effort in levels:
            calls = len(items) * len(seeds)
            expected_per_call = pr["expected_output_tokens"][str(effort)]
            out_tok = (
                min(expected_per_call, budget)
                if cap_bounds_billable
                else expected_per_call
            ) * calls
            max_out_tok = budget * calls
            in_tok = pr["expected_input_tokens"] * calls
            cost = (
                out_tok * pr["output_per_mtok"]
                + in_tok * pr["input_per_mtok"]
            ) / 1e6
            max_cost = (
                max_out_tok * pr["output_per_mtok"]
                + in_tok * pr["input_per_mtok"]
            ) / 1e6
            total_calls += calls
            total_out += out_tok
            total_cost += cost
            if cap_bounds_billable:
                worst_out += max_out_tok
                worst_cost += max_cost
            print(
                f"{str(effort):>8} {budget:>8,} {calls:>7} "
                f"{out_tok:>14,} {cost:>9.2f}$"
            )
    print("-" * 54)
    print(
        f"{'TOTAL':>8} {'':>8} {total_calls:>7} "
        f"{total_out:>14,} {total_cost:>9.2f}$"
    )
    if cap_bounds_billable:
        print(
            f"worst-case exposure: {worst_out:,} completion tokens, "
            f"{worst_cost:.2f}$"
        )
    else:
        print(
            "worst-case exposure: not bounded by max_tokens; provider-reported "
            "billable reasoning can exceed the requested cap"
        )
    print("\nEstimates only — verify pricing in config against your provider.")


def run(mock: bool, config_path: str | Path | None = None) -> None:
    cfg = load_config(config_path)
    if not mock and cfg["sweep"].get("enabled") is False:
        reason = cfg["sweep"].get("pause_reason", "manual safety gate")
        raise SystemExit(f"Paid sweep is disabled: {reason}")
    data_dir = ROOT / cfg["paths"]["data"]
    results_dir = ROOT / cfg["paths"]["results"]
    results_dir.mkdir(parents=True, exist_ok=True)

    items = load_items(
        data_dir,
        cfg["sweep"]["domains"],
        cfg["sweep"]["items_per_domain"],
        item_ids=cfg["sweep"].get("item_ids"),
    )
    client = InklingClient(cfg, ROOT, mock=mock)
    levels = cfg["effort"]["levels"]
    budgets = cfg["sweep"].get("budgets") or [None]
    seeds = cfg["sweep"].get("seeds") or [None]

    tag = "mock" if mock else "real"
    out_path = results_dir / f"sweep_{tag}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    print(
        f"{len(items)} items × {len(levels)} effort levels "
        f"× {len(budgets)} output budgets × {len(seeds)} seeds → {out_path}\n"
    )

    n_done = 0
    consecutive_failures = 0
    with out_path.open("w") as fh:
        for budget in budgets:
            for effort in levels:
                correct_by_domain: dict[str, list[bool]] = {}
                for seed in seeds:
                    for item in items:
                        prompt = item["prompt"]
                        if mock:  # let mock fabricate answers; never sent for real
                            prompt = f"{prompt}\n\nMOCK_GOLD: {item['answer']}"
                        try:
                            comp = client.complete(
                                prompt,
                                effort,
                                item["id"],
                                max_tokens=budget,
                                seed=seed,
                            )
                            if not comp.cached:
                                consecutive_failures = 0
                        except Exception as err:  # noqa: BLE001 — log the row, keep sweeping
                            consecutive_failures += 1
                            fh.write(json.dumps({
                                "item_id": item["id"], "domain": item["domain"],
                                "effort": effort, "max_tokens_requested": budget,
                                "seed": seed,
                                "error": str(err), "mock": mock,
                            }) + "\n")
                            fh.flush()
                            print(f"  FAILED {item['id']} @ {effort} "
                                  f"({consecutive_failures} consecutive): {err}")
                            if consecutive_failures >= 5:
                                print(
                                    "\nCircuit breaker: 5 consecutive failures — the endpoint "
                                    "is likely down or overloaded.\nRe-run this same command "
                                    "later: completed calls are cached and cost nothing to "
                                    "replay; only failed/missing ones hit the API."
                                )
                                return
                            time.sleep(30)
                            continue
                        ok, extracted = grade(item["grader"], comp.text, item["answer"])
                        row = {
                            "item_id": item["id"], "domain": item["domain"],
                            "effort": effort, "seed": seed,
                            "max_tokens_requested": (
                                budget
                                if budget is not None
                                else cfg["provider"]["max_completion_tokens"]
                            ),
                            "correct": ok, "extracted": extracted, "gold": item["answer"],
                            "completion_tokens": comp.completion_tokens,
                            "reasoning_tokens": comp.reasoning_tokens,
                            "prompt_tokens": comp.prompt_tokens,
                            "latency_s": comp.latency_s, "cached": comp.cached, "mock": mock,
                            "model": cfg["provider"]["model"],
                            "effort_mode": cfg["effort"]["mode"],
                            "response_text": comp.text,
                            "reasoning_chars": len(comp.reasoning_text),
                            "reasoning_text": comp.reasoning_text,
                            "finish_reason": comp.finish_reason,
                            "served_provider": comp.provider,
                            "generation_id": comp.generation_id,
                            "reported_cost_usd": comp.reported_cost_usd,
                        }
                        fh.write(json.dumps(row) + "\n")
                        fh.flush()
                        correct_by_domain.setdefault(item["domain"], []).append(ok)
                        n_done += 1
                        total = len(items) * len(levels) * len(budgets) * len(seeds)
                        if total <= 10 or n_done % 25 == 0:
                            print(f"  {n_done}/{total} calls done")
                summary = "  ".join(
                    f"{d}: {sum(v)}/{len(v)}"
                    for d, v in sorted(correct_by_domain.items())
                )
                print(f"budget={budget or 'default'} effort={effort}: {summary}")

    print(f"\nDone → {out_path}\nNext: python -m effort_atlas.analyze")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="cost estimate only")
    ap.add_argument("--mock", action="store_true", help="fake responses, no API")
    ap.add_argument(
        "--config",
        default=None,
        help="configuration file (default: config.yaml)",
    )
    args = ap.parse_args()

    if args.dry_run:
        cfg = load_config(args.config)
        items = load_items(
            ROOT / cfg["paths"]["data"],
            cfg["sweep"]["domains"],
            cfg["sweep"]["items_per_domain"],
            item_ids=cfg["sweep"].get("item_ids"),
        )
        dry_run(cfg, items)
    else:
        run(mock=args.mock, config_path=args.config)


if __name__ == "__main__":
    main()
