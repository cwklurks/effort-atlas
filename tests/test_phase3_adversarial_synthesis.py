from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNTHESIS = ROOT / "reap" / "15_PHASE3_ADVERSARIAL_SYNTHESIS_2026-08-10.md"


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


if __name__ == "__main__":
    unittest.main()
