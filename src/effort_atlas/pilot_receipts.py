"""Content-free completion and receipt checks for the exploratory pilot.

Receipt lookups are read-only and bounded. This module never submits a
generation, loads an environment file, or returns response/provider error text.
"""
from __future__ import annotations

import os
import re
import time
from decimal import Decimal

from .confirmatory import SENSITIVE_VALUE_PATTERN, _normalize_finish_reason
from .openrouter_receipts import _fetch_generation
from .pilot_accounting import AccountingHalt, money

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PERMITTED_FINISH_REASONS = frozenset({"stop", "length", "content_filter"})


def _integer(value: object, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise AccountingHalt("invalid_token_accounting")
    return value


def _amount(value: object) -> Decimal:
    try:
        return money(value)
    except (ValueError, TypeError, OverflowError):
        raise AccountingHalt("invalid_cost_or_duration") from None


def _identity(value: object) -> str:
    if (not isinstance(value, str) or len(value) > 256
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value) is None
            or SENSITIVE_VALUE_PATTERN.search(value)):
        raise AccountingHalt("invalid_generation_identity")
    return value


def _provider(value: object) -> str:
    if (not isinstance(value, str) or len(value) > 128
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._:/-]*", value.strip()) is None
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or SENSITIVE_VALUE_PATTERN.search(value)):
        raise AccountingHalt("invalid_provider_identity")
    return value.strip().casefold()


def _pin(cfg: dict) -> str:
    try:
        only = cfg["provider"]["request_extra_body"]["provider"]["only"]
    except (KeyError, TypeError):
        raise AccountingHalt("invalid_provider_pin") from None
    if not isinstance(only, list) or len(only) != 1:
        raise AccountingHalt("invalid_provider_pin")
    return _provider(only[0])


def _finish(value: object) -> str:
    if (not isinstance(value, str)
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise AccountingHalt("invalid_finish_reason")
    normalized = _normalize_finish_reason(value)
    if normalized not in PERMITTED_FINISH_REASONS:
        raise AccountingHalt("invalid_finish_reason")
    return normalized


def _allowances(cfg: dict) -> tuple[int, int]:
    try:
        return (_integer(cfg["pilot"]["input_token_allowance"], positive=True),
                _integer(cfg["pilot"]["cap"], positive=True))
    except (KeyError, TypeError):
        raise AccountingHalt("invalid_token_allowances") from None


def _usage(prompt: object, completion: object, reasoning: object,
           *, input_allowance: int, cap: int) -> None:
    prompt = _integer(prompt, positive=True)
    completion = _integer(completion, positive=True)
    if prompt > input_allowance or completion > cap:
        raise AccountingHalt("token_allowance_exceeded")
    if reasoning is not None and _integer(reasoning) > completion:
        raise AccountingHalt("reasoning_exceeds_completion_usage")


def validate_completion(cfg: dict, comp, *, mock: bool = False) -> None:
    """Validate required accounting; unknown reasoning and stream cost stay None."""
    allowance, cap = _allowances(cfg)
    _usage(getattr(comp, "prompt_tokens", None), getattr(comp, "completion_tokens", None),
           getattr(comp, "reasoning_tokens", None), input_allowance=allowance, cap=cap)
    _identity(getattr(comp, "generation_id", None))
    served = _provider(getattr(comp, "provider", None))
    if not mock and served != _pin(cfg):
        raise AccountingHalt("served_provider_mismatch")
    finish = _finish(getattr(comp, "finish_reason", None))
    if finish == "length" and comp.completion_tokens != cap:
        raise AccountingHalt("length_stop_below_approved_cap")
    if finish == "content_filter":
        raise AccountingHalt("filtered_response_has_no_natural_length_measurement")
    _amount(getattr(comp, "latency_s", None))
    cost = getattr(comp, "reported_cost_usd", None)
    if cost is not None:
        _amount(cost)


def _cost_matches(actual: Decimal, expected: Decimal, tolerance: Decimal) -> bool:
    # Multiplication avoids division and binary rounding at the inclusive limit.
    return abs(actual - expected) <= expected * tolerance


def reconcile_receipt(cfg: dict, comp, payload: dict) -> dict:
    """Check a raw OpenRouter generation receipt and return allowlisted metadata."""
    validate_completion(cfg, comp)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise AccountingHalt("malformed_generation_receipt")
    data = payload["data"]
    receipt_id = _identity(data.get("id"))
    if receipt_id != comp.generation_id:
        raise AccountingHalt("receipt_generation_mismatch")
    provider = data.get("provider_name")
    if _provider(provider) != _provider(comp.provider) or _provider(provider) != _pin(cfg):
        raise AccountingHalt("receipt_provider_mismatch")
    finish = _finish(data.get("finish_reason"))
    if finish != _finish(comp.finish_reason):
        raise AccountingHalt("receipt_finish_mismatch")

    native_prompt = data.get("native_tokens_prompt")
    native_completion = data.get("native_tokens_completion")
    native_reasoning = data.get("native_tokens_reasoning")
    allowance, cap = _allowances(cfg)
    _usage(native_prompt, native_completion, native_reasoning,
           input_allowance=allowance, cap=cap)
    if native_prompt != comp.prompt_tokens or native_completion != comp.completion_tokens:
        raise AccountingHalt("receipt_usage_mismatch")
    if (native_reasoning is not None and comp.reasoning_tokens is not None
            and native_reasoning != comp.reasoning_tokens):
        raise AccountingHalt("receipt_reasoning_usage_mismatch")

    cost = _amount(data.get("total_cost"))
    try:
        input_price = _amount(cfg["pricing"]["input_per_mtok"])
        output_price = _amount(cfg["pricing"]["output_per_mtok"])
        tolerance = _amount(cfg["budget"]["receipt_mismatch_stop_fraction"])
    except (KeyError, TypeError):
        raise AccountingHalt("invalid_receipt_pricing_configuration") from None
    if input_price <= 0 or output_price <= 0 or tolerance > 1:
        raise AccountingHalt("invalid_receipt_pricing_configuration")
    predicted = (native_prompt * input_price + native_completion * output_price) / Decimal(1_000_000)
    if not _cost_matches(cost, predicted, tolerance):
        raise AccountingHalt("receipt_price_mismatch")
    if (comp.reported_cost_usd is not None
            and not _cost_matches(cost, _amount(comp.reported_cost_usd), tolerance)):
        raise AccountingHalt("receipt_stream_cost_mismatch")

    result = {
        "receipt_generation_id": receipt_id,
        "receipt_provider": provider.strip(),
        "receipt_finish_reason": finish,
        "receipt_cost_usd": float(cost),
        "native_prompt_tokens": native_prompt,
        "native_completion_tokens": native_completion,
    }
    if native_reasoning is not None:
        result["native_reasoning_tokens"] = native_reasoning
    native_finish = data.get("native_finish_reason")
    if native_finish is not None:
        # Native vocabularies differ from public stop/length labels; preserve a
        # bounded identifier without treating it as the normalized finish reason.
        if (not isinstance(native_finish, str) or len(native_finish) > 128
                or re.fullmatch(r"[A-Za-z0-9_.:-]+", native_finish) is None
                or SENSITIVE_VALUE_PATTERN.search(native_finish)):
            raise AccountingHalt("invalid_native_finish_reason")
        result["native_finish_reason"] = native_finish
    return result


def fetch_receipt(cfg: dict, generation_id: str) -> dict:
    """Fetch an existing receipt at most three times; never resubmit a generation."""
    _identity(generation_id)
    try:
        provider = cfg["provider"]
        key_env = provider["api_key_env"]
        base_env = provider["base_url_env"]
        default_base = provider["default_base_url"]
    except (KeyError, TypeError):
        raise AccountingHalt("invalid_receipt_endpoint_configuration") from None
    if not isinstance(key_env, str) or not key_env or not isinstance(base_env, str) or not base_env:
        raise AccountingHalt("invalid_receipt_endpoint_configuration")
    base_url = os.environ.get(base_env, default_base)
    if default_base != OPENROUTER_BASE_URL or base_url != OPENROUTER_BASE_URL:
        raise AccountingHalt("unapproved_receipt_endpoint")
    api_key = os.environ.get(key_env)
    if not api_key or not api_key.strip():
        raise AccountingHalt("missing_receipt_api_key_environment")
    for attempt in range(3):
        try:
            payload = _fetch_generation(OPENROUTER_BASE_URL, api_key, generation_id)
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
                raise AccountingHalt("receipt_not_ready")
            return payload
        except Exception:
            if attempt == 2:
                raise AccountingHalt("receipt_lookup_failed") from None
        time.sleep((0.25, 0.5)[attempt])
    raise AssertionError("unreachable")
