"""Synthetic regressions for durable exploratory accounting; never use a provider."""
import tempfile
import unittest
from pathlib import Path

from effort_atlas.pilot_accounting import BudgetJournal, AccountingHalt, CeilingHalt


def event(job, dataset="a", model="model"):
    return {"job_id": job, "panel": "pilot", "model": model, "domain": dataset,
            "item_id": job, "phase": "exploratory_pilot", "request_config": {}}


class BudgetJournalTests(unittest.TestCase):
    def journal(self, path, *, total=0.15, dataset=0.15, pool=0.25):
        return BudgetJournal(path, model="model", total_ceiling=total,
                             per_dataset_ceiling=dataset, pool_ceiling=pool)

    def test_restart_and_new_dataset_preserve_spend(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            j = self.journal(path)
            j.reserve(event("one"), 0.10)
            j.settle(event("one"), 0.10, generation_id="g1")
            fresh = self.journal(path)
            with self.assertRaises(CeilingHalt):
                fresh.reserve(event("two", "b"), 0.10)
            self.assertAlmostEqual(fresh.spent_total, 0.10)

    def test_unknown_charge_blocks_every_further_reservation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            j = self.journal(path)
            j.reserve(event("one"), 0.10)
            j.unresolved(event("one"), error_class="RequestFailure")
            fresh = self.journal(path)
            self.assertAlmostEqual(fresh.exposure_total, 0.10)
            with self.assertRaises(AccountingHalt):
                fresh.reserve(event("two"), 0.01)

    def test_exact_ceiling_and_duplicate_job(self):
        with tempfile.TemporaryDirectory() as td:
            j = self.journal(Path(td) / "ledger.jsonl", total=0.3, dataset=0.3, pool=1.0)
            for job, cost in (("one", 0.1), ("two", 0.2)):
                j.reserve(event(job), cost)
                j.settle(event(job), cost, generation_id=job)
            self.assertTrue(j.completed("one"))
            with self.assertRaises(AccountingHalt):
                j.reserve(event("one"), 0.0)
            with self.assertRaises(CeilingHalt):
                j.reserve(event("three"), 0.000001)

    def test_pool_shared_across_models(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            j = self.journal(path)
            j.reserve(event("one"), 0.15)
            j.settle(event("one"), 0.15, generation_id="g1")
            other = BudgetJournal(path, model="other", total_ceiling=1,
                                  per_dataset_ceiling=1, pool_ceiling=0.25)
            with self.assertRaises(CeilingHalt):
                other.reserve(event("two", model="other"), 0.11)

    def test_nonfinite_negative_and_changed_limits_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            j = self.journal(path)
            for value in (float("nan"), float("inf"), -1, True):
                with self.assertRaises(ValueError):
                    j.reserve(event("bad"), value)
            j.reserve(event("one"), 0.10)
            j.settle(event("one"), 0.10, generation_id="g1")
            with self.assertRaises(AccountingHalt):
                self.journal(path, total=1).reserve(event("two"), 0.1)

    def test_duplicate_generation_cannot_become_second_measurement(self):
        with tempfile.TemporaryDirectory() as td:
            j = self.journal(Path(td) / "ledger.jsonl", total=1, dataset=1, pool=1)
            j.reserve(event("one"), 0.1)
            j.settle(event("one"), 0.1, generation_id="same")
            j.reserve(event("two"), 0.1)
            with self.assertRaises(AccountingHalt):
                j.settle(event("two"), 0.1, generation_id="same")
            self.assertAlmostEqual(j.exposure_total, 0.2)

    def test_settlement_above_reserved_exposure_stays_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            j = self.journal(Path(td) / "ledger.jsonl")
            j.reserve(event("one"), 0.1)
            with self.assertRaises(AccountingHalt):
                j.settle(event("one"), 0.2, generation_id="g1")
            self.assertGreaterEqual(j.exposure_total, 0.2)
            with self.assertRaises(AccountingHalt):
                j.reserve(event("two"), 0.0)

    def test_receipt_pending_cannot_raise_original_reservation_after_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            j = self.journal(path)
            j.reserve(event("one"), 0.10)
            j.unresolved(event("one"), error_class="ReceiptPending", known_exposure_usd=0.11)
            fresh = self.journal(path)
            with self.assertRaises(AccountingHalt):
                fresh.settle(event("one"), 0.11, generation_id="g1")
            self.assertIsNone(fresh.completed("one"))
            self.assertAlmostEqual(fresh.exposure_total, 0.11)
            with self.assertRaises(AccountingHalt):
                fresh.reserve(event("two"), 0.0)


if __name__ == "__main__":
    unittest.main()
