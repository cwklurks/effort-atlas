from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from effort_atlas import ROOT, load_config
from effort_atlas.analyze import effort_ordinal
from effort_atlas.client import InklingClient
from effort_atlas.openrouter_receipts import build_receipt
from effort_atlas.sweep import dry_run, load_items


class _FakeCompletions:
    def __init__(self, chunks: list[SimpleNamespace]):
        self.chunks = chunks
        self.kwargs: dict | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return iter(self.chunks)


class OpenRouterSupportTests(unittest.TestCase):
    def test_openrouter_config_isolated_from_tinker_paths(self):
        cfg = load_config(ROOT / "config_openrouter.yaml")

        self.assertEqual(cfg["provider"]["api_key_env"], "OPENROUTER_API_KEY")
        self.assertEqual(cfg["provider"]["base_url_env"], "OPENROUTER_BASE_URL")
        self.assertEqual(cfg["paths"]["cache"], ".cache_openrouter")
        self.assertEqual(cfg["paths"]["results"], "results_openrouter")
        self.assertEqual(cfg["paths"]["reports"], "reports_openrouter")

    def test_openrouter_stream_records_reasoning_usage_finish_and_provider(self):
        chunks = [
            SimpleNamespace(
                id="gen-test",
                usage=None,
                provider="Together",
                error=None,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=None,
                            reasoning="normalized reasoning",
                            reasoning_content="must not be duplicated",
                        ),
                        finish_reason=None,
                    )
                ],
            ),
            SimpleNamespace(
                id="gen-test",
                usage=SimpleNamespace(
                    completion_tokens=4321,
                    prompt_tokens=123,
                    completion_tokens_details=SimpleNamespace(
                        reasoning_tokens=4000,
                    ),
                    cost=0.017624,
                ),
                provider="Together",
                error=None,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content="Final answer: 42",
                            reasoning=None,
                            reasoning_content=" fallback reasoning",
                        ),
                        finish_reason="stop",
                    )
                ],
            ),
        ]
        completions = _FakeCompletions(chunks)
        client = InklingClient.__new__(InklingClient)
        client.cfg = {
            "provider": {
                "model": "thinkingmachines/inkling",
                "max_completion_tokens": 20000,
                "max_retries": 0,
                "request_extra_body": {
                    "provider": {
                        "only": ["together"],
                        "allow_fallbacks": False,
                    }
                },
            },
            "effort": {
                "mode": "openrouter_reasoning",
                "param_name": "reasoning",
            },
        }
        client._client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        result = client._real_complete("prompt", "high")

        self.assertEqual(result["text"], "Final answer: 42")
        self.assertEqual(
            result["reasoning_text"], "normalized reasoning fallback reasoning"
        )
        self.assertEqual(result["completion_tokens"], 4321)
        self.assertEqual(result["reasoning_tokens"], 4000)
        self.assertEqual(result["prompt_tokens"], 123)
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["provider"], "Together")
        self.assertEqual(result["generation_id"], "gen-test")
        self.assertEqual(result["reported_cost_usd"], 0.017624)
        self.assertEqual(
            completions.kwargs["extra_body"],
            {
                "reasoning": {"effort": "high", "exclude": False},
                "provider": {
                    "only": ["together"],
                    "allow_fallbacks": False,
                },
            },
        )
        self.assertNotIn("separate_reasoning", json.dumps(completions.kwargs))

    def test_openrouter_default_reasoning_mode_does_not_invent_effort(self):
        chunks = [
            SimpleNamespace(
                id="gen-default-reasoning",
                usage=SimpleNamespace(
                    completion_tokens=100,
                    prompt_tokens=10,
                    completion_tokens_details={"reasoning_tokens": 80},
                    cost=0.001,
                ),
                provider="Moonshot AI",
                error=None,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content="Final answer: 42",
                            reasoning="reasoning",
                            reasoning_content=None,
                        ),
                        finish_reason="stop",
                    )
                ],
            )
        ]
        completions = _FakeCompletions(chunks)
        client = InklingClient.__new__(InklingClient)
        client.cfg = {
            "provider": {
                "model": "moonshotai/kimi-k2.6",
                "max_completion_tokens": 2000,
                "max_retries": 0,
            },
            "effort": {
                "mode": "openrouter_reasoning_default",
                "param_name": "reasoning",
            },
        }
        client._client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        result = client._real_complete("prompt", "default", max_tokens=2000)

        self.assertEqual(result["reasoning_tokens"], 80)
        self.assertEqual(
            completions.kwargs["extra_body"],
            {"reasoning": {"enabled": True, "exclude": False}},
        )
        self.assertNotIn("effort", json.dumps(completions.kwargs["extra_body"]))

    def test_stream_without_terminal_usage_is_rejected(self):
        chunks = [
            SimpleNamespace(
                id="gen-incomplete",
                usage=None,
                provider="Together",
                error=None,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=None,
                            reasoning="partial reasoning",
                            reasoning_content=None,
                        ),
                        finish_reason=None,
                    )
                ],
            )
        ]
        client = InklingClient.__new__(InklingClient)
        client.cfg = {
            "provider": {
                "model": "thinkingmachines/inkling",
                "max_completion_tokens": 49152,
                "max_retries": 0,
            },
            "effort": {
                "mode": "openrouter_reasoning",
                "param_name": "reasoning",
            },
        }
        client._client = SimpleNamespace(
            chat=SimpleNamespace(completions=_FakeCompletions(chunks))
        )

        with self.assertRaisesRegex(
            RuntimeError, "ended without usage.*gen-incomplete"
        ):
            client._real_complete("prompt", "max")

    def test_unaccounted_real_cache_entry_is_not_replayed(self):
        client = InklingClient.__new__(InklingClient)
        client.mock = False
        client.cache_dir = ROOT / ".cache_openrouter_rescue"
        key = "test-unaccounted-entry"
        path = client.cache_dir / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"completion_tokens": -1, "prompt_tokens": -1}))
        try:
            self.assertIsNone(client._cache_get(key))
        finally:
            path.unlink(missing_ok=True)

    def test_categorical_efforts_follow_configured_ordinal_order(self):
        cfg = {
            "effort": {
                "ordinal": {
                    "minimal": 1,
                    "low": 2,
                    "medium": 3,
                    "high": 4,
                    "max": 5,
                }
            }
        }

        ordered = sorted(
            ["max", "medium", "minimal", "high", "low"],
            key=lambda effort: effort_ordinal(cfg, effort),
        )

        self.assertEqual(
            ordered, ["minimal", "low", "medium", "high", "max"]
        )

    def test_requested_output_budget_changes_cache_identity(self):
        client = InklingClient.__new__(InklingClient)
        client.cfg = {"provider": {"model": "thinkingmachines/inkling"}}
        client.mock = False

        tight = client._cache_key("prompt", "max", max_tokens=8192)
        generous = client._cache_key("prompt", "max", max_tokens=49152)

        self.assertNotEqual(tight, generous)

    def test_provider_route_changes_cache_identity(self):
        client = InklingClient.__new__(InklingClient)
        client.cfg = {
            "provider": {
                "model": "thinkingmachines/inkling",
                "request_extra_body": {"provider": {"only": ["together"]}},
            }
        }
        client.mock = False
        together = client._cache_key("prompt", "max", max_tokens=49152)
        client.cfg["provider"]["request_extra_body"] = {
            "provider": {"only": ["other-provider"]}
        }
        other = client._cache_key("prompt", "max", max_tokens=49152)

        self.assertNotEqual(together, other)

    def test_seed_changes_cache_identity_and_is_sent(self):
        chunks = [
            SimpleNamespace(
                id="gen-seeded",
                usage=SimpleNamespace(
                    completion_tokens=100,
                    prompt_tokens=10,
                    cost=0.001,
                ),
                provider="xAI",
                error=None,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content="Final answer: 42",
                            reasoning="reasoning",
                            reasoning_content=None,
                        ),
                        finish_reason="stop",
                    )
                ],
            )
        ]
        completions = _FakeCompletions(chunks)
        client = InklingClient.__new__(InklingClient)
        client.cfg = {
            "provider": {
                "model": "x-ai/grok-4.5",
                "max_completion_tokens": 49152,
                "max_retries": 0,
            },
            "effort": {
                "mode": "openrouter_reasoning",
                "param_name": "reasoning",
            },
        }
        client.mock = False
        client._client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        first = client._cache_key("prompt", "max", 49152, seed=7001)
        second = client._cache_key("prompt", "max", 49152, seed=7002)
        client._real_complete("prompt", "max", max_tokens=49152, seed=7001)

        self.assertNotEqual(first, second)
        self.assertEqual(completions.kwargs["seed"], 7001)

    def test_requested_output_budget_overrides_provider_default(self):
        chunks = [
            SimpleNamespace(
                id="gen-budget",
                usage=SimpleNamespace(
                    completion_tokens=100,
                    prompt_tokens=10,
                    cost=0.001,
                ),
                provider="Together",
                error=None,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content="Final answer: 42",
                            reasoning="reasoning",
                            reasoning_content=None,
                        ),
                        finish_reason="stop",
                    )
                ],
            )
        ]
        completions = _FakeCompletions(chunks)
        client = InklingClient.__new__(InklingClient)
        client.cfg = {
            "provider": {
                "model": "thinkingmachines/inkling",
                "max_completion_tokens": 20000,
                "max_retries": 0,
            },
            "effort": {
                "mode": "openrouter_reasoning",
                "param_name": "reasoning",
            },
        }
        client._client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        client._real_complete("prompt", "max", max_tokens=49152)

        self.assertEqual(completions.kwargs["max_tokens"], 49152)

    def test_load_items_can_select_an_explicit_ordered_subset(self):
        items = load_items(
            ROOT / "data",
            ["math"],
            limit=50,
            item_ids=["math_0015", "math_0003"],
        )

        self.assertEqual([item["id"] for item in items], ["math_0015", "math_0003"])

    def test_dry_run_counts_each_budget_and_reports_worst_case(self):
        cfg = {
            "provider": {"max_completion_tokens": 20000},
            "effort": {"levels": [0.99]},
            "sweep": {"budgets": [4096, 49152]},
            "pricing": {
                "expected_output_tokens": {"0.99": 18000},
                "expected_input_tokens": 1000,
                "input_per_mtok": 1.0,
                "output_per_mtok": 4.0,
            },
        }
        output = StringIO()

        with redirect_stdout(output):
            dry_run(cfg, [{"id": "math_0003"}])

        report = output.getvalue()
        self.assertIn("TOTAL", report)
        self.assertIn("2", report)
        self.assertIn("worst-case exposure", report)
        # Expected output is min(18,000, 4,096) + 18,000 = 22,096.
        self.assertIn("22,096", report)
        # Worst-case output is 4,096 + 49,152 = 53,248.
        self.assertIn("53,248", report)

    def test_dry_run_does_not_claim_cap_bound_when_reasoning_escapes_it(self):
        cfg = {
            "provider": {"max_completion_tokens": 20000},
            "effort": {"levels": ["high"]},
            "sweep": {"budgets": [20000]},
            "pricing": {
                "expected_output_tokens": {"high": 55000},
                "expected_input_tokens": 1000,
                "input_per_mtok": 2.0,
                "output_per_mtok": 6.0,
                "cap_bounds_billable_tokens": False,
            },
        }
        output = StringIO()

        with redirect_stdout(output):
            dry_run(cfg, [{"id": "math_0003"}])

        report = output.getvalue()
        self.assertIn("55,000", report)
        self.assertIn("not bounded by max_tokens", report)

    def test_generation_receipt_preserves_raw_openrouter_payload(self):
        row = {
            "item_id": "math_0003",
            "effort": "medium",
            "max_tokens_requested": 2000,
            "generation_id": "gen-receipt",
        }
        payload = {
            "data": {
                "id": "gen-receipt",
                "total_cost": 0.008,
                "native_tokens_completion": 2000,
                "native_tokens_reasoning": 1900,
            }
        }

        receipt = build_receipt("results/input.jsonl", row, payload)

        self.assertEqual(receipt["source_result"], "results/input.jsonl")
        self.assertEqual(receipt["item_id"], "math_0003")
        self.assertIs(receipt["openrouter_response"], payload)


if __name__ == "__main__":
    unittest.main()
