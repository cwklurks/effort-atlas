"""Offline whole-stage accounting for the exploratory Tinker baseline.

This module contains no provider client or transport.  It reserves a complete
stage before its first attempt and releases that exposure only after normalized
aggregate billing evidence reconciles exactly with the recorded response usage.
"""
from __future__ import annotations

import fcntl
import json
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Sequence

from .confirmatory import AttemptLedger, sha256_json
from .pilot_accounting import AccountingHalt, CeilingHalt


STAGES = ("medium", "max")
NATIVE_STOP_REASONS = frozenset({"end_turn", "max_tokens"})
PRODUCTION_ITEM_COUNT = 1000
PRODUCTION_MAX_TOKENS = 32768
ACCOUNTING_SCHEMA_VERSION = "inkling-stage-accounting-v1"
PANEL = "inkling_baseline"
MILLION = Decimal(1_000_000)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_ERROR_CLASS_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.]{0,127}\Z")


@dataclass(frozen=True)
class BillingEvidence:
    """Normalized billing evidence produced from read-only provider exports."""

    account_sha256: str
    billing_group_sha256: str
    model: str
    window_start: datetime
    window_end: datetime
    prompt_tokens: int
    completion_tokens: int
    account_deduction_usd: Decimal
    manifest_sha256: str
    source_sha256s: tuple[str, ...]
    complete: bool


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _require_positive_int(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _require_decimal(name: str, value: object, *, positive: bool) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be a finite {qualifier} Decimal")
    if (positive and value <= 0) or (not positive and value < 0):
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be a finite {qualifier} Decimal")
    return value


def _policy_money(name: str, value: object, *, positive: bool = True) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
        raise ValueError(f"policy {name} must be an exact decimal value")
    try:
        amount = Decimal(str(value))
    except Exception as exc:  # Decimal raises several arithmetic subclasses.
        raise ValueError(f"policy {name} must be an exact decimal value") from exc
    if not amount.is_finite() or (amount <= 0 if positive else amount < 0):
        raise ValueError(f"policy {name} must be {'positive' if positive else 'nonnegative'}")
    return amount


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _require_stage(stage: object) -> str:
    if stage not in STAGES:
        raise ValueError("stage must be 'medium' or 'max'")
    return str(stage)


def _utc_instant(value: datetime | None = None) -> datetime:
    instant = value if value is not None else datetime.now(timezone.utc)
    if not isinstance(instant, datetime) or instant.tzinfo is None:
        raise ValueError("time must be a timezone-aware datetime")
    if instant.utcoffset() != timezone.utc.utcoffset(instant):
        raise ValueError("time must use UTC")
    return instant.astimezone(timezone.utc)


def _utc_hour(name: str, value: datetime | str) -> tuple[datetime, str]:
    if isinstance(value, str):
        if not (value.endswith("Z") or value.endswith("+00:00")):
            raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
        try:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an RFC3339 UTC timestamp") from exc
        instant = _utc_instant(instant)
    else:
        instant = _utc_instant(value)
    if any((instant.minute, instant.second, instant.microsecond)):
        raise ValueError(f"{name} must be an exact UTC whole-hour boundary")
    return instant, instant.strftime("%Y-%m-%dT%H:00:00Z")


def _event_time(value: datetime) -> str:
    return _utc_instant(value).isoformat().replace("+00:00", "Z")


def _parse_event_time(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AccountingHalt("Journal event time is malformed")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AccountingHalt("Journal event time is malformed") from exc


def _parse_money(name: str, value: object) -> Decimal:
    if not isinstance(value, str):
        raise AccountingHalt(f"Journal {name} is malformed")
    try:
        amount = Decimal(value)
    except Exception as exc:
        raise AccountingHalt(f"Journal {name} is malformed") from exc
    if not amount.is_finite() or amount < 0 or _decimal_text(amount) != value:
        raise AccountingHalt(f"Journal {name} is malformed")
    return amount


class InklingStageJournal:
    """Durable state machine for one medium stage and one conditional max stage."""

    def __init__(
        self,
        path: str | Path,
        *,
        policy: dict[str, Any],
        plan_sha256: str,
        account_sha256: str,
        billing_group_sha256: str,
        item_ids: Sequence[str],
        synthetic: bool = False,
    ):
        if not isinstance(policy, dict):
            raise ValueError("policy must be a dictionary")
        self.policy = json.loads(json.dumps(policy))
        self.policy_sha256 = sha256_json(self.policy)
        self.plan_sha256 = _require_sha256("plan_sha256", plan_sha256)
        self.account_sha256 = _require_sha256("account_sha256", account_sha256)
        self.billing_group_sha256 = _require_sha256(
            "billing_group_sha256", billing_group_sha256
        )
        if type(synthetic) is not bool:
            raise ValueError("synthetic must be a boolean")
        self.synthetic = synthetic
        self.phase = "mock_only" if synthetic else "exploratory_tinker_baseline"
        self.ledger = AttemptLedger(path)

        if self.policy.get("schema_version") != "inkling-stage-policy-v1":
            raise ValueError("unsupported Inkling accounting policy schema")
        if self.policy.get("decision") != "whole_stage_reservation_then_aggregate_reconciliation":
            raise ValueError("policy does not approve whole-stage accounting")
        if self.policy.get("phase") != "exploratory":
            raise ValueError("Inkling stage accounting is exploratory only")
        if self.policy.get("maximum_requires_reconciled_uncapped_medium") is not True:
            raise ValueError("policy must require reconciled, uncapped medium before max")
        if not isinstance(self.policy.get("model"), str) or not self.policy["model"]:
            raise ValueError("policy model is missing")
        self.model = self.policy["model"]
        self.max_tokens = _require_positive_int("policy max_tokens", self.policy.get("max_tokens"))
        self.item_count = _require_positive_int(
            "policy items_per_stage", self.policy.get("items_per_stage")
        )
        if isinstance(item_ids, (str, bytes)):
            raise ValueError("item_ids must be an ordered sequence")
        self.item_ids = tuple(item_ids)
        if (
            len(self.item_ids) != self.item_count
            or any(not isinstance(item, str) or not item for item in self.item_ids)
            or len(set(self.item_ids)) != len(self.item_ids)
        ):
            raise ValueError("item_ids must be unique, nonempty, and match items_per_stage")

        ceilings = self.policy.get("stage_ceilings_usd")
        if not isinstance(ceilings, dict) or set(ceilings) != set(STAGES):
            raise ValueError("policy must provide medium and max stage ceilings")
        self.stage_ceilings = {
            stage: _policy_money(f"stage_ceilings_usd.{stage}", ceilings[stage])
            for stage in STAGES
        }
        self.combined_ceiling = _policy_money(
            "combined_ceiling_usd", self.policy.get("combined_ceiling_usd")
        )
        self.research_reserve = _policy_money(
            "research_reserve_usd", self.policy.get("research_reserve_usd")
        )
        if sum(self.stage_ceilings.values(), Decimal(0)) > self.combined_ceiling:
            raise ValueError("stage ceilings exceed the combined approved ceiling")
        _require_sha256(
            "policy approval_record_sha256", self.policy.get("approval_record_sha256")
        )

    @contextmanager
    def _locked(self) -> Iterator[list[dict[str, Any]]]:
        path = self.ledger.path
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + ".stage.lock")
        with lock_path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                rows = (
                    [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
                    if path.exists()
                    else []
                )
                self.ledger._verify_rows(rows)
                yield rows
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _empty_state(self) -> dict[str, Any]:
        return {
            "stages": {
                stage: {
                    "reserved": False,
                    "attempts": {},
                    "blocked": False,
                    "finished": False,
                    "reconciled": False,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "length_stops": 0,
                    "deduction": Decimal(0),
                }
                for stage in STAGES
            },
            "request_ids": set(),
            "provider_response_ids": set(),
        }

    def _verify_binding(self, row: dict[str, Any], config: dict[str, Any]) -> str:
        expected_config = {
            "schema_version": ACCOUNTING_SCHEMA_VERSION,
            "policy_sha256": self.policy_sha256,
            "plan_sha256": self.plan_sha256,
            "account_sha256": self.account_sha256,
            "billing_group_sha256": self.billing_group_sha256,
            "synthetic": self.synthetic,
        }
        if any(config.get(key) != value for key, value in expected_config.items()):
            raise AccountingHalt("Ledger policy, plan, account, or billing identity changed")
        if (
            row.get("panel") != PANEL
            or row.get("model") != self.model
            or row.get("phase") != self.phase
            or row.get("cap") != self.max_tokens
            or row.get("replicate") != 1
            or row.get("domain") != "all"
        ):
            raise AccountingHalt("Ledger row is outside the bound Inkling stage plan")
        return _require_stage(row.get("effort"))

    def _stage_job_id(self, stage: str) -> str:
        return sha256_json(
            {"plan_sha256": self.plan_sha256, "stage": stage, "scope": "stage"}
        )

    def attempt_job_id(self, stage: str, item_id: str) -> str:
        stage = _require_stage(stage)
        if item_id not in self.item_ids:
            raise ValueError("item_id is outside the bound plan")
        return sha256_json(
            {"plan_sha256": self.plan_sha256, "stage": stage, "item_id": item_id}
        )

    def _base_config(self, action: str) -> dict[str, Any]:
        return {
            "schema_version": ACCOUNTING_SCHEMA_VERSION,
            "accounting_action": action,
            "policy_sha256": self.policy_sha256,
            "plan_sha256": self.plan_sha256,
            "account_sha256": self.account_sha256,
            "billing_group_sha256": self.billing_group_sha256,
            "synthetic": self.synthetic,
        }

    def _base_event(
        self, stage: str, action: str, *, item_id: str = "__stage__"
    ) -> dict[str, Any]:
        return {
            "job_id": (
                self._stage_job_id(stage)
                if item_id == "__stage__"
                else self.attempt_job_id(stage, item_id)
            ),
            "panel": PANEL,
            "model": self.model,
            "domain": "all",
            "item_id": item_id,
            "effort": stage,
            "cap": self.max_tokens,
            "replicate": 1,
            "phase": self.phase,
            "request_config": self._base_config(action),
        }

    def _stage_config(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            **self._base_config(""),
            "input_allowance": state["input_allowance"],
            "input_rate_per_million": _decimal_text(state["input_rate"]),
            "output_rate_per_million": _decimal_text(state["output_rate"]),
            "original_stage_bound_usd": _decimal_text(state["bound"]),
            "approved_stage_ceiling_usd": _decimal_text(state["ceiling"]),
            "window_start": state["window_start_text"],
            "window_end": state["window_end_text"],
        }

    def _add_stage_config(self, event: dict[str, Any], state: dict[str, Any]) -> None:
        action = event["request_config"]["accounting_action"]
        event["request_config"] = {
            **self._stage_config(state),
            "accounting_action": action,
        }

    def _load_stage_config(self, config: dict[str, Any], stage: str) -> dict[str, Any]:
        allowance = config.get("input_allowance")
        if type(allowance) is not int or allowance <= 0:
            raise AccountingHalt("Journal input allowance is malformed")
        input_rate = _parse_money("input rate", config.get("input_rate_per_million"))
        output_rate = _parse_money("output rate", config.get("output_rate_per_million"))
        if input_rate <= 0 or output_rate <= 0:
            raise AccountingHalt("Journal rates must be positive")
        bound = _parse_money("original stage bound", config.get("original_stage_bound_usd"))
        ceiling = _parse_money("approved stage ceiling", config.get("approved_stage_ceiling_usd"))
        if ceiling != self.stage_ceilings[stage]:
            raise AccountingHalt("Journal stage ceiling differs from approved policy")
        start = self._parse_hour_text("window_start", config.get("window_start"))
        end = self._parse_hour_text("window_end", config.get("window_end"))
        if end <= start:
            raise AccountingHalt("Journal billing window is invalid")
        expected_bound = self._worst_bound(allowance, input_rate, output_rate)
        if bound != expected_bound or bound > ceiling:
            raise AccountingHalt("Journal stage bound does not match its approved inputs")
        return {
            "input_allowance": allowance,
            "input_rate": input_rate,
            "output_rate": output_rate,
            "bound": bound,
            "ceiling": ceiling,
            "window_start": start,
            "window_end": end,
            "window_start_text": config["window_start"],
            "window_end_text": config["window_end"],
        }

    @staticmethod
    def _parse_hour_text(name: str, value: object) -> datetime:
        if not isinstance(value, str):
            raise AccountingHalt(f"Journal {name} is malformed")
        try:
            instant = datetime.strptime(value, "%Y-%m-%dT%H:00:00Z").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise AccountingHalt(f"Journal {name} is malformed") from exc
        return instant

    def _same_stage_config(
        self, config: dict[str, Any], stage_state: dict[str, Any]
    ) -> None:
        expected = self._stage_config(stage_state)
        expected.pop("accounting_action")
        if any(config.get(key) != value for key, value in expected.items()):
            raise AccountingHalt("Stage configuration changed within the ledger")

    def _state(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        state = self._empty_state()
        for row in rows:
            config = row.get("request_config")
            if not isinstance(config, dict):
                raise AccountingHalt("Inkling accounting row lacks request_config")
            stage = self._verify_binding(row, config)
            action = config.get("accounting_action")
            if action not in {
                "reserve_stage", "begin_attempt", "record_response",
                "block_attempt", "block_stage", "finish_stage",
                "block_reconciliation", "settle_stage",
            }:
                raise AccountingHalt("Unknown event in the Inkling accounting journal")
            current = state["stages"][stage]

            if action == "reserve_stage":
                if current["reserved"] or row.get("item_id") != "__stage__":
                    raise AccountingHalt("Stage reservation is duplicated or malformed")
                if row.get("job_id") != self._stage_job_id(stage):
                    raise AccountingHalt("Stage reservation identity is malformed")
                if row.get("event_type") != "unaccounted":
                    raise AccountingHalt("Stage reservation event is malformed")
                current.update(self._load_stage_config(config, stage))
                verified_balance = _parse_money(
                    "verified balance", config.get("verified_balance_usd")
                )
                _require_sha256(
                    "balance_evidence_sha256", config.get("balance_evidence_sha256")
                )
                prior_exposure = sum(
                    other.get("bound", Decimal(0))
                    for other in state["stages"].values()
                    if other["reserved"] and not other["reconciled"]
                )
                if verified_balance < self.research_reserve + prior_exposure + current["bound"]:
                    raise AccountingHalt("Recorded balance did not cover reserve and exposure")
                prior_bounds = sum(
                    other.get("bound", Decimal(0))
                    for other in state["stages"].values()
                    if other["reserved"]
                )
                if prior_bounds + current["bound"] > self.combined_ceiling:
                    raise AccountingHalt("Recorded stage bounds exceed the combined ceiling")
                if stage == "medium" and state["stages"]["max"]["reserved"]:
                    raise AccountingHalt("Medium must be the first Inkling stage")
                if stage == "max":
                    medium = state["stages"]["medium"]
                    if not medium["reconciled"] or medium["blocked"] or medium["length_stops"]:
                        raise AccountingHalt("Max requires reconciled medium with zero cap stops")
                    if any(
                        current[key] != medium[key]
                        for key in ("input_allowance", "input_rate", "output_rate", "bound")
                    ):
                        raise AccountingHalt("Max must reuse the medium accounting configuration")
                    if current["window_start"] < medium["window_end"]:
                        raise AccountingHalt("Max billing window overlaps medium")
                current["reserved"] = True
                continue

            if not current["reserved"]:
                raise AccountingHalt("Journal action precedes its stage reservation")
            self._same_stage_config(config, current)

            if action == "begin_attempt":
                item_id = row.get("item_id")
                request_id = row.get("request_id")
                if (
                    current["blocked"] or current["finished"] or current["reconciled"]
                    or item_id not in self.item_ids or item_id in current["attempts"]
                    or not isinstance(request_id, str) or not request_id
                    or request_id in state["request_ids"]
                    or row.get("job_id") != self.attempt_job_id(stage, item_id)
                    or row.get("event_type") != "unaccounted"
                ):
                    raise AccountingHalt("Attempt start violates the fixed stage plan")
                if any(
                    attempt["status"] == "pending"
                    for other in state["stages"].values()
                    for attempt in other["attempts"].values()
                ):
                    raise AccountingHalt("Parallel pending attempts are forbidden")
                expected_item = self.item_ids[len(current["attempts"])]
                if item_id != expected_item:
                    raise AccountingHalt("Attempts must follow the bound item order")
                started = _parse_event_time(row.get("request_started_at"))
                if not current["window_start"] <= started < current["window_end"]:
                    raise AccountingHalt("Attempt start lies outside its billing window")
                current["attempts"][item_id] = {
                    "status": "pending", "request_id": request_id,
                    "request_started_at": row["request_started_at"],
                }
                state["request_ids"].add(request_id)
                continue

            if action == "block_stage":
                if current["finished"] or current["reconciled"]:
                    raise AccountingHalt("Finished stage cannot be blocked before transport")
                current["blocked"] = True
                current["block_reason"] = row.get("error_class")
                continue

            if action in {"record_response", "block_attempt"}:
                item_id = row.get("item_id")
                attempt = current["attempts"].get(item_id)
                if (
                    attempt is None or attempt["status"] != "pending"
                    or row.get("job_id") != self.attempt_job_id(stage, item_id)
                    or row.get("request_id") != attempt["request_id"]
                ):
                    raise AccountingHalt("Attempt outcome lacks one matching pending attempt")
                if action == "block_attempt":
                    attempt["status"] = "blocked"
                    attempt["error_class"] = row.get("error_class")
                    current["blocked"] = True
                    current["block_reason"] = row.get("error_class")
                    continue

                provider_id = row.get("provider_response_id")
                response_sha256 = config.get("response_sha256")
                prompt_tokens = row.get("prompt_tokens")
                completion_tokens = row.get("completion_tokens")
                stop = row.get("native_finish_reason")
                ended = _parse_event_time(row.get("request_ended_at"))
                started = _parse_event_time(attempt["request_started_at"])
                if (
                    row.get("event_type") != "success"
                    or not isinstance(provider_id, str) or not provider_id
                    or provider_id in state["provider_response_ids"]
                    or _SHA256_RE.fullmatch(response_sha256 or "") is None
                    or type(prompt_tokens) is not int or prompt_tokens <= 0
                    or type(completion_tokens) is not int or completion_tokens <= 0
                    or prompt_tokens > current["input_allowance"]
                    or completion_tokens > self.max_tokens
                    or stop not in NATIVE_STOP_REASONS
                    or ended < started
                    or not current["window_start"] <= ended < current["window_end"]
                ):
                    raise AccountingHalt("Recorded response violates the accounting contract")
                attempt.update({
                    "status": "complete", "provider_response_id": provider_id,
                    "response_sha256": response_sha256,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "native_stop_reason": stop,
                    "request_ended_at": row["request_ended_at"],
                })
                state["provider_response_ids"].add(provider_id)
                current["prompt_tokens"] += prompt_tokens
                current["completion_tokens"] += completion_tokens
                current["length_stops"] += int(stop == "max_tokens")
                continue

            if action == "finish_stage":
                if (
                    current["blocked"] or current["finished"] or current["reconciled"]
                    or tuple(current["attempts"]) != self.item_ids
                    or any(a["status"] != "complete" for a in current["attempts"].values())
                    or row.get("item_id") != "__stage__"
                    or row.get("event_type") != "success"
                ):
                    raise AccountingHalt("Stage cannot finish without every planned response")
                current["finished"] = True
                continue

            if action == "block_reconciliation":
                if not current["finished"] or current["reconciled"]:
                    raise AccountingHalt("Reconciliation block is out of sequence")
                current["blocked"] = True
                current["block_reason"] = row.get("error_class")
                continue

            if action == "settle_stage":
                if current["blocked"] or not current["finished"] or current["reconciled"]:
                    raise AccountingHalt("Stage settlement is out of sequence")
                # These exact keys are the accounting-safe token names allowed by
                # AttemptLedger's recursive sanitizer.
                evidence_prompt = config.get("prompt_tokens")
                evidence_completion = config.get("completion_tokens")
                if (
                    type(evidence_prompt) is not int
                    or type(evidence_completion) is not int
                    or evidence_prompt != current["prompt_tokens"]
                    or evidence_completion != current["completion_tokens"]
                    or config.get("evidence_window_start") != current["window_start_text"]
                    or config.get("evidence_window_end") != current["window_end_text"]
                ):
                    raise AccountingHalt("Settled evidence totals or window changed")
                _require_sha256("evidence_manifest_sha256", config.get("evidence_manifest_sha256"))
                source_hashes = config.get("evidence_source_sha256s")
                if (
                    not isinstance(source_hashes, list) or not source_hashes
                    or any(_SHA256_RE.fullmatch(value or "") is None for value in source_hashes)
                ):
                    raise AccountingHalt("Settled evidence hashes are malformed")
                deduction = _parse_money(
                    "account deduction", config.get("account_deduction_usd")
                )
                calculated = self._actual_cost(current)
                if (
                    deduction != calculated
                    or config.get("calculated_cost_usd") != _decimal_text(calculated)
                    or deduction > current["bound"]
                    or deduction > current["ceiling"]
                ):
                    raise AccountingHalt("Settled deduction does not match approved rates")
                prior_spent = sum(
                    other["deduction"] for other in state["stages"].values()
                    if other["reconciled"]
                )
                if prior_spent + deduction > self.combined_ceiling:
                    raise AccountingHalt("Settled deductions exceed the combined ceiling")
                current["deduction"] = deduction
                current["reconciled"] = True
                current["evidence_manifest_sha256"] = config["evidence_manifest_sha256"]
                current["evidence_source_sha256s"] = tuple(source_hashes)
        return state

    def _worst_bound(
        self, input_allowance: int, input_rate: Decimal, output_rate: Decimal
    ) -> Decimal:
        return (
            Decimal(self.item_count)
            * (
                Decimal(input_allowance) * input_rate
                + Decimal(self.max_tokens) * output_rate
            )
            / MILLION
        )

    @staticmethod
    def _actual_cost(stage_state: dict[str, Any]) -> Decimal:
        return (
            Decimal(stage_state["prompt_tokens"]) * stage_state["input_rate"]
            + Decimal(stage_state["completion_tokens"]) * stage_state["output_rate"]
        ) / MILLION

    def _active_exposure(self, state: dict[str, Any]) -> Decimal:
        return sum(
            stage.get("bound", Decimal(0))
            for stage in state["stages"].values()
            if stage["reserved"] and not stage["reconciled"]
        )

    def reserve_stage(
        self,
        stage: str,
        *,
        input_allowance: int,
        input_rate_per_million: Decimal,
        output_rate_per_million: Decimal,
        verified_balance_usd: Decimal,
        balance_evidence_sha256: str,
        window_start: datetime | str,
        window_end: datetime | str,
    ) -> dict[str, Any]:
        stage = _require_stage(stage)
        allowance = _require_positive_int("input_allowance", input_allowance)
        input_rate = _require_decimal(
            "input_rate_per_million", input_rate_per_million, positive=True
        )
        output_rate = _require_decimal(
            "output_rate_per_million", output_rate_per_million, positive=True
        )
        balance = _require_decimal(
            "verified_balance_usd", verified_balance_usd, positive=False
        )
        balance_hash = _require_sha256(
            "balance_evidence_sha256", balance_evidence_sha256
        )
        start, start_text = _utc_hour("window_start", window_start)
        end, end_text = _utc_hour("window_end", window_end)
        if end <= start:
            raise ValueError("billing window end must follow its start")
        now = datetime.now(timezone.utc)
        if now >= end:
            raise ValueError("billing window has already expired")
        bound = self._worst_bound(allowance, input_rate, output_rate)
        ceiling = self.stage_ceilings[stage]
        if bound > ceiling:
            raise CeilingHalt("whole-stage worst-case bound exceeds its approved ceiling")

        with self._locked() as rows:
            state = self._state(rows)
            current = state["stages"][stage]
            if current["reserved"]:
                raise AccountingHalt("Stage is already reserved")
            if any(other["blocked"] for other in state["stages"].values()):
                raise AccountingHalt("A blocked stage retains exposure and stops later work")
            if stage == "medium":
                if any(other["reserved"] for other in state["stages"].values()):
                    raise AccountingHalt("Medium must be the first and only initial stage")
            else:
                medium = state["stages"]["medium"]
                if not medium["reconciled"] or medium["length_stops"]:
                    raise AccountingHalt("Max requires reconciled medium with zero cap stops")
                if any(
                    value != medium[key]
                    for value, key in (
                        (allowance, "input_allowance"),
                        (input_rate, "input_rate"),
                        (output_rate, "output_rate"),
                        (bound, "bound"),
                    )
                ):
                    raise AccountingHalt("Max must reuse the medium accounting configuration")
                if start < medium["window_end"]:
                    raise AccountingHalt("Max billing window must not overlap medium")
            existing_bounds = sum(
                other.get("bound", Decimal(0))
                for other in state["stages"].values()
                if other["reserved"]
            )
            if existing_bounds + bound > self.combined_ceiling:
                raise CeilingHalt("whole-stage bounds exceed the combined approved ceiling")
            exposure = self._active_exposure(state)
            if balance < self.research_reserve + exposure + bound:
                raise CeilingHalt("verified balance does not preserve reserve plus exposure")

            event = self._base_event(stage, "reserve_stage")
            event.update({
                "event_type": "unaccounted",
                "accounting_status": "stage_reserved",
                "billed_status": "held",
            })
            event["request_config"].update({
                "input_allowance": allowance,
                "input_rate_per_million": _decimal_text(input_rate),
                "output_rate_per_million": _decimal_text(output_rate),
                "original_stage_bound_usd": _decimal_text(bound),
                "approved_stage_ceiling_usd": _decimal_text(ceiling),
                "verified_balance_usd": _decimal_text(balance),
                "balance_evidence_sha256": balance_hash,
                "window_start": start_text,
                "window_end": end_text,
            })
            return self.ledger.append(event)

    def _require_collecting_stage(
        self, state: dict[str, Any], stage: str
    ) -> dict[str, Any]:
        current = state["stages"][stage]
        if (
            not current["reserved"] or current["blocked"]
            or current["finished"] or current["reconciled"]
        ):
            raise AccountingHalt("Stage is not open for collection")
        return current

    def _block_stage_locked(
        self, stage: str, current: dict[str, Any], error_class: str
    ) -> dict[str, Any]:
        event = self._base_event(stage, "block_stage")
        self._add_stage_config(event, current)
        event.update({
            "event_type": "unaccounted", "accounting_status": "blocked",
            "billed_status": "held", "error_class": error_class,
        })
        return self.ledger.append(event)

    def begin_attempt(
        self,
        stage: str,
        *,
        item_id: str,
        request_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        stage = _require_stage(stage)
        if item_id not in self.item_ids:
            raise ValueError("item_id is outside the bound plan")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a nonempty local submission identity")
        instant = _utc_instant(now)
        with self._locked() as rows:
            state = self._state(rows)
            current = self._require_collecting_stage(state, stage)
            if instant < current["window_start"]:
                raise AccountingHalt("Stage billing window has not started")
            if instant >= current["window_end"]:
                self._block_stage_locked(stage, current, "BillingWindowExpired")
                raise AccountingHalt("Stage billing window expired before transport")
            if item_id in current["attempts"]:
                raise AccountingHalt("Item was already attempted; automatic retry is forbidden")
            if any(
                attempt["status"] == "pending"
                for other in state["stages"].values()
                for attempt in other["attempts"].values()
            ):
                raise AccountingHalt("Parallel pending attempts are forbidden")
            if request_id in state["request_ids"]:
                raise AccountingHalt("Local request identity was already used")
            expected_item = self.item_ids[len(current["attempts"])]
            if item_id != expected_item:
                raise AccountingHalt("Attempts must follow the bound item order")

            event = self._base_event(stage, "begin_attempt", item_id=item_id)
            self._add_stage_config(event, current)
            event.update({
                "event_type": "unaccounted", "request_id": request_id,
                "request_started_at": _event_time(instant),
                "accounting_status": "attempt_pending", "billed_status": "held",
            })
            return self.ledger.append(event)

    def _block_attempt_locked(
        self,
        stage: str,
        item_id: str,
        current: dict[str, Any],
        request_id: str,
        error_class: str,
    ) -> dict[str, Any]:
        event = self._base_event(stage, "block_attempt", item_id=item_id)
        self._add_stage_config(event, current)
        event.update({
            "event_type": "unaccounted", "request_id": request_id,
            "accounting_status": "unresolved", "billed_status": "held",
            "error_class": error_class,
        })
        return self.ledger.append(event)

    def block_attempt(
        self,
        stage: str,
        *,
        item_id: str,
        request_id: str,
        error_class: str,
    ) -> dict[str, Any]:
        stage = _require_stage(stage)
        if _ERROR_CLASS_RE.fullmatch(error_class or "") is None:
            raise ValueError("error_class must be a class name, not an error message")
        with self._locked() as rows:
            state = self._state(rows)
            current = self._require_collecting_stage(state, stage)
            attempt = current["attempts"].get(item_id)
            if attempt is None or attempt["status"] != "pending":
                raise AccountingHalt("Unknown outcome needs one pending attempt")
            if request_id != attempt["request_id"]:
                raise AccountingHalt("Unknown outcome request identity does not match")
            return self._block_attempt_locked(
                stage, item_id, current, request_id, error_class
            )

    def record_response(
        self,
        stage: str,
        *,
        item_id: str,
        request_id: str,
        provider_response_id: str,
        response_sha256: str,
        prompt_tokens: int,
        completion_tokens: int,
        native_stop_reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        stage = _require_stage(stage)
        instant = _utc_instant(now)
        with self._locked() as rows:
            state = self._state(rows)
            current = self._require_collecting_stage(state, stage)
            attempt = current["attempts"].get(item_id)
            if attempt is None or attempt["status"] != "pending":
                raise AccountingHalt("Response needs one pending attempt")

            error_class = None
            if request_id != attempt["request_id"]:
                error_class = "RequestIdentityMismatch"
            elif not isinstance(provider_response_id, str) or not provider_response_id:
                error_class = "ProviderResponseIdentityMissing"
            elif provider_response_id in state["provider_response_ids"]:
                error_class = "ProviderResponseIdentityReused"
            elif _SHA256_RE.fullmatch(response_sha256 or "") is None:
                error_class = "PrivateResponseHashInvalid"
            elif type(prompt_tokens) is not int or prompt_tokens <= 0:
                error_class = "PromptUsageInvalid"
            elif type(completion_tokens) is not int or completion_tokens <= 0:
                error_class = "CompletionUsageInvalid"
            elif prompt_tokens > current["input_allowance"]:
                error_class = "InputAllowanceExceeded"
            elif completion_tokens > self.max_tokens:
                error_class = "OutputCapExceeded"
            elif native_stop_reason not in NATIVE_STOP_REASONS:
                error_class = "NativeStopReasonUnknown"
            else:
                started = _parse_event_time(attempt["request_started_at"])
                if instant < started:
                    error_class = "ResponseTimePrecedesAttempt"
                elif not current["window_start"] <= instant < current["window_end"]:
                    error_class = "BillingWindowExpired"

            if error_class is not None:
                self._block_attempt_locked(
                    stage, item_id, current, attempt["request_id"], error_class
                )
                raise AccountingHalt(
                    f"Response failed accounting validation: {error_class}"
                )

            event = self._base_event(stage, "record_response", item_id=item_id)
            self._add_stage_config(event, current)
            event["request_config"]["response_sha256"] = response_sha256
            event.update({
                "event_type": "success", "request_id": request_id,
                "provider_response_id": provider_response_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "native_finish_reason": native_stop_reason,
                "request_ended_at": _event_time(instant),
                "accounting_status": "usage_recorded_unreconciled",
                "billed_status": "held",
            })
            return self.ledger.append(event)

    def finish_stage(self, stage: str) -> dict[str, Any]:
        stage = _require_stage(stage)
        with self._locked() as rows:
            state = self._state(rows)
            current = self._require_collecting_stage(state, stage)
            if tuple(current["attempts"]) != self.item_ids or any(
                attempt["status"] != "complete"
                for attempt in current["attempts"].values()
            ):
                raise AccountingHalt("Every planned item must have one recorded response")
            event = self._base_event(stage, "finish_stage")
            self._add_stage_config(event, current)
            event.update({
                "event_type": "success",
                "accounting_status": "awaiting_aggregate_reconciliation",
                "billed_status": "held",
            })
            return self.ledger.append(event)

    def _billing_evidence_error(
        self, evidence: BillingEvidence | None, current: dict[str, Any]
    ) -> str | None:
        if not isinstance(evidence, BillingEvidence):
            return "BillingEvidenceMissing"
        if evidence.complete is not True:
            return "BillingEvidenceIncomplete"
        if evidence.account_sha256 != self.account_sha256:
            return "BillingAccountMismatch"
        if evidence.billing_group_sha256 != self.billing_group_sha256:
            return "BillingGroupMismatch"
        if evidence.model != self.model:
            return "BillingModelMismatch"
        try:
            _, start_text = _utc_hour("evidence.window_start", evidence.window_start)
            _, end_text = _utc_hour("evidence.window_end", evidence.window_end)
        except ValueError:
            return "BillingWindowMalformed"
        if (
            start_text != current["window_start_text"]
            or end_text != current["window_end_text"]
        ):
            return "BillingWindowMismatch"
        if type(evidence.prompt_tokens) is not int or evidence.prompt_tokens <= 0:
            return "BillingPromptUsageInvalid"
        if evidence.prompt_tokens != current["prompt_tokens"]:
            return "BillingPromptUsageMismatch"
        if type(evidence.completion_tokens) is not int or evidence.completion_tokens <= 0:
            return "BillingCompletionUsageInvalid"
        if evidence.completion_tokens != current["completion_tokens"]:
            return "BillingCompletionUsageMismatch"
        try:
            deduction = _require_decimal(
                "account_deduction_usd", evidence.account_deduction_usd, positive=False
            )
        except ValueError:
            return "BillingDeductionInvalid"
        calculated = self._actual_cost(current)
        if deduction != calculated:
            return "BillingDeductionMismatch"
        if deduction > current["bound"] or deduction > current["ceiling"]:
            return "BillingDeductionExceedsReservation"
        if _SHA256_RE.fullmatch(evidence.manifest_sha256 or "") is None:
            return "BillingManifestHashInvalid"
        if (
            not isinstance(evidence.source_sha256s, tuple)
            or not evidence.source_sha256s
            or len(set(evidence.source_sha256s)) != len(evidence.source_sha256s)
            or any(_SHA256_RE.fullmatch(value or "") is None for value in evidence.source_sha256s)
        ):
            return "BillingSourceHashesInvalid"
        return None

    def _block_reconciliation_locked(
        self,
        stage: str,
        current: dict[str, Any],
        error_class: str,
        evidence: BillingEvidence | None,
    ) -> dict[str, Any]:
        event = self._base_event(stage, "block_reconciliation")
        self._add_stage_config(event, current)
        if isinstance(evidence, BillingEvidence):
            if _SHA256_RE.fullmatch(evidence.manifest_sha256 or ""):
                event["request_config"]["evidence_manifest_sha256"] = evidence.manifest_sha256
            if (
                isinstance(evidence.source_sha256s, tuple)
                and evidence.source_sha256s
                and all(_SHA256_RE.fullmatch(value or "") for value in evidence.source_sha256s)
            ):
                event["request_config"]["evidence_source_sha256s"] = list(
                    evidence.source_sha256s
                )
        event.update({
            "event_type": "unaccounted", "accounting_status": "blocked",
            "billed_status": "held", "error_class": error_class,
        })
        return self.ledger.append(event)

    def settle_stage(
        self, stage: str, *, evidence: BillingEvidence | None
    ) -> dict[str, Any]:
        stage = _require_stage(stage)
        with self._locked() as rows:
            state = self._state(rows)
            current = state["stages"][stage]
            if current["blocked"] or not current["finished"] or current["reconciled"]:
                raise AccountingHalt("Stage is not awaiting aggregate reconciliation")
            error_class = self._billing_evidence_error(evidence, current)
            if error_class is None:
                assert evidence is not None
                prior_spent = sum(
                    other["deduction"]
                    for other in state["stages"].values()
                    if other["reconciled"]
                )
                if prior_spent + evidence.account_deduction_usd > self.combined_ceiling:
                    error_class = "CombinedDeductionCeilingExceeded"
            if error_class is not None:
                self._block_reconciliation_locked(
                    stage, current, error_class, evidence
                )
                raise AccountingHalt(
                    f"Aggregate billing reconciliation failed: {error_class}"
                )

            assert evidence is not None
            calculated = self._actual_cost(current)
            event = self._base_event(stage, "settle_stage")
            self._add_stage_config(event, current)
            event["request_config"].update({
                "prompt_tokens": evidence.prompt_tokens,
                "completion_tokens": evidence.completion_tokens,
                "evidence_window_start": current["window_start_text"],
                "evidence_window_end": current["window_end_text"],
                "account_deduction_usd": _decimal_text(evidence.account_deduction_usd),
                "calculated_cost_usd": _decimal_text(calculated),
                "evidence_manifest_sha256": evidence.manifest_sha256,
                "evidence_source_sha256s": list(evidence.source_sha256s),
            })
            event.update({
                "event_type": "success", "accounting_status": "valid",
                "billed_status": "aggregate_reconciled",
            })
            return self.ledger.append(event)

    def snapshot(self) -> dict[str, Any]:
        with self._locked() as rows:
            state = self._state(rows)
        exposure = self._active_exposure(state)
        spent = sum(
            stage["deduction"]
            for stage in state["stages"].values()
            if stage["reconciled"]
        )
        stages: dict[str, Any] = {}
        for name, stage in state["stages"].items():
            if stage["blocked"]:
                status = "blocked"
            elif stage["reconciled"]:
                status = "reconciled"
            elif stage["finished"]:
                status = "finished"
            elif stage["attempts"]:
                status = "running"
            elif stage["reserved"]:
                status = "reserved"
            else:
                status = "not_started"
            attempts = {item_id: dict(attempt) for item_id, attempt in stage["attempts"].items()}
            configuration = None
            reserved_usd = "0"
            if stage["reserved"]:
                reserved_usd = _decimal_text(stage["bound"])
                configuration = {
                    "input_allowance": stage["input_allowance"],
                    "input_rate_per_million": _decimal_text(stage["input_rate"]),
                    "output_rate_per_million": _decimal_text(stage["output_rate"]),
                    "window_start": stage["window_start_text"],
                    "window_end": stage["window_end_text"],
                }
            stages[name] = {
                "status": status,
                "reserved_usd": reserved_usd,
                "configuration": configuration,
                "attempts": attempts,
                "prompt_tokens": stage["prompt_tokens"],
                "completion_tokens": stage["completion_tokens"],
                "length_stops": stage["length_stops"],
                "response_count": sum(
                    attempt["status"] == "complete" for attempt in attempts.values()
                ),
                "complete": stage["finished"],
                "reconciled": stage["reconciled"],
                "blocked": stage["blocked"],
            }
            if stage.get("block_reason"):
                stages[name]["block_reason"] = stage["block_reason"]
            if stage["reconciled"]:
                stages[name]["spent_usd"] = _decimal_text(stage["deduction"])
                stages[name]["evidence_manifest_sha256"] = stage[
                    "evidence_manifest_sha256"
                ]
                stages[name]["evidence_source_sha256s"] = list(
                    stage["evidence_source_sha256s"]
                )
        return {
            "policy_sha256": self.policy_sha256,
            "plan_sha256": self.plan_sha256,
            "account_sha256": self.account_sha256,
            "billing_group_sha256": self.billing_group_sha256,
            "synthetic": self.synthetic,
            "reserved_usd": _decimal_text(exposure),
            "spent_usd": _decimal_text(spent),
            "active_exposure_usd": _decimal_text(exposure),
            "reconciled_deduction_usd": _decimal_text(spent),
            "blocked": any(stage["blocked"] for stage in state["stages"].values()),
            "stages": stages,
        }
