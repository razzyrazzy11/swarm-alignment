"""Only synthetic/public fixtures; never opens completion journals or credentials."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from experiments import hf_completion_analysis as a
from experiments import factorial_analysis as f, factorial_reporting as r, factorial_study as s
from experiments.tests import test_factorial_reporting as fixtures


class CompletedAnalysisTests(unittest.TestCase):
    def fixture(self):
        design,actors,audits=fixtures.ReportingTests().fixture()
        kept=[x for x in audits if x['model']!=s.config()['hf_model'] or x['metadata']['procedure']=='direct']
        _,old,_=r.build_cases(actors,kept,design)
        _,_,jobs,_,_=r.build_plan(actors,design)
        body={j['id']:s.digest(s.body_for(j)[1]) for j in jobs}
        old_ids={x['id'] for x in old}
        fresh=[dict(x,request_sha256=body[x['id']]) for x in audits if x['id'] not in old_ids]
        return design,actors,audits,old,fresh

    def test_exact_frozen_three_model_analysis_and_bootstrap(self):
        design,actors,audits,old,fresh=self.fixture()
        ts,cases=f.build_cases(actors,audits,design)
        expected=f.analyze(actors,ts,cases)
        result=a.build_completed(actors,old,fresh,design)
        self.assertEqual(result['cases'],cases)
        self.assertEqual(result['trajectories'],ts)
        self.assertEqual(result['analysis'],expected)
        self.assertEqual(set(result['analysis']['models']),set(s.config()['monitors']))
        self.assertEqual(result['analysis']['primary']['result']['resamples'],10000)

    def test_duplicates_missing_conditions_provider_and_body(self):
        design,actors,_,old,fresh=self.fixture()
        for changed in (fresh[:-1],fresh+[deepcopy(fresh[0])]):
            with self.assertRaises(ValueError):a.build_completed(actors,old,changed,design)
        for field,value in (('provider','adaption'),('request_sha256','wrong'),('native_response',{})):
            changed=deepcopy(fresh);changed[0][field]=value
            with self.assertRaises(ValueError):a.build_completed(actors,old,changed,design)
        changed=deepcopy(old);changed[0]['condition_id']='later_extension'
        with self.assertRaises(ValueError):a.build_completed(actors,changed,fresh,design)
        changed=deepcopy(old);changed[0]['scored']['grounded_correct']=not changed[0]['scored']['grounded_correct']
        with self.assertRaises(ValueError):a.build_completed(actors,changed,fresh,design)

    def test_known_zero_and_unknown_reservation_are_distinct(self):
        design,actors,_,old,fresh=self.fixture()
        changed=deepcopy(fresh)
        zero=changed[0];zero['response']['usage']=dict(input_tokens=0,output_tokens=0);zero['estimated_cost']='0'
        unknown=changed[1];unknown['response']=dict(status='failed',output_text='',usage=None,returned_model=None)
        unknown['transport']=dict(http_status=429,error='HTTPError');unknown['known_usage']=False
        ri,ro=s.rates(unknown['model']);cfg=s.config()
        unknown['estimated_cost']=str((cfg['input_byte_cap']*ri+cfg['max_output_tokens']*ro)/1000000)
        result=a.build_completed(actors,old,changed,design)
        by={x['id']:x for x in result['cases']}
        self.assertTrue(by[zero['id']]['known_usage'])
        self.assertFalse(by[unknown['id']]['known_usage'])
        self.assertEqual(by[unknown['id']]['scored']['status'],'INVALID')
        self.assertEqual(len(result['cases']),len(old)+len(fresh))
        changed[1]['estimated_cost']='0'
        with self.assertRaises(ValueError):a.build_completed(actors,old,changed,design)

    def test_export_refuses_active_driver_before_private_answers(self):
        with patch.object(a,'verify_registration',return_value={}),patch.object(a.h,'verify',return_value={}),patch.object(a,'driver_stopped',side_effect=ValueError('active')),patch.object(a.h,'original_prefix') as raw:
            with self.assertRaises(ValueError):a.export(True)
            raw.assert_not_called()

    def test_stale_source_prefix_stops_before_supplement_reads(self):
        with patch.object(a,'verify_registration',return_value={}),patch.object(a.h,'verify',return_value={}),patch.object(a,'driver_stopped'),patch.object(a.h,'original_prefix',side_effect=ValueError('stale prefix')),patch.object(a.h,'supplement_ledger') as supplement:
            with self.assertRaises(ValueError):a.export(True)
            supplement.assert_not_called()

    def test_complete_identity_guard_includes_failed_terminals(self):
        with self.assertRaises(ValueError):a._check_completion_counts([],dict(pending=[]))
        with patch.object(a,'verify_registration') as registration:
            with self.assertRaises(ValueError):a.export(False)
            registration.assert_not_called()


if __name__=='__main__':unittest.main()
