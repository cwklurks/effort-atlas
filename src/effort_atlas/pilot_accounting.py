"""Durable, content-free accounting for the exploratory pilot only.

Reuses AttemptLedger's append/fsync/hash chain. A second lock serializes the
read/check/reserve transaction across processes. An outstanding request blocks
the account until reconciled, including after a crash or lost response.
"""
from __future__ import annotations

import fcntl
import json
import math
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from .confirmatory import AttemptLedger


class CeilingHalt(RuntimeError):
    pass


class AccountingHalt(RuntimeError):
    pass


def money(value: object) -> Decimal:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Accounting amounts must be finite nonnegative numbers")
    return Decimal(str(value))


class BudgetJournal:
    def __init__(self, path: Path, *, model: str, total_ceiling: float,
                 per_dataset_ceiling: float, pool_ceiling: float):
        self.ledger = AttemptLedger(path)
        self.model = model
        self.limits = {"total_ceiling": float(money(total_ceiling)),
                       "per_dataset_ceiling": float(money(per_dataset_ceiling)),
                       "pool_ceiling": float(money(pool_ceiling))}

    @contextmanager
    def _locked(self):
        path = self.ledger.path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_suffix(".lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                rows = [json.loads(line) for line in path.read_text().splitlines()
                        if line.strip()] if path.exists() else []
                self.ledger._verify_rows(rows)
                yield rows
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _state(self, rows):
        jobs = {}
        for row in rows:
            config = row.get("request_config", {})
            action = config.get("budget_action")
            job = row.get("job_id")
            if action == "reserve":
                if not job or job in jobs:
                    raise AccountingHalt("Duplicate or absent journal job identity")
                limits = config["budget_limits"]
                if money(limits["pool_ceiling"]) != money(self.limits["pool_ceiling"]):
                    raise AccountingHalt("Account allowance changed; explicit ledger reconciliation required")
                if row["model"] == self.model and any(
                    money(limits[k]) != money(self.limits[k])
                    for k in ("total_ceiling", "per_dataset_ceiling")
                ):
                    raise AccountingHalt("Model ceiling changed; explicit ledger reconciliation required")
                jobs[job] = {"reserve": row, "exposure": money(config["reserved_usd"]),
                             "settled": None}
            elif action in {"settle", "unresolved"}:
                if job not in jobs or jobs[job]["settled"] is not None:
                    raise AccountingHalt("Journal outcome without an outstanding reservation")
                state = jobs[job]
                if action == "settle":
                    state["exposure"] = money(row["receipt_cost_usd"])
                    state["settled"] = row
                elif config.get("known_exposure_usd") is not None:
                    state["exposure"] = max(state["exposure"], money(config["known_exposure_usd"]))
            else:
                raise AccountingHalt("Unknown event in the pilot budget journal")
        return jobs

    def snapshot(self):
        with self._locked() as rows:
            jobs = self._state(rows)
        spent, exposure = {}, {}
        for state in jobs.values():
            row = state["reserve"]
            if row["model"] == self.model:
                ds = row["domain"]
                exposure[ds] = exposure.get(ds, Decimal(0)) + state["exposure"]
                if state["settled"] is not None:
                    spent[ds] = spent.get(ds, Decimal(0)) + state["exposure"]
        return {"spent_by_dataset": {k: float(v) for k, v in spent.items()},
                "exposure_by_dataset": {k: float(v) for k, v in exposure.items()},
                "spent_total": float(sum(spent.values(), Decimal(0))),
                "exposure_total": float(sum(exposure.values(), Decimal(0))),
                "pool_exposure": float(sum((s["exposure"] for s in jobs.values()), Decimal(0))),
                "unresolved_jobs": sum(s["settled"] is None for s in jobs.values())}

    @property
    def spent_total(self):
        return self.snapshot()["spent_total"]

    @property
    def exposure_total(self):
        return self.snapshot()["exposure_total"]

    def completed(self, job_id):
        with self._locked() as rows:
            state = self._state(rows).get(job_id)
            return state["settled"] if state else None

    def reserve(self, event: dict, worst_usd: float):
        amount = money(worst_usd)
        with self._locked() as rows:
            jobs = self._state(rows)
            if event.get("model") != self.model or not event.get("domain") or not event.get("job_id"):
                raise AccountingHalt("Reservation identity is incomplete")
            if event["job_id"] in jobs:
                raise AccountingHalt("Job already attempted; automatic resubmission is forbidden")
            if any(s["settled"] is None for s in jobs.values()):
                raise AccountingHalt("Outstanding account exposure requires receipt reconciliation")
            dataset_total = model_total = pool_total = Decimal(0)
            for state in jobs.values():
                pool_total += state["exposure"]
                row = state["reserve"]
                if row["model"] == self.model:
                    model_total += state["exposure"]
                    if row["domain"] == event["domain"]:
                        dataset_total += state["exposure"]
            for label, used, limit in (
                ("per-dataset", dataset_total, "per_dataset_ceiling"),
                ("model total", model_total, "total_ceiling"),
                ("account", pool_total, "pool_ceiling"),
            ):
                if used + amount > money(self.limits[limit]):
                    raise CeilingHalt(f"{label} ceiling would be exceeded by the next reservation")
            self.ledger.append({**event, "event_type": "unaccounted",
                                "billed_status": "reserved", "accounting_status": "pending",
                                "request_config": {**event.get("request_config", {}),
                                                   "budget_action": "reserve",
                                                   "reserved_usd": float(amount),
                                                   "budget_limits": self.limits}})

    def settle(self, event: dict, cost_usd: float, *, generation_id: str):
        amount = money(cost_usd)
        with self._locked() as rows:
            jobs = self._state(rows)
            state = jobs.get(event["job_id"])
            if state is None or state["settled"] is not None:
                raise AccountingHalt("Settlement needs an outstanding reservation")
            if not generation_id or any(s["settled"] and
                s["settled"].get("generation_id") == generation_id for s in jobs.values()
            ):
                raise AccountingHalt("Missing or reused generation identity")
            if amount > state["exposure"]:
                self._append_unresolved(event, "ReservationExceeded", amount)
                raise AccountingHalt("Billed cost exceeded the reserved allowance")
            self.ledger.append({**event, "event_type": "success", "generation_id": generation_id,
                                "receipt_cost_usd": float(amount),
                                "request_config": {**event.get("request_config", {}),
                                                   "budget_action": "settle"}})

    def _append_unresolved(self, event, error_class, known_exposure=None):
        self.ledger.append({**event, "event_type": "unaccounted",
                            "billed_status": "unresolved", "accounting_status": "unresolved",
                            "error_class": error_class,
                            "request_config": {**event.get("request_config", {}),
                                               "budget_action": "unresolved",
                                               "known_exposure_usd": (float(known_exposure)
                                                                      if known_exposure is not None else None)}})

    def unresolved(self, event: dict, *, error_class: str, known_exposure_usd=None):
        known = money(known_exposure_usd) if known_exposure_usd is not None else None
        with self._locked() as rows:
            state = self._state(rows).get(event["job_id"])
            if state is None or state["settled"] is not None:
                raise AccountingHalt("Unresolved outcome needs an outstanding reservation")
            self._append_unresolved(event, error_class, known)
