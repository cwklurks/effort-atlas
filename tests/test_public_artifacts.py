from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas.public_artifacts import export_bundle


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


class PublicArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.results = self.workspace / "private" / "results.jsonl"
        self.receipts = self.workspace / "private" / "receipts.jsonl"
        self.dataset = self.workspace / "private" / "math.jsonl"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _export(self, bundle_id: str = "test-bundle") -> Path:
        return export_bundle(
            workspace=self.workspace,
            output_root=self.workspace / "public_artifacts",
            bundle_id=bundle_id,
            result_paths=[Path("private/results.jsonl")],
            receipt_paths=[Path("private/receipts.jsonl")],
            dataset_paths=[Path("private/math.jsonl")],
            code_commit="a" * 40,
        )

    def test_exports_only_allowlisted_fields_and_preserves_accounting(self):
        sentinel = "NEVER-PUBLISH-RAW-CONTENT"
        _write_jsonl(
            self.results,
            [
                {
                    "item_id": "math_0003",
                    "domain": "math",
                    "effort": "max",
                    "seed": None,
                    "max_tokens_requested": 2000,
                    "correct": False,
                    "completion_tokens": 2000,
                    "reasoning_tokens": 1999,
                    "prompt_tokens": 321,
                    "latency_s": 70.44,
                    "cached": False,
                    "mock": False,
                    "model": "thinkingmachines/inkling",
                    "effort_mode": "openrouter_reasoning_default",
                    "finish_reason": "length",
                    "served_provider": "Together",
                    "generation_id": "gen-public-link",
                    "reported_cost_usd": 0.008201,
                    "extracted": "",
                    "gold": sentinel,
                    "response_text": sentinel,
                    "reasoning_text": sentinel,
                    "reasoning_chars": 999,
                    "error": sentinel,
                    "unknown_private_field": sentinel,
                },
                {
                    "item_id": "math_0003",
                    "generation_id": "gen-public-link",
                    "extracted": "42",
                },
            ],
        )
        _write_jsonl(
            self.receipts,
            [
                {
                    "fetched_at": "2026-07-21T10:00:00+00:00",
                    "item_id": "math_0003",
                    "effort": "max",
                    "max_tokens_requested": 2000,
                    "generation_id": "gen-public-link",
                    "source_result": sentinel,
                    "openrouter_response": {
                        "data": {
                            "id": "gen-public-link",
                            "request_id": "req-audit-link",
                            "upstream_id": "upstream-audit-link",
                            "created_at": "2026-07-21T09:59:00+00:00",
                            "api_type": "completions",
                            "data_region": "global",
                            "model": "thinkingmachines/inkling",
                            "provider_name": "Together",
                            "finish_reason": "length",
                            "native_finish_reason": "length",
                            "tokens_prompt": 320,
                            "tokens_completion": 2000,
                            "native_tokens_prompt": 321,
                            "native_tokens_completion": 2000,
                            "native_tokens_reasoning": 1999,
                            "native_tokens_cached": 0,
                            "latency": 70440,
                            "generation_time": 70000,
                            "streamed": True,
                            "total_cost": 0.008201,
                            "upstream_inference_cost": 0.008,
                            "provider_responses": [
                                {
                                    "id": "provider-audit-link",
                                    "endpoint_id": "endpoint-audit-link",
                                    "provider_name": "Together",
                                    "model_permaslug": "inkling-snapshot",
                                    "status": 200,
                                }
                            ],
                            "user_agent": sentinel,
                            "origin": sentinel,
                            "external_user": sentinel,
                        },
                        "private_payload": sentinel,
                    },
                }
            ],
        )
        _write_jsonl(self.dataset, [{"problem": sentinel, "answer": sentinel}])

        output = self._export()
        public_text = "".join(path.read_text() for path in output.iterdir())
        self.assertNotIn(sentinel, public_text)
        self.assertNotIn("reasoning_text", public_text)
        self.assertNotIn("response_text", public_text)
        self.assertNotIn('"gold"', public_text)
        self.assertNotIn('"extracted"', public_text)
        self.assertNotIn('"error"', public_text)

        rows = _read_jsonl(output / "results.jsonl")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["completion_tokens"], 2000)
        self.assertEqual(rows[0]["reasoning_tokens"], 1999)
        self.assertEqual(rows[0]["reported_cost_usd"], 0.008201)
        self.assertTrue(rows[0]["error_present"])
        self.assertFalse(rows[0]["extracted_answer_present"])
        self.assertEqual(rows[1]["generation_id"], "gen-public-link")
        self.assertIsNone(rows[1]["completion_tokens"])
        self.assertTrue(rows[1]["extracted_answer_present"])

        receipt = _read_jsonl(output / "receipts.jsonl")[0]
        self.assertEqual(receipt["request_id"], "req-audit-link")
        self.assertEqual(receipt["provider_response_id"], "provider-audit-link")
        self.assertEqual(receipt["native_completion_tokens"], 2000)
        self.assertEqual(receipt["native_reasoning_tokens"], 1999)
        self.assertEqual(receipt["receipt_total_cost_usd"], 0.008201)

    def test_preserves_source_order_duplicates_and_provenance_deterministically(self):
        _write_jsonl(
            self.results,
            [
                {"item_id": "easy", "generation_id": "duplicate"},
                {"item_id": "hard", "generation_id": "duplicate"},
            ],
        )
        _write_jsonl(self.receipts, [])
        _write_jsonl(self.dataset, [{"problem": "private", "answer": "1"}])

        first = self._export("first")
        second = export_bundle(
            workspace=self.workspace,
            output_root=self.workspace / "public_artifacts",
            bundle_id="second",
            result_paths=[Path("private/results.jsonl")],
            receipt_paths=[Path("private/receipts.jsonl")],
            dataset_paths=[Path("private/math.jsonl")],
            code_commit="a" * 40,
        )

        rows = _read_jsonl(first / "results.jsonl")
        self.assertEqual([row["item_id"] for row in rows], ["easy", "hard"])
        self.assertEqual([row["source_line"] for row in rows], [1, 2])
        self.assertEqual([row["generation_id"] for row in rows], ["duplicate"] * 2)

        manifest = json.loads((first / "manifest.json").read_text())
        source = next(item for item in manifest["sources"] if item["role"] == "result")
        self.assertEqual(
            source["sha256"], hashlib.sha256(self.results.read_bytes()).hexdigest()
        )
        self.assertFalse(Path(source["path"]).is_absolute())
        self.assertEqual(manifest["policies"]["deduplication"], "none")
        self.assertEqual(manifest["policies"]["repair"], "none")

        for name in ("results.jsonl", "receipts.jsonl", "dataset_manifest.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_rejects_malformed_blank_external_and_existing_inputs(self):
        self.results.parent.mkdir(parents=True, exist_ok=True)
        self.results.write_text('{"item_id":"ok"}\n\n')
        _write_jsonl(self.receipts, [])
        _write_jsonl(self.dataset, [])

        with self.assertRaisesRegex(ValueError, "blank JSONL line"):
            self._export()

        self.results.write_text("[]\n")
        with self.assertRaisesRegex(ValueError, "JSON object"):
            self._export()

        _write_jsonl(self.results, [])
        with self.assertRaisesRegex(ValueError, "workspace-relative"):
            export_bundle(
                workspace=self.workspace,
                output_root=self.workspace / "public_artifacts",
                bundle_id="external",
                result_paths=[Path("/tmp/not-allowed.jsonl")],
                receipt_paths=[],
                dataset_paths=[],
                code_commit="a" * 40,
            )

        output = self._export("existing")
        self.assertTrue(output.exists())
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            self._export("existing")

    def test_dataset_manifest_contains_only_source_level_metadata(self):
        sentinel = "PRIVATE-PROBLEM-AND-GOLD"
        _write_jsonl(self.results, [])
        _write_jsonl(self.receipts, [])
        _write_jsonl(self.dataset, [{"problem": sentinel, "answer": sentinel}])

        output = self._export()
        dataset_manifest = (output / "dataset_manifest.json").read_text()
        self.assertNotIn(sentinel, dataset_manifest)
        data = json.loads(dataset_manifest)
        self.assertEqual(data["datasets"][0]["line_count"], 1)
        self.assertEqual(data["datasets"][0]["path"], "private/math.jsonl")
        self.assertNotIn("items", data)

    def test_config_sources_are_hashed_without_parsing_or_copying_content(self):
        _write_jsonl(self.results, [])
        _write_jsonl(self.receipts, [])
        _write_jsonl(self.dataset, [])
        config = self.workspace / "private" / "route.yaml"
        config.write_text("provider:\n  api_key_env: PRIVATE_ENV_NAME\n")

        output = export_bundle(
            workspace=self.workspace,
            output_root=self.workspace / "public_artifacts",
            bundle_id="config-source",
            result_paths=[Path("private/results.jsonl")],
            receipt_paths=[Path("private/receipts.jsonl")],
            dataset_paths=[Path("private/math.jsonl")],
            config_paths=[Path("private/route.yaml")],
            code_commit="a" * 40,
        )

        public_text = "".join(path.read_text() for path in output.iterdir())
        self.assertNotIn("PRIVATE_ENV_NAME", public_text)
        manifest = json.loads((output / "manifest.json").read_text())
        source = next(item for item in manifest["sources"] if item["role"] == "config")
        self.assertEqual(source["line_count"], 2)
        self.assertEqual(source["sha256"], hashlib.sha256(config.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
