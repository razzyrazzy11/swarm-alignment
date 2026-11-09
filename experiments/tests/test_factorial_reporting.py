"""Synthetic reporting checks: no private contexts, journals or inference."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments import factorial_reporting as r, factorial_analysis as f, factorial_study as s
from experiments.tests import test_factorial_analysis as fixtures


def fast_effect(values,strata):
    return dict(n=len(values),estimate=sum(values.values())/len(values),ordered=list(values),strata_order=list(strata))


class FakeExtension:
    def config(self):
        return dict(conditions=[dict(id=ident,model='deepseek-fixture' if ident!='gemma_bridge' else 'gemma-fixture',
            think='low' if ident=='ds_low' else False,views='all' if ident=='ds_off' else 'sufficient_calibration',
            input_rate='.30',output_rate='1.20') for ident in ('ds_off','ds_low','gemma_bridge')])

    def jobs_from_templates(self,templates):
        jobs=[]
        for condition in self.config()['conditions']:
            for template in templates:
                meta=template['metadata']
                if condition['views']!='all' and meta['view']!='sufficient' and not meta['view'].startswith('calibration_'):continue
                meta=dict(meta,condition_id=condition['id'],phase='readers')
                jobs.append(dict(id=f"extension:{condition['id']}:{template['id']}",model=condition['model'],
                    condition_id=condition['id'],metadata=meta,messages=s.body_for(template)[1]['messages']))
        return jobs

    def body_for(self,job):
        condition=next(c for c in self.config()['conditions'] if c['id']==job['condition_id'])
        return dict(model=job['model'],messages=job['messages'],stream=False,think=condition['think'],options=dict(temperature=0,num_predict=4096))

    def admit_response(self,transport,response,known,anomaly):
        if known and not anomaly and transport.get('http_status')==200 and response['status']=='completed':return dict(response)
        return dict(response,output_text='',status='incomplete' if response['status']=='incomplete' else 'failed')


class ReportingTests(unittest.TestCase):
    def fixture(self):
        design,actors,audits=fixtures.FactorialAnalysisTests().fixture()
        registry=r.descriptors()
        for row in actors+audits:
            descriptor=next(d for d in registry.values() if d['model']==row['model'])
            if descriptor['provider']=='hf':row['response']['returned_model']=r.live_config()['hf_allowed_returned_models'][0]
            row['estimated_cost']=str(r._cost(row,descriptor))
        return design,actors,audits

    def extension_rows(self,actors,design,extension):
        _,_,_,jobs,registry=r.build_plan(actors,design,extension)
        values=[]
        for job in jobs:
            row=dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider='ollama',transport={'http_status':200},
                response=dict(status='completed',output_text='{"status":"ABSTAIN","worker_id":null}',
                    usage=dict(input_tokens=10,output_tokens=10),returned_model=job['model']),known_usage=True,
                profile_anomaly=False,service_overload=False,capture_failed=False)
            row['estimated_cost']=str(r._cost(row,registry[job['condition_id']]))
            values.append(row)
        return values

    def test_original_primary_and_secondary_exact_frozen_bootstrap(self):
        design,actors,audits=self.fixture()
        ts,old_cases=f.build_cases(actors,audits,design)
        old=f.analyze(actors,ts,old_cases)
        kept=[row for row in audits if row['model']!=s.config()['hf_model'] or row['metadata']['procedure']=='direct']
        ts,cases,manifest=r.build_cases(actors,kept,design)
        new=r.analyze(actors,ts,cases,manifest,expected_sources=2)
        self.assertEqual(old['primary'],new['primary'])
        for model in s.config()['monitors'][:2]:
            for field,value in old['models'][model].items():self.assertEqual(value,new['models'][model][field],field)
        for key in ('actual_behavior','baselines','secondary_oracle_coverage'):self.assertEqual(old[key],new[key])
        hf=new['models'][s.config()['hf_model']]
        self.assertEqual(hf['availability']['unstarted'],40)
        self.assertNotIn('primary_same_packet_procedure_minus_direct',hf)
        self.assertEqual(hf['sufficient_identification_bounds']['unknown_cells'],2)

    def test_missing_has_manifest_identity_but_no_fabricated_invalid(self):
        design,actors,audits=self.fixture();missing=audits.pop()
        _,cases,manifest=r.build_cases(actors,audits,design)
        self.assertNotIn(missing['id'],{row['id'] for row in cases})
        entry=next(job for job in manifest['jobs'] if job['id']==missing['id'])
        self.assertEqual(entry['state'],'UNSTARTED');self.assertNotIn('response',entry)
        self.assertEqual(len(cases)+1,len(manifest['jobs']))
        self.assertEqual(sum(job['state']=='UNSTARTED' for job in manifest['jobs']),1)

    def test_duplicates_unplanned_packet_and_condition_swaps_rejected(self):
        design,actors,audits=self.fixture()
        for mutate in ('duplicate','unknown','packet','procedure'):
            bad=copy.deepcopy(audits)
            if mutate=='duplicate':bad.append(bad[0])
            elif mutate=='unknown':bad[0]['id']='not-planned'
            elif mutate=='packet':bad[0]['metadata']['packet_sha256']='tamper'
            else:bad[0]['metadata']['procedure']='procedure'
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):r.build_cases(actors,bad,design)

    def test_invalid_observed_zero_distinct_from_unstarted_none(self):
        design,actors,audits=self.fixture();hf=s.config()['hf_model']
        target=next(row for row in audits if row['model']==hf and row['metadata']['view']=='sufficient' and row['metadata']['procedure']=='direct')
        target['response'].update(status='failed',output_text='',usage=None,returned_model=None)
        target.update(known_usage=False,transport={'http_status':429,'error':'HTTPError'})
        target['estimated_cost']=str(r._cost(target,r.descriptors()['original_hf']))
        other=next(row for row in audits if row['model']==hf and row['metadata']['view']=='sufficient' and row['metadata']['procedure']=='procedure' and row['metadata']['source_seed']==target['metadata']['source_seed'])
        audits.remove(other)
        ts,cases,manifest=r.build_cases(actors,audits,design)
        pairs=r._procedure_pairs(cases,[t['source_seed'] for t in ts],'original_hf')
        pair=next(pair for pair in pairs if pair['source_seed']==target['metadata']['source_seed'])
        self.assertEqual(pair['direct'],0);self.assertIsNone(pair['procedure'])
        self.assertEqual(r._bounds(pairs)['unknown_cells'],1)

    def test_complete_primary_required_even_if_other_readers_complete(self):
        design,actors,audits=self.fixture();audits.pop(0)
        ts,cases,manifest=r.build_cases(actors,audits,design)
        with self.assertRaisesRegex(ValueError,'complete planned grids'):r.analyze(actors,ts,cases,manifest,effect_fn=fast_effect,expected_sources=2)

    def test_two_same_model_modes_are_separate_planned_conditions(self):
        design,actors,audits=self.fixture();extension=FakeExtension()
        extra=self.extension_rows(actors,design,extension)
        ts,cases,manifest=r.build_cases(actors,audits,design,extra,extension)
        result=r.analyze(actors,ts,cases,manifest,effect_fn=fast_effect,expected_sources=2)
        conditions=result['extensions']['conditions']
        self.assertEqual(conditions['ds_off']['availability']['planned'],80)
        self.assertEqual(conditions['ds_low']['availability']['planned'],44)
        self.assertEqual(conditions['ds_off']['model'],conditions['ds_low']['model'])
        self.assertNotEqual(conditions['ds_off']['think'],conditions['ds_low']['think'])
        self.assertEqual(result['extensions']['contrasts']['low_minus_off_direct_sufficient']['result']['n'],2)
        self.assertNotIn('primary_same_packet_procedure_minus_direct',conditions['gemma_bridge'])
        self.assertEqual(result['extensions']['contrasts']['gemma_bridge_minus_adaption31_direct_sufficient']['status'],'complete')

    def test_partial_extension_gets_bounds_without_complete_pair_point(self):
        design,actors,audits=self.fixture();extension=FakeExtension();extra=self.extension_rows(actors,design,extension)
        missing=next(row for row in extra if row['metadata']['condition_id']=='ds_low' and row['metadata']['view']=='sufficient' and row['metadata']['procedure']=='direct')
        extra.remove(missing);ts,cases,manifest=r.build_cases(actors,audits,design,extra,extension)
        result=r.analyze(actors,ts,cases,manifest,effect_fn=fast_effect,expected_sources=2)
        contrast=result['extensions']['contrasts']['low_minus_off_direct_sufficient']
        self.assertEqual(contrast['status'],'partial');self.assertNotIn('result',contrast)
        self.assertEqual(contrast['identification_bounds']['unknown_cells'],1)
        self.assertEqual(contrast['identification_bounds']['n'],2)

    def test_technical_anomaly_answer_never_scored_as_valid(self):
        design,actors,audits=self.fixture();extension=FakeExtension();extra=self.extension_rows(actors,design,extension)
        extra[0]['profile_anomaly']=True
        ts,cases,_=r.build_cases(actors,audits,design,extra,extension)
        self.assertEqual(next(row for row in cases if row['id']==extra[0]['id'])['scored']['status'],'INVALID')

    def test_public_native_headers_thinking_unknown_flags_and_cost_drift_rejected(self):
        design,actors,audits=self.fixture();descriptor=r.descriptors()['original_g26'];base=audits[0]
        for key in ('native_response','thinking','headers','unexpected'):
            bad=copy.deepcopy(base);bad[key]='never public'
            with self.subTest(key=key),self.assertRaises(ValueError):r.validate_row(bad,descriptor)
        bad=copy.deepcopy(base);bad['transport']['headers']={}
        with self.assertRaises(ValueError):r.validate_row(bad,descriptor)
        bad=copy.deepcopy(base);bad['estimated_cost']='0'
        with self.assertRaises(ValueError):r.validate_row(bad,descriptor)

    def test_counter_types_model_aliases_and_latency_nonfinite_rejected(self):
        _,_,audits=self.fixture();descriptor=r.descriptors()['original_g26']
        for mutate in ('bool_counter','negative_counter','model','nan_latency','bool_http'):
            row=copy.deepcopy(audits[0])
            if mutate=='bool_counter':row['response']['usage']['input_tokens']=True
            elif mutate=='negative_counter':row['response']['usage']['input_tokens']=-1
            elif mutate=='model':row['response']['returned_model']='wrong'
            elif mutate=='nan_latency':row['transport']['latency_seconds']=float('nan')
            else:row['transport']['http_status']=True
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):r.validate_row(row,descriptor)

    def test_export_requires_explicit_flag_before_registration_or_private_reads(self):
        with patch.object(r,'verify_registration',side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(ValueError,'Explicit'):r.export()

    def test_stopped_ledger_rejects_locks_duplicate_and_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/'attempts.jsonl').write_text('{"id":"a"}\n',encoding='utf-8')
            (folder/'responses.jsonl').write_text('{"id":"a"}\n',encoding='utf-8')
            self.assertEqual(r._stopped_ledger(folder)['returned'],1)
            for lock in ('collector.lock','continuation.lock','continuation-pacing.lock'):
                path=folder/lock;path.write_text('owner',encoding='utf-8')
                with self.subTest(lock=lock),self.assertRaises(ValueError):r._stopped_ledger(folder)
                path.unlink()
            (folder/'responses.jsonl').write_text('',encoding='utf-8')
            with self.assertRaises(ValueError):r._stopped_ledger(folder)
            (folder/'responses.jsonl').write_text('{"id":"a"}\n{"id":"a"}\n',encoding='utf-8')
            with self.assertRaises(ValueError):r._stopped_ledger(folder)

    def test_driver_must_be_stopped_and_pid_absent_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            path=Path(directory)/'runs/ollama-extension-driver/state.json';path.parent.mkdir(parents=True)
            for status,returncode,allowed in (('running',3,False),('complete',0,False),('stopped',4,False),('stopped',3,True)):
                path.write_text(json.dumps(dict(pid=123,status=status)),encoding='utf-8')
                with self.subTest(status=status,returncode=returncode),patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=returncode)):
                    if allowed:r._driver_stopped()
                    else:
                        with self.assertRaises(ValueError):r._driver_stopped()

    def test_public_registration_verification_never_reads_outcomes_or_private_contexts(self):
        record=dict(schema_version=1,registration_tag=r.TAG,base_commit='base',original_freeze_sha256='hash',
            original_checkpoint_sha256='hash',extension_freeze_sha256=None,source_sha256={'safe.py':'hash'})
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'research/freeze.json';freeze.parent.mkdir();freeze.write_text('safe',encoding='utf-8')
            (root/'safe.py').write_text('safe',encoding='utf-8')
            with patch.object(r,'ROOT',root),patch.object(r,'FREEZE',freeze),patch.object(r,'SOURCES',('safe.py',)),\
                 patch.object(r,'read',return_value=record),patch.object(r.s,'sha',return_value='hash'),\
                 patch.object(r.continuation,'verify_original_sources'),patch.object(r.subprocess,'check_output',return_value=b'safe'),\
                 patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=0)),\
                 patch.object(r.s,'contexts',side_effect=AssertionError('private contexts')),\
                 patch.object(r,'rows',side_effect=AssertionError('outcome journals')):
                self.assertEqual(r.verify_registration(),(record,None))

    def test_public_registration_rejects_source_drift(self):
        record=dict(schema_version=1,registration_tag=r.TAG,base_commit='base',original_freeze_sha256='hash',
            original_checkpoint_sha256='hash',extension_freeze_sha256=None,source_sha256={'safe.py':'different'})
        with patch.object(r,'SOURCES',('safe.py',)),patch.object(r,'read',return_value=record),\
             patch.object(r.s,'sha',return_value='hash'),patch.object(r.continuation,'verify_original_sources'):
            with self.assertRaisesRegex(ValueError,'sources changed'):r.verify_registration()


if __name__=='__main__':unittest.main()
