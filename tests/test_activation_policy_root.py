from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from effort_atlas import activation
from effort_atlas.activation import evaluate_activation
from effort_atlas.reap_manifest import seal_manifest


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_frozen_root(
    root: Path, predicate_ids: tuple[str, ...]
) -> tuple[dict[str, object], bytes]:
    contents = {
        "dataset": b'{"items":[]}',
        "prompt_renderer_grader": b'{"template":"Final answer:"}',
        "route_price": b'{"rates":[]}',
        "schedule": b'{"jobs":[]}',
        "analysis": b'{"analysis_version":1}',
        "activation": json.dumps(
            {
                "activation_policy_version": 1,
                "predicate_ids": list(predicate_ids),
                "substitution_allowed": False,
                "terminal_actions": ["activate", "omit"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    }
    paths = {
        name: f"artifacts/{name}.json" for name in contents
    }
    for name, data in contents.items():
        target = root / paths[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    hashes = {name: _digest(data) for name, data in contents.items()}
    manifest = seal_manifest(
        {
            "manifest_version": 2,
            "state": "frozen",
            "dataset": {"path": paths["dataset"], "sha256": hashes["dataset"]},
            "prompt_renderer_grader": {
                "path": paths["prompt_renderer_grader"],
                "sha256": hashes["prompt_renderer_grader"],
            },
            "route_price": {
                "path": paths["route_price"],
                "sha256": hashes["route_price"],
            },
            "schedule": {
                "path": paths["schedule"],
                "sha256": hashes["schedule"],
                "dataset_sha256": hashes["dataset"],
                "prompt_renderer_grader_sha256": hashes["prompt_renderer_grader"],
                "route_price_sha256": hashes["route_price"],
            },
            "analysis": {
                "path": paths["analysis"],
                "sha256": hashes["analysis"],
                "schedule_sha256": hashes["schedule"],
            },
            "activation": {
                "path": paths["activation"],
                "sha256": hashes["activation"],
                "schedule_sha256": hashes["schedule"],
                "route_price_sha256": hashes["route_price"],
            },
        }
    )
    return manifest, contents["activation"]


def _passing_evidence(
    manifest: dict[str, object], predicate_ids: tuple[str, ...]
) -> dict[str, object]:
    activation_reference = manifest["activation"]
    assert isinstance(activation_reference, dict)
    return {
        "manifest_sha256": manifest["manifest_sha256"],
        "activation_policy_sha256": activation_reference["sha256"],
        "generation_retry_count": 0,
        "receipt_reconciled": True,
        "budget_within_bound": True,
        "schedule_manifest_match": True,
        "served_route_match": True,
        "predicates": [
            {
                "id": predicate_id,
                "status": "pass",
                "evidence_sha256": hashlib.sha256(predicate_id.encode()).hexdigest(),
            }
            for predicate_id in predicate_ids
        ],
    }


class ActivationPolicyRootTests(unittest.TestCase):
    def test_direct_verified_root_classmethod_cannot_self_authorize(self) -> None:
        predicate_ids = ("cap_semantics",)
        requirements = activation._ActivationRequirements(
            predicate_ids=predicate_ids,
            expected_manifest_sha256="a" * 64,
            policy_sha256="b" * 64,
        )

        decision = evaluate_activation(
            manifest=requirements,
            approved_root=Path("does-not-matter"),
            evidence={
                "manifest_sha256": "a" * 64,
                "activation_policy_sha256": "b" * 64,
            },
        )

        self.assertEqual(decision.action, "omit")
        self.assertEqual(
            decision.failed_predicates, ("activation_manifest:invalid",)
        )

    def test_public_boundary_accepts_no_policy_object_or_verification_token(self) -> None:
        parameters = inspect.signature(evaluate_activation).parameters
        self.assertEqual(set(parameters), {"manifest", "approved_root", "evidence"})
        self.assertFalse(hasattr(activation, "ActivationPolicy"))
        self.assertFalse(hasattr(activation, "load_activation_policy"))
        self.assertNotIn("policy", parameters)
        self.assertNotIn("verified", parameters)

    def test_raw_manifest_and_policy_digests_without_files_cannot_activate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = _write_frozen_root(root, ("cap_semantics",))
            for path in (root / "artifacts").iterdir():
                path.unlink()

            decision = evaluate_activation(
                manifest=manifest,
                approved_root=root,
                evidence=_passing_evidence(manifest, ("cap_semantics",)),
            )

        self.assertEqual(decision.action, "omit")
        self.assertEqual(
            decision.failed_predicates, ("activation_manifest:invalid",)
        )

    def test_manifest_verifier_filesystem_failures_omit_instead_of_escaping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = _write_frozen_root(root, ("cap_semantics",))
            evidence = _passing_evidence(manifest, ("cap_semantics",))
            for error in (OSError("unreadable"), RuntimeError("symlink loop")):
                with self.subTest(error=type(error).__name__):
                    with patch(
                        "effort_atlas.activation.verify_manifest_files",
                        side_effect=error,
                    ):
                        decision = evaluate_activation(
                            manifest=manifest,
                            approved_root=root,
                            evidence=evidence,
                        )

                    self.assertEqual(decision.action, "omit")
                    self.assertEqual(
                        decision.failed_predicates,
                        ("activation_manifest:invalid",),
                    )

    def test_exact_file_verified_frozen_activation_artifact_can_activate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = _write_frozen_root(
                root, ("cap_semantics", "termination_mapping")
            )

            decision = evaluate_activation(
                manifest=manifest,
                approved_root=root,
                evidence=_passing_evidence(
                    manifest, ("cap_semantics", "termination_mapping")
                ),
            )

        self.assertEqual(decision.action, "activate")
        self.assertEqual(decision.failed_predicates, ())

    def test_activation_artifact_byte_drift_fails_before_policy_construction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = _write_frozen_root(root, ("cap_semantics",))
            activation_path = root / manifest["activation"]["path"]
            activation_path.write_bytes(b'{"predicate_ids":[]}')

            decision = evaluate_activation(
                manifest=manifest,
                approved_root=root,
                evidence=_passing_evidence(manifest, ("cap_semantics",)),
            )

        self.assertEqual(decision.action, "omit")
        self.assertEqual(
            decision.failed_predicates, ("activation_manifest:invalid",)
        )


if __name__ == "__main__":
    unittest.main()
