from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from effort_atlas.activation import evaluate_activation
from tests.test_activation_policy_root import _passing_evidence, _write_frozen_root

REQUIRED = ("cap_semantics", "termination_mapping")


class ActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary_directory.name)
        self.manifest, _ = _write_frozen_root(self.root, REQUIRED)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def passing_evidence(self) -> dict[str, object]:
        return _passing_evidence(self.manifest, REQUIRED)

    def evaluate(self, evidence: object):
        return evaluate_activation(
            manifest=self.manifest,
            approved_root=self.root,
            evidence=evidence,
        )

    def test_each_structural_safeguard_fails_closed_to_omit(self) -> None:
        mutations = {
            "manifest_mismatch": ("manifest_sha256", "d" * 64),
            "activation_policy_mismatch": (
                "activation_policy_sha256",
                "d" * 64,
            ),
            "generation_retry_count": ("generation_retry_count", 1),
            "receipt_reconciled": ("receipt_reconciled", False),
            "budget_within_bound": ("budget_within_bound", False),
            "schedule_manifest_match": ("schedule_manifest_match", False),
            "served_route_match": ("served_route_match", False),
        }
        for expected_failure, (key, value) in mutations.items():
            evidence = self.passing_evidence()
            evidence[key] = value
            decision = self.evaluate(evidence)
            with self.subTest(expected_failure=expected_failure):
                self.assertEqual(decision.action, "omit")
                self.assertIn(expected_failure, decision.failed_predicates)

    def test_missing_failed_unknown_and_unreceipted_predicates_omit(self) -> None:
        cases: dict[str, list[dict[str, object]]] = {
            "predicate:termination_mapping:missing": [
                {"id": "cap_semantics", "status": "pass", "evidence_sha256": "b" * 64}
            ],
            "predicate:cap_semantics:fail": [
                {"id": "cap_semantics", "status": "fail", "evidence_sha256": "b" * 64},
                {
                    "id": "termination_mapping",
                    "status": "pass",
                    "evidence_sha256": "c" * 64,
                },
            ],
            "predicate:cap_semantics:unknown": [
                {
                    "id": "cap_semantics",
                    "status": "unknown",
                    "evidence_sha256": "b" * 64,
                },
                {
                    "id": "termination_mapping",
                    "status": "pass",
                    "evidence_sha256": "c" * 64,
                },
            ],
            "predicate:cap_semantics:missing_evidence": [
                {"id": "cap_semantics", "status": "pass", "evidence_sha256": None},
                {
                    "id": "termination_mapping",
                    "status": "pass",
                    "evidence_sha256": "c" * 64,
                },
            ],
        }
        for expected_failure, predicates in cases.items():
            evidence = self.passing_evidence()
            evidence["predicates"] = predicates
            decision = self.evaluate(evidence)
            with self.subTest(expected_failure=expected_failure):
                self.assertEqual(decision.action, "omit")
                self.assertIn(expected_failure, decision.failed_predicates)

    def test_malformed_or_extra_evidence_never_activates(self) -> None:
        cases: list[dict[str, object]] = []
        for key in tuple(self.passing_evidence()):
            mutation = self.passing_evidence()
            del mutation[key]
            cases.append(mutation)

        duplicate = self.passing_evidence()
        predicates = duplicate["predicates"]
        assert isinstance(predicates, list)
        duplicate["predicates"] = [
            *predicates,
            {"id": "cap_semantics", "status": "pass", "evidence_sha256": "d" * 64},
        ]
        cases.append(duplicate)

        extra = self.passing_evidence()
        extra["fallback_provider"] = "forbidden"
        cases.append(extra)

        bool_retry = self.passing_evidence()
        bool_retry["generation_retry_count"] = False
        cases.append(bool_retry)

        for index, evidence in enumerate(cases):
            decision = self.evaluate(evidence)
            with self.subTest(index=index):
                self.assertEqual(decision.action, "omit")
                self.assertTrue(decision.failed_predicates)

    def test_inputs_are_not_mutated(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        evidence = self.passing_evidence()
        original_manifest = copy.deepcopy(manifest)
        original_evidence = copy.deepcopy(evidence)

        evaluate_activation(
            manifest=manifest,
            approved_root=self.root,
            evidence=evidence,
        )

        self.assertEqual(manifest, original_manifest)
        self.assertEqual(evidence, original_evidence)

    def test_caller_cannot_activate_with_arbitrary_predicate_subset(self) -> None:
        evidence = self.passing_evidence()
        evidence["predicates"] = [
            {"id": "cap_semantics", "status": "pass", "evidence_sha256": "b" * 64}
        ]

        decision = self.evaluate(evidence)

        self.assertEqual(decision.action, "omit")
        self.assertIn(
            "predicate:termination_mapping:missing", decision.failed_predicates
        )

    def test_unknown_duplicate_and_malformed_statuses_omit(self) -> None:
        base_predicates = self.passing_evidence()["predicates"]
        assert isinstance(base_predicates, list)
        cases: list[list[dict[str, object]]] = [
            [
                *copy.deepcopy(base_predicates),
                {"id": "unfrozen", "status": "pass", "evidence_sha256": "d" * 64},
            ],
            [
                {"id": "cap_semantics", "status": "pass", "evidence_sha256": "b" * 64}
            ],
            [
                *copy.deepcopy(base_predicates),
                {"id": "cap_semantics", "status": "pass", "evidence_sha256": "d" * 64},
            ],
        ]
        for malformed_status in ([], {}, ["pass"], {"status": "pass"}):
            predicates = copy.deepcopy(base_predicates)
            predicates[0]["status"] = malformed_status
            cases.append(predicates)

        for index, predicates in enumerate(cases):
            evidence = self.passing_evidence()
            evidence["predicates"] = predicates
            with self.subTest(index=index):
                decision = self.evaluate(evidence)
                self.assertEqual(decision.action, "omit")
                self.assertTrue(decision.failed_predicates)
                if index >= 3:
                    self.assertIn(
                        "predicate:cap_semantics:invalid_status",
                        decision.failed_predicates,
                    )

    def test_invalid_manifest_and_evidence_use_only_terminal_actions(self) -> None:
        decisions = [
            evaluate_activation(
                manifest=object(),
                approved_root=self.root,
                evidence=self.passing_evidence(),
            ),
            self.evaluate(self.passing_evidence()),
            self.evaluate([]),
        ]

        self.assertLessEqual(
            {decision.action for decision in decisions}, {"activate", "omit"}
        )


if __name__ == "__main__":
    unittest.main()
