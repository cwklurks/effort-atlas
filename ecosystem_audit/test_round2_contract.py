from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "ecosystem_audit"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "ecosystem_audit_runner", AUDIT / "run_executable_audit.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoundTwoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_runner()
        with gzip.open(
            ROOT / "observational" / "real_truncated_fixtures.jsonl.gz",
            "rt",
            encoding="utf-8",
        ) as handle:
            cls.real_rows = [json.loads(line) for line in handle]

    def test_one_frozen_integer_gold_control_schema(self):
        controls = [
            row
            for row in self.real_rows
            if row["kind"] == "control_correct"
            and self.runner.control_gold_eligible(row)
        ]
        unique_items = {
            (row["dataset"], row["problem_idx"], str(row["gold_answer"]))
            for row in controls
        }
        self.assertEqual(len(controls), 28)
        self.assertEqual(len(unique_items), 4)

    def test_pre_truncation_answer_marker_strata_are_frozen(self):
        truncated = [row for row in self.real_rows if row["kind"] == "truncated"]
        counts = {
            True: sum(
                self.runner.pre_truncation_answer_present(row["text"])
                for row in truncated
            ),
            False: sum(
                not self.runner.pre_truncation_answer_present(row["text"])
                for row in truncated
            ),
        }
        self.assertEqual(counts, {True: 26, False: 105})

    def test_metric_contract_never_blends_real_and_synthetic(self):
        with (AUDIT / "pipeline_metrics.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertNotIn("combined", {row["stratum"] for row in rows})
        self.assertNotIn("fabrication_pct", {row["metric"] for row in rows})

    def test_report_is_real_first_and_labels_constructed_probes(self):
        report = (AUDIT / "results_table.md").read_text(encoding="utf-8")
        real = report.index("## Real truncated generations")
        synthetic = report.index("## Constructed synthetic probes")
        self.assertLess(real, synthetic)
        self.assertIn("insufficient_power", report)
        self.assertIn("aime_last50", report)
        self.assertNotIn("91.216216%", report)

    def test_every_executed_pipeline_has_dispatch_receipts(self):
        receipts = {
            row["finding_id"]
            for row in json.loads(
                (AUDIT / "receipt_index.json").read_text(encoding="utf-8")
            )["receipts"]
        }
        with (AUDIT / "applicability.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            pipelines = list(csv.DictReader(handle))
        for pipeline in pipelines:
            dispatch = {
                item.strip()
                for item in pipeline["dispatch_receipt_ids"].split(";")
                if item.strip()
            }
            self.assertTrue(dispatch, pipeline["pipeline_id"])
            self.assertLessEqual(dispatch, receipts, pipeline["pipeline_id"])


if __name__ == "__main__":
    unittest.main()
