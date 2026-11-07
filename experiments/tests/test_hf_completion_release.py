"""Synthetic release guards only; never opens actual completion journals."""
from contextlib import ExitStack,nullcontext
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from experiments import hf_completion_release as r
from experiments import swarm_ledger_dispatch_v2 as pid_owner
from experiments.tests import test_hf_completion_analysis as frozen_tests


class DriverTests(unittest.TestCase):
    def setup_tree(self,root):
        ended=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
        for i,name in enumerate(r.DRIVERS):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            state=dict(status='complete' if i==2 else 'stopped',updated=ended,pid=100+i*10)
            if i:state['child_pid']=101+i*10
            path.write_text(json.dumps(state))
        for name in ('audits','hf1','hf2'):(root/'runs'/name).mkdir(exist_ok=True)
        return ended

    def locations(self,stack,root):
        stack.enter_context(patch.object(r,'ROOT',root))
        stack.enter_context(patch.object(r.s,'folder',side_effect=lambda _:root/'runs/audits'))
        stack.enter_context(patch.object(r.h,'folder',return_value=root/'runs/hf1'))
        stack.enter_context(patch.object(r.recovery,'folder',return_value=root/'runs/hf2'))

    def test_actual_parent_children_state_bytes_and_relevant_locks(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);ended=self.setup_tree(root);self.locations(stack,root)
            dead=stack.enter_context(patch.object(r,'process_dead',return_value=True))
            proof=r.driver_proof();self.assertEqual(set(proof),set(r.DRIVERS));self.assertEqual(dead.call_count,5)
            self.assertTrue(all(call.args[1]==ended for call in dead.call_args_list))
            path=root/r.DRIVERS[1];raw=path.read_bytes()
            def mutate(pid,*_):
                if pid==110:path.write_bytes(raw+b' ')
            with patch.object(r,'process_dead',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'state changed'):r.driver_proof()
            path.write_bytes(raw)
            lock=root/'runs/audits/collector.lock';lock.write_text('owned elsewhere')
            with self.assertRaisesRegex(ValueError,'Relevant HF collector'):r.driver_proof()
            lock.unlink()
            owned=root/'runs/audits/continuation.lock';owned.write_text('owned')
            recovery_lock=root/'runs/hf2/collector.lock';recovery_lock.write_text('owned')
            with self.assertRaises(ValueError):r.driver_proof()
            self.assertEqual(r.driver_proof(True),proof)

    def test_incomplete_or_active_child_rejected(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);self.setup_tree(root);self.locations(stack,root)
            with patch.object(r,'process_dead',side_effect=ValueError('active child')):
                with self.assertRaisesRegex(ValueError,'active child'):r.driver_proof()
            path=root/r.DRIVERS[2];state=json.loads(path.read_text());state['status']='running';path.write_text(json.dumps(state))
            with patch.object(r,'process_dead'):
                with self.assertRaisesRegex(ValueError,'not terminal-complete'):r.driver_proof()

    def test_frozen_pid_helper_accepts_only_proven_later_creation(self):
        ended='2026-11-07T10:00:00+00:00'
        with patch.object(pid_owner.os,'name','nt'):
            for created,allowed in [('2026-11-07T10:01:00+00:00',True),('2026-11-07T09:59:00+00:00',False)]:
                result=subprocess.CompletedProcess([],0,stdout=created.encode(),stderr=b'')
                with patch.object(pid_owner.subprocess,'run',return_value=result):
                    if allowed:self.assertTrue(r.process_dead(123,ended))
                    else:
                        with self.assertRaisesRegex(ValueError,'PID reuse unproven'):r.process_dead(123,ended)
            with patch.object(pid_owner.subprocess,'run',return_value=subprocess.CompletedProcess([],4)):
                with self.assertRaises(ValueError):r.process_dead(123,ended)

    def test_private_archive_hashes_detect_native_or_error_byte_change(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);self.setup_tree(root);self.locations(stack,root)
            for folder in (r.h.folder(),r.recovery.folder()):
                for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json'):(folder/name).write_text('{}')
                (folder/'private-errors').mkdir();(folder/'private-errors/error-000000.json').write_text('{"synthetic":true}')
            before=r.private_snapshot();self.assertEqual(len(before),10)
            (r.recovery.folder()/'responses.jsonl').write_text('{"native_response":"changed"}')
            self.assertNotEqual(r.private_snapshot(),before)
            second=r.private_snapshot();(r.recovery.folder()/'private-errors/error-000000.json').write_text('{}')
            self.assertNotEqual(r.private_snapshot(),second)


class RegistrationTests(unittest.TestCase):
    def test_registered_source_and_parent_tamper_fail_before_unblinding(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);freeze=root/'research/release.json';freeze.parent.mkdir()
            names=('source.py','test.py','protocol.md','pid.py')
            for name in names:(root/name).write_text('synthetic source\n')
            stack.enter_context(patch.object(r,'ROOT',root));stack.enter_context(patch.object(r,'FREEZE',freeze))
            stack.enter_context(patch.object(r,'SOURCES',names));anchors=stack.enter_context(patch.object(r,'parent_anchors',return_value={'parent':'a'*64}))
            stack.enter_context(patch.object(r.h,'blob',side_effect=lambda name,tag:(root/name).read_bytes()))
            stack.enter_context(patch.object(r.subprocess,'check_output',return_value='commit'))
            stack.enter_context(patch.object(r.subprocess,'run',return_value=subprocess.CompletedProcess([],0)))
            r.freeze();self.assertEqual(r.verify()['tag'],r.TAG)
            (root/'source.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'source changed'):r.verify()
            with patch.object(r,'private_completed') as private:
                with self.assertRaises(ValueError):r.export(True)
                private.assert_not_called()
            (root/'source.py').write_text('synthetic source\n');anchors.return_value={'parent':'b'*64}
            with self.assertRaisesRegex(ValueError,'registrations changed'):r.verify()

    def test_explicit_publication_opt_in_before_any_registration_or_answers(self):
        with patch.object(r,'verify') as verify,patch.object(r,'private_completed') as private:
            with self.assertRaisesRegex(ValueError,'publication flag'):r.export(False)
            verify.assert_not_called();private.assert_not_called()

    def test_frozen_math_and_body_native_validation_unchanged(self):
        fixture=frozen_tests.CompletedAnalysisTests();design,actors,audits,old,fresh=fixture.fixture()
        expected=r.a.build_completed(actors,old,fresh,design)
        self.assertEqual(expected['analysis']['primary']['result']['resamples'],10000)
        bad=deepcopy(fresh);bad[0]['request_sha256']='tampered'
        with self.assertRaises(ValueError):r.a.build_completed(actors,old,bad,design)
        bad=deepcopy(fresh);bad[0]['native_response']={'forbidden':'unredacted'}
        with self.assertRaises(ValueError):r.a.build_completed(actors,old,bad,design)


class SerializerTests(unittest.TestCase):
    def test_old_and_new_serializer_bytes_identical_companion_separate(self):
        model=r.s.config()['hf_model'];private=[];pending=[];body={}
        for i in range(1898):
            row=dict(id=str(i),model=model,metadata={},provider='hf',transport={'http_status':200},
                     response={'status':'completed','output_text':'synthetic','usage':{'input_tokens':0,'output_tokens':0}},
                     known_usage=True,estimated_cost='0')
            private.append(row);body[str(i)]='body';pending.append(dict(id=str(i),model=model,metadata={},provider='hf',request_sha256='body'))
        summary=dict(planned=1898,returned=1898,unstarted=0,complete=True,halted=False,stop_reason='',
                     new_transient_errors=0,historical_429_preserved=5,new_estimated_cost='0',historical_hf_cost='0.880229785',
                     freeze_sha256='frozen',cost_basis='synthetic',original_audit_returned=11640,original_hf_returned=3880)
        union=(private,body,summary,{'hf-completion-v1':{},'hf-completion-v2':{}})
        result=dict(cases=[{}]*11640,analysis={'primary':{'result':{'estimate':0}}})
        outputs=[]
        for modern in (False,True):
            with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
                root=Path(temp);(root/'research').mkdir();(root/'data').mkdir()
                report=root/'research/result.json';supplement='data/supplement.jsonl';companion=root/'research/proof.json'
                for obj,name,value in [(r,'ROOT',root),(r,'COMPANION',companion),(r.a,'ROOT',root),(r.a,'REPORT',report),(r.a,'SUPPLEMENT',supplement)]:
                    stack.enter_context(patch.object(obj,name,value))
                stack.enter_context(patch.object(r.a,'verify_registration',return_value={'anchors':{}}))
                stack.enter_context(patch.object(r.h,'verify',return_value={'pending':pending,'historical_429_ids':list(range(5))}))
                stack.enter_context(patch.object(r.recovery,'verify',return_value={}))
                stack.enter_context(patch.object(r.h,'exclusive',side_effect=lambda _:nullcontext()))
                stack.enter_context(patch.object(r.s,'sha',return_value='frozen'))
                stack.enter_context(patch.object(r.a,'_old_inputs',return_value=([],[],[])))
                stack.enter_context(patch.object(r.a,'build_completed',return_value=result))
                stack.enter_context(patch.object(r.a,'read',return_value={'analysis':result['analysis']}))
                stack.enter_context(patch.object(r.a,'_availability',return_value={'synthetic':True}))
                final=stack.enter_context(patch.object(r.a,'verify_public',return_value={'valid':True}))
                stack.enter_context(patch.object(r.a,'driver_stopped'));stack.enter_context(patch.object(r.a,'recovery_stopped'))
                stack.enter_context(patch.object(r,'verify',return_value={}))
                stack.enter_context(patch.object(r,'driver_proof',return_value={'driver':'hash'}))
                stack.enter_context(patch.object(r,'private_snapshot',return_value={'native':'hash'}))
                stack.enter_context(patch.object(r,'private_completed',return_value=union))
                stack.enter_context(patch.object(r.recovery,'private_completed',return_value=union))
                self.assertEqual(r.export(True) if modern else r.a.export(True),{'valid':True})
                final.assert_called_once()
                outputs.append((report.read_bytes(),(root/supplement).read_bytes()))
                self.assertEqual(companion.exists(),modern)
                self.assertNotIn('release_tag',json.loads(report.read_text()))
        self.assertEqual(outputs[0],outputs[1])


if __name__=='__main__':unittest.main()
