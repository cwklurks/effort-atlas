from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from effort_atlas.graders import grade, validate_grade_state


FIXTURE = Path(__file__).parent / "fixtures" / "grader_v2_acceptance.json"


class GraderV2Tests(unittest.TestCase):
    def test_terminator_before_later_truncation_remains_answered(self):
        result = grade(
            "numeric",
            "Reasoning.\nFinal answer: 42\nA later explanation is cut at 10",
            "42",
        )

        self.assertTrue(result["correct"])
        self.assertTrue(result["extracted_answer_present"])
        self.assertEqual(result["extracted_answer"], "42")

    def test_stray_numbers_mid_reasoning_are_unanswered(self):
        result = grade("numeric", "Try 17, then 29, but I need more time", "29")

        self.assertFalse(result["correct"])
        self.assertFalse(result["extracted_answer_present"])
        self.assertIsNone(result["extracted_answer"])

    def test_partial_box_is_unanswered_without_exception(self):
        result = grade("numeric", r"The calculation gives \boxed{29", "29")

        self.assertFalse(result["correct"])
        self.assertFalse(result["extracted_answer_present"])
        self.assertIsNone(result["extracted_answer"])

    def test_mid_enumeration_mcq_letter_is_unanswered(self):
        result = grade(
            "multiple_choice",
            "Consider (C), which is one intermediate case.",
            "C",
        )

        self.assertFalse(result["correct"])
        self.assertFalse(result["extracted_answer_present"])
        self.assertIsNone(result["extracted_answer"])

    def test_well_formed_final_answer_is_answered(self):
        result = grade("numeric", "Work\nFinal answer: 42", "42")

        self.assertTrue(result["correct"])
        self.assertTrue(result["extracted_answer_present"])
        self.assertEqual(result["extracted_answer"], "42")

    def test_terminator_pattern_is_configurable_and_line_anchored(self):
        custom = re.compile(
            r"^[ \t]*RESULT[ \t]*=[ \t]*(?P<answer>\S(?:[^\r\n]*\S)?)[ \t]*$",
            re.IGNORECASE | re.MULTILINE,
        )

        absent = grade("numeric", "prefix RESULT=7 suffix", "7", pattern=custom)
        present = grade("numeric", "work\nRESULT=7", "7", pattern=custom)

        self.assertFalse(absent["extracted_answer_present"])
        self.assertTrue(present["correct"])
        self.assertEqual(present["extracted_answer"], "7")

    def test_correct_without_answer_is_flagged_internally_inconsistent(self):
        self.assertEqual(
            validate_grade_state(
                correct=True,
                extracted_answer_present=False,
                extracted_answer=None,
            ),
            "grade_extraction_inconsistent",
        )

    def test_sanitized_archives_have_exactly_78_unanswered_4096_rows(self):
        fixture = json.loads(FIXTURE.read_text())

        self.assertEqual(
            [source["path"] for source in fixture["sources"]],
            [
                "results/sweep_real_20260719_154609.jsonl",
                "results/sweep_real_20260719_172721.jsonl",
            ],
        )
        unanswered_by_domain: dict[str, int] = {}
        legacy_empty_extractions = 0
        for source in fixture["sources"]:
            self.assertEqual(source["completion_tokens"], 4096)
            self.assertEqual(source["terminator_projection"], "")
            legacy_empty_extractions += source["legacy_empty_extractions"]
            for _source_line in source["affected_source_lines"]:
                result = grade(
                    source["grader"],
                    source["terminator_projection"],
                    "sanitized-gold-not-retained",
                )
                if not result["extracted_answer_present"]:
                    unanswered_by_domain[source["domain"]] = (
                        unanswered_by_domain.get(source["domain"], 0) + 1
                    )

        self.assertEqual(unanswered_by_domain, {"math": 68, "knowledge": 10})
        self.assertEqual(sum(unanswered_by_domain.values()), 78)
        self.assertEqual(legacy_empty_extractions, 0)


if __name__ == "__main__":
    unittest.main()
