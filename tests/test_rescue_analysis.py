import unittest

from effort_atlas.rescue_analysis import classify_pairs


def old_row(item_id, *, extracted_answer_present):
    return {
        "item_id": item_id,
        "domain": "math",
        "effort": "max",
        "finish_reason": "length",
        "completion_tokens": 20000,
        "correct": False,
        "extracted_answer_present": extracted_answer_present,
        "extracted_answer": "17" if extracted_answer_present else None,
        "error": None,
    }


def rescue_row(item_id, *, correct=True, finish_reason="stop"):
    return {
        "item_id": item_id,
        "domain": "math",
        "effort": "max",
        "finish_reason": finish_reason,
        "completion_tokens": 30000,
        "prompt_tokens": 100,
        "correct": correct,
        "extracted_answer_present": True,
        "extracted_answer": "42" if correct else "17",
        "reported_cost_usd": 0.1,
        "error": None,
    }


class RescueAnalysisTests(unittest.TestCase):
    def test_amended_rescue_requires_unanswered_smaller_cap_length_stop(self):
        old = [
            old_row("primary", extracted_answer_present=False),
            old_row("grade-transition", extracted_answer_present=True),
            old_row("not-normal", extracted_answer_present=False),
        ]
        rescue = [
            rescue_row("primary"),
            rescue_row("grade-transition"),
            rescue_row("not-normal", finish_reason="tool_calls"),
        ]

        pairs = classify_pairs(old, rescue, "math", "max", 20000)

        self.assertEqual(
            [pair["status"] for pair in pairs],
            [
                "answer_present_grade_transition",
                "other_terminal",
                "primary_answer_rescue",
            ],
        )
        self.assertFalse(pairs[2]["old_extracted_answer_present"])

    def test_classify_pairs_separates_unaccounted_and_missing(self):
        old = [old_row(item_id, extracted_answer_present=False) for item_id in ["a", "b", "c"]]
        rescue = [
            rescue_row("a"),
            {
                **rescue_row("b"),
                "finish_reason": None,
                "completion_tokens": -1,
                "prompt_tokens": -1,
            },
        ]

        pairs = classify_pairs(old, rescue, "math", "max", 20000)

        self.assertEqual(
            [pair["status"] for pair in pairs],
            ["primary_answer_rescue", "unaccounted_stream", "missing"],
        )


if __name__ == "__main__":
    unittest.main()
