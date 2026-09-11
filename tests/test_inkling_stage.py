"""Run boundary checks without an SDK or model calls."""
from pathlib import Path
import tempfile
import json
import base64
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, Mock

from effort_atlas import inkling_stage as stage
from effort_atlas.inkling_stage_contract import load_policy


class StageBoundaryTests(unittest.TestCase):
    def counting_cli_error(self, error):
        output = io.StringIO()
        with patch('sys.argv', ['inkling_stage', '--count-inputs', '/unused/counts.json']), \
             patch.object(stage, 'prepare', return_value={'directory': '/unused'}), \
             patch.object(stage, 'load_plan', return_value=({}, [])), \
             patch.object(stage, 'load_policy', return_value={}), \
             patch.object(stage, 'execution_manifest', return_value={}), \
             patch.object(stage, 'count_inputs', side_effect=error), redirect_stdout(output):
            self.assertEqual(stage.main(), 2)
        return json.loads(output.getvalue())

    def test_count_cli_explains_missing_key_in_the_launching_terminal(self):
        with self.assertRaises(ValueError) as raised:
            stage._make_client({})
        result = self.counting_cli_error(raised.exception)
        self.assertEqual(result['error_code'], 'api_key_missing')
        self.assertIn('same terminal', result['message'])

    def test_cli_does_not_echo_unrecognized_exception_details(self):
        secret = 'private-test-credential-and-response-text'
        for error in (ValueError(secret), RuntimeError(secret)):
            with self.subTest(error=type(error).__name__):
                result = self.counting_cli_error(error)
                self.assertNotIn(secret, json.dumps(result))
                self.assertNotIn('message', result)

    def test_invalid_invocation_limit_stops_before_client_or_reservation(self):
        for limit in (0, -1, True, 1.5, 1001):
            with self.subTest(limit=limit), patch.object(stage, '_make_client') as client, \
                 patch.object(stage, '_journal') as journal:
                with self.assertRaisesRegex(ValueError, 'max_new_requests'):
                    stage.collect({}, [], {}, {}, {}, stage='medium', env={}, max_new_requests=limit)
                client.assert_not_called()
                journal.assert_not_called()

    def test_direct_call_cannot_replace_approved_policy(self):
        with patch.object(stage, '_make_client') as client:
            with self.assertRaisesRegex(ValueError, 'approved policy'):
                stage.collect({'plan_sha256': 'a'*64}, [], {}, {}, {}, stage='medium', env={})
            client.assert_not_called()

    def test_missing_evidence_stops_before_client_or_reservation(self):
        policy=load_policy()
        plan={'plan_sha256':'a'*64, 'items':[]}
        execution={'execution_sha256':'b'*64,'policy_sha256':'c'*64}
        with patch.object(stage, 'execution_manifest', return_value=execution), \
             patch.object(stage, '_make_client') as client, patch.object(stage, '_journal') as journal:
            with self.assertRaises(ValueError):
                stage.collect(plan, [], policy, execution, None, stage='medium', env={})
            client.assert_not_called(); journal.assert_not_called()

    def test_counting_requires_separate_human_invocation(self):
        with patch.object(stage, '_make_client') as client:
            with self.assertRaises(ValueError):
                stage.count_inputs({}, [], 'medium', Path('/unused'), env={})
            client.assert_not_called()

    def test_direct_counting_cannot_send_unapproved_templates(self):
        with patch.object(stage, '_make_client') as client, patch.object(stage, '_write_private'), \
             patch.object(stage, 'prepare', return_value={'directory': '/synthetic'}), \
             patch.object(stage, 'load_plan', return_value=({'plan_sha256': 'a'*64}, [{'template': 'approved'}])):
            with self.assertRaises(ValueError):
                stage.count_inputs({'plan_sha256': 'a'*64}, [], 'medium', Path('/unused'),
                    env={'EFFORT_ATLAS_INKLING_COUNT_ACK': 'I_APPROVE_INPUT_TOKEN_COUNTING', 'TINKER_API_KEY': 'synthetic'})
            client.assert_not_called()

    def test_private_results_are_durable_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td).resolve()/'private'/'response.json'
            stage._write_private(path,b'{"synthetic":true}')
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777,0o700)
            stage._write_private(path,b'{"synthetic":true}')
            with self.assertRaises(ValueError): stage._write_private(path,b'changed')
            self.assertEqual(path.read_bytes(),b'{"synthetic":true}')

    def test_existing_public_file_and_symlinked_parent_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            public = root / 'existing.json'
            public.write_bytes(b'same')
            public.chmod(0o644)
            with self.assertRaises(ValueError): stage._write_private(public, b'same')
            target = root / 'target'
            target.mkdir(mode=0o700)
            link = root / 'linked'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises((OSError, ValueError)): stage._write_private(link / 'response.json', b'private')
            self.assertFalse((target / 'response.json').exists())

    def test_saved_response_restores_missing_grade_but_refuses_changed_grade(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            item = {'dataset': 'synthetic', 'source_item_id': 'one'}
            identity = stage._identity(item)
            plan = {'plan_sha256': 'a'*64}
            body = {'id': 'synthetic-response', 'model': stage.MODEL, 'role': 'assistant', 'type': 'message',
                    'content': [{'type': 'text', 'text': 'Final answer: A'}],
                    'usage': {'input_tokens': 10, 'output_tokens': 20}, 'stop_reason': 'end_turn'}
            envelope = json.dumps({'raw_response_base64': base64.b64encode(json.dumps(body).encode()).decode()}).encode()
            directory = root / 'results_pilot/inkling_tinker_baseline/collection' / plan['plan_sha256'] / 'medium'
            stage._write_private(directory / f'{identity}.response.private.json', envelope)
            record = {'status': 'complete', 'response_sha256': stage.digest(envelope),
                      'provider_response_id': 'synthetic-response', 'prompt_tokens': 10,
                      'completion_tokens': 20, 'native_stop_reason': 'end_turn'}
            journal = Mock()
            journal.snapshot.return_value = {'stages': {'medium': {'attempts': {identity: record}}}}
            grade_path = directory / f'{identity}.grade.private.json'
            with patch.object(stage, '_grade_bytes', return_value=b'correct synthetic grade'):
                stage._verify_saved(journal, plan, [item], [{}], [None], 'medium', root)
                self.assertEqual(grade_path.read_bytes(), b'correct synthetic grade')
                grade_path.write_bytes(b'changed grade')
                with self.assertRaises(ValueError):
                    stage._verify_saved(journal, plan, [item], [{}], [None], 'medium', root)

    def test_account_lock_rejects_second_process_owner(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Path(td).resolve()/'journal.jsonl'
            with stage._runner_lock(ledger):
                with self.assertRaises(ValueError):
                    with stage._runner_lock(ledger): self.fail('second lock acquired')


if __name__ == '__main__': unittest.main()
