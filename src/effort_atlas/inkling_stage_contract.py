"""Offline evidence binding for the approved exploratory Tinker stages."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import socket
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from . import ROOT
from .confirmatory import sha256_json
from .inkling_baseline import MODEL, BASE_URL, CAP, DATASETS, build_request

POLICY_PATH = Path('reap/inkling_baseline/approved_policy.json')
APPROVAL_PATH = Path('reap/inkling_baseline/ACCOUNTING_APPROVAL_2026-09-07.md')
ACCOUNT_LEDGER = Path.home() / '.local/state/effort-atlas/tinker/inkling-stages.jsonl'
ACK_ENV = 'EFFORT_ATLAS_INKLING_LIVE_ACK'
ACK_VALUE = 'I_HAVE_VERIFIED_THE_STAGE_EVIDENCE'
CHECKS = ('pricing', 'balance', 'credit_eligibility', 'cap_semantics',
          'billing_attribution', 'independent_review', 'input_counts')
FIRST_FIVE_SCHEMA = 'inkling-first-five-evidence-v1'
FIRST_FIVE_APPROVAL = Path('reap/inkling_baseline/FIRST_FIVE_APPROVAL_2026-09-15.md')
FIRST_FIVE_ACK = 'I_ACCEPT_THE_FIRST_FIVE_ASSUMPTIONS'
FIRST_FIVE_ASSUMPTIONS = {
    'pricing': 'Listed rates are assumed to apply to this account and endpoint; actual charges are unverified.',
    'credit_eligibility': 'Research credits are assumed to cover this endpoint; eligibility is unverified.',
    'cap_semantics': 'The cap and reported output usage are assumed to include thinking and final-answer tokens; route-specific behavior is unverified.',
}
PREPARATION_FILES = ('src/effort_atlas/inkling_baseline.py', 'src/effort_atlas/baseline_upstream.py',
                     'src/effort_atlas/graders.py', 'src/effort_atlas/wrapper.py',
                     'reap/inkling_baseline/requirements.lock')
EXECUTION_FILES = PREPARATION_FILES + ('src/effort_atlas/inkling_accounting.py',
                   'src/effort_atlas/inkling_stage_contract.py', 'src/effort_atlas/inkling_stage.py',
                   'src/effort_atlas/inkling_billing.py', 'src/effort_atlas/confirmatory.py',
                   'src/effort_atlas/pilot_integrity.py', 'src/effort_atlas/pilot_accounting.py',
                   'src/effort_atlas/benchmark_provenance.py', 'src/effort_atlas/__init__.py',
                   'reap/inkling_baseline/upstream_sources.json', str(FIRST_FIVE_APPROVAL))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def finite_money(value) -> Decimal:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('amount must be a finite nonnegative number')
    return Decimal(str(value))


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('timestamp missing')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError('timestamp must include UTC offset')
    return result


def load_policy(root: Path = ROOT) -> dict:
    policy = json.loads((root / POLICY_PATH).read_text())
    required = {'schema_version': 'inkling-stage-policy-v1', 'approved_by': 'Connor',
                'approved_on': '2026-09-07', 'decision': 'whole_stage_reservation_then_aggregate_reconciliation',
                'phase': 'exploratory', 'model': MODEL, 'stage_ceilings_usd': {'medium': 250, 'max': 250},
                'combined_ceiling_usd': 500, 'research_reserve_usd': 3000, 'items_per_stage': 1000,
                'max_tokens': CAP, 'maximum_requires_reconciled_uncapped_medium': True,
                'live_account_evidence_verified': False,
                'approval_record_sha256': digest((root / APPROVAL_PATH).read_bytes())}
    if policy != required:
        raise ValueError('policy differs from the September 7 approval')
    return policy


def load_plan(directory: Path, *, root: Path = ROOT) -> tuple[dict, list[dict]]:
    manifest = json.loads((directory / 'manifest.json').read_text())
    unsigned = {k: v for k, v in manifest.items() if k != 'plan_sha256'}
    if manifest.get('plan_sha256') != sha256_json(unsigned):
        raise ValueError('preparation plan hash mismatch')
    if (manifest.get('phase') != 'exploratory' or manifest.get('endpoint') != BASE_URL
            or manifest.get('model') != MODEL or manifest.get('max_tokens') != CAP
            or manifest.get('dataset_counts') != {dataset: 200 for dataset in DATASETS}
            or manifest.get('initial_effort') != 'medium' or manifest.get('conditional_second_effort') != 'max'
            or manifest.get('generation_retries') != 0 or manifest.get('tools_enabled') is not False):
        raise ValueError('preparation differs from the approved baseline')
    hashes = manifest.get('implementation_sha256', {})
    if set(hashes) != set(PREPARATION_FILES) or any(
            digest((root / path).read_bytes()) != hashes[path] for path in PREPARATION_FILES):
        raise ValueError('preparation code changed; regenerate and review the plan')
    raw = (directory / 'requests.private.jsonl').read_bytes()
    if digest(raw) != manifest.get('private_requests_sha256'):
        raise ValueError('private request or gold-map hash mismatch')
    private = [json.loads(line) for line in raw.splitlines()]
    public = manifest.get('items', [])
    if len(private) != 1000 or len(public) != 1000:
        raise ValueError('preparation must contain exactly 1000 items')
    identities = set()
    for item, planned in zip(private, public):
        identity = (item['dataset'], item['source_item_id'])
        if identity in identities or any(item[k] != planned[k] for k in ('dataset', 'source_item_id', 'source_row_index')):
            raise ValueError('duplicate or mismatched item identity')
        identities.add(identity)
        for stage in ('medium', 'max'):
            if sha256_json(build_request(item['template'], stage)) != planned[f'{stage}_request_sha256']:
                raise ValueError('request bytes differ from the plan')
    return manifest, private


def execution_manifest(plan: dict, policy: dict, *, root: Path = ROOT) -> dict:
    result = {'plan_sha256': plan['plan_sha256'], 'policy_sha256': sha256_json(policy),
              'execution_host': socket.gethostname(), 'account_ledger': str(ACCOUNT_LEDGER),
              'implementation_sha256': {path: digest((root / path).read_bytes()) for path in EXECUTION_FILES}}
    return {**result, 'execution_sha256': sha256_json(result)}


def read_artifact(root: Path, spec: dict) -> bytes:
    if not isinstance(spec, dict) or set(spec) != {'path', 'sha256'} or not text(spec['path']):
        raise ValueError('invalid evidence artifact reference')
    relative = Path(spec['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('evidence path must stay inside the checkout')
    path = (root / relative).resolve()
    parts = path.relative_to(root.resolve()).parts
    if not parts or parts[0] not in {'results_pilot', 'reap'} or any(p.startswith('.') for p in parts):
        raise ValueError('evidence artifact outside allowed directories')
    data = path.read_bytes()
    if not data.strip() or digest(data) != spec['sha256']:
        raise ValueError('missing or changed evidence artifact')
    return data


def validate_evidence(evidence: dict, *, root: Path, plan_sha256: str, policy_sha256: str,
                      execution_sha256: str, stage: str, request_hashes: list[str], allow_expired: bool = False) -> dict:
    """Validate human-reviewed artifacts; do not manufacture provider evidence."""
    fields = {'schema_version', 'execution_sha256', 'plan_sha256', 'policy_sha256', 'stage',
              'execution_host', 'account_id', 'approved_by', 'approved_at', 'expires_at', 'rates',
              'balance_usd', 'input_allowance', 'context_window', 'billing_group', 'window_start',
              'window_end', 'checks', 'artifacts'}
    first_five = isinstance(evidence, dict) and evidence.get('schema_version') == FIRST_FIVE_SCHEMA
    if first_five:
        fields |= {'assumptions', 'first_five_policy_sha256'}
    if not isinstance(evidence, dict) or set(evidence) != fields:
        raise ValueError('launch evidence fields are missing or unexpected')
    if first_five and (stage != 'medium' or evidence['assumptions'] != FIRST_FIVE_ASSUMPTIONS
            or evidence['first_five_policy_sha256'] != digest((root / FIRST_FIVE_APPROVAL).read_bytes())):
        raise ValueError('first-five evidence must bind the approved medium-only assumptions')
    expected = {'schema_version': FIRST_FIVE_SCHEMA if first_five else 'inkling-launch-evidence-v1', 'execution_sha256': execution_sha256,
                'plan_sha256': plan_sha256, 'policy_sha256': policy_sha256, 'stage': stage,
                'execution_host': socket.gethostname()}
    if stage not in {'medium', 'max'} or any(evidence[k] != v for k, v in expected.items()):
        raise ValueError('launch evidence identity mismatch')
    if any(not text(evidence[k]) for k in ('account_id', 'billing_group', 'approved_by')):
        raise ValueError('human, account or billing attribution missing')
    now = datetime.now(timezone.utc)
    approved, expires = timestamp(evidence['approved_at']), timestamp(evidence['expires_at'])
    start, end = timestamp(evidence['window_start']), timestamp(evidence['window_end'])
    if approved > now:
        raise ValueError('approval cannot be in the future')
    if allow_expired:
        now = approved  # Reconciliation validates the original launch, after billing arrives.
    if (not now - timedelta(days=1) <= approved <= now or not now < expires <= approved + timedelta(days=1)
            or not start <= now < end or expires > end or end - start > timedelta(days=14)
            or any(dt.minute or dt.second or dt.microsecond for dt in (start, end))):
        raise ValueError('launch evidence or billing window is stale or invalid')
    allowance, context = evidence['input_allowance'], evidence['context_window']
    if (type(allowance) is not int or not 0 < allowance <= 32768 or type(context) is not int
            or context < allowance + CAP):
        raise ValueError('input allowance does not fit the context window')
    rates = evidence['rates']
    if not isinstance(rates, dict) or set(rates) != {'input_per_mtok', 'output_per_mtok'}:
        raise ValueError('rate schema mismatch')
    in_rate, out_rate = (finite_money(rates[k]) for k in ('input_per_mtok', 'output_per_mtok'))
    if min(in_rate, out_rate) <= 0:
        raise ValueError('positive verified rates required')
    worst = Decimal(1000) * (allowance * in_rate + CAP * out_rate) / Decimal(1_000_000)
    if worst > 250 or finite_money(evidence['balance_usd']) < Decimal(3000) + worst:
        raise ValueError('stage cost exceeds ceiling or available balance after reserve')
    if (not isinstance(evidence['checks'], dict) or not isinstance(evidence['artifacts'], dict)
            or set(evidence['checks']) != set(CHECKS) or set(evidence['artifacts']) != set(CHECKS)
            or any(evidence['checks'][name] is not (False if first_five and name in FIRST_FIVE_ASSUMPTIONS else True)
                   for name in CHECKS)):
        raise ValueError('required human evidence check missing')
    artifacts = {name: read_artifact(root, evidence['artifacts'][name]) for name in CHECKS}
    counts = json.loads(artifacts['input_counts'])
    if (counts.get('schema_version') != 'inkling-input-counts-v1' or counts.get('plan_sha256') != plan_sha256
            or counts.get('stage') != stage or counts.get('model') != MODEL or counts.get('endpoint') != BASE_URL):
        raise ValueError('input-count evidence identity mismatch')
    values = {}
    for row in counts.get('rows', []):
        if (set(row) != {'request_sha256', 'input_tokens'} or row['request_sha256'] in values
                or type(row['input_tokens']) is not int or not 0 < row['input_tokens'] <= allowance):
            raise ValueError('invalid or duplicate input count')
        values[row['request_sha256']] = row['input_tokens']
    if len(request_hashes) != len(set(request_hashes)) or set(values) != set(request_hashes):
        raise ValueError('input counts do not cover the exact stage requests')
    return {'input_counts': values, 'worst_case_usd': worst,
            'first_five_policy_sha256': evidence['first_five_policy_sha256'] if first_five else None,
            'account_sha256': digest(evidence['account_id'].encode()),
            'billing_group_sha256': digest(evidence['billing_group'].encode()),
            'evidence_sha256': sha256_json(evidence)}
