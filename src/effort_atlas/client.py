"""OpenAI-compatible client with validated, single-attempt requests and disk cache.

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
import math
import os
import random
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


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


class RequestFailure(RuntimeError):
    """Content-free request failure with safe partial accounting for the ledger.

    ``submitted`` means create() was entered, so billing may have occurred even
    without a generation ID or usage. It never implies a safe retry.

    The SDK can discard top-level accounting on SSE error events before yielding
    them. Missing metadata stays unknown; callers must retain the reservation
    and stop submissions until accounting is reconciled.
    """

    def __init__(self, code: str, *, submitted: bool = False,
                 metadata: dict | None = None, status_code: int | None = None,
                 interrupted: bool = False):
        self.code = code
        self.submitted = submitted
        self.interrupted = interrupted
        self.status_code = status_code if type(status_code) is int else None
        self.metadata = {
            "generation_id": "", "provider": "", "finish_reason": "",
            "prompt_tokens": None, "completion_tokens": None,
            "reasoning_tokens": None, "reported_cost_usd": None, "latency_s": None,
            **(metadata or {}),
        }
        super().__init__(f"Request failed: {code}")


class InklingClient:
    def __init__(self, cfg: dict, root: Path, mock: bool = False, *,
                 live_authorized: bool = False):
        if not mock and live_authorized is not True:
            raise PermissionError("Live client construction requires explicit authorization")
        self.cfg = cfg
        self.mock = mock
        self._client = None
        if not mock:
            from openai import DefaultHttpxClient, OpenAI

            pcfg = cfg["provider"]
            self._validate_retries()
            self._validate_headers()
            api_key = os.environ.get(pcfg["api_key_env"])
            base_url = os.environ.get(pcfg["base_url_env"]) or pcfg.get("default_base_url")
            if not api_key:
                raise RequestFailure("missing_api_key_environment")
            self._endpoint_identity = self._safe_endpoint(base_url)
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=pcfg["timeout_s"],
                max_retries=0,
                default_headers=pcfg.get("default_headers"),
                http_client=DefaultHttpxClient(follow_redirects=False),
            )
        self.cache_dir = root / cfg["paths"]["cache"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── public ────────────────────────────────────────────────────────────
    def complete(
        self,
        prompt: str,
        effort: str | float,
        item_id: str,
        max_tokens: int | None = None,
        seed: int | None = None,
        messages: list[dict] | None = None,
    ) -> Completion:
        """`messages` (optional) sends a multi-turn chat history instead of a
        single user turn; `prompt` is then only used by mock mode and for the
        cache key alongside the canonical messages."""
        if not self.mock:
            self._request_kwargs(prompt, effort, max_tokens, seed, messages)
            self._validate_retries()
            self._validate_transport()
        key = self._cache_key(
            prompt, effort, max_tokens=max_tokens, seed=seed, messages=messages,
            item_id=item_id,
        )
        cached = self.cached_completion(prompt, effort, item_id, max_tokens, seed, messages)
        if cached is not None:
            return cached

        if self.mock:
            result = self._mock_complete(prompt, effort, item_id)
        else:
            result = self._real_complete(
                prompt,
                effort,
                max_tokens=max_tokens,
                seed=seed,
                messages=messages,
            )

        try:
            self._cache_put(key, result)
        except BaseException as err:
            if self.mock:
                raise
            metadata = {name: result.get(name) for name in RequestFailure("initial").metadata}
            raise RequestFailure(
                "cache_write_failed", submitted=True, metadata=metadata,
                interrupted=isinstance(err, (KeyboardInterrupt, SystemExit)),
            ) from None
        return Completion(**result)

    def cached_completion(
        self, prompt: str, effort: str | float, item_id: str,
        max_tokens: int | None = None, seed: int | None = None,
        messages: list[dict] | None = None,
    ) -> Completion | None:
        """Read this exact item/run/request from disk without making a request."""
        key = self._cache_key(prompt, effort, max_tokens, seed, messages, item_id)
        cached = self._cache_get(key)
        return Completion(**cached, cached=True) if cached is not None else None

    # ── real request ──────────────────────────────────────────────────────
    def _real_complete(
        self,
        prompt: str,
        effort: str | float,
        max_tokens: int | None = None,
        seed: int | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        request = self._request_kwargs(prompt, effort, max_tokens, seed, messages)
        self._validate_retries()
        self._validate_transport()
        metadata = RequestFailure("initial").metadata
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        stream = None
        t0 = time.monotonic()
        try:
            # A create call is a potentially billed attempt, even if it raises.
            stream = self._client.chat.completions.create(**request)
            for chunk in stream:
                self._record_chunk_metadata(chunk, metadata)
                if self._field(chunk, "error"):
                    raise RequestFailure("provider_stream_error")
                choices = self._field(chunk, "choices") or []
                if len(choices) > 1:
                    raise RequestFailure("multiple_completion_choices")
                if choices:
                    choice = choices[0]
                    if type(self._field(choice, "index")) is not int or self._field(choice, "index") != 0:
                        raise RequestFailure("invalid_completion_index")
                    delta = self._field(choice, "delta")
                    content = self._field(delta, "content")
                    if content:
                        if not isinstance(content, str):
                            raise RequestFailure("invalid_content")
                        text_parts.append(content)
                    reasoning = self._field(delta, "reasoning") or self._field(delta, "reasoning_content")
                    if reasoning:
                        reasoning_parts.append(self._reasoning_text(reasoning))
                    finish_reason = self._field(choice, "finish_reason")
                    if finish_reason:
                        self._record_identity(metadata, "finish_reason", finish_reason)
            if metadata["completion_tokens"] is None or metadata["prompt_tokens"] is None:
                raise RequestFailure("missing_usage_accounting")
            if not metadata["finish_reason"]:
                raise RequestFailure("missing_finish_reason")
            completed_stream, stream = stream, None
            if callable(getattr(completed_stream, "close", None)):
                completed_stream.close()
            metadata["latency_s"] = round(time.monotonic() - t0, 2)
            return {"text": "".join(text_parts), "reasoning_text": "".join(reasoning_parts), **metadata}
        except BaseException as err:
            # Preserve accounting on interrupts as well as SDK/stream failures.
            # Never chain raw SDK exceptions, which may include private prompts.
            metadata["latency_s"] = round(time.monotonic() - t0, 2)
            code = err.code if isinstance(err, RequestFailure) else (
                "interrupted" if isinstance(err, (KeyboardInterrupt, SystemExit)) else "request_error"
            )
            raise RequestFailure(
                code, submitted=True, metadata=metadata,
                status_code=getattr(err, "status_code", None),
                interrupted=isinstance(err, (KeyboardInterrupt, SystemExit)),
            ) from None
        finally:
            if stream is not None and callable(getattr(stream, "close", None)):
                try:
                    stream.close()
                except BaseException:
                    # Closing a failed stream must not replace its ledger metadata.
                    pass

    def _validate_retries(self) -> None:
        retries = self.cfg["provider"].get("max_retries")
        sdk_retries = getattr(self._client, "max_retries", 0)
        if type(retries) is not int or retries != 0 or type(sdk_retries) is not int or sdk_retries != 0:
            raise RequestFailure("retries_forbidden")

    def _validate_transport(self) -> None:
        # HTTP 307/308 redirects can repeat a billed POST independently of SDK
        # retry settings. Recheck the effective HTTP client before every create.
        transport = getattr(self._client, "_client", None)
        if transport is not None and getattr(transport, "follow_redirects", None) is not False:
            raise RequestFailure("redirects_forbidden")

    def _validate_headers(self) -> None:
        headers = self.cfg["provider"].get("default_headers", {})
        if not isinstance(headers, dict) or any(
            key != "X-OpenRouter-Metadata" or value != "enabled" for key, value in headers.items()
        ):
            raise RequestFailure("forbidden_default_headers")

    def _request_kwargs(self, prompt: str, effort: str | float,
                        max_tokens: int | None, seed: int | None,
                        chat_history: list[dict] | None) -> dict:
        """Build the entire billed request before entering the SDK boundary."""
        pcfg, ecfg = self.cfg["provider"], self.cfg["effort"]
        self._validate_headers()
        cap = max_tokens if max_tokens is not None else pcfg.get("max_completion_tokens")
        if type(cap) is not int or cap <= 0:
            raise RequestFailure("invalid_max_tokens")
        if seed is not None and type(seed) is not int:
            raise RequestFailure("invalid_seed")
        if not isinstance(pcfg.get("model"), str) or not pcfg["model"].strip() or "REPLACE" in pcfg["model"]:
            raise RequestFailure("invalid_model")
        mode = ecfg.get("mode")
        if not isinstance(mode, str):
            raise RequestFailure("invalid_effort_configuration")
        names = {"param": "reasoning_effort", "extra_body": "reasoning_effort",
                 "openrouter_reasoning": "reasoning", "openrouter_reasoning_default": "reasoning"}
        if mode != "system" and (mode not in names or ecfg.get("param_name") != names[mode]):
            raise RequestFailure("invalid_effort_configuration")
        categorical = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
        if mode == "openrouter_reasoning_default":
            valid_effort = effort == "default"
        elif mode == "openrouter_reasoning":
            valid_effort = isinstance(effort, str) and effort in categorical
        else:
            valid_effort = ((isinstance(effort, str) and effort in categorical)
                            or (type(effort) in (float, int) and math.isfinite(effort) and 0 <= effort < 1))
        if not valid_effort:
            raise RequestFailure("invalid_effort")
        extra = pcfg.get("request_extra_body", {})
        if not isinstance(extra, dict) or set(extra) - {"provider"}:
            raise RequestFailure("forbidden_request_extra")
        if "provider" in extra and not isinstance(extra["provider"], dict):
            raise RequestFailure("invalid_provider_extra")
        if not isinstance(prompt, str):
            raise RequestFailure("invalid_prompt")
        if chat_history is not None:
            if not isinstance(chat_history, list) or not chat_history:
                raise RequestFailure("invalid_messages")
            for message in chat_history:
                if (not isinstance(message, dict) or set(message) != {"role", "content"}
                        or not isinstance(message["role"], str)
                        or message["role"] not in {"system", "developer", "user", "assistant"}
                        or not isinstance(message["content"], str)):
                    raise RequestFailure("invalid_messages")
        messages: list[dict] = []
        kwargs: dict = {}
        if mode == "system":
            template = ecfg.get("system_template")
            if not isinstance(template, str) or "{effort}" not in template:
                raise RequestFailure("invalid_effort_template")
            try:
                system_content = template.format(effort=effort)
            except (KeyError, ValueError, IndexError):
                raise RequestFailure("invalid_effort_template") from None
            messages.append(
                {"role": "system", "content": system_content}
            )
        elif mode == "param":
            kwargs["reasoning_effort"] = effort
        elif mode == "extra_body":
            kwargs["extra_body"] = {
                "reasoning_effort": effort,
                # Tinker-specific: keep chain-of-thought out of final content.
                "separate_reasoning": True,
            }
        elif mode == "openrouter_reasoning":
            kwargs["extra_body"] = {
                "reasoning": {
                    "effort": effort,
                    "exclude": False,
                }
            }
        elif mode == "openrouter_reasoning_default":
            kwargs["extra_body"] = {
                "reasoning": {
                    "enabled": True,
                    "exclude": False,
                }
            }
        if extra:
            kwargs["extra_body"] = {
                **kwargs.get("extra_body", {}),
                **deepcopy(extra),
            }
        if seed is not None:
            kwargs["seed"] = seed
        if chat_history is not None:
            messages.extend(
                {"role": m["role"], "content": m["content"]} for m in chat_history
            )
        else:
            messages.append({"role": "user", "content": prompt})

        # Keep the endpoint's legacy max_tokens field explicit: it previously
        # ignored max_completion_tokens and silently capped output at 4096.
        return {"model": pcfg["model"], "messages": messages, "max_tokens": cap,
                "n": 1, "stream": True, "stream_options": {"include_usage": True}, **kwargs}

    @staticmethod
    def _field(value: object, key: str):
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)

    @staticmethod
    def _record_identity(metadata: dict, key: str, value: object) -> None:
        # IDs/provider labels are data, never error text or serialized payloads.
        patterns = {"generation_id": r"(?:gen|chatcmpl)-[A-Za-z0-9_-]{1,180}",
                    "provider": r"[A-Za-z0-9][A-Za-z0-9 ._:/()\-]{0,63}",
                    "finish_reason": r"stop|length|tool_calls|content_filter|function_call|error"}
        if not isinstance(value, str) or not re.fullmatch(patterns[key], value):
            raise RequestFailure(f"invalid_{key}")
        if metadata[key] and metadata[key] != value:
            raise RequestFailure(f"changed_{key}")
        metadata[key] = value

    def _record_chunk_metadata(self, chunk: object, metadata: dict) -> None:
        failure = None
        identity_metadata = metadata.copy()
        for key, value in (("generation_id", self._field(chunk, "id")),
                           ("provider", self._field(chunk, "provider")),
                           ("provider", self._field(self._field(chunk, "openrouter_metadata"), "provider"))):
            if value:
                try:
                    self._record_identity(identity_metadata, key, value)
                except RequestFailure as err:
                    if metadata[key] or err.code in {"changed_generation_id", "changed_provider"}:
                        # No metadata from a conflicting identity belongs to the
                        # previously recorded generation, including its usage.
                        raise
                    failure = failure or err
        metadata.update(identity_metadata)
        choices = self._field(chunk, "choices") or []
        if len(choices) == 1 and self._field(choices[0], "index") == 0:
            finish_reason = self._field(choices[0], "finish_reason")
            if finish_reason:
                try:
                    self._record_identity(metadata, "finish_reason", finish_reason)
                except RequestFailure as err:
                    failure = failure or err
        usage = self._field(chunk, "usage")
        if usage is None:
            if failure:
                raise failure
            return
        values = {key: self._field(usage, key) for key in ("completion_tokens", "prompt_tokens")}
        values["reasoning_tokens"] = self._field(self._field(usage, "completion_tokens_details"), "reasoning_tokens")
        invalid = False
        for key, value in values.items():
            if value is None:
                continue
            if type(value) is not int or value < 0:
                invalid = True
            else:
                metadata[key] = value
        cost = self._field(usage, "cost")
        if cost is not None:
            if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
                invalid = True
            else:
                metadata["reported_cost_usd"] = float(cost)
        if invalid:
            raise RequestFailure("invalid_usage_accounting")
        if failure:
            raise failure

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
        if isinstance(err, RequestFailure):
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
        messages: list[dict] | None = None,
        item_id: str | None = None,
    ) -> str:
        pcfg = self.cfg["provider"]
        identity = {
            "cache_version": 2,
            "prompt": prompt,
            "effort": effort,
            "effort_config": self.cfg.get("effort"),
            "model": pcfg["model"],
            "mock": self.mock,
            "item_id": item_id,
            "run_id": self.cfg.get("_pilot_run_id"),
            "endpoint": self._safe_endpoint(
                getattr(getattr(self, "_client", None), "base_url", None)
                or getattr(self, "_endpoint_identity", None)
                or pcfg.get("default_base_url")
            ),
            "endpoint_env_name": pcfg.get("base_url_env"),
            "max_tokens": max_tokens if max_tokens is not None else pcfg.get("max_completion_tokens"),
            "n": 1,
        }
        if messages is not None:
            identity["messages"] = messages
        if seed is not None:
            identity["seed"] = seed
        if pcfg.get("request_extra_body"):
            identity["request_extra_body"] = pcfg["request_extra_body"]
        blob = json.dumps(identity, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:32]

    @staticmethod
    def _safe_endpoint(value: object) -> str:
        """Endpoint identity excludes userinfo and query credentials."""
        if value is None:
            return "default"
        try:
            parsed = urlsplit(str(value))
            host = parsed.hostname or ""
            if ":" in host:
                host = f"[{host}]"
            if parsed.port is not None:
                host += f":{parsed.port}"
            return urlunsplit((parsed.scheme.lower(), host, parsed.path.rstrip("/"), "", ""))
        except ValueError:
            raise RequestFailure("invalid_endpoint") from None

    def _cache_get(self, key: str) -> dict | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            try:
                result = json.loads(path.read_text())
            except (ValueError, OSError):
                return None
            if not self.mock and (
                not isinstance(result, dict)
                or any(type(result.get(key)) is not int or result[key] < 0
                       for key in ("completion_tokens", "prompt_tokens"))
            ):
                return None
            return result
        return None

    def _cache_put(self, key: str, result: dict) -> None:
        (self.cache_dir / f"{key}.json").write_text(json.dumps(result))
