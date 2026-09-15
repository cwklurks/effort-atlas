import unittest

from effort_atlas.rescue_analysis import classify_pairs


class RescueAnalysisTests(unittest.TestCase):
    def test_classify_pairs_separates_rescue_unaccounted_and_missing(self):
        old = [
            {
                "item_id": "math_0001",
                "domain": "math",
                "effort": "max",
                "completion_tokens": 20000,
                "finish_reason": "length",
                "correct": False,
            },
            {
                "item_id": "math_0002",
                "domain": "math",
                "effort": "max",
                "completion_tokens": 20000,
                "finish_reason": "length",
                "correct": False,
            },
            {
                "item_id": "math_0003",
                "domain": "math",
                "effort": "max",
                "completion_tokens": 20000,
                "finish_reason": "length",
                "correct": False,
            },
        ]
        rescue = [
            {
                "item_id": "math_0001",
                "domain": "math",
                "effort": "max",
                "completion_tokens": 30000,
                "prompt_tokens": 100,
                "finish_reason": "stop",
                "correct": True,
                "reported_cost_usd": 0.12,
            },
            {
                "item_id": "math_0002",
                "domain": "math",
                "effort": "max",
                "completion_tokens": -1,
                "prompt_tokens": -1,
                "finish_reason": "",
                "correct": False,
            },
        ]

        pairs = classify_pairs(old, rescue, "math", "max", 20000)

        self.assertEqual(
            [pair["status"] for pair in pairs],
            ["rescued", "unaccounted_stream", "missing"],
        )
        self.assertEqual(pairs[0]["new_completion_tokens"], 30000)
        self.assertIsNone(pairs[1]["new_completion_tokens"])


if __name__ == "__main__":
    unittest.main()
