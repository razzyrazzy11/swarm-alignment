"""Synthetic PID/state and serializer parity tests; no actual study data/calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from analysis import ledger_release as r


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cfg={'study_id':'toy-science'}
        self.patches=[patch.object(r.s,'ROOT',self.root),patch.object(r.s,'config',side_effect=lambda:deepcopy(self.cfg)),
            patch.object(r.s,'folder',side_effect=lambda split:self.root/('runs/toy-science-'+split)),
            patch.object(r.s,'freeze_path',side_effect=lambda split:self.root/('research/toy-science-'+split+'-freeze.json'))]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.state=self.root/'runs/toy-science-main-driver/state.json';self.state.parent.mkdir(parents=True)
        self.value=dict(status='complete',pid=101,child_pid=102,updated='2000-01-01T00:00:00+00:00')
        self.state.write_text(json.dumps(self.value))
        self.guard=self.root/'runs/toy-science-guard/collector.lock';self.guard.parent.mkdir();self.guard.write_text('toy owned lock')

    def data(self):
        data=dict(contexts=[{'toy':True}],sources=[{'source_id':'toy'}],cases=[{'profile_id':'g26','toy':True}],
            calibration=[{'toy':True}],influence_sources=[{'toy':True}],actor_rows=[],influence_rows=[],
            coverage={'toy':{'complete':True}},engineering=dict(development_contexts=[{'toy':True}],
                development_actor_rows=[],technical_rows=[],development_reader_rows=[]))
        data['_admission']=dict(data_sha256=r.a.data_commitment(data),driver_state=str(self.state.resolve()),
            driver_state_sha256=hashlib.sha256(self.state.read_bytes()).hexdigest(),registration_sha256='science',
            operational_registration_sha256='ops')
        return data

    def test_absent_parent_and_child_accept_without_changing_actual_toy_state(self):
        original=self.state.read_bytes()
        with patch.object(r.dispatch.subprocess,'run',return_value=SimpleNamespace(returncode=3,stdout=b'')) as process:
            proof=r.termination_proof(self.state,self.guard)
        self.assertEqual(process.call_count,2);self.assertEqual(self.state.read_bytes(),original)
        self.assertEqual(proof['driver_state_sha256'],hashlib.sha256(original).hexdigest())

    def test_creation_proves_reused_pid_without_rewriting_state(self):
        original=self.state.read_bytes()
        result=SimpleNamespace(returncode=0,stdout=b'2001-01-01T00:00:00+00:00\r\n')
        with patch.object(r.dispatch.subprocess,'run',return_value=result) as process:
            r.termination_proof(self.state,self.guard)
        self.assertEqual(self.state.read_bytes(),original)
        self.assertTrue(all('Get-Process' in call.args[0][-1] and 'Stop-Process' not in call.args[0][-1] for call in process.call_args_list))

    def test_live_equal_older_and_unknown_processes_fail_closed(self):
        for code,stamp in ((0,b'1999-01-01T00:00:00Z'),(0,b'2000-01-01T00:00:00Z'),(0,b'not-a-date'),(4,b'')):
            with patch.object(r.dispatch.subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=stamp)):
                with self.assertRaises(ValueError):r.termination_proof(self.state,self.guard)

    def test_wrong_path_status_timestamp_and_child_are_rejected(self):
        other=self.root/'runs/toy-pilot-driver/state.json';other.parent.mkdir();other.write_bytes(self.state.read_bytes())
        with self.assertRaises(ValueError):r.termination_proof(other,self.guard)
        for change in (dict(status='running'),dict(updated='2000-01-01T00:00:00'),dict(updated='2999-01-01T00:00:00Z'),dict(child_pid=None),dict(child_pid=101)):
            self.state.write_text(json.dumps(dict(self.value,**change)))
            with self.assertRaises(ValueError):r.termination_proof(self.state,self.guard)

    def test_state_change_during_checks_and_unrelated_lock_are_preserved(self):
        def changed(*args):self.state.write_text(json.dumps(dict(self.value,exit_code=0)))
        with patch.object(r.dispatch,'process_dead',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed during'):r.termination_proof(self.state,self.guard)
        self.state.write_text(json.dumps(self.value))
        lock=self.root/'runs/unrelated-study/collector.lock';lock.parent.mkdir();lock.write_text('other owner')
        with patch.object(r.dispatch,'process_dead',return_value=True):
            with self.assertRaisesRegex(ValueError,'global collector lock'):r.termination_proof(self.state,self.guard)
        self.assertEqual(lock.read_text(),'other owner')

    def test_private_proof_detects_state_data_and_registration_drift(self):
        with patch.object(r,'_registrations',return_value=dict(registration_sha256='science',operational_registration_sha256='ops')),patch.object(r.dispatch,'process_dead',return_value=True):
            original=self.data();r.check_admission(original,self.guard)
            for key in ('driver_state_sha256','registration_sha256','operational_registration_sha256'):
                data=deepcopy(original);data['_admission'][key]='changed'
                with self.assertRaises(ValueError):r.check_admission(data,self.guard)
            data=deepcopy(original);data['contexts'][0]['toy']=False
            with self.assertRaises(ValueError):r.check_admission(data,self.guard)
            data=deepcopy(original);data['coverage']['toy']['complete']=False
            data['_admission']['data_sha256']=r.a.data_commitment(data)
            with self.assertRaisesRegex(ValueError,'must be complete'):r.check_admission(data,self.guard)

    def test_unresolved_frozen_admission_error_prevents_export(self):
        identity=dict(driver_state=str(self.state),driver_state_sha256='toy')
        with patch.object(r,'_registrations',return_value={}),patch.object(r,'termination_proof',return_value=identity),patch.object(r.s,'contexts',return_value=[]),patch.object(r.a,'validate_contexts'),patch.object(r.s,'read',return_value={'contexts_sha256':r.s.digest([])}),patch.object(r.a,'validate_pre_main',return_value=({},{})),patch.object(r.s,'actor_jobs',return_value=[{'id':'toy'}]),patch.object(r.a,'admit_phase',side_effect=ValueError('Unknown started request: manual reconciliation required')),patch.object(r,'_write_public') as writer:
            with self.assertRaisesRegex(ValueError,'Unknown started'):
                r._build_private(self.state,self.guard)
            writer.assert_not_called()

    def test_serializer_matches_frozen_bytes_without_duplicate_bootstrap(self):
        data=self.data();original=deepcopy(data)
        original['_admission']={k:original['_admission'][k] for k in ('data_sha256','driver_state','registration_sha256')}
        one=self.root/'original';two=self.root/'wrapper'
        with patch.object(r.a,'analyze',return_value={'toy_report':'synthetic serialization only'}) as analyze,patch.object(r.a,'release_idle'),patch.object(r.s,'registration',return_value={}),patch.object(r.s,'sha',return_value='science'),patch.object(r.s,'actor_jobs',return_value=[]),patch.object(r.s,'influence_jobs',return_value=[]),patch.object(r.s,'reader_jobs',return_value=[]),patch.object(r.s,'source_worlds',return_value=[]),patch.object(r.s,'technical_jobs',return_value=[]),patch.object(r.s,'read',return_value={'toy_registration':True}):
            r.a._export(original,one,owned_lock=self.guard)
            r._write_public(data,two)
            self.assertEqual(analyze.call_count,2)
        files=lambda p:{x.name:x.read_bytes() for x in p.iterdir()}
        self.assertEqual(files(one),files(two))
        self.assertNotIn('operational_registration.json',files(two))

    def test_preflight_and_postflight_failures_prevent_authorized_export(self):
        target=self.root/'new-public';data=self.data()
        with patch.object(r,'check_admission',side_effect=ValueError('live')),patch.object(r,'_write_public') as writer:
            with self.assertRaises(ValueError):r._export(data,target,self.guard)
            writer.assert_not_called()
        with patch.object(r,'check_admission',side_effect=[True,ValueError('state drift')]),patch.object(r,'_write_public',return_value={}),patch.object(r.a,'verify_public') as verify:
            with self.assertRaises(ValueError):r._export(data,target,self.guard)
            verify.assert_not_called()
        with patch.object(r,'check_admission',return_value=True) as preflight,patch.object(r,'_write_public',return_value={}),patch.object(r.a,'verify_public',return_value={'valid':True}) as verify:
            result=r._export(data,target,self.guard)
            self.assertEqual(result['verification'],{'valid':True});self.assertEqual(preflight.call_count,3)
            verify.assert_called_once_with(target)


if __name__=='__main__':unittest.main()
