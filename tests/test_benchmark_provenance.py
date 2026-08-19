from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from effort_atlas.benchmark_provenance import (
    _CAPABILITY_FIELDS,
    ProvenanceError,
    _parse_helm_gpqa_contract,
    build_capability_table,
    build_helm_capability_rows,
    build_matharena_capability_rows,
    load_manifest,
    summarize_capability_rows,
    validate_manifest,
    verify_download_root,
    write_capability_outputs,
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class BenchmarkProvenanceTests(unittest.TestCase):
    def _manifest(self, payload: bytes = b"pinned bytes") -> dict:
        return {
            "schema_version": "benchmark-source-manifest-v1",
            "source_policies": {
                "fixture": {"license": "test", "redistribution": "test"}
            },
            "entries": [
                {
                    "source_id": "fixture",
                    "role": "fixture",
                    "policy": "fixture",
                    "url": "https://raw.githubusercontent.com/example/repo/"
                    + "a" * 40
                    + "/fixture.txt",
                    "path": "fixture.txt",
                    "bytes": len(payload),
                    "sha256": _sha256(payload),
                }
            ],
        }

    def test_manifest_rejects_mutable_or_unsafe_urls(self):
        mutable = self._manifest()
        mutable["entries"][0]["url"] = (
            "https://raw.githubusercontent.com/example/repo/main/fixture.txt"
        )
        with self.assertRaisesRegex(ProvenanceError, "immutable"):
            validate_manifest(mutable)

        unsafe = self._manifest()
        unsafe["entries"][0]["path"] = "../fixture.txt"
        with self.assertRaisesRegex(ProvenanceError, "relative"):
            validate_manifest(unsafe)

        near_match = self._manifest()
        near_match["entries"][0]["url"] = (
            "https://raw.githubusercontent.com/example/repo/"
            + "a" * 40
            + "b/fixture.txt"
        )
        with self.assertRaisesRegex(ProvenanceError, "immutable"):
            validate_manifest(near_match)

    def test_verifier_fails_closed_on_missing_or_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self._manifest()
            with self.assertRaisesRegex(ProvenanceError, "missing"):
                verify_download_root(manifest, root)
            (root / "fixture.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ProvenanceError, "size|sha256"):
                verify_download_root(manifest, root)
            (root / "fixture.txt").write_bytes(b"pinned bytes")
            self.assertEqual(
                verify_download_root(manifest, root)[0]["source_id"], "fixture"
            )

    def test_matharena_rows_are_sanitized_and_keep_source_grade_separate(self):
        rows = build_matharena_capability_rows(
            benchmark="hmmt_feb_2025",
            source_records=[
                {"problem_idx": 1, "problem": "NEVER-PUBLISH", "answer": "42"},
            ],
            output_records=[
                {
                    "problem_idx": 1,
                    "model_name": "model-a",
                    "correct": True,
                    "output_tokens": 123,
                    "problem": "NEVER-PUBLISH",
                    "answer": "NEVER-PUBLISH",
                    "all_messages": "NEVER-PUBLISH",
                }
            ],
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_native_correct_count"], 1)
        self.assertEqual(row["strict_marker_regrade_status"], "not_applied")
        self.assertEqual(row["termination_status"], "not_published")
        self.assertEqual(row["source_output_text_match_status"], "matches_source")
        self.assertFalse(any("NEVER-PUBLISH" in str(value) for value in row.values()))
        self.assertFalse({"problem", "answer", "all_messages"} & set(row))

    def test_matharena_source_text_mismatch_is_visible_not_silently_accepted(self):
        rows = build_matharena_capability_rows(
            benchmark="hmmt_feb_2026",
            source_records=[{"problem_idx": 25, "problem": "old source wording"}],
            output_records=[
                {
                    "problem_idx": 25,
                    "model_name": "model-a",
                    "correct": True,
                    "output_tokens": 100,
                    "problem": "different archived wording",
                }
            ],
        )
        self.assertEqual(rows[0]["source_output_text_match_status"], "mismatch_source")

    def test_matharena_materializes_missing_cells_and_marks_zero_nonfinite_unusable(
        self,
    ):
        rows = build_matharena_capability_rows(
            benchmark="fixture",
            source_records=[
                {"problem_idx": 1, "problem": "one", "answer": "a"},
                {"problem_idx": 2, "problem": "two", "answer": "b"},
            ],
            output_records=[
                {
                    "problem_idx": 1,
                    "model_name": "model-a",
                    "correct": True,
                    "output_tokens": 0,
                    "problem": "one",
                    "gold_answer": "a",
                },
                {
                    "problem_idx": 1,
                    "model_name": "model-b",
                    "correct": False,
                    "output_tokens": float("nan"),
                    "problem": "one",
                    "gold_answer": "wrong",
                },
            ],
        )
        by_key = {(row["model"], row["question_id"]): row for row in rows}
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            by_key[("model-a", "1")]["output_tokens_status"], "zero_values_only"
        )
        self.assertFalse(by_key[("model-a", "1")]["output_tokens_available"])
        self.assertEqual(by_key[("model-b", "1")]["output_tokens_nonfinite_count"], 1)
        self.assertEqual(
            by_key[("model-b", "1")]["source_output_gold_match_status"],
            "mismatch_source",
        )
        self.assertFalse(by_key[("model-a", "2")]["archived_response_available"])
        self.assertEqual(
            by_key[("model-a", "2")]["source_native_grade_status"], "not_archived"
        )

    def test_helm_missing_source_native_correctness_fails_closed(self):
        state = {
            "instance": {"id": "id0"},
            "request": {"max_tokens": 128},
            "result": {"completions": [{"finish_reason": {"reason": "stop"}}]},
        }
        prediction = {"instance_id": "id0", "stats": {"num_output_tokens": 4}}
        with self.assertRaisesRegex(ProvenanceError, "correctness"):
            build_helm_capability_rows(
                model="fixture",
                request_states=[state],
                display_predictions=[prediction],
            )

    def test_gpqa_contract_parser_derives_indices_and_pinned_revision(self):
        scenario = """TRAIN_EXAMPLE_INDICES = {"gpqa_main": [2, 0]}\nrevision="90b8e5be2b1d3d2dbfe016cdab47981150600c4a"\n"""
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "dataset.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr(
                    "dataset/gpqa_main.csv", "Question,Correct Answer\na,a\nb,b\nc,c\n"
                )
            contract = _parse_helm_gpqa_contract(
                archive, scenario, "Password for dataset.zip: `deserted-untie-orchid`."
            )
        self.assertEqual(contract["source_row_count"], 3)
        self.assertEqual(contract["train_indices"], [0, 2])
        self.assertEqual(
            contract["hf_revision"], "90b8e5be2b1d3d2dbfe016cdab47981150600c4a"
        )

    def test_writer_is_deterministic_and_rejects_raw_content_fields(self):
        rows = [
            {
                "schema_version": "benchmark-question-capability-v1",
                "benchmark": "fixture",
                "model": "model-a",
                "question_id": "1",
                "source_question_available": True,
                "archived_response_available": True,
                "attempt_count": 1,
                "source_native_correct_count": 1,
                "source_native_accuracy": 1.0,
                "source_native_grade_semantics": "MathArena archived correct field",
                "source_native_grade_status": "available",
                "source_output_text_match_status": "not_comparable",
                "source_output_gold_match_status": "not_comparable",
                "prompt_fingerprint_set_digest": None,
                "prompt_fingerprint_count": 0,
                "output_tokens_available": False,
                "output_tokens_mean": None,
                "output_tokens_invalid_count": 0,
                "output_tokens_zero_count": 0,
                "output_tokens_negative_count": 0,
                "output_tokens_nonfinite_count": 0,
                "output_tokens_status": "not_published",
                "requested_max_tokens": None,
                "requested_cap_status": "not_published",
                "finish_reason": None,
                "termination_status": "not_published",
                "censoring_status": "unknown",
                "strict_marker_regrade_status": "not_applied",
            }
        ]
        summary = {
            "schema_version": "benchmark-question-capability-summary-v1",
            "benchmarks": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table = root / "capabilities.jsonl"
            summary_path = root / "summary.json"
            write_capability_outputs(rows, summary, table, summary_path)
            first = table.read_bytes()
            write_capability_outputs(rows, summary, table, summary_path)
            self.assertEqual(first, table.read_bytes())
            self.assertEqual(
                json.loads(summary_path.read_text())["schema_version"],
                summary["schema_version"],
            )

            with self.assertRaisesRegex(ProvenanceError, "exact schema"):
                write_capability_outputs(
                    [{**rows[0], "problem": "not allowed"}],
                    summary,
                    table,
                    summary_path,
                )
            with self.assertRaisesRegex(ProvenanceError, "exact schema"):
                write_capability_outputs(
                    [{**rows[0], "unrecognized": True}], summary, table, summary_path
                )
            with self.assertRaisesRegex(ProvenanceError, "invalid prompt_fingerprint"):
                write_capability_outputs(
                    [{**rows[0], "prompt_fingerprint_set_digest": "not-a-hash"}],
                    summary,
                    table,
                    summary_path,
                )
            with self.assertRaisesRegex(
                ProvenanceError, "archived response invariants"
            ):
                write_capability_outputs(
                    [
                        {
                            **rows[0],
                            "archived_response_available": False,
                            "attempt_count": 1,
                        }
                    ],
                    summary,
                    table,
                    summary_path,
                )
            with self.assertRaisesRegex(
                ProvenanceError, "unsupported output-token status"
            ):
                write_capability_outputs(
                    [{**rows[0], "output_tokens_status": "raw response text"}],
                    summary,
                    table,
                    summary_path,
                )

    def test_checked_in_manifest_is_structurally_pinned(self):
        manifest = load_manifest(Path("observational/benchmark_sources_manifest.json"))
        validate_manifest(manifest)

    def test_committed_table_recomputes_summary_and_keeps_known_audit_findings(self):
        table = Path("observational/benchmark_question_capabilities.jsonl")
        summary_path = Path(
            "observational/benchmark_question_capabilities_summary.json"
        )
        rows = [json.loads(line) for line in table.read_text().splitlines()]
        summary = json.loads(summary_path.read_text())
        self.assertEqual(len(rows), 4248)
        self.assertEqual(
            len({(row["benchmark"], row["model"], row["question_id"]) for row in rows}),
            len(rows),
        )
        self.assertTrue(all(set(row) == _CAPABILITY_FIELDS for row in rows))
        recomputed = summarize_capability_rows(
            rows,
            {
                "hmmt_feb_2025": 30,
                "hmmt_feb_2026": 33,
                "helm_gpqa_main_cot_v1.15.0": 448,
            },
        )
        self.assertEqual(recomputed["benchmarks"], summary["benchmarks"])
        self.assertEqual(summary["privacy"]["gpqa_content"], "excluded")
        self.assertEqual(summary["helm_gpqa_contract"]["train_indices"], [105, 339])
        self.assertEqual(summary["helm_gpqa_contract"]["evaluated_question_count"], 446)
        hmmt_2026 = next(
            item
            for item in summary["benchmarks"]
            if item["benchmark"] == "hmmt_feb_2026"
        )
        self.assertEqual(hmmt_2026["source_output_text_mismatch_rows"], 28)
        self.assertEqual(hmmt_2026["source_output_text_mismatch_attempts"], 106)
        self.assertEqual(hmmt_2026["question_by_model_rows"], 990)
        self.assertEqual(hmmt_2026["source_native_correctness_rows"], 979)
        self.assertEqual(hmmt_2026["archived_response_missing_rows"], 11)
        self.assertEqual(hmmt_2026["unmaterialized_question_by_model_rows"], 0)
        self.assertEqual(
            summary["integrity"]["capability_rows_sha256"],
            hashlib.sha256(table.read_bytes()).hexdigest(),
        )
        helm_gemini = [
            row
            for row in rows
            if row["benchmark"] == "helm_gpqa_main_cot_v1.15.0"
            and row["model"] == "google_gemini-3-pro-preview"
        ]
        self.assertEqual(len(helm_gemini), 446)
        self.assertTrue(
            all(
                row["output_tokens_status"] == "zero_values_only" for row in helm_gemini
            )
        )

    @unittest.skipUnless(
        os.environ.get("REAP_BENCHMARK_SOURCE_ROOT"),
        "set REAP_BENCHMARK_SOURCE_ROOT for exact-root rebuild",
    )
    def test_optional_exact_root_rebuild_matches_committed_artifacts(self):
        root = Path(os.environ["REAP_BENCHMARK_SOURCE_ROOT"])
        manifest = load_manifest(Path("observational/benchmark_sources_manifest.json"))
        rows, summary = build_capability_table(manifest, root)
        committed_rows = [
            json.loads(line)
            for line in Path("observational/benchmark_question_capabilities.jsonl")
            .read_text()
            .splitlines()
        ]
        committed_summary = json.loads(
            Path(
                "observational/benchmark_question_capabilities_summary.json"
            ).read_text()
        )
        self.assertEqual(rows, committed_rows)
        self.assertEqual(summary, committed_summary)


if __name__ == "__main__":
    unittest.main()
