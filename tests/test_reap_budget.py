from __future__ import annotations

import unittest
from decimal import Decimal

from effort_atlas.reap_budget import (
    BudgetCeilingExceeded,
    BudgetRow,
    RouteRate,
    enforce_budget_ceiling,
    enforce_freeze_budget_gate,
    project_maximum_exposure,
)


class ReapBudgetTests(unittest.TestCase):
    def test_maximum_exposure_sums_every_rows_prompt_and_cap(self) -> None:
        rows = (
            BudgetRow("job-main", "route-a", "main", 100, 200),
            BudgetRow("job-smoke", "route-a", "smoke", 50, 75),
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
            (BudgetRow("job", "route", "main", 1_000_000, 1_000_000),),
            (RouteRate("route", Decimal(2), Decimal(12), "b" * 64, "list"),),
        )
        self.assertEqual(projection.maximum_exposure_usd, Decimal(14))
        self.assertEqual(enforce_budget_ceiling(projection, Decimal(14)), projection)
        with self.assertRaisesRegex(BudgetCeilingExceeded, "14"):
            enforce_budget_ceiling(projection, Decimal("13.999999"))

    def test_missing_route_rate_duplicate_ids_and_malformed_values_fail(self) -> None:
        valid_row = BudgetRow("job", "route", "main", 1, 1)
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
            BudgetRow("discount-job", "discount-route", "main", 0, 1_000_000, "pool", "panel"),
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

    def test_projection_defaults_to_list_and_preserves_snapshot_pool_panel_identity(self) -> None:
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

    def test_freeze_gate_enforces_panel_and_pool_ceilings_and_discount_policy(self) -> None:
        row = BudgetRow("job", "route", "main", 0, 1_000_000, "pool", "panel")
        list_projection = project_maximum_exposure(
            (row,), (RouteRate("route", Decimal(0), Decimal(10), "e" * 64, "list"),)
        )
        self.assertEqual(
            enforce_freeze_budget_gate(
                list_projection,
                pool_ceilings_usd={"pool": Decimal(10)},
                panel_ceilings_usd={("pool", "panel"): Decimal(10)},
            ),
            list_projection,
        )
        with self.assertRaisesRegex(BudgetCeilingExceeded, "panel"):
            enforce_freeze_budget_gate(
                list_projection,
                pool_ceilings_usd={"pool": Decimal(10)},
                panel_ceilings_usd={("pool", "panel"): Decimal("9.99")},
            )

        discount_projection = project_maximum_exposure(
            (row,),
            (
                RouteRate("route", Decimal(0), Decimal(5), "e" * 64, "discount"),
                RouteRate("route", Decimal(0), Decimal(10), "e" * 64, "list"),
            ),
            price_basis="discount",
        )
        with self.assertRaisesRegex(BudgetCeilingExceeded, "discount"):
            enforce_freeze_budget_gate(
                discount_projection,
                pool_ceilings_usd={"pool": Decimal(5)},
                panel_ceilings_usd={("pool", "panel"): Decimal(5)},
            )
        self.assertEqual(
            enforce_freeze_budget_gate(
                discount_projection,
                pool_ceilings_usd={"pool": Decimal(5)},
                panel_ceilings_usd={("pool", "panel"): Decimal(5)},
                receipt_checked_discount_policy=True,
            ),
            discount_projection,
        )


if __name__ == "__main__":
    unittest.main()
