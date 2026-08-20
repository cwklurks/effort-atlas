from __future__ import annotations

import math
import unittest

from effort_atlas.power_simulation import (
    SimulationProvenanceError,
    canonical_json,
    run_deterministic_simulation,
)

SOURCE_SHA256 = "a" * 64


def deterministic_fixture_simulator(*, scenario_parameters, seed, monte_carlo_counts):
    """A deterministic fixture, not a statistical power model."""
    return {
        "seed_echo": seed,
        "scenario_name": scenario_parameters["scenario_name"],
        "draws": monte_carlo_counts["replicates"],
        "summary": {"value": scenario_parameters["effect_size"]},
    }


def valid_kwargs():
    return {
        "scenario_parameters": {"scenario_name": "fixture", "effect_size": 0.1},
        "assumptions": {"outcome_model": "declared_fixture_only"},
        "seed": 20260722,
        "monte_carlo_counts": {"replicates": 100, "bootstrap_resamples": 50},
        "simulator_identifier": "tests.deterministic_fixture_simulator",
        "simulator_version": "1.0.0",
        "simulator_source_sha256": SOURCE_SHA256,
    }


class PowerSimulationProvenanceTests(unittest.TestCase):
    def test_identical_declared_inputs_and_outputs_reproduce_exact_record(self):
        first = run_deterministic_simulation(
            deterministic_fixture_simulator, **valid_kwargs()
        )
        second = run_deterministic_simulation(
            deterministic_fixture_simulator, **valid_kwargs()
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first["provenance_sha256"], first["provenance"]["provenance_sha256"]
        )
        self.assertEqual(first["provenance"]["seed"], 20260722)
        self.assertEqual(first["output"]["seed_echo"], 20260722)

    def test_each_declared_identity_input_changes_provenance_hash(self):
        baseline = run_deterministic_simulation(
            deterministic_fixture_simulator, **valid_kwargs()
        )
        mutations = (
            {"seed": 7},
            {"scenario_parameters": {"scenario_name": "changed", "effect_size": 0.1}},
            {"simulator_version": "1.0.1"},
            {"simulator_source_sha256": "b" * 64},
        )

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                kwargs = {**valid_kwargs(), **mutation}
                actual = run_deterministic_simulation(
                    deterministic_fixture_simulator, **kwargs
                )
                self.assertNotEqual(
                    actual["provenance_sha256"], baseline["provenance_sha256"]
                )

    def test_canonical_json_has_stable_key_order_and_rejects_nonfinite_values(self):
        self.assertEqual(canonical_json({"z": 1, "a": [2, 3]}), '{"a":[2,3],"z":1}')
        with self.assertRaisesRegex(SimulationProvenanceError, "non-finite"):
            canonical_json({"value": math.nan})

    def test_rejects_missing_or_placeholder_assumptions(self):
        for assumptions in ({}, {"outcome_model": "TBD"}, {"outcome_model": ""}):
            with (
                self.subTest(assumptions=assumptions),
                self.assertRaisesRegex(
                    SimulationProvenanceError, "assumptions|placeholder"
                ),
            ):
                run_deterministic_simulation(
                    deterministic_fixture_simulator,
                    **{**valid_kwargs(), "assumptions": assumptions},
                )

    def test_rejects_booleans_as_seed_or_monte_carlo_counts(self):
        for mutation in (
            {"seed": True},
            {"monte_carlo_counts": {"replicates": True}},
            {"monte_carlo_counts": {"replicates": 0}},
        ):
            with (
                self.subTest(mutation=mutation),
                self.assertRaisesRegex(SimulationProvenanceError, "integer|positive"),
            ):
                run_deterministic_simulation(
                    deterministic_fixture_simulator, **{**valid_kwargs(), **mutation}
                )

    def test_rejects_missing_simulator_metadata_and_bad_source_hash(self):
        for mutation in (
            {"simulator_identifier": ""},
            {"simulator_version": "PENDING"},
            {"simulator_source_sha256": "not-a-hash"},
        ):
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(SimulationProvenanceError),
            ):
                run_deterministic_simulation(
                    deterministic_fixture_simulator, **{**valid_kwargs(), **mutation}
                )

    def test_rejects_simulator_outputs_that_are_nonfinite_or_not_json_objects(self):
        for simulator in (
            lambda **_: {"value": math.inf},
            lambda **_: ["not", "an", "object"],
        ):
            with (
                self.subTest(simulator=simulator),
                self.assertRaises(SimulationProvenanceError),
            ):
                run_deterministic_simulation(simulator, **valid_kwargs())

    def test_nested_inputs_and_output_are_detached_from_caller_mutation(self):
        scenario_parameters = {
            "scenario_name": "nested-fixture",
            "effect_size": 0.1,
            "design": {"caps": [4096, 16384]},
        }
        assumptions = {
            "outcome_model": "declared_fixture_only",
            "nested": {"labels": ["before"]},
        }
        simulator_output = {"summary": {"values": [1, 2]}}

        def nested_output_simulator(**_):
            return simulator_output

        record = run_deterministic_simulation(
            nested_output_simulator,
            **{
                **valid_kwargs(),
                "scenario_parameters": scenario_parameters,
                "assumptions": assumptions,
            },
        )
        expected_provenance = canonical_json(record["provenance"])
        expected_output = canonical_json(record["output"])

        scenario_parameters["design"]["caps"].append(32768)
        assumptions["nested"]["labels"].append("after")
        simulator_output["summary"]["values"].append(3)
        record["output"]["summary"]["values"].append(4)

        self.assertEqual(canonical_json(record["provenance"]), expected_provenance)
        self.assertNotEqual(canonical_json(record["output"]), expected_output)
        self.assertEqual(
            record["provenance_sha256"],
            record["provenance"]["provenance_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
