"""Cumulative first-five boundary survives restart and direct journal calls."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from effort_atlas.inkling_accounting import InklingStageJournal
from effort_atlas.pilot_accounting import AccountingHalt
from test_inkling_accounting import policy


class FirstFiveJournalTests(unittest.TestCase):
    def journal(self, path):
        return InklingStageJournal(path, policy=policy(items=6), plan_sha256='b'*64,
            account_sha256='c'*64, billing_group_sha256='d'*64,
            item_ids=[str(i) for i in range(6)], synthetic=True)

    def test_cumulative_pause_and_review_release_survive_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ledger.jsonl'
            journal = self.journal(path)
            now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            journal.reserve_stage('medium', input_allowance=5, input_rate_per_million=Decimal(1),
                output_rate_per_million=Decimal(1), verified_balance_usd=Decimal(5000),
                balance_evidence_sha256='e'*64, window_start=now, window_end=now+timedelta(hours=2),
                first_five_policy_sha256='f'*64)
            for i in range(5):
                journal = self.journal(path)
                journal.begin_attempt('medium', item_id=str(i), request_id=str(i))
                journal.record_response('medium', item_id=str(i), request_id=str(i),
                    provider_response_id=str(i), response_sha256=str(i)*64,
                    prompt_tokens=2, completion_tokens=3, native_stop_reason='end_turn')
                if i < 4:
                    with self.assertRaises(AccountingHalt):
                        journal.review_first_five('medium', review_sha256='a'*64,
                            response_sha256s=[str(n)*64 for n in range(i+1)])
            before = journal.snapshot()
            self.assertTrue(before['stages']['medium']['first_five_review_required'])
            with self.assertRaises(AccountingHalt):
                self.journal(path).begin_attempt('medium', item_id='5', request_id='5')
            hashes = [str(i)*64 for i in range(5)]
            with self.assertRaises(AccountingHalt):
                journal.review_first_five('medium', review_sha256='a'*64, response_sha256s=list(reversed(hashes)))
            # A validly hash-chained sixth start inserted below the public method
            # must still fail replay. Copying here creates a synthetic test only.
            shadow_path = Path(td) / 'shadow.jsonl'
            shadow_path.write_bytes(path.read_bytes())
            shadow = self.journal(shadow_path)
            with shadow._locked() as rows:
                current = shadow._state(rows)['stages']['medium']
                event = shadow._base_event('medium', 'begin_attempt', item_id='5')
                shadow._add_stage_config(event, current)
            event.update(event_type='unaccounted', request_id='injected-sixth',
                         request_started_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
            shadow.ledger.append(event)
            with self.assertRaises(AccountingHalt): shadow.snapshot()
            journal.review_first_five('medium', review_sha256='a'*64, response_sha256s=hashes)
            with self.assertRaises(AccountingHalt):
                journal.review_first_five('medium', review_sha256='a'*64, response_sha256s=hashes)
            journal = self.journal(path)
            self.assertFalse(journal.snapshot()['stages']['medium']['first_five_review_required'])
            self.assertEqual(journal.snapshot()['reserved_usd'], before['reserved_usd'])
            journal.begin_attempt('medium', item_id='5', request_id='5')
            self.assertEqual(len(journal.snapshot()['stages']['medium']['attempts']), 6)


if __name__ == '__main__': unittest.main()
