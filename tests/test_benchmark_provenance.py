from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas.benchmark_provenance import (
    ProvenanceError,
    build_matharena_capability_rows,
    load_manifest,
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
            "entries": [
                {
                    "source_id": "fixture",
                    "role": "fixture",
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

    def test_writer_is_deterministic_and_rejects_raw_content_fields(self):
        rows = [
            {
                "schema_version": "benchmark-question-capability-v1",
                "benchmark": "fixture",
                "model": "model-a",
                "question_id": "1",
                "source_native_correct_count": 1,
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

            with self.assertRaisesRegex(ProvenanceError, "forbidden"):
                write_capability_outputs(
                    [{**rows[0], "problem": "not allowed"}],
                    summary,
                    table,
                    summary_path,
                )

    def test_checked_in_manifest_is_structurally_pinned(self):
        manifest = load_manifest(Path("observational/benchmark_sources_manifest.json"))
        validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
