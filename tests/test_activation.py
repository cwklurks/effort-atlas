from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest

from effort_atlas.activation import (
    ActivationPolicy,
    ActivationPolicyInvalid,
    evaluate_activation,
)

DIGEST = "a" * 64
REQUIRED = ("cap_semantics", "termination_mapping")


def policy_digest(predicate_ids: tuple[str, ...], manifest_sha256: str = DIGEST) -> str:
    payload = {
        "expected_manifest_sha256": manifest_sha256,
        "policy_version": 1,
        "predicate_ids": list(predicate_ids),
        "substitution_allowed": False,
        "terminal_actions": ["activate", "omit"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


POLICY = ActivationPolicy(
    predicate_ids=REQUIRED,
    expected_manifest_sha256=DIGEST,
    policy_sha256=policy_digest(REQUIRED),
)


def passing_evidence() -> dict[str, object]:
    return {
        "manifest_sha256": DIGEST,
        "activation_policy_sha256": POLICY.policy_sha256,
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
            policy=POLICY,
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
                policy=POLICY,
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
                policy=POLICY,
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
                policy=POLICY,
                evidence=evidence,
            )
            with self.subTest(index=index):
                self.assertEqual(decision.action, "omit")
                self.assertTrue(decision.failed_predicates)

    def test_input_is_not_mutated(self) -> None:
        evidence = passing_evidence()
        original = copy.deepcopy(evidence)
        evaluate_activation(
            policy=POLICY,
            evidence=evidence,
        )
        self.assertEqual(evidence, original)

    def test_caller_cannot_activate_with_arbitrary_predicate_subset(self) -> None:
        with self.assertRaises(ActivationPolicyInvalid) as raised:
            ActivationPolicy(
                predicate_ids=("cap_semantics",),
                expected_manifest_sha256=DIGEST,
                policy_sha256=POLICY.policy_sha256,
            )

        self.assertEqual(raised.exception.reason, "policy_digest_mismatch")
        self.assertNotIn(
            "required_predicate_ids", inspect.signature(evaluate_activation).parameters
        )

    def test_policy_digest_is_bound_to_manifest_and_evidence(self) -> None:
        wrong_policy = passing_evidence()
        wrong_policy["activation_policy_sha256"] = "d" * 64
        self.assertEqual(
            evaluate_activation(policy=POLICY, evidence=wrong_policy).action,
            "omit",
        )

        wrong_manifest = passing_evidence()
        wrong_manifest["manifest_sha256"] = "e" * 64
        self.assertEqual(
            evaluate_activation(policy=POLICY, evidence=wrong_manifest).action,
            "omit",
        )

        with self.assertRaises(ActivationPolicyInvalid) as raised:
            ActivationPolicy(
                predicate_ids=REQUIRED,
                expected_manifest_sha256="f" * 64,
                policy_sha256=POLICY.policy_sha256,
            )
        self.assertEqual(raised.exception.reason, "policy_digest_mismatch")

    def test_unknown_missing_duplicate_and_malformed_statuses_omit(self) -> None:
        cases: list[list[dict[str, object]]] = []

        unknown = passing_evidence()["predicates"]
        assert isinstance(unknown, list)
        cases.append(
            [
                *unknown,
                {"id": "unfrozen", "status": "pass", "evidence_sha256": "d" * 64},
            ]
        )
        cases.append(
            [{"id": "cap_semantics", "status": "pass", "evidence_sha256": "b" * 64}]
        )
        duplicate = list(unknown)
        duplicate.append(
            {"id": "cap_semantics", "status": "pass", "evidence_sha256": "d" * 64}
        )
        cases.append(duplicate)
        for malformed_status in ([], {}, ["pass"], {"status": "pass"}):
            predicates = copy.deepcopy(unknown)
            predicates[0]["status"] = malformed_status
            cases.append(predicates)

        for index, predicates in enumerate(cases):
            evidence = passing_evidence()
            evidence["predicates"] = predicates
            with self.subTest(index=index):
                decision = evaluate_activation(policy=POLICY, evidence=evidence)
                self.assertEqual(decision.action, "omit")
                self.assertTrue(decision.failed_predicates)
                if index >= 3:
                    self.assertIn(
                        "predicate:cap_semantics:invalid_status",
                        decision.failed_predicates,
                    )

    def test_invalid_policy_input_and_all_decisions_use_only_terminal_actions(
        self,
    ) -> None:
        decisions = [
            evaluate_activation(policy=object(), evidence=passing_evidence()),
            evaluate_activation(policy=POLICY, evidence=passing_evidence()),
            evaluate_activation(policy=POLICY, evidence=[]),
        ]

        self.assertEqual(
            {decision.action for decision in decisions}, {"activate", "omit"}
        )


if __name__ == "__main__":
    unittest.main()
