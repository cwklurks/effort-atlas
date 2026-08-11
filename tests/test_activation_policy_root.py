from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas.activation import (
    ActivationPolicy,
    evaluate_activation,
    load_activation_policy,
)
from effort_atlas.reap_manifest import seal_manifest


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _policy_digest(predicate_ids: tuple[str, ...], manifest_sha256: str) -> str:
    payload = {
        "expected_manifest_sha256": manifest_sha256,
        "policy_version": 1,
        "predicate_ids": list(predicate_ids),
        "substitution_allowed": False,
        "terminal_actions": ["activate", "omit"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def _passing_evidence(policy: ActivationPolicy) -> dict[str, object]:
    return {
        "manifest_sha256": policy.expected_manifest_sha256,
        "activation_policy_sha256": policy.policy_sha256,
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
            for predicate_id in policy.predicate_ids
        ],
    }


class ActivationPolicyRootTests(unittest.TestCase):
    def test_verification_authority_is_not_a_public_constructor_argument(self) -> None:
        self.assertNotIn(
            "_verified_root", inspect.signature(ActivationPolicy).parameters
        )

    def test_caller_recomputed_subset_policy_cannot_activate(self) -> None:
        predicate_ids = ("cap_semantics",)
        manifest_sha256 = "a" * 64
        caller_policy = ActivationPolicy(
            predicate_ids=predicate_ids,
            expected_manifest_sha256=manifest_sha256,
            policy_sha256=_policy_digest(predicate_ids, manifest_sha256),
        )

        decision = evaluate_activation(
            policy=caller_policy,
            evidence=_passing_evidence(caller_policy),
        )

        self.assertEqual(decision.action, "omit")
        self.assertIn("activation_policy:unverified_root", decision.failed_predicates)

    def test_exact_file_verified_frozen_activation_artifact_can_activate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = _write_frozen_root(
                root, ("cap_semantics", "termination_mapping")
            )

            policy = load_activation_policy(manifest=manifest, approved_root=root)
            decision = evaluate_activation(
                policy=policy,
                evidence=_passing_evidence(policy),
            )

        self.assertEqual(policy.policy_sha256, manifest["activation"]["sha256"])
        self.assertEqual(decision.action, "activate")
        self.assertEqual(decision.failed_predicates, ())

    def test_activation_artifact_byte_drift_fails_before_policy_construction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = _write_frozen_root(root, ("cap_semantics",))
            activation_path = root / manifest["activation"]["path"]
            activation_path.write_bytes(b'{"predicate_ids":[]}')

            with self.assertRaisesRegex(ValueError, "activation SHA-256 mismatch"):
                load_activation_policy(manifest=manifest, approved_root=root)


if __name__ == "__main__":
    unittest.main()
