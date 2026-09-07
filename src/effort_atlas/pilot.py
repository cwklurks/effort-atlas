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
  * live execution requires dated human evidence and approval of the exact
    inputs/configuration/host, plus an explicit environment acknowledgement;
  * the ledger (confirmatory.AttemptLedger, hash-chained, append-only) is
    content-free; responses and caches are gitignored because they can echo
    restricted questions. The original GPQA source remains restricted_local/.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
import statistics
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import ROOT, load_config
from .client import Completion, InklingClient
from .confirmatory import sha256_json
from .pilot_accounting import AccountingHalt, BudgetJournal, CeilingHalt, money
from .pilot_contract import ACCOUNT_LEDGER_PATH, configuration_failures, live_gate_failures, run_manifest
from .pilot_integrity import load_selected_items
from .pilot_receipts import validate_completion, reconcile_receipt, fetch_receipt
from .wrapper import Rendered, render, strict_terminator_present

LIVE_ACK_ENV = "EFFORT_ATLAS_PILOT_LIVE_ACK"
LIVE_ACK_VALUE = "I_HAVE_READ_THE_APPROVED_PREFLIGHT"
RESTRICTED_FILES = {"gpqa_main": "restricted_local/gpqa_main.RESTRICTED.jsonl"}
EXIT_GATE_REFUSED, EXIT_CEILING_HALT, EXIT_CIRCUIT_BREAKER = 2, 3, 4


# ── cost and ceilings ────────────────────────────────────────────────────────

def estimate_prompt_tokens(text: str) -> int:
    """Forecast heuristic only; spending reservations use an approved allowance."""
    return max(1, math.ceil(len(text) / 3))


def request_input_bytes(item: Rendered) -> int:
    messages = item.messages if item.messages is not None else [{"role": "user", "content": item.prompt}]
    return len(json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def worst_case_call_usd(cfg: dict, prompt_tokens: int) -> float:
    pr = cfg["pricing"]
    cap = int(cfg["pilot"]["cap"])
    return (cfg["pilot"]["input_token_allowance"] * pr["input_per_mtok"] + cap * pr["output_per_mtok"]) / 1e6


def expected_call_usd(cfg: dict, prompt_tokens: int, effort: str) -> float:
    pr = cfg["pricing"]
    cap = int(cfg["pilot"]["cap"])
    exp_out = pr["expected_output_tokens"][str(effort)]
    if pr.get("cap_bounds_billable_tokens", True):
        exp_out = min(exp_out, cap)
    return (prompt_tokens * pr["input_per_mtok"] + exp_out * pr["output_per_mtok"]) / 1e6


def actual_call_usd(cfg: dict, comp: Completion) -> float:
    if comp.cached:
        return 0.0
    if comp.reported_cost_usd is not None:
        return float(money(comp.reported_cost_usd))
    pr = cfg["pricing"]
    # OpenRouter completion usage includes the reasoning-token subset.
    return (comp.prompt_tokens * pr["input_per_mtok"] + comp.completion_tokens * pr["output_per_mtok"]) / 1e6


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
        key = self._cache_key(prompt, effort, max_tokens=max_tokens, seed=seed, messages=messages, item_id=item_id)
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


def _cell_summary(cfg: dict, rows: list[dict]) -> dict:
    cap = int(cfg["pilot"]["cap"])
    responses = [r for r in rows if not r.get("error")]
    tokens = [r["completion_tokens"] for r in responses]
    n = len(responses)
    length_stops = sum(r["finish_reason"] == "length" for r in responses)
    required = [r for r in responses if r["terminator_required"]]
    return {
        "attempts": len(rows), "responses": n, "errors": len(rows) - n,
        "length_stops": length_stops,
        "length_stop_rate": length_stops / n if n else None,
        "terminator_required": len(required),
        "terminator_present": sum(bool(r["terminator_present"]) for r in required),
        # Cap-censored rows also satisfy length >= c for c <= the collection cap.
        "p_length_ge": {str(c): sum(t >= c for t in tokens) / n if n else None
                        for c in cfg["pilot"]["report_caps"] if c <= cap},
        "median_completion_tokens": statistics.median(tokens) if n and length_stops < n / 2 else None,
        "mean_reported": False,
        "spend_usd": round(sum(r["cost_usd"] for r in responses), 4),
    }


def _summary(cfg: dict, rows: list[dict], guard: CeilingGuard, halt: str | None) -> dict:
    datasets: dict[str, list[dict]] = {}
    cells: dict[str, dict[str, list[dict]]] = {}
    for row in rows:
        dataset = row["dataset"]
        # Historical rows without effort remain visibly unidentified, never
        # assigned to a configured level by guesswork.
        effort = row.get("effort", "unspecified")
        datasets.setdefault(dataset, []).append(row)
        cells.setdefault(dataset, {}).setdefault(effort, []).append(row)
    return {
        "label": cfg["pilot"]["label"],
        "exploratory": True,
        "cap": int(cfg["pilot"]["cap"]),
        "datasets": {name: _cell_summary(cfg, group) for name, group in datasets.items()},
        "dataset_summary_scope": "pooled_across_efforts",
        "dataset_effort_cells": {
            dataset: {effort: _cell_summary(cfg, group) for effort, group in groups.items()}
            for dataset, groups in cells.items()
        },
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
        d = table.setdefault(r.dataset, {"items": 0, "est_prompt_tokens": 0, "expected_usd": 0.0,
                                        "worst_usd": 0.0, "requests_over_input_byte_limit": 0})
        d["items"] += 1
        d["est_prompt_tokens"] += est_in
        d["requests_over_input_byte_limit"] += int(request_input_bytes(r) > cfg["pilot"]["request_input_byte_limit"])
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
    print("\nDry run only. Reservations assume the configured input allowance, output cap and price limits are valid for the approved route. Human evidence is required.")
    report = {
        "mode": "dry_run", "generated_at": _now(), "levels": levels, "cap": cfg["pilot"]["cap"],
        "pricing": cfg["pricing"], "budget": guard_limits, "datasets": table,
        "reservation_input_allowance": cfg["pilot"]["input_token_allowance"],
        "input_admissible": not any(d["requests_over_input_byte_limit"] for d in table.values()),
        "expected_total_usd": round(tot_e, 4), "worst_total_usd": round(tot_w, 4),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dry_run.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


def _safe_metadata(comp) -> dict:
    """Allowlisted accounting only; never copy exception text or request content."""
    result = {}
    for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
        value = getattr(comp, key, None)
        if type(value) is int and value >= 0:
            result[key] = value
    for key in ("reported_cost_usd", "latency_s"):
        value = getattr(comp, key, None)
        if type(value) in (int, float) and math.isfinite(value) and value >= 0:
            result[key] = value
    import re
    for source, target in (("generation_id", "generation_id"), ("provider", "served_provider"),
                           ("finish_reason", "finish_reason")):
        value = getattr(comp, source, None)
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._:/-]{0,159}", value):
            result[target] = value
    return result


def _refused(failures):
    print("RUN REFUSED: " + "; ".join(failures))
    return {"exploratory": True, "halt": "gate_refused", "failures": failures}, EXIT_GATE_REFUSED


def run(cfg: dict, rendered: list[Rendered], *, mock: bool, out_dir: Path,
        client: InklingClient | None = None, receipt_fetcher=None) -> tuple[dict, int]:
    cfg = deepcopy(cfg)
    failures = configuration_failures(cfg)
    if failures:
        return _refused(failures)
    selection_digest = cfg.get("_selection_sha256", "synthetic")
    try:
        if not mock:
            # Direct Python callers pass through the same gates as the CLI.
            selection = json.loads((ROOT / cfg["pilot"]["selection"]).read_text())
            expected = render_all(cfg, load_selected_items(cfg, selection, cap_dir=ROOT / cfg["paths"]["data"]))
            selection_digest = selection["selection_sha256"]
            expected_manifest = run_manifest(cfg, expected, selection_digest)
            supplied_manifest = run_manifest(cfg, rendered, selection_digest)
            if expected_manifest != supplied_manifest:
                return _refused(["rendered inputs differ from the validated selection"])
            if out_dir.resolve() != (ROOT / cfg["paths"]["results"]).resolve():
                return _refused(["output directory differs from the approved configuration"])
        manifest = run_manifest(cfg, rendered, selection_digest)
        if not mock:
            failures = live_gate_failures(cfg, manifest_sha256=manifest["run_sha256"], root=ROOT)
            if failures:
                return _refused(failures)
        for item in rendered:
            if request_input_bytes(item) > cfg["pilot"]["request_input_byte_limit"]:
                return _refused(["request exceeds the approved input byte limit"])
    except (OSError, ValueError, KeyError, TypeError):
        return _refused(["selection, rendered inputs, or approval manifest is invalid"])

    cfg["_pilot_run_id"] = manifest["run_sha256"]
    tag = "mock" if mock else "live"
    stamp = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:12]
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / f"run_manifest_{tag}_{manifest['run_sha256']}.json"
    encoded_manifest = json.dumps(manifest, indent=1, allow_nan=False) + "\n"
    if manifest_path.exists() and manifest_path.read_text() != encoded_manifest:
        return _refused(["immutable run manifest already exists with different bytes"])
    if not manifest_path.exists():
        with manifest_path.open("x") as fh:
            fh.write(encoded_manifest)
    responses_path = out_dir / f"responses_{tag}_{stamp}.jsonl"
    budget = cfg["budget"]
    # All live models/stages share this fixed account journal. Output/cache paths
    # and new run labels cannot reset the account or per-model ceilings.
    ledger_path = out_dir / "ledger_mock.jsonl" if mock else ACCOUNT_LEDGER_PATH
    pool = (budget["total_ceiling_usd"] if mock else
            budget["balance_verified_usd"] - budget["reserve_margin_usd"])
    journal = BudgetJournal(ledger_path, model=cfg["provider"]["model"],
                            total_ceiling=budget["total_ceiling_usd"],
                            per_dataset_ceiling=budget["per_dataset_ceiling_usd"], pool_ceiling=pool)
    client = client or PilotClient(cfg, ROOT, mock=mock, live_authorized=not mock)
    # Injected mock clients stay useful for offline failure fixtures. Real clients
    # receive the same immutable scope before cache lookup.
    if hasattr(client, "cfg"):
        client.cfg = cfg
    fetch = receipt_fetcher or fetch_receipt
    cap, levels = cfg["pilot"]["cap"], cfg["effort"]["levels"]
    seed = cfg["pilot"]["request_seed"]
    pcfg = cfg["provider"]
    route = pcfg["request_extra_body"]["provider"]["only"][0].strip().casefold()
    rows, halt, exit_code, reused = [], None, 0, 0
    n_total = len(rendered) * len(levels)
    with responses_path.open("x", encoding="utf-8") as resp_fh:
        try:
            for r in rendered:
                for effort in levels:
                    item_id = f"{r.dataset}:{r.source_item_id}"
                    identity = {"model": pcfg["model"], "provider_route": route,
                                "item_id": item_id, "effort": effort, "cap": cap,
                                "seed": seed, "prompt_sha256": r.prompt_sha256, "mock": mock}
                    job_id = sha256_json(identity)
                    if journal.completed(job_id):
                        reused += 1
                        continue  # existing measurement, never another independent sample
                    kwargs = {"max_tokens": cap, "seed": seed, "messages": r.messages}
                    if hasattr(client, "cached_completion") and client.cached_completion(
                        r.request_text_for_estimate(), effort, item_id, **kwargs
                    ) is not None:
                        raise AccountingHalt("Cache entry lacks a reconciled journal job; manual reconciliation required")
                    event = {
                        "job_id": job_id, "panel": cfg["pilot"]["label"], "phase": "exploratory_pilot",
                        "model": pcfg["model"], "requested_provider": pcfg["name"],
                        "provider_route": route, "item_id": item_id, "domain": r.dataset,
                        "effort": effort, "cap": cap, "replicate": 1,
                        "max_tokens": cap, "max_tokens_requested": cap, "request_started_at": _now(),
                        "request_config": {"run_sha256": manifest["run_sha256"],
                                           "wrapper_version": r.wrapper_version,
                                           "prompt_sha256": r.prompt_sha256,
                                           "terminator_required": r.terminator_required,
                                           "seed": seed, "effort_mode": cfg["effort"]["mode"]},
                    }
                    journal.reserve(event, worst_case_call_usd(cfg, 0))
                    comp, known_cost = None, None
                    try:
                        comp = client.complete(r.request_text_for_estimate(), effort, item_id, **kwargs)
                        event.update(_safe_metadata(comp))
                        event["request_ended_at"] = _now()
                        known_cost = event.get("reported_cost_usd")
                        if comp.cached:
                            raise AccountingHalt("Unjournaled cache response cannot become a fresh measurement")
                        validate_completion(cfg, comp, mock=mock)
                        term = strict_terminator_present(comp.text)
                        resp_fh.write(json.dumps({
                            "job_id": job_id, "run_sha256": manifest["run_sha256"],
                            "dataset": r.dataset, "item_id": item_id, "effort": effort, "cap": cap,
                            **_safe_metadata(comp), "terminator_present": term,
                            "terminator_required": r.terminator_required,
                            "response_text": comp.text, "reasoning_text": comp.reasoning_text,
                            "cached": False, "mock": mock,
                        }, allow_nan=False) + "\n")
                        resp_fh.flush()
                        os.fsync(resp_fh.fileno())
                        if mock:
                            cost = actual_call_usd(cfg, comp)
                            event.update(route_status="mock", accounting_status="mock", billed_status="mock")
                        else:
                            # Preserve the generation ID and usage before any receipt race/crash.
                            journal.unresolved(event, error_class="ReceiptPending", known_exposure_usd=known_cost)
                            payload = fetch(cfg, comp.generation_id)
                            if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
                                data = payload["data"]
                                amount = data.get("total_cost")
                                if data.get("id") == comp.generation_id and type(amount) in (int, float) and math.isfinite(amount) and amount >= 0:
                                    known_cost = max(known_cost or 0, amount)
                            receipt = reconcile_receipt(cfg, comp, payload)
                            event.update(receipt)
                            cost = receipt["receipt_cost_usd"]
                            event.update(route_status="expected", accounting_status="valid", billed_status="reconciled")
                        event.update(cached=False, extracted_answer_present=term)
                        journal.settle(event, cost, generation_id=comp.generation_id)
                    except (Exception, KeyboardInterrupt, SystemExit) as err:
                        if comp is None:
                            from types import SimpleNamespace
                            event.update(_safe_metadata(SimpleNamespace(**getattr(err, "metadata", {}))))
                            known_cost = event.get("reported_cost_usd")
                        event["request_ended_at"] = _now()
                        journal.unresolved(event, error_class=type(err).__name__, known_exposure_usd=known_cost)
                        rows.append({"dataset": r.dataset, "item_id": item_id, "effort": effort,
                                     "error": "accounting_unresolved"})
                        raise AccountingHalt("Attempt unresolved; reservation retained, further submissions blocked") from None
                    rows.append({"dataset": r.dataset, "item_id": item_id, "effort": effort,
                                 "finish_reason": comp.finish_reason, "completion_tokens": comp.completion_tokens,
                                 "terminator_present": term, "terminator_required": r.terminator_required,
                                 "cost_usd": cost})
                    if len(rows) % 100 == 0 or n_total <= 10:
                        print(f"  {len(rows)}/{n_total}  accounted ${journal.spent_total:.2f}")
        except CeilingHalt as err:
            halt, exit_code = f"ceiling_halt: {err}", EXIT_CEILING_HALT
        except (AccountingHalt, ValueError):
            halt, exit_code = "accounting_halt: ledger reconciliation required", EXIT_CIRCUIT_BREAKER
    try:
        snapshot = journal.snapshot()
        guard = CeilingGuard(budget["per_dataset_ceiling_usd"], budget["total_ceiling_usd"],
                             snapshot["spent_by_dataset"])
        summary = _summary(cfg, rows, guard, halt)
        summary.update(snapshot)
        verified = journal.ledger.verify()
    except (AccountingHalt, ValueError, OSError):
        summary = {"exploratory": True, "halt": "accounting_halt: invalid journal", "datasets": {}}
        exit_code, verified = EXIT_CIRCUIT_BREAKER, False
    summary.update(ledger=str(ledger_path), ledger_verified=verified,
                   run_sha256=manifest["run_sha256"], already_completed_jobs=reused,
                   statistics_scope="new reconciled observations in this invocation",
                   mock=mock, responses=str(responses_path))
    (out_dir / f"summary_{tag}_{stamp}.json").write_text(json.dumps(summary, indent=1, allow_nan=False) + "\n")
    print(f"\n{tag} run: {len(rows)} new attempts, {reused} already completed; halt={summary['halt'] or 'none'}")
    return summary, exit_code


def render_all(cfg: dict, items: list[dict]) -> list[Rendered]:
    seed = int(cfg["pilot"]["wrapper_seed"])
    return [render(row, seed=seed) for row in items]


def write_rendered_manifest(cfg: dict, selection: dict, rendered: list[Rendered], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_manifest(cfg, rendered, selection["selection_sha256"])
    path = out_dir / f"rendered_manifest_{manifest['run_sha256']}.json"
    content = json.dumps(manifest, indent=1, allow_nan=False) + "\n"
    if path.exists() and path.read_text() != content:
        raise ValueError("Immutable rendered manifest differs from existing bytes")
    if not path.exists():
        with path.open("x") as fh:
            fh.write(content)
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
    failures = configuration_failures(cfg)
    if failures:
        return _refused(failures)[1]
    if args.selection:
        cfg["pilot"]["selection"] = args.selection
    if args.live and cfg["pilot"]["enabled"] is not True:
        return _refused(live_gate_failures(cfg, root=ROOT))[1]
    try:
        sel_path = ROOT / cfg["pilot"]["selection"]
        selection = json.loads(sel_path.read_text())
        items = load_selected_items(cfg, selection, cap_dir=ROOT / cfg["paths"]["data"])
        rendered = render_all(cfg, items)
        cfg["_selection_sha256"] = selection["selection_sha256"]
        out_dir = ROOT / cfg["paths"]["results"]
        if args.live:
            failures = live_gate_failures(cfg, manifest_sha256=run_manifest(cfg, rendered, selection["selection_sha256"])["run_sha256"], root=ROOT)
            if failures:
                return _refused(failures)[1]
        manifest_path = write_rendered_manifest(cfg, selection, rendered, out_dir)
    except (OSError, ValueError, TypeError, KeyError):
        return _refused(["selection or immutable rendered manifest validation failed"])[1]
    print(f"{len(rendered)} items rendered; content-free manifest -> {manifest_path}")

    if args.mock or args.live:
        _, code = run(cfg, rendered, mock=args.mock, out_dir=out_dir)
        return code
    dry_run(cfg, rendered, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
