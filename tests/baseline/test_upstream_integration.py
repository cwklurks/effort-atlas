"""Supplemental lane: actual pinned upstream code and an in-memory SDK transport.

Run alongside, never instead of, scripts/verify_offline.sh. No model calls.
"""
import json
import hashlib
from pathlib import Path
from dataclasses import replace
import shutil
import tempfile
import unittest
from unittest.mock import patch

import anthropic
import httpx2

from effort_atlas import ROOT
from effort_atlas.baseline_upstream import render_baseline, score_baseline, verify_upstream
from effort_atlas.inkling_baseline import build_request, client_options, parse_response, prepare, DATASETS, SELECTION
from test_pilot import _row

UPSTREAM = ROOT / ".cache_pilot/inkling_baseline_upstream"


class PinnedPromptAndScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_upstream(UPSTREAM)

    def test_choice_prompt_retains_upstream_reasoning_and_strict_answer_marker(self):
        row = _row("mmlu_pro", 1, category="business")
        rendered, temperature = render_baseline(row, seed=7)
        self.assertTrue(rendered.prompt.startswith("What is the correct answer to this question: "))
        self.assertIn("\nChoices:\nA. c0\nB. c1\nC. c2\nD. c3\n", rendered.prompt)
        self.assertIn("Let’s think step by step.", rendered.prompt)
        self.assertTrue(rendered.prompt.endswith("Final answer: <letter>"))
        self.assertNotIn("Think as much as you need", rendered.prompt)
        self.assertNotIn("The correct answer is", rendered.prompt)
        self.assertEqual(temperature, 1)

    def test_gpqa_permutation_and_gold_stay_matched_and_deterministic(self):
        row = _row("gpqa_main", 3)
        first, _ = render_baseline(row, seed=20260830)
        second, _ = render_baseline(row, seed=20260830)
        self.assertEqual(first.prompt, second.prompt)
        self.assertIn(f"({first.gold_letter}) c0", first.prompt)
        score = score_baseline(row, first, f"Final answer: {first.gold_letter}\nExtra text cut off",
                               upstream_root=UPSTREAM)
        self.assertTrue(score["correct"])

    def test_multiple_choice_does_not_credit_an_ambiguous_final_answer(self):
        row = _row("mmlu_pro", 1, category="business")
        rendered, _ = render_baseline(row, seed=7)
        result = score_baseline(row, rendered, "Final answer: A or B", upstream_root=UPSTREAM)
        self.assertTrue(result["extracted_answer_present"])
        self.assertFalse(result["correct"])
        self.assertFalse(result["answer_format_valid"])

    def test_ifeval_verbatim_prompt_and_original_google_checker(self):
        row = _row("ifeval", 1, kind="verifiable_instructions")
        row["prompt_text"] = "Write a greeting with no commas.\n"
        row["grading"].update(instruction_id_list=["punctuation:no_comma"], kwargs=[{}])
        rendered, temperature = render_baseline(row, seed=7)
        self.assertEqual(rendered.prompt, row["prompt_text"])
        self.assertEqual(temperature, 0)
        for text, expected in (("hello world", True), ("hello, world", False)):
            result = score_baseline(row, rendered, text, upstream_root=UPSTREAM)
            self.assertEqual(result["correct"], expected)
            self.assertEqual(result["instruction_results"], [expected])

    def test_checker_failure_is_not_scored_as_wrong(self):
        row = _row("ifeval", 1, kind="verifiable_instructions")
        row["grading"].update(instruction_id_list=["unknown:instruction"], kwargs=[{}])
        rendered, _ = render_baseline(row, seed=7)
        result = score_baseline(row, rendered, "hello", upstream_root=UPSTREAM)
        self.assertEqual(result["grading_status"], "grader_error")
        self.assertIsNone(result["correct"])

    def test_wildbench_conversation_is_preserved_without_answer_marker(self):
        turns = [{"role": "user", "content": "First synthetic turn"},
                 {"role": "assistant", "content": "Prior synthetic reply"},
                 {"role": "user", "content": "Follow-up synthetic turn"}]
        row = _row("wildbench_v2", 1, kind="judge_checklist", conversation_input=turns)
        rendered, temperature = render_baseline(row, seed=7)
        self.assertIsNone(rendered.prompt)
        self.assertEqual(rendered.messages, turns)
        self.assertEqual(temperature, 0)
        self.assertEqual(score_baseline(row, rendered, "hello", upstream_root=UPSTREAM)["grading_status"],
                         "quality_judging_deferred")

    def test_omni_math_keeps_reasoning_instruction_and_defers_paid_judging(self):
        row = _row("omni_math", 1, kind="gold_answer")
        rendered, _ = render_baseline(row, seed=7)
        self.assertIn("giving your reasoning beforehand", rendered.prompt)
        self.assertIn("Final answer: <answer>", rendered.prompt)
        self.assertNotIn("\\boxed{}", rendered.prompt)
        score = score_baseline(row, rendered, "Reasoning only: 12", upstream_root=UPSTREAM)
        self.assertFalse(score["extracted_answer_present"])
        self.assertIsNone(score["correct"])
        self.assertEqual(score["grading_status"], "pending_official_judge")


    def test_plan_binds_private_answer_keys_and_refuses_tampered_artifacts(self):
        rows = [_row(dataset, index, category="business")
                for dataset in DATASETS for index in range(200)]
        rendered, temperature = render_baseline(rows[0], seed=20260830)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (SELECTION, "src/effort_atlas/inkling_baseline.py",
                             "src/effort_atlas/baseline_upstream.py", "src/effort_atlas/graders.py",
                             "src/effort_atlas/wrapper.py", "reap/inkling_baseline/requirements.lock"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            with patch("effort_atlas.inkling_baseline.load_selected_items", return_value=rows), \
                 patch("effort_atlas.baseline_upstream.render_baseline", return_value=(rendered, temperature)):
                first = prepare(root=root, upstream_root=UPSTREAM)
                directory = Path(first["directory"])
                manifest = json.loads((directory / "manifest.json").read_text())
                private_path = directory / "requests.private.jsonl"
                self.assertEqual(manifest["private_requests_sha256"],
                                 hashlib.sha256(private_path.read_bytes()).hexdigest())
                self.assertIn("src/effort_atlas/wrapper.py", manifest["implementation_sha256"])
                private_path.write_bytes(private_path.read_bytes() + b" ")
                with self.assertRaisesRegex(ValueError, "refusing to replace"):
                    prepare(root=root, upstream_root=UPSTREAM)
            changed = replace(rendered, gold_letter="B" if rendered.gold_letter != "B" else "A")
            with patch("effort_atlas.inkling_baseline.load_selected_items", return_value=rows), \
                 patch("effort_atlas.baseline_upstream.render_baseline", return_value=(changed, temperature)):
                second = prepare(root=root, upstream_root=UPSTREAM)
            self.assertNotEqual(first["plan_sha256"], second["plan_sha256"])
            second_manifest = json.loads((Path(second["directory"]) / "manifest.json").read_text())
            self.assertEqual(manifest["items"], second_manifest["items"])


class ActualSDKTransportTests(unittest.TestCase):
    def request(self):
        return build_request({"model": "thinkingmachines/Inkling", "max_tokens": 32768,
                              "temperature": 1.0,
                              "messages": [{"role": "user", "content": "SYNTHETIC TEST ONLY"}]}, "medium")

    def client(self, handler):
        transport = httpx2.MockTransport(handler)
        return anthropic.Anthropic(api_key="SYNTHETIC_TEST_KEY", **client_options(),
                                   http_client=httpx2.Client(transport=transport,
                                                            follow_redirects=False, trust_env=False))

    def test_actual_sdk_sends_explicit_cap_effort_and_one_request(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx2.Response(200, json={
                "id": "synthetic-1", "type": "message", "role": "assistant",
                "model": "thinkingmachines/Inkling", "stop_reason": "end_turn", "stop_sequence": None,
                "content": [{"type": "thinking", "thinking": "Final answer: B", "signature": ""},
                            {"type": "text", "text": "Final answer: A"}],
                "usage": {"input_tokens": 10, "output_tokens": 20}})
        with self.client(handler) as client:
            response = client.messages.create(**self.request())
        self.assertEqual(len(requests), 1)
        body = json.loads(requests[0].content)
        self.assertEqual(body["max_tokens"], 32768)
        self.assertEqual(body["output_config"], {"effort": "medium"})
        self.assertEqual(body["temperature"], 1.0)
        self.assertNotIn("tools", body)
        self.assertEqual(str(requests[0].url), client_options()["base_url"] + "/v1/messages")
        parsed = parse_response(response.model_dump(), cap=32768)
        self.assertEqual(parsed["text"], "Final answer: A")
        self.assertIsNone(parsed["reasoning_tokens_reported"])

    def test_error_timeout_and_redirect_do_not_resubmit(self):
        for outcome in (429, 500, 307, "timeout"):
            with self.subTest(outcome=outcome):
                requests = []
                def handler(request):
                    requests.append(request)
                    if outcome == "timeout":
                        raise httpx2.ReadTimeout("synthetic timeout", request=request)
                    return httpx2.Response(outcome, headers={"location": "https://example.invalid/"},
                                           json={"type": "error", "error": {"type": "api_error", "message": "synthetic"}})
                with self.client(handler) as client, self.assertRaises(anthropic.APIError):
                    client.messages.create(**self.request())
                self.assertEqual(len(requests), 1)


if __name__ == "__main__":
    unittest.main()
