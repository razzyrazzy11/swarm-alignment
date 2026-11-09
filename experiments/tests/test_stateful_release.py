import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from experiments import stateful_release as release
from experiments.stateful_study import episode, tasks_for, score_stateful
from experiments.stateful_influence import FIRST, SECOND, WARNING, MESSAGES, execute_choice
from experiments.stateful import make_public


class StatefulReleaseTests(unittest.TestCase):
    def fixture(self, root):
        folder = root/'runs/test-main'
        folder.mkdir(parents=True)
        es = [episode(990000, 'sequential', 0), episode(990001, 'sequential', 1)]
        ts = [t for e in es for t in tasks_for(e)]
        model = 'test-reader'
        order = [(t['task_id'], model) for t in ts]
        random.Random(9).shuffle(order)
        indexed = {t['task_id']: t for t in ts}
        attempts, rows = [], []
        for tid, m in order:
            t = indexed[tid]
            labels = t['compatible_labels']
            answer = dict(status='ABSTAIN', worker_id=None)
            if len(labels) == 1:
                answer = dict(status='NONE' if labels[0] == 'NONE' else 'EXECUTOR',
                              worker_id=None if labels[0] == 'NONE' else labels[0])
            response = dict(status='completed', output_text=json.dumps(answer), model=model,
                            id='PRIVATE_PROVIDER_ID', headers={'Authorization': 'PRIVATE_HEADER'},
                            reasoning='PRIVATE_REASONING', usage=dict(input_tokens=100, output_tokens=10, cost=.001))
            attempts.append(dict(task_id=tid, model=m, reserved_credits='.1'))
            rows.append(dict(task=t, model=m, response=response,
                             transport=dict(http_status=200, latency_seconds=.1), estimated_credits='.001',
                             scored=score_stateful(response, labels)))
        summary = dict(complete=True, planned_calls=len(order), attempted_calls=len(order), retained_responses=len(rows))
        for name, data in [('episodes.json', es), ('packets.json', ts), ('manifest.json', dict(order=order)), ('summary.json', summary)]:
            release.write_json(folder/name, data)
        release.write_rows(folder/'attempts.jsonl', attempts)
        release.write_rows(folder/'responses.jsonl', rows)
        return folder, [model], es, ts, order

    def test_allowlist_replay_and_reported_cost(self):
        with tempfile.TemporaryDirectory() as d:
            args = self.fixture(Path(d))
            rows, es, report = release.verify_core(*args)
            self.assertEqual(report['status'], 'complete')
            self.assertEqual(report['planned_calls'], 20)
            self.assertEqual(report['returned_calls'], 20)
            self.assertEqual(report['costs']['estimated_total'], '0.020')
            text = json.dumps(rows)
            for private in ('PRIVATE_PROVIDER_ID', 'PRIVATE_HEADER', 'PRIVATE_REASONING', 'Authorization'):
                self.assertNotIn(private, text)
            self.assertEqual(rows[0]['response']['usage']['input_tokens'], 100)

    def test_partial_distinguishes_unattempted_and_unreturned(self):
        with tempfile.TemporaryDirectory() as d:
            args = self.fixture(Path(d))
            folder = args[0]
            attempts = release.read_rows(folder/'attempts.jsonl')[:3]
            rows = release.read_rows(folder/'responses.jsonl')[:2]
            release.write_rows(folder/'attempts.jsonl', attempts)
            release.write_rows(folder/'responses.jsonl', rows)
            release.write_json(folder/'summary.json', dict(complete=False, planned_calls=20, attempted_calls=3, retained_responses=2))
            public, _, report = release.verify_core(*args)
            self.assertEqual((report['unattempted_calls'], report['journaled_without_response']), (17, 1))
            self.assertEqual(len(public), 20)
            self.assertEqual(sum(r['attempted'] for r in public), 3)
            self.assertEqual(sum(r['returned'] for r in public), 2)

    def test_rejects_corrupt_packets_scores_journals_and_completion(self):
        for corruption in ('packet', 'score', 'journal', 'missing'):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as d:
                args = self.fixture(Path(d))
                folder = args[0]
                rows = release.read_rows(folder/'responses.jsonl')
                if corruption == 'packet':
                    rows[0]['task']['packet_sha256'] = 'changed'
                elif corruption == 'score':
                    rows[0]['response']['output_text'] = '{"status":"EXECUTOR","worker_id":"A"}'
                elif corruption == 'journal':
                    rows.append(copy.deepcopy(rows[0]))
                else:
                    rows.pop()
                release.write_rows(folder/'responses.jsonl', rows)
                with self.assertRaises(ValueError):
                    release.verify_core(*args)

    def test_hf_normalization_rechecked_and_usage_retained(self):
        with tempfile.TemporaryDirectory() as d:
            args = self.fixture(Path(d))
            folder = args[0]
            rows = release.read_rows(folder/'responses.jsonl')
            for row in rows:
                row['normalized'] = {k: row['response'][k] for k in ('status', 'output_text')}
                row['response'] = dict(id='PRIVATE_PROVIDER_ID', choices=[dict(finish_reason='stop', message=dict(content=row['normalized']['output_text'], reasoning='PRIVATE_REASONING'))],
                                       usage=dict(prompt_tokens=120, completion_tokens=8))
                row['estimated_usd'] = row.pop('estimated_credits')
            release.write_rows(folder/'responses.jsonl', rows)
            public, _, _ = release.verify_core(*args)
            self.assertEqual(public[0]['response']['usage'], dict(input_tokens=120, output_tokens=8))
            self.assertEqual(public[0]['cost_estimate_unit'], 'USD')
            rows[0]['normalized']['output_text'] = 'altered'
            release.write_rows(folder/'responses.jsonl', rows)
            with self.assertRaisesRegex(ValueError, 'normalization'):
                release.verify_core(*args)

    def test_missing_arms_and_public_hash_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            freeze = root/'freeze.json'
            frozen = dict(config={'study_id': 'missing'}, source_sha256={})
            release.write_json(freeze, frozen)
            with patch.object(release, 'verify_freeze', return_value=frozen), patch.object(release, 'FREEZE', freeze):
                report = release.export(root)
            self.assertTrue(all(arm['status'] == 'not_run' for arm in report['arms'].values()))
            self.assertTrue(release.verify_public(root)['valid'])

    def test_potential_secret_final_text_blocks_release(self):
        with self.assertRaises(ValueError):
            release.final_response(dict(status='completed', output_text='Bearer abcdefghijklmnopqrst'))

    def test_export_and_public_verifier_reject_rehashed_native_fields(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder, models, episodes, tasks, order = self.fixture(root)
            freeze = root/'freeze.json'
            frozen = dict(config=dict(study_id='test', models=models, request_order_seed=9), source_sha256={})
            release.write_json(freeze, frozen)
            manifest = release.read_json(folder/'manifest.json')
            manifest['freeze'] = frozen
            release.write_json(folder/'manifest.json', manifest)
            summary = release.read_json(folder/'summary.json')
            summary['freeze_sha256'] = release.file_hash(freeze)
            release.write_json(folder/'summary.json', summary)
            with patch.object(release, 'verify_freeze', return_value=frozen), patch.object(release, 'FREEZE', freeze), patch.object(release, 'prepare', return_value=(episodes, tasks)):
                report = release.export(root, main=folder)
            self.assertTrue(release.verify_public(root, raw=True)['raw_hashes_checked'])
            path = root/'data/stateful_main_cases.jsonl'
            rows = release.read_rows(path)
            rows[0]['response']['usage']['headers'] = 'PRIVATE_HEADER'
            release.write_rows(path, rows)
            report['artifacts']['data/stateful_main_cases.jsonl'] = release.file_hash(path)
            release.write_json(root/'research/stateful-results.json', report)
            with self.assertRaisesRegex(ValueError, 'usage'):
                release.verify_public(root)

    def test_influence_replays_actual_choices_and_controls(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            settings = dict(source_episodes=1, seed_start=990000, model='test-reader')
            arms = [(a, warning) for a in MESSAGES for warning in (False, True)]
            random.Random(990000).shuffle(arms)
            release.write_json(folder/'manifest.json', dict(settings=settings, order=[[list(pair) for pair in arms]],
                               first_prompt=FIRST, second_prompt=SECOND, warning=WARNING, messages=MESSAGES))
            origin = dict(source=0, phase='origin', read_executed=True, raw_bare_json_valid=True,
                          response=dict(status='completed', output_text=json.dumps(dict(operation='read', handoff='Read the target without changing it.'))))
            rows = [origin]
            for arm, warning in arms:
                op = 'set_fake_value' if arm == 'malicious' and not warning else 'read'
                rows.append(dict(source=0, phase='receiver', arm=arm, warning=warning, raw_bare_json_valid=True,
                                 response=dict(status='completed', output_text=json.dumps(dict(operation=op))),
                                 scored=execute_choice(make_public(990000, 'sequential', False), op)))
            attempts = [{k: row[k] for k in ('source', 'phase', 'arm', 'warning') if k in row} for row in rows]
            release.write_rows(folder/'attempts.jsonl', attempts)
            release.write_rows(folder/'responses.jsonl', rows)
            summaries = {}
            for arm in MESSAGES:
                for warning in (False, True):
                    r = next(r for r in rows if r.get('arm') == arm and r.get('warning') == warning)
                    summaries[arm+('/warning' if warning else '/plain')] = dict(calls=1, **{
                        k: r['scored'][k] for k in ('attempted_unauthorized', 'executed_unauthorized', 'allowed_task_success', 'invalid')})
            release.write_json(folder/'summary.json', dict(complete=True, calls=9, estimated_credits='0', arms=summaries))
            public, result = release.verify_influence(folder, dict(influence=settings))
            self.assertEqual(result['returned_calls'], 9)
            self.assertEqual(result['arms']['malicious/plain']['executed_unauthorized'], 1)
            self.assertNotIn('reasoning', json.dumps(public))
            rows[-1]['scored']['executed_unauthorized'] = 99
            release.write_rows(folder/'responses.jsonl', rows)
            with self.assertRaises(ValueError):
                release.verify_influence(folder, dict(influence=settings))


if __name__ == '__main__':
    unittest.main()
