from __future__ import annotations

import copy
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from effort_atlas.reap_manifest import (
    seal_manifest,
    validate_manifest,
    verify_manifest_files,
)

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


def file_backed_manifest(root: Path) -> dict[str, object]:
    contents = {
        "dataset": b'{"items":[]}',
        "prompt": b'{"prompt":"Final answer:"}',
        "routes": b'{"rates":[]}',
        "schedule": b'{"jobs":[]}',
        "analysis": b'{"analysis":"frozen"}',
        "activation": b'{"action":"omit"}',
    }
    paths = {
        "dataset": "artifacts/dataset.json",
        "prompt": "artifacts/prompt-renderer-grader.json",
        "routes": "artifacts/routes.json",
        "schedule": "artifacts/schedule.json",
        "analysis": "artifacts/analysis.json",
        "activation": "artifacts/activation.json",
    }
    digests = {name: hashlib.sha256(value).hexdigest() for name, value in contents.items()}
    for name, relative_path in paths.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents[name])
    return seal_manifest(
        {
            "manifest_version": 2,
            "state": "frozen",
            "dataset": _reference(paths["dataset"], digests["dataset"]),
            "prompt_renderer_grader": _reference(paths["prompt"], digests["prompt"]),
            "route_price": _reference(paths["routes"], digests["routes"]),
            "schedule": {
                **_reference(paths["schedule"], digests["schedule"]),
                "dataset_sha256": digests["dataset"],
                "prompt_renderer_grader_sha256": digests["prompt"],
                "route_price_sha256": digests["routes"],
            },
            "analysis": {
                **_reference(paths["analysis"], digests["analysis"]),
                "schedule_sha256": digests["schedule"],
            },
            "activation": {
                **_reference(paths["activation"], digests["activation"]),
                "schedule_sha256": digests["schedule"],
                "route_price_sha256": digests["routes"],
            },
        }
    )


class ReapManifestTests(unittest.TestCase):
    def test_file_verification_reads_exact_bytes_and_returns_detached_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = file_backed_manifest(root)

            verified = verify_manifest_files(manifest, approved_root=root)

            self.assertEqual(verified["manifest"], manifest)
            self.assertEqual(verified["evidence"]["manifest_sha256"], manifest["manifest_sha256"])
            self.assertEqual(len(verified["evidence"]["sections"]), 6)
            verified["manifest"]["dataset"]["path"] = "mutated"  # type: ignore[index]
            self.assertEqual(manifest["dataset"]["path"], "artifacts/dataset.json")  # type: ignore[index]

    def test_file_verification_rejects_byte_mutation_for_each_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = file_backed_manifest(root)
            for section in (
                "dataset",
                "prompt_renderer_grader",
                "route_price",
                "schedule",
                "analysis",
                "activation",
            ):
                path = root / manifest[section]["path"]  # type: ignore[index]
                path.write_bytes(path.read_bytes() + b"mutation")
                with self.subTest(section=section), self.assertRaisesRegex(ValueError, section):
                    verify_manifest_files(manifest, approved_root=root)
                path.write_bytes(path.read_bytes()[: -len(b"mutation")])

    def test_file_verification_rejects_missing_nonfile_and_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            manifest = file_backed_manifest(root)
            dataset = root / "artifacts/dataset.json"

            dataset.unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                verify_manifest_files(manifest, approved_root=root)

            dataset.mkdir()
            with self.assertRaisesRegex(ValueError, "not a regular file"):
                verify_manifest_files(manifest, approved_root=root)

            dataset.rmdir()
            outside = Path(outside_directory) / "outside.json"
            outside.write_bytes(b"outside")
            os.symlink(outside, dataset)
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify_manifest_files(manifest, approved_root=root)

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
