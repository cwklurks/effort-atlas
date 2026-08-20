from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reap" / "next_chapter"


class NextChapterReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact_path = REPORT_ROOT / "artifact.json"
        self.html_path = REPORT_ROOT / "index.html"

    def test_artifact_has_answer_first_report_structure(self) -> None:
        artifact = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["surface"], "report")
        manifest = artifact["manifest"]
        self.assertEqual(manifest["surface"], "report")
        blocks = manifest["blocks"]
        self.assertEqual(blocks[0]["type"], "markdown")
        self.assertEqual(blocks[0]["body"], f"# {manifest['title']}")
        self.assertEqual(blocks[1]["type"], "markdown")
        self.assertTrue(blocks[1]["body"].startswith("## Executive Summary"))
        visible_text = "\n".join(
            block.get("body", "") for block in blocks if block["type"] == "markdown"
        )
        for heading in (
            "What the archives can answer",
            "The important exceptions",
            "What was completed today",
            "Recommended next steps",
            "Questions still worth deciding",
            "Caveats and assumptions",
        ):
            self.assertIn(heading, visible_text)

    def test_visuals_are_source_backed_and_show_the_known_exceptions(self) -> None:
        artifact = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        manifest = artifact["manifest"]
        source_ids = {source["id"] for source in manifest["sources"]}
        for chart in manifest["charts"]:
            self.assertIn(chart["sourceId"], source_ids)
        for table in manifest["tables"]:
            self.assertIn(table["sourceId"], source_ids)

        datasets = artifact["snapshot"]["datasets"]
        coverage = datasets["question_coverage"]
        self.assertIn(
            {"benchmark": "GPQA / HELM", "series": "Source IDs", "questions": 448},
            coverage,
        )
        self.assertIn(
            {
                "benchmark": "GPQA / HELM",
                "series": "Archived/evaluated IDs",
                "questions": 446,
            },
            coverage,
        )
        exceptions = {row["issue"]: row for row in datasets["exceptions"]}
        self.assertEqual(exceptions["HMMT-2026 item 25"]["affected_attempts"], 106)
        self.assertEqual(exceptions["HMMT-2026 missing cells"]["affected_cells"], 11)
        self.assertEqual(
            exceptions["HELM Gemini length labels"]["affected_attempts"], 42
        )

    def test_report_never_overstates_grades_tokens_or_execution(self) -> None:
        artifact_text = self.artifact_path.read_text(encoding="utf-8")
        self.assertNotIn("16 of 17", artifact_text)
        self.assertIn("source-native", artifact_text)
        self.assertIn("not comparable", artifact_text)
        self.assertIn("No provider calls", artifact_text)
        self.assertIn("Linux", artifact_text)

    def test_html_is_self_contained_packaged_reader_output(self) -> None:
        html = self.html_path.read_text(encoding="utf-8")
        self.assertIn('id="data-analytics-portable-reader"', html)
        self.assertIn("From public benchmark archives to the next experiment", html)
        self.assertIsNone(
            re.search(r"<script[^>]+src=[\"']https?://", html, re.IGNORECASE)
        )
        self.assertIsNone(
            re.search(r"<link[^>]+href=[\"']https?://", html, re.IGNORECASE)
        )

    def test_build_receipt_pins_current_report_bytes(self) -> None:
        receipt = (REPORT_ROOT / "BUILD_RECEIPT.md").read_text(encoding="utf-8")
        for path in (
            self.artifact_path,
            self.html_path,
            ROOT / "observational" / "benchmark_question_capabilities.jsonl",
            ROOT / "observational" / "benchmark_question_capabilities_summary.json",
        ):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertIn(digest, receipt)
        self.assertIn("verification: `structural_only`", receipt)
        self.assertNotIn("browser verification passed", receipt.lower())


if __name__ == "__main__":
    unittest.main()
