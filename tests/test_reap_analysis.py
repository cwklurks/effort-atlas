from __future__ import annotations

import unittest

from effort_atlas.reap_analysis import validate_single_arm_rows


def analysis_row(
    *, arm_key: object = "arm-a", item_id: str = "item-1"
) -> dict[str, object]:
    return {
        "panel": "panel-a",
        "model": "model-a",
        "provider_route": "provider-a",
        "item_id": item_id,
        "effort": "high",
        "cap": 4096,
        "replicate": 1,
        "arm_key": arm_key,
        "correct": True,
        "extracted_answer_present": True,
        "extracted_answer": "42",
        "finish_reason": "stop",
        "completion_tokens": 12,
    }


class ReapAnalysisGuardTests(unittest.TestCase):
    def test_one_arm_is_returned_with_validated_rows(self) -> None:
        arm_key, rows = validate_single_arm_rows(
            [analysis_row(item_id="item-2"), analysis_row(item_id="item-1")]
        )
        self.assertEqual(arm_key, "arm-a")
        self.assertEqual([row["item_id"] for row in rows], ["item-2", "item-1"])

    def test_missing_blank_or_non_string_arm_key_is_rejected(self) -> None:
        missing = analysis_row()
        del missing["arm_key"]
        for value in (missing, analysis_row(arm_key=""), analysis_row(arm_key=1)):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "arm_key"),
            ):
                validate_single_arm_rows([value])

    def test_cross_arm_input_is_rejected_before_statistics(self) -> None:
        rows = [analysis_row(arm_key="arm-a"), analysis_row(arm_key="arm-b")]
        with self.assertRaisesRegex(ValueError, "exactly one arm_key"):
            validate_single_arm_rows(rows)

    def test_empty_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            validate_single_arm_rows([])

    def test_existing_analysis_validation_is_reused(self) -> None:
        invalid = analysis_row()
        invalid["correct"] = 1
        with self.assertRaisesRegex(ValueError, "non-boolean grade"):
            validate_single_arm_rows([invalid])


if __name__ == "__main__":
    unittest.main()
