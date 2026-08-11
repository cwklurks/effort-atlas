from __future__ import annotations

import unittest
from dataclasses import replace
from decimal import Decimal

from effort_atlas import reap_budget
from effort_atlas.reap_budget import (
    BudgetCeilingExceeded,
    BudgetProjection,
    BudgetRow,
    RouteRate,
    _validate_projected_planning_budget_ceiling,
    project_maximum_exposure,
    validate_planning_budget_ceiling,
    validate_planning_ceiling,
)


class ReapBudgetTests(unittest.TestCase):
    def test_public_budget_api_claims_planning_only_not_freeze_authority(self) -> None:
        public_symbols = {name for name in dir(reap_budget) if not name.startswith("_")}
        self.assertFalse(
            {name for name in public_symbols if "freeze" in name.casefold()}
        )
        for name in (
            "project_maximum_exposure",
            "validate_planning_ceiling",
            "validate_planning_budget_ceiling",
        ):
            with self.subTest(name=name):
                symbol = getattr(reap_budget, name)
                self.assertIn("planning", (symbol.__doc__ or "").casefold())
                self.assertNotIn("authoriz", (symbol.__doc__ or "").casefold())

    def test_planning_api_rejects_fabricated_zero_projection(self) -> None:
        fabricated = BudgetProjection(
            maximum_exposure_usd=Decimal(0),
            row_count=1,
            by_phase_usd=(("main", Decimal(0)),),
            by_price_basis_usd=(("list", Decimal(0)),),
            snapshot_sha256="a" * 64,
            by_pool_usd=(("pool", Decimal(0)),),
            by_pool_panel_usd=(("pool", "panel", Decimal(0)),),
            price_basis="list",
        )

        with self.assertRaisesRegex(TypeError, "does not accept BudgetProjection"):
            validate_planning_budget_ceiling(
                fabricated,
                (),
                pool_ceilings_usd={"pool": Decimal(0)},
                panel_ceilings_usd={("pool", "panel"): Decimal(0)},
            )

    def test_budget_rows_require_explicit_pool_and_panel_identity(self) -> None:
        with self.assertRaisesRegex(TypeError, "pool_id.*panel_id"):
            BudgetRow("job", "route", "main", 1, 1)
        for pool_id, panel_id in (("", "panel"), ("pool", ""), (" ", "panel")):
            with (
                self.subTest(pool_id=pool_id, panel_id=panel_id),
                self.assertRaises(ValueError),
            ):
                BudgetRow("job", "route", "main", 1, 1, pool_id, panel_id)

    def test_budget_rows_reject_reserved_scope_placeholders(self) -> None:
        placeholder_values = (
            "unscoped",
            " UNSCOPED ",
            "tbd",
            " Pending ",
            "UNKNOWN",
            "[__]",
            "__",
            "[DECIDE]",
        )
        for placeholder in placeholder_values:
            for pool_id, panel_id in (
                (placeholder, "real-panel"),
                ("real-provider-pool", placeholder),
            ):
                with (
                    self.subTest(pool_id=pool_id, panel_id=panel_id),
                    self.assertRaisesRegex(ValueError, "placeholder"),
                ):
                    BudgetRow("job", "route", "main", 1, 1, pool_id, panel_id)

        row = BudgetRow(
            "job",
            "route",
            "main",
            1,
            1,
            "openai-direct",
            "hmmt-2026-terra",
        )
        self.assertEqual(row.pool_id, "openai-direct")
        self.assertEqual(row.panel_id, "hmmt-2026-terra")

    def test_planning_validator_rejects_placeholder_scope_in_forged_projection(
        self,
    ) -> None:
        projection = BudgetProjection(
            maximum_exposure_usd=Decimal(1),
            row_count=1,
            by_phase_usd=(("main", Decimal(1)),),
            by_price_basis_usd=(("list", Decimal(1)),),
            snapshot_sha256="a" * 64,
            by_pool_usd=((" UnScOpEd ", Decimal(1)),),
            by_pool_panel_usd=((" UnScOpEd ", "real-panel", Decimal(1)),),
            price_basis="list",
        )

        with self.assertRaisesRegex(ValueError, "placeholder"):
            _validate_projected_planning_budget_ceiling(
                projection,
                pool_ceilings_usd={"real-pool": Decimal(1)},
                panel_ceilings_usd={("real-pool", "real-panel"): Decimal(1)},
            )

    def test_planning_validator_rejects_placeholder_scope_in_ceiling_maps(self) -> None:
        projection = project_maximum_exposure(
            (
                BudgetRow(
                    "job", "route", "main", 0, 1_000_000, "real-pool", "real-panel"
                ),
            ),
            (RouteRate("route", Decimal(0), Decimal(1), "a" * 64, "list"),),
        )

        invalid_maps = (
            (
                {"real-pool": Decimal(1), "UNKNOWN": Decimal(1)},
                {("real-pool", "real-panel"): Decimal(1)},
            ),
            (
                {"real-pool": Decimal(1)},
                {
                    ("real-pool", "real-panel"): Decimal(1),
                    ("real-pool", " [DECIDE] "): Decimal(1),
                },
            ),
        )
        for pool_ceilings, panel_ceilings in invalid_maps:
            with (
                self.subTest(
                    pool_ceilings=pool_ceilings, panel_ceilings=panel_ceilings
                ),
                self.assertRaisesRegex(ValueError, "placeholder"),
            ):
                _validate_projected_planning_budget_ceiling(
                    projection,
                    pool_ceilings_usd=pool_ceilings,
                    panel_ceilings_usd=panel_ceilings,
                )

    def test_planning_validator_rejects_empty_or_malformed_projection_structure(
        self,
    ) -> None:
        valid = project_maximum_exposure(
            (BudgetRow("job", "route", "main", 0, 1_000_000, "pool", "panel"),),
            (RouteRate("route", Decimal(0), Decimal(1), "a" * 64, "list"),),
        )
        mutations = (
            ("row_count", replace(valid, row_count=0)),
            ("row_count", replace(valid, row_count=True)),
            (
                "maximum_exposure_usd",
                replace(valid, maximum_exposure_usd=Decimal("NaN")),
            ),
            (
                "maximum_exposure_usd",
                replace(valid, maximum_exposure_usd=Decimal("-0.01")),
            ),
            ("snapshot_sha256", replace(valid, snapshot_sha256="bad")),
            ("price_basis", replace(valid, price_basis="guess")),
            ("by_phase_usd", replace(valid, by_phase_usd=())),
            ("by_price_basis_usd", replace(valid, by_price_basis_usd=())),
            ("by_pool_usd", replace(valid, by_pool_usd=())),
            ("by_pool_panel_usd", replace(valid, by_pool_panel_usd=())),
            ("by_phase_usd", replace(valid, by_phase_usd=[])),  # type: ignore[arg-type]
            (
                "by_pool_panel_usd",
                replace(valid, by_pool_panel_usd=(("pool", "panel"),)),  # type: ignore[arg-type]
            ),
        )
        for expected, projection in mutations:
            with (
                self.subTest(expected=expected),
                self.assertRaisesRegex(ValueError, expected),
            ):
                _validate_projected_planning_budget_ceiling(
                    projection,
                    pool_ceilings_usd={"pool": Decimal(1)},
                    panel_ceilings_usd={("pool", "panel"): Decimal(1)},
                )

    def test_planning_validator_rejects_non_decimal_and_nonfinite_aggregate_exposure(
        self,
    ) -> None:
        valid = project_maximum_exposure(
            (BudgetRow("job", "route", "main", 0, 1_000_000, "pool", "panel"),),
            (RouteRate("route", Decimal(0), Decimal(1), "a" * 64, "list"),),
        )
        mutations = (
            replace(valid, by_phase_usd=(("main", 1),)),
            replace(valid, by_price_basis_usd=(("list", Decimal("Infinity")),)),
            replace(valid, by_pool_usd=(("pool", Decimal("-0.01")),)),
            replace(
                valid,
                by_pool_panel_usd=(("pool", "panel", Decimal("NaN")),),
            ),
        )
        for projection in mutations:
            with (
                self.subTest(projection=projection),
                self.assertRaisesRegex(ValueError, "finite nonnegative Decimal"),
            ):
                _validate_projected_planning_budget_ceiling(
                    projection,
                    pool_ceilings_usd={"pool": Decimal(1)},
                    panel_ceilings_usd={("pool", "panel"): Decimal(1)},
                )

    def test_planning_validator_rejects_duplicate_or_unreconciled_aggregates(
        self,
    ) -> None:
        valid = project_maximum_exposure(
            (BudgetRow("job", "route", "main", 0, 1_000_000, "pool", "panel"),),
            (RouteRate("route", Decimal(0), Decimal(1), "a" * 64, "list"),),
        )
        mutations = (
            ("duplicate", replace(valid, by_phase_usd=(("main", Decimal("0.5")),) * 2)),
            (
                "duplicate",
                replace(
                    valid,
                    by_price_basis_usd=(("list", Decimal("0.5")),) * 2,
                ),
            ),
            ("duplicate", replace(valid, by_pool_usd=(("pool", Decimal("0.5")),) * 2)),
            (
                "duplicate",
                replace(
                    valid,
                    by_pool_panel_usd=(("pool", "panel", Decimal("0.5")),) * 2,
                ),
            ),
            ("does not sum", replace(valid, by_phase_usd=(("main", Decimal("0.5")),))),
            (
                "does not sum",
                replace(valid, by_price_basis_usd=(("list", Decimal("0.5")),)),
            ),
            (
                "price_basis",
                replace(valid, by_price_basis_usd=(("discount", Decimal(1)),)),
            ),
            ("does not sum", replace(valid, by_pool_usd=(("pool", Decimal("0.5")),))),
            (
                "does not sum",
                replace(
                    valid,
                    by_pool_panel_usd=(("pool", "panel", Decimal("0.5")),),
                ),
            ),
            (
                "pool identities",
                replace(
                    valid,
                    by_pool_panel_usd=(("other-pool", "panel", Decimal(1)),),
                ),
            ),
            (
                "panel sum",
                replace(
                    valid,
                    by_pool_usd=(
                        ("pool-a", Decimal("0.5")),
                        ("pool-b", Decimal("0.5")),
                    ),
                    by_pool_panel_usd=(
                        ("pool-a", "panel-a", Decimal("0.25")),
                        ("pool-b", "panel-b", Decimal("0.75")),
                    ),
                ),
            ),
        )
        for expected, projection in mutations:
            with (
                self.subTest(expected=expected),
                self.assertRaisesRegex(ValueError, expected),
            ):
                _validate_projected_planning_budget_ceiling(
                    projection,
                    pool_ceilings_usd={
                        pool_id: Decimal(1)
                        for pool_id, _exposure in projection.by_pool_usd
                    },
                    panel_ceilings_usd={
                        (pool_id, panel_id): Decimal(1)
                        for pool_id, panel_id, _exposure in projection.by_pool_panel_usd
                    },
                )

    def test_planning_validator_requires_exact_ceiling_scope_sets(self) -> None:
        rows = (BudgetRow("job", "route", "main", 0, 1_000_000, "pool", "panel"),)
        rates = (RouteRate("route", Decimal(0), Decimal(1), "a" * 64, "list"),)
        mutations = (
            ({}, {("pool", "panel"): Decimal(1)}),
            (
                {"pool": Decimal(1), "extra-pool": Decimal(1)},
                {("pool", "panel"): Decimal(1)},
            ),
            ({"pool": Decimal(1)}, {}),
            (
                {"pool": Decimal(1)},
                {
                    ("pool", "panel"): Decimal(1),
                    ("pool", "extra-panel"): Decimal(1),
                },
            ),
        )
        for pool_ceilings, panel_ceilings in mutations:
            with (
                self.subTest(
                    pool_ceilings=pool_ceilings, panel_ceilings=panel_ceilings
                ),
                self.assertRaisesRegex(BudgetCeilingExceeded, "scope"),
            ):
                validate_planning_budget_ceiling(
                    rows,
                    rates,
                    pool_ceilings_usd=pool_ceilings,
                    panel_ceilings_usd=panel_ceilings,
                )

    def test_zero_cost_inputs_return_planning_projection_not_authorization(
        self,
    ) -> None:
        rows = (BudgetRow("job", "free-route", "main", 0, 1, "pool", "panel"),)
        rates = (RouteRate("free-route", Decimal(0), Decimal(0), "a" * 64, "list"),)
        projection = project_maximum_exposure(rows, rates)

        self.assertEqual(projection.maximum_exposure_usd, Decimal(0))
        self.assertEqual(projection.by_pool_usd, (("pool", Decimal(0)),))
        result = validate_planning_budget_ceiling(
            rows,
            rates,
            pool_ceilings_usd={"pool": Decimal(0)},
            panel_ceilings_usd={("pool", "panel"): Decimal(0)},
        )
        self.assertEqual(result, projection)
        self.assertIs(type(result), BudgetProjection)
        self.assertFalse(
            {
                field
                for field in result.__dataclass_fields__
                if "freeze" in field.casefold() or "authoriz" in field.casefold()
            }
        )

    def test_maximum_exposure_sums_every_rows_prompt_and_cap(self) -> None:
        rows = (
            BudgetRow("job-main", "route-a", "main", 100, 200, "pool", "panel"),
            BudgetRow("job-smoke", "route-a", "smoke", 50, 75, "pool", "panel"),
        )
        rates = (
            RouteRate(
                "route-a",
                Decimal(2),
                Decimal(12),
                "a" * 64,
                "list",
            ),
        )

        projection = project_maximum_exposure(rows, rates)

        expected_main = (Decimal(100) * 2 + Decimal(200) * 12) / Decimal(1_000_000)
        expected_smoke = (Decimal(50) * 2 + Decimal(75) * 12) / Decimal(1_000_000)
        self.assertEqual(
            projection.maximum_exposure_usd, expected_main + expected_smoke
        )
        self.assertEqual(
            projection.by_phase_usd,
            (("main", expected_main), ("smoke", expected_smoke)),
        )
        self.assertEqual(projection.row_count, 2)

    def test_exact_ceiling_passes_and_any_excess_refuses(self) -> None:
        projection = project_maximum_exposure(
            (BudgetRow("job", "route", "main", 1_000_000, 1_000_000, "pool", "panel"),),
            (RouteRate("route", Decimal(2), Decimal(12), "b" * 64, "list"),),
        )
        self.assertEqual(projection.maximum_exposure_usd, Decimal(14))
        self.assertEqual(validate_planning_ceiling(projection, Decimal(14)), projection)
        with self.assertRaisesRegex(BudgetCeilingExceeded, "14"):
            validate_planning_ceiling(projection, Decimal("13.999999"))

    def test_missing_route_rate_duplicate_ids_and_malformed_values_fail(self) -> None:
        valid_row = BudgetRow("job", "route", "main", 1, 1, "pool", "panel")
        valid_rate = RouteRate("route", Decimal(1), Decimal(1), "c" * 64, "list")

        with self.assertRaisesRegex(ValueError, "no price"):
            project_maximum_exposure((valid_row,), ())
        with self.assertRaisesRegex(ValueError, "Duplicate job_id"):
            project_maximum_exposure((valid_row, valid_row), (valid_rate,))
        with self.assertRaisesRegex(ValueError, "Duplicate route_id and basis"):
            project_maximum_exposure((valid_row,), (valid_rate, valid_rate))

        invalid_rows = (
            {"prompt_token_bound": True},
            {"prompt_token_bound": -1},
            {"max_output_tokens": True},
            {"max_output_tokens": 0},
        )
        for mutation in invalid_rows:
            values = {
                "job_id": "job",
                "route_id": "route",
                "phase": "main",
                "prompt_token_bound": 1,
                "max_output_tokens": 1,
                "pool_id": "pool",
                "panel_id": "panel",
                **mutation,
            }
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                BudgetRow(**values)  # type: ignore[arg-type]

    def test_rates_are_explicit_finite_nonnegative_decimals_with_provenance(
        self,
    ) -> None:
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-0.01")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RouteRate("route", value, Decimal(1), "d" * 64, "list")
        with self.assertRaisesRegex(ValueError, "snapshot"):
            RouteRate("route", Decimal(1), Decimal(1), "bad", "list")
        with self.assertRaisesRegex(ValueError, "basis"):
            RouteRate("route", Decimal(1), Decimal(1), "d" * 64, "guess")

    def test_projection_reports_list_and_discount_bases_separately(self) -> None:
        rows = (
            BudgetRow("list-job", "list-route", "main", 0, 1_000_000, "pool", "panel"),
            BudgetRow(
                "discount-job", "discount-route", "main", 0, 1_000_000, "pool", "panel"
            ),
        )
        rates = (
            RouteRate("list-route", Decimal(0), Decimal(10), "e" * 64, "discount"),
            RouteRate("list-route", Decimal(0), Decimal(20), "e" * 64, "list"),
            RouteRate(
                "discount-route",
                Decimal(0),
                Decimal(5),
                "e" * 64,
                "discount",
            ),
            RouteRate("discount-route", Decimal(0), Decimal(10), "e" * 64, "list"),
        )
        projection = project_maximum_exposure(rows, rates)
        self.assertEqual(
            projection.by_price_basis_usd,
            (("list", Decimal(30)),),
        )

    def test_projection_defaults_to_list_and_preserves_snapshot_pool_panel_identity(
        self,
    ) -> None:
        row = BudgetRow("job", "route", "main", 0, 1_000_000, "tinker", "p1")
        rates = (
            RouteRate("route", Decimal(0), Decimal(5), "e" * 64, "discount"),
            RouteRate("route", Decimal(0), Decimal(10), "e" * 64, "list"),
        )

        projection = project_maximum_exposure((row,), rates)

        self.assertEqual(projection.maximum_exposure_usd, Decimal(10))
        self.assertEqual(projection.snapshot_sha256, "e" * 64)
        self.assertEqual(projection.by_pool_panel_usd, (("tinker", "p1", Decimal(10)),))

    def test_mixed_snapshot_digests_and_missing_list_rates_fail_closed(self) -> None:
        row = BudgetRow("job", "route", "main", 0, 1, "pool", "panel")
        with self.assertRaisesRegex(ValueError, "snapshot"):
            project_maximum_exposure(
                (row,),
                (
                    RouteRate("route", Decimal(0), Decimal(1), "e" * 64, "list"),
                    RouteRate("other", Decimal(0), Decimal(1), "f" * 64, "list"),
                ),
            )
        with self.assertRaisesRegex(ValueError, "list"):
            project_maximum_exposure(
                (row,),
                (RouteRate("route", Decimal(0), Decimal(1), "e" * 64, "discount"),),
            )

    def test_planning_validator_checks_panel_pool_ceilings_and_discount_policy(
        self,
    ) -> None:
        row = BudgetRow("job", "route", "main", 0, 1_000_000, "pool", "panel")
        list_rates = (RouteRate("route", Decimal(0), Decimal(10), "e" * 64, "list"),)
        list_projection = project_maximum_exposure((row,), list_rates)
        self.assertEqual(
            validate_planning_budget_ceiling(
                (row,),
                list_rates,
                pool_ceilings_usd={"pool": Decimal(10)},
                panel_ceilings_usd={("pool", "panel"): Decimal(10)},
            ),
            list_projection,
        )
        with self.assertRaisesRegex(BudgetCeilingExceeded, "panel"):
            validate_planning_budget_ceiling(
                (row,),
                list_rates,
                pool_ceilings_usd={"pool": Decimal(10)},
                panel_ceilings_usd={("pool", "panel"): Decimal("9.99")},
            )

        discount_rates = (
            RouteRate("route", Decimal(0), Decimal(5), "e" * 64, "discount"),
            RouteRate("route", Decimal(0), Decimal(10), "e" * 64, "list"),
        )
        discount_projection = project_maximum_exposure(
            (row,),
            discount_rates,
            price_basis="discount",
        )
        with self.assertRaisesRegex(BudgetCeilingExceeded, "discount"):
            validate_planning_budget_ceiling(
                (row,),
                discount_rates,
                pool_ceilings_usd={"pool": Decimal(5)},
                panel_ceilings_usd={("pool", "panel"): Decimal(5)},
                price_basis="discount",
            )
        self.assertEqual(
            validate_planning_budget_ceiling(
                (row,),
                discount_rates,
                pool_ceilings_usd={"pool": Decimal(5)},
                panel_ceilings_usd={("pool", "panel"): Decimal(5)},
                price_basis="discount",
                receipt_checked_discount_policy=True,
            ),
            discount_projection,
        )


if __name__ == "__main__":
    unittest.main()
