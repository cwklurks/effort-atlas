from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from effort_atlas.confirmatory import (
    AttemptLedger,
    ReplicateDecisionRequired,
    analyze_confirmatory_events,
    build_schedule,
    export_schedule_artifacts,
)
from effort_atlas import ROOT, load_config


PANEL = {
    "name": "inkling_together", "model": "thinkingmachines/inkling",
    "requested_provider": "Together", "efforts": ["medium", "max"],
    "caps": [20000, 49152], "replicates": 1,
}
ITEMS = [{"id": f"math_{number:04d}", "domain": "math"} for number in range(1, 4)]


def accounted_success(job, **overrides):
    return {
        **job, "event_type": "success", "route_status": "expected",
        "accounting_status": "valid", "served_provider": job["requested_provider"],
        "request_id": f"request-{job['job_id']}",
        "generation_id": f"generation-{job['job_id']}",
        "receipt_generation_id": f"generation-{job['job_id']}",
        "receipt_provider": job["requested_provider"], "receipt_finish_reason": "stop",
        "receipt_cost_usd": 0.01, "native_completion_tokens": 20,
        "native_prompt_tokens": 10, "native_finish_reason": "stop",
        "completion_tokens": 20, "prompt_tokens": 10, "finish_reason": "stop",
        "correct": False, "extracted_answer_present": True, **overrides,
    }


class ConfirmatoryPreflightTests(unittest.TestCase):
    def test_schedule_is_deterministic_and_has_four_permuted_conditions_per_item(self):
        first = build_schedule(PANEL, ITEMS)
        second = build_schedule(PANEL, ITEMS)

        self.assertEqual(first, second)
        self.assertEqual(len(first["jobs"]), 12)
        self.assertEqual(len({job["job_id"] for job in first["jobs"]}), 12)
        self.assertEqual(
            first["sha256"],
            "03c28919f8c8b66e9ed0ca8bc251f257d5da9dc668fe9b6a7fd6c5c473f46bf3",
        )
        for item_id in {item["id"] for item in ITEMS}:
            conditions = [(job["effort"], job["cap"]) for job in first["jobs"] if job["item_id"] == item_id]
            self.assertEqual(set(conditions), {("medium", 20000), ("medium", 49152), ("max", 20000), ("max", 49152)})

    def test_schedule_refuses_to_choose_replicates_implicitly(self):
        with self.assertRaises(ReplicateDecisionRequired):
            build_schedule({**PANEL, "replicates": None}, ITEMS)

    def test_two_replicates_are_rejected_until_a_preregistration_amendment(self):
        with self.assertRaises(ReplicateDecisionRequired):
            build_schedule({**PANEL, "replicates": 2}, ITEMS)

    def test_config_fixes_one_replicate_and_panel_consistent(self):
        config = load_config(ROOT / "config_confirmatory.yaml")

        self.assertEqual(config["study"]["replicate_decision"], 1)
        self.assertTrue(all(panel["replicates"] == 1 for panel in config["panels"]))
        self.assertTrue(all(len(build_schedule(panel, ITEMS[:1])["jobs"]) == 4 for panel in config["panels"]))

    def test_ledger_is_append_only_and_redacts_request_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AttemptLedger(Path(directory) / "attempts.jsonl")
            base = build_schedule(PANEL, ITEMS)["jobs"][0]
            first = ledger.append({**base, "event_type": "error", "route_status": "unknown", "accounting_status": "unaccounted", "request_config": {"api_key": "do-not-write", "temperature": 1}})
            second = ledger.append({**base, "event_type": "manual_rerun", "route_status": "expected", "accounting_status": "unaccounted", "request_config": {"nested": {"Authorization": "nope"}}})

            rows = [json.loads(line) for line in ledger.path.read_text().splitlines()]
            self.assertEqual([row["attempt_ordinal"] for row in rows], [1, 2])
            self.assertEqual(first["request_config"]["api_key"], "[REDACTED]")
            self.assertEqual(second["request_config"]["nested"]["Authorization"], "[REDACTED]")
            self.assertNotIn("do-not-write", ledger.path.read_text())

    def test_ledger_protects_metadata_and_sanitizes_all_event_content(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AttemptLedger(Path(directory) / "attempts.jsonl")
            base = build_schedule(PANEL, ITEMS)["jobs"][0]
            with self.assertRaisesRegex(ValueError, "reserved"):
                ledger.append({**base, "event_type": "error", "ledger_version": 99})
            with self.assertRaisesRegex(ValueError, "reserved"):
                ledger.append({**base, "event_type": "error", "timestamp": "fake"})
            with self.assertRaisesRegex(ValueError, "reserved"):
                ledger.append({**base, "event_type": "error", "attempt_ordinal": 99})
            with self.assertRaisesRegex(ValueError, "allowlisted"):
                ledger.append({**base, "event_type": "error", "raw_response": "forbidden"})
            with self.assertRaisesRegex(ValueError, "allowlisted"):
                ledger.append({**base, "event_type": "error", "raw_header": "Bearer forbidden"})
            row = ledger.append({
                **base, "event_type": "error", "top_level_secret": "do-not-write",
                "request_config": {"X-Api-Key": "also-do-not-write", "completion_tokens": 4},
                "max_tokens": 99, "max_tokens_requested": 98,
                "prompt_tokens": 3, "completion_tokens": 4, "reasoning_tokens": 5,
            })

            self.assertEqual(row["ledger_version"], 1)
            self.assertEqual(row["attempt_ordinal"], 1)
            self.assertEqual(row["top_level_secret"], "[REDACTED]")
            self.assertEqual(row["request_config"]["X-Api-Key"], "[REDACTED]")
            self.assertEqual(row["request_config"]["completion_tokens"], 4)
            self.assertEqual(
                {key: row[key] for key in ("max_tokens", "max_tokens_requested", "prompt_tokens", "completion_tokens", "reasoning_tokens")},
                {"max_tokens": 99, "max_tokens_requested": 98, "prompt_tokens": 3, "completion_tokens": 4, "reasoning_tokens": 5},
            )

    def test_analyzer_keeps_cap_cells_separate_and_calculates_interaction(self):
        schedule = build_schedule(PANEL, ITEMS[:2])
        jobs = {(job["effort"], job["cap"], job["item_id"]): job for job in schedule["jobs"]}
        rows = []
        outcomes = {
            ("medium", 20000): [True, False], ("max", 20000): [False, False],
            ("medium", 49152): [True, False], ("max", 49152): [True, True],
        }
        for (effort, cap), corrects in outcomes.items():
            for item_number, correct in enumerate(corrects, start=1):
                job = jobs[(effort, cap, f"math_{item_number:04d}")]
                rows.append(accounted_success(job, generation_id=f"g-{effort}-{cap}-{item_number}", receipt_generation_id=f"g-{effort}-{cap}-{item_number}", correct=correct))
        rows.append({"event_type": "unaccounted"})
        report = analyze_confirmatory_events(rows, schedule)

        self.assertEqual(len(report["cells"]), 4)
        self.assertEqual({cell["cap"] for cell in report["cells"]}, {20000, 49152})
        self.assertEqual(report["interactions"][0]["interaction"], 1.0)
        self.assertEqual(report["excluded_events"], {"unaccounted": 1})
        self.assertEqual(len(report["selection_audit"]["accepted_job_ids"]), 8)

    def test_analyzer_requires_schedule_identity_and_audits_unscheduled_rows(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        job = schedule["jobs"][0]
        valid = accounted_success(job, generation_id="g", receipt_generation_id="g", correct=True)
        stray = {**valid, "job_id": "not-in-schedule"}
        mismatched = {**valid, "schedule_ordinal": 999}

        report = analyze_confirmatory_events([valid, stray, mismatched], schedule)

        self.assertEqual(len(report["cells"]), 1)
        self.assertEqual(
            [item["reason"] for item in report["selection_audit"]["excluded"]],
            ["job_id_not_in_schedule", "schedule_identity_mismatch"],
        )

    def test_accuracy_uses_grader_for_length_stops_and_bounds_only_unanswered(self):
        schedule = build_schedule(PANEL, ITEMS[:3])
        target_jobs = [job for job in schedule["jobs"] if job["effort"] == "medium" and job["cap"] == 20000]
        rows = [
            accounted_success(target_jobs[0], generation_id="g-0", receipt_generation_id="g-0", correct=True, extracted_answer_present=True, finish_reason="length", native_finish_reason="length", receipt_finish_reason="length"),
            accounted_success(target_jobs[1], generation_id="g-1", receipt_generation_id="g-1", correct=False, extracted_answer_present=False, finish_reason="length", native_finish_reason="length", receipt_finish_reason="length"),
            accounted_success(target_jobs[2], generation_id="g-2", receipt_generation_id="g-2", correct=False, extracted_answer_present=True, finish_reason="length", native_finish_reason="length", receipt_finish_reason="length"),
        ]

        report = analyze_confirmatory_events(rows, schedule)

        self.assertEqual(report["cells"][0]["accuracy"], 1 / 3)
        self.assertEqual(report["cells"][0]["length_stops"], 3)
        self.assertEqual(report["cells"][0]["unanswered_length_stops"], 1)
        self.assertEqual(report["cells"][0]["accuracy_bound_hi"], 2 / 3)

    def test_analyzer_requires_reconciled_receipt_expected_provider_and_boolean_grade(self):
        schedule = build_schedule(PANEL, ITEMS[:2])
        first, second, third, fourth, fifth = schedule["jobs"][:5]
        rows = [
            accounted_success(first, served_provider="Other"),
            accounted_success(second, receipt_generation_id="different"),
            accounted_success(third, correct=1),
            accounted_success(fourth, extracted_answer_present=None),
            accounted_success(fifth, correct=True, extracted_answer_present=False),
        ]
        report = analyze_confirmatory_events(rows, schedule)

        self.assertEqual(report["cells"], [])
        self.assertEqual(
            [row["reason"] for row in report["selection_audit"]["excluded"]],
            [
                "served_provider_mismatch", "receipt_linkage_invalid", "malformed_correct",
                "malformed_extracted_answer_presence", "grade_extraction_inconsistent",
            ],
        )

    def test_receipt_provider_must_match_and_native_finish_vocabulary_may_differ(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        valid, invalid = schedule["jobs"][:2]
        report = analyze_confirmatory_events([
            accounted_success(valid, finish_reason="stop", receipt_finish_reason="completed", native_finish_reason="provider_complete"),
            accounted_success(invalid, receipt_provider="Other"),
        ], schedule)

        self.assertEqual(len(report["cells"]), 1)
        self.assertEqual(report["selection_audit"]["excluded"][0]["reason"], "receipt_provider_mismatch")

    def test_ledger_preserves_allowlisted_audit_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AttemptLedger(Path(directory) / "attempts.jsonl")
            row = ledger.append({
                **build_schedule(PANEL, ITEMS[:1])["jobs"][0], "event_type": "cache",
                "request_started_at": "2026-07-22T00:00:00Z", "request_ended_at": "2026-07-22T00:00:01Z",
                "request_id": "request", "upstream_id": "upstream", "provider_response_id": "response",
                "endpoint_id": "endpoint", "receipt_created_at": "2026-07-22T00:00:01Z",
                "receipt_fetched_at": "2026-07-22T00:00:02Z", "cached": True, "replayed": False,
                "latency_s": 1.0, "extracted_answer_present": False, "billed_status": "not_billed",
                "manual_rerun_reason": "receipt-confirmed-unbilled",
            })
        self.assertEqual(row["request_id"], "request")
        self.assertEqual(row["latency_s"], 1.0)
        self.assertFalse(row["replayed"])

    def test_exporter_writes_deterministic_main_and_smoke_artifacts_without_prompt_content(self):
        config_path = ROOT / "config_confirmatory.yaml"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "artifacts"
            commit = "a" * 40
            manifest = export_schedule_artifacts(config_path, output, exporter_code_commit=commit)
            duplicate = Path(directory) / "duplicate"
            second = export_schedule_artifacts(config_path, duplicate, exporter_code_commit=commit)

            self.assertEqual(manifest, second)
            self.assertEqual(manifest["preregistration_commit"], "bc941bf118516cddafc671fcb9acc4607fd7ea33")
            self.assertEqual(
                manifest["preregistration_file_sha256"],
                hashlib.sha256((ROOT / "PREREGISTRATION.md").read_bytes()).hexdigest(),
            )
            self.assertEqual(
                manifest["amendment_file_sha256"],
                {
                    "PREREGISTRATION_AMENDMENT_2026-07-22.md": hashlib.sha256(
                        (ROOT / "PREREGISTRATION_AMENDMENT_2026-07-22.md").read_bytes()
                    ).hexdigest(),
                },
            )
            self.assertEqual(set(manifest["panels"]), {"inkling_together", "glm52_together"})
            for panel in manifest["panels"].values():
                schedule = json.loads((output / panel["main_file"]).read_text())
                self.assertEqual(len(schedule["jobs"]), 120)
                self.assertEqual(len({job["item_id"] for job in schedule["jobs"]}), 30)
                self.assertEqual(len({job["job_id"] for job in schedule["jobs"]}), 120)
                self.assertTrue(all(job["phase"] == "main" for job in schedule["jobs"]))
                self.assertNotIn("prompt", (output / panel["main_file"]).read_text())
                self.assertEqual(
                    panel["main_file_sha256"],
                    hashlib.sha256((output / panel["main_file"]).read_bytes()).hexdigest(),
                )
                self.assertEqual(
                    panel["smoke_file_sha256"],
                    hashlib.sha256((output / panel["smoke_file"]).read_bytes()).hexdigest(),
                )
                smoke = json.loads((output / panel["smoke_file"]).read_text())
                self.assertTrue(all(job["phase"] == "smoke" for job in smoke["jobs"]))
            with self.assertRaises(FileExistsError):
                export_schedule_artifacts(config_path, output, exporter_code_commit=commit)

    def test_exporter_validation_failure_leaves_no_partial_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "no-artifacts"
            with self.assertRaisesRegex(ValueError, "40-character"):
                export_schedule_artifacts(ROOT / "config_confirmatory.yaml", output, exporter_code_commit="short")
            self.assertFalse(output.exists())

    def test_analyzer_requires_request_id_and_strict_numeric_accounting_types(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        first, second, third, fourth = schedule["jobs"]
        report = analyze_confirmatory_events([
            accounted_success(first, request_id=""),
            accounted_success(second, native_completion_tokens=True),
            accounted_success(third, receipt_cost_usd=True),
            accounted_success(fourth, reasoning_tokens=True),
        ], schedule)

        self.assertEqual(report["cells"], [])
        self.assertEqual(
            [row["reason"] for row in report["selection_audit"]["excluded"]],
            ["request_id_invalid", "native_usage_invalid", "receipt_linkage_invalid", "reasoning_tokens_invalid"],
        )

    def test_analyzer_rejects_nonfinite_receipt_costs(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        report = analyze_confirmatory_events([
            accounted_success(schedule["jobs"][0], receipt_cost_usd=float("nan")),
            accounted_success(schedule["jobs"][1], receipt_cost_usd=float("inf")),
            accounted_success(schedule["jobs"][2], receipt_cost_usd=float("-inf")),
        ], schedule)

        self.assertEqual(report["cells"], [])
        self.assertEqual(
            [row["reason"] for row in report["selection_audit"]["excluded"]],
            ["receipt_linkage_invalid"] * 3,
        )

    def test_ledger_hash_chain_verifies_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AttemptLedger(Path(directory) / "attempts.jsonl")
            job = build_schedule(PANEL, ITEMS[:1])["jobs"][0]
            first = ledger.append({**job, "event_type": "error"})
            second = ledger.append({**job, "event_type": "unaccounted"})
            self.assertEqual(second["previous_event_sha256"], first["event_sha256"])
            self.assertTrue(ledger.verify())
            ledger.path.write_text(ledger.path.read_text().replace('"error"', '"edited"', 1))
            with self.assertRaisesRegex(ValueError, "hash chain"):
                ledger.verify()
            with self.assertRaisesRegex(ValueError, "hash chain"):
                ledger.append({**job, "event_type": "error"})

    def test_ledger_redacts_credential_like_values_defensively(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AttemptLedger(Path(directory) / "attempts.jsonl")
            row = ledger.append({
                **build_schedule(PANEL, ITEMS[:1])["jobs"][0], "event_type": "manual_rerun",
                "manual_rerun_reason": "token=not-safe",
                "request_config": {"note": "sk-or-not-safe", "cookie": "not-safe"},
            })
        self.assertEqual(row["manual_rerun_reason"], "[REDACTED]")
        self.assertEqual(row["request_config"]["note"], "[REDACTED]")
        self.assertEqual(row["request_config"]["cookie"], "[REDACTED]")

    def test_analyzer_excludes_cap_exceedance_with_machine_readable_audit(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        job = schedule["jobs"][0]
        report = analyze_confirmatory_events(
            [accounted_success(job, native_completion_tokens=job["cap"] + 1)], schedule,
        )

        self.assertEqual(report["cells"], [])
        self.assertEqual(report["selection_audit"]["schedule_sha256"], schedule["sha256"])
        self.assertEqual(report["selection_audit"]["excluded"][0]["reason"], "native_cap_exceeded")

    def test_analyzer_rejects_reused_generation_id_across_scheduled_jobs(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        first, second = schedule["jobs"][:2]
        rows = [
            accounted_success(first, generation_id="same", receipt_generation_id="same"),
            accounted_success(second, generation_id="same", receipt_generation_id="same"),
        ]
        with self.assertRaisesRegex(ValueError, "generation ID"):
            analyze_confirmatory_events(rows, schedule)

    def test_analyzer_rejects_duplicate_valid_job_instead_of_silently_collapsing(self):
        schedule = build_schedule(PANEL, ITEMS[:1])
        row = accounted_success(schedule["jobs"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyze_confirmatory_events([row, row], schedule)
