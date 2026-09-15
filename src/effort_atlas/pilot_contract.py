"""Offline validation and human approval binding for exploratory pilots."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import socket
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

from . import ROOT
from .confirmatory import sha256_json
from .wrapper import canonical_messages_sha256

LIVE_ACK_ENV = "EFFORT_ATLAS_PILOT_LIVE_ACK"
LIVE_ACK_VALUE = "I_HAVE_READ_THE_APPROVED_PREFLIGHT"
EVIDENCE_CHECKS = ("balance", "pricing", "route", "input_allowance", "human_mock", "data_spotcheck")
ACCOUNT_LEDGER_PATH = Path.home() / ".local/state/effort-atlas/openrouter/attempts.jsonl"
CONFIG_FIELDS = {
    "provider": {"name", "model", "base_url_env", "default_base_url", "api_key_env",
                 "max_completion_tokens", "timeout_s", "max_retries", "default_headers", "request_extra_body"},
    "effort": {"mode", "param_name", "levels", "ordinal"},
    "pilot": {"enabled", "label", "selection", "datasets", "wrapper_seed", "request_seed", "cap",
              "report_caps", "circuit_breaker_consecutive_errors", "input_token_allowance", "request_input_byte_limit"},
    "pricing": {"input_per_mtok", "output_per_mtok", "expected_input_tokens", "expected_output_tokens",
                "cap_bounds_billable_tokens", "completion_includes_reasoning", "verified_on"},
    "budget": {"per_dataset_ceiling_usd", "total_ceiling_usd", "reserve_margin_usd", "balance_verified_usd",
               "balance_verified_on", "preflight_approved_by", "receipt_mismatch_stop_fraction",
               "approved_run_sha256", "approval_evidence"},
    "paths": {"data", "results", "reports", "cache"},
}


def _number(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def _positive_int(value):
    return type(value) is int and value > 0


def _date(value):
    try:
        return (isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
                and date.fromisoformat(value) <= datetime.now(timezone.utc).date())
    except ValueError:
        return False


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def configuration_failures(cfg: dict) -> list[str]:
    if not isinstance(cfg, dict) or any(not isinstance(cfg.get(k), dict) for k in
                                      ("pilot", "budget", "pricing", "provider", "effort", "paths")):
        return ["configuration requires pilot, budget, pricing, provider, effort and paths objects"]
    p, b, pr, pc, e = (cfg[k] for k in ("pilot", "budget", "pricing", "provider", "effort"))
    fails = []
    if set(cfg) - set(CONFIG_FIELDS) - {"_selection_sha256", "_pilot_run_id"}:
        fails.append("unexpected top-level configuration field")
    for section, allowed in CONFIG_FIELDS.items():
        if set(cfg[section]) - allowed:
            fails.append(f"unexpected {section} configuration field")
    headers = pc.get("default_headers", {})
    if not isinstance(headers, dict) or any(
        key != "X-OpenRouter-Metadata" or value != "enabled" for key, value in headers.items()
    ):
        fails.append("provider.default_headers may only enable OpenRouter metadata; credentials must come from environment")
    if type(p.get("enabled")) is not bool:
        fails.append("pilot.enabled must be a boolean")
    for key in ("cap", "input_token_allowance", "request_input_byte_limit"):
        if not _positive_int(p.get(key)):
            fails.append(f"pilot.{key} must be a positive integer")
    if pc.get("max_completion_tokens") != p.get("cap") or not _positive_int(pc.get("max_completion_tokens")):
        fails.append("provider.max_completion_tokens must equal pilot.cap")
    for key in ("wrapper_seed", "request_seed"):
        if type(p.get(key)) is not int:
            fails.append(f"pilot.{key} must be an explicit integer")
    if not _text(p.get("label")) or not _text(pc.get("model")):
        fails.append("pilot label and model must be nonempty strings")
    for key in ("datasets", "report_caps"):
        values = p.get(key)
        if not isinstance(values, list) or not values:
            fails.append(f"pilot.{key} must be a nonempty list")
        elif key == "datasets" and (any(not _text(v) for v in values) or len(set(values)) != len(values)):
            fails.append("pilot.datasets must contain unique names")
        elif key == "report_caps" and any(not _positive_int(v) for v in values):
            fails.append("pilot.report_caps must contain positive integers")
    if type(pc.get("max_retries")) is not int or pc["max_retries"] != 0:
        fails.append("provider.max_retries must be 0")
    if e.get("mode") != "openrouter_reasoning" or e.get("param_name") != "reasoning":
        fails.append("pilot requires explicit normalized OpenRouter reasoning effort")
    levels = e.get("levels")
    valid_levels = isinstance(levels, list) and bool(levels) and all(
        isinstance(v, str) and v in {"minimal", "low", "medium", "high", "max", "xhigh"} for v in levels)
    if not valid_levels or len(set(levels)) != len(levels):
        fails.append("effort.levels must contain unique explicit supported labels")
    ordinal = e.get("ordinal")
    if not isinstance(ordinal, dict) or (valid_levels and (
        set(ordinal) != set(levels) or any(not _number(v, positive=True) for v in ordinal.values())
    )):
        fails.append("effort.ordinal must cover every level with a finite positive rank")
    for key in ("per_dataset_ceiling_usd", "total_ceiling_usd", "reserve_margin_usd"):
        if not _number(b.get(key)):
            fails.append(f"budget.{key} must be a finite nonnegative number")
    bal = b.get("balance_verified_usd")
    if bal is not None and not _number(bal):
        fails.append("budget.balance_verified_usd must be finite and nonnegative")
    mismatch = b.get("receipt_mismatch_stop_fraction")
    if not _number(mismatch) or mismatch > 1:
        fails.append("budget.receipt_mismatch_stop_fraction must be between 0 and 1")
    for key in ("input_per_mtok", "output_per_mtok"):
        if not _number(pr.get(key), positive=True):
            fails.append(f"pricing.{key} must be finite and positive")
    if pr.get("cap_bounds_billable_tokens") is not True or pr.get("completion_includes_reasoning") is not True:
        fails.append("pricing must explicitly attest cap-inclusive output and reasoning accounting")
    expected = pr.get("expected_output_tokens", {})
    if not isinstance(expected, dict) or (valid_levels and (set(expected) != set(levels) or
            any(not _positive_int(v) for v in expected.values()))):
        fails.append("pricing.expected_output_tokens must cover each effort with positive integers")
    extra = pc.get("request_extra_body")
    pin = extra.get("provider") if isinstance(extra, dict) else None
    if not isinstance(extra, dict) or set(extra) != {"provider"} or not isinstance(pin, dict):
        fails.append("request_extra_body may contain only the provider pin")
    else:
        if set(pin) - {"only", "allow_fallbacks", "require_parameters", "max_price"}:
            fails.append("unexpected provider routing field")
        only = pin.get("only")
        if (not isinstance(only, list) or len(only) != 1 or not _text(only[0])
                or pin.get("allow_fallbacks") is not False or pin.get("require_parameters") is not True):
            fails.append("provider requires one pin, allow_fallbacks=false and require_parameters=true")
        prices = pin.get("max_price")
        if not isinstance(prices, dict) or any(
            not _number(prices.get(k), positive=True) or prices.get(k) != pr.get(rate)
            for k, rate in (("prompt", "input_per_mtok"), ("completion", "output_per_mtok"))
        ):
            fails.append("provider.max_price must match the approved accounting rates")
    return fails


def run_manifest(cfg: dict, rendered: list, selection_sha256: str) -> dict:
    """Hash request bytes too; a stale dataclass digest cannot approve new text."""
    if configuration_failures(cfg):
        raise ValueError("Invalid pilot configuration cannot produce an approval manifest")
    ids = set()
    for item in rendered:
        identity = (item.dataset, item.source_item_id)
        if identity in ids:
            raise ValueError("Rendered items contain duplicate identities")
        ids.add(identity)
        digest = (hashlib.sha256(item.prompt.encode()).hexdigest() if item.prompt is not None
                  else canonical_messages_sha256(item.messages))
        if digest != item.prompt_sha256:
            raise ValueError("Rendered request bytes do not match the recorded digest")
    config = deepcopy({k: v for k, v in cfg.items() if not k.startswith("_")})
    config["pilot"].pop("enabled", None)
    for key in ("preflight_approved_by", "approved_run_sha256", "approval_evidence"):
        config["budget"].pop(key, None)
    manifest = {"version": 1, "phase": "exploratory_pilot", "configuration": config,
                "execution_host": socket.gethostname(), "account_ledger": str(ACCOUNT_LEDGER_PATH),
                "selection_sha256": selection_sha256,
                "items": [item.manifest_row() for item in rendered]}
    return {**manifest, "run_sha256": sha256_json(manifest)}


def _evidence_file(root: Path, spec: dict):
    if not isinstance(spec, dict) or not _text(spec.get("path")):
        raise ValueError("evidence path missing")
    path = (root / spec["path"]).resolve()
    relative = path.relative_to(root.resolve())
    if relative.parts[0] not in {"reap", "results_pilot"} or any(p.startswith(".") for p in relative.parts):
        raise ValueError("evidence must be inside reap or results_pilot")
    data = path.read_bytes()
    if not data.strip():
        raise ValueError("evidence is empty")
    if hashlib.sha256(data).hexdigest() != spec.get("sha256"):
        raise ValueError("evidence bytes mismatch")
    return data


def live_gate_failures(cfg: dict, env: dict | None = None, *,
                       manifest_sha256: str | None = None, root: Path = ROOT) -> list[str]:
    fails = configuration_failures(cfg)
    if not isinstance(cfg, dict) or any(not isinstance(cfg.get(k), dict) for k in ("pilot", "budget", "pricing", "provider", "paths")):
        return fails
    env = os.environ if env is None else env
    p, b, pr, pc = (cfg[k] for k in ("pilot", "budget", "pricing", "provider"))
    if p.get("enabled") is not True:
        fails.append("pilot.enabled is false")
    if not _number(b.get("balance_verified_usd")) or not _date(b.get("balance_verified_on")):
        fails.append("budget.balance_verified_usd / balance_verified_on need a finite balance and ISO date")
    if not _text(b.get("preflight_approved_by")):
        fails.append("budget.preflight_approved_by is empty")
    if not _date(pr.get("verified_on")):
        fails.append("pricing.verified_on needs an ISO date")
    if env.get(LIVE_ACK_ENV) != LIVE_ACK_VALUE:
        fails.append(f"environment {LIVE_ACK_ENV} != {LIVE_ACK_VALUE}")
    amounts = (b.get("balance_verified_usd"), b.get("reserve_margin_usd"), b.get("total_ceiling_usd"))
    if all(_number(v) for v in amounts) and amounts[2] > amounts[0] - amounts[1]:
        fails.append("budget.total_ceiling_usd exceeds verified balance minus reserve")
    if not manifest_sha256 or b.get("approved_run_sha256") != manifest_sha256:
        fails.append("budget.approved_run_sha256 does not match the validated runtime manifest")
    if pc.get("default_base_url") != "https://openrouter.ai/api/v1" or env.get(pc.get("base_url_env", ""), pc.get("default_base_url")) != "https://openrouter.ai/api/v1":
        fails.append("pilot supports only the approved OpenRouter endpoint")
    for key, folder in (("results", "results_pilot"), ("cache", ".cache_pilot")):
        try:
            (root / cfg["paths"][key]).resolve().relative_to((root / folder).resolve())
        except (KeyError, TypeError, ValueError):
            fails.append(f"paths.{key} must remain inside {folder}")
    try:
        evidence = json.loads(_evidence_file(root, b.get("approval_evidence")))
        if (evidence.get("run_sha256") != manifest_sha256 or not manifest_sha256
                or evidence.get("approved_by") != b.get("preflight_approved_by")
                or not _text(evidence.get("approved_by")) or not _date(evidence.get("approved_on"))):
            raise ValueError("approval identity mismatch")
        for key in EVIDENCE_CHECKS:
            if evidence.get("checks", {}).get(key) is not True:
                raise ValueError("approval check missing")
            _evidence_file(root, evidence.get("artifacts", {}).get(key))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        fails.append("budget.approval_evidence must hash-bind dated human review and all supporting artifacts")
    return fails
