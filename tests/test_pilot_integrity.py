"""Offline source-integrity adversaries using only synthetic source content."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas.pilot_integrity import load_selected_items, rendered_digest, verify_selection
from effort_atlas.pilot_select import build_selection
from effort_atlas.wrapper import render


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value) -> str:
    # Acquisition's source-row serialization differs from selection serialization.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _finish(row: dict) -> dict:
    row = {key: value for key, value in row.items() if key != "full_row_sha256"}
    return {**row, "full_row_sha256": _sha(_canonical(row).encode())}


def _row(dataset: str, index: int) -> dict:
    prompt = f"Synthetic café\u2028question {index}"
    row = {
        "schema_version": "source-item-v1", "dataset": dataset,
        "split": "main" if dataset == "gpqa_main" else "test",
        "source_url": "https://example.invalid/synthetic", "source_revision": "r" * 40,
        "source_row_index": index, "source_item_id": f"{dataset}-{index}",
        "prompt_text": prompt, "prompt_sha256": _sha(prompt.encode()),
        "choices": ["synthetic correct", "synthetic wrong"],
        "grading": {"kind": "gold_choice", "gold": "A", "gold_index": 0},
        "license_policy": "open_commit_ok", "meta": {"category": "synthétique"},
    }
    if dataset == "gpqa_main":
        row["choices"] += ["synthetic wrong 2", "synthetic wrong 3"]
        row["grading"]["gold"] = row["choices"][0]
        row["license_policy"] = "restricted_no_plaintext"
    if dataset == "wildbench_v2":
        turns = [{"role": "user", "content": prompt, "source_extra": "preserve me"}]
        row.update(prompt_text=None, choices=None, conversation_input=turns,
                   prompt_sha256=_sha(_canonical(turns).encode()),
                   grading={"kind": "judge_checklist", "checklist": ["synthetic"]})
    return _finish(row)


def _skeleton(row: dict) -> dict:
    return {**row, "prompt_text": None, "choices": None,
            "grading": {"kind": "gold_choice", "gold": None, "gold_index": None}}


def _sign(selection: dict) -> None:
    unsigned = {key: value for key, value in selection.items() if key != "selection_sha256"}
    selection["selection_sha256"] = _sha(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode())


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cap = Path(self.temp.name)
        self.manifest = {"schema_version": "capabilities-source-manifest-v1",
                         "outputs": [], "restricted_local_outputs": []}

    def write_rows(self, relative: str, rows: list[dict], *, restricted=False):
        path = self.cap / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = ("".join(_canonical(row) + "\n" for row in rows)).encode()
        path.write_bytes(blob)
        section = "restricted_local_outputs" if restricted else "outputs"
        metadata = {"path": path.name, "rows": len(rows), "bytes": len(blob), "sha256": _sha(blob)}
        self.manifest[section] = [entry for entry in self.manifest[section] if entry["path"] != path.name]
        self.manifest[section].append(metadata)
        self.save_manifest()

    def save_manifest(self):
        (self.cap / "sources_manifest.json").write_text(json.dumps(self.manifest))

    def fixture(self, dataset="public", n=2):
        self.rows = [_row(dataset, index) for index in range(3)]
        self.dataset = dataset
        self.filename = f"{dataset}.jsonl"
        self.restricted_filename = "restricted_local/gpqa_main.RESTRICTED.jsonl"
        if dataset == "gpqa_main":
            self.write_rows(self.restricted_filename, self.rows, restricted=True)
            self.write_rows(self.filename, [_skeleton(row) for row in self.rows])
        else:
            self.write_rows(self.filename, self.rows)
        self.selection = build_selection("first200", n=n, cap_dir=self.cap, datasets={dataset: {
            "file": self.filename, "split": self.rows[0]["split"],
            "stratum_key": None, "stratum": None,
        }})
        self.cfg = {"pilot": {"datasets": [dataset]}, "paths": {"data": "capabilities"}}
        return self.selection["datasets"][dataset]

    def load(self):
        return load_selected_items(self.cfg, self.selection, cap_dir=self.cap)

    def repin_public(self):
        self.selection["datasets"][self.dataset]["file_sha256"] = _sha(
            (self.cap / self.filename).read_bytes())
        _sign(self.selection)

    def test_valid_source_and_selection_use_their_distinct_unicode_canonicalizations(self):
        self.fixture()
        self.selection["purpose"] = "Synthétique selection"
        _sign(self.selection)
        original = copy.deepcopy(self.selection)
        self.assertEqual(verify_selection(self.selection), self.selection["selection_sha256"])
        self.assertEqual(self.load(), self.rows[:2])
        self.assertEqual(self.selection, original)

    def test_stale_selection_digest_refused(self):
        self.fixture()
        self.selection["purpose"] = "edited"
        with self.assertRaisesRegex(ValueError, "selection_sha256"):
            self.load()

    def test_invalid_counts_refused_even_with_fresh_selection_digest(self):
        spec = self.fixture()
        for field, value in (("n", 3), ("n", True), ("n", 0)):
            with self.subTest(field=field, value=value):
                spec[field] = value
                _sign(self.selection)
                with self.assertRaises(ValueError):
                    self.load()
        spec["n"] = 2
        self.selection["n_per_dataset"] = 3
        _sign(self.selection)
        with self.assertRaises(ValueError):
            self.load()

    def test_duplicate_selected_ids_and_coordinates_refused(self):
        spec = self.fixture()
        original = copy.deepcopy(spec["items"])
        for field in ("source_item_id", "source_row_index"):
            with self.subTest(field=field):
                spec["items"] = copy.deepcopy(original)
                spec["items"][1][field] = spec["items"][0][field]
                _sign(self.selection)
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    self.load()

    def test_duplicate_config_datasets_refused(self):
        self.fixture()
        self.cfg["pilot"]["datasets"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load()

    def test_selection_identity_split_and_optional_full_hash_pins_checked(self):
        spec = self.fixture()
        original = copy.deepcopy(spec["items"][0])
        for field, value in (("source_item_id", "absent"), ("source_row_index", 999),
                             ("split", "absent"), ("prompt_sha256", "0" * 64),
                             ("full_row_sha256", "0" * 64)):
            with self.subTest(field=field):
                spec["items"][0] = {**original, field: value}
                _sign(self.selection)
                with self.assertRaises(ValueError):
                    self.load()

    def test_file_bytes_must_match_both_selection_and_manifest(self):
        spec = self.fixture()
        original = spec["file_sha256"]
        spec["file_sha256"] = "0" * 64
        _sign(self.selection)
        with self.assertRaisesRegex(ValueError, "file_sha256"):
            self.load()
        spec["file_sha256"] = original
        _sign(self.selection)
        with (self.cap / self.filename).open("ab") as fh:
            fh.write(b"\n")
        self.repin_public()
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.load()

    def test_manifest_metadata_and_missing_or_duplicate_output_refused(self):
        self.fixture()
        original = copy.deepcopy(self.manifest)
        for field, value in (("sha256", "0" * 64), ("bytes", 1), ("rows", 2), ("rows", True)):
            with self.subTest(field=field):
                self.manifest = copy.deepcopy(original)
                self.manifest["outputs"][0][field] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "manifest"):
                    self.load()
        for outputs in ([], original["outputs"] * 2):
            self.manifest = {**original, "outputs": outputs}
            self.save_manifest()
            with self.assertRaises(ValueError):
                self.load()

    def test_public_full_row_hash_recomputed_after_outer_files_repinned(self):
        self.fixture()
        self.rows[0]["choices"][0] = "altered synthetic choice"
        self.write_rows(self.filename, self.rows)
        self.repin_public()
        with self.assertRaisesRegex(ValueError, "full_row_sha256"):
            self.load()

    def test_public_prompt_hash_recomputed_even_if_full_row_hash_repinned(self):
        self.fixture()
        self.rows[0]["prompt_text"] = "changed synthetic prompt"
        self.rows[0] = _finish(self.rows[0])
        self.write_rows(self.filename, self.rows)
        self.repin_public()
        with self.assertRaisesRegex(ValueError, "prompt_sha256"):
            self.load()

    def test_unselected_rows_are_checked_for_duplicate_ids_and_coordinates(self):
        self.fixture()
        original = copy.deepcopy(self.rows)
        for field in ("source_item_id", "source_row_index"):
            with self.subTest(field=field):
                self.rows = copy.deepcopy(original)
                self.rows[-1][field] = self.rows[0][field]
                self.rows[-1] = _finish(self.rows[-1])
                self.write_rows(self.filename, self.rows)
                self.repin_public()
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    self.load()

    def test_source_dataset_and_revision_checked(self):
        self.fixture()
        original = copy.deepcopy(self.rows)
        for field in ("dataset", "source_revision"):
            with self.subTest(field=field):
                self.rows = copy.deepcopy(original)
                self.rows[-1][field] = "unexpected"
                self.rows[-1] = _finish(self.rows[-1])
                self.write_rows(self.filename, self.rows)
                self.repin_public()
                with self.assertRaises(ValueError):
                    self.load()

    def test_wildbench_hashes_full_source_conversation_not_wrapper_projection(self):
        self.fixture("wildbench_v2")
        self.assertEqual(self.load(), self.rows[:2])
        self.rows[0]["conversation_input"][0]["source_extra"] = "changed"
        self.rows[0] = _finish(self.rows[0])
        self.write_rows(self.filename, self.rows)
        self.repin_public()
        with self.assertRaisesRegex(ValueError, "prompt_sha256"):
            self.load()

    def test_absolute_traversal_and_symlink_source_paths_refused(self):
        spec = self.fixture()
        for filename in (str(self.cap / self.filename), "../outside.jsonl", "nested/../../outside.jsonl"):
            with self.subTest(filename=filename):
                spec["file"] = filename
                _sign(self.selection)
                with self.assertRaisesRegex(ValueError, "path"):
                    self.load()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "source.jsonl"
            target.write_bytes((self.cap / self.filename).read_bytes())
            (self.cap / "escape.jsonl").symlink_to(target)
            spec["file"] = "escape.jsonl"
            _sign(self.selection)
            with self.assertRaisesRegex(ValueError, "path"):
                self.load()

    def test_gpqa_returns_verified_full_rows_not_skeletons(self):
        self.fixture("gpqa_main")
        self.assertEqual(self.load(), self.rows[:2])

    def test_gpqa_missing_and_empty_restricted_files_refused(self):
        self.fixture("gpqa_main")
        path = self.cap / self.restricted_filename
        path.unlink()
        with self.assertRaises(ValueError):
            self.load()
        self.write_rows(self.restricted_filename, [], restricted=True)
        with self.assertRaises(ValueError):
            self.load()

    def test_gpqa_actual_restricted_bytes_must_match_manifest(self):
        self.fixture("gpqa_main")
        path = self.cap / self.restricted_filename
        with path.open("ab") as fh:
            fh.write(b"\n")
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.load()

    def test_gpqa_changed_content_with_old_claimed_hashes_refused_without_text_in_error(self):
        self.fixture("gpqa_main")
        sentinel = "PRIVATE-SYNTHETIC-SENTINEL"
        self.rows[0]["prompt_text"] = sentinel
        self.write_rows(self.restricted_filename, self.rows, restricted=True)
        with self.assertRaisesRegex(ValueError, "full_row_sha256") as raised:
            self.load()
        self.assertNotIn(sentinel, str(raised.exception))

    def test_gpqa_fresh_full_hash_does_not_bypass_prompt_hash(self):
        self.fixture("gpqa_main")
        self.rows[0]["prompt_text"] = "changed synthetic prompt"
        self.rows[0] = _finish(self.rows[0])
        self.write_rows(self.restricted_filename, self.rows, restricted=True)
        with self.assertRaisesRegex(ValueError, "prompt_sha256"):
            self.load()

    def test_gpqa_duplicates_and_missing_rows_refused(self):
        self.fixture("gpqa_main")
        for rows in ([self.rows[0], self.rows[0], self.rows[2]], self.rows[:2], self.rows[1:]):
            with self.subTest(count=len(rows)):
                self.write_rows(self.restricted_filename, rows, restricted=True)
                with self.assertRaises(ValueError):
                    self.load()

    def test_gpqa_skeleton_must_equal_sanitized_real_row(self):
        self.fixture("gpqa_main")
        skeletons = [_skeleton(row) for row in self.rows]
        skeletons[0]["meta"] = {"category": "changed"}
        self.write_rows(self.filename, skeletons)
        self.repin_public()
        with self.assertRaisesRegex(ValueError, "skeleton"):
            self.load()

    def test_gpqa_restricted_symlink_outside_capabilities_refused(self):
        self.fixture("gpqa_main")
        path = self.cap / self.restricted_filename
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / path.name
            target.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "path"):
                self.load()

    def test_invalid_source_json_is_sanitized(self):
        self.fixture()
        sentinel = "PRIVATE-SYNTHETIC-SENTINEL"
        (self.cap / self.filename).write_text('{"prompt_text":"' + sentinel)
        self.repin_public()
        entry = self.manifest["outputs"][0]
        entry.update(sha256=self.selection["datasets"][self.dataset]["file_sha256"],
                     bytes=(self.cap / self.filename).stat().st_size)
        self.save_manifest()
        with self.assertRaises(ValueError) as raised:
            self.load()
        self.assertNotIn(sentinel, str(raised.exception))

    def test_rendered_digest_binds_order_and_metadata_without_mutation(self):
        rendered = [render(_row("public", index), seed=7) for index in range(2)]
        manifests = [item.manifest_row() for item in rendered]
        expected = _sha(json.dumps(manifests, sort_keys=True, separators=(",", ":")).encode())
        self.assertEqual(rendered_digest(rendered), expected)
        self.assertNotEqual(rendered_digest(rendered[::-1]), expected)
        self.assertEqual([item.manifest_row() for item in rendered], manifests)


if __name__ == "__main__":
    unittest.main()
