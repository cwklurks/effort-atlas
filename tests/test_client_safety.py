from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import httpx
import openai

from effort_atlas.client import InklingClient


def config() -> dict:
    return {
        "provider": {
            "model": "synthetic/model",
            "api_key_env": "SYNTHETIC_API_KEY",
            "base_url_env": "SYNTHETIC_BASE_URL",
            "default_base_url": "https://offline.invalid/v1",
            "timeout_s": 10,
            "max_completion_tokens": 1000,
            "max_retries": 0,
            "request_extra_body": {
                "provider": {
                    "only": ["synthetic"],
                    "allow_fallbacks": False,
                    "require_parameters": True,
                }
            },
        },
        "effort": {"mode": "openrouter_reasoning", "param_name": "reasoning"},
        "paths": {"cache": "cache"},
        "_pilot_run_id": "synthetic-run",
    }


def chunk(**changes):
    values = {
        "id": "gen-synthetic",
        "provider": "Synthetic Provider",
        "usage": NS(prompt_tokens=10, completion_tokens=100, cost=0.01),
        "error": None,
        "choices": [NS(index=0, delta=NS(content="Final answer: A"), finish_reason="stop")],
    }
    values.update(changes)
    return NS(**values)


class FakeCompletions:
    def __init__(self, values=None):
        self.values = values if values is not None else [chunk()]
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        def stream():
            for value in self.values:
                if isinstance(value, BaseException):
                    raise value
                yield value

        return stream()


def fake_client(cfg=None, values=None):
    client = InklingClient.__new__(InklingClient)
    client.cfg = copy.deepcopy(cfg if cfg is not None else config())
    client.mock = False
    completions = FakeCompletions(values)
    client._client = NS(chat=NS(completions=completions), max_retries=0)
    return client, completions


class ClientSafetyTests(unittest.TestCase):
    def test_constructor_requires_explicit_authorization_before_sdk_or_cache(self):
        with tempfile.TemporaryDirectory() as directory, patch("openai.OpenAI") as sdk:
            root = Path(directory)
            with self.assertRaises(PermissionError):
                InklingClient(config(), root)
            sdk.assert_not_called()
            self.assertFalse((root / "cache").exists())

    def test_authorized_constructor_reads_only_environment(self):
        with tempfile.TemporaryDirectory() as directory, patch("openai.OpenAI") as sdk:
            with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key"}, clear=True):
                with patch("dotenv.load_dotenv") as dotenv:
                    InklingClient(config(), Path(directory), live_authorized=True)
            dotenv.assert_not_called()
            self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)
            transport = sdk.call_args.kwargs["http_client"]
            self.assertIsInstance(transport, openai.DefaultHttpxClient)
            self.assertFalse(transport.follow_redirects)
            transport.close()

    def test_missing_environment_secret_is_sanitized_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with patch("openai.OpenAI") as sdk, self.assertRaises(RuntimeError) as raised:
                InklingClient(config(), Path(directory), live_authorized=True)
            self.assertEqual(type(raised.exception).__name__, "RequestFailure")
            self.assertFalse(raised.exception.submitted)
            sdk.assert_not_called()

    def test_every_protected_extra_is_refused_before_create(self):
        protected = {
            "model": "other", "messages": [], "max_tokens": 2000,
            "max_completion_tokens": 2000, "n": 2, "seed": 2,
            "reasoning": {"effort": "max"}, "reasoning_effort": "max",
            "stream": False, "stream_options": {}, "temperature": 2,
            "tools": [], "route": "fallback", "extra_body": {},
        }
        for name, value in protected.items():
            with self.subTest(field=name):
                cfg = config()
                cfg["provider"]["request_extra_body"][name] = value
                client, completions = fake_client(cfg)
                with self.assertRaises(RuntimeError) as raised:
                    client._real_complete("PRIVATE_PROMPT", "medium", max_tokens=1000)
                self.assertEqual(type(raised.exception).__name__, "RequestFailure")
                self.assertFalse(raised.exception.submitted)
                self.assertEqual(completions.calls, [])

    def test_retry_counts_are_rejected_even_with_injected_sdk(self):
        for retries in (1, -1, True, "0", 0.0, None):
            with self.subTest(retries=retries):
                cfg = config()
                cfg["provider"]["max_retries"] = retries
                client, completions = fake_client(cfg)
                with self.assertRaises(RuntimeError):
                    client._real_complete("prompt", "medium")
                self.assertEqual(completions.calls, [])
        client, completions = fake_client()
        client._client.max_retries = 1
        with self.assertRaises(RuntimeError):
            client._real_complete("prompt", "medium")
        self.assertEqual(completions.calls, [])

    def test_constructor_transport_does_not_resubmit_redirected_posts(self):
        original_init = httpx.Client.__init__
        for status in (307, 308):
            with self.subTest(status=status):
                calls = []

                def handler(request):
                    calls.append(request.method)
                    if len(calls) == 1:
                        return httpx.Response(status, headers={"location": "https://offline.invalid/redirected"})
                    return httpx.Response(400, json={"error": {"message": "redirected request"}})

                def offline_init(transport_self, *args, **kwargs):
                    # Preserve the actual SDK default client's redirect options;
                    # replace only network IO with an in-memory transport.
                    kwargs["transport"] = httpx.MockTransport(handler)
                    original_init(transport_self, *args, **kwargs)

                with tempfile.TemporaryDirectory() as directory:
                    with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key"}, clear=True):
                        with patch.object(httpx.Client, "__init__", offline_init):
                            client = InklingClient(config(), Path(directory), live_authorized=True)
                    try:
                        with self.assertRaises(RuntimeError) as raised:
                            client._real_complete("synthetic", "medium")
                        self.assertEqual(calls, ["POST"])
                        self.assertFalse(client._client._client.follow_redirects)
                        self.assertEqual(raised.exception.status_code, status)
                        self.assertTrue(raised.exception.submitted)
                    finally:
                        client._client.close()

    def test_effective_sdk_transport_redirects_are_checked_before_create(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(400, json={"error": {"message": "synthetic"}})

        with openai.OpenAI(api_key="synthetic-key", base_url="https://offline.invalid/v1",
                           max_retries=0, http_client=openai.DefaultHttpxClient(
                               follow_redirects=False, transport=httpx.MockTransport(handler))) as sdk:
            client, _ = fake_client()
            client._client = sdk
            sdk._client.follow_redirects = True
            with self.assertRaises(RuntimeError) as raised:
                client._real_complete("synthetic", "medium")
            self.assertEqual(calls, [])
            self.assertEqual(raised.exception.code, "redirects_forbidden")
            self.assertFalse(raised.exception.submitted)

    def test_invalid_request_values_are_refused_before_create(self):
        invalid = [
            {"max_tokens": None}, {"max_tokens": 0}, {"max_tokens": -1},
            {"max_tokens": True}, {"max_tokens": 1.5}, {"max_tokens": float("nan")},
            {"seed": True}, {"seed": 1.5}, {"effort": ""}, {"effort": float("nan")},
            {"effort": True}, {"effort": "arbitrary"}, {"messages": []},
            {"messages": [{"role": "user", "content": None}]},
        ]
        for values in invalid:
            with self.subTest(values=values):
                client, completions = fake_client()
                if values == {"max_tokens": None}:
                    client.cfg["provider"]["max_completion_tokens"] = None
                kwargs = {"max_tokens": 1000, "effort": "medium", **values}
                with self.assertRaises(RuntimeError):
                    client._real_complete("prompt", **kwargs)
                self.assertEqual(completions.calls, [])

    def test_effort_parameter_cannot_name_protected_request_field(self):
        for mode in ("param", "extra_body", "openrouter_reasoning"):
            cfg = config()
            cfg["effort"] = {"mode": mode, "param_name": "max_tokens"}
            client, completions = fake_client(cfg)
            with self.assertRaises(RuntimeError):
                client._real_complete("prompt", "medium")
            self.assertEqual(completions.calls, [])

    def test_serialized_request_has_one_completion_and_explicit_controls(self):
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            payload = {
                "id": "gen-synthetic", "object": "chat.completion.chunk", "created": 1,
                "model": "synthetic/model", "provider": "Synthetic Provider",
                "choices": [{"index": 0, "delta": {"content": "Final answer: A"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 100, "total_tokens": 110, "cost": 0.01},
            }
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content="data: " + json.dumps(payload) + "\n\ndata: [DONE]\n\n")

        client, _ = fake_client()
        with openai.OpenAI(api_key="synthetic-key", base_url="https://offline.invalid/v1",
                           max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))) as sdk:
            client._client = sdk
            client._real_complete("synthetic prompt", "medium", max_tokens=1000, seed=7)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["n"], 1)
        self.assertEqual(requests[0]["max_tokens"], 1000)
        self.assertEqual(requests[0]["reasoning"], {"effort": "medium", "exclude": False})
        self.assertEqual(requests[0]["seed"], 7)

    def test_http_errors_are_sanitized_and_never_retried(self):
        for status in (400, 401, 402, 403, 429, 503):
            with self.subTest(status=status):
                calls = []

                def handler(request):
                    calls.append(request)
                    return httpx.Response(status, json={"error": {"message": "reasoning PRIVATE_PROMPT API_SECRET"}})

                client, _ = fake_client()
                with openai.OpenAI(api_key="synthetic-key", base_url="https://offline.invalid/v1",
                                   max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))) as sdk:
                    client._client = sdk
                    with self.assertRaises(RuntimeError) as raised:
                        client._real_complete("PRIVATE_PROMPT", "medium")
                error = raised.exception
                self.assertEqual(type(error).__name__, "RequestFailure")
                self.assertTrue(error.submitted)
                self.assertEqual(error.status_code, status)
                self.assertEqual(len(calls), 1)
                self.assertNotIn("PRIVATE_PROMPT", str(error))
                self.assertNotIn("API_SECRET", str(error))

    def test_partial_accounting_survives_errors_and_interrupts(self):
        for failure in (RuntimeError("PRIVATE_PROMPT"), KeyboardInterrupt(), SystemExit("API_SECRET")):
            with self.subTest(failure=type(failure).__name__):
                client, completions = fake_client(values=[chunk(), failure])
                with self.assertRaises(RuntimeError) as raised:
                    client._real_complete("prompt", "medium")
                error = raised.exception
                self.assertEqual(type(error).__name__, "RequestFailure")
                self.assertTrue(error.submitted)
                self.assertEqual(error.metadata["generation_id"], "gen-synthetic")
                self.assertEqual(error.metadata["provider"], "Synthetic Provider")
                self.assertEqual(error.metadata["finish_reason"], "stop")
                self.assertEqual(error.metadata["completion_tokens"], 100)
                self.assertEqual(error.metadata["prompt_tokens"], 10)
                self.assertEqual(error.metadata["reported_cost_usd"], 0.01)
                self.assertEqual(error.interrupted, isinstance(failure, (KeyboardInterrupt, SystemExit)))
                self.assertNotIn("PRIVATE_PROMPT", str(error))
                self.assertNotIn("API_SECRET", str(error))
                self.assertEqual(len(completions.calls), 1)

    def test_stream_error_chunk_preserves_its_accounting(self):
        client, _ = fake_client(values=[chunk(error={"message": "PRIVATE_PROMPT"})])
        with self.assertRaises(RuntimeError) as raised:
            client._real_complete("prompt", "medium")
        self.assertEqual(raised.exception.metadata["generation_id"], "gen-synthetic")
        self.assertEqual(raised.exception.metadata["completion_tokens"], 100)
        self.assertEqual(raised.exception.metadata["finish_reason"], "stop")
        self.assertNotIn("PRIVATE_PROMPT", str(raised.exception))

    def test_sdk_sse_error_keeps_known_identity_and_marks_discarded_usage_unknown(self):
        calls = []
        first = {
            "id": "gen-synthetic", "object": "chat.completion.chunk", "created": 1,
            "model": "synthetic/model", "provider": "Synthetic Provider",
            "choices": [{"index": 0, "delta": {"content": "partial"}, "finish_reason": None}],
        }
        error_chunk = {
            **first,
            "error": {"message": "PRIVATE_PROMPT", "code": 500},
            "usage": {"prompt_tokens": 10, "completion_tokens": 100, "total_tokens": 110, "cost": 0.01},
        }

        def handler(request):
            calls.append(request)
            body = "".join("data: " + json.dumps(value) + "\n\n" for value in (first, error_chunk))
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

        with openai.OpenAI(api_key="synthetic-key", base_url="https://offline.invalid/v1",
                           max_retries=0, http_client=openai.DefaultHttpxClient(
                               follow_redirects=False, transport=httpx.MockTransport(handler))) as sdk:
            client, _ = fake_client()
            client._client = sdk
            with self.assertRaises(RuntimeError) as raised:
                client._real_complete("synthetic", "medium")
        error = raised.exception
        self.assertEqual(len(calls), 1)
        self.assertTrue(error.submitted)
        self.assertEqual(error.metadata["generation_id"], "gen-synthetic")
        self.assertEqual(error.metadata["provider"], "Synthetic Provider")
        self.assertEqual(error.metadata["finish_reason"], "")
        self.assertIsNone(error.metadata["prompt_tokens"])
        self.assertIsNone(error.metadata["completion_tokens"])
        self.assertIsNone(error.metadata["reported_cost_usd"])
        self.assertIsInstance(error.__context__, openai.APIError)
        self.assertNotIn("usage", error.__context__.body)
        self.assertNotIn("id", error.__context__.body)
        self.assertNotIn("PRIVATE_PROMPT", str(error))

    def test_invalid_usage_keeps_other_safe_fields_and_never_leaks_payload(self):
        for name, value in (("prompt_tokens", True), ("completion_tokens", -1),
                            ("completion_tokens", 10.5), ("cost", float("nan")),
                            ("cost", float("inf")), ("cost", "PRIVATE_PROMPT")):
            with self.subTest(name=name, value=value):
                usage = {"prompt_tokens": 10, "completion_tokens": 100, "cost": 0.01}
                usage[name] = value
                client, _ = fake_client(values=[chunk(usage=usage)])
                with self.assertRaises(RuntimeError) as raised:
                    client._real_complete("prompt", "medium")
                self.assertEqual(raised.exception.code, "invalid_usage_accounting")
                self.assertEqual(raised.exception.metadata["generation_id"], "gen-synthetic")
                self.assertNotIn("PRIVATE_PROMPT", json.dumps(raised.exception.metadata, allow_nan=False))

    def test_successful_stream_close_interrupt_preserves_metadata(self):
        client, completions = fake_client()

        class InterruptOnClose:
            def __iter__(self):
                return iter([chunk()])

            def close(self):
                raise KeyboardInterrupt()

        completions.create = lambda **kwargs: InterruptOnClose()
        with self.assertRaises(RuntimeError) as raised:
            client._real_complete("prompt", "medium")
        self.assertTrue(raised.exception.interrupted)
        self.assertEqual(raised.exception.metadata["reported_cost_usd"], 0.01)

    def test_unstructured_ids_and_finish_text_are_not_failure_metadata(self):
        for changes, key in (({"id": "PRIVATE_PROMPT"}, "generation_id"),
                             ({"id": "gen-PRIVATE PROMPT"}, "generation_id"),
                             ({"choices": [NS(index=0, finish_reason="PRIVATE_PROMPT")]}, "finish_reason")):
            with self.subTest(changes=changes):
                client, _ = fake_client(values=[chunk(**changes)])
                with self.assertRaises(RuntimeError) as raised:
                    client._real_complete("prompt", "medium")
                self.assertEqual(raised.exception.metadata[key], "")
                self.assertEqual(raised.exception.metadata["reported_cost_usd"], 0.01)
                self.assertNotIn("PRIVATE", json.dumps(raised.exception.metadata))

    def test_cache_write_failure_preserves_completed_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            client, _ = fake_client()
            client.cache_dir = Path(directory)
            client._cache_put = lambda *args: (_ for _ in ()).throw(OSError("PRIVATE_PROMPT"))
            with self.assertRaises(RuntimeError) as raised:
                client.complete("prompt", "medium", "a")
            self.assertEqual(raised.exception.code, "cache_write_failed")
            self.assertEqual(raised.exception.metadata["generation_id"], "gen-synthetic")
            self.assertEqual(raised.exception.metadata["reported_cost_usd"], 0.01)
            self.assertNotIn("PRIVATE_PROMPT", str(raised.exception))

    def test_stream_rejects_multiple_choices_and_nonzero_indices(self):
        for choices in ([NS(index=1, delta=NS(content="ignored"), finish_reason="stop")],
                        [NS(index=0), NS(index=1)]):
            with self.subTest(choices=choices):
                client, _ = fake_client(values=[chunk(choices=choices)])
                with self.assertRaises(RuntimeError):
                    client._real_complete("prompt", "medium")

    def test_stream_rejects_changing_generation_or_provider(self):
        for second in (chunk(id="gen-other"), chunk(provider="Other Provider"),
                       chunk(openrouter_metadata={"provider": "Other Provider"})):
            with self.subTest(second=second):
                client, _ = fake_client(values=[chunk(), second])
                with self.assertRaises(RuntimeError) as raised:
                    client._real_complete("prompt", "medium")
                self.assertEqual(raised.exception.metadata["generation_id"], "gen-synthetic")
                self.assertEqual(raised.exception.metadata["provider"], "Synthetic Provider")

    def test_conflicting_identity_never_overwrites_already_associated_usage(self):
        for identity in ({"id": "gen-other"}, {"provider": "Other Provider"},
                         {"openrouter_metadata": {"provider": "Other Provider"}},
                         {"id": "invalid ID"}, {"provider": "invalid\nprovider"}):
            with self.subTest(identity=identity):
                first = chunk(usage=NS(prompt_tokens=10, completion_tokens=100, cost=0.01),
                              choices=[NS(index=0, delta=NS(content="partial"), finish_reason=None)])
                second = chunk(**identity, usage=NS(prompt_tokens=20, completion_tokens=200, cost=0.02))
                client, _ = fake_client(values=[first, second])
                with self.assertRaises(RuntimeError) as raised:
                    client._real_complete("synthetic", "medium")
                metadata = raised.exception.metadata
                self.assertEqual(metadata["generation_id"], "gen-synthetic")
                self.assertEqual(metadata["provider"], "Synthetic Provider")
                self.assertEqual(metadata["prompt_tokens"], 10)
                self.assertEqual(metadata["completion_tokens"], 100)
                self.assertEqual(metadata["reported_cost_usd"], 0.01)
                self.assertEqual(metadata["finish_reason"], "")

    def test_cache_identity_covers_item_run_endpoint_and_effective_cap(self):
        client, _ = fake_client()
        base = client._cache_key("prompt", "medium", item_id="a")
        self.assertNotEqual(base, client._cache_key("prompt", "medium", item_id="b"))
        client.cfg["_pilot_run_id"] = "other-run"
        self.assertNotEqual(base, client._cache_key("prompt", "medium", item_id="a"))
        client.cfg = config()
        client.cfg["provider"]["default_base_url"] = "https://other.invalid/v1"
        self.assertNotEqual(base, client._cache_key("prompt", "medium", item_id="a"))
        client.cfg = config()
        client.cfg["provider"]["max_completion_tokens"] = 2000
        self.assertNotEqual(base, client._cache_key("prompt", "medium", item_id="a"))
        client.cfg = config()
        client.cfg["effort"]["mode"] = "system"
        self.assertNotEqual(base, client._cache_key("prompt", "medium", item_id="a"))

    def test_cache_identity_excludes_endpoint_credentials(self):
        client, _ = fake_client()
        client._client.base_url = "https://user:PRIVATE_KEY@offline.invalid/v1?api_key=SECRET"
        first = client._cache_key("prompt", "medium", item_id="a")
        client._client.base_url = "https://other:OTHER_KEY@offline.invalid/v1?api_key=OTHER_SECRET"
        self.assertEqual(first, client._cache_key("prompt", "medium", item_id="a"))
        self.assertEqual(client._safe_endpoint(client._client.base_url), "https://offline.invalid/v1")

    def test_complete_uses_item_identity_for_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = config()
            client = InklingClient(cfg, Path(directory), mock=True)
            client._mock_complete = lambda *args: {
                "text": "synthetic", "completion_tokens": 1, "prompt_tokens": 1, "latency_s": 0,
            }
            first = client.complete("prompt", "medium", "a")
            second = client.complete("prompt", "medium", "b")
            again = client.complete("prompt", "medium", "a")
            self.assertFalse(first.cached)
            self.assertFalse(second.cached)
            self.assertTrue(again.cached)

    def test_cached_completion_never_submits_and_uses_scoped_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            client, completions = fake_client()
            client.cache_dir = Path(directory)
            self.assertIsNone(client.cached_completion("prompt", "medium", "a"))
            self.assertEqual(completions.calls, [])
            client.complete("prompt", "medium", "a")
            cached = client.cached_completion("prompt", "medium", "a")
            self.assertTrue(cached.cached)
            self.assertEqual(cached.generation_id, "gen-synthetic")
            self.assertIsNone(client.cached_completion("prompt", "medium", "b"))
            client.cfg["_pilot_run_id"] = "other-run"
            self.assertIsNone(client.cached_completion("prompt", "medium", "a"))
            self.assertEqual(len(completions.calls), 1)


if __name__ == "__main__":
    unittest.main()
