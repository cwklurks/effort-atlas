from __future__ import annotations

import json
import math
import unittest

from effort_atlas.reap_schedule import (
    IDENTITY_FIELDS,
    ReapScheduleIdentity,
    build_reap_schedule,
)


def planned_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "phase": "main",
        "panel": "panel-alpha",
        "model": "model-alpha",
        "provider_route": "provider/route-alpha",
        "item_id": "item-001",
        "effort": "high",
        "cap": 4096,
        "replicate": 1,
        "arm_key": "arm-a",
        "master_seed": 20260722,
    }
    row.update(overrides)
    return row


class ReapScheduleIdentityTests(unittest.TestCase):
    def test_phase_and_master_seed_are_required_identity_inputs(self) -> None:
        baseline = {
            **planned_row(),
            "phase": "main",
            "master_seed": 20260722,
        }
        identity = ReapScheduleIdentity.from_mapping(baseline)
        different_phase = ReapScheduleIdentity.from_mapping(
            {**baseline, "phase": "smoke"}
        )
        different_master_seed = ReapScheduleIdentity.from_mapping(
            {**baseline, "master_seed": 20260723}
        )

        self.assertNotEqual(identity.job_id, different_phase.job_id)
        self.assertNotEqual(identity.provider_seed, different_phase.provider_seed)
        self.assertNotEqual(identity.job_id, different_master_seed.job_id)
        self.assertNotEqual(identity.provider_seed, different_master_seed.provider_seed)

    def test_canonical_identity_and_derived_values_are_deterministic(self) -> None:
        first = ReapScheduleIdentity.from_mapping(planned_row())
        reordered = {key: planned_row()[key] for key in reversed(IDENTITY_FIELDS)}
        second = ReapScheduleIdentity.from_mapping(reordered)

        self.assertEqual(first.canonical_json(), second.canonical_json())
        self.assertEqual(first.job_id, second.job_id)
        self.assertEqual(first.provider_seed, second.provider_seed)
        self.assertEqual(
            first.canonical_json(),
            '{"arm_key":"arm-a","cap":4096,"effort":"high",'
            '"item_id":"item-001","master_seed":20260722,'
            '"model":"model-alpha","panel":"panel-alpha","phase":"main",'
            '"provider_route":"provider/route-alpha",'
            '"replicate":1}',
        )
        self.assertEqual(
            first.job_id,
            "04cc07fb703d91a0b5ce5cb47d267ffedbb716159d73080e31daa445d3e22fe7",
        )
        self.assertEqual(first.provider_seed, 1461308915)
        self.assertEqual(
            json.loads(first.canonical_json()),
            {field: planned_row()[field] for field in IDENTITY_FIELDS},
        )
        self.assertRegex(first.job_id, r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(first.provider_seed, 0)
        self.assertLessEqual(first.provider_seed, 2**31 - 1)

    def test_arm_key_prevents_otherwise_identical_arms_from_colliding(self) -> None:
        arm_a = ReapScheduleIdentity.from_mapping(planned_row(arm_key="arm-a"))
        arm_b = ReapScheduleIdentity.from_mapping(planned_row(arm_key="arm-b"))

        self.assertNotEqual(arm_a.job_id, arm_b.job_id)
        self.assertNotEqual(arm_a.canonical_json(), arm_b.canonical_json())

        # This directly guards the failure mode: without arm_key, the two
        # canonical identities would be byte-for-byte identical.
        without_arm_a = arm_a.as_dict()
        without_arm_b = arm_b.as_dict()
        without_arm_a.pop("arm_key")
        without_arm_b.pop("arm_key")
        self.assertEqual(
            json.dumps(without_arm_a, sort_keys=True, separators=(",", ":")),
            json.dumps(without_arm_b, sort_keys=True, separators=(",", ":")),
        )

    def test_every_required_field_participates_in_job_identity(self) -> None:
        baseline = ReapScheduleIdentity.from_mapping(planned_row())
        alternatives = {
            "phase": "smoke",
            "panel": "panel-beta",
            "model": "model-beta",
            "provider_route": "provider/route-beta",
            "item_id": "item-002",
            "effort": "medium",
            "cap": 8192,
            "replicate": 2,
            "arm_key": "arm-b",
            "master_seed": 20260723,
        }

        for field, value in alternatives.items():
            with self.subTest(field=field):
                changed = ReapScheduleIdentity.from_mapping(
                    planned_row(**{field: value})
                )
                self.assertNotEqual(baseline.job_id, changed.job_id)

    def test_missing_unknown_and_blank_fields_are_rejected(self) -> None:
        for field in IDENTITY_FIELDS:
            with self.subTest(missing=field):
                row = planned_row()
                row.pop(field)
                with self.assertRaisesRegex(ValueError, "missing"):
                    ReapScheduleIdentity.from_mapping(row)

        with self.assertRaisesRegex(ValueError, "unknown"):
            ReapScheduleIdentity.from_mapping({**planned_row(), "unexpected": "x"})

        for field in (
            "phase",
            "panel",
            "model",
            "provider_route",
            "item_id",
            "arm_key",
        ):
            with self.subTest(blank=field), self.assertRaisesRegex(ValueError, field):
                ReapScheduleIdentity.from_mapping(planned_row(**{field: "  "}))

    def test_direct_construction_cannot_bypass_validation(self) -> None:
        row = planned_row(arm_key="")
        with self.assertRaisesRegex(ValueError, "arm_key"):
            ReapScheduleIdentity(**row)  # type: ignore[arg-type]

    def test_cap_and_replicate_require_positive_non_boolean_integers(self) -> None:
        for field in ("cap", "replicate"):
            for invalid in (True, False, 0, -1, 1.0, "1"):
                with (
                    self.subTest(field=field, invalid=invalid),
                    self.assertRaisesRegex(ValueError, field),
                ):
                    ReapScheduleIdentity.from_mapping(planned_row(**{field: invalid}))

    def test_master_seed_requires_a_nonnegative_non_boolean_integer(self) -> None:
        for valid in (0, 20260722):
            self.assertEqual(
                ReapScheduleIdentity.from_mapping(
                    planned_row(master_seed=valid)
                ).master_seed,
                valid,
            )
        for invalid in (True, False, -1, 1.0, "1"):
            with (
                self.subTest(invalid=invalid),
                self.assertRaisesRegex(ValueError, "master_seed"),
            ):
                ReapScheduleIdentity.from_mapping(planned_row(master_seed=invalid))

    def test_effort_supports_labels_or_finite_numbers_but_not_booleans(self) -> None:
        for effort in ("medium", 0, 0.7, 0.99):
            with self.subTest(valid=effort):
                self.assertEqual(
                    ReapScheduleIdentity.from_mapping(
                        planned_row(effort=effort)
                    ).effort,
                    effort,
                )

        for effort in (True, False, "", "  ", math.nan, math.inf, None):
            with (
                self.subTest(invalid=effort),
                self.assertRaisesRegex(ValueError, "effort"),
            ):
                ReapScheduleIdentity.from_mapping(planned_row(effort=effort))

    def test_semantically_equal_numeric_efforts_have_one_canonical_identity(
        self,
    ) -> None:
        integer = ReapScheduleIdentity.from_mapping(planned_row(effort=0))
        floating = ReapScheduleIdentity.from_mapping(planned_row(effort=0.0))

        self.assertIsInstance(integer.effort, float)
        self.assertEqual(integer.canonical_json(), floating.canonical_json())
        self.assertEqual(integer.job_id, floating.job_id)
        self.assertEqual(integer.provider_seed, floating.provider_seed)


class ReapScheduleBuilderTests(unittest.TestCase):
    def test_builder_output_is_independent_of_input_order(self) -> None:
        rows = [
            planned_row(item_id="item-002", effort=0.7, arm_key="arm-b"),
            planned_row(item_id="item-001", effort="high", arm_key="arm-a"),
            planned_row(item_id="item-001", effort=0.99, arm_key="arm-c", replicate=2),
        ]

        forward = build_reap_schedule(rows)
        reverse = build_reap_schedule(reversed(rows))

        self.assertEqual(forward, reverse)
        self.assertEqual(
            [job.identity.canonical_json() for job in forward],
            sorted(job.identity.canonical_json() for job in forward),
        )
        self.assertEqual(len({job.job_id for job in forward}), len(forward))

    def test_builder_rejects_duplicate_canonical_identity(self) -> None:
        row = planned_row()
        reordered = {key: row[key] for key in reversed(tuple(row))}

        with self.assertRaisesRegex(ValueError, "Duplicate canonical identity"):
            build_reap_schedule([row, reordered])

    def test_builder_rejects_distinct_jobs_with_same_provider_seed(self) -> None:
        first = planned_row(item_id="item-65150")
        second = planned_row(item_id="item-88099")
        self.assertNotEqual(
            ReapScheduleIdentity.from_mapping(first).job_id,
            ReapScheduleIdentity.from_mapping(second).job_id,
        )
        self.assertEqual(
            ReapScheduleIdentity.from_mapping(first).provider_seed,
            ReapScheduleIdentity.from_mapping(second).provider_seed,
        )

        with self.assertRaisesRegex(ValueError, "provider seed collision"):
            build_reap_schedule([first, second])


if __name__ == "__main__":
    unittest.main()
