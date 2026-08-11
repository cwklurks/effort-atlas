from __future__ import annotations

import copy
import unittest

from effort_atlas.activation import evaluate_activation

DIGEST = "a" * 64


def passing_evidence() -> dict[str, object]:
    return {
        "manifest_sha256": DIGEST,
        "generation_retry_count": 0,
        "receipt_reconciled": True,
        "budget_within_bound": True,
        "schedule_manifest_match": True,
        "served_route_match": True,
        "predicates": [
            {"id": "cap_semantics", "status": "pass", "evidence_sha256": "b" * 64},
            {
                "id": "termination_mapping",
                "status": "pass",
                "evidence_sha256": "c" * 64,
            },
        ],
    }


class ActivationTests(unittest.TestCase):
    def test_all_required_evidence_activates_without_substitution_output(self) -> None:
        decision = evaluate_activation(
            required_predicate_ids=("cap_semantics", "termination_mapping"),
            expected_manifest_sha256=DIGEST,
            evidence=passing_evidence(),
        )
        self.assertEqual(decision.action, "activate")
        self.assertEqual(decision.failed_predicates, ())
        self.assertNotIn("substitut", repr(decision).lower())

    def test_each_structural_safeguard_fails_closed_to_omit(self) -> None:
        mutations = {
            "manifest_mismatch": ("manifest_sha256", "d" * 64),
            "generation_retry_count": ("generation_retry_count", 1),
            "receipt_reconciled": ("receipt_reconciled", False),
            "budget_within_bound": ("budget_within_bound", False),
            "schedule_manifest_match": ("schedule_manifest_match", False),
            "served_route_match": ("served_route_match", False),
        }
        for expected_failure, (key, value) in mutations.items():
            evidence = passing_evidence()
            evidence[key] = value
            decision = evaluate_activation(
                required_predicate_ids=("cap_semantics", "termination_mapping"),
                expected_manifest_sha256=DIGEST,
                evidence=evidence,
            )
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
            evidence = passing_evidence()
            evidence["predicates"] = predicates
            decision = evaluate_activation(
                required_predicate_ids=("cap_semantics", "termination_mapping"),
                expected_manifest_sha256=DIGEST,
                evidence=evidence,
            )
            with self.subTest(expected_failure=expected_failure):
                self.assertEqual(decision.action, "omit")
                self.assertIn(expected_failure, decision.failed_predicates)

    def test_malformed_or_extra_evidence_never_activates(self) -> None:
        cases: list[dict[str, object]] = []
        for key in tuple(passing_evidence()):
            mutation = passing_evidence()
            del mutation[key]
            cases.append(mutation)

        duplicate = passing_evidence()
        duplicate["predicates"] = [
            *duplicate["predicates"],  # type: ignore[list-item]
            {"id": "cap_semantics", "status": "pass", "evidence_sha256": "d" * 64},
        ]
        cases.append(duplicate)

        extra = passing_evidence()
        extra["fallback_provider"] = "forbidden"
        cases.append(extra)

        bool_retry = passing_evidence()
        bool_retry["generation_retry_count"] = False
        cases.append(bool_retry)

        for index, evidence in enumerate(cases):
            decision = evaluate_activation(
                required_predicate_ids=("cap_semantics", "termination_mapping"),
                expected_manifest_sha256=DIGEST,
                evidence=evidence,
            )
            with self.subTest(index=index):
                self.assertEqual(decision.action, "omit")
                self.assertTrue(decision.failed_predicates)

    def test_input_is_not_mutated(self) -> None:
        evidence = passing_evidence()
        original = copy.deepcopy(evidence)
        evaluate_activation(
            required_predicate_ids=("cap_semantics", "termination_mapping"),
            expected_manifest_sha256=DIGEST,
            evidence=evidence,
        )
        self.assertEqual(evidence, original)


if __name__ == "__main__":
    unittest.main()
