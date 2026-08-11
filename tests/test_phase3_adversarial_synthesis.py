from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNTHESIS = ROOT / "reap" / "15_PHASE3_ADVERSARIAL_SYNTHESIS_2026-08-10.md"
EXTERNAL_REVIEW = ROOT / "reap" / "14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md"
CONNOR_WORKSHEET = ROOT / "reap" / "12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md"
DATASET_CANDIDATES = ROOT / "reap" / "04_DATASET_CANDIDATES.md"
REAP_README = ROOT / "reap" / "README.md"
REVIEW_ARTIFACTS_README = (
    ROOT / "reap" / "review_artifacts" / "2026-08-10" / "README.md"
)
PROJECT_BRIEF = ROOT / "reap" / "claude_project" / "PROJECT_BRIEF.md"


class Phase3AdversarialSynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SYNTHESIS.read_text(encoding="utf-8")

    def test_is_non_frozen_and_authorizes_no_external_action(self) -> None:
        opening = self.text.split("## Bottom line", 1)[0]
        self.assertIn("non-frozen working record", opening)
        normalized = " ".join(opening.split())
        for action in (
            "model call",
            "smoke test",
            "provider probe",
            "spend",
            "route activation",
            "preregistration freeze",
            "confirmatory collection",
        ):
            self.assertIn(action, normalized)

    def test_all_five_declared_call_counters_are_uniquely_zero(self) -> None:
        expected = (
            "CONFIRMATORY_CALLS",
            "PAID_STUDY_GENERATION_CALLS",
            "PAID_SMOKE_CALLS",
            "PROVIDER_PROBE_CALLS",
            "DEEPSEEK_DEVELOPMENT_CALLS",
        )
        for counter in expected:
            self.assertEqual(self.text.count(f"{counter}=0"), 1)
        self.assertNotRegex(self.text, r"(?:CALLS|SPEND)=[1-9]")

    def test_decision_table_has_every_d_id_once(self) -> None:
        section = self.text.split("## Decision record after the review", 1)[1].split(
            "## Offline implementation", 1
        )[0]
        ids = re.findall(r"^\| (D\d{2}) \|", section, flags=re.MULTILINE)
        self.assertEqual(ids, [f"D{index:02d}" for index in range(1, 16)])

    def test_openai_recommendation_and_costs_are_explicitly_planning_only(self) -> None:
        self.assertIn("Terra as the main closed-model", self.text)
        self.assertIn("Luna as a cheap GPT-5.6 family sensitivity", self.text)
        self.assertIn("**Add beside Terra, not instead of it**", self.text)
        for value in ("$12.582912", "$125.829120", "$138.412032", "$314.572800"):
            self.assertIn(value, self.text)
        self.assertIn("mutable planning prices", self.text)
        self.assertIn("not a quote or", self.text)
        self.assertIn("spending authority", self.text)

    def test_dataset_and_relay_uncertainty_remain_visible(self) -> None:
        self.assertIn("rows 31–33", self.text)
        self.assertIn("planning default remains items 1–30", self.text)
        self.assertIn("not freeze-authoritative", self.text)
        self.assertIn("Internal CLI request counts also remain unverified", self.text)
        self.assertIn("Chirag's rerun remains authoritative", self.text)

    def test_current_effort_auth_and_hmmt_facts_do_not_repeat_superseded_wording(
        self,
    ) -> None:
        external_review = EXTERNAL_REVIEW.read_text(encoding="utf-8")
        worksheet = CONNOR_WORKSHEET.read_text(encoding="utf-8")
        candidates = DATASET_CANDIDATES.read_text(encoding="utf-8")

        normalized = " ".join(self.text.split())
        self.assertIn("first-party Claude subscription authentication", normalized)
        self.assertIn("reported as `claude.ai`", normalized)
        self.assertNotIn("requires OAuth for Claude", self.text)
        self.assertIn("`none/low/medium/high/xhigh/max`", external_review)
        self.assertNotIn("none/minimal/low/medium/high/xhigh/max", external_review)
        self.assertIn("hard short-answer math", worksheet.lower())
        self.assertNotIn("Hard, clean integer math", worksheet)
        self.assertIn(
            "2025 has 30 rows; the current 2026 source has 33 rows", candidates
        )

    def test_current_documents_and_review_artifact_provenance_are_bounded(self) -> None:
        readme = REAP_README.read_text(encoding="utf-8")
        artifacts = REVIEW_ARTIFACTS_README.read_text(encoding="utf-8")
        project_brief = PROJECT_BRIEF.read_text(encoding="utf-8")
        normalized_artifacts = " ".join(artifacts.split())

        for document in (
            "14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md",
            "15_PHASE3_ADVERSARIAL_SYNTHESIS_2026-08-10.md",
        ):
            self.assertIn(document, readme)
        self.assertIn("committed scripts reproduce", normalized_artifacts)
        self.assertIn(
            "origin claim was not independently verified", normalized_artifacts
        )
        self.assertNotIn("transferred verbatim", artifacts)
        self.assertIn(
            "84c1f07b52ca99f4c470594341df1b1ffcf4c8ad775d0358b610f4aaf15d484c",
            artifacts,
        )
        for phrase in (
            "15_PHASE3_ADVERSARIAL_SYNTHESIS_2026-08-10.md",
            "completed bounded Claude/Codex development relay",
            "Luna",
            "Terra",
            "Decision-independent offline safeguards",
        ):
            self.assertIn(phrase, project_brief)


if __name__ == "__main__":
    unittest.main()
