"""Exercise the collection boundary with real upstream prompts and SDK, offline."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import anthropic
import httpx2

from effort_atlas import ROOT
from effort_atlas import inkling_stage as runner
from effort_atlas.baseline_upstream import render_baseline
from effort_atlas.confirmatory import sha256_json
from effort_atlas.inkling_baseline import MODEL, CAP, SELECTION, build_request, client_options
from effort_atlas.inkling_stage_contract import (load_policy, ACK_ENV, ACK_VALUE, FIRST_FIVE_ACK,
    FIRST_FIVE_SCHEMA, FIRST_FIVE_ASSUMPTIONS, FIRST_FIVE_APPROVAL)
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from test_pilot import _row
import test_inkling_stage_contract as stage_contract_tests


class StageCollectionIntegrationTests(unittest.TestCase):
    @contextmanager
    def scenario(self, *, error=False, count=2, first_five=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            selection = root / SELECTION
            selection.parent.mkdir(parents=True)
            selection.write_bytes((ROOT / SELECTION).read_bytes())
            rows = [_row('mmlu_pro', index, category='business') for index in range(1, count + 1)]
            private, items = [], []
            for row in rows:
                rendered, temperature = render_baseline(row, seed=20260830)
                template = {'model': MODEL, 'max_tokens': CAP, 'temperature': temperature,
                            'messages': [{'role': 'user', 'content': rendered.prompt}]}
                private.append({'dataset': row['dataset'], 'source_item_id': row['source_item_id'],
                                'source_row_index': row['source_row_index'], 'template': template,
                                'gold_letter': rendered.gold_letter, 'choice_permutation': rendered.choice_permutation})
                items.append({f'{stage}_request_sha256': sha256_json(build_request(template, stage)) for stage in ('medium','max')})
            plan = {'plan_sha256': 'b'*64, 'items': items}
            policy = deepcopy(load_policy())
            policy['items_per_stage'] = count  # This fixture is synthetic, never a launch policy.
            execution = {'execution_sha256': 'c'*64, 'policy_sha256': sha256_json(policy)}
            evidence = stage_contract_tests.StageEvidenceTests().fixture(root)
            approval = root / FIRST_FIVE_APPROVAL
            approval.parent.mkdir(parents=True, exist_ok=True)
            approval.write_bytes((ROOT / FIRST_FIVE_APPROVAL).read_bytes())
            if first_five:
                evidence.update(schema_version=FIRST_FIVE_SCHEMA, assumptions=dict(FIRST_FIVE_ASSUMPTIONS),
                    first_five_policy_sha256=hashlib.sha256(approval.read_bytes()).hexdigest())
                for name in FIRST_FIVE_ASSUMPTIONS:
                    evidence['checks'][name] = False
            evidence['policy_sha256'] = sha256_json(policy)
            count_ref = evidence['artifacts']['input_counts']
            count_path = root / count_ref['path']
            counts = json.loads(count_path.read_text())
            counts['rows'] = [{'request_sha256': item['medium_request_sha256'], 'input_tokens': 12} for item in items]
            count_path.write_text(json.dumps(counts))
            count_ref['sha256'] = hashlib.sha256(count_path.read_bytes()).hexdigest()
            requests, clients = [], []
            def handler(request):
                requests.append(request)
                if error:
                    return httpx2.Response(500, json={'type':'error','error':{'type':'api_error','message':'synthetic provider error'}})
                return httpx2.Response(200, headers={'request-id':f'provider-{len(requests)}'}, json={
                    'id':f'synthetic-response-{len(requests)}','type':'message','role':'assistant','model':MODEL,
                    'content':[{'type':'text','text':'Final answer: A'}], 'stop_reason':'end_turn',
                    'usage':{'input_tokens':12,'output_tokens':20}})
            def factory(env):
                client = anthropic.Anthropic(api_key='synthetic', **client_options(),
                    http_client=httpx2.Client(transport=httpx2.MockTransport(handler), follow_redirects=False, trust_env=False))
                clients.append(client)
                return client
            original_journal = runner._journal
            def synthetic_journal(*args, **kwargs):
                return original_journal(*args, **kwargs, synthetic=True)
            with ExitStack() as stack:
                for target, value in (
                    ('load_policy', policy), ('execution_manifest', execution),
                    ('prepare', {'directory':str(root),'plan_sha256':plan['plan_sha256']}),
                    ('load_plan', (plan,private))):
                    stack.enter_context(patch.object(runner,target,return_value=value))
                stack.enter_context(patch('effort_atlas.pilot_integrity.load_selected_items',return_value=rows))
                stack.enter_context(patch.object(runner,'ACCOUNT_LEDGER',root/'account'/'ledger.jsonl'))
                stack.enter_context(patch.object(runner,'_make_client',side_effect=factory))
                stack.enter_context(patch.object(runner,'_journal',side_effect=synthetic_journal))
                def collect(**kwargs):
                    return runner.collect(plan,private,policy,execution,evidence,stage='medium',root=root,
                        env={ACK_ENV:FIRST_FIVE_ACK if first_five else ACK_VALUE,'TINKER_API_KEY':'synthetic'}, **kwargs)
                def review(snapshot):
                    value = runner.first_five_review_template(snapshot, execution)
                    value.update(reviewed_by='Synthetic reviewer', reviewed_at=datetime.now(timezone.utc).isoformat(),
                                 authorize_remaining=True)
                    value['checks'] = {name: True for name in runner.REVIEW_CHECKS}
                    for name in value['artifacts']:
                        p = root / 'results_pilot' / f'review-{name}.json'
                        p.write_text('Synthetic review and billing evidence only')
                        value['artifacts'][name] = {'path':str(p.relative_to(root)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                    return value
                collect.review = review
                collect.evidence = evidence
                collect.execution = execution
                collect.journal = lambda: original_journal(root/'account'/'ledger.jsonl', policy, plan,
                    runner._validated(plan, execution, evidence, 'medium', root), private, synthetic=True)
                yield root, private, requests, clients, collect

    def test_pause_after_five_and_resume_keeps_reservation_and_never_repeats_items(self):
        with self.scenario(count=6) as (root, private, requests, clients, collect):
            paused = collect(max_new_requests=5)
            self.assertEqual(len(requests), 5)
            self.assertEqual(paused['invocation_status'], 'paused_for_review')
            self.assertEqual(paused['new_response_count'], 5)
            self.assertEqual(paused['stages']['medium']['response_count'], 5)
            self.assertNotIn(paused['stages']['medium']['status'], {'finished', 'reconciled'})
            reservation = paused['reserved_usd']
            self.assertNotEqual(reservation, '0')
            held = collect()
            self.assertEqual(held['invocation_status'], 'paused_for_review')
            self.assertEqual(len(requests), 5)
            self.assertEqual(len(clients), 1)
            finished = collect(max_new_requests=5, first_five_review=collect.review(paused))
            self.assertEqual(len(requests), 6)
            self.assertEqual(finished['stages']['medium']['status'], 'finished')
            self.assertEqual(finished['stages']['medium']['response_count'], 6)
            self.assertEqual(finished['reserved_usd'], reservation)
            self.assertEqual(len({request.content for request in requests}), 6)
            collect(max_new_requests=5)
            self.assertEqual(len(requests), 6)
            self.assertEqual(len(clients), 2)

    def test_no_optional_flag_and_repeated_small_invocations_cannot_send_sixth(self):
        with self.scenario(count=6) as (_, _, requests, clients, collect):
            for _ in range(5):
                paused = collect(max_new_requests=1)
            self.assertEqual(len(requests), 5)
            for limit in (None, 5, 1000):
                held = collect(max_new_requests=limit)
                self.assertEqual(held['new_response_count'], 0)
            self.assertEqual(len(requests), 5)
            self.assertEqual(len(clients), 5)

    def test_full_v1_cannot_create_initial_medium_reservation(self):
        with self.scenario(first_five=False) as (root, _, requests, clients, collect):
            with self.assertRaisesRegex(ValueError, 'initial medium'):
                collect()
            self.assertEqual(requests, [])
            self.assertEqual(clients, [])
            self.assertFalse((root / 'account/ledger.jsonl').exists())

    def test_stale_wrong_and_unapproved_reviews_do_not_release_sixth(self):
        with self.scenario(count=6) as (root, _, requests, clients, collect):
            paused = collect()
            review = collect.review(paused)
            changes = ({'authorize_remaining':False}, {'execution_sha256':'x'*64},
                       {'responses':list(reversed(review['responses']))},
                       {'reviewed_at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()},
                       {'checks':{name:False for name in runner.REVIEW_CHECKS}})
            for change in changes:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    collect(first_five_review={**review, **change})
            (root / review['artifacts']['billing']['path']).write_text('tampered')
            with self.assertRaises(ValueError): collect(first_five_review=review)
            self.assertEqual(len(requests), 5)
            self.assertEqual(len(clients), 1)

    def test_replacement_v1_evidence_cannot_remove_saved_first_five_restriction(self):
        with self.scenario(count=6) as (_, _, requests, clients, collect):
            collect()
            evidence = collect.evidence
            evidence['schema_version'] = 'inkling-launch-evidence-v1'
            evidence.pop('assumptions')
            evidence.pop('first_five_policy_sha256')
            evidence['checks'] = {name:True for name in evidence['checks']}
            # Use the ordinary acknowledgement to exercise the saved journal gate.
            with patch.object(runner, 'ACK_VALUE', FIRST_FIVE_ACK):
                with self.assertRaisesRegex(ValueError, 'cannot be bypassed'):
                    collect()
            self.assertEqual(len(requests), 5)
            self.assertEqual(len(clients), 1)

    def test_saved_review_cannot_authorize_changed_execution(self):
        with self.scenario(count=8) as (_, _, requests, clients, collect):
            paused = collect()
            collect(first_five_review=collect.review(paused), max_new_requests=1)
            self.assertEqual(len(requests), 6)
            collect.execution['execution_sha256'] = 'd'*64
            collect.evidence['execution_sha256'] = 'd'*64
            with self.assertRaisesRegex(ValueError, 'different execution'):
                collect()
            self.assertEqual(len(requests), 6)
            self.assertEqual(len(clients), 2)

    def test_legacy_empty_unrestricted_reservation_cannot_bypass_initial_gate(self):
        with self.scenario(count=6, first_five=False) as (_, _, requests, clients, collect):
            e = collect.evidence
            collect.journal().reserve_stage('medium', input_allowance=e['input_allowance'],
                input_rate_per_million=Decimal(str(e['rates']['input_per_mtok'])),
                output_rate_per_million=Decimal(str(e['rates']['output_per_mtok'])),
                verified_balance_usd=Decimal(e['balance_usd']),
                balance_evidence_sha256=e['artifacts']['balance']['sha256'],
                window_start=runner.timestamp(e['window_start']), window_end=runner.timestamp(e['window_end']))
            with self.assertRaisesRegex(ValueError, 'legacy unrestricted'):
                collect()
            self.assertEqual(requests, [])
            self.assertEqual(clients, [])

    def test_pause_does_not_allow_resume_with_a_changed_saved_response(self):
        with self.scenario() as (root, private, requests, clients, collect):
            collect(max_new_requests=1)
            identity = runner._identity(private[0])
            folder = root / 'results_pilot/inkling_tinker_baseline/collection' / ('b'*64) / 'medium'
            (folder / f'{identity}.response.private.json').write_text('tampered')
            with self.assertRaises(ValueError):
                collect(max_new_requests=1)
            self.assertEqual(len(requests), 1)
            self.assertEqual(len(clients), 1)

    def test_actual_sdk_collection_and_clean_restart_do_not_resubmit(self):
        with self.scenario() as (root, private, requests, clients, collect):
            result = collect()
            self.assertEqual(result['stages']['medium']['response_count'],2)
            self.assertEqual(result['stages']['medium']['status'],'finished')
            self.assertNotEqual(result['reserved_usd'],'0')
            for request in requests:
                body=json.loads(request.content)
                self.assertEqual(body['max_tokens'],32768)
                self.assertEqual(body['output_config']['effort'],'medium')
            identity=runner._identity(private[0])
            folder=root/'results_pilot/inkling_tinker_baseline/collection'/('b'*64)/'medium'
            saved=json.loads((folder/f'{identity}.response.private.json').read_text())
            self.assertEqual(saved['provider_request_id'],'provider-1')
            (folder/f'{identity}.grade.private.json').unlink()
            collect()
            self.assertTrue((folder/f'{identity}.grade.private.json').exists())
            self.assertEqual(len(requests),2)
            self.assertEqual(len(clients),1)
            (folder/f'{identity}.grade.private.json').write_text('tampered')
            with self.assertRaises(ValueError): collect()
            self.assertEqual(len(clients),1)

    def test_actual_sdk_error_holds_stage_and_restart_sends_nothing(self):
        with self.scenario(error=True) as (root, private, requests, clients, collect):
            with self.assertRaises(anthropic.APIError): collect()
            self.assertEqual(len(requests),1)
            with self.assertRaises(ValueError): collect()
            self.assertEqual(len(requests),1)
            self.assertEqual(len(clients),1)
            ledger=(root/'account/ledger.jsonl').read_text()
            self.assertIn('block_attempt',ledger)
            self.assertIn('mock_only',ledger)


if __name__ == '__main__': unittest.main()
