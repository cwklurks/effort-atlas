from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from effort_atlas import grader_acceptance
from effort_atlas.graders import extract_final_answer, grade, validate_grade_state

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

    def test_unanchored_custom_pattern_rejects_embedded_markers(self):
        custom = re.compile(r"RESULT\s*=\s*(?P<answer>\d+)", re.IGNORECASE)

        for response in (
            "prefix RESULT=7 suffix",
            "Reasoning mentions RESULT=7 as an intermediate value.",
        ):
            with self.subTest(response=response):
                result = grade("numeric", response, "7", pattern=custom)
                self.assertFalse(result["extracted_answer_present"])
                self.assertFalse(result["correct"])

        embedded_default = grade(
            "numeric",
            "Reasoning mentions Final answer: 7 as an example.",
            "7",
        )
        complete_line = grade("numeric", "work\nRESULT=7", "7", pattern=custom)

        self.assertFalse(embedded_default["extracted_answer_present"])
        self.assertTrue(complete_line["correct"])

    def test_numeric_comparator_preserves_pre_v2_field_parity(self):
        cases = (
            (r"Final answer: \boxed{42}", "42"),
            ("Final answer: $1,234$", "1234"),
            ("Final answer: 42.00", "42"),
            ("Final answer: -29", "-29"),
            ("Final answer: candidates 17 then 29", "29"),
        )

        for response, gold in cases:
            with self.subTest(response=response, gold=gold):
                result = grade("numeric", response, gold)
                self.assertTrue(result["extracted_answer_present"])
                self.assertTrue(result["correct"])

    def test_custom_capture_group_validation_and_first_group_support(self):
        first_group = grade(
            "numeric",
            "result=42",
            "42",
            pattern=r"RESULT\s*=\s*(\d+)",
        )
        optional_group = extract_final_answer(
            "RESULT=",
            pattern=re.compile(r"RESULT=(?P<answer>\d+)?"),
        )

        self.assertTrue(first_group["correct"])
        self.assertIsNone(optional_group)
        with self.assertRaisesRegex(ValueError, "must capture the answer"):
            grade(
                "numeric",
                "RESULT=42",
                "42",
                pattern=re.compile(r"RESULT=\d+"),
            )

    def test_non_numeric_and_other_comparator_paths(self):
        self.assertFalse(grade("numeric", "Final answer: unknown", "42")["correct"])
        self.assertTrue(
            grade("multiple_choice", "Final answer: option C", "C")["correct"]
        )
        self.assertFalse(
            grade("multiple_choice", "Final answer: option D", "C")["correct"]
        )
        self.assertTrue(grade("exact_field", "Final answer: $ 42.00", "42")["correct"])
        self.assertFalse(
            grade("exact_field", "Final answer: unknown", "known")["correct"]
        )

    def test_correct_without_answer_is_flagged_internally_inconsistent(self):
        self.assertEqual(
            validate_grade_state(
                correct=True,
                extracted_answer_present=False,
                extracted_answer=None,
            ),
            "grade_extraction_inconsistent",
        )

    def test_grade_state_validation_rejects_all_malformed_shapes(self):
        cases = (
            (
                {
                    "correct": 1,
                    "extracted_answer_present": False,
                    "extracted_answer": None,
                },
                "malformed_correct",
            ),
            (
                {
                    "correct": False,
                    "extracted_answer_present": None,
                    "extracted_answer": None,
                },
                "malformed_extracted_answer_presence",
            ),
            (
                {
                    "correct": False,
                    "extracted_answer_present": True,
                    "extracted_answer": None,
                },
                "grade_extraction_inconsistent",
            ),
            (
                {
                    "correct": False,
                    "extracted_answer_present": False,
                    "extracted_answer": "",
                },
                "grade_extraction_inconsistent",
            ),
            (
                {
                    "correct": False,
                    "extracted_answer_present": False,
                    "extracted_answer": None,
                },
                None,
            ),
            (
                {
                    "correct": True,
                    "extracted_answer_present": True,
                    "extracted_answer": "42",
                },
                None,
            ),
        )

        for grade_state, expected in cases:
            with self.subTest(grade_state=grade_state):
                self.assertEqual(validate_grade_state(**grade_state), expected)

    def test_response_projection_rejects_malformed_structures(self):
        malformed = (
            {},
            {"line_count": True, "terminator_line_numbers": []},
            {"line_count": -1, "terminator_line_numbers": []},
            {"line_count": 1, "terminator_line_numbers": "1"},
            {"line_count": 1, "terminator_line_numbers": [0]},
            {"line_count": 1, "terminator_line_numbers": [2]},
            {"line_count": 1, "terminator_line_numbers": [True]},
            {"line_count": 1, "terminator_line_numbers": [1, 1]},
        )

        for projection in malformed:
            with self.subTest(projection=projection), self.assertRaises(ValueError):
                grader_acceptance.render_response_projection(projection)

    def test_archive_integrity_validation_rejects_each_mismatch(self):
        payload = b'{"row": 1}\n'
        spec = {
            "path": "results/source.jsonl",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "line_count": 1,
            "domain": "math",
            "grader": "numeric",
        }

        malformed_specs = (
            {**spec, "bytes": len(payload) + 1},
            {**spec, "sha256": "0" * 64},
            {**spec, "line_count": 2},
        )
        for malformed_spec in malformed_specs:
            with self.subTest(spec=malformed_spec), self.assertRaises(ValueError):
                grader_acceptance._validate_source(malformed_spec, payload)

    def test_archive_projection_rejects_malformed_grade_fields(self):
        row = {
            "completion_tokens": 4096,
            "domain": "math",
            "response_text": 42,
            "gold": "42",
            "extracted": "42",
        }
        payload = (json.dumps(row) + "\n").encode()
        spec = {
            "path": "results/source.jsonl",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "line_count": 1,
            "domain": "math",
            "grader": "numeric",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / spec["path"]
            source.parent.mkdir()
            source.write_bytes(payload)
            with (
                patch.object(grader_acceptance, "ARCHIVE_SPECS", (spec,)),
                self.assertRaisesRegex(TypeError, "grading fields malformed"),
            ):
                grader_acceptance.build_archive_projection(Path(temp_dir))

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
            len({(row["source_path"], row["source_line"]) for row in fixture["rows"]}),
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
            response_projection = grader_acceptance.render_response_projection(
                row["response_projection"]
            )
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
            grader_acceptance.build_archive_projection(archive_root),
            json.loads(FIXTURE.read_text()),
        )


if __name__ == "__main__":
    unittest.main()
