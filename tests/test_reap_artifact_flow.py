from __future__ import annotations

import hashlib
import json
import unittest
from decimal import Decimal

from effort_atlas.activation import ActivationPolicy, evaluate_activation
from effort_atlas.confirmatory import sha256_json
from effort_atlas.reap_budget import (
    BudgetCeilingExceeded,
    BudgetRow,
    RouteRate,
    enforce_freeze_budget_gate,
    project_maximum_exposure,
)
from effort_atlas.reap_manifest import seal_manifest, validate_manifest
from effort_atlas.reap_schedule import build_reap_schedule


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


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


class ReapArtifactFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        base = {
            "phase": "main",
            "panel": "test-panel",
            "model": "test-model",
            "provider_route": "test-route",
            "item_id": "test-item",
            "effort": "low",
            "cap": 4096,
            "replicate": 1,
            "master_seed": 20260722,
        }
        self.jobs = build_reap_schedule(
            ({**base, "arm_key": "arm-a"}, {**base, "arm_key": "arm-b"})
        )

    def _sealed_manifest(self) -> dict[str, object]:
        dataset_sha = _digest("dataset")
        prompt_sha = _digest("prompt-renderer-grader")
        route_sha = _digest("route-price-snapshot")
        schedule_sha = sha256_json(
            [
                {
                    **job.identity.as_dict(),
                    "job_id": job.job_id,
                    "provider_seed": job.provider_seed,
                }
                for job in self.jobs
            ]
        )
        return seal_manifest(
            {
                "manifest_version": 2,
                "state": "frozen",
                "dataset": {"path": "artifacts/dataset.json", "sha256": dataset_sha},
                "prompt_renderer_grader": {
                    "path": "artifacts/prompt_renderer_grader.json",
                    "sha256": prompt_sha,
                },
                "route_price": {
                    "path": "artifacts/route_price.json",
                    "sha256": route_sha,
                },
                "schedule": {
                    "path": "artifacts/schedule.json",
                    "sha256": schedule_sha,
                    "dataset_sha256": dataset_sha,
                    "prompt_renderer_grader_sha256": prompt_sha,
                    "route_price_sha256": route_sha,
                },
                "analysis": {
                    "path": "artifacts/analysis.json",
                    "sha256": _digest("analysis"),
                    "schedule_sha256": schedule_sha,
                },
                "activation": {
                    "path": "artifacts/activation.json",
                    "sha256": _digest("activation"),
                    "schedule_sha256": schedule_sha,
                    "route_price_sha256": route_sha,
                },
            }
        )

    def test_schedule_budget_manifest_and_activation_compose_fail_closed(self) -> None:
        self.assertEqual(len(self.jobs), 2)
        self.assertNotEqual(self.jobs[0].job_id, self.jobs[1].job_id)
        self.assertNotEqual(self.jobs[0].provider_seed, self.jobs[1].provider_seed)

        budget_rows = tuple(
            BudgetRow(
                job_id=job.job_id,
                route_id="openai-direct::test-route",
                phase="main",
                prompt_token_bound=512,
                max_output_tokens=job.identity.cap,
                pool_id="openai-direct",
                panel_id=job.identity.panel,
            )
            for job in self.jobs
        )
        projection = project_maximum_exposure(
            budget_rows,
            (
                RouteRate(
                    route_id="openai-direct::test-route",
                    input_usd_per_million=Decimal("0.20"),
                    output_usd_per_million=Decimal("1.20"),
                    snapshot_sha256=_digest("route-price-snapshot"),
                    basis="list",
                ),
            ),
        )
        self.assertEqual(projection.maximum_exposure_usd, Decimal("0.0100352"))
        self.assertEqual(projection.price_basis, "list")
        self.assertEqual(
            projection.by_pool_usd,
            (("openai-direct", Decimal("0.0100352")),),
        )
        self.assertEqual(
            projection.by_pool_panel_usd,
            (("openai-direct", "test-panel", Decimal("0.0100352")),),
        )
        enforce_freeze_budget_gate(
            projection,
            pool_ceilings_usd={"openai-direct": Decimal("0.0100352")},
            panel_ceilings_usd={("openai-direct", "test-panel"): Decimal("0.0100352")},
        )
        with self.assertRaisesRegex(BudgetCeilingExceeded, "openai-direct"):
            enforce_freeze_budget_gate(
                projection,
                pool_ceilings_usd={"tinker": Decimal("0.0100352")},
                panel_ceilings_usd={("tinker", "test-panel"): Decimal("0.0100352")},
            )

        manifest = validate_manifest(self._sealed_manifest(), require_frozen=True)
        required = ("single_submission", "termination_mapping")
        policy = ActivationPolicy(
            predicate_ids=required,
            expected_manifest_sha256=manifest["manifest_sha256"],
            policy_sha256=_policy_digest(required, manifest["manifest_sha256"]),
        )
        evidence = {
            "manifest_sha256": manifest["manifest_sha256"],
            "activation_policy_sha256": policy.policy_sha256,
            "generation_retry_count": 0,
            "receipt_reconciled": True,
            "budget_within_bound": True,
            "schedule_manifest_match": True,
            "served_route_match": True,
            "predicates": [
                {
                    "id": "single_submission",
                    "status": "pass",
                    "evidence_sha256": _digest("single-submission-evidence"),
                },
                {
                    "id": "termination_mapping",
                    "status": "pass",
                    "evidence_sha256": _digest("termination-mapping-evidence"),
                },
            ],
        }
        unverified_policy_decision = evaluate_activation(
            policy=policy,
            evidence=evidence,
        )
        self.assertEqual(unverified_policy_decision.action, "omit")
        self.assertIn(
            "activation_policy:unverified_root",
            unverified_policy_decision.failed_predicates,
        )

        for failed_field in ("budget_within_bound", "schedule_manifest_match"):
            failed = {**evidence, failed_field: False}
            decision = evaluate_activation(
                policy=policy,
                evidence=failed,
            )
            self.assertEqual(decision.action, "omit")
            self.assertIn(failed_field, decision.failed_predicates)


if __name__ == "__main__":
    unittest.main()
