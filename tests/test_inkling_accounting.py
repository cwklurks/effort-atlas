"""Offline synthetic tests for whole-stage Tinker accounting."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from effort_atlas.inkling_accounting import BillingEvidence, InklingStageJournal
from effort_atlas.pilot_accounting import AccountingHalt, CeilingHalt


UTC = timezone.utc
MEDIUM_START = datetime(2099, 1, 1, 10, tzinfo=UTC)
MEDIUM_END = datetime(2099, 1, 1, 11, tzinfo=UTC)
MAX_START = datetime(2099, 1, 1, 11, tzinfo=UTC)
MAX_END = datetime(2099, 1, 1, 12, tzinfo=UTC)


def digest(char: str) -> str:
    return char * 64


def policy(*, items: int = 2, cap: int = 10, stage_ceiling: int = 5,
           combined_ceiling: int = 10, reserve: int = 3000) -> dict:
    return {
        "schema_version": "inkling-stage-policy-v1",
        "approved_by": "Connor",
        "approved_on": "2026-09-07",
        "decision": "whole_stage_reservation_then_aggregate_reconciliation",
        "phase": "exploratory",
        "model": "thinkingmachines/Inkling",
        "stage_ceilings_usd": {"medium": stage_ceiling, "max": stage_ceiling},
        "combined_ceiling_usd": combined_ceiling,
        "research_reserve_usd": reserve,
        "items_per_stage": items,
        "max_tokens": cap,
        "maximum_requires_reconciled_uncapped_medium": True,
        "approval_record_sha256": digest("a"),
        "live_account_evidence_verified": False,
    }


class InklingAccountingTests(unittest.TestCase):
    def journal(self, path: Path, *, policy_value: dict | None = None,
                plan: str | None = None, account: str | None = None,
                group: str | None = None) -> InklingStageJournal:
        return InklingStageJournal(
            path,
            policy=policy_value or policy(),
            plan_sha256=plan or digest("b"),
            account_sha256=account or digest("c"),
            billing_group_sha256=group or digest("d"),
            item_ids=("item-1", "item-2"),
        )

    def reserve(self, journal: InklingStageJournal, stage: str = "medium") -> dict:
        start, end = ((MEDIUM_START, MEDIUM_END) if stage == "medium"
                      else (MAX_START, MAX_END))
        return journal.reserve_stage(
            stage,
            input_allowance=5,
            input_rate_per_million=Decimal("100000"),
            output_rate_per_million=Decimal("200000"),
            verified_balance_usd=Decimal("3005"),
            balance_evidence_sha256=digest("e"),
            window_start=start,
            window_end=end,
        )

    def response(self, journal: InklingStageJournal, item_id: str, *,
                 stage: str = "medium", stop: str = "end_turn",
                 request_id: str | None = None, response_id: str | None = None,
                 prompt_tokens: int = 5, completion_tokens: int = 10,
                 now: datetime | None = None) -> dict:
        ordinal = int(item_id.rsplit("-", 1)[1])
        return journal.record_response(
            stage,
            item_id=item_id,
            request_id=request_id or f"local-{stage}-{ordinal}",
            provider_response_id=response_id or f"provider-{stage}-{ordinal}",
            response_sha256=digest(str(ordinal)),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            native_stop_reason=stop,
            now=now or (MEDIUM_START if stage == "medium" else MAX_START),
        )

    def collect_medium(self, journal: InklingStageJournal, *, cap_stop: bool = False) -> None:
        self.reserve(journal)
        for ordinal, item_id in enumerate(("item-1", "item-2"), start=1):
            journal.begin_attempt(
                "medium", item_id=item_id, request_id=f"local-medium-{ordinal}",
                now=MEDIUM_START,
            )
            self.response(
                journal, item_id,
                stop="max_tokens" if cap_stop and ordinal == 2 else "end_turn",
            )
        journal.finish_stage("medium")

    def evidence(self, *, stage: str = "medium", prompt_tokens: int = 10,
                 completion_tokens: int = 20, deduction: str = "5",
                 complete: bool = True) -> BillingEvidence:
        start, end = ((MEDIUM_START, MEDIUM_END) if stage == "medium"
                      else (MAX_START, MAX_END))
        return BillingEvidence(
            account_sha256=digest("c"),
            billing_group_sha256=digest("d"),
            model="thinkingmachines/Inkling",
            window_start=start,
            window_end=end,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            account_deduction_usd=Decimal(deduction),
            manifest_sha256=digest("f"),
            source_sha256s=(digest("1"), digest("2")),
            complete=complete,
        )

    def test_reserves_whole_bound_and_holds_it_until_aggregate_settlement(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "account.jsonl"
            journal = self.journal(path)
            reserved = self.reserve(journal)
            self.assertEqual(
                reserved["request_config"]["original_stage_bound_usd"], "5"
            )
            journal.begin_attempt(
                "medium", item_id="item-1", request_id="local-medium-1",
                now=MEDIUM_START,
            )
            self.response(journal, "item-1")
            partial = journal.snapshot()
            self.assertEqual(partial["active_exposure_usd"], "5")
            self.assertEqual(partial["stages"]["medium"]["response_count"], 1)
            self.assertEqual(
                partial["stages"]["medium"]["attempts"]["item-1"]["response_sha256"],
                digest("1"),
            )
            self.assertEqual(partial["stages"]["medium"]["configuration"], {
                "input_allowance": 5,
                "input_rate_per_million": "100000",
                "output_rate_per_million": "200000",
                "window_start": "2099-01-01T10:00:00Z",
                "window_end": "2099-01-01T11:00:00Z",
            })

            journal.begin_attempt(
                "medium", item_id="item-2", request_id="local-medium-2",
                now=MEDIUM_START,
            )
            self.response(journal, "item-2")
            journal.finish_stage("medium")
            self.assertEqual(journal.snapshot()["active_exposure_usd"], "5")
            journal.settle_stage("medium", evidence=self.evidence())
            settled = journal.snapshot()
            self.assertEqual(settled["active_exposure_usd"], "0")
            self.assertEqual(settled["reconciled_deduction_usd"], "5")
            self.assertTrue(settled["stages"]["medium"]["complete"])
            self.assertTrue(settled["stages"]["medium"]["reconciled"])

    def test_exact_balance_and_stage_ceiling_are_inclusive(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "exact.jsonl")
            self.reserve(journal)
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "short.jsonl")
            with self.assertRaises(CeilingHalt):
                journal.reserve_stage(
                    "medium", input_allowance=5,
                    input_rate_per_million=Decimal("100000"),
                    output_rate_per_million=Decimal("200000"),
                    verified_balance_usd=Decimal("3004.999999"),
                    balance_evidence_sha256=digest("e"),
                    window_start=MEDIUM_START, window_end=MEDIUM_END,
                )
            self.assertEqual(journal.snapshot()["active_exposure_usd"], "0")
        with tempfile.TemporaryDirectory() as td:
            too_low = policy(stage_ceiling=4)
            journal = self.journal(Path(td) / "over.jsonl", policy_value=too_low)
            with self.assertRaises(CeilingHalt):
                self.reserve(journal)

    def test_rates_require_positive_decimal_and_counts_are_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rates.jsonl"
            for bad in (0, 1.0, Decimal("0"), Decimal("-1"), Decimal("NaN")):
                with self.subTest(bad=bad):
                    journal = self.journal(path)
                    with self.assertRaises(ValueError):
                        journal.reserve_stage(
                            "medium", input_allowance=5,
                            input_rate_per_million=bad,
                            output_rate_per_million=Decimal("1"),
                            verified_balance_usd=Decimal("4000"),
                            balance_evidence_sha256=digest("e"),
                            window_start=MEDIUM_START, window_end=MEDIUM_END,
                        )
            journal = self.journal(path)
            with self.assertRaises(ValueError):
                journal.reserve_stage(
                    "medium", input_allowance=True,
                    input_rate_per_million=Decimal("1"),
                    output_rate_per_million=Decimal("1"),
                    verified_balance_usd=Decimal("4000"),
                    balance_evidence_sha256=digest("e"),
                    window_start=MEDIUM_START, window_end=MEDIUM_END,
                )

    def test_attempt_start_survives_restart_and_forbids_duplicate_or_parallel_work(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "account.jsonl"
            journal = self.journal(path)
            self.reserve(journal)
            started = journal.begin_attempt(
                "medium", item_id="item-1", request_id="local-medium-1",
                now=MEDIUM_START,
            )
            self.assertEqual(
                started["job_id"], journal.attempt_job_id("medium", "item-1")
            )
            fresh = self.journal(path)
            for item_id, request_id in (
                ("item-1", "retry"), ("item-2", "local-medium-2")
            ):
                with self.subTest(item_id=item_id), self.assertRaises(AccountingHalt):
                    fresh.begin_attempt(
                        "medium", item_id=item_id, request_id=request_id,
                        now=MEDIUM_START,
                    )
            fresh.block_attempt(
                "medium", item_id="item-1", request_id="local-medium-1",
                error_class="UnknownRequestOutcome",
            )
            blocked = self.journal(path).snapshot()
            self.assertEqual(blocked["active_exposure_usd"], "5")
            self.assertEqual(
                blocked["stages"]["medium"]["attempts"]["item-1"]["status"],
                "blocked",
            )
            with self.assertRaises(AccountingHalt):
                self.journal(path).begin_attempt(
                    "medium", item_id="item-2", request_id="local-medium-2",
                    now=MEDIUM_START,
                )

    def test_malformed_unknown_overcap_and_input_breach_permanently_block(self):
        cases = {
            "missing_response_id": {"provider_response_id": ""},
            "missing_response_hash": {"response_sha256": ""},
            "unknown_stop": {"native_stop_reason": "unknown"},
            "over_cap": {"completion_tokens": 11},
            "input_breach": {"prompt_tokens": 6},
            "bad_usage": {"prompt_tokens": True},
        }
        for name, changes in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "account.jsonl"
                journal = self.journal(path)
                self.reserve(journal)
                journal.begin_attempt(
                    "medium", item_id="item-1", request_id="local-medium-1",
                    now=MEDIUM_START,
                )
                kwargs = {
                    "item_id": "item-1", "request_id": "local-medium-1",
                    "provider_response_id": "provider-medium-1",
                    "response_sha256": digest("1"),
                    "prompt_tokens": 5, "completion_tokens": 10,
                    "native_stop_reason": "end_turn", "now": MEDIUM_START,
                }
                kwargs.update(changes)
                with self.assertRaises(AccountingHalt):
                    journal.record_response("medium", **kwargs)
                fresh = self.journal(path)
                snap = fresh.snapshot()
                self.assertTrue(snap["stages"]["medium"]["blocked"])
                self.assertEqual(snap["active_exposure_usd"], "5")
                with self.assertRaises(AccountingHalt):
                    fresh.begin_attempt(
                        "medium", item_id="item-2", request_id="local-medium-2",
                        now=MEDIUM_START,
                    )

    def test_expired_window_blocks_before_transport_and_window_must_be_whole_hour(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "expired.jsonl")
            self.reserve(journal)
            with self.assertRaises(AccountingHalt):
                journal.begin_attempt(
                    "medium", item_id="item-1", request_id="never-sent",
                    now=MEDIUM_END,
                )
            snap = journal.snapshot()
            self.assertTrue(snap["stages"]["medium"]["blocked"])
            self.assertEqual(snap["stages"]["medium"]["attempts"], {})
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "bad-window.jsonl")
            with self.assertRaises(ValueError):
                journal.reserve_stage(
                    "medium", input_allowance=5,
                    input_rate_per_million=Decimal("1"),
                    output_rate_per_million=Decimal("1"),
                    verified_balance_usd=Decimal("4000"),
                    balance_evidence_sha256=digest("e"),
                    window_start=MEDIUM_START.replace(minute=1),
                    window_end=MEDIUM_END,
                )

    def test_finish_requires_every_planned_response(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "account.jsonl")
            self.reserve(journal)
            journal.begin_attempt(
                "medium", item_id="item-1", request_id="local-medium-1",
                now=MEDIUM_START,
            )
            self.response(journal, "item-1")
            with self.assertRaises(AccountingHalt):
                journal.finish_stage("medium")
            with self.assertRaises(AccountingHalt):
                journal.begin_attempt(
                    "medium", item_id="item-1", request_id="retry",
                    now=MEDIUM_START,
                )

    def test_max_requires_finished_reconciled_medium_with_zero_cap_stops(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "early.jsonl")
            with self.assertRaises(AccountingHalt):
                self.reserve(journal, "max")

        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "capped.jsonl")
            self.collect_medium(journal, cap_stop=True)
            journal.settle_stage("medium", evidence=self.evidence())
            with self.assertRaises(AccountingHalt):
                self.reserve(journal, "max")

        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "allowed.jsonl")
            self.collect_medium(journal)
            with self.assertRaises(AccountingHalt):
                self.reserve(journal, "max")
            journal.settle_stage("medium", evidence=self.evidence())
            self.reserve(journal, "max")
            snap = journal.snapshot()
            self.assertEqual(snap["active_exposure_usd"], "5")
            self.assertEqual(snap["stages"]["max"]["status"], "reserved")

    def test_max_must_reuse_medium_rates_allowance_and_nonoverlapping_window(self):
        with tempfile.TemporaryDirectory() as td:
            journal = self.journal(Path(td) / "account.jsonl")
            self.collect_medium(journal)
            journal.settle_stage("medium", evidence=self.evidence())
            for label, changed in (
                ("allowance", {"input_allowance": 4}),
                ("input_rate", {"input_rate_per_million": Decimal("99999")}),
                ("output_rate", {"output_rate_per_million": Decimal("199999")}),
                ("window", {"window_start": MEDIUM_START, "window_end": MEDIUM_END}),
            ):
                with self.subTest(label=label):
                    kwargs = {
                        "input_allowance": 5,
                        "input_rate_per_million": Decimal("100000"),
                        "output_rate_per_million": Decimal("200000"),
                        "verified_balance_usd": Decimal("3005"),
                        "balance_evidence_sha256": digest("e"),
                        "window_start": MAX_START,
                        "window_end": MAX_END,
                    }
                    kwargs.update(changed)
                    with self.assertRaises(AccountingHalt):
                        journal.reserve_stage("max", **kwargs)

    def test_reconciliation_mismatch_stays_held_and_blocks_later_stage(self):
        evidence_changes = {
            "input_total": {"prompt_tokens": 9},
            "output_total": {"completion_tokens": 19},
            "deduction": {"account_deduction_usd": Decimal("4.99")},
            "account": {"account_sha256": digest("9")},
            "group": {"billing_group_sha256": digest("9")},
            "model": {"model": "other"},
            "window": {"window_end": MAX_END},
            "incomplete": {"complete": False},
            "bad_manifest_hash": {"manifest_sha256": "bad"},
            "no_source_hashes": {"source_sha256s": ()},
        }
        for label, changes in evidence_changes.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "account.jsonl"
                journal = self.journal(path)
                self.collect_medium(journal)
                with self.assertRaises(AccountingHalt):
                    journal.settle_stage(
                        "medium", evidence=replace(self.evidence(), **changes)
                    )
                snap = self.journal(path).snapshot()
                self.assertEqual(snap["active_exposure_usd"], "5")
                self.assertTrue(snap["stages"]["medium"]["blocked"])
                with self.assertRaises(AccountingHalt):
                    self.reserve(self.journal(path), "max")

    def test_missing_reconciliation_evidence_is_durably_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "account.jsonl"
            journal = self.journal(path)
            self.collect_medium(journal)
            with self.assertRaises(AccountingHalt):
                journal.settle_stage("medium", evidence=None)
            fresh = self.journal(path)
            self.assertEqual(fresh.snapshot()["stages"]["medium"]["status"], "blocked")
            self.assertEqual(fresh.snapshot()["reserved_usd"], "5")

    def test_provider_response_identity_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "account.jsonl"
            journal = self.journal(path)
            self.reserve(journal)
            journal.begin_attempt(
                "medium", item_id="item-1", request_id="local-medium-1",
                now=MEDIUM_START,
            )
            self.response(journal, "item-1", response_id="same")
            journal.begin_attempt(
                "medium", item_id="item-2", request_id="local-medium-2",
                now=MEDIUM_START,
            )
            with self.assertRaises(AccountingHalt):
                self.response(journal, "item-2", response_id="same")
            self.assertTrue(self.journal(path).snapshot()["stages"]["medium"]["blocked"])

    def test_policy_plan_account_and_group_are_fixed_by_existing_ledger(self):
        variants = {
            "policy": {"policy_value": policy(combined_ceiling=11)},
            "plan": {"plan": digest("9")},
            "account": {"account": digest("9")},
            "group": {"group": digest("9")},
        }
        for label, kwargs in variants.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "account.jsonl"
                self.reserve(self.journal(path))
                with self.assertRaises(AccountingHalt):
                    self.journal(path, **kwargs).snapshot()

    def test_synthetic_ledger_cannot_be_reopened_as_nonsynthetic(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mock.jsonl"
            mock = InklingStageJournal(
                path, policy=policy(), plan_sha256=digest("b"),
                account_sha256=digest("c"), billing_group_sha256=digest("d"),
                item_ids=("item-1", "item-2"), synthetic=True,
            )
            self.reserve(mock)
            with self.assertRaises(AccountingHalt):
                self.journal(path).snapshot()
            row = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(row["phase"], "mock_only")
            self.assertTrue(row["request_config"]["synthetic"])

    def test_hash_chain_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "account.jsonl"
            journal = self.journal(path)
            self.reserve(journal)
            row = json.loads(path.read_text().strip())
            row["request_config"]["original_stage_bound_usd"] = "0"
            path.write_text(json.dumps(row) + "\n")
            with self.assertRaises(ValueError):
                self.journal(path).snapshot()


if __name__ == "__main__":
    unittest.main()
