from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from effort_atlas.activation import evaluate_activation
from effort_atlas.analysis import analyze_confirmatory_rows
from effort_atlas.reap_budget import (
    BudgetCeilingExceeded,
    BudgetRow,
    RouteRate,
    project_maximum_exposure,
    validate_planning_budget_ceiling,
)
from effort_atlas.reap_manifest import seal_manifest, verify_manifest_files
from effort_atlas.reap_schedule import build_reap_schedule


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class ReapArtifactFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        base = {
            "phase": "main",
            "panel": "test-panel",
            "model": "test-model",
            "provider_route": "openai-direct::test-route",
            "item_id": "test-item",
            "replicate": 1,
            "master_seed": 20260722,
        }
        self.jobs = build_reap_schedule(
            {
                **base,
                "arm_key": arm_key,
                "effort": effort,
                "cap": cap,
            }
            for arm_key in ("arm-a", "arm-b")
            for effort in ("low", "high")
            for cap in (4096, 8192)
        )

    def _write_frozen_artifact_tree(self, root: Path) -> dict[str, object]:
        schedule_rows = [
            {
                **job.identity.as_dict(),
                "job_id": job.job_id,
                "provider_seed": job.provider_seed,
            }
            for job in self.jobs
        ]
        contents = {
            "dataset": json.dumps(
                {
                    "dataset_id": "fixture-math",
                    "items": [{"item_id": "test-item", "gold": r"\frac{1}{2}"}],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
            "prompt_renderer_grader": json.dumps(
                {
                    "final_answer_terminator": "Final answer: <answer>",
                    "matharena_scorer": {
                        "distribution_version": "fixture-version",
                        "module_name": "matharena.parser",
                        "source_sha256": _digest("pinned-matharena-source"),
                    },
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
            "route_price": json.dumps(
                {
                    "basis": "list",
                    "route_id": "openai-direct::test-route",
                    "input_usd_per_million": "0.20",
                    "output_usd_per_million": "1.20",
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
            "schedule": json.dumps(
                schedule_rows, sort_keys=True, separators=(",", ":")
            ).encode(),
            "analysis": b'{"analysis_version":1,"input_schema":"reap_v2"}',
            "activation": json.dumps(
                {
                    "activation_policy_version": 1,
                    "predicate_ids": [
                        "single_submission",
                        "termination_mapping",
                    ],
                    "substitution_allowed": False,
                    "terminal_actions": ["activate", "omit"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
        }
        paths = {name: f"artifacts/{name}.json" for name in contents}
        for name, data in contents.items():
            target = root / paths[name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        hashes = {
            name: hashlib.sha256(data).hexdigest() for name, data in contents.items()
        }
        return seal_manifest(
            {
                "manifest_version": 2,
                "state": "frozen",
                "dataset": {
                    "path": paths["dataset"],
                    "sha256": hashes["dataset"],
                },
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

    def test_schedule_planning_budget_manifest_and_activation_compose_fail_closed(
        self,
    ) -> None:
        self.assertEqual(len(self.jobs), 8)
        self.assertNotEqual(self.jobs[0].job_id, self.jobs[1].job_id)
        self.assertNotEqual(self.jobs[0].provider_seed, self.jobs[1].provider_seed)

        budget_rows = tuple(
            BudgetRow(
                job_id=job.job_id,
                route_id=job.identity.provider_route,
                phase="main",
                prompt_token_bound=512,
                max_output_tokens=job.identity.cap,
                pool_id="openai-direct",
                panel_id=job.identity.panel,
            )
            for job in self.jobs
        )
        budget_rates = (
            RouteRate(
                route_id="openai-direct::test-route",
                input_usd_per_million=Decimal("0.20"),
                output_usd_per_million=Decimal("1.20"),
                snapshot_sha256=_digest("route-price-snapshot"),
                basis="list",
            ),
        )
        planning_projection = project_maximum_exposure(budget_rows, budget_rates)
        self.assertEqual(planning_projection.maximum_exposure_usd, Decimal("0.0598016"))
        self.assertEqual(planning_projection.price_basis, "list")
        self.assertEqual(
            planning_projection.by_pool_usd,
            (("openai-direct", Decimal("0.0598016")),),
        )
        self.assertEqual(
            planning_projection.by_pool_panel_usd,
            (("openai-direct", "test-panel", Decimal("0.0598016")),),
        )
        self.assertEqual(
            validate_planning_budget_ceiling(
                budget_rows,
                budget_rates,
                pool_ceilings_usd={"openai-direct": Decimal("0.0598016")},
                panel_ceilings_usd={
                    ("openai-direct", "test-panel"): Decimal("0.0598016")
                },
            ),
            planning_projection,
        )
        with self.assertRaisesRegex(BudgetCeilingExceeded, "openai-direct"):
            validate_planning_budget_ceiling(
                budget_rows,
                budget_rates,
                pool_ceilings_usd={"tinker": Decimal("0.0598016")},
                panel_ceilings_usd={("tinker", "test-panel"): Decimal("0.0598016")},
            )

        required = ("single_submission", "termination_mapping")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._write_frozen_artifact_tree(root)
            verified = verify_manifest_files(manifest, approved_root=root)
            self.assertEqual(
                len(verified["evidence"]["sections"]),
                6,
            )
            evidence = self._activation_evidence(manifest, required)
            self.assertEqual(
                evaluate_activation(
                    manifest=manifest,
                    approved_root=root,
                    evidence=evidence,
                ).action,
                "activate",
            )

            for failed_field in ("budget_within_bound", "schedule_manifest_match"):
                failed = {**evidence, failed_field: False}
                decision = evaluate_activation(
                    manifest=manifest,
                    approved_root=root,
                    evidence=failed,
                )
                self.assertEqual(decision.action, "omit")
                self.assertIn(failed_field, decision.failed_predicates)

            arm_a_rows = [
                self._analysis_row(job)
                for job in self.jobs
                if job.identity.arm_key == "arm-a"
            ]
            report = analyze_confirmatory_rows(
                arm_a_rows,
                planned_rows=arm_a_rows,
                effort_order=["low", "high"],
                caps=[4096, 8192],
                bootstrap_resamples=10,
            )
            self.assertEqual(len(report["panels"]), 1)
            self.assertEqual(report["panels"][0]["arm_key"], "arm-a")

    @staticmethod
    def _activation_evidence(
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
                    "id": predicate_ids[0],
                    "status": "pass",
                    "evidence_sha256": _digest("single-submission-evidence"),
                },
                {
                    "id": predicate_ids[1],
                    "status": "pass",
                    "evidence_sha256": _digest("termination-mapping-evidence"),
                },
            ],
        }

    @staticmethod
    def _analysis_row(job: object) -> dict[str, object]:
        identity = job.identity
        correct = identity.effort == "high" or identity.cap == 8192
        return {
            **identity.as_dict(),
            "correct": correct,
            "extracted_answer_present": True,
            "extracted_answer": "1" if correct else "0",
            "finish_reason": "stop",
            "completion_tokens": 8,
        }


if __name__ == "__main__":
    unittest.main()
