from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECOMMENDATION = ROOT / "reap" / "13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md"
REVIEW_PROMPT = (
    ROOT / "reap" / "prompts" / "PHASE3_EXTERNAL_REVIEW_PROMPT_2026-08-10.md"
)


class Phase3IntegratedRecommendationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recommendation = RECOMMENDATION.read_text(encoding="utf-8")
        self.review_prompt = REVIEW_PROMPT.read_text(encoding="utf-8")

    def test_recommendation_is_advisory_and_preserves_zero_call_state(self) -> None:
        self.assertIn("NON-FROZEN", self.recommendation)
        self.assertIn("NO CALL AUTHORIZATION", self.recommendation)
        for counter in (
            "CONFIRMATORY_CALLS=0",
            "PAID_STUDY_GENERATION_CALLS=0",
            "SMOKE_CALLS=0",
            "PROVIDER_PROBE_CALLS=0",
            "DEEPSEEK_DEVELOPMENT_CALLS=0",
        ):
            self.assertEqual(self.recommendation.count(counter), 1)

    def test_recommendation_covers_every_decision_and_requested_topic(self) -> None:
        for number in range(1, 16):
            self.assertRegex(self.recommendation, rf"(?m)^### D{number:02d}\b")
        for heading in (
            "## Recommended scientific design",
            "## Recommended model portfolio",
            "## Dataset and grader recommendation",
            "## Statistical recommendation",
            "## Operational and budget recommendation",
            "## Questions for Chirag",
            "## Evidence and mutable facts",
        ):
            self.assertIn(heading, self.recommendation)

    def test_recommendation_surfaces_known_route_and_grader_limits(self) -> None:
        required = (
            "Tinker SDK 0.25.0",
            "one and only one billed submission",
            "30-of-33",
            "fractions or radicals",
            "pinned upstream MathArena",
            "OpenRouter",
            "Groq",
            "does **not** list Fireworks",
            "DeepSeek V4 Flash",
            "NO SUBSTITUTION",
        )
        for phrase in required:
            self.assertIn(phrase, self.recommendation)
        self.assertRegex(self.recommendation, r"item-clustered\s+bootstrap")

    def test_recommendation_states_scientific_target_and_readiness_boundary(self) -> None:
        required = (
            "## Scientific target, contribution, and readiness",
            "D_c = accuracy(high effort, c) - accuracy(low effort, c)",
            "I = D_large - D_small",
            "The Coupling Tax",
            "scientific validity > reliable collection > budget safety",
            "The full REAP A/B/C schedule exporter does not exist",
            "The paid runner and executable budget gates do not exist",
            "effective sample size is governed mainly by independent items",
        )
        for phrase in required:
            self.assertIn(phrase, self.recommendation)

    def test_recommendation_covers_marker_route_and_dataset_interpretation_risks(
        self,
    ) -> None:
        required = (
            "marker compliance",
            "quantization or numerical precision",
            "tokenizer",
            "training-data contamination",
            "VERIFIED REPOSITORY FACT",
            "PROPOSED DESIGN CHOICE",
            "UNRESOLVED HUMAN DECISION",
        )
        for phrase in required:
            self.assertIn(phrase, self.recommendation)

    def test_external_prompt_is_self_contained_and_demands_a_final_plan(self) -> None:
        required = (
            "You are an independent scientific and systems reviewer",
            "Do not assume the proposed recommendation is correct",
            "No provider or model-generation calls",
            "D01-D15",
            "Final recommended plan",
            "disagreements",
            "confidence",
            "primary sources",
            "NO SUBSTITUTION",
        )
        for phrase in required:
            self.assertIn(phrase, self.review_prompt)
        self.assertIsNotNone(
            re.search(r"(?m)^## Required output format$", self.review_prompt)
        )

    def test_external_prompt_requires_missing_scientific_and_evidence_checks(self) -> None:
        required = (
            "attach or paste both",
            "I = D_large - D_small",
            "The Coupling Tax",
            "effective sample size",
            "multiple comparisons",
            "marker compliance",
            "quantization or numerical precision",
            "training-data contamination",
            "Preregistration freeze blocker",
            "Panel activation blocker",
            "Recommended improvement",
            "Later-study idea",
            "Supplied repository fact",
            "do not claim that you independently verified repository code",
        )
        for phrase in required:
            self.assertIn(phrase, self.review_prompt)


if __name__ == "__main__":
    unittest.main()
