"""Synthetic metadata-only readiness checks; no provider calls or outcomes."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from types import SimpleNamespace
from experiments import server_resume_preflight as p

class ServerPreflightTests(unittest.TestCase):
    def test_absent_process_query_explicitly_normalizes_powershell_exit(self):
        with patch.object(p.os,'name','nt'),patch.object(p.subprocess,'run',return_value=SimpleNamespace(stdout='')) as run:
            self.assertIsNone(p.process_snapshot(99))
            self.assertIn('exit 0',run.call_args.args[0][-1])
    def make(self,root,batch='swarm-ledger-resume-v2-main',ids=('a',),starts=None,terminals=None):
        folder=Path(root)/'runs'/batch/'readers';folder.mkdir(parents=True)
        (folder/'plan.json').write_text(json.dumps(dict(jobs_sha256='a'*64,freeze_sha256='b'*64,ids=list(ids))))
        if starts is None:starts=[dict(id='a',profile_id='g26',request_sha256='c'*64,reserved_cost='1')]
        if terminals is None:terminals=[]
        for name,rows in (('attempts',starts),('responses',terminals)):
            (folder/(name+'.jsonl')).write_text(''.join(json.dumps(x)+'\n' for x in rows))
        return folder
    def test_inflight_and_partial_final_line_are_not_corruption(self):
        with tempfile.TemporaryDirectory() as root:
            folder=self.make(root)
            with (folder/'responses.jsonl').open('a') as stream:stream.write('{"incomplete')
            value=p.journal_metadata(root)
            self.assertEqual(value['total_started'],1);self.assertEqual(value['total_terminal'],0)
            self.assertEqual(value['partial_final_lines'],1)
    def test_duplicate_reissue_and_terminal_subset_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            failure=dict(id='a',profile_id='g26',known_usage=False,estimated_cost='1')
            self.make(root,batch='swarm-ledger-resume-v1-main',terminals=[failure]);self.make(root)
            with self.assertRaises(ValueError):p.journal_metadata(root)
        with tempfile.TemporaryDirectory() as root:
            self.make(root,terminals=[dict(id='unstarted')])
            with self.assertRaises(ValueError):p.journal_metadata(root)
    def test_unknown_failure_retains_full_reservation(self):
        with tempfile.TemporaryDirectory() as root:
            failure=dict(id='a',profile_id='g26',known_usage=False,estimated_cost='1',transport=dict(http_status=500),response={'private':'must not appear'})
            self.make(root,terminals=[failure]);value=p.journal_metadata(root)
            self.assertEqual(value['total_terminal'],1)
            self.assertNotIn('must not appear',json.dumps(value))
        with tempfile.TemporaryDirectory() as root:
            failure['estimated_cost']='0';self.make(root,terminals=[failure])
            with self.assertRaises(ValueError):p.journal_metadata(root)
    def test_body_commitment_drift_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.make(root,batch='swarm-ledger-resume-v1-main',starts=[],terminals=[])
            folder=self.make(root,starts=[],terminals=[])
            plan=json.loads((folder/'plan.json').read_text());plan['jobs_sha256']='d'*64
            (folder/'plan.json').write_text(json.dumps(plan))
            with self.assertRaises(ValueError):p.journal_metadata(root)
    def test_running_process_must_have_current_creation_identity(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'runs/swarm-ledger-resume-v2-driver';folder.mkdir(parents=True)
            (folder/'state.json').write_text(json.dumps(dict(status='running',pid=11,updated='2026-01-01T00:00:00+00:00')))
            for observed in (None,dict(pid=11,created_utc='2026-01-02T00:00:00+00:00')):
                with patch.object(p,'process_snapshot',return_value=observed):
                    with self.assertRaises(ValueError):p.driver_metadata(root)
    def test_complete_state_is_not_scientific_validation(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'runs/swarm-ledger-resume-v2-driver';folder.mkdir(parents=True)
            (folder/'state.json').write_text(json.dumps(dict(status='complete',pid=11,updated='2026-01-01T00:00:00+00:00')))
            with patch.object(p,'process_snapshot',return_value=None):value=p.driver_metadata(root)
            self.assertFalse(value['swarm-ledger-resume-v2-driver']['scientific_readiness'])
    def test_failure_aggregation_never_claims_integration(self):
        from experiments import swarm_ledger_resume_v2 as resume
        from experiments import server_resume_analysis as analysis
        with patch.object(resume,'verify',return_value={'valid':True}),patch.object(analysis,'verify',return_value={'valid':True}),patch.object(p,'context_metadata',return_value={}),patch.object(p,'driver_metadata',side_effect=ValueError('private never emit')),patch.object(p,'journal_metadata',return_value={}),patch.object(p,'environment',return_value={}):
            value=p.check()
        self.assertFalse(value['operational_preflight_passed']);self.assertFalse(value['scientific_validation_complete'])
        self.assertFalse(value['paper_integration_complete']);self.assertNotIn('private never emit',json.dumps(value))

if __name__=='__main__':unittest.main()
