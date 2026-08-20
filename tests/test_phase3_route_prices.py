from __future__ import annotations

import hashlib
import json
import unittest
from decimal import Decimal
from pathlib import Path

from effort_atlas.reap_budget import BudgetRow, RouteRate, project_maximum_exposure

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "reap" / "phase3_evidence" / "route_prices_2026-08-10.json"
MILLION = Decimal(1_000_000)


class Phase3RoutePriceSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        cls.prices = {row["price_id"]: row for row in cls.snapshot["prices"]}

    def test_snapshot_is_non_frozen_dated_and_authorizes_nothing(self) -> None:
        self.assertEqual(self.snapshot["schema_version"], 1)
        self.assertEqual(self.snapshot["status"], "NON_FROZEN_PLANNING_EVIDENCE")
        self.assertEqual(self.snapshot["local_evidence_date"], "2026-08-10")
        self.assertRegex(
            self.snapshot["retrieved_at_utc"], r"^2026-08-11T\d{2}:\d{2}:\d{2}Z$"
        )
        self.assertIs(self.snapshot["no_call_authorization"], True)
        self.assertNotIn("approved", SNAPSHOT.read_text(encoding="utf-8").lower())

    def test_prices_are_unique_decimal_strings_with_primary_sources(self) -> None:
        self.assertEqual(len(self.prices), len(self.snapshot["prices"]))
        sources = self.snapshot["sources"]
        for source in sources.values():
            self.assertRegex(source, r"^https://")
        for price in self.prices.values():
            self.assertIn(price["source_id"], sources)
            self.assertIn(price["basis"], {"list", "discount"})
            for field in ("input_usd_per_million", "output_usd_per_million"):
                value = price[field]
                self.assertIsInstance(value, str)
                parsed = Decimal(value)
                self.assertTrue(parsed.is_finite())
                self.assertGreaterEqual(parsed, 0)

    def test_planning_examples_recompute_from_snapshot_prices(self) -> None:
        expected = {
            ("direct-openai-arm-a-30", "openai-terra-list-2026-08-10"): Decimal(
                "125.82912"
            ),
            ("direct-openai-arm-a-30", "openai-luna-list-2026-08-10"): Decimal(
                "12.582912"
            ),
            ("direct-openai-arm-a-30", "openai-sol-list-2026-08-10"): Decimal(
                "314.5728"
            ),
            ("inkling-abc-30", "tinker-inkling-promo-2026-08-10"): Decimal(
                "746.0880384"
            ),
            ("inkling-abc-30", "tinker-inkling-list-2026-08-10"): Decimal(
                "1492.1760768"
            ),
            (
                "gpt-oss-abc-60-cap-20480",
                "tinker-gpt-oss-120b-list-2026-08-10",
            ): Decimal("187.7999616"),
            ("breadth-arm-a-30-n8", "tinker-nemotron-ultra-promo-2026-08-10"): Decimal(
                "80.7763968"
            ),
            ("breadth-arm-a-30-n8", "tinker-nemotron-ultra-list-2026-08-10"): Decimal(
                "161.5527936"
            ),
            ("breadth-arm-a-30-n8", "tinker-qwen35-397b-list-2026-08-10"): Decimal(
                "97.3209600"
            ),
            (
                "breadth-arm-a-30-n8",
                "openrouter-baseten-gpt-oss-list-2026-08-10",
            ): Decimal("5.7016320"),
            ("breadth-arm-a-30-n8", "openrouter-groq-gpt-oss-list-2026-08-10"): Decimal(
                "7.0778880"
            ),
            (
                "breadth-arm-a-30-n8",
                "openrouter-cerebras-gpt-oss-list-2026-08-10",
            ): Decimal("10.1253120"),
            (
                "breadth-arm-a-30-n8",
                "openrouter-deepinfra-gpt-oss-list-2026-08-10",
            ): Decimal("1.97787648"),
        }
        observed = {}
        for example in self.snapshot["planning_examples"]:
            self.assertEqual(example["status"], "advisory_not_selected")
            for price_id in example["price_ids"]:
                price = self.prices[price_id]
                cost = (
                    Decimal(example["prompt_token_bound"])
                    * Decimal(price["input_usd_per_million"])
                    + Decimal(example["output_token_bound"])
                    * Decimal(price["output_usd_per_million"])
                ) / MILLION
                observed[(example["example_id"], price_id)] = cost
        self.assertEqual(observed, expected)

    def test_every_promotional_price_has_a_matching_list_price(self) -> None:
        for promo in (
            price for price in self.prices.values() if price["basis"] == "discount"
        ):
            matches = [
                price
                for price in self.prices.values()
                if price["basis"] == "list"
                and price["route_id"] == promo["route_id"]
                and price["provider"] == promo["provider"]
            ]
            with self.subTest(price_id=promo["price_id"]):
                self.assertEqual(len(matches), 1)

        nemotron = self.prices["tinker-nemotron-ultra-list-2026-08-10"]
        self.assertEqual(
            (nemotron["input_usd_per_million"], nemotron["output_usd_per_million"]),
            ("4.98", "12.45"),
        )

    def test_current_openai_snapshot_matches_primary_model_pages(
        self,
    ) -> None:
        terra = self.prices["openai-terra-list-2026-08-10"]
        luna = self.prices["openai-luna-list-2026-08-10"]
        self.assertEqual(
            (terra["input_usd_per_million"], terra["output_usd_per_million"]),
            ("2.00", "12.00"),
        )
        self.assertEqual(
            (luna["input_usd_per_million"], luna["output_usd_per_million"]),
            ("0.20", "1.20"),
        )
        self.assertEqual(terra["cached_input_usd_per_million"], "0.20")
        self.assertEqual(luna["cached_input_usd_per_million"], "0.02")

    def test_provider_qualified_routes_form_one_unambiguous_budget_snapshot(
        self,
    ) -> None:
        snapshot_sha256 = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
        list_prices = [
            price for price in self.prices.values() if price["basis"] == "list"
        ]
        rates = tuple(
            RouteRate(
                route_id=price["route_id"],
                input_usd_per_million=Decimal(price["input_usd_per_million"]),
                output_usd_per_million=Decimal(price["output_usd_per_million"]),
                snapshot_sha256=snapshot_sha256,
                basis=price["basis"],
            )
            for price in list_prices
        )
        rows = tuple(
            BudgetRow(
                job_id=f"job-{index}",
                route_id=price["route_id"],
                phase="planning-test",
                prompt_token_bound=1,
                max_output_tokens=1,
                pool_id=price["route_id"].split("::", 1)[0],
                panel_id=price["price_id"],
            )
            for index, price in enumerate(list_prices)
        )

        projection = project_maximum_exposure(rows, rates)

        self.assertEqual(projection.row_count, len(list_prices))
        self.assertEqual(
            len(
                {(price["route_id"], price["basis"]) for price in self.prices.values()}
            ),
            len(self.prices),
        )
        for price in self.prices.values():
            with self.subTest(price_id=price["price_id"]):
                self.assertIn("provider_route", price)
                self.assertNotEqual(price["route_id"], price["provider_route"])
                self.assertIn("::", price["route_id"])

        tinker = self.prices["tinker-gpt-oss-120b-list-2026-08-10"]
        baseten = self.prices["openrouter-baseten-gpt-oss-list-2026-08-10"]
        self.assertEqual(tinker["provider_route"], baseten["provider_route"])
        self.assertNotEqual(tinker["route_id"], baseten["route_id"])


if __name__ == "__main__":
    unittest.main()
