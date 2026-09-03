from __future__ import annotations

import unittest

from effort_atlas.dataset_manifest import (
    DatasetManifestError,
    build_dataset_manifest,
    canonical_json,
    validate_dataset_manifest,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def valid_manifest_kwargs():
    return {
        "dataset_identifier": "example_math_fixture",
        "source": {
            "url": "https://example.test/datasets/math",
            "revision": "abc123",
            "license": "CC-BY-4.0",
        },
        "items": [
            {"item_id": "item-1", "gold_sha256": SHA_A, "schema_sha256": SHA_B},
            {"item_id": "item-2", "gold_sha256": SHA_C, "schema_sha256": SHA_D},
        ],
        "scorer": {"mode_reference": "deterministic_symbolic", "mode_sha256": SHA_A},
        "selection": {
            "rule": "source_documented_item_ids",
            "provenance_statement": "Selection is defined from source metadata before model responses.",
            "evidence_sha256": SHA_B,
        },
    }


class DatasetManifestTests(unittest.TestCase):
    def test_builds_canonical_hash_sealed_manifest(self):
        first = build_dataset_manifest(**valid_manifest_kwargs())
        second = build_dataset_manifest(**valid_manifest_kwargs())

        self.assertEqual(first, second)
        self.assertEqual(first["manifest_sha256"], validate_dataset_manifest(first))
        self.assertEqual(canonical_json({"z": 1, "a": 2}), '{"a":2,"z":1}')

    def test_rejects_unknown_fields_and_bool_as_manifest_version(self):
        manifest = build_dataset_manifest(**valid_manifest_kwargs())
        with self.assertRaisesRegex(DatasetManifestError, "unknown"):
            validate_dataset_manifest({**manifest, "extra": "not allowed"})
        with self.assertRaisesRegex(DatasetManifestError, "integer"):
            validate_dataset_manifest({**manifest, "manifest_version": True})

    def test_rejects_duplicate_and_empty_or_nonstring_item_ids(self):
        cases = (
            [
                {"item_id": "same", "gold_sha256": SHA_A, "schema_sha256": SHA_B},
                {"item_id": "same", "gold_sha256": SHA_C, "schema_sha256": SHA_D},
            ],
            [{"item_id": "", "gold_sha256": SHA_A, "schema_sha256": SHA_B}],
            [{"item_id": 3, "gold_sha256": SHA_A, "schema_sha256": SHA_B}],
        )
        for items in cases:
            with self.subTest(items=items), self.assertRaisesRegex(DatasetManifestError, "item_id"):
                build_dataset_manifest(**{**valid_manifest_kwargs(), "items": items})

    def test_rejects_placeholders_at_each_provenance_boundary(self):
        for mutation in (
            {"dataset_identifier": "TBD"},
            {"source": {**valid_manifest_kwargs()["source"], "revision": ""}},
            {"scorer": {"mode_reference": "PENDING", "mode_sha256": SHA_A}},
            {
                "selection": {
                    "rule": "source_documented_item_ids",
                    "provenance_statement": "[__]",
                    "evidence_sha256": SHA_B,
                }
            },
        ):
            with self.subTest(mutation=mutation), self.assertRaisesRegex(DatasetManifestError, "placeholder"):
                build_dataset_manifest(**{**valid_manifest_kwargs(), **mutation})

    def test_rejects_response_or_outcome_derived_selection(self):
        for rule in (
            "highest model accuracy items",
            "remove items with a response parsing failure",
            "choose by observed outcomes",
        ):
            with self.subTest(rule=rule), self.assertRaisesRegex(DatasetManifestError, "response|outcome"):
                build_dataset_manifest(
                    **{**valid_manifest_kwargs(), "selection": {**valid_manifest_kwargs()["selection"], "rule": rule}}
                )

    def test_hmmt_30_or_33_requires_provenance_statement_and_evidence_digest(self):
        for item_count in (30, 33):
            items = [
                {"item_id": f"item-{index}", "gold_sha256": SHA_A, "schema_sha256": SHA_B}
                for index in range(item_count)
            ]
            base = {
                **valid_manifest_kwargs(),
                "dataset_identifier": "hmmt_feb_fixture",
                "items": items,
            }
            for selection in (
                {"rule": "source_documented_item_ids", "provenance_statement": "", "evidence_sha256": SHA_B},
                {
                    "rule": "source_documented_item_ids",
                    "provenance_statement": "Selection is source documented.",
                    "evidence_sha256": "not-a-hash",
                },
            ):
                with self.subTest(item_count=item_count, selection=selection), self.assertRaises(DatasetManifestError):
                    build_dataset_manifest(**{**base, "selection": selection})

    def test_undocumented_positional_first_30_is_rejected(self):
        selection = {
            "rule": "first 30 rows",
            "provenance_statement": "Rows were listed in a viewer.",
            "evidence_sha256": SHA_B,
        }
        with self.assertRaisesRegex(DatasetManifestError, "positional"):
            build_dataset_manifest(**{**valid_manifest_kwargs(), "selection": selection})

        documented = {
            **selection,
            "provenance_statement": "The source-defined individual-round rule documents these positions.",
        }
        self.assertIn("manifest_sha256", build_dataset_manifest(**{**valid_manifest_kwargs(), "selection": documented}))


if __name__ == "__main__":
    unittest.main()
