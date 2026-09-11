"""Human-operated exploratory Inkling stages. Default is offline preflight.

Codex verification uses --mock only. --live requires a current, hash-bound human
launch record, an explicit environment acknowledgement and account credentials.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import fcntl
import importlib.metadata
import json
import os
import stat
from pathlib import Path
import tempfile
import uuid

from . import ROOT
from .confirmatory import sha256_json
from .inkling_baseline import MODEL, BASE_URL, CAP, build_request, client_options, parse_response, prepare
from .inkling_stage_contract import (ACK_ENV, ACK_VALUE, ACCOUNT_LEDGER, CHECKS, digest,
    execution_manifest, load_plan, load_policy, timestamp, validate_evidence)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _private_parent(path: Path, *, create: bool):
    absolute = path.absolute()
    if '..' in absolute.parts:
        raise ValueError('private artifact path cannot contain parent traversal')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in absolute.parts[1:-1]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        info = os.fstat(directory)
        if info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise ValueError('private artifacts require an owned private parent directory')
        yield directory, absolute.name
    finally:
        os.close(directory)


def _read_private_at(directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o777 != 0o600 or info.st_uid != os.getuid():
            raise ValueError('private artifact must be an owned regular file with mode 0600')
        return handle.read()


def _read_private(path: Path) -> bytes:
    with _private_parent(path, create=False) as (directory, name):
        return _read_private_at(directory, name)


def _write_private(path: Path, data: bytes) -> None:
    with _private_parent(path, create=True) as (directory, name):
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        except FileExistsError:
            if _read_private_at(directory, name) != data:
                raise ValueError('refusing to replace a changed private artifact')
            return
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(directory)


@contextmanager
def _runner_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with path.with_suffix('.runner.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another Inkling stage process owns this account') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _make_client(env: dict):
    if not env.get('TINKER_API_KEY'):
        raise ValueError('TINKER_API_KEY must be set in the launching environment')
    if importlib.metadata.version('anthropic') != '1.4.0':
        raise ValueError('use the pinned supplemental Anthropic environment')
    import anthropic
    import httpx2
    return anthropic.Anthropic(api_key=env['TINKER_API_KEY'], **client_options(),
        http_client=httpx2.Client(follow_redirects=False, trust_env=False))


def _request(client, request: dict) -> tuple[bytes, dict]:
    response = client.messages.with_raw_response.create(**request)
    return response.read(), {'provider_request_id': response.headers.get('request-id'),
                             'http_status': response.status_code}


def _identity(item: dict) -> str:
    return sha256_json({'dataset': item['dataset'], 'source_item_id': item['source_item_id']})


def evidence_template(manifest: dict, execution: dict, stage: str) -> dict:
    return {'schema_version': 'inkling-launch-evidence-v1', 'execution_sha256': execution['execution_sha256'],
            'plan_sha256': manifest['plan_sha256'], 'policy_sha256': execution['policy_sha256'],
            'stage': stage, 'execution_host': execution['execution_host'], 'account_id': None,
            'approved_by': None, 'approved_at': None, 'expires_at': None,
            'rates': {'input_per_mtok': None, 'output_per_mtok': None},
            'balance_usd': None, 'input_allowance': None, 'context_window': None,
            'billing_group': None, 'window_start': None, 'window_end': None,
            'checks': {name: False for name in CHECKS},
            'artifacts': {name: {'path': None, 'sha256': None} for name in CHECKS}}


def _validated(plan: dict, execution: dict, evidence: dict, stage: str, root: Path, *, allow_expired=False):
    return validate_evidence(evidence, root=root, plan_sha256=plan['plan_sha256'],
        policy_sha256=execution['policy_sha256'], execution_sha256=execution['execution_sha256'],
        stage=stage, request_hashes=[r[f'{stage}_request_sha256'] for r in plan['items']],
        allow_expired=allow_expired)


def _journal(path, policy, plan, valid, private, *, synthetic=False):
    from .inkling_accounting import InklingStageJournal
    return InklingStageJournal(path, policy=policy, plan_sha256=plan['plan_sha256'],
        account_sha256=valid['account_sha256'], billing_group_sha256=valid['billing_group_sha256'],
        item_ids=[_identity(item) for item in private], synthetic=synthetic)


def _grade_bytes(row, rendered, parsed, stage, root):
    from .baseline_upstream import score_baseline
    grade = score_baseline(row, rendered, parsed['text'],
                           upstream_root=root / '.cache_pilot/inkling_baseline_upstream')
    if grade['grading_status'] in {'grader_error', 'import_failed'}:
        raise ValueError('upstream scoring failed')
    return (json.dumps({'synthetic': False, 'phase': 'exploratory', 'dataset': row['dataset'],
                        'source_item_id': row['source_item_id'], 'effort': stage,
                        'native_stop_reason': parsed['native_stop_reason'], 'grade': grade}) + '\n').encode()


def _verify_saved(journal, plan, private, rows, rendered, stage, root):
    attempts = journal.snapshot()['stages'][stage]['attempts']
    directory = root / 'results_pilot/inkling_tinker_baseline/collection' / plan['plan_sha256'] / stage
    for index, item in enumerate(private):
        identity = _identity(item)
        record = attempts.get(identity)
        if record is None:
            continue
        if record['status'] != 'complete':
            raise ValueError('prior attempt is uncertain; automatic resubmission is forbidden')
        raw = _read_private(directory / f'{identity}.response.private.json')
        if digest(raw) != record['response_sha256']:
            raise ValueError('recorded private response bytes changed')
        envelope = json.loads(raw)
        parsed = parse_response(json.loads(base64.b64decode(envelope['raw_response_base64'], validate=True)), cap=CAP)
        if (parsed['generation_id'] != record['provider_response_id']
                or parsed['input_tokens_reported'] != record['prompt_tokens']
                or parsed['output_tokens_reported'] != record['completion_tokens']
                or parsed['native_stop_reason'] != record['native_stop_reason']):
            raise ValueError('saved response differs from journal accounting')
        # Missing grades can be restored without a provider call; changed grades refuse.
        _write_private(directory / f'{identity}.grade.private.json',
                       _grade_bytes(rows[index], rendered[index], parsed, stage, root))


def collect(plan: dict, private: list[dict], policy: dict, execution: dict, evidence: dict,
            *, stage: str, root: Path = ROOT, env: dict | None = None,
            max_new_requests: int | None = None) -> dict:
    """Validate identically for CLI and direct calls, before constructing a client."""
    if max_new_requests is not None and (
            type(max_new_requests) is not int or not 1 <= max_new_requests <= 1000):
        raise ValueError('max_new_requests must be an integer from 1 to 1000')
    env = os.environ if env is None else env
    if policy != load_policy(root) or execution != execution_manifest(plan, policy, root=root):
        raise ValueError('direct launch differs from the current approved policy or execution')
    valid = _validated(plan, execution, evidence, stage, root)
    if env.get(ACK_ENV) != ACK_VALUE:
        raise ValueError(f'{ACK_ENV} must explicitly acknowledge verified stage evidence')
    if not env.get('TINKER_API_KEY'):
        raise ValueError('TINKER_API_KEY must be set in the launching environment')
    # Re-render from verified original sources before any reservation/submission.
    refreshed = prepare(root=root)
    current_plan, current_private = load_plan(Path(refreshed['directory']), root=root)
    if current_plan != plan or current_private != private:
        raise ValueError('current source and preparation bytes differ from approved plan')
    from .baseline_upstream import render_baseline
    from .pilot_integrity import load_selected_items
    from .inkling_baseline import DATASETS, SELECTION
    selection = json.loads((root / SELECTION).read_text())
    rows = load_selected_items({'pilot': {'datasets': list(DATASETS)}}, selection, cap_dir=root / 'capabilities')
    rendered = [render_baseline(row, seed=20260830)[0] for row in rows]
    out = root / 'results_pilot/inkling_tinker_baseline/collection' / plan['plan_sha256'] / stage
    with _runner_lock(ACCOUNT_LEDGER):
        journal = _journal(ACCOUNT_LEDGER, policy, plan, valid, private)
        if stage == 'max':
            _verify_saved(journal, plan, private, rows, rendered, 'medium', root)
        _reserve_if_new(journal, stage, evidence)
        _verify_saved(journal, plan, private, rows, rendered, stage, root)
        if journal.snapshot()['stages'][stage]['status'] in {'finished', 'reconciled'}:
            return journal.snapshot()
        _write_private(out / f'launch-evidence.{valid["evidence_sha256"]}.private.json', (json.dumps(evidence, indent=2) + '\n').encode())
        new_response_count = 0
        with _make_client(env) as client:
            for index, item in enumerate(private):
                identity = _identity(item)
                record = journal.snapshot()['stages'][stage]['attempts'].get(identity)
                raw_path = out / f'{identity}.response.private.json'
                if record is not None:
                    if record['status'] != 'complete' or digest(_read_private(raw_path)) != record['response_sha256']:
                        raise ValueError('prior attempt is uncertain or its private response is missing/changed')
                    continue
                if max_new_requests is not None and new_response_count >= max_new_requests:
                    # Keep the full stage reservation and all remaining items pending.
                    # A later invocation authenticates saved rows and continues this plan.
                    return {**journal.snapshot(), 'invocation_status': 'paused',
                            'new_response_count': new_response_count}
                if datetime.now(timezone.utc) >= timestamp(evidence['expires_at']):
                    raise ValueError('launch evidence expired; stop before the next submission')
                request = build_request(item['template'], stage)
                request_id = str(uuid.uuid4())
                journal.begin_attempt(stage, item_id=identity, request_id=request_id)
                try:
                    raw, headers = _request(client, request)
                    envelope = (json.dumps({'raw_response_base64': base64.b64encode(raw).decode(),
                        'local_request_id': request_id, 'received_at': _utc(),
                        'launch_evidence_sha256': valid['evidence_sha256'],
                        'execution_sha256': execution['execution_sha256'], **headers}) + '\n').encode()
                    _write_private(raw_path, envelope)
                    parsed = parse_response(json.loads(raw), cap=CAP)
                    expected_input = valid['input_counts'][sha256_json(request)]
                    if parsed['input_tokens_reported'] != expected_input:
                        raise ValueError('reported input usage differs from the verified count')
                    _write_private(out / f'{identity}.grade.private.json',
                                   _grade_bytes(rows[index], rendered[index], parsed, stage, root))
                    journal.record_response(stage, item_id=identity, request_id=request_id,
                        provider_response_id=parsed['generation_id'], prompt_tokens=parsed['input_tokens_reported'],
                        completion_tokens=parsed['output_tokens_reported'], native_stop_reason=parsed['native_stop_reason'],
                        response_sha256=digest(envelope))
                    new_response_count += 1
                except BaseException as exc:
                    response = getattr(exc, 'response', None)
                    try:
                        error_body = response.content if response is not None else b''
                        _write_private(out / f'{identity}.error.private.json',
                            (json.dumps({'error_class': type(exc).__name__, 'local_request_id': request_id,
                                         'received_at': _utc(), 'raw_error_base64': base64.b64encode(error_body).decode()}) + '\n').encode())
                    except Exception:
                        pass  # Disk failure cannot authorize another submission.
                    # Every uncertain outcome is durably blocked; never include exception text.
                    try:
                        journal.block_attempt(stage, item_id=identity, request_id=request_id, error_class=type(exc).__name__)
                    except Exception:
                        pass  # A prior response validation may already have durably blocked it.
                    raise
        journal.finish_stage(stage)
        return journal.snapshot()


def _reserve_if_new(journal, stage, evidence):
    snapshot = journal.snapshot()['stages'].get(stage, {'status': 'not_started'})
    if snapshot['status'] == 'not_started':
        journal.reserve_stage(stage, input_allowance=evidence['input_allowance'],
            input_rate_per_million=Decimal(str(evidence['rates']['input_per_mtok'])),
            output_rate_per_million=Decimal(str(evidence['rates']['output_per_mtok'])),
            verified_balance_usd=Decimal(str(evidence['balance_usd'])),
            balance_evidence_sha256=evidence['artifacts']['balance']['sha256'],
            window_start=timestamp(evidence['window_start']), window_end=timestamp(evidence['window_end']))
    else:
        config = snapshot.get('configuration') or {}
        if (config.get('input_allowance') != evidence['input_allowance']
                or Decimal(config.get('input_rate_per_million', '-1')) != Decimal(str(evidence['rates']['input_per_mtok']))
                or Decimal(config.get('output_rate_per_million', '-1')) != Decimal(str(evidence['rates']['output_per_mtok']))
                or timestamp(config.get('window_start')) != timestamp(evidence['window_start'])
                or timestamp(config.get('window_end')) != timestamp(evidence['window_end'])):
            raise ValueError('resume configuration differs from the reserved stage')
        if snapshot['status'] == 'blocked' or any(
                row['status'] != 'complete' for row in snapshot['attempts'].values()):
            raise ValueError('uncertain stage or pending attempt requires manual reconciliation')


def count_inputs(plan, private, stage, destination: Path, *, env=None, root: Path = ROOT):
    """Human-initiated tokenizer requests only; Codex does not execute this path."""
    env = os.environ if env is None else env
    if env.get('EFFORT_ATLAS_INKLING_COUNT_ACK') != 'I_APPROVE_INPUT_TOKEN_COUNTING':
        raise ValueError('explicit input-count acknowledgement required')
    if stage not in {'medium', 'max'}:
        raise ValueError('input counts require an approved effort stage')
    load_policy(root)
    current = prepare(root=root)
    current_plan, current_private = load_plan(Path(current['directory']), root=root)
    if plan != current_plan or private != current_private:
        raise ValueError('input counting requires the current verified baseline requests')
    counts = []
    with _make_client(env) as client:
        for item in private:
            request = build_request(item['template'], stage)
            result = client.messages.count_tokens(model=MODEL, messages=request['messages'],
                extra_body={'max_tokens': CAP, **request['extra_body']})
            value = result.input_tokens
            if type(value) is not int or value <= 0:
                raise ValueError('invalid input count')
            counts.append({'request_sha256': sha256_json(request), 'input_tokens': value})
    report = {'schema_version': 'inkling-input-counts-v1', 'plan_sha256': plan['plan_sha256'],
              'stage': stage, 'endpoint': BASE_URL, 'model': MODEL, 'rows': counts}
    _write_private(destination, (json.dumps(report, indent=2) + '\n').encode())
    return {'model_generations': 0, 'input_count_requests': len(counts), 'path': str(destination)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, help='existing preparation directory; otherwise prepare offline')
    parser.add_argument('--stage', choices=('medium', 'max'), default='medium')
    parser.add_argument('--evidence', type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true', help='default: offline preflight only')
    modes.add_argument('--live', action='store_true', help='human launch, requires all bound evidence')
    modes.add_argument('--mock', action='store_true', help='synthetic stage accounting rehearsal only')
    modes.add_argument('--count-inputs', type=Path, metavar='OUTPUT', help='human tokenizer requests; no generation')
    modes.add_argument('--reconcile', type=Path, metavar='RECORD', help='read local billing evidence; no provider call')
    parser.add_argument('--write-evidence-template', type=Path)
    parser.add_argument('--max-new-requests', type=int, metavar='N',
                        help='with --live, pause after at most N new requests; retain the full stage reservation')
    args = parser.parse_args()
    if args.max_new_requests is not None and not args.live:
        parser.error('--max-new-requests requires --live')
    try:
        directory = args.plan or Path(prepare()['directory'])
        plan, private = load_plan(directory)
        policy = load_policy()
        execution = execution_manifest(plan, policy)
        evidence = json.loads(args.evidence.read_text()) if args.evidence else None
        if args.write_evidence_template:
            if args.live or args.reconcile or args.count_inputs:
                raise ValueError('write the evidence template during offline preflight only')
            _write_private(args.write_evidence_template,
                (json.dumps(evidence_template(plan, execution, args.stage), indent=2) + '\n').encode())
        if args.live:
            result = collect(plan, private, policy, execution, evidence, stage=args.stage,
                             max_new_requests=args.max_new_requests)
        elif args.count_inputs:
            result = count_inputs(plan, private, args.stage, args.count_inputs)
        elif args.reconcile:
            from .inkling_billing import read_billing_evidence
            valid = _validated(plan, execution, evidence, args.stage, ROOT, allow_expired=True)
            billing_record = json.loads(args.reconcile.read_text())
            if billing_record['plan_sha256'] != plan['plan_sha256'] or billing_record['stage'] != args.stage:
                raise ValueError('billing record does not match this stage')
            billing = read_billing_evidence(ROOT, billing_record)
            with _runner_lock(ACCOUNT_LEDGER):
                journal = _journal(ACCOUNT_LEDGER, policy, plan, valid, private)
                journal.settle_stage(args.stage, evidence=billing)
                result = journal.snapshot()
        elif args.mock:
            result = rehearse(plan, private, policy)
        else:
            failures = []
            try:
                _validated(plan, execution, evidence, args.stage, ROOT)
            except (ValueError, TypeError, KeyError, OSError):
                failures.append('current host-bound launch evidence is absent or invalid')
            result = {'mode': 'dry_run', 'model_calls': 0, 'launch_ready': False,
                      'stage_ceilings_usd': policy['stage_ceilings_usd'], 'execution': execution,
                      'missing_evidence': failures, 'next': 'verify account/route artifacts and independently review the exact execution hash'}
        print(json.dumps(result, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'stage_refused', 'error_class': type(exc).__name__}))
        return 2


def rehearse(plan, private, policy):
    """A local, clearly synthetic ledger exercises all 1,000 planned identities."""
    from .inkling_accounting import BillingEvidence
    now = datetime.now(timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)
    valid = {'account_sha256': digest(b'synthetic-account'), 'billing_group_sha256': digest(b'synthetic-group')}
    with tempfile.TemporaryDirectory(prefix='inkling-stage-mock-') as tmp:
        path = Path(tmp) / 'mock-ledger.jsonl'
        journal = _journal(path, policy, plan, valid, private, synthetic=True)
        journal.reserve_stage('medium', input_allowance=32768, input_rate_per_million=Decimal('1.87'),
            output_rate_per_million=Decimal('4.68'), verified_balance_usd=Decimal(5000),
            balance_evidence_sha256=digest(b'synthetic-balance'), window_start=start, window_end=end)
        for item in private:
            identity = _identity(item)
            request_id = f'synthetic-{identity}'
            journal.begin_attempt('medium', item_id=identity, request_id=request_id)
            journal.record_response('medium', item_id=identity, request_id=request_id,
                provider_response_id=f'synthetic-response-{identity}', prompt_tokens=10, completion_tokens=20,
                native_stop_reason='end_turn', response_sha256=digest(b'synthetic-response'))
        journal.finish_stage('medium')
        # This is simulated account evidence, never a provider receipt.
        journal.settle_stage('medium', evidence=BillingEvidence(**valid, model=MODEL,
            window_start=start, window_end=end, prompt_tokens=10000,
            completion_tokens=20000, account_deduction_usd=Decimal('0.1123'),
            manifest_sha256=digest(b'synthetic-reconciliation'), source_sha256s=(digest(b'synthetic-export'),), complete=True))
        snapshot = journal.snapshot()
        destination = ROOT / 'results_pilot/inkling_tinker_baseline/accounting_mock' / plan['plan_sha256'] / str(uuid.uuid4())
        _write_private(destination / 'ledger.jsonl', path.read_bytes())
        return {'synthetic': True, 'phase': 'mock_only', 'model_calls': 0, 'items': len(private),
                'plan_sha256': plan['plan_sha256'], 'directory': str(destination),
                'accounting': {k: v for k, v in snapshot.items() if k != 'stages'}}


if __name__ == '__main__':
    raise SystemExit(main())
