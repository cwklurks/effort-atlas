from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import call, patch

from effort_atlas.client import Completion
from effort_atlas.confirmatory import AttemptLedger, EVENT_FIELDS
from effort_atlas.pilot_accounting import AccountingHalt
from effort_atlas.pilot_receipts import (
    fetch_receipt,
    reconcile_receipt,
    validate_completion,
)


def config():
    return {
        "provider": {
            "default_base_url": "https://openrouter.ai/api/v1",
            "base_url_env": "PILOT_TEST_BASE_URL",
            "api_key_env": "PILOT_TEST_API_KEY",
            "request_extra_body": {"provider": {"only": ["together"]}},
        },
        "pilot": {"cap": 1000, "input_token_allowance": 500},
        "pricing": {"input_per_mtok": 1.0, "output_per_mtok": 4.0},
        "budget": {"receipt_mismatch_stop_fraction": 0.20},
    }


def completion(**overrides):
    return replace(Completion(
        text="PRIVATE RESPONSE", reasoning_text="PRIVATE REASONING",
        prompt_tokens=100, completion_tokens=100, reasoning_tokens=80,
        latency_s=0.25, generation_id="gen-test-1", provider="Together",
        finish_reason="stop", reported_cost_usd=0.0005,
    ), **overrides)


def receipt(**overrides):
    return {"data": {
        "id": "gen-test-1", "provider_name": "Together",
        "finish_reason": "stop", "native_finish_reason": "stop",
        "native_tokens_prompt": 100, "native_tokens_completion": 100,
        "native_tokens_reasoning": 80, "total_cost": 0.0005,
        "response": "PRIVATE RECEIPT TEXT", "api_key": "PRIVATE KEY",
        **overrides,
    }}


class CompletionAccountingTests(unittest.TestCase):
    def test_valid_usage_and_provider_case_normalization(self):
        self.assertIsNone(validate_completion(config(), completion()))
        self.assertIsNone(validate_completion(config(), completion(provider="together")))

    def test_optional_usage_cost_and_inclusive_token_boundaries(self):
        self.assertIsNone(validate_completion(config(), completion(
            prompt_tokens=500, completion_tokens=1000, reasoning_tokens=None,
            reported_cost_usd=None, latency_s=0,
        )))

    def test_positive_integral_usage_required(self):
        for key in ("prompt_tokens", "completion_tokens"):
            for value in (None, True, False, -1, 0, 1.5, "100", float("nan"), float("inf")):
                with self.subTest(key=key, value=value), self.assertRaises(AccountingHalt):
                    validate_completion(config(), completion(**{key: value}))

    def test_optional_reasoning_must_be_integer_subset(self):
        for value in (True, -1, 1.5, "80", 101, float("nan")):
            with self.subTest(value=value), self.assertRaises(AccountingHalt):
                validate_completion(config(), completion(reasoning_tokens=value))

    def test_cost_and_latency_are_finite_nonnegative_numbers(self):
        for key in ("reported_cost_usd", "latency_s"):
            for value in (True, -1, "0.1", float("nan"), float("inf"), float("-inf")):
                with self.subTest(key=key, value=value), self.assertRaises(AccountingHalt):
                    validate_completion(config(), completion(**{key: value}))
        with self.assertRaises(AccountingHalt):
            validate_completion(config(), completion(latency_s=None))

    def test_usage_must_fit_cap_and_input_allowance(self):
        for overrides in ({"completion_tokens": 1001}, {"prompt_tokens": 501}):
            with self.subTest(overrides=overrides), self.assertRaises(AccountingHalt):
                validate_completion(config(), completion(**overrides))

    def test_stable_identity_and_supported_finish_required(self):
        for key, values in (
            ("generation_id", (None, "", " ", "gen\nchanged", " gen-test-1 ")),
            ("provider", (None, "", " ", "Together\nOther", "\vTogether")),
            ("finish_reason", (None, "", "unknown", "tool_calls", "stop\nlength", "\nstop")),
        ):
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(AccountingHalt):
                    validate_completion(config(), completion(**{key: value}))

    def test_provider_match_is_conservative_and_mock_skips_only_route(self):
        for provider in ("Other", "Together AI", "together/another-route"):
            with self.subTest(provider=provider), self.assertRaises(AccountingHalt):
                validate_completion(config(), completion(provider=provider))
        self.assertIsNone(validate_completion(config(), completion(provider="fake"), mock=True))
        with self.assertRaises(AccountingHalt):
            validate_completion(config(), completion(provider="fake", prompt_tokens=0), mock=True)

    def test_invalid_accounting_configuration_fails_safely(self):
        for section, key, value in (
            ("pilot", "cap", True), ("pilot", "input_token_allowance", 0),
            ("pilot", "cap", None),
        ):
            cfg = config()
            cfg[section][key] = value
            with self.subTest(key=key), self.assertRaises(AccountingHalt):
                validate_completion(cfg, completion())
        cfg = config()
        cfg["provider"]["request_extra_body"]["provider"]["only"] = ["together", "other"]
        with self.assertRaises(AccountingHalt):
            validate_completion(cfg, completion())


class ReceiptReconciliationTests(unittest.TestCase):
    def test_receipt_returns_only_safe_ledger_metadata(self):
        metadata = reconcile_receipt(config(), completion(), receipt())
        self.assertTrue(set(metadata) <= EVENT_FIELDS)
        self.assertEqual(metadata["receipt_generation_id"], "gen-test-1")
        self.assertEqual(metadata["receipt_provider"], "Together")
        self.assertEqual(metadata["receipt_cost_usd"], 0.0005)
        self.assertEqual(metadata["native_prompt_tokens"], 100)
        self.assertEqual(metadata["native_completion_tokens"], 100)
        self.assertEqual(metadata["native_reasoning_tokens"], 80)
        self.assertNotIn("PRIVATE", json.dumps(metadata))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            ledger = AttemptLedger(path)
            ledger.append({"event_type": "success", "generation_id": "gen-test-1", **metadata})
            persisted = json.loads(path.read_text())
            self.assertEqual(persisted["receipt_cost_usd"], 0.0005)
            self.assertEqual(persisted["receipt_generation_id"], "gen-test-1")
            self.assertNotIn("PRIVATE", path.read_text())

    def test_optional_native_reasoning_and_native_finish_are_retained_if_known(self):
        payload = receipt()
        del payload["data"]["native_tokens_reasoning"]
        del payload["data"]["native_finish_reason"]
        metadata = reconcile_receipt(config(), completion(), payload)
        self.assertIsNone(metadata.get("native_reasoning_tokens"))
        self.assertIsNone(metadata.get("native_finish_reason"))
        metadata = reconcile_receipt(config(), completion(reasoning_tokens=None), receipt())
        self.assertEqual(metadata["native_reasoning_tokens"], 80)

    def test_generation_provider_finish_and_usage_must_match(self):
        for key, value in (
            ("id", "gen-other"), ("provider_name", "Other"),
            ("finish_reason", "length"), ("native_tokens_prompt", 101),
            ("native_tokens_completion", 101), ("native_tokens_reasoning", 79),
        ):
            with self.subTest(key=key), self.assertRaises(AccountingHalt):
                reconcile_receipt(config(), completion(), receipt(**{key: value}))

    def test_public_finish_alias_uses_existing_normalizer(self):
        for finish in ("completed", "complete", "STOP"):
            with self.subTest(finish=finish):
                metadata = reconcile_receipt(config(), completion(), receipt(finish_reason=finish))
                self.assertEqual(metadata["receipt_finish_reason"], "stop")
        cfg = config()
        cfg["pilot"]["cap"] = 100
        metadata = reconcile_receipt(cfg, completion(finish_reason="length"),
                                     receipt(finish_reason="length"))
        self.assertEqual(metadata["receipt_finish_reason"], "length")

    def test_receipt_types_missing_fields_and_native_usage_are_validated(self):
        for payload in (None, [], {}, {"data": []}, {"data": None}):
            with self.subTest(payload=payload), self.assertRaises(AccountingHalt):
                reconcile_receipt(config(), completion(), payload)
        for key in ("id", "provider_name", "finish_reason", "total_cost",
                    "native_tokens_prompt", "native_tokens_completion"):
            payload = receipt()
            del payload["data"][key]
            with self.subTest(missing=key), self.assertRaises(AccountingHalt):
                reconcile_receipt(config(), completion(), payload)
        for key in ("native_tokens_prompt", "native_tokens_completion", "native_tokens_reasoning"):
            for value in (True, -1, "100", 1.5, float("inf")):
                with self.subTest(key=key, value=value), self.assertRaises(AccountingHalt):
                    reconcile_receipt(config(), completion(), receipt(**{key: value}))
        with self.assertRaises(AccountingHalt):
            reconcile_receipt(config(), completion(reasoning_tokens=None),
                              receipt(native_tokens_reasoning=101))

    def test_receipt_usage_cannot_exceed_either_allowance(self):
        for changes, native in (
            ({"prompt_tokens": 501}, {"native_tokens_prompt": 501}),
            ({"completion_tokens": 1001}, {"native_tokens_completion": 1001}),
        ):
            with self.subTest(changes=changes), self.assertRaises(AccountingHalt):
                reconcile_receipt(config(), completion(**changes), receipt(**native))

    def test_receipt_cost_must_be_finite_nonnegative_number(self):
        for value in (None, True, -1, "0.0005", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(AccountingHalt):
                reconcile_receipt(config(), completion(), receipt(total_cost=value))

    def test_price_prediction_counts_completion_once_and_accepts_exact_threshold(self):
        # 100 input * $1/M + 100 total completion * $4/M = $0.0005.
        # The 80 reasoning tokens are already included in the 100 completion tokens.
        for value in (0.0004, 0.0005, 0.0006):
            with self.subTest(value=value):
                metadata = reconcile_receipt(config(), completion(reported_cost_usd=None),
                                             receipt(total_cost=value))
                self.assertEqual(metadata["receipt_cost_usd"], value)
        for value in (0.000399999999, 0.000600000001):
            with self.subTest(value=value), self.assertRaises(AccountingHalt):
                reconcile_receipt(config(), completion(reported_cost_usd=None),
                                  receipt(total_cost=value))

    def test_stream_cost_comparison_is_independent_and_exact_at_threshold(self):
        for value in (0.0004, 0.0006):
            with self.subTest(value=value):
                reconcile_receipt(config(), completion(), receipt(total_cost=value))
        with self.assertRaises(AccountingHalt):
            reconcile_receipt(config(), completion(reported_cost_usd=0.0006), receipt(total_cost=0.0004))
        with self.assertRaises(AccountingHalt):
            reconcile_receipt(config(), completion(reported_cost_usd=0), receipt())

    def test_invalid_price_and_threshold_configuration_fail_safely(self):
        for section, key, value in (
            ("pricing", "input_per_mtok", float("nan")),
            ("pricing", "output_per_mtok", True),
            ("pricing", "output_per_mtok", -1),
            ("budget", "receipt_mismatch_stop_fraction", 1.1),
            ("budget", "receipt_mismatch_stop_fraction", -0.1),
            ("budget", "receipt_mismatch_stop_fraction", None),
        ):
            cfg = config()
            cfg[section][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AccountingHalt):
                reconcile_receipt(cfg, completion(), receipt())


class ReceiptFetchTests(unittest.TestCase):
    def test_successful_first_lookup_does_not_sleep(self):
        expected = receipt()
        with (patch.dict("os.environ", {"PILOT_TEST_API_KEY": "synthetic-test-key"}, clear=True),
              patch("effort_atlas.pilot_receipts._fetch_generation", return_value=expected) as fetch,
              patch("effort_atlas.pilot_receipts.time.sleep") as sleep):
            self.assertEqual(fetch_receipt(config(), "gen-test-1"), expected)
        fetch.assert_called_once()
        sleep.assert_not_called()

    def test_not_ready_payload_is_retried_and_then_fails_safely(self):
        with (patch.dict("os.environ", {"PILOT_TEST_API_KEY": "synthetic-test-key"}, clear=True),
              patch("effort_atlas.pilot_receipts._fetch_generation", return_value={"data": None}) as fetch,
              patch("effort_atlas.pilot_receipts.time.sleep") as sleep,
              self.assertRaises(AccountingHalt)):
            fetch_receipt(config(), "gen-test-1")
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_read_only_retries_reuse_generation_and_env_only_key(self):
        expected = receipt()
        with (patch.dict("os.environ", {"PILOT_TEST_API_KEY": "synthetic-test-key"}, clear=True),
              patch("effort_atlas.pilot_receipts._fetch_generation",
                    side_effect=[OSError("private transport detail"), ValueError("private detail"), expected]) as fetch,
              patch("effort_atlas.pilot_receipts.time.sleep") as sleep):
            self.assertEqual(fetch_receipt(config(), "gen-test-1"), expected)
        self.assertEqual(fetch.call_args_list, [call("https://openrouter.ai/api/v1", "synthetic-test-key", "gen-test-1")] * 3)
        self.assertEqual(sleep.call_args_list, [call(0.25), call(0.5)])

    def test_exhaustion_is_bounded_and_does_not_expose_transport_error(self):
        with (patch.dict("os.environ", {"PILOT_TEST_API_KEY": "synthetic-test-key"}, clear=True),
              patch("effort_atlas.pilot_receipts._fetch_generation", side_effect=OSError("PRIVATE KEY AND BODY")) as fetch,
              patch("effort_atlas.pilot_receipts.time.sleep") as sleep,
              self.assertRaises(AccountingHalt) as caught):
            fetch_receipt(config(), "gen-test-1")
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertNotIn("PRIVATE", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_fixed_endpoint_and_env_key_fail_before_transport(self):
        cases = (
            ({}, {}),
            ({"default_base_url": "https://attacker.invalid/api/v1"}, {"PILOT_TEST_API_KEY": "fake"}),
            ({}, {"PILOT_TEST_API_KEY": "fake", "PILOT_TEST_BASE_URL": "http://openrouter.ai/api/v1"}),
            ({}, {"PILOT_TEST_API_KEY": "fake", "PILOT_TEST_BASE_URL": "https://openrouter.ai/api/v1?key=private"}),
            ({}, {"PILOT_TEST_API_KEY": "fake", "PILOT_TEST_BASE_URL": "https://user:pass@openrouter.ai/api/v1"}),
        )
        for overrides, environment in cases:
            cfg = config()
            cfg["provider"].update(overrides)
            with (self.subTest(overrides=overrides), patch.dict("os.environ", environment, clear=True),
                  patch("effort_atlas.pilot_receipts._fetch_generation") as fetch,
                  self.assertRaises(AccountingHalt)):
                fetch_receipt(cfg, "gen-test-1")
            fetch.assert_not_called()

    def test_invalid_generation_never_reaches_transport(self):
        with (patch.dict("os.environ", {"PILOT_TEST_API_KEY": "fake"}, clear=True),
              patch("effort_atlas.pilot_receipts._fetch_generation") as fetch,
              self.assertRaises(AccountingHalt)):
            fetch_receipt(config(), "gen\nunsafe")
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
