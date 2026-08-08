#!/usr/bin/env python3
"""Dry-run-first Tinker probes for REAP's pre-confirmatory smoke gates.

No model call is made unless ``--live`` is supplied and ``TINKER_API_KEY`` is
present in the environment. Live results are append-only JSONL records and do
not include raw response text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, TextIO


SCHEMA_VERSION = 1
SMOKE_MODEL = "openai/gpt-oss-20b"
# The extended-context IDs are deliberate: the base GPT-OSS-120B route has a
# 32K context and base Inkling has a 64K context, so a nonempty prompt plus a
# 65,536-token requested completion requires their longer-context variants.
CAP_PROBE_MODELS = (
    "thinkingmachines/Inkling:peft:262144",
    "openai/gpt-oss-120b:peft:131072",
)
CAP_PROBE_CAPS = (4096, 16384, 32768, 65536)
DEFAULT_REPORT_PATH = Path("reports/tinker_probe.jsonl")
PRICING_SOURCE = "https://tinker-docs.thinkingmachines.ai/tinker/models/"
PRICING_AS_OF = "2026-08-08"

# USD per million tokens. These are used only for an upper-bound projection
# printed before a human-authorized live call; actual billing must be reconciled
# separately. Values match the exact model IDs above on PRICING_AS_OF.
MODEL_PRICING = {
    "openai/gpt-oss-20b": {"prefill": 0.18, "sample": 0.45},
    "openai/gpt-oss-120b:peft:131072": {"prefill": 0.78, "sample": 1.94},
    "thinkingmachines/Inkling:peft:262144": {"prefill": 3.74, "sample": 9.36},
}

REQUIRED_RECORD_FIELDS = {
    "schema_version",
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
    "sample_index",
    "response_text_sha256",
    "usage",
    "stop_reason",
    "latency_seconds",
    "returned_tokens_exceed_requested_cap",
    "projected_cost_usd",
    "pricing_source",
    "pricing_as_of",
    "sdk_version",
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
    for model in CAP_PROBE_MODELS:
        model_label = "inkling" if model.startswith("thinkingmachines/Inkling") else "gpt_oss_120b"
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


class TinkerSDKAdapter:
    """Small adapter over the inspected Tinker 0.25 SDK surface."""

    def __init__(
        self,
        api_key: str,
        *,
        sdk_module: Any | None = None,
        retry_config_cls: type[Any] | None = None,
    ) -> None:
        if sdk_module is None:
            try:
                import tinker as sdk_module  # type: ignore[no-redef]
            except ImportError as exc:
                raise RuntimeError(
                    "The Tinker SDK is required for --live. Install the project-pinned "
                    "SDK in the human execution environment."
                ) from exc
        if retry_config_cls is None:
            try:
                from tinker.lib.retry_handler import RetryConfig as retry_config_cls
            except ImportError as exc:
                raise RuntimeError(
                    "Installed Tinker SDK does not expose the inspected RetryConfig API; "
                    "refusing a billed call because zero retries cannot be guaranteed."
                ) from exc
        self._sdk = sdk_module
        self._retry_config_cls = retry_config_cls
        # max_retries=0 disables the generated HTTP client's own retry layer.
        self._service = sdk_module.ServiceClient(api_key=api_key, max_retries=0)

    def sample(self, spec: ProbeSpec) -> CallResult:
        # enable_retry_logic=False disables the sampling client's retry handler.
        retry_config = self._retry_config_cls(enable_retry_logic=False)
        client = self._service.create_sampling_client(
            base_model=spec.model,
            retry_config=retry_config,
        )
        tokenizer = client.get_tokenizer()
        token_ids = _encode_prompt(tokenizer, spec.prompt)
        prompt = self._sdk.ModelInput.from_ints(token_ids)
        sampling_params = self._sdk.SamplingParams(**spec.request_params())
        response = client.sample(
            prompt=prompt,
            num_samples=spec.num_samples,
            sampling_params=sampling_params,
        ).result()
        observations = tuple(
            SampleObservation(
                text=tokenizer.decode(list(sequence.tokens)),
                completion_tokens=len(sequence.tokens),
                stop_reason=str(sequence.stop_reason),
            )
            for sequence in response.sequences
        )
        if len(observations) != spec.num_samples:
            raise RuntimeError(
                f"Tinker returned {len(observations)} sequences for num_samples={spec.num_samples}"
            )
        return CallResult(
            observations=observations,
            prompt_tokens=len(token_ids),
            prompt_cache_hit_tokens=int(getattr(response, "prompt_cache_hit_tokens", 0)),
            sdk_version=str(getattr(self._sdk, "__version__", "unknown")),
        )


def _encode_prompt(tokenizer: Any, prompt: str) -> list[int]:
    """Encode a one-turn user prompt without assuming one tokenizer family."""
    apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
    if callable(apply_chat_template):
        tokens = apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True,
            add_generation_prompt=True,
        )
    else:
        tokens = tokenizer.encode(prompt)
    if hasattr(tokens, "tolist"):
        tokens = tokens.tolist()
    if tokens and isinstance(tokens[0], list):
        if len(tokens) != 1:
            raise ValueError("tokenizer returned an unexpected batched prompt")
        tokens = tokens[0]
    return [int(token) for token in tokens]


class AppendOnlyJSONL:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


def hash_response_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_response_records(
    spec: ProbeSpec,
    result: CallResult,
    *,
    call_id: str,
    latency_seconds: float,
    timestamp: str,
    projected_cost_usd: float | None,
) -> list[dict[str, Any]]:
    records = []
    for sample_index, observation in enumerate(result.observations):
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
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
                "pricing_source": PRICING_SOURCE,
                "pricing_as_of": PRICING_AS_OF,
                "sdk_version": result.sdk_version,
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
    projected_cost_usd: float | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
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
        "pricing_source": PRICING_SOURCE,
        "pricing_as_of": PRICING_AS_OF,
        "sdk_version": None,
        "error": {"type": type(error).__name__, "message": str(error)},
    }


def projected_cost_usd(spec: ProbeSpec) -> float | None:
    """Return a conservative request upper bound, or None for default-cap."""
    if spec.max_tokens is None:
        return None
    prices = MODEL_PRICING[spec.model]
    estimated_prompt_tokens = max(1, math.ceil(len(spec.prompt.encode("utf-8")) / 4))
    prefill = estimated_prompt_tokens * prices["prefill"] / 1_000_000
    sample = spec.max_tokens * spec.num_samples * prices["sample"] / 1_000_000
    return prefill + sample


def print_cost_projection(spec: ProbeSpec, stream: TextIO) -> float | None:
    projection = projected_cost_usd(spec)
    if projection is None:
        detail = "upper_bound_usd=UNKNOWN reason=intentional_max_tokens_omission"
    else:
        detail = f"upper_bound_usd={projection:.6f}"
    stream.write(
        f"COST PROJECTION probe={spec.name} model={spec.model} {detail} "
        f"pricing_as_of={PRICING_AS_OF}\n"
    )
    stream.flush()
    return projection


def summarize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
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
    headers = ("probe", "kind", "class", "model", "max_tokens", "num_samples")
    rows = [
        (
            spec.name,
            spec.kind,
            spec.classification,
            spec.model,
            "OMITTED" if spec.deliberately_omits_max_tokens else str(spec.max_tokens),
            str(spec.num_samples),
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
    mode.add_argument("--live", action="store_true", help="make human-authorized billed calls")
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
    return parser


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

    factory = TinkerSDKAdapter if adapter_factory is None else adapter_factory
    adapter = factory(api_key)
    writer = AppendOnlyJSONL(args.report)
    run_records: list[dict[str, Any]] = []
    for spec in plan:
        projection = print_cost_projection(spec, stdout)
        call_id = str(uuid.uuid4())
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
            )
            writer.append(record)
            run_records.append(record)
            stdout.write(f"ERROR probe={spec.name} type={type(error).__name__}: {error}\n")
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
        )
        for record in records:
            writer.append(record)
        run_records.extend(records)

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
