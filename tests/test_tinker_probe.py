from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
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
                ("thinkingmachines/Inkling", 4096),
                ("thinkingmachines/Inkling", 16384),
                ("thinkingmachines/Inkling", 32768),
                ("thinkingmachines/Inkling", 65536),
                ("openai/gpt-oss-120b", 4096),
                ("openai/gpt-oss-120b", 16384),
                ("openai/gpt-oss-120b", 32768),
                ("openai/gpt-oss-120b", 65536),
            },
        )
        self.assertEqual(len(cap_specs), 8)

    def test_65536_never_changes_the_configured_target_model_or_route(self) -> None:
        plan = tinker_probe.build_probe_plan()
        cap_specs = [spec for spec in plan if spec.kind == "cap_semantics"]

        for model_label, target_model in (
            ("inkling", "thinkingmachines/Inkling"),
            ("gpt_oss_120b", "openai/gpt-oss-120b"),
        ):
            panel_specs = [
                spec for spec in cap_specs if spec.name.startswith(f"cap_semantics_{model_label}_")
            ]
            self.assertEqual(
                {spec.max_tokens for spec in panel_specs},
                {4096, 16384, 32768, 65536},
            )
            self.assertEqual({spec.model for spec in panel_specs}, {target_model})

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

    def test_default_cap_has_a_finite_context_derived_cost_bound(self) -> None:
        diagnostic = next(
            spec for spec in tinker_probe.build_probe_plan() if spec.kind == "default_cap"
        )

        self.assertEqual(
            diagnostic.cost_projection_output_token_bound,
            32768,
        )
        # Full 32K context prefill at $0.18/M + full 32K sample at $0.45/M.
        self.assertAlmostEqual(
            tinker_probe.projected_cost_usd(diagnostic),
            32768 * (0.18 + 0.45) / 1_000_000,
        )

    def test_projection_bounds_full_prefill_and_cached_prefill_for_all_samples(self) -> None:
        samples = next(
            spec for spec in tinker_probe.build_probe_plan()
            if spec.name == "samples_independence_n8"
        )

        expected = (
            32768 * 0.18
            + 32768 * 7 * 0.036
            + 256 * 8 * 0.45
        ) / 1_000_000
        self.assertAlmostEqual(tinker_probe.projected_cost_usd(samples), expected)


class TinkerProbeSafetyTests(unittest.TestCase):
    def test_probe_environment_is_python_and_hash_locked(self) -> None:
        lock = Path("scripts/tinker_probe_requirements.lock").read_text()

        self.assertIn("--python-version 3.12.8", lock.splitlines()[1])
        self.assertIn("tinker==0.25.0", lock)
        self.assertIn("--hash=sha256:", lock)

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

    def test_locked_environment_manifest_verifies_every_distribution(self) -> None:
        manifest = tinker_probe.verify_locked_environment()

        self.assertEqual(manifest["python_version"], "3.12.8")
        self.assertEqual(len(manifest["distributions"]), 42)
        self.assertIn(
            {"name": "tinker", "version": "0.25.0"},
            manifest["distributions"],
        )

    def test_locked_environment_version_mutation_fails_closed(self) -> None:
        installed = dict(tinker_probe.locked_distribution_versions())
        installed["tinker"] = "0.25.1"

        with self.assertRaisesRegex(RuntimeError, "tinker==0.25.0"):
            tinker_probe.verify_locked_environment(installed_versions=installed)

    def test_locked_environment_rejects_unlocked_distributions(self) -> None:
        installed = dict(tinker_probe.locked_distribution_versions())
        installed["unlocked-package"] = "1.0"

        with self.assertRaisesRegex(RuntimeError, "unexpected unlocked-package==1.0"):
            tinker_probe.verify_locked_environment(installed_versions=installed)

    def test_pinned_sdk_internal_429_path_resubmits_even_with_outer_retries_disabled(self) -> None:
        from tinker.lib.public_interfaces import sampling_client as upstream

        submissions = 0

        class StopAfterSecondSubmission(RuntimeError):
            pass

        class FakeHolder:
            _sample_backoff_until = None

            @staticmethod
            def estimate_bytes_count_in_model_input(_prompt: object) -> int:
                return 1

            @staticmethod
            @contextlib.asynccontextmanager
            async def sample_dispatch_rate_limit(_estimated_bytes: int):
                yield

            @staticmethod
            async def execute_with_retries(function, *args):
                return await function(*args)

        client = upstream.SamplingClient.__new__(upstream.SamplingClient)
        client.holder = FakeHolder()
        client._request_id_counter = 0

        async def fake_send(*_args):
            nonlocal submissions
            submissions += 1
            if submissions == 1:
                return None  # exact value used by upstream for HTTP 429/backpressure
            raise StopAfterSecondSubmission

        client._send_asample_request = fake_send

        async def run_challenge() -> None:
            with mock.patch.object(upstream.asyncio, "sleep", new=mock.AsyncMock()):
                with self.assertRaises(StopAfterSecondSubmission):
                    await client._sample_async_impl(object(), 1, object(), False)

        asyncio.run(run_challenge())
        self.assertEqual(submissions, 2)

    def test_pinned_sdk_capability_reports_live_unsupported(self) -> None:
        capability = tinker_probe.inspect_pinned_sdk_one_attempt_capability()

        self.assertFalse(capability["supported"])
        self.assertEqual(capability["sdk_version"], "0.25.0")
        self.assertIn("SamplingClient._sample_async_impl has a 429 resubmission loop", capability["reasons"])
        self.assertIn("InternalClientHolder.execute_with_retries retries submissions", capability["reasons"])
        self.assertEqual(
            capability["observed_signatures"],
            {"sampling_429_loop": True, "holder_retry_wrapper": True},
        )
        self.assertEqual(
            capability["upstream_source_sha256"],
            {
                "SamplingClient._sample_async_impl": (
                    "60b3ed71c9f541536c08ed2311ef53af680f809c61f5ec8d0057249bcb93e16d"
                ),
                "InternalClientHolder.execute_with_retries": (
                    "b0c51012f81289957279d4d166767aaba485557a9825d075761fa039e0d22a03"
                ),
            },
        )

    def test_live_preflights_sink_records_manifest_then_blocks_before_client(self) -> None:
        constructed = False

        def forbidden_factory(_api_key: str):
            nonlocal constructed
            constructed = True
            raise AssertionError("client construction must be unreachable")

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            with self.assertRaisesRegex(SystemExit, "zero-resubmission"):
                tinker_probe.main(
                    ["--live", "--probe", "caps", "--report", str(report)],
                    environ={"TINKER_API_KEY": "secret"},
                    adapter_factory=forbidden_factory,
                    stdout=io.StringIO(),
                )
            records = [json.loads(line) for line in report.read_text().splitlines()]

        self.assertFalse(constructed)
        self.assertEqual(
            [record["record_type"] for record in records],
            ["sink_preflight", "environment_verified", "live_blocked"],
        )
        self.assertEqual(len(records[1]["environment_manifest"]["distributions"]), 42)

    def test_default_cap_live_still_requires_bounded_explicit_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            with self.assertRaisesRegex(SystemExit, "authorize-default-cap-cost-usd"):
                tinker_probe.main(
                    ["--live", "--probe", "default-cap", "--report", str(report)],
                    environ={"TINKER_API_KEY": "secret"},
                    adapter_factory=lambda _key: self.fail("must not construct client"),
                    stdout=io.StringIO(),
                )

        projection = 32768 * (0.18 + 0.45) / 1_000_000
        self.assertLess(projection, 0.03)

    def test_invalid_or_malformed_sink_yields_zero_client_construction(self) -> None:
        for malformed in (False, True):
            with self.subTest(malformed=malformed), tempfile.TemporaryDirectory() as directory:
                report = Path(directory) / "report.jsonl"
                if malformed:
                    report.write_text("not-json\n")
                else:
                    report.mkdir()
                constructed = False

                def forbidden_factory(_api_key: str):
                    nonlocal constructed
                    constructed = True
                    raise AssertionError

                with self.assertRaises((OSError, ValueError)):
                    tinker_probe.main(
                        ["--live", "--probe", "caps", "--report", str(report)],
                        environ={"TINKER_API_KEY": "secret"},
                        adapter_factory=forbidden_factory,
                        stdout=io.StringIO(),
                    )
                self.assertFalse(constructed)

    def test_unwritable_sink_yields_zero_client_construction(self) -> None:
        constructed = False

        def forbidden_factory(_api_key: str):
            nonlocal constructed
            constructed = True
            raise AssertionError

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            report.write_text("{}\n")
            report.chmod(0o400)
            try:
                with self.assertRaises(PermissionError):
                    tinker_probe.main(
                        ["--live", "--probe", "caps", "--report", str(report)],
                        environ={"TINKER_API_KEY": "secret"},
                        adapter_factory=forbidden_factory,
                        stdout=io.StringIO(),
                    )
            finally:
                report.chmod(0o600)

        self.assertFalse(constructed)

    def test_attempt_started_is_fsynced_before_each_possible_billed_call(self) -> None:
        events: list[str] = []
        real_fsync = os.fsync

        class InspectingAdapter(RecordingAdapter):
            def __init__(self, report: Path):
                super().__init__([])
                self.report = report

            def sample(self, spec: tinker_probe.ProbeSpec) -> tinker_probe.CallResult:
                latest = json.loads(self.report.read_text().splitlines()[-1])
                self.assert_attempt(latest, spec)
                events.append("call")
                return super().sample(spec)

            @staticmethod
            def assert_attempt(record: dict, spec: tinker_probe.ProbeSpec) -> None:
                if record["record_type"] != "attempt_started" or record["probe_name"] != spec.name:
                    raise AssertionError("write-ahead record was not durable before call")

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            writer = tinker_probe.AppendOnlyJSONL(report)
            writer.preflight()
            adapter = InspectingAdapter(report)

            def recording_fsync(fd: int) -> None:
                real_fsync(fd)
                events.append("fsync")

            with mock.patch.object(tinker_probe.os, "fsync", side_effect=recording_fsync):
                result = tinker_probe._execute_live_plan(
                    [next(spec for spec in tinker_probe.build_probe_plan() if spec.kind == "stop_reason")],
                    adapter,
                    writer,
                    stdout=io.StringIO(),
                    default_cap_authorization_usd=None,
                )

        self.assertEqual(result, 0)
        self.assertEqual(events[:2], ["fsync", "call"])

    def test_structured_error_preserves_known_billing_join_identifiers(self) -> None:
        calls = 0

        class FailingAdapter:
            def sample(self, _spec: tinker_probe.ProbeSpec) -> tinker_probe.CallResult:
                nonlocal calls
                calls += 1
                raise tinker_probe.ProbeCallError(
                    "synthetic failure",
                    sampling_session_id="sampling-session-1",
                    request_id="request-2",
                    billing_join_id="billing-3",
                )

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            writer = tinker_probe.AppendOnlyJSONL(report)
            writer.preflight()
            result = tinker_probe._execute_live_plan(
                [next(spec for spec in tinker_probe.build_probe_plan() if spec.kind == "stop_reason")],
                FailingAdapter(),
                writer,
                stdout=io.StringIO(),
                default_cap_authorization_usd=None,
            )
            error = [
                json.loads(line) for line in report.read_text().splitlines()
                if json.loads(line)["record_type"] == "result"
            ][0]

        self.assertEqual(result, 1)
        self.assertEqual(error["sampling_session_id"], "sampling-session-1")
        self.assertEqual(error["request_id"], "request-2")
        self.assertEqual(error["billing_join_id"], "billing-3")
        self.assertEqual(calls, 1)

    def test_cost_projection_precedes_every_synthetic_call(self) -> None:
        events: list[tuple[str, str]] = []
        adapter = RecordingAdapter(events)
        stdout = EventStream(events)
        cap_plan = [spec for spec in tinker_probe.build_probe_plan() if spec.kind == "cap_semantics"]

        with tempfile.TemporaryDirectory() as directory:
            writer = tinker_probe.AppendOnlyJSONL(Path(directory) / "report.jsonl")
            writer.preflight()
            result = tinker_probe._execute_live_plan(
                cap_plan,
                adapter,
                writer,
                stdout=stdout,
                default_cap_authorization_usd=None,
            )

        self.assertEqual(result, 0)
        self.assertEqual(len(events), 16)
        for index in range(0, len(events), 2):
            self.assertEqual(events[index][0], "projection")
            self.assertEqual(events[index + 1][0], "call")
            self.assertEqual(events[index][1], events[index + 1][1])

    def test_unsupported_caps_are_reported_without_substitution_and_matrix_continues(self) -> None:
        calls: list[tinker_probe.ProbeSpec] = []

        class CapRejectingAdapter(RecordingAdapter):
            def sample(self, spec: tinker_probe.ProbeSpec) -> tinker_probe.CallResult:
                calls.append(spec)
                if spec.max_tokens == 65536:
                    raise RuntimeError("requested max_tokens is unsupported")
                return super().sample(spec)

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.jsonl"
            writer = tinker_probe.AppendOnlyJSONL(report)
            writer.preflight()
            stdout = io.StringIO()
            result = tinker_probe._execute_live_plan(
                [spec for spec in tinker_probe.build_probe_plan() if spec.kind == "cap_semantics"],
                CapRejectingAdapter([]),
                writer,
                stdout=stdout,
                default_cap_authorization_usd=None,
            )
            records = [
                json.loads(line) for line in report.read_text().splitlines()
                if json.loads(line).get("record_type") == "result"
            ]

        self.assertEqual(result, 1)
        self.assertEqual(len(calls), 8)
        self.assertEqual(len(records), 8)
        rejected = [record for record in records if record["requested_cap"] == 65536]
        self.assertEqual(
            {record["model"] for record in rejected},
            {"thinkingmachines/Inkling", "openai/gpt-oss-120b"},
        )
        self.assertTrue(all(record["status"] == "error" for record in rejected))
        self.assertNotIn(":peft:", json.dumps(records))


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
        self.assertEqual(row["num_samples"], 8)
        self.assertIn("sampling_session_id", row)
        self.assertEqual(row["usage"]["completion_tokens"], 7)
        self.assertIsNone(row["usage"]["billed_completion_tokens"])
        self.assertEqual(row["cost_projection_output_token_bound"], 256)
        self.assertIsNone(row["cost_authorization_usd"])
        self.assertEqual(
            row["environment_lock_sha256"],
            hashlib.sha256(
                Path("scripts/tinker_probe_requirements.lock").read_bytes()
            ).hexdigest(),
        )

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
