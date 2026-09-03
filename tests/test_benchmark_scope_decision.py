from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "reap" / "23_BENCHMARK_SCOPE_DECISION_2026-08-20.md"


class BenchmarkScopeDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DECISION.read_text(encoding="utf-8")

    def test_scope_boundary_is_non_frozen_and_call_free(self) -> None:
        self.assertIn("NON-FROZEN SCOPE BOUNDARY", self.text)
        self.assertIn("NO CALL AUTHORIZATION", self.text)
        for counter in (
            "CONFIRMATORY_CALLS=0",
            "PAID_STUDY_GENERATION_CALLS=0",
            "PAID_SMOKE_CALLS=0",
            "PROVIDER_PROBE_CALLS=0",
            "DEEPSEEK_DEVELOPMENT_CALLS=0",
        ):
            self.assertIn(counter, self.text)

    def test_exploratory_and_controlled_denominators_cannot_mix(self) -> None:
        self.assertIn("Exploratory public-archive scope", self.text)
        self.assertIn("Controlled experiment scope", self.text)
        self.assertIn(
            "No archived response row, grade, token count, or termination field may enter a\n"
            "controlled-effect denominator",
            self.text,
        )
        self.assertIn("Source-native archived grade", self.text)
        self.assertIn("Strict `Final answer: <answer>`", self.text)

    def test_scope_does_not_overclaim_censoring_or_token_comparability(self) -> None:
        self.assertIn("a causal claim that a particular answer was wrong because of a cap", self.text)
        self.assertIn("a censoring-adjusted or imputed accuracy", self.text)
        self.assertIn("a pooled native-token ratio across providers or tokenizers", self.text)
        self.assertIn("`not_estimable`", self.text)

    def test_exact_controlled_questions_remain_a_later_human_decision(self) -> None:
        self.assertIn("What this phase deliberately does not decide", self.text)
        self.assertIn("the disposition of HMMT-2026 question 25", self.text)
        self.assertIn("items 31-33", self.text)
        self.assertIn("owned by Connor and Chirag", self.text)


if __name__ == "__main__":
    unittest.main()
