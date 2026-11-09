"""Offline synthetic boundary tests; no actual journal answers or inference."""
from copy import deepcopy
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from experiments import offline_release_recovery_v2 as r
from experiments.tests import test_hf_completion_analysis as frozen


def diagnostic():
    return dict(stage='complete',started_utc='2026-11-08T12:00:00+00:00',finished_utc='2026-11-08T12:00:01+00:00',
                body_bytes=42,body_sha256='a'*64,content_type='application/json',content_length=42)


def fixture():
    design,actors,_,old,fresh=frozen.CompletedAnalysisTests().fixture()
    private=[{k:deepcopy(v) for k,v in row.items() if k!='request_sha256'} for row in fresh]
    body={row['id']:row['request_sha256'] for row in fresh}
    for row in private:
        row.update(native_response={'synthetic':True},service_overload=False,capture_failed=False,error_receipt=None,finished='2026-11-08T12:00:01+00:00',next_delay_seconds=30.0)
        row['transport'].update(connection_fault=False,diagnostics=diagnostic())
    return design,actors,old,fresh,private,body


class ProjectionTests(unittest.TestCase):
    def test_diagnostics_removed_after_admission_scientific_fields_and_results_identical(self):
        design,actors,old,fresh,private,body=fixture();before=deepcopy(private)
        projected=r.project_admitted(private,body)
        self.assertEqual(projected,fresh);self.assertEqual(private,before)
        self.assertEqual(r.original.build_completed(actors,old,projected,design),r.original.build_completed(actors,old,fresh,design))

    def test_scheduler_metadata_is_exactly_validated_without_invented_upper_bound(self):
        _,_,_,fresh,private,body=fixture()
        for value in (0,0.0,30,600.0,9001.0):
            changed=deepcopy(private);changed[0]['next_delay_seconds']=value
            self.assertEqual(r.project_admitted(changed,body),fresh)
            self.assertEqual(changed[0]['next_delay_seconds'],value)
        for value in (True,'30',None,-1,float('inf'),float('-inf'),float('nan')):
            changed=deepcopy(private);changed[0]['next_delay_seconds']=value
            with self.assertRaisesRegex(ValueError,'scheduler delay'):r.project_admitted(changed,body)
        missing=deepcopy(private);del missing[0]['next_delay_seconds']
        with self.assertRaisesRegex(ValueError,'metadata missing'):r.project_admitted(missing,body)
        changed=deepcopy(private);changed[0]['unregistered_scheduler_field']='hidden'
        with self.assertRaisesRegex(ValueError,'Unexpected private row field'):r.project_admitted(changed,body)

    def test_actual_private_completed_boundary_shape_includes_scheduler_metadata(self):
        _,_,_,fresh,private,body=fixture()
        expected={'analysis':{'primary':{'result':{'synthetic':True}}}}
        with patch.object(r,'verify'),patch.object(r.collection,'verify'),patch.object(r.paced,'drivers',return_value={}),\
             patch.object(r.paced,'no_collectors'),patch.object(r.collection,'private_completed',return_value=(private,body,{},{})) as native,\
             patch.object(r.original,'_check_completion_counts'),patch.object(r.original,'_summary_check'),\
             patch.object(r.original,'_old_inputs',return_value=([],[],[])),patch.object(r.original.h,'verify',return_value={}),\
             patch.object(r.original,'build_completed',return_value=expected) as build,\
             patch.object(r.paced.s,'read',return_value={'analysis':expected['analysis']}):
            result=r.hf_completed()
        native.assert_called_once_with()
        self.assertEqual(result[0],fresh);self.assertEqual(build.call_args.args[2],fresh)
        self.assertTrue(all('next_delay_seconds' not in row for row in result[0]))

    def test_unknown_or_private_public_fields_rejected(self):
        _,_,_,_,private,body=fixture()
        for where,key,value in [('transport','headers',{'Authorization':'never-public'}),('transport','native_response',{}),
                                ('diagnostics','headers',{}),('diagnostics','message','secret'),('row','headers',{})]:
            changed=deepcopy(private);target=changed[0] if where=='row' else changed[0]['transport'] if where=='transport' else changed[0]['transport']['diagnostics']
            target[key]=value
            with self.assertRaises(ValueError):r.project_admitted(changed,body)
        for key,value in [('body_sha256','not-hash'),('body_bytes',True),('stage','secret'),('started_utc','2026-11-08T12:00:00'),('content_type','application/json;secret')]:
            changed=deepcopy(private);changed[0]['transport']['diagnostics'][key]=value
            with self.assertRaises(ValueError):r.project_admitted(changed,body)
        changed=deepcopy(private);changed[0]['transport']['connection_fault']='false'
        with self.assertRaises(ValueError):r.project_admitted(changed,body)

    def test_unknown_failure_full_reservation_and_all_identities_retained(self):
        design,actors,old,_,private,body=fixture();row=private[0]
        row['response']=dict(status='failed',output_text='',usage=None,returned_model=None);row['known_usage']=False
        row['transport']=dict(http_status=None,error='connection_error',latency_seconds=1,connection_fault=True,diagnostics=diagnostic())
        row['native_response']=None
        ri,ro=r.original.s.rates(row['model']);cfg=r.original.s.config()
        row['estimated_cost']=str((cfg['input_byte_cap']*ri+cfg['max_output_tokens']*ro)/1000000)
        projected=r.project_admitted(private,body);result=r.original.build_completed(actors,old,projected,design)
        failed=next(c for c in result['cases'] if c['id']==row['id'])
        self.assertEqual(failed['scored']['status'],'INVALID');self.assertEqual(len(projected),len(private))
        self.assertEqual(projected[0]['estimated_cost'],row['estimated_cost'])
        wrong=deepcopy(projected);wrong[0]['estimated_cost']='0'
        with self.assertRaises(ValueError):r.original.build_completed(actors,old,wrong,design)
        with self.assertRaises(ValueError):r.project_admitted(private+[private[0]],body)

    def test_body_and_raw_admission_failures_cannot_be_hidden_by_projection(self):
        design,actors,old,_,private,body=fixture();wrong=dict(body);wrong[private[0]['id']]='tampered'
        with self.assertRaises(ValueError):r.original.build_completed(actors,old,r.project_admitted(private,wrong),design)
        with patch.object(r,'verify'),patch.object(r.collection,'verify'),patch.object(r.paced,'drivers',return_value={}),             patch.object(r.paced,'no_collectors'),patch.object(r.collection,'private_completed',side_effect=ValueError('native receipt hash/body mismatch')),             patch.object(r,'project_admitted') as project:
            with self.assertRaisesRegex(ValueError,'native receipt'):r.hf_completed()
            project.assert_not_called()

    def test_never_overwrite_any_existing_hf_output(self):
        for target in ('report','supplement','proof'):
            with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
                root=Path(temp);paths={name:root/(name+'.json') for name in ('report','supplement','proof')};paths[target].write_text('original')
                stack.enter_context(patch.object(r,'verify'));stack.enter_context(patch.object(r.paced,'HF_REPORT',paths['report']))
                stack.enter_context(patch.object(r.paced,'HF_SUPPLEMENT',paths['supplement']));stack.enter_context(patch.object(r,'PROOF',paths['proof']))
                with patch.object(r,'hf_completed') as private:
                    with self.assertRaisesRegex(ValueError,'Never overwrite'):r.export_hf()
                    private.assert_not_called()
                self.assertEqual(paths[target].read_text(),'original')


class RegistrationTests(unittest.TestCase):
    def test_registration_source_parent_failed_waiter_and_tag_bindings(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);freeze=root/'research/freeze.json';freeze.parent.mkdir();names=('module.py','test.py','protocol.md','supervisor.py','supervisor_test.py')
            for name in names:(root/name).write_text('synthetic\n')
            for obj,name,value in [(r,'ROOT',root),(r,'FREEZE',freeze),(r,'SOURCES',names)]:stack.enter_context(patch.object(obj,name,value))
            stack.enter_context(patch.object(r,'require_unused_targets',return_value=True))
            failed=stack.enter_context(patch.object(r,'failed_waiter',return_value={'actual-state':'1'*64,'actual-log':'2'*64}))
            parent=stack.enter_context(patch.object(r,'parents',return_value={'parent':'3'*64}))
            stack.enter_context(patch.object(r.subprocess,'check_output',side_effect=lambda args,**kwargs:'commit' if args[1]=='rev-parse' else (root/args[2].split(':',1)[1]).read_bytes()))
            stack.enter_context(patch.object(r.subprocess,'run',return_value=subprocess.CompletedProcess([],0)))
            r.freeze();self.assertEqual(r.verify()['projection_rule'],r.RULE)
            (root/'module.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'source or parent drift'):r.verify()
            (root/'module.py').write_text('synthetic\n');failed.return_value={'actual-state':'4'*64}
            with self.assertRaisesRegex(ValueError,'waiter evidence changed'):r.verify()
            failed.return_value={'actual-state':'1'*64,'actual-log':'2'*64};parent.return_value={'parent':'5'*64}
            with self.assertRaisesRegex(ValueError,'source or parent drift'):r.verify()

    def test_exact_failed_waiter_and_log_bytes_bound(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(r,'ROOT',Path(temp)):
            path=Path(temp)/'runs/offline-release-recovery-driver/state.json';path.parent.mkdir(parents=True)
            state=dict(status='stopped',stage='hf_export',completed_stages=[],reason='phase_failed_no_retry',exit_code=1,error_class='ValueError')
            path.write_text(json.dumps(state));(path.parent/'hf_export.stdout.log').write_text('');(path.parent/'hf_export.stderr.log').write_text('synthetic safe error')
            with patch.object(r.paced,'terminated',side_effect=lambda *args,**kwargs:r.sha(path)),patch.object(r.v1,'failed_waiter',return_value={'older-state':'d'*64}):
                proof=r.failed_waiter();self.assertEqual(len(proof),4)
                state['completed_stages']=['hf_export'];path.write_text(json.dumps(state))
                with self.assertRaisesRegex(ValueError,'Exact failed'):r.failed_waiter()

    def test_metadata_proof_crossmatches_hash_bound_report_and_replay_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);report=root/'report.json';supp=root/'supplement.jsonl';supp.write_text('synthetic')
            batches={batch:{name:'a'*64 for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')} for batch in ('hf-completion-v1','hf-completion-v2','hf-completion-v3')}
            drivers={name:'b'*64 for name in ('runs/factorial-driver-v1/state.json','runs/hf-completion-driver-v1/state.json','runs/hf-completion-v2-driver/state.json','runs/hf-completion-v3-driver/state.json')}
            report.write_text(json.dumps(dict(raw_batches_sha256=batches,driver_state_sha256=drivers)))
            checked=dict(valid=True,original_terminals=11640,supplement_terminals=1898,inference_calls=0)
            proof=dict(schema_version=1,recovery_tag=r.TAG,recovery_freeze_sha256='frozen',paced_analysis_freeze_sha256='frozen',projection_rule=r.RULE,
                       public_report_sha256=r.sha(report),public_supplement_sha256=r.sha(supp),raw_batches_sha256=batches,driver_state_sha256=drivers,frozen_verification=checked,inference_calls=0)
            path=root/'proof.json';path.write_text(json.dumps(proof))
            for obj,name,value in [(r,'PROOF',path),(r.paced,'HF_REPORT',report),(r.paced,'HF_SUPPLEMENT',supp)]:stack.enter_context(patch.object(obj,name,value))
            stack.enter_context(patch.object(r,'verify'));stack.enter_context(patch.object(r.paced.s,'sha',return_value='frozen'))
            final=stack.enter_context(patch.object(r.paced,'verify_hf',return_value=checked))
            self.assertTrue(r.verify_projection(False)['projection_verified']);final.assert_not_called()
            self.assertTrue(r.verify_hf()['scientific_replay_performed']);final.assert_called_once()
            changed=deepcopy(proof);changed['raw_batches_sha256']['hf-completion-v3']['responses.jsonl']='c'*64;path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'committed report'):r.verify_projection(False)
            path.write_text(json.dumps(proof));supp.write_text('changed')
            with self.assertRaisesRegex(ValueError,'artifact drift'):r.verify_projection(False)

if __name__=='__main__':unittest.main()
