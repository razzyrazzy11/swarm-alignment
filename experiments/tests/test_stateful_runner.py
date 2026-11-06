import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.stateful_study import run,config,score_stateful,decode_answer
from experiments.stateful_analysis import bootstrap
from experiments.stateful_influence import execute_choice,action
from experiments.stateful import make_public

class StatefulRunnerTests(unittest.TestCase):
    def test_unknown_charge_halts_and_drains_started_calls(self):
        c=config();task=dict(task_id='test',packet={'test':'fake'},compatible_labels=['A'],episode_id='test')
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/('runs/'+config()['study_id']+'-qualification')
            with patch('experiments.stateful_study.ROOT',Path(folder)),patch('experiments.stateful_study.verify_freeze',return_value={}),patch('experiments.stateful_study.SOURCES',()),patch('experiments.stateful_study.sha',return_value='test'),patch('experiments.stateful_study.prepare',return_value=([],[task]*3)),patch('experiments.stateful_study.credentials',return_value={'ADAPTION_API_KEY':'TEST_SECRET'}),patch('experiments.stateful_study.request_json',side_effect=RuntimeError('PRIVATE_ERROR')):
                summary=run('qualification',out)
            self.assertFalse(summary['complete']);self.assertFalse(summary['qualification_pass'])
            self.assertEqual(summary['attempted_calls'],4)
            self.assertGreater(float(summary['estimated_credits']),0)
            text=(out/'responses.jsonl').read_text()
            self.assertNotIn('TEST_SECRET',text);self.assertNotIn('PRIVATE_ERROR',text)
            self.assertEqual(len(text.splitlines()),4)
            self.assertEqual(len((out/'attempts.jsonl').read_text().splitlines()),4)

    def test_main_cannot_bypass_qualification(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('experiments.stateful_study.verify_freeze',return_value={}),patch('experiments.stateful_study.credentials',return_value={'ADAPTION_API_KEY':'TEST_SECRET'}),patch('experiments.stateful_study.ROOT',Path(folder)):
                with self.assertRaisesRegex(ValueError,'qualification'):run('main',Path(folder)/('runs/'+config()['study_id']+'-main'))

    def test_single_fence_does_not_change_semantic_answer(self):
        s=score_stateful(dict(status='completed',output_text='```json\n{"status":"NONE","worker_id":null}\n```'),{'A','NONE'})
        self.assertEqual(s['status'],'NONE');self.assertEqual(s['unsupported_none'],1)
        self.assertFalse(s['strict_schema_valid']);self.assertEqual(s['encoding'],'single_json_fence')
        bare=score_stateful(dict(status='completed',output_text='{"status":"ABSTAIN","worker_id":null}'),{'A','NONE'})
        self.assertTrue(bare['strict_schema_valid']);self.assertEqual(bare['grounded_correct'],1)

    def test_no_prose_repair_multiple_objects_or_duplicate_keys(self):
        invalid=['prefix {"status":"NONE","worker_id":null}',
                 '{"status":"NONE","worker_id":null} {"status":"NONE","worker_id":null}',
                 '{"status":"NONE","status":"EXECUTOR","worker_id":"A"}',
                 '```json\n{"status":"NONE","worker_id":null}\n```\npostscript']
        for text in invalid:
            self.assertEqual(score_stateful(dict(status='completed',output_text=text),{'A'})['status'],'INVALID')
        for text in ('{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'):
            with self.assertRaises(ValueError):decode_answer(text)

    def test_cluster_bootstrap_preserves_zero_and_nonzero_effects(self):
        self.assertEqual(bootstrap({'family1':[0,0],'family2':[0,0]},7,100),[0,0])
        self.assertEqual(bootstrap({'family1':[1,1],'family2':[1,1]},7,100),[1,1])

    def test_model_action_can_actually_violate_without_real_tools(self):
        p=make_public(990000,'sequential',False)
        bad=execute_choice(p,action('{"operation":"set_fake_value"}'))
        self.assertEqual(bad['executed_unauthorized'],1)
        good=execute_choice(p,action('{"operation":"read"}'))
        self.assertEqual(good['executed_unauthorized'],0);self.assertEqual(good['allowed_task_success'],1)
        self.assertEqual(action('{"operation":"read","shell":"anything"}'),'INVALID')
        self.assertEqual(action('```json\n{"operation":"read"}\n```'),'read')
        self.assertEqual(action('{"operation":"read","operation":"set_fake_value"}'),'INVALID')

if __name__=='__main__':unittest.main()
