from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import tinker_probe


class RecordingAdapter:
    def __init__(self, events: list[tuple[str, str]]) -> None:
        self.events = events
        self.calls: list[tinker_probe.ProbeSpec] = []

    def sample(self, spec: tinker_probe.ProbeSpec) -> tinker_probe.CallResult:
        self.events.append(("call", spec.name))
        self.calls.append(spec)
        observations = tuple(
            tinker_probe.SampleObservation(
                text=f"response-{spec.name}-{index}",
                completion_tokens=(spec.max_tokens or 4096),
                stop_reason="length" if spec.max_tokens is not None else "stop",
            )
            for index in range(spec.num_samples)
        )
        return tinker_probe.CallResult(
            observations=observations,
            prompt_tokens=12,
            prompt_cache_hit_tokens=0,
            sdk_version="test-sdk",
        )


class EventStream(io.StringIO):
    def __init__(self, events: list[tuple[str, str]]) -> None:
        super().__init__()
        self.events = events

    def write(self, value: str) -> int:
        if value.startswith("COST PROJECTION"):
            probe_name = value.split("probe=", 1)[1].split()[0]
            self.events.append(("projection", probe_name))
        return super().write(value)


class TinkerProbePlanTests(unittest.TestCase):
    def test_cap_plan_covers_every_model_cap_pair(self) -> None:
        cap_specs = [spec for spec in tinker_probe.build_probe_plan() if spec.kind == "cap_semantics"]

        self.assertEqual(tinker_probe.CAP_PROBE_CAPS, (4096, 16384, 32768, 65536))
        self.assertEqual(
            {(spec.model, spec.max_tokens) for spec in cap_specs},
            {
                (model, cap)
                for model in tinker_probe.CAP_PROBE_MODELS
                for cap in tinker_probe.CAP_PROBE_CAPS
            },
        )

    def test_gpt_oss_20b_is_used_for_cheapest_smoke_probes(self) -> None:
        non_cap_specs = [spec for spec in tinker_probe.build_probe_plan() if spec.kind != "cap_semantics"]

        self.assertTrue(non_cap_specs)
        self.assertEqual({spec.model for spec in non_cap_specs}, {tinker_probe.SMOKE_MODEL})
        self.assertEqual(tinker_probe.SMOKE_MODEL, "openai/gpt-oss-20b")

    def test_only_isolated_exploratory_default_diagnostic_omits_max_tokens(self) -> None:
        plan = tinker_probe.build_probe_plan()
        omitted = [spec for spec in plan if "max_tokens" not in spec.request_params()]

        self.assertEqual(len(omitted), 1)
        self.assertEqual(omitted[0].kind, "default_cap")
        self.assertEqual(omitted[0].classification, "exploratory")
        self.assertTrue(omitted[0].deliberately_omits_max_tokens)
        for spec in plan:
            if spec is not omitted[0]:
                self.assertIn("max_tokens", spec.request_params())

    def test_sampling_params_and_client_num_samples_are_planned(self) -> None:
        plan = tinker_probe.build_probe_plan(
            seed=123,
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            stop=("END",),
        )
        ordinary = next(spec for spec in plan if spec.max_tokens is not None)
        params = ordinary.request_params()

        self.assertEqual(
            {key: params[key] for key in ("seed", "temperature", "top_p", "top_k", "stop")},
            {"seed": 123, "temperature": 0.7, "top_p": 0.8, "top_k": 20, "stop": ["END"]},
        )
        samples = next(spec for spec in plan if spec.kind == "sample_independence")
        self.assertEqual(samples.num_samples, 8)


class TinkerProbeSafetyTests(unittest.TestCase):
    def test_dry_run_is_default_and_makes_zero_client_calls(self) -> None:
        called = False

        def forbidden_factory(_api_key: str) -> RecordingAdapter:
            nonlocal called
            called = True
            raise AssertionError("dry-run must not construct a client")

        stdout = io.StringIO()
        result = tinker_probe.main([], environ={}, adapter_factory=forbidden_factory, stdout=stdout)

        self.assertEqual(result, 0)
        self.assertFalse(called)
        self.assertIn("DRY RUN", stdout.getvalue())

    def test_live_fails_loudly_without_tinker_api_key(self) -> None:
        with self.assertRaisesRegex(SystemExit, "TINKER_API_KEY"):
            tinker_probe.main(["--live"], environ={}, stdout=io.StringIO())

    def test_cost_projection_is_printed_before_every_client_call(self) -> None:
        events: list[tuple[str, str]] = []
        adapter = RecordingAdapter(events)
        stdout = EventStream(events)

        with tempfile.TemporaryDirectory() as directory:
            result = tinker_probe.main(
                ["--live", "--probe", "samples", "--report", str(Path(directory) / "report.jsonl")],
                environ={"TINKER_API_KEY": "secret"},
                adapter_factory=lambda _key: adapter,
                stdout=stdout,
            )

        self.assertEqual(result, 0)
        self.assertEqual([kind for kind, _ in events], ["projection", "call"])
        self.assertEqual(events[0][1], events[1][1])

    def test_sdk_adapter_disables_sdk_and_sampling_retries(self) -> None:
        captured: dict[str, object] = {}

        class FakeRetryConfig:
            def __init__(self, **kwargs: object) -> None:
                captured["retry_kwargs"] = kwargs

        class FakeTokenizer:
            def encode(self, _text: str) -> list[int]:
                return [1, 2, 3]

            def decode(self, tokens: list[int]) -> str:
                return "decoded:" + ",".join(str(token) for token in tokens)

        class FakeFuture:
            def result(self) -> object:
                sequence = SimpleNamespace(tokens=[4, 5], stop_reason="stop")
                return SimpleNamespace(sequences=[sequence], prompt_cache_hit_tokens=1)

        class FakeSamplingClient:
            def get_tokenizer(self) -> FakeTokenizer:
                return FakeTokenizer()

            def sample(self, **kwargs: object) -> FakeFuture:
                captured["sample_kwargs"] = kwargs
                return FakeFuture()

        class FakeServiceClient:
            def __init__(self, **kwargs: object) -> None:
                captured["service_kwargs"] = kwargs

            def create_sampling_client(self, **kwargs: object) -> FakeSamplingClient:
                captured["sampling_client_kwargs"] = kwargs
                return FakeSamplingClient()

        class FakeSamplingParams:
            def __init__(self, **kwargs: object) -> None:
                self.values = kwargs

        fake_sdk = SimpleNamespace(
            ServiceClient=FakeServiceClient,
            SamplingParams=FakeSamplingParams,
            ModelInput=SimpleNamespace(from_ints=lambda tokens: ("prompt", tokens)),
            __version__="0.test",
        )
        adapter = tinker_probe.TinkerSDKAdapter(
            "secret", sdk_module=fake_sdk, retry_config_cls=FakeRetryConfig
        )
        spec = next(spec for spec in tinker_probe.build_probe_plan() if spec.max_tokens is not None)

        result = adapter.sample(spec)

        self.assertEqual(captured["service_kwargs"], {"api_key": "secret", "max_retries": 0})
        self.assertEqual(captured["retry_kwargs"], {"enable_retry_logic": False})
        self.assertEqual(
            captured["sampling_client_kwargs"],
            {"base_model": spec.model, "retry_config": mock.ANY},
        )
        self.assertEqual(captured["sample_kwargs"]["num_samples"], spec.num_samples)
        self.assertEqual(result.observations[0].completion_tokens, 2)

    def test_sdk_adapter_actually_omits_max_tokens_for_default_diagnostic(self) -> None:
        captured: dict[str, object] = {}

        class FakeSamplingParams:
            def __init__(self, **kwargs: object) -> None:
                captured["params"] = kwargs

        sequence = SimpleNamespace(tokens=[1], stop_reason="stop")
        client = SimpleNamespace(
            get_tokenizer=lambda: SimpleNamespace(
                encode=lambda _text: [1], decode=lambda _tokens: "response"
            ),
            sample=lambda **_kwargs: SimpleNamespace(
                result=lambda: SimpleNamespace(
                    sequences=[sequence], prompt_cache_hit_tokens=0
                )
            ),
        )
        service = SimpleNamespace(create_sampling_client=lambda **_kwargs: client)
        fake_sdk = SimpleNamespace(
            ServiceClient=lambda **_kwargs: service,
            SamplingParams=FakeSamplingParams,
            ModelInput=SimpleNamespace(from_ints=lambda tokens: tokens),
            __version__="0.test",
        )
        adapter = tinker_probe.TinkerSDKAdapter(
            "secret",
            sdk_module=fake_sdk,
            retry_config_cls=lambda **_kwargs: object(),
        )
        diagnostic = next(
            spec for spec in tinker_probe.build_probe_plan() if spec.kind == "default_cap"
        )

        adapter.sample(diagnostic)

        self.assertNotIn("max_tokens", captured["params"])

    def test_failed_live_call_is_appended_once_and_not_retried(self) -> None:
        calls = 0

        class FailingAdapter:
            def sample(self, _spec: tinker_probe.ProbeSpec) -> tinker_probe.CallResult:
                nonlocal calls
                calls += 1
                raise RuntimeError("synthetic failure")

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            result = tinker_probe.main(
                ["--live", "--probe", "stop-reason", "--report", str(report)],
                environ={"TINKER_API_KEY": "secret"},
                adapter_factory=lambda _key: FailingAdapter(),
                stdout=io.StringIO(),
            )
            records = [json.loads(line) for line in report.read_text().splitlines()]

        self.assertEqual(result, 1)
        self.assertEqual(calls, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "error")


class TinkerProbeReportTests(unittest.TestCase):
    def test_jsonl_writer_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.jsonl"
            original = {"schema_version": 1, "record_id": "existing"}
            path.write_text(json.dumps(original) + "\n")
            writer = tinker_probe.AppendOnlyJSONL(path)

            writer.append({"schema_version": 1, "record_id": "new"})

            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(rows, [original, {"record_id": "new", "schema_version": 1}])

    def test_response_rows_have_required_schema_hashes_and_no_raw_text(self) -> None:
        spec = next(spec for spec in tinker_probe.build_probe_plan() if spec.kind == "sample_independence")
        call = tinker_probe.CallResult(
            observations=(
                tinker_probe.SampleObservation("sensitive response", 7, "stop"),
            ),
            prompt_tokens=3,
            prompt_cache_hit_tokens=0,
            sdk_version="test",
        )

        row = tinker_probe.make_response_records(
            spec,
            call,
            call_id="call-1",
            latency_seconds=1.25,
            timestamp="2026-08-08T00:00:00+00:00",
            projected_cost_usd=0.01,
        )[0]

        self.assertTrue(tinker_probe.REQUIRED_RECORD_FIELDS <= row.keys())
        self.assertEqual(
            row["response_text_sha256"],
            hashlib.sha256(b"sensitive response").hexdigest(),
        )
        serialized = json.dumps(row)
        self.assertNotIn("sensitive response", serialized)
        self.assertNotIn("response_text", row)
        self.assertEqual(row["usage"]["completion_tokens"], 7)
        self.assertIsNone(row["usage"]["billed_completion_tokens"])

    def test_num_samples_distinct_output_count_and_summary_generation(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "tinker_probe_records.jsonl"
        records = [json.loads(line) for line in fixture.read_text().splitlines()]

        summary = tinker_probe.summarize_records(records)
        rendered = tinker_probe.render_summary_table(summary)

        sample_row = next(row for row in summary if row["probe"] == "samples_independence_n8")
        self.assertEqual(sample_row["samples"], 8)
        self.assertEqual(sample_row["distinct_outputs"], 3)
        self.assertIn("distinct_outputs", rendered)
        self.assertIn("samples_independence_n8", rendered)


if __name__ == "__main__":
    unittest.main()
