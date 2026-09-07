"""Synthetic-only tests for the read-only Tinker billing artifact adapter."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from effort_atlas.confirmatory import sha256_json
from effort_atlas.inkling_billing import read_billing_evidence


MODEL = "thinkingmachines/Inkling"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BillingArtifactTests(unittest.TestCase):
    def _write_json(self, root: Path, name: str, value: object) -> dict:
        path = root / "results_pilot" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, separators=(",", ":")) + "\n")
        return {"path": str(path.relative_to(root)), "sha256": _sha(path.read_bytes())}

    def fixture(self, root: Path) -> tuple[dict, dict, dict]:
        events = []
        for hour, prompt, completion in ((0, 11, 23), (1, 13, 29)):
            envelope = {
                "bucket_start": f"2026-09-01T0{hour}:00:00Z",
                "bucket_end": f"2026-09-01T0{hour + 1}:00:00Z",
                "base_model": MODEL,
                "user_id": "user-synthetic",
                "user_name": "Synthetic User",
                "session_id": "session-synthetic",
                "project_id": "project-synthetic",
            }
            events.extend((
                {**envelope, "event_info": {
                    "type": "sampling_prefill", "cached": False, "token_count": prompt,
                }},
                {**envelope, "event_info": {
                    "type": "sampling_sample", "token_count": completion,
                }},
            ))
        raw = {
            "data": events,
            "sessions": {
                "session-synthetic": {"user_metadata": {"purpose": "synthetic-test"}},
            },
        }
        raw_spec = self._write_json(root, "billing-usage.json", raw)
        statement_spec = self._write_json(
            root, "synthetic-statement.json", {"synthetic": True, "not_a_provider_statement": True},
        )
        account_id = "synthetic-account"
        group = "synthetic-isolated-stage"
        deduction = {
            "schema_version": "inkling-account-deduction-v1",
            "plan_sha256": "a" * 64,
            "stage": "medium",
            "account_sha256": _sha(account_id.encode()),
            "billing_group_sha256": _sha(group.encode()),
            "model": MODEL,
            "window_start": "2026-09-01T00:00:00Z",
            "window_end": "2026-09-01T02:00:00Z",
            "raw_export_sha256": raw_spec["sha256"],
            "deduction_usd": 1.25,
            "statement_artifacts": [statement_spec],
        }
        deduction_spec = self._write_json(root, "account-deduction.json", deduction)
        record = {
            "schema_version": "inkling-billing-reconciliation-v1",
            "plan_sha256": "a" * 64,
            "stage": "medium",
            "account_id": account_id,
            "billing_group": group,
            "model": MODEL,
            "window_start": "2026-09-01T00:00:00Z",
            "window_end": "2026-09-01T02:00:00Z",
            "export_observed_at": "2026-09-01T06:00:00Z",
            "complete": True,
            "billing_scope": {
                "user_id": "user-synthetic",
                "project_id": "project-synthetic",
                "session_ids": ["session-synthetic"],
            },
            "raw_export": raw_spec,
            "account_deduction": deduction_spec,
            "attestation": {
                "reviewed_by": "Synthetic Reviewer",
                "reviewed_at": "2026-09-01T06:05:00Z",
                "reviewed_raw_export": True,
                "reviewed_account_deduction": True,
                "no_unrelated_usage": True,
            },
        }
        return record, raw, deduction

    def _rewrite(self, root: Path, record: dict, key: str, value: object) -> None:
        spec = self._write_json(root, spec_name := {
            "raw_export": "billing-usage.json",
            "account_deduction": "account-deduction.json",
        }[key], value)
        record[key] = spec
        if key == "raw_export":
            deduction_path = root / record["account_deduction"]["path"]
            deduction = json.loads(deduction_path.read_text())
            deduction["raw_export_sha256"] = spec["sha256"]
            record["account_deduction"] = self._write_json(
                root, "account-deduction.json", deduction,
            )
        self.assertEqual(spec["path"], f"results_pilot/{spec_name}")

    def test_reads_official_json_shape_and_computes_token_totals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record, _, deduction = self.fixture(root)
            evidence = read_billing_evidence(root, record)
            self.assertEqual(evidence.account_sha256, _sha(b"synthetic-account"))
            self.assertEqual(evidence.billing_group_sha256, _sha(b"synthetic-isolated-stage"))
            self.assertEqual(evidence.model, MODEL)
            self.assertEqual(evidence.window_start, datetime(2026, 9, 1, tzinfo=timezone.utc))
            self.assertEqual(evidence.window_end, datetime(2026, 9, 1, 2, tzinfo=timezone.utc))
            self.assertEqual((evidence.prompt_tokens, evidence.completion_tokens), (24, 52))
            self.assertEqual(evidence.account_deduction_usd, Decimal("1.25"))
            self.assertEqual(evidence.manifest_sha256, sha256_json(record))
            self.assertEqual(evidence.source_sha256s, (
                record["raw_export"]["sha256"],
                record["account_deduction"]["sha256"],
                deduction["statement_artifacts"][0]["sha256"],
            ))
            self.assertTrue(evidence.complete)

    def test_hour_without_activity_does_not_make_export_partial(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record, raw, _ = self.fixture(root)
            record["window_end"] = "2026-09-01T03:00:00Z"
            record["export_observed_at"] = "2026-09-01T07:00:00Z"
            record["attestation"]["reviewed_at"] = "2026-09-01T07:05:00Z"
            for event in raw["data"][2:]:
                event["bucket_start"] = "2026-09-01T02:00:00Z"
                event["bucket_end"] = "2026-09-01T03:00:00Z"
            self._rewrite(root, record, "raw_export", raw)
            deduction_path = root / record["account_deduction"]["path"]
            deduction = json.loads(deduction_path.read_text())
            deduction["window_end"] = record["window_end"]
            self._rewrite(root, record, "account_deduction", deduction)
            evidence = read_billing_evidence(root, record)
            self.assertEqual((evidence.prompt_tokens, evidence.completion_tokens), (24, 52))

    def test_missing_duplicate_and_invalid_token_rows_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for mutation in ("missing", "duplicate", "boolean", "zero", "extra"):
                record, raw, _ = self.fixture(root)
                if mutation == "missing":
                    del raw["data"][0]["event_info"]["token_count"]
                elif mutation == "duplicate":
                    raw["data"].append(deepcopy(raw["data"][0]))
                elif mutation == "boolean":
                    raw["data"][0]["event_info"]["token_count"] = True
                elif mutation == "zero":
                    raw["data"][0]["event_info"]["token_count"] = 0
                else:
                    raw["data"][0]["event_info"]["unknown"] = 1
                self._rewrite(root, record, "raw_export", raw)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)

    def test_wrong_or_mixed_attribution_refuses_without_filtering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for field, value in (
                ("base_model", "other/model"),
                ("user_id", "other-user"),
                ("project_id", "other-project"),
                ("session_id", "other-session"),
            ):
                record, raw, _ = self.fixture(root)
                raw["data"][0][field] = value
                self._rewrite(root, record, "raw_export", raw)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)

    def test_partial_unknown_or_too_early_export_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for mutation in ("incomplete", "pagination", "early", "outside_window"):
                record, raw, _ = self.fixture(root)
                if mutation == "incomplete":
                    record["complete"] = False
                elif mutation == "pagination":
                    raw["next_cursor"] = "possibly-partial"
                    self._rewrite(root, record, "raw_export", raw)
                elif mutation == "early":
                    record["export_observed_at"] = "2026-09-01T03:59:59Z"
                else:
                    raw["data"][0]["bucket_start"] = "2026-08-31T23:00:00Z"
                    raw["data"][0]["bucket_end"] = "2026-09-01T00:00:00Z"
                    self._rewrite(root, record, "raw_export", raw)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)

    def test_future_export_observation_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record, _, _ = self.fixture(root)
            record["export_observed_at"] = "2099-09-01T06:00:00Z"
            record["attestation"]["reviewed_at"] = "2099-09-01T06:05:00Z"
            with self.assertRaises(ValueError):
                read_billing_evidence(root, record)

    def test_future_human_review_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record, _, _ = self.fixture(root)
            record["attestation"]["reviewed_at"] = "2099-09-01T06:05:00Z"
            with self.assertRaises(ValueError):
                read_billing_evidence(root, record)

    def test_future_billing_window_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record, raw, _ = self.fixture(root)
            record.update(
                window_start="2099-09-01T00:00:00Z",
                window_end="2099-09-01T02:00:00Z",
                export_observed_at="2099-09-01T06:00:00Z",
            )
            record["attestation"]["reviewed_at"] = "2099-09-01T06:05:00Z"
            for index, event in enumerate(raw["data"]):
                hour = index // 2
                event["bucket_start"] = f"2099-09-01T0{hour}:00:00Z"
                event["bucket_end"] = f"2099-09-01T0{hour + 1}:00:00Z"
            self._rewrite(root, record, "raw_export", raw)
            deduction_path = root / record["account_deduction"]["path"]
            deduction = json.loads(deduction_path.read_text())
            deduction["window_start"] = record["window_start"]
            deduction["window_end"] = record["window_end"]
            self._rewrite(root, record, "account_deduction", deduction)
            with self.assertRaises(ValueError):
                read_billing_evidence(root, record)

    def test_cached_prefill_and_non_sampling_charges_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for mutation in ("cached", "training"):
                record, raw, _ = self.fixture(root)
                if mutation == "cached":
                    raw["data"][0]["event_info"]["cached"] = True
                else:
                    raw["data"][0]["event_info"] = {"type": "training", "token_count": 11}
                self._rewrite(root, record, "raw_export", raw)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)

    def test_bad_deduction_money_and_identity_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for mutation in ("negative", "zero", "boolean", "string", "nan", "account"):
                record, _, deduction = self.fixture(root)
                if mutation == "negative":
                    deduction["deduction_usd"] = -0.01
                elif mutation == "zero":
                    deduction["deduction_usd"] = 0
                elif mutation == "boolean":
                    deduction["deduction_usd"] = True
                elif mutation == "string":
                    deduction["deduction_usd"] = "1.25"
                elif mutation == "nan":
                    deduction["deduction_usd"] = float("nan")
                else:
                    deduction["account_sha256"] = "f" * 64
                self._rewrite(root, record, "account_deduction", deduction)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)

    def test_session_table_and_human_attestation_are_mandatory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for mutation in ("missing_session", "extra_session", "not_reviewed", "stale_review"):
                record, raw, _ = self.fixture(root)
                if mutation == "missing_session":
                    raw["sessions"] = {}
                    self._rewrite(root, record, "raw_export", raw)
                elif mutation == "extra_session":
                    raw["sessions"]["unrelated"] = {"user_metadata": None}
                    self._rewrite(root, record, "raw_export", raw)
                elif mutation == "not_reviewed":
                    record["attestation"]["reviewed_raw_export"] = False
                else:
                    record["attestation"]["reviewed_at"] = "2026-09-01T05:59:59Z"
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)

    def test_changed_raw_statement_or_deduction_artifact_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for artifact in ("raw_export", "account_deduction"):
                record, _, _ = self.fixture(root)
                (root / record[artifact]["path"]).write_text("changed")
                with self.subTest(artifact=artifact), self.assertRaises(ValueError):
                    read_billing_evidence(root, record)
            record, _, deduction = self.fixture(root)
            statement = deduction["statement_artifacts"][0]
            (root / statement["path"]).write_text("changed")
            with self.assertRaises(ValueError):
                read_billing_evidence(root, record)


if __name__ == "__main__":
    unittest.main()
