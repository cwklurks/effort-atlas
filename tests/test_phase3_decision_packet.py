import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "reap" / "11_PHASE3_DECISION_PACKET_2026-08-08.md"
EXPECTED_DECISION_IDS = tuple(f"D{index:02d}" for index in range(1, 16))


class Phase3DecisionPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PACKET.read_text(encoding="utf-8")
        cls.flat_text = re.sub(r"\s+", " ", cls.text)

    def test_packet_is_a_human_decision_aid_not_an_approval(self):
        self.assertIn("Status: HUMAN DECISIONS REQUIRED", self.flat_text)
        self.assertIn("Every D01-D15 row remains HUMAN DECISION REQUIRED", self.flat_text)
        self.assertIn("Recommended defaults are not approvals", self.flat_text)

    def test_numbered_matrix_contains_every_required_decision_once(self):
        decision_ids = re.findall(r"^\|\s*(D\d{2})\s*\|", self.text, re.MULTILINE)
        self.assertEqual(decision_ids, list(EXPECTED_DECISION_IDS))
        for line in self.text.splitlines():
            if re.match(r"^\|\s*D\d{2}\s*\|", line):
                self.assertRegex(line, r"\|\s*(Connor|Chirag|both)\s*\|")
                self.assertIn("HUMAN DECISION REQUIRED", line)

    def test_packet_has_no_unresolved_bracket_placeholders(self):
        for placeholder in ("[__]", "[TBD]", "[DECIDE]", "n=__"):
            self.assertNotIn(placeholder, self.text)

    def test_zero_safety_counters_are_explicit(self):
        for counter in (
            "CONFIRMATORY_CALLS=0",
            "PAID_STUDY_GENERATION_CALLS=0",
            "SMOKE_CALLS=0",
            "PROVIDER_PROBE_CALLS=0",
            "DEEPSEEK_DEVELOPMENT_CALLS=0",
        ):
            self.assertIn(counter, self.text)

    def test_freeze_smoke_resolution_is_fail_closed_and_has_no_substitution(self):
        self.assertIn(
            "freeze scientific design and exact fail-closed activation criteria",
            self.flat_text,
        )
        self.assertIn("human smoke occurs only after the runner", self.flat_text)
        self.assertIn("activation or omission", self.flat_text)
        self.assertIn("NO SUBSTITUTION", self.text)

    def test_context_budget_and_reference_blockers_are_prominent(self):
        for blocker in (
            "standard GPT-OSS-120B route is 32K context",
            "128K PEFT route is a distinct",
            "Inkling standard route is 64K context",
            "literal 64K output allowance plus a prompt is unsafe",
            "90-item worst-case grid exceeds the $2,000 Tinker ceiling",
            "P3 n=28 exceeds the approximately $200 OpenAI pool",
            "reference-cap length stops remain censored floors",
        ):
            self.assertIn(blocker, self.flat_text)

    def test_required_analysis_terms_and_unimplemented_tests_are_disclosed(self):
        for statement in (
            "item-level empirical-marginal expected mass",
            "item-level independent-draw rescue evidence",
            "method-of-moments variance components are descriptive",
            "KS on common support",
            "absolute truncation-rate error",
            "H6 tolerance is not implemented",
            "H5 monotonicity is not implemented",
        ):
            self.assertIn(statement, self.flat_text)

    def test_sources_artifacts_approval_form_and_protected_paths_are_present(self):
        for url in (
            "https://tinker-docs.thinkingmachines.ai/tinker/models/",
            "https://developers.openai.com/api/docs/models/gpt-5.6-terra",
            "https://fireworks.ai/models/fireworks/deepseek-v4-flash",
        ):
            self.assertIn(url, self.text)
        self.assertIn("Retrieval date for all route facts: 2026-08-08", self.text)
        self.assertIn("## Required artifacts and code after decisions", self.text)
        self.assertIn("## Copyable approval form", self.text)
        self.assertIn(
            "Protected-path statement: this packet does not edit or authorize edits to",
            self.text,
        )
        for protected in (
            "PREREGISTRATION*.md",
            "confirmatory_artifacts/**",
            "observational/pipeline.py",
            "reap/status/",
            "reap/CODEX_BRIEFING.md",
        ):
            self.assertIn(protected, self.text)


if __name__ == "__main__":
    unittest.main()
