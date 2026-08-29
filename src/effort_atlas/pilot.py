"""Exploratory Inkling length pilot runner (200 items x 5 datasets, 32k cap).

    python -m effort_atlas.pilot                 # DRY RUN (default): cost table, zero calls
    python -m effort_atlas.pilot --mock          # full pipeline with fabricated responses
    python -m effort_atlas.pilot --live          # refuses unless every human gate is open

What this measures: generation length and termination under an explicit
32,000-token allowance, per dataset. Correctness is not graded here; only
strict-terminator presence is recorded (safeguard 5). Data are EXPLORATORY and
never pooled with confirmatory estimates (safeguard 7).

Fail-closed by construction:
  * one attempt per item, max_retries must be 0, fallbacks disabled;
  * ledgered spend + worst case of the next call must stay under both the
    per-dataset and the total ceiling, or the run halts BEFORE that call;
  * live execution requires pilot.enabled, a verified balance with a date, a
    named approver, and an explicit environment acknowledgement;
  * the ledger (confirmatory.AttemptLedger, hash-chained, append-only) is
    content-free; response text goes to a gitignored file. GPQA question text
    never leaves restricted_local/.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import ROOT, load_config
from .client import Completion, InklingClient
from .confirmatory import AttemptLedger
from .wrapper import Rendered, render, strict_terminator_present

LIVE_ACK_ENV = "EFFORT_ATLAS_PILOT_LIVE_ACK"
LIVE_ACK_VALUE = "I_HAVE_READ_THE_APPROVED_PREFLIGHT"
RESTRICTED_FILES = {"gpqa_main": "restricted_local/gpqa_main.RESTRICTED.jsonl"}
EXIT_GATE_REFUSED, EXIT_CEILING_HALT, EXIT_CIRCUIT_BREAKER = 2, 3, 4


class CeilingHalt(RuntimeError):
    pass


class CircuitBreaker(RuntimeError):
    pass


# ── items ────────────────────────────────────────────────────────────────────

def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_selected_items(cfg: dict, selection: dict, *, cap_dir: Path | None = None) -> list[dict]:
    """Return the selected source rows, with GPQA text merged from restricted_local.

    Every selected row is checked against the selection file's prompt_sha256 so
    the runner cannot silently ask a different item than the one recorded.
    """
    cap_dir = cap_dir or (ROOT / cfg["paths"]["data"])
    wanted = cfg["pilot"]["datasets"]
    out: list[dict] = []
    for name in wanted:
        if name not in selection["datasets"]:
            raise SystemExit(f"selection has no dataset {name!r}")
        spec = selection["datasets"][name]
        path = cap_dir / spec["file"]
        if not path.exists():
            raise SystemExit(f"{path} missing; run capabilities/acquire.py")
        rows = {(r["split"], r["source_row_index"]): r for r in _read_jsonl(path)}
        restricted: dict[str, dict] = {}
        if name in RESTRICTED_FILES:
            rpath = cap_dir / RESTRICTED_FILES[name]
            if not rpath.exists():
                raise SystemExit(
                    f"{rpath} missing: GPQA text exists only locally; run "
                    "capabilities/acquire.py (never commit or share that file)"
                )
            restricted = {r["source_item_id"]: r for r in _read_jsonl(rpath)}
        for e in spec["items"]:
            row = rows.get((e["split"], e["source_row_index"]))
            if row is None:
                raise SystemExit(f"{name}: selected row {e['split']}/{e['source_row_index']} not in file")
            if row["source_item_id"] != e["source_item_id"]:
                raise SystemExit(f"{name}: item id mismatch at row {e['source_row_index']}")
            if row["prompt_sha256"] != e["prompt_sha256"]:
                raise SystemExit(f"{name}: prompt_sha256 mismatch for {e['source_item_id']}")
            if restricted:
                full = restricted.get(row["source_item_id"])
                if full is None or full["full_row_sha256"] != row["full_row_sha256"]:
                    raise SystemExit(
                        f"{name}: restricted row for {row['source_item_id']} missing or "
                        "hash-mismatched against the committed skeleton"
                    )
                row = full
            out.append(row)
    return out


# ── cost and ceilings ────────────────────────────────────────────────────────

def estimate_prompt_tokens(text: str) -> int:
    """Conservative pre-call estimate (chars/3). Real counts come from usage."""
    return max(1, math.ceil(len(text) / 3))


def worst_case_call_usd(cfg: dict, prompt_tokens: int) -> float:
    pr = cfg["pricing"]
    cap = int(cfg["pilot"]["cap"])
    return (prompt_tokens * pr["input_per_mtok"] + cap * pr["output_per_mtok"]) / 1e6


def expected_call_usd(cfg: dict, prompt_tokens: int, effort: str) -> float:
    pr = cfg["pricing"]
    cap = int(cfg["pilot"]["cap"])
    exp_out = pr["expected_output_tokens"][str(effort)]
    if pr.get("cap_bounds_billable_tokens", True):
        exp_out = min(exp_out, cap)
    return (prompt_tokens * pr["input_per_mtok"] + exp_out * pr["output_per_mtok"]) / 1e6


def actual_call_usd(cfg: dict, comp: Completion) -> float:
    if comp.reported_cost_usd is not None:
        return float(comp.reported_cost_usd)
    pr = cfg["pricing"]
    out_tokens = comp.completion_tokens + (comp.reasoning_tokens or 0)
    return (comp.prompt_tokens * pr["input_per_mtok"] + out_tokens * pr["output_per_mtok"]) / 1e6


@dataclass
class CeilingGuard:
    per_dataset_ceiling: float
    total_ceiling: float
    spent_by_dataset: dict[str, float] = field(default_factory=dict)

    @property
    def spent_total(self) -> float:
        return sum(self.spent_by_dataset.values())

    def check_before_call(self, dataset: str, worst_next_usd: float) -> None:
        ds = self.spent_by_dataset.get(dataset, 0.0)
        if ds + worst_next_usd > self.per_dataset_ceiling:
            raise CeilingHalt(
                f"{dataset}: ledgered ${ds:.4f} + worst-case next call ${worst_next_usd:.4f} "
                f"would exceed per-dataset ceiling ${self.per_dataset_ceiling:.2f}"
            )
        if self.spent_total + worst_next_usd > self.total_ceiling:
            raise CeilingHalt(
                f"total: ledgered ${self.spent_total:.4f} + worst-case next call "
                f"${worst_next_usd:.4f} would exceed total ceiling ${self.total_ceiling:.2f}"
            )

    def record(self, dataset: str, usd: float) -> None:
        self.spent_by_dataset[dataset] = self.spent_by_dataset.get(dataset, 0.0) + usd


# ── live gate ────────────────────────────────────────────────────────────────

def live_gate_failures(cfg: dict, env: dict | None = None) -> list[str]:
    env = os.environ if env is None else env
    b, p = cfg["budget"], cfg["pilot"]
    fails = []
    if not p.get("enabled"):
        fails.append("pilot.enabled is false")
    if b.get("balance_verified_usd") is None or not b.get("balance_verified_on"):
        fails.append("budget.balance_verified_usd / balance_verified_on not set from the account page")
    if not b.get("preflight_approved_by"):
        fails.append("budget.preflight_approved_by is empty (needs written approval)")
    if cfg["provider"].get("max_retries", 1) != 0:
        fails.append("provider.max_retries must be 0")
    extra = cfg["provider"].get("request_extra_body", {}).get("provider", {})
    if extra.get("allow_fallbacks") is not False or not extra.get("only"):
        fails.append("provider must be pinned (only: [...]) with allow_fallbacks: false")
    if env.get(LIVE_ACK_ENV) != LIVE_ACK_VALUE:
        fails.append(f"environment {LIVE_ACK_ENV} != {LIVE_ACK_VALUE}")
    bal = b.get("balance_verified_usd")
    if bal is not None and b["total_ceiling_usd"] > float(bal) - float(b.get("reserve_margin_usd", 0)):
        fails.append("budget.total_ceiling_usd exceeds verified balance minus reserve")
    return fails


# ── mock client ──────────────────────────────────────────────────────────────

MOCK_MEDIAN_TOKENS = {
    "mmlu_pro": 2500, "gpqa_main": 6000, "ifeval": 800, "wildbench_v2": 1500, "omni_math": 7000,
}


class PilotClient(InklingClient):
    """InklingClient whose mock path is cap-aware and dataset-aware.

    Mock lengths are lognormal around a per-dataset median with a heavy tail,
    so a few percent of fabricated responses hit the 32k cap and come back
    with finish_reason="length". Nothing here touches the network.
    """

    def complete(self, prompt, effort, item_id, max_tokens=None, seed=None, messages=None):
        if not self.mock:
            return super().complete(
                prompt, effort, item_id, max_tokens=max_tokens, seed=seed, messages=messages
            )
        key = self._cache_key(prompt, effort, max_tokens=max_tokens, seed=seed, messages=messages)
        cached = self._cache_get(key)
        if cached is not None:
            return Completion(**cached, cached=True)
        result = self._mock_pilot(prompt, effort, item_id, max_tokens or 32000)
        self._cache_put(key, result)
        return Completion(**result)

    def _mock_pilot(self, prompt: str, effort: str, item_id: str, cap: int) -> dict:
        dataset = item_id.split(":", 1)[0]
        rng = random.Random(f"pilot-mock:{item_id}:{effort}:{cap}")
        median = MOCK_MEDIAN_TOKENS.get(dataset, 3000)
        ordinal = self.cfg["effort"].get("ordinal", {})
        rank = float(ordinal.get(effort, 1))
        natural = int(median * (1.0 + 0.6 * (rank - 1)) * math.exp(rng.gauss(0.0, 0.9)))
        clipped = natural >= cap
        tokens = cap if clipped else max(50, natural)
        prompt_tokens = max(1, len(prompt) // 4)
        if clipped:
            text = "(mock reasoning that never reached an answer"
        elif rng.random() < 0.97:
            text = f"(mock reasoning)\nFinal answer: {rng.choice('ABCDEFGHIJ')}"
        else:
            text = "(mock reasoning that forgot the terminator) the answer is B"
        return {
            "text": text,
            "reasoning_text": "",
            "completion_tokens": tokens,
            "prompt_tokens": prompt_tokens,
            "reasoning_tokens": None,
            "latency_s": round(tokens / 4000, 2),
            "finish_reason": "length" if clipped else "stop",
            "provider": "mock",
            "generation_id": f"mock-{rng.randrange(1 << 40):010x}",
            "reported_cost_usd": None,
            "mock": True,
        }


# ── run ──────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary(cfg: dict, rows: list[dict], guard: CeilingGuard, halt: str | None) -> dict:
    caps = [int(c) for c in cfg["pilot"]["report_caps"]]
    cap = int(cfg["pilot"]["cap"])
    per: dict[str, dict] = {}
    for r in rows:
        d = per.setdefault(r["dataset"], {
            "attempts": 0, "errors": 0, "length_stops": 0, "terminator_present": 0,
            "terminator_required": 0, "completion_tokens": [], "spend_usd": 0.0,
        })
        d["attempts"] += 1
        if r.get("error"):
            d["errors"] += 1
            continue
        d["spend_usd"] += r["cost_usd"]
        d["completion_tokens"].append(r["completion_tokens"])
        if r["finish_reason"] == "length":
            d["length_stops"] += 1
        if r["terminator_required"]:
            d["terminator_required"] += 1
            d["terminator_present"] += int(r["terminator_present"])
    for name, d in per.items():
        toks = d.pop("completion_tokens")
        n = len(toks)
        # P(length >= c) is exactly identified for c <= cap: censored rows
        # (finish_reason=length at the cap) also satisfy length >= c.
        d["p_length_ge"] = {str(c): (sum(t >= c for t in toks) / n if n else None) for c in caps if c <= cap}
        d["median_completion_tokens"] = (
            sorted(toks)[n // 2] if n and d["length_stops"] < n / 2 else None
        )
        d["mean_reported"] = False  # never report a mean with censored rows
        d["spend_usd"] = round(d["spend_usd"], 4)
    return {
        "label": cfg["pilot"]["label"],
        "exploratory": True,
        "cap": cap,
        "datasets": per,
        "spend_total_usd": round(guard.spent_total, 4),
        "halt": halt,
        "finished_at": _now(),
    }


def dry_run(cfg: dict, rendered: list[Rendered], out_dir: Path) -> dict:
    guard_limits = cfg["budget"]
    levels = cfg["effort"]["levels"]
    table: dict[str, dict] = {}
    for r in rendered:
        est_in = estimate_prompt_tokens(r.request_text_for_estimate())
        d = table.setdefault(r.dataset, {"items": 0, "est_prompt_tokens": 0, "expected_usd": 0.0, "worst_usd": 0.0})
        d["items"] += 1
        d["est_prompt_tokens"] += est_in
        for lvl in levels:
            d["expected_usd"] += expected_call_usd(cfg, est_in, lvl)
            d["worst_usd"] += worst_case_call_usd(cfg, est_in)
    print(f"{'dataset':<14}{'items':>6}{'calls':>7}{'expected $':>12}{'worst $':>10}  ceiling ${guard_limits['per_dataset_ceiling_usd']:.2f}")
    tot_e = tot_w = 0.0
    for name, d in table.items():
        calls = d["items"] * len(levels)
        flag = "OK" if d["worst_usd"] <= guard_limits["per_dataset_ceiling_usd"] else "worst case exceeds ceiling: staged run will halt"
        print(f"{name:<14}{d['items']:>6}{calls:>7}{d['expected_usd']:>12.2f}{d['worst_usd']:>10.2f}  {flag}")
        tot_e += d["expected_usd"]; tot_w += d["worst_usd"]
        d["expected_usd"] = round(d["expected_usd"], 4); d["worst_usd"] = round(d["worst_usd"], 4)
    print(f"{'TOTAL':<14}{'':>6}{'':>7}{tot_e:>12.2f}{tot_w:>10.2f}  total ceiling ${guard_limits['total_ceiling_usd']:.2f}")
    print("\nDry run only. No provider call was made. Prices are the config's and must be re-pinned in the preflight doc.")
    report = {
        "mode": "dry_run", "generated_at": _now(), "levels": levels, "cap": cfg["pilot"]["cap"],
        "pricing": cfg["pricing"], "budget": guard_limits, "datasets": table,
        "expected_total_usd": round(tot_e, 4), "worst_total_usd": round(tot_w, 4),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dry_run.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


def run(cfg: dict, rendered: list[Rendered], *, mock: bool, out_dir: Path,
        client: InklingClient | None = None) -> tuple[dict, int]:
    tag = "mock" if mock else "live"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = AttemptLedger(out_dir / f"ledger_{tag}_{stamp}.jsonl")
    responses_path = out_dir / f"responses_{tag}_{stamp}.jsonl"
    guard = CeilingGuard(
        per_dataset_ceiling=float(cfg["budget"]["per_dataset_ceiling_usd"]),
        total_ceiling=float(cfg["budget"]["total_ceiling_usd"]),
    )
    client = client or PilotClient(cfg, ROOT, mock=mock)
    cap = int(cfg["pilot"]["cap"])
    levels = cfg["effort"]["levels"]
    req_seed = cfg["pilot"].get("request_seed")
    breaker_n = int(cfg["pilot"].get("circuit_breaker_consecutive_errors", 5))
    pcfg = cfg["provider"]
    route = (pcfg.get("request_extra_body", {}).get("provider", {}).get("only") or ["unpinned"])
    rows: list[dict] = []
    halt: str | None = None
    exit_code = 0
    consecutive_errors = 0
    n_total = len(rendered) * len(levels)

    with responses_path.open("a", encoding="utf-8") as resp_fh:
        try:
            for r in rendered:
                for effort in levels:
                    item_id = f"{r.dataset}:{r.source_item_id}"
                    est_in = estimate_prompt_tokens(r.request_text_for_estimate())
                    guard.check_before_call(r.dataset, worst_case_call_usd(cfg, est_in))
                    started = _now()
                    base_event = {
                        "panel": cfg["pilot"]["label"], "phase": "exploratory_pilot",
                        "model": pcfg["model"], "requested_provider": pcfg["name"],
                        "provider_route": ",".join(route), "item_id": item_id,
                        "domain": r.dataset, "effort": effort, "cap": cap, "replicate": 1,
                        "max_tokens": cap, "max_tokens_requested": cap,
                        "request_started_at": started,
                        "request_config": {
                            "wrapper_version": r.wrapper_version,
                            "prompt_sha256": r.prompt_sha256,
                            "terminator_required": r.terminator_required,
                            "seed": req_seed, "effort_mode": cfg["effort"]["mode"],
                        },
                    }
                    try:
                        comp = client.complete(
                            r.request_text_for_estimate(), effort, item_id,
                            max_tokens=cap, seed=req_seed, messages=r.messages,
                        )
                    except Exception as err:  # noqa: BLE001 — ledger the attempt, keep going
                        consecutive_errors += 1
                        ledger.append({
                            **base_event, "event_type": "error", "route_status": "request_failed",
                            "accounting_status": "none", "error_class": type(err).__name__,
                            "request_ended_at": _now(), "cached": False,
                        })
                        rows.append({"dataset": r.dataset, "item_id": item_id, "effort": effort, "error": str(err)})
                        print(f"  FAILED {item_id} @ {effort}: {err}")
                        if consecutive_errors >= breaker_n:
                            raise CircuitBreaker(f"{consecutive_errors} consecutive errors")
                        continue
                    consecutive_errors = 0
                    cost = actual_call_usd(cfg, comp)
                    guard.record(r.dataset, cost)
                    term = strict_terminator_present(comp.text)
                    ledger.append({
                        **base_event,
                        "event_type": "cache" if comp.cached else "success",
                        "route_status": "mock" if mock else "pinned",
                        "accounting_status": "mock" if mock else "usage_reported",
                        "served_provider": comp.provider, "generation_id": comp.generation_id,
                        "prompt_tokens": comp.prompt_tokens, "completion_tokens": comp.completion_tokens,
                        "reasoning_tokens": comp.reasoning_tokens, "finish_reason": comp.finish_reason,
                        "reported_cost_usd": comp.reported_cost_usd, "latency_s": comp.latency_s,
                        "cached": comp.cached, "extracted_answer_present": term,
                        "request_ended_at": _now(),
                        "billed_status": "mock" if mock else ("receipt_pending" if not comp.cached else "cached"),
                    })
                    resp_fh.write(json.dumps({
                        "dataset": r.dataset, "item_id": item_id, "effort": effort, "cap": cap,
                        "finish_reason": comp.finish_reason, "completion_tokens": comp.completion_tokens,
                        "reasoning_tokens": comp.reasoning_tokens, "prompt_tokens": comp.prompt_tokens,
                        "terminator_present": term, "terminator_required": r.terminator_required,
                        "response_text": comp.text, "reasoning_text": comp.reasoning_text,
                        "cached": comp.cached, "mock": mock,
                    }) + "\n")
                    resp_fh.flush()
                    rows.append({
                        "dataset": r.dataset, "item_id": item_id, "effort": effort,
                        "finish_reason": comp.finish_reason, "completion_tokens": comp.completion_tokens,
                        "terminator_present": term, "terminator_required": r.terminator_required,
                        "cost_usd": cost,
                    })
                    if len(rows) % 100 == 0 or n_total <= 10:
                        print(f"  {len(rows)}/{n_total}  spent ${guard.spent_total:.2f}")
        except CeilingHalt as err:
            halt, exit_code = f"ceiling_halt: {err}", EXIT_CEILING_HALT
            print(f"\nHALT before next call: {err}")
        except CircuitBreaker as err:
            halt, exit_code = f"circuit_breaker: {err}", EXIT_CIRCUIT_BREAKER
            print(f"\nHALT: {err}")

    summary = _summary(cfg, rows, guard, halt)
    summary["ledger"] = str(ledger.path.relative_to(ROOT)) if ledger.path.is_absolute() and ROOT in ledger.path.parents else str(ledger.path)
    summary["ledger_verified"] = ledger.verify()
    (out_dir / f"summary_{tag}_{stamp}.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"\n{'mock' if mock else 'LIVE'} run finished: {len(rows)} attempts, spent ${guard.spent_total:.2f}, "
          f"halt={halt or 'none'} -> {out_dir}")
    return summary, exit_code


def render_all(cfg: dict, items: list[dict]) -> list[Rendered]:
    seed = int(cfg["pilot"]["wrapper_seed"])
    return [render(row, seed=seed) for row in items]


def write_rendered_manifest(cfg: dict, selection: dict, rendered: list[Rendered], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "label": cfg["pilot"]["label"],
        "selection_sha256": selection["selection_sha256"],
        "selection_rule": selection["rule"],
        "wrapper_seed": cfg["pilot"]["wrapper_seed"],
        "cap": cfg["pilot"]["cap"],
        "content_free": True,
        "items": [r.manifest_row() for r in rendered],
    }
    path = out_dir / "rendered_manifest.json"
    path.write_text(json.dumps(manifest, indent=1) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config_pilot_inkling.yaml")
    ap.add_argument("--selection", default=None, help="override pilot.selection")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="cost table only (default)")
    mode.add_argument("--mock", action="store_true", help="fabricated responses, no API")
    mode.add_argument("--live", action="store_true", help="real calls; refuses unless every gate is open")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    sel_path = Path(args.selection or cfg["pilot"]["selection"])
    if not sel_path.is_absolute():
        sel_path = ROOT / sel_path
    selection = json.loads(sel_path.read_text())
    out_dir = ROOT / cfg["paths"]["results"]

    if args.live:
        fails = live_gate_failures(cfg)
        if fails:
            print("LIVE REFUSED. Open gates:")
            for f in fails:
                print(f"  - {f}")
            return EXIT_GATE_REFUSED

    items = load_selected_items(cfg, selection)
    rendered = render_all(cfg, items)
    manifest_path = write_rendered_manifest(cfg, selection, rendered, out_dir)
    print(f"{len(rendered)} items rendered with {rendered[0].wrapper_version if rendered else '-'}; "
          f"content-free manifest -> {manifest_path.relative_to(ROOT)}")

    if args.mock or args.live:
        _, code = run(cfg, rendered, mock=args.mock, out_dir=out_dir)
        return code
    dry_run(cfg, rendered, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
