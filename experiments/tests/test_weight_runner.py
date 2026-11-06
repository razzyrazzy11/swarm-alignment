"""Offline orchestration/statistics guards, with synthetic fixtures only."""
import json,unittest
from unittest.mock import patch
from experiments import weight_study as s
from experiments.weight_audit import problem,assess,canonical

class WeightRunnerTests(unittest.TestCase):
    def test_wrong_returned_model_never_becomes_requested_writer_success(self):
        j=s.jobs()[0];lc=s.live_config();returned=lc['hf_allowed_returned_models'][0] if j['model']==lc['hf_model'] else j['model']
        row=dict(model=j['model'],known_usage=True,transport={'http_status':200},response=dict(status='completed',returned_model=returned,usage=dict(input_tokens=10,output_tokens=10)))
        self.assertTrue(s.profile_valid(row))
        row['response']['returned_model']='unregistered-model'
        self.assertFalse(s.profile_valid(row))

    def test_fixed_main_and_qualification_grid(self):
        main=s.jobs();qual=s.jobs(True)
        self.assertEqual(len(main),144);self.assertEqual(len(qual),6)
        self.assertEqual(len({j['id'] for j in main}),144)
        self.assertTrue({j['id'] for j in main}.isdisjoint(j['id'] for j in qual))
        self.assertTrue(all(j['history']==[] for j in main))
        self.assertTrue(all(j['payload']['given_networks'] is None for j in main if j['metadata']['task']=='synthesize'))

    def test_all_planned_invalid_artifacts_remain_in_denominator(self):
        c=s.config();c['bootstrap_resamples']=50;cases=[]
        for j in s.jobs():
            p=problem(j['metadata']['seed'],j['metadata']['index'])
            cases.append(dict(model=j['model'],metadata=j['metadata'],scored=assess(p,j['metadata']['task'],'bad'),random_control=None,provider='hf' if 'novita' in j['model'] else 'adaption',estimated_cost='0'))
        with patch.object(s,'config',return_value=c):r=s.summary(cases)
        for result in r['model_results'].values():
            for task in result.values():
                self.assertEqual(task['calls'],24);self.assertEqual(task['exact']['n'],24)
                self.assertEqual(task['exact']['rate'],0);self.assertEqual(task['random_draws'],0)
        self.assertEqual(r['checkpoint_change_alarm']['benign_false_harm_alarms'],24)
        self.assertGreater(r['same_handoff_unsafe_changes'],0)

    def test_variant_bootstrap_does_not_use_truth_rows(self):
        c=s.config();c['bootstrap_resamples']=100
        with patch.object(s,'config',return_value=c):
            r=s.bootstrap([True,False,True,False,True,False],list(range(6)))
        self.assertEqual(r['n'],6);self.assertEqual(r['rate'],.5)
        self.assertLessEqual(r['ci95'][0],.5);self.assertGreaterEqual(r['ci95'][1],.5)

if __name__=='__main__':unittest.main()
