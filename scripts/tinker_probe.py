#!/usr/bin/env python3
"""Dry-run-first Tinker probes for REAP's pre-confirmatory smoke gates.

Pinned Tinker 0.25.0 cannot guarantee one billed submission, so ``--live``
currently fails closed before constructing a client. Its preflight decisions
are recorded in append-only JSONL and no raw response text is ever stored.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
import platform
import re
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, TextIO


SCHEMA_VERSION = 3
PROBE_PYTHON_VERSION = "3.12.8"
TINKER_SDK_VERSION = "0.25.0"
SMOKE_MODEL = "openai/gpt-oss-20b"
CAP_PROBE_CAPS = (4096, 16384, 32768, 65536)
# Every requested cap is sent to the same exact target model ID. In particular,
# a 65,536 rejection is evidence that this cap is unsupported on that target;
# substituting a PEFT or extended-context route would answer a different question.
CAP_PROBE_MODELS = {
    "inkling": "thinkingmachines/Inkling",
    "gpt_oss_120b": "openai/gpt-oss-120b",
}
DEFAULT_REPORT_PATH = Path("reports/tinker_probe.jsonl")
ENVIRONMENT_LOCK_PATH = Path(__file__).with_name("tinker_probe_requirements.lock")
PRICING_SOURCE = "https://tinker-docs.thinkingmachines.ai/tinker/models/"
PRICING_AS_OF = "2026-08-08"
DEFAULT_CAP_OUTPUT_TOKEN_COST_BOUND = 32768
DEFAULT_CAP_MAX_AUTHORIZATION_USD = 0.03

# USD per million tokens. These are used only for an upper-bound projection
# printed before a human-authorized live call; actual billing must be reconciled
# separately. Values match the exact model IDs above on PRICING_AS_OF.
MODEL_PRICING = {
    "openai/gpt-oss-20b": {"prefill": 0.18, "cached_prefill": 0.036, "sample": 0.45},
    "openai/gpt-oss-120b": {"prefill": 0.33, "cached_prefill": 0.066, "sample": 0.84},
    "thinkingmachines/Inkling": {"prefill": 1.87, "cached_prefill": 0.374, "sample": 4.68},
}
MODEL_CONTEXT_TOKEN_BOUNDS = {
    "openai/gpt-oss-20b": 32768,
    "openai/gpt-oss-120b": 32768,
    "thinkingmachines/Inkling": 65536,
}

REQUIRED_RECORD_FIELDS = {
    "schema_version",
    "record_type",
    "record_id",
    "call_id",
    "probe_name",
    "probe_kind",
    "classification",
    "status",
    "timestamp",
    "model",
    "requested_cap",
    "deliberately_omits_max_tokens",
    "request_params",
    "num_samples",
    "sampling_session_id",
    "request_id",
    "billing_join_id",
    "sample_index",
    "response_text_sha256",
    "usage",
    "stop_reason",
    "latency_seconds",
    "returned_tokens_exceed_requested_cap",
    "projected_cost_usd",
    "cost_projection_output_token_bound",
    "cost_projection_prompt_token_bound",
    "cost_authorization_usd",
    "pricing_source",
    "pricing_as_of",
    "sdk_version",
    "python_version",
    "environment_lock_sha256",
    "error",
}

EASY_PROMPT = (
    "Return exactly one short line in this format: Final answer: 4. "
    "What is 2 + 2?"
)
FORCED_TRUNCATION_PROMPT = (
    "Write the positive integers in order, separated by spaces, and continue "
    "without concluding until the service stops you."
)
HARD_CAP_PROMPT = (
    "Produce a long, careful derivation of the sum of the first one million "
    "positive integers. Check it using several independent methods, then keep "
    "enumerating verification steps until the service stops you. End with "
    "Final answer: 500000500000 only if you reach a natural conclusion."
)


@dataclass(frozen=True)
class ProbeSpec:
    name: str
    kind: str
    classification: str
    model: str
    prompt: str
    max_tokens: int | None
    num_samples: int
    seed: int | None
    temperature: float
    top_p: float
    top_k: int
    stop: tuple[str, ...] | None
    deliberately_omits_max_tokens: bool = False

    @property
    def cost_projection_output_token_bound(self) -> int:
        """Finite completion-token bound used only for cost authorization."""
        if self.max_tokens is not None:
            return self.max_tokens
        if self.kind == "default_cap" and self.deliberately_omits_max_tokens:
            # GPT-OSS-20B's published maximum sequence length is 32K. Using the
            # full context as output is conservative because the prompt also
            # consumes context. This value is never sent as max_tokens.
            return DEFAULT_CAP_OUTPUT_TOKEN_COST_BOUND
        raise ValueError("a finite cost-projection output-token bound is required")

    @property
    def cost_projection_prompt_token_bound(self) -> int:
        """Published full-context bound; conservative for any rendered prompt."""
        return MODEL_CONTEXT_TOKEN_BOUNDS[self.model]

    def request_params(self) -> dict[str, Any]:
        """Return exactly the fields passed to ``tinker.SamplingParams``."""
        params: dict[str, Any] = {
            "seed": self.seed,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "stop": list(self.stop) if self.stop is not None else None,
        }
        if self.deliberately_omits_max_tokens:
            if self.kind != "default_cap" or self.classification != "exploratory":
                raise ValueError("max_tokens omission is restricted to the exploratory default-cap diagnostic")
        else:
            if self.max_tokens is None:
                raise ValueError("ordinary Tinker requests require explicit max_tokens")
            params["max_tokens"] = self.max_tokens
        return params


@dataclass(frozen=True)
class SampleObservation:
    text: str
    completion_tokens: int
    stop_reason: str


@dataclass(frozen=True)
class CallResult:
    observations: tuple[SampleObservation, ...]
    prompt_tokens: int
    prompt_cache_hit_tokens: int
    sdk_version: str
    sampling_session_id: str | None = None
    python_version: str = PROBE_PYTHON_VERSION
    request_id: str | None = None
    billing_join_id: str | None = None


class ProbeCallError(RuntimeError):
    """A failed logical call plus any identifiers learned before failure."""

    def __init__(
        self,
        message: str,
        *,
        sampling_session_id: str | None = None,
        request_id: str | None = None,
        billing_join_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.sampling_session_id = sampling_session_id
        self.request_id = request_id
        self.billing_join_id = billing_join_id


class ProbeAdapter(Protocol):
    def sample(self, spec: ProbeSpec) -> CallResult: ...


def build_probe_plan(
    *,
    seed: int | None = 20260808,
    temperature: float = 1.0,
    top_p: float = 1.0,
    top_k: int = -1,
    stop: Sequence[str] | None = None,
) -> list[ProbeSpec]:
    """Build the complete pre-confirmatory Tinker probe matrix."""
    common = {
        "seed": seed,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "stop": tuple(stop) if stop else None,
    }
    plan = [
        ProbeSpec(
            name="smoke_generous_gpt_oss_20b",
            kind="smoke",
            classification="smoke",
            model=SMOKE_MODEL,
            prompt=EASY_PROMPT,
            max_tokens=256,
            num_samples=1,
            **common,
        ),
        ProbeSpec(
            name="stop_reason_forced_collision",
            kind="stop_reason",
            classification="smoke",
            model=SMOKE_MODEL,
            prompt=FORCED_TRUNCATION_PROMPT,
            max_tokens=1,
            num_samples=1,
            **common,
        ),
        ProbeSpec(
            name="default_cap_exploratory_omission",
            kind="default_cap",
            classification="exploratory",
            model=SMOKE_MODEL,
            prompt=FORCED_TRUNCATION_PROMPT,
            max_tokens=None,
            num_samples=1,
            deliberately_omits_max_tokens=True,
            **common,
        ),
        ProbeSpec(
            name="samples_independence_n8",
            kind="sample_independence",
            classification="smoke",
            model=SMOKE_MODEL,
            prompt=HARD_CAP_PROMPT,
            max_tokens=256,
            num_samples=8,
            **common,
        ),
    ]
    for model_label, model in CAP_PROBE_MODELS.items():
        for cap in CAP_PROBE_CAPS:
            plan.append(
                ProbeSpec(
                    name=f"cap_semantics_{model_label}_{cap}",
                    kind="cap_semantics",
                    classification="smoke",
                    model=model,
                    prompt=HARD_CAP_PROMPT,
                    max_tokens=cap,
                    num_samples=1,
                    **common,
                )
            )
    # This assertion is a research safeguard, not merely a programming check.
    omitted = [spec for spec in plan if "max_tokens" not in spec.request_params()]
    if len(omitted) != 1 or omitted[0].kind != "default_cap":
        raise AssertionError("exactly one isolated default-cap request may omit max_tokens")
    return plan


def _canonical_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def locked_distribution_versions() -> dict[str, str]:
    """Parse exact distribution pins from the generated requirements lock."""
    pins: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")
    for line in ENVIRONMENT_LOCK_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        name = _canonical_distribution_name(match.group(1))
        if name in pins:
            raise RuntimeError(f"duplicate locked distribution: {name}")
        pins[name] = match.group(2)
    if not pins:
        raise RuntimeError("probe environment lock contains no exact distribution pins")
    return pins


def _installed_distribution_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            versions[_canonical_distribution_name(name)] = distribution.version
    return versions


def verify_locked_environment(
    *, installed_versions: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Fail closed unless Python and every hash-locked distribution match."""
    observed_python = platform.python_version()
    if observed_python != PROBE_PYTHON_VERSION:
        raise RuntimeError(
            f"probe requires CPython {PROBE_PYTHON_VERSION}; observed {observed_python}"
        )
    expected = locked_distribution_versions()
    installed = (
        {_canonical_distribution_name(name): version for name, version in installed_versions.items()}
        if installed_versions is not None
        else _installed_distribution_versions()
    )
    mismatches = [
        f"{name}=={version} (observed {installed.get(name, 'missing')})"
        for name, version in sorted(expected.items())
        if installed.get(name) != version
    ]
    mismatches.extend(
        f"unexpected {name}=={installed[name]}"
        for name in sorted(set(installed) - set(expected))
    )
    if mismatches:
        raise RuntimeError("locked environment mismatch: " + "; ".join(mismatches))
    return {
        "python_version": observed_python,
        "environment_lock_sha256": environment_lock_sha256(),
        "distributions": [
            {"name": name, "version": version} for name, version in sorted(expected.items())
        ],
    }


def inspect_pinned_sdk_one_attempt_capability(*, sdk_module: Any | None = None) -> dict[str, Any]:
    """Inspect upstream 0.25.0 submission code; never reproduce its behavior."""
    if sdk_module is None:
        import tinker as sdk_module  # type: ignore[no-redef]
    observed_sdk = str(getattr(sdk_module, "__version__", "unknown"))
    if observed_sdk != TINKER_SDK_VERSION:
        raise RuntimeError(
            f"Tinker SDK {TINKER_SDK_VERSION} is required; observed {observed_sdk}"
        )
    from tinker.lib import internal_client_holder
    from tinker.lib.public_interfaces import sampling_client

    sample_source = inspect.getsource(sampling_client.SamplingClient._sample_async_impl)
    holder_source = inspect.getsource(
        internal_client_holder.InternalClientHolder.execute_with_retries
    )
    # Tinker 0.25.0 exposes no documented client-side switch that disables both
    # submission retry paths. Keep this version fail-closed even if a locally
    # patched distribution does not match these source signatures: that would
    # not establish a supported upstream one-attempt contract.
    reasons = [
        "SamplingClient._sample_async_impl has a 429 resubmission loop",
        "InternalClientHolder.execute_with_retries retries submissions",
    ]
    observed_signatures = {
        "sampling_429_loop": (
            "while True" in sample_source and "untyped_future is not None" in sample_source
        ),
        "holder_retry_wrapper": (
            "holder.execute_with_retries" in sample_source and "while True" in holder_source
        ),
    }
    return {
        "supported": False,
        "sdk_version": observed_sdk,
        "reasons": reasons,
        "observed_signatures": observed_signatures,
        "upstream_source_sha256": {
            "SamplingClient._sample_async_impl": hashlib.sha256(
                sample_source.encode("utf-8")
            ).hexdigest(),
            "InternalClientHolder.execute_with_retries": hashlib.sha256(
                holder_source.encode("utf-8")
            ).hexdigest(),
        },
    }


class AppendOnlyJSONL:
    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _validate_existing(handle: TextIO) -> None:
        handle.seek(0)
        text = handle.read()
        if text and not text.endswith("\n"):
            raise ValueError("append-only evidence sink has an unterminated final line")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line:
                raise ValueError(f"append-only evidence sink has blank line {line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"append-only evidence sink has invalid JSON on line {line_number}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"append-only evidence sink line {line_number} is not an object"
                )

    def preflight(self) -> None:
        """Open and validate the sink before any client can be constructed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("append-only evidence sink may not be a symbolic link")
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                self._validate_existing(handle)
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def append(self, record: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                self._validate_existing(handle)
                handle.seek(0, 2)
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def hash_response_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def environment_lock_sha256() -> str:
    return hashlib.sha256(ENVIRONMENT_LOCK_PATH.read_bytes()).hexdigest()


def make_control_record(record_type: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": record_type,
        "record_id": str(uuid.uuid4()),
        "timestamp": _utc_now(),
        **fields,
    }


def make_attempt_started_record(
    spec: ProbeSpec,
    *,
    call_id: str,
    projected_cost: float,
    cost_authorization_usd: float | None,
) -> dict[str, Any]:
    return make_control_record(
        "attempt_started",
        call_id=call_id,
        probe_name=spec.name,
        probe_kind=spec.kind,
        classification=spec.classification,
        status="started",
        model=spec.model,
        requested_cap=spec.max_tokens,
        deliberately_omits_max_tokens=spec.deliberately_omits_max_tokens,
        request_params=spec.request_params(),
        num_samples=spec.num_samples,
        projected_cost_usd=projected_cost,
        cost_projection_output_token_bound=spec.cost_projection_output_token_bound,
        cost_projection_prompt_token_bound=spec.cost_projection_prompt_token_bound,
        cost_authorization_usd=cost_authorization_usd,
        sampling_session_id=None,
        request_id=None,
        billing_join_id=None,
    )


def make_response_records(
    spec: ProbeSpec,
    result: CallResult,
    *,
    call_id: str,
    latency_seconds: float,
    timestamp: str,
    projected_cost_usd: float,
    cost_authorization_usd: float | None = None,
) -> list[dict[str, Any]]:
    records = []
    for sample_index, observation in enumerate(result.observations):
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_type": "result",
                "record_id": str(uuid.uuid4()),
                "call_id": call_id,
                "probe_name": spec.name,
                "probe_kind": spec.kind,
                "classification": spec.classification,
                "status": "ok",
                "timestamp": timestamp,
                "model": spec.model,
                "requested_cap": spec.max_tokens,
                "deliberately_omits_max_tokens": spec.deliberately_omits_max_tokens,
                "request_params": spec.request_params(),
                "num_samples": spec.num_samples,
                "sampling_session_id": result.sampling_session_id,
                "request_id": result.request_id,
                "billing_join_id": result.billing_join_id,
                "sample_index": sample_index,
                "response_text_sha256": hash_response_text(observation.text),
                "usage": {
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": observation.completion_tokens,
                    # SampleResponse has no per-call billing receipt. Never equate
                    # returned tokens with billed tokens silently.
                    "billed_completion_tokens": None,
                    "prompt_cache_hit_tokens": result.prompt_cache_hit_tokens,
                },
                "stop_reason": observation.stop_reason,
                "latency_seconds": latency_seconds,
                "returned_tokens_exceed_requested_cap": (
                    observation.completion_tokens > spec.max_tokens
                    if spec.max_tokens is not None
                    else None
                ),
                "projected_cost_usd": projected_cost_usd,
                "cost_projection_output_token_bound": spec.cost_projection_output_token_bound,
                "cost_projection_prompt_token_bound": spec.cost_projection_prompt_token_bound,
                "cost_authorization_usd": cost_authorization_usd,
                "pricing_source": PRICING_SOURCE,
                "pricing_as_of": PRICING_AS_OF,
                "sdk_version": result.sdk_version,
                "python_version": result.python_version,
                "environment_lock_sha256": environment_lock_sha256(),
                "error": None,
            }
        )
    return records


def make_error_record(
    spec: ProbeSpec,
    error: Exception,
    *,
    call_id: str,
    latency_seconds: float,
    timestamp: str,
    projected_cost_usd: float,
    cost_authorization_usd: float | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "result",
        "record_id": str(uuid.uuid4()),
        "call_id": call_id,
        "probe_name": spec.name,
        "probe_kind": spec.kind,
        "classification": spec.classification,
        "status": "error",
        "timestamp": timestamp,
        "model": spec.model,
        "requested_cap": spec.max_tokens,
        "deliberately_omits_max_tokens": spec.deliberately_omits_max_tokens,
        "request_params": spec.request_params(),
        "num_samples": spec.num_samples,
        "sampling_session_id": getattr(error, "sampling_session_id", None),
        "request_id": getattr(error, "request_id", None),
        "billing_join_id": getattr(error, "billing_join_id", None),
        "sample_index": None,
        "response_text_sha256": None,
        "usage": {
            "prompt_tokens": None,
            "completion_tokens": None,
            "billed_completion_tokens": None,
            "prompt_cache_hit_tokens": None,
        },
        "stop_reason": None,
        "latency_seconds": latency_seconds,
        "returned_tokens_exceed_requested_cap": None,
        "projected_cost_usd": projected_cost_usd,
        "cost_projection_output_token_bound": spec.cost_projection_output_token_bound,
        "cost_projection_prompt_token_bound": spec.cost_projection_prompt_token_bound,
        "cost_authorization_usd": cost_authorization_usd,
        "pricing_source": PRICING_SOURCE,
        "pricing_as_of": PRICING_AS_OF,
        "sdk_version": None,
        "python_version": platform.python_version(),
        "environment_lock_sha256": environment_lock_sha256(),
        "error": {"type": type(error).__name__, "message": str(error)},
    }


def projected_cost_usd(spec: ProbeSpec) -> float:
    """Return the finite conservative upper bound used for authorization."""
    prices = MODEL_PRICING[spec.model]
    prompt_bound = spec.cost_projection_prompt_token_bound
    uncached_prefill = prompt_bound * prices["prefill"]
    cached_prefill = prompt_bound * max(0, spec.num_samples - 1) * prices["cached_prefill"]
    sample = spec.cost_projection_output_token_bound * spec.num_samples * prices["sample"]
    return (uncached_prefill + cached_prefill + sample) / 1_000_000


def print_cost_projection(spec: ProbeSpec, stream: TextIO) -> float:
    projection = projected_cost_usd(spec)
    detail = (
        f"upper_bound_usd={projection:.6f} "
        f"prompt_token_cost_bound={spec.cost_projection_prompt_token_bound} "
        f"output_token_cost_bound={spec.cost_projection_output_token_bound} "
        "prefill_basis=one_uncached_then_all_remaining_cached"
    )
    if spec.deliberately_omits_max_tokens:
        detail += " bound_basis=published_model_context max_tokens_parameter=OMITTED"
    stream.write(
        f"COST PROJECTION probe={spec.name} model={spec.model} {detail} "
        f"pricing_as_of={PRICING_AS_OF}\n"
    )
    stream.flush()
    return projection


def summarize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("record_type", "result") != "result":
            continue
        grouped[str(record["call_id"])].append(record)

    summary = []
    for call_records in grouped.values():
        first = call_records[0]
        successful = [record for record in call_records if record.get("status") == "ok"]
        hashes = {
            str(record["response_text_sha256"])
            for record in successful
            if record.get("response_text_sha256") is not None
        }
        completion_counts = [
            int(record["usage"]["completion_tokens"])
            for record in successful
            if record.get("usage", {}).get("completion_tokens") is not None
        ]
        stop_reasons = sorted(
            {str(record["stop_reason"]) for record in successful if record.get("stop_reason")}
        )
        cap_exceeded = any(
            record.get("returned_tokens_exceed_requested_cap") is True for record in successful
        )
        summary.append(
            {
                "probe": first["probe_name"],
                "model": first["model"],
                "cap": first.get("requested_cap"),
                "status": "ok" if successful and len(successful) == len(call_records) else "error",
                "samples": len(successful),
                "distinct_outputs": len(hashes),
                "stop_reasons": ",".join(stop_reasons) or "-",
                "max_completion_tokens": max(completion_counts) if completion_counts else None,
                "returned_cap_exceeded": cap_exceeded if successful else None,
                "billed_cap_status": "unresolved_no_per_call_receipt",
            }
        )
    return sorted(summary, key=lambda row: str(row["probe"]))


def render_summary_table(summary: Sequence[Mapping[str, Any]]) -> str:
    headers = (
        "probe",
        "model",
        "cap",
        "status",
        "samples",
        "distinct_outputs",
        "stop_reasons",
        "max_completion_tokens",
        "returned_cap_exceeded",
        "billed_cap_status",
    )
    rows = [["-" if row.get(header) is None else str(row.get(header)) for header in headers] for row in summary]
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row, strict=True)]
    rendered = [" | ".join(header.ljust(width) for header, width in zip(headers, widths, strict=True))]
    rendered.append("-+-".join("-" * width for width in widths))
    rendered.extend(
        " | ".join(value.ljust(width) for value, width in zip(row, widths, strict=True))
        for row in rows
    )
    return "\n".join(rendered)


def render_plan_table(plan: Sequence[ProbeSpec]) -> str:
    headers = (
        "probe",
        "kind",
        "class",
        "model",
        "max_tokens",
        "num_samples",
        "prompt_cost_bound",
        "output_cost_bound",
        "projected_cost_usd",
    )
    rows = [
        (
            spec.name,
            spec.kind,
            spec.classification,
            spec.model,
            "OMITTED" if spec.deliberately_omits_max_tokens else str(spec.max_tokens),
            str(spec.num_samples),
            str(spec.cost_projection_prompt_token_bound),
            str(spec.cost_projection_output_token_bound),
            f"{projected_cost_usd(spec):.6f}",
        )
        for spec in plan
    ]
    widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]
    output = [" | ".join(header.ljust(width) for header, width in zip(headers, widths, strict=True))]
    output.append("-+-".join("-" * width for width in widths))
    output.extend(
        " | ".join(value.ljust(width) for value, width in zip(row, widths, strict=True))
        for row in rows
    )
    return "\n".join(output)


def _select_plan(plan: Sequence[ProbeSpec], selection: str) -> list[ProbeSpec]:
    kind_by_cli = {
        "smoke": "smoke",
        "default-cap": "default_cap",
        "stop-reason": "stop_reason",
        "samples": "sample_independence",
        "caps": "cap_semantics",
    }
    if selection == "all":
        return list(plan)
    return [spec for spec in plan if spec.kind == kind_by_cli[selection]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print the plan without making a client call (default)")
    mode.add_argument(
        "--live",
        action="store_true",
        help="run live preflight; pinned Tinker 0.25.0 currently fails closed",
    )
    parser.add_argument(
        "--probe",
        choices=("all", "smoke", "default-cap", "stop-reason", "samples", "caps"),
        default="all",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--seed", type=int, default=20260808)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=-1)
    parser.add_argument("--stop", action="append", default=None, help="repeat for multiple stop strings")
    parser.add_argument(
        "--authorize-default-cap-cost-usd",
        type=float,
        default=None,
        help=(
            "explicit authorization for the isolated max_tokens-omission diagnostic; "
            f"must cover its projection and may not exceed ${DEFAULT_CAP_MAX_AUTHORIZATION_USD:.2f}"
        ),
    )
    return parser


def _validate_default_cap_authorization(
    plan: Sequence[ProbeSpec], authorization_usd: float | None
) -> None:
    diagnostics = [spec for spec in plan if spec.deliberately_omits_max_tokens]
    if not diagnostics:
        return
    if authorization_usd is None or not math.isfinite(authorization_usd):
        raise SystemExit(
            "live default-cap diagnostic requires --authorize-default-cap-cost-usd "
            "with a finite amount"
        )
    required = sum(projected_cost_usd(spec) for spec in diagnostics)
    if authorization_usd < required:
        raise SystemExit(
            f"default-cap authorization ${authorization_usd:.6f} is below the "
            f"projected upper bound ${required:.6f}"
        )
    if authorization_usd > DEFAULT_CAP_MAX_AUTHORIZATION_USD:
        raise SystemExit(
            f"default-cap authorization may not exceed "
            f"${DEFAULT_CAP_MAX_AUTHORIZATION_USD:.2f}"
        )


def _execute_live_plan(
    plan: Sequence[ProbeSpec],
    adapter: ProbeAdapter,
    writer: AppendOnlyJSONL,
    *,
    stdout: TextIO,
    default_cap_authorization_usd: float | None,
) -> int:
    """Execute an already-authorized plan with durable write-ahead records.

    This internal seam is exercised only with synthetic adapters. The public
    ``--live`` path cannot reach it while pinned Tinker 0.25.0 lacks an
    upstream-supported zero-resubmission transport.
    """
    run_records: list[dict[str, Any]] = []
    had_error = False
    for spec in plan:
        projection = print_cost_projection(spec, stdout)
        call_id = str(uuid.uuid4())
        cost_authorization_usd = (
            default_cap_authorization_usd if spec.deliberately_omits_max_tokens else None
        )
        # AppendOnlyJSONL.append flushes and fsyncs. A failure here propagates,
        # so adapter.sample remains unreachable without durable intent evidence.
        writer.append(
            make_attempt_started_record(
                spec,
                call_id=call_id,
                projected_cost=projection,
                cost_authorization_usd=cost_authorization_usd,
            )
        )
        started = time.perf_counter()
        try:
            result = adapter.sample(spec)
        except Exception as error:
            latency = time.perf_counter() - started
            record = make_error_record(
                spec,
                error,
                call_id=call_id,
                latency_seconds=latency,
                timestamp=_utc_now(),
                projected_cost_usd=projection,
                cost_authorization_usd=cost_authorization_usd,
            )
            writer.append(record)
            run_records.append(record)
            stdout.write(f"ERROR probe={spec.name} type={type(error).__name__}: {error}\n")
            had_error = True
            if spec.kind == "cap_semantics":
                stdout.write(
                    "FAIL CLOSED: exact target model/cap retained; no route or cap "
                    "substitution. Continuing the remaining independent cap probes.\n"
                )
                continue
            stdout.write(render_summary_table(summarize_records(run_records)) + "\n")
            return 1
        latency = time.perf_counter() - started
        records = make_response_records(
            spec,
            result,
            call_id=call_id,
            latency_seconds=latency,
            timestamp=_utc_now(),
            projected_cost_usd=projection,
            cost_authorization_usd=cost_authorization_usd,
        )
        for record in records:
            writer.append(record)
        run_records.extend(records)
        if any(record["returned_tokens_exceed_requested_cap"] is True for record in records):
            had_error = True
            stdout.write(
                f"CAP VIOLATION probe={spec.name}: returned tokens exceeded the exact "
                "requested cap; no substitution or retry will be attempted.\n"
            )

    stdout.write(render_summary_table(summarize_records(run_records)) + "\n")
    stdout.write(
        "LIMITATION: returned/native token counts are recorded, but the SDK sample "
        "response has no per-call billing receipt; billed-cap semantics remain unresolved "
        "until a human reconciles billing evidence.\n"
    )
    stdout.write(
        "OUTSTANDING: OpenAI gpt-5.6-terra usage-accounting sanity is not part of "
        "this Tinker tool and remains a preregistration blocker.\n"
    )
    return 1 if had_error else 0


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    adapter_factory: Callable[[str], ProbeAdapter] | None = None,
    stdout: TextIO | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    environ = os.environ if environ is None else environ
    stdout = sys.stdout if stdout is None else stdout
    plan = _select_plan(
        build_probe_plan(
            seed=args.seed,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            stop=args.stop,
        ),
        args.probe,
    )

    if not args.live:
        stdout.write("DRY RUN: zero Tinker client calls will be made.\n")
        stdout.write(render_plan_table(plan) + "\n")
        stdout.write(
            "UNRESOLVED: all Tinker facts require human live evidence; OpenAI "
            "gpt-5.6-terra usage-accounting sanity is a separate outstanding blocker.\n"
        )
        return 0

    api_key = environ.get("TINKER_API_KEY")
    if not api_key:
        raise SystemExit("--live requires TINKER_API_KEY in the environment")
    writer = AppendOnlyJSONL(args.report)
    writer.preflight()
    writer.append(
        make_control_record("sink_preflight", report_path=str(args.report), status="ok")
    )
    try:
        environment_manifest = verify_locked_environment()
    except Exception as error:
        writer.append(
            make_control_record(
                "environment_validation_failed",
                status="error",
                error={"type": type(error).__name__, "message": str(error)},
            )
        )
        raise
    writer.append(
        make_control_record(
            "environment_verified",
            status="ok",
            environment_manifest=environment_manifest,
        )
    )
    try:
        _validate_default_cap_authorization(plan, args.authorize_default_cap_cost_usd)
    except SystemExit as error:
        writer.append(
            make_control_record(
                "live_blocked",
                status="blocked",
                blocked_capability="default_cap_cost_authorization",
                reason=str(error),
            )
        )
        raise

    capability = inspect_pinned_sdk_one_attempt_capability()
    if capability["supported"]:
        # No live adapter exists until a specific upstream one-attempt contract
        # is independently reviewed and covered by an integration challenge.
        reason = "no audited upstream one-attempt adapter is implemented"
    else:
        reason = "; ".join(capability["reasons"])
    writer.append(
        make_control_record(
            "live_blocked",
            status="blocked",
            blocked_capability="zero_resubmission",
            reason=reason,
            sdk_capability=capability,
        )
    )
    raise SystemExit(
        "--live is disabled: zero-resubmission execution is unavailable for "
        f"pinned Tinker 0.25.0 ({reason})"
    )


if __name__ == "__main__":
    raise SystemExit(main())
