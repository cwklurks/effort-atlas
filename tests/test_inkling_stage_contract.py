"""Offline launch-evidence regressions; only synthetic evidence is used."""
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from effort_atlas.inkling_stage_contract import load_policy, validate_evidence, execution_manifest, EXECUTION_FILES


class StageEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        start = now.replace(minute=0, second=0)
        end = start + timedelta(hours=2)
        rows = [{"request_sha256": "a" * 64, "input_tokens": 12}]
        counts = {"schema_version": "inkling-input-counts-v1", "plan_sha256": "b" * 64,
                  "stage": "medium", "endpoint": "https://tinker.thinkingmachines.dev/services/tinker-prod/anthropic/api",
                  "model": "thinkingmachines/Inkling", "rows": rows}
        artifacts = {}
        for name in ("pricing", "balance", "credit_eligibility", "cap_semantics", "billing_attribution", "independent_review", "input_counts"):
            path = root / 'results_pilot' / (name + '.json')
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(counts) if name == 'input_counts' else 'Synthetic attestation only')
            artifacts[name] = {"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        evidence = {"schema_version": "inkling-launch-evidence-v1", "execution_sha256": "c" * 64,
                    "plan_sha256": "b" * 64, "policy_sha256": "d" * 64,
                    "stage": "medium", "execution_host": socket.gethostname(), "account_id": "synthetic-account",
                    "approved_by": "Synthetic human", "approved_at": now.isoformat(), "expires_at": end.isoformat(),
                    "rates": {"input_per_mtok": 1.87, "output_per_mtok": 4.68},
                    "balance_usd": 5000, "input_allowance": 32768, "context_window": 65536,
                    "billing_group": "synthetic-isolated-user", "window_start": start.isoformat(), "window_end": end.isoformat(),
                    "checks": {name: True for name in artifacts}, "artifacts": artifacts}
        return evidence

    def validate(self, evidence, root):
        return validate_evidence(evidence, root=root, plan_sha256='b'*64,
                                 policy_sha256='d'*64, execution_sha256='c'*64,
                                 stage='medium', request_hashes=['a'*64])

    def test_billing_parser_change_invalidates_reviewed_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for relative in set(EXECUTION_FILES) | {'src/effort_atlas/inkling_billing.py'}:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic version one')
            first = execution_manifest({'plan_sha256': 'a'*64}, {}, root=root)
            (root / 'src/effort_atlas/inkling_billing.py').write_text('synthetic version two')
            second = execution_manifest({'plan_sha256': 'a'*64}, {}, root=root)
            self.assertNotEqual(first['execution_sha256'], second['execution_sha256'])

    def test_approved_ceilings_are_not_live_account_verification(self):
        policy = load_policy()
        self.assertEqual(policy['stage_ceilings_usd'], {'medium': 250, 'max': 250})
        self.assertEqual(policy['combined_ceiling_usd'], 500)
        self.assertFalse(policy['live_account_evidence_verified'])

    def test_complete_evidence_and_exact_input_count_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            evidence=self.fixture(root)
            valid=self.validate(evidence, root)
            self.assertEqual(valid['input_counts'], {'a'*64:12})
            evidence['plan_sha256']='e'*64
            with self.assertRaises(ValueError): self.validate(evidence,root)

    def test_missing_changed_expired_host_and_oversized_input_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for change in ({'artifacts':{}}, {'execution_host':'different-host'}, {'balance_usd':3000},
                           {'input_allowance':32769}, {'context_window':40000},
                           {'expires_at':'2020-01-01T00:00:00+00:00'}, {'rates':{'input_per_mtok':float('nan'),'output_per_mtok':4.68}}):
                evidence=self.fixture(root)
                evidence.update(change)
                with self.subTest(change=change), self.assertRaises(ValueError): self.validate(evidence,root)
            evidence=self.fixture(root)
            (root / evidence['artifacts']['pricing']['path']).write_text('Changed')
            with self.assertRaises(ValueError): self.validate(evidence,root)

    def test_reconciliation_can_read_an_expired_original_launch_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence = self.fixture(root)
            old = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(days=2)
            evidence.update(approved_at=(old + timedelta(minutes=1)).isoformat(),
                            expires_at=(old + timedelta(hours=1)).isoformat(),
                            window_start=old.isoformat(), window_end=(old + timedelta(hours=2)).isoformat())
            with self.assertRaises(ValueError): self.validate(evidence, root)
            result = validate_evidence(evidence, root=root, plan_sha256='b'*64,
                policy_sha256='d'*64, execution_sha256='c'*64, stage='medium',
                request_hashes=['a'*64], allow_expired=True)
            self.assertEqual(result['input_counts']['a'*64], 12)

    def test_input_count_omission_and_reused_hash_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rows in ([], [{'request_sha256':'a'*64,'input_tokens':True}],
                         [{'request_sha256':'a'*64,'input_tokens':32769}],
                         [{'request_sha256':'a'*64,'input_tokens':1}]*2):
                evidence=self.fixture(root)
                spec=evidence['artifacts']['input_counts']; path=root/spec['path']
                data=json.loads(path.read_text()); data['rows']=rows; path.write_text(json.dumps(data))
                spec['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError): self.validate(evidence,root)


if __name__ == '__main__': unittest.main()
