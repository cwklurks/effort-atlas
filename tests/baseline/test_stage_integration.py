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
from effort_atlas.inkling_stage_contract import load_policy, ACK_ENV, ACK_VALUE
from test_pilot import _row
import test_inkling_stage_contract as stage_contract_tests


class StageCollectionIntegrationTests(unittest.TestCase):
    @contextmanager
    def scenario(self, *, error=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            selection = root / SELECTION
            selection.parent.mkdir(parents=True)
            selection.write_bytes((ROOT / SELECTION).read_bytes())
            rows = [_row('mmlu_pro', index, category='business') for index in (1, 2)]
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
            policy['items_per_stage'] = 2  # This fixture is synthetic, never a launch policy.
            execution = {'execution_sha256': 'c'*64, 'policy_sha256': sha256_json(policy)}
            evidence = stage_contract_tests.StageEvidenceTests().fixture(root)
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
                def collect():
                    return runner.collect(plan,private,policy,execution,evidence,stage='medium',root=root,
                        env={ACK_ENV:ACK_VALUE,'TINKER_API_KEY':'synthetic'})
                yield root, private, requests, clients, collect

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
