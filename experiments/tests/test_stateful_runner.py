import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.stateful_study import run,config
from experiments.stateful_analysis import bootstrap
from experiments.stateful_influence import execute_choice,action
from experiments.stateful import make_public

class StatefulRunnerTests(unittest.TestCase):
    def test_unknown_charge_halts_and_drains_started_calls(self):
        c=config();task=dict(task_id='test',packet={'test':'fake'},compatible_labels=['A'],episode_id='test')
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'runs/stateful-qualification'
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
                with self.assertRaisesRegex(ValueError,'qualification'):run('main',Path(folder)/'runs/stateful-main')

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

if __name__=='__main__':unittest.main()
