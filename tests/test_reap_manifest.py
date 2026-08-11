from __future__ import annotations

import copy
import unittest

from effort_atlas.reap_manifest import seal_manifest, validate_manifest

HASHES = {
    name: str(index) * 64
    for index, name in enumerate(
        ("dataset", "prompt", "routes", "schedule", "analysis", "activation"),
        start=1,
    )
}


def _reference(path: str, digest: str) -> dict[str, str]:
    return {"path": path, "sha256": digest}


def valid_manifest(*, state: str = "frozen") -> dict[str, object]:
    unsigned: dict[str, object] = {
        "manifest_version": 2,
        "state": state,
        "dataset": _reference("artifacts/dataset.json", HASHES["dataset"]),
        "prompt_renderer_grader": _reference(
            "artifacts/prompt-renderer-grader.json", HASHES["prompt"]
        ),
        "route_price": _reference("artifacts/routes.json", HASHES["routes"]),
        "schedule": {
            **_reference("artifacts/schedule.json", HASHES["schedule"]),
            "dataset_sha256": HASHES["dataset"],
            "prompt_renderer_grader_sha256": HASHES["prompt"],
            "route_price_sha256": HASHES["routes"],
        },
        "analysis": {
            **_reference("artifacts/analysis.json", HASHES["analysis"]),
            "schedule_sha256": HASHES["schedule"],
        },
        "activation": {
            **_reference("artifacts/activation.json", HASHES["activation"]),
            "schedule_sha256": HASHES["schedule"],
            "route_price_sha256": HASHES["routes"],
        },
    }
    return seal_manifest(unsigned)


class ReapManifestTests(unittest.TestCase):
    def test_seal_and_validate_return_detached_nested_values(self) -> None:
        sealed = valid_manifest()
        validated = validate_manifest(sealed)

        validated_dataset = validated["dataset"]
        self.assertIsInstance(validated_dataset, dict)
        validated_dataset["path"] = "mutated-after-validation.json"
        self.assertEqual(
            sealed["dataset"]["path"],  # type: ignore[index]
            "artifacts/dataset.json",
        )

        unsigned = {
            key: value for key, value in sealed.items() if key != "manifest_sha256"
        }
        resealed = seal_manifest(unsigned)
        unsigned_dataset = unsigned["dataset"]
        self.assertIsInstance(unsigned_dataset, dict)
        unsigned_dataset["path"] = "mutated-after-sealing.json"
        self.assertEqual(
            resealed["dataset"]["path"],  # type: ignore[index]
            "artifacts/dataset.json",
        )

    def test_sealed_manifest_is_deterministic_and_valid(self) -> None:
        manifest = valid_manifest()
        self.assertEqual(
            manifest,
            seal_manifest(
                {
                    key: value
                    for key, value in manifest.items()
                    if key != "manifest_sha256"
                }
            ),
        )
        self.assertEqual(validate_manifest(manifest), manifest)
        self.assertRegex(str(manifest["manifest_sha256"]), r"^[0-9a-f]{64}$")

    def test_missing_unknown_and_wrongly_typed_fields_fail(self) -> None:
        mutations: list[dict[str, object]] = []

        missing = valid_manifest()
        del missing["analysis"]
        mutations.append(missing)

        unknown = valid_manifest()
        unknown["fallback_route"] = "forbidden"
        mutations.append(unknown)

        wrong_version = valid_manifest()
        wrong_version["manifest_version"] = True
        mutations.append(wrong_version)

        unknown_section = valid_manifest()
        unknown_section["dataset"] = {
            **unknown_section["dataset"],  # type: ignore[arg-type]
            "selection_rule": "first 30",
        }
        mutations.append(unknown_section)

        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_manifest(mutation)

    def test_paths_hashes_and_frozen_placeholders_fail_closed(self) -> None:
        cases = (
            ("dataset", "path", "/absolute/dataset.json"),
            ("dataset", "path", "../dataset.json"),
            ("dataset", "sha256", "not-a-hash"),
            ("route_price", "path", "TBD"),
        )
        for section, key, value in cases:
            manifest = valid_manifest()
            section_value = dict(manifest[section])  # type: ignore[arg-type]
            section_value[key] = value
            manifest[section] = section_value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                validate_manifest(manifest)

    def test_every_cross_artifact_hash_mismatch_fails(self) -> None:
        mutations: list[dict[str, object]] = []
        for section, key in (
            ("schedule", "dataset_sha256"),
            ("schedule", "prompt_renderer_grader_sha256"),
            ("schedule", "route_price_sha256"),
            ("analysis", "schedule_sha256"),
            ("activation", "schedule_sha256"),
            ("activation", "route_price_sha256"),
        ):
            manifest = valid_manifest()
            section_value = dict(manifest[section])  # type: ignore[arg-type]
            section_value[key] = "f" * 64
            manifest[section] = section_value
            mutations.append(manifest)

        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_manifest(mutation)

    def test_manifest_digest_detects_any_change(self) -> None:
        manifest = valid_manifest()
        mutation = copy.deepcopy(manifest)
        mutation["state"] = "draft"
        with self.assertRaises(ValueError):
            validate_manifest(mutation)

    def test_draft_is_labeled_but_not_treated_as_frozen(self) -> None:
        manifest = valid_manifest(state="draft")
        validated = validate_manifest(manifest)
        self.assertEqual(validated["state"], "draft")
        with self.assertRaises(ValueError):
            validate_manifest(manifest, require_frozen=True)


if __name__ == "__main__":
    unittest.main()
