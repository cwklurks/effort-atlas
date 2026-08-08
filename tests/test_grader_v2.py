from __future__ import annotations

import inspect
import json
import os
import re
import unittest
from collections import Counter
from pathlib import Path

from effort_atlas.grader_acceptance import (
    build_archive_projection,
    render_response_projection,
)
from effort_atlas.graders import grade, validate_grade_state


FIXTURE = Path(__file__).parent / "fixtures" / "grader_v2_acceptance.json"


class GraderV2Tests(unittest.TestCase):
    def test_termination_metadata_is_not_a_grader_input(self):
        grader_inputs = inspect.signature(grade).parameters

        self.assertTrue(
            {"finish_reason", "termination", "completion_tokens"}.isdisjoint(
                grader_inputs
            )
        )

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

    def test_explicit_but_unparseable_answer_is_present_and_wrong(self):
        result = grade("numeric", "Final answer: unknown", "42")

        self.assertFalse(result["correct"])
        self.assertTrue(result["extracted_answer_present"])
        self.assertEqual(result["extracted_answer"], "unknown")

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
        self.assertEqual(fixture["schema_version"], "grader-v2-acceptance-v2")
        self.assertEqual(len(fixture["rows"]), 78)
        expected_by_source = {
            source["path"]: source["selected_4096_rows"]
            for source in fixture["sources"]
        }
        self.assertEqual(
            Counter(row["source_path"] for row in fixture["rows"]),
            expected_by_source,
        )
        self.assertEqual(
            len(
                {
                    (row["source_path"], row["source_line"])
                    for row in fixture["rows"]
                }
            ),
            78,
        )

        unanswered_by_domain: dict[str, int] = {}
        legacy_empty_extractions = 0
        for row in fixture["rows"]:
            self.assertEqual(row["completion_tokens"], 4096)
            self.assertRegex(row["source_row_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(row["response_sha256"], r"^[0-9a-f]{64}$")
            self.assertNotIn("response_text", row)
            self.assertNotIn("gold", row)
            response_projection = render_response_projection(row["response_projection"])
            result = grade(
                row["grader"],
                response_projection,
                "sanitized-gold-not-retained",
            )
            if not result["extracted_answer_present"]:
                unanswered_by_domain[row["domain"]] = (
                    unanswered_by_domain.get(row["domain"], 0) + 1
                )
            legacy_empty_extractions += not row["legacy_extracted_answer_present"]

        self.assertEqual(unanswered_by_domain, {"math": 68, "knowledge": 10})
        self.assertEqual(sum(unanswered_by_domain.values()), 78)
        self.assertEqual(legacy_empty_extractions, 0)

    @unittest.skipUnless(
        os.environ.get("GRADER_V2_ARCHIVE_ROOT"),
        "set GRADER_V2_ARCHIVE_ROOT to verify the private source archives",
    )
    def test_committed_projection_matches_private_archives(self):
        archive_root = Path(os.environ["GRADER_V2_ARCHIVE_ROOT"])

        self.assertEqual(
            build_archive_projection(archive_root),
            json.loads(FIXTURE.read_text()),
        )


if __name__ == "__main__":
    unittest.main()
