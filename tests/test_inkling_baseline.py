"""Offline contract tests for the agreed Tinker baseline preparation."""
import unittest

from effort_atlas.inkling_baseline import build_request, parse_response


class InklingBaselineContractTests(unittest.TestCase):
    def template(self):
        return {"model": "thinkingmachines/Inkling", "max_tokens": 32768,
                "temperature": 1.0, "messages": [{"role": "user", "content": "Synthetic question"}]}

    def response(self):
        return {"id": "synthetic-message-1", "type": "message", "role": "assistant",
                "model": "thinkingmachines/Inkling", "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 20},
                "content": [{"type": "thinking", "thinking": "Final answer: B", "signature": ""},
                            {"type": "text", "text": "Final answer: A"}]}

    def test_effort_comparison_changes_only_explicit_effort(self):
        medium = build_request(self.template(), "medium")
        maximum = build_request(self.template(), "max")
        self.assertEqual(medium.pop("extra_body"), {"temperature": 1.0, "output_config": {"effort": "medium"}})
        self.assertEqual(maximum.pop("extra_body"), {"temperature": 1.0, "output_config": {"effort": "max"}})
        self.assertEqual(medium, maximum)
        self.assertEqual(medium["max_tokens"], 32768)
        self.assertNotIn("tools", medium)

    def test_unknown_effort_cap_omission_and_injected_fields_refuse(self):
        for effort in (None, "automatic", "MEDIUM"):
            with self.assertRaises(ValueError):
                build_request(self.template(), effort)
        for bad in ({"max_tokens": None}, {"max_tokens": 32000}, {"tools": []}, {"system": "override"}):
            with self.assertRaises(ValueError):
                build_request({**self.template(), **bad}, "medium")

    def test_native_stop_and_usage_stay_separate_from_answer_text(self):
        body = self.response()
        parsed = parse_response(body, cap=32768)
        self.assertEqual(parsed["text"], "Final answer: A")
        self.assertEqual(parsed["thinking"], "Final answer: B")
        self.assertEqual(parsed["native_stop_reason"], "end_turn")
        self.assertEqual(parsed["output_tokens_reported"], 20)
        self.assertIsNone(parsed["reasoning_tokens_reported"])
        self.assertFalse(parsed["cap_hit_reported"])
        body["stop_reason"] = "max_tokens"
        self.assertTrue(parse_response(body, cap=32768)["cap_hit_reported"])

    def test_missing_usage_is_unknown_and_malformed_usage_refuses(self):
        body = self.response()
        body.pop("usage")
        parsed = parse_response(body, cap=32768)
        self.assertIsNone(parsed["output_tokens_reported"])
        self.assertEqual(parsed["accounting_status"], "usage_missing")
        for value in (-1, True, 1.5, 32769):
            body["usage"] = {"input_tokens": 10, "output_tokens": value}
            with self.assertRaises(ValueError):
                parse_response(body, cap=32768)


if __name__ == "__main__":
    unittest.main()
