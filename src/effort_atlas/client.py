"""OpenAI-compatible client for Inkling with effort injection, disk cache, retries.

Effort injection modes (config: effort.mode):
  param      → top-level request field, e.g. reasoning_effort=0.6
  extra_body → same field but inside extra_body (providers that reject unknown
               top-level kwargs need this)
  openrouter_reasoning → OpenRouter's normalized reasoning.effort object
  openrouter_reasoning_default → enable normalized reasoning without claiming
                                 a provider effort level
  system     → rendered into effort.system_template and prepended as a system msg

Mock mode never touches the network: it fabricates plausible responses with
effort-dependent accuracy/token behavior so the full pipeline can be exercised
for free.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Completion:
    text: str
    completion_tokens: int
    prompt_tokens: int
    latency_s: float
    reasoning_text: str = ""
    reasoning_tokens: int | None = None
    finish_reason: str = ""
    provider: str = ""
    generation_id: str = ""
    reported_cost_usd: float | None = None
    cached: bool = False
    mock: bool = False


class InklingClient:
    def __init__(self, cfg: dict, root: Path, mock: bool = False):
        self.cfg = cfg
        self.mock = mock
        self.cache_dir = root / cfg["paths"]["cache"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        if not mock:
            import os

            from dotenv import load_dotenv
            from openai import OpenAI

            pcfg = cfg["provider"]
            load_dotenv(
                root / ".env",
                override=bool(pcfg.get("env_file_override", False)),
            )
            api_key = os.environ.get(pcfg["api_key_env"])
            base_url = os.environ.get(pcfg["base_url_env"]) or pcfg.get("default_base_url")
            if not api_key:
                raise SystemExit(
                    f"Set {pcfg['api_key_env']} in .env "
                    "or run with --mock / --dry-run."
                )
            if "REPLACE" in pcfg["model"]:
                raise SystemExit(
                    "Set provider.model in config.yaml to your Tinker sampler "
                    "checkpoint path (tinker://…/sampler_weights/…)."
                )
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=pcfg["timeout_s"],
                max_retries=0,  # we do our own backoff
                default_headers=pcfg.get("default_headers"),
            )

    # ── public ────────────────────────────────────────────────────────────
    def complete(
        self,
        prompt: str,
        effort: str | float,
        item_id: str,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> Completion:
        key = self._cache_key(prompt, effort, max_tokens=max_tokens, seed=seed)
        cached = self._cache_get(key)
        if cached is not None:
            return Completion(**cached, cached=True)

        if self.mock:
            result = self._mock_complete(prompt, effort, item_id)
        else:
            result = self._real_complete(
                prompt,
                effort,
                max_tokens=max_tokens,
                seed=seed,
            )

        self._cache_put(key, result)
        return Completion(**result)

    # ── real request ──────────────────────────────────────────────────────
    def _real_complete(
        self,
        prompt: str,
        effort: str | float,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> dict:
        pcfg, ecfg = self.cfg["provider"], self.cfg["effort"]
        messages = []
        kwargs: dict = {}
        if ecfg["mode"] == "system":
            messages.append(
                {"role": "system",
                 "content": ecfg["system_template"].format(effort=effort)}
            )
        elif ecfg["mode"] == "param":
            kwargs[ecfg["param_name"]] = effort
        elif ecfg["mode"] == "extra_body":
            kwargs["extra_body"] = {
                ecfg["param_name"]: effort,
                # Tinker-specific: keep chain-of-thought out of final content.
                "separate_reasoning": True,
            }
        elif ecfg["mode"] == "openrouter_reasoning":
            kwargs["extra_body"] = {
                ecfg["param_name"]: {
                    "effort": effort,
                    "exclude": False,
                }
            }
        elif ecfg["mode"] == "openrouter_reasoning_default":
            kwargs["extra_body"] = {
                ecfg["param_name"]: {
                    "enabled": True,
                    "exclude": False,
                }
            }
        else:
            raise ValueError(f"Unknown effort mode: {ecfg['mode']}")
        request_extra_body = pcfg.get("request_extra_body")
        if request_extra_body:
            kwargs["extra_body"] = {
                **kwargs.get("extra_body", {}),
                **deepcopy(request_extra_body),
            }
        if seed is not None:
            kwargs["seed"] = seed
        messages.append({"role": "user", "content": prompt})

        last_err: Exception | None = None
        for attempt in range(pcfg["max_retries"] + 1):
            try:
                t0 = time.monotonic()
                # STREAMING: non-streamed calls died at ~60s (proxy kills idle
                # connections — discovered 2026-07-20 when uncapped high-effort
                # calls started exceeding a minute). Streaming keeps bytes
                # flowing so long generations survive.
                stream = self._client.chat.completions.create(
                    model=pcfg["model"],
                    messages=messages,
                    # NOTE: the endpoint ignores max_completion_tokens and
                    # defaults to 4096 — it respects the legacy max_tokens name.
                    max_tokens=(
                        max_tokens
                        if max_tokens is not None
                        else pcfg["max_completion_tokens"]
                    ),
                    stream=True,
                    stream_options={"include_usage": True},
                    **kwargs,
                )
                text_parts: list[str] = []
                reasoning_parts: list[str] = []
                finish_reason = ""
                usage = None
                served_provider = ""
                generation_id = ""
                for chunk in stream:
                    chunk_error = getattr(chunk, "error", None)
                    if chunk_error:
                        code = (
                            chunk_error.get("code")
                            if isinstance(chunk_error, dict)
                            else getattr(chunk_error, "code", None)
                        )
                        raise RuntimeError(
                            "Provider stream error"
                            f"{f' (HTTP {code})' if code else ''}"
                        )
                    if getattr(chunk, "usage", None):
                        usage = chunk.usage
                    if getattr(chunk, "id", None):
                        generation_id = str(chunk.id)
                    chunk_provider = getattr(chunk, "provider", None)
                    if chunk_provider:
                        served_provider = str(chunk_provider)
                    metadata = getattr(chunk, "openrouter_metadata", None)
                    metadata_provider = (
                        getattr(metadata, "provider", None) if metadata else None
                    )
                    if metadata_provider:
                        served_provider = str(metadata_provider)
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if getattr(delta, "content", None):
                            text_parts.append(delta.content)
                        rc = getattr(delta, "reasoning", None)
                        if not rc:
                            rc = getattr(delta, "reasoning_content", None)
                        if rc:
                            reasoning_parts.append(self._reasoning_text(rc))
                        if chunk.choices[0].finish_reason:
                            finish_reason = chunk.choices[0].finish_reason
                latency = time.monotonic() - t0
                if usage is None:
                    raise RuntimeError(
                        "Stream ended without usage accounting"
                        f" (generation_id={generation_id or 'unknown'})."
                    )
                if usage.completion_tokens is None or usage.prompt_tokens is None:
                    raise RuntimeError(
                        "Stream returned incomplete usage accounting"
                        f" (generation_id={generation_id or 'unknown'})."
                    )
                if not finish_reason:
                    raise RuntimeError(
                        "Stream ended without finish_reason"
                        f" (generation_id={generation_id or 'unknown'})."
                    )
                return {
                    "text": "".join(text_parts),
                    "reasoning_text": "".join(reasoning_parts),
                    "completion_tokens": usage.completion_tokens if usage else -1,
                    "prompt_tokens": usage.prompt_tokens if usage else -1,
                    "reasoning_tokens": self._reasoning_tokens(usage),
                    "latency_s": round(latency, 2),
                    "finish_reason": finish_reason,
                    "provider": served_provider,
                    "generation_id": generation_id,
                    "reported_cost_usd": (
                        float(usage.cost)
                        if usage and getattr(usage, "cost", None) is not None
                        else None
                    ),
                }
            except Exception as err:  # noqa: BLE001 — retry then surface
                status_code = getattr(err, "status_code", None)
                if status_code == 400 and "reasoning" in str(err).lower():
                    raise SystemExit(
                        f"Endpoint rejected reasoning_effort — this checkpoint may "
                        f"not support it. Full error: {err}"
                    ) from err
                if status_code in {400, 401, 402, 403}:
                    raise SystemExit(
                        f"Endpoint rejected the request with HTTP {status_code}."
                    ) from err
                last_err = err
                if attempt < pcfg["max_retries"]:
                    wait = min(2 ** attempt * 5, 120)
                    print(
                        f"    retry {attempt + 1} in {wait}s: "
                        f"{self._error_summary(err)}"
                    )
                    time.sleep(wait)
        raise RuntimeError(
            f"Request failed after retries: {self._error_summary(last_err)}"
        )

    @staticmethod
    def _reasoning_tokens(usage: object) -> int | None:
        details = getattr(usage, "completion_tokens_details", None)
        if details is None:
            return None
        value = (
            details.get("reasoning_tokens")
            if isinstance(details, dict)
            else getattr(details, "reasoning_tokens", None)
        )
        return int(value) if value is not None else None

    @staticmethod
    def _reasoning_text(value: object) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = []
            for part in value:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text") or part.get("content")
                    if text:
                        parts.append(str(text))
            if parts:
                return "".join(parts)
        return str(value)

    @staticmethod
    def _error_summary(err: Exception | None) -> str:
        if err is None:
            return "unknown error"
        if isinstance(err, RuntimeError):
            return str(err)
        status_code = getattr(err, "status_code", None)
        if status_code is not None:
            return f"HTTP {status_code} ({type(err).__name__})"
        return type(err).__name__

    # ── mock ──────────────────────────────────────────────────────────────
    def _mock_complete(self, prompt: str, effort: str | float, item_id: str) -> dict:
        """Deterministic fake: harder domains benefit from effort, easy ones don't."""
        rng = random.Random(f"{item_id}:{effort}")
        # crude domain guess from the item id prefix (math_… / extraction_… / …)
        domain = item_id.split("_")[0]
        base, gain = {"math": (0.35, 0.55), "knowledge": (0.55, 0.30),
                      "extraction": (0.90, 0.05), "code": (0.45, 0.40)}.get(
                          domain, (0.5, 0.3))
        ordinal = self.cfg["effort"].get("ordinal", {})
        if isinstance(effort, str):
            rank = float(ordinal[effort])
            effort_value = (rank - 1) / max(1, len(ordinal) - 1)
        else:
            effort_value = effort
        p_correct = base + gain * effort_value
        correct = rng.random() < p_correct
        # the sweep stores the gold answer in the prompt footer for mock mode only
        gold = prompt.rsplit("MOCK_GOLD:", 1)[-1].strip() if "MOCK_GOLD:" in prompt else "42"
        answer = gold if correct else f"WRONG_{rng.randint(0, 99)}"
        tokens = int(
            (300 + 20000 * effort_value ** 1.5) * rng.uniform(0.6, 1.4)
        )
        return {
            "text": f"(mock reasoning…)\nFinal answer: {answer}",
            "completion_tokens": tokens,
            "prompt_tokens": max(1, len(prompt) // 4),
            "latency_s": round(tokens / 4000, 2),
        }

    # ── cache ─────────────────────────────────────────────────────────────
    def _cache_key(
        self,
        prompt: str,
        effort: str | float,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> str:
        pcfg = self.cfg["provider"]
        identity = {
            "prompt": prompt,
            "effort": effort,
            "model": pcfg["model"],
            "mock": self.mock,
        }
        # Preserve the historical key exactly when no explicit budget axis is
        # configured. New budgeted runs include the requested cap so results
        # from different censoring conditions can never collide.
        if max_tokens is not None:
            identity["max_tokens"] = max_tokens
        if seed is not None:
            identity["seed"] = seed
        if pcfg.get("request_extra_body"):
            identity["request_extra_body"] = pcfg["request_extra_body"]
        blob = json.dumps(identity, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:32]

    def _cache_get(self, key: str) -> dict | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            result = json.loads(path.read_text())
            if not self.mock and (
                result.get("completion_tokens", -1) < 0
                or result.get("prompt_tokens", -1) < 0
            ):
                return None
            return result
        return None

    def _cache_put(self, key: str, result: dict) -> None:
        (self.cache_dir / f"{key}.json").write_text(json.dumps(result))
