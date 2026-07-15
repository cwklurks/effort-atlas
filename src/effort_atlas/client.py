"""OpenAI-compatible client for Inkling with effort injection, disk cache, retries.

Effort injection modes (config: effort.mode):
  param      → top-level request field, e.g. reasoning_effort=0.6
  extra_body → same field but inside extra_body (providers that reject unknown
               top-level kwargs need this)
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
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Completion:
    text: str
    completion_tokens: int
    prompt_tokens: int
    latency_s: float
    reasoning_text: str = ""
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

            load_dotenv(root / ".env")
            pcfg = cfg["provider"]
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
            )

    # ── public ────────────────────────────────────────────────────────────
    def complete(self, prompt: str, effort: float, item_id: str) -> Completion:
        key = self._cache_key(prompt, effort)
        cached = self._cache_get(key)
        if cached is not None:
            return Completion(**cached, cached=True)

        if self.mock:
            result = self._mock_complete(prompt, effort, item_id)
        else:
            result = self._real_complete(prompt, effort)

        self._cache_put(key, result)
        return Completion(**result)

    # ── real request ──────────────────────────────────────────────────────
    def _real_complete(self, prompt: str, effort: float) -> dict:
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
            kwargs["extra_body"] = {ecfg["param_name"]: effort}
        else:
            raise ValueError(f"Unknown effort mode: {ecfg['mode']}")
        # Tinker: keep chain-of-thought out of `content` (defaults true; be explicit)
        kwargs.setdefault("extra_body", {})["separate_reasoning"] = True
        messages.append({"role": "user", "content": prompt})

        last_err: Exception | None = None
        for attempt in range(pcfg["max_retries"] + 1):
            try:
                t0 = time.monotonic()
                resp = self._client.chat.completions.create(
                    model=pcfg["model"],
                    messages=messages,
                    max_completion_tokens=pcfg["max_completion_tokens"],
                    **kwargs,
                )
                latency = time.monotonic() - t0
                usage = resp.usage
                msg = resp.choices[0].message
                return {
                    "text": msg.content or "",
                    "reasoning_text": getattr(msg, "reasoning_content", None) or "",
                    "completion_tokens": usage.completion_tokens if usage else -1,
                    "prompt_tokens": usage.prompt_tokens if usage else -1,
                    "latency_s": round(latency, 2),
                }
            except Exception as err:  # noqa: BLE001 — retry then surface
                if "400" in str(err) and "reasoning" in str(err).lower():
                    raise SystemExit(
                        f"Endpoint rejected reasoning_effort — this checkpoint may "
                        f"not support it. Full error: {err}"
                    ) from err
                last_err = err
                wait = min(2 ** attempt * 2, 60)
                print(f"    retry {attempt + 1} in {wait}s: {err}")
                time.sleep(wait)
        raise RuntimeError(f"Request failed after retries: {last_err}")

    # ── mock ──────────────────────────────────────────────────────────────
    def _mock_complete(self, prompt: str, effort: float, item_id: str) -> dict:
        """Deterministic fake: harder domains benefit from effort, easy ones don't."""
        rng = random.Random(f"{item_id}:{effort}")
        # crude domain guess from the item id prefix (math_… / extraction_… / …)
        domain = item_id.split("_")[0]
        base, gain = {"math": (0.35, 0.55), "knowledge": (0.55, 0.30),
                      "extraction": (0.90, 0.05), "code": (0.45, 0.40)}.get(
                          domain, (0.5, 0.3))
        p_correct = base + gain * effort
        correct = rng.random() < p_correct
        # the sweep stores the gold answer in the prompt footer for mock mode only
        gold = prompt.rsplit("MOCK_GOLD:", 1)[-1].strip() if "MOCK_GOLD:" in prompt else "42"
        answer = gold if correct else f"WRONG_{rng.randint(0, 99)}"
        tokens = int((300 + 20000 * effort ** 1.5) * rng.uniform(0.6, 1.4))
        return {
            "text": f"(mock reasoning…)\nFinal answer: {answer}",
            "completion_tokens": tokens,
            "prompt_tokens": max(1, len(prompt) // 4),
            "latency_s": round(tokens / 4000, 2),
        }

    # ── cache ─────────────────────────────────────────────────────────────
    def _cache_key(self, prompt: str, effort: float) -> str:
        pcfg = self.cfg["provider"]
        blob = json.dumps(
            {"prompt": prompt, "effort": effort, "model": pcfg["model"],
             "mock": self.mock},
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:32]

    def _cache_get(self, key: str) -> dict | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def _cache_put(self, key: str, result: dict) -> None:
        (self.cache_dir / f"{key}.json").write_text(json.dumps(result))
