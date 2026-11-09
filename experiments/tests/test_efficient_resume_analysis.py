"""Efficient scheduling admission tests; synthetic metadata only, no inference."""
from pathlib import Path
import tempfile,json,unittest
from unittest.mock import patch
from experiments import efficient_resume_analysis as a

class EfficientResumeAnalysisTests(unittest.TestCase):
    def test_five_batch_union_preserves_http500_and_hf_unavailability(self):
        failed={'id':'b','transport':{'http_status':500},'known_usage':False,'estimated_cost':'1'}
        unavailable={'id':'c','transport':{'http_status':429},'known_usage':False,'estimated_cost':'2'}
        result=a.disjoint_union([[{'id':'a'}],[failed],[unavailable],[{'id':'d'}],[{'id':'e'}]],['a','b','c','d','e'])
        self.assertIs(result[1],failed)
        self.assertEqual(result[1]['estimated_cost'],'1')
        self.assertFalse(result[1]['known_usage'])
        self.assertIs(result[2],unavailable)
    def test_union_rejects_duplicate_missing_and_extra(self):
        for groups,wanted in (([[{'id':'a'}],[],[{'id':'a'}]],['a']),
                              ([[{'id':'a'}],[],[]],['a','b']),
                              ([[{'id':'a'}],[],[{'id':'x'}]],['a'])):
            with self.assertRaises(ValueError):a.disjoint_union(groups,wanted)
    def test_actual_efficient_complete_driver_required_without_state_edit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'state.json';p.write_text(json.dumps({'status':'stopped'}));raw=p.read_bytes()
            with patch.object(a,'ROOT',root):
                with self.assertRaises(ValueError):a.terminated('state.json',True)
            self.assertEqual(p.read_bytes(),raw)
    def test_old_main_driver_must_be_actually_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'state.json';p.write_text(json.dumps({'status':'complete'}))
            with patch.object(a,'ROOT',root):
                with self.assertRaises(ValueError):a.terminated('state.json',stopped=True)
    def test_analysis_freeze_refuses_live_v3_without_writing_registration(self):
        with tempfile.TemporaryDirectory() as d:
            freeze=Path(d)/'new-freeze.json';seen=[]
            def stopped(path,**kwargs):
                seen.append(path)
                if 'resume-v3-driver' in path:raise ValueError('v3 still running')
                return 'a'*64
            with patch.object(a,'FREEZE',freeze),patch.object(a,'SOURCES',()),patch.object(a,'terminated',side_effect=stopped):
                with self.assertRaises(ValueError):a.freeze()
            self.assertFalse(freeze.exists())
            self.assertIn('runs/swarm-ledger-resume-v3-driver/state.json',seen)
    def test_canonical_five_batch_main_driver_paths(self):
        seen=[]
        with patch.object(a,'terminated',side_effect=lambda p,c,**kw:seen.append((p,c,kw['stopped'])) or 'hash'):
            a.drivers('main')
        self.assertEqual(seen,[('runs/swarm-ledger-v1-main-driver/state.json',False,True),
            ('runs/swarm-ledger-resume-v1-driver/state.json',False,True),
            ('runs/swarm-ledger-resume-v2-driver/state.json',False,True),
            ('runs/swarm-ledger-resume-v3-driver/state.json',False,True),
            ('runs/swarm-ledger-efficient-v1-driver/state.json',True,False)])
    def test_hf_canonical_driver_paths_and_unknown_kind(self):
        seen=[]
        with patch.object(a,'terminated',side_effect=lambda p,c,**kw:seen.append((p,c,kw['stopped'])) or 'hash'):
            a.drivers('hf')
        self.assertIn(('runs/hf-completion-driver-v1/state.json',False,False),seen)
        self.assertIn(('runs/hf-completion-v3-driver/state.json',True,False),seen)
        with self.assertRaises(ValueError):a.drivers('other')
    def test_live_or_reused_pid_blocks_stale_complete_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'state.json'
            p.write_text(json.dumps(dict(status='complete',pid=100,updated='2026-01-01T00:00:00+00:00')))
            with patch.object(a,'ROOT',root),patch('experiments.swarm_ledger_complete_dispatch.process_dead',side_effect=ValueError('still alive')):
                with self.assertRaises(ValueError):a.terminated('state.json',True)
    def test_driver_mutation_during_creation_identity_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'state.json'
            p.write_text(json.dumps(dict(status='complete',pid=100,updated='2026-01-01T00:00:00+00:00')))
            def mutate(*args):p.write_text('{}')
            with patch.object(a,'ROOT',root),patch('experiments.swarm_ledger_complete_dispatch.process_dead',side_effect=mutate):
                with self.assertRaises(ValueError):a.terminated('state.json',True)
    def test_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'exists';target.mkdir()
            with patch.object(a,'ROOT',root),patch.object(a,'verify'),patch.object(a,'no_collectors'):
                with self.assertRaises(ValueError):a.export_main(target)
    def test_hf_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            existing=Path(d)/'report';existing.write_text('prior')
            with patch.object(a,'verify'),patch.object(a,'HF_REPORT',existing):
                with self.assertRaises(ValueError):a.export_hf()
            self.assertEqual(existing.read_text(),'prior')
    def test_stale_lock_blocks_release_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'runs/x/collector.lock';p.parent.mkdir(parents=True);p.write_text('owned')
            with patch.object(a,'ROOT',root):
                with self.assertRaises(ValueError):a.no_collectors()
            self.assertTrue(p.exists())
    def test_incomplete_new_driver_blocks_main_before_scoring(self):
        from experiments import swarm_ledger_efficient as resume
        with patch.object(resume,'verify'),patch.object(a,'drivers',side_effect=ValueError('efficient incomplete')),patch.object(a.a,'score_case') as score:
            with self.assertRaises(ValueError):a.admission_main()
            score.assert_not_called()
    def test_incomplete_main_blocks_separate_hf_before_private_read(self):
        from experiments import hf_completion_v3 as resume
        with patch.object(resume,'verify'),patch.object(a,'drivers',side_effect=ValueError('efficient incomplete')),patch.object(resume,'private_completed') as load:
            with self.assertRaises(ValueError):a.hf_completed()
            load.assert_not_called()
    def test_proof_binds_five_driver_inventory_and_all_continuations(self):
        from experiments import swarm_ledger_efficient as resume
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);public=root/'public';public.mkdir();(root/'research').mkdir()
            prior=root/'research/swarm-ledger-resume-v1-freeze.json'
            server=root/'research/swarm-ledger-resume-v2-freeze.json'
            provider=root/'research/swarm-ledger-resume-v3-freeze.json'
            for p in (public/'manifest.json',public/'report.json',root/'analysis.json',root/'resume.json',prior,server,provider):p.write_text('{}')
            proof=dict(schema_version=1,analysis_tag=a.TAG,analysis_freeze_sha256=a.s.sha(root/'analysis.json'),
                continuation_freeze_sha256=a.s.sha(root/'resume.json'),prior_continuation_freeze_sha256=a.s.sha(prior),
                server_continuation_freeze_sha256=a.s.sha(server),provider_continuation_freeze_sha256=a.s.sha(provider),
                driver_state_sha256={'runs/swarm-ledger-v1-main-driver/state.json':'a'*64,
                  'runs/swarm-ledger-resume-v1-driver/state.json':'b'*64,
                  'runs/swarm-ledger-resume-v2-driver/state.json':'c'*64,
                  'runs/swarm-ledger-resume-v3-driver/state.json':'d'*64,
                  'runs/swarm-ledger-efficient-v1-driver/state.json':'e'*64},
                public_manifest_sha256=a.sha(public/'manifest.json'),public_report_sha256=a.sha(public/'report.json'),
                unchanged_scientific_serializer=True,verification={'valid':True},inference_calls=0)
            sidecar=root/'proof.json';sidecar.write_text(json.dumps(proof))
            with patch.object(a,'ROOT',root),patch.object(a,'verify'),patch.object(a,'MAIN_PROOF',sidecar),patch.object(a,'FREEZE',root/'analysis.json'),patch.object(resume,'FREEZE',root/'resume.json'):
                self.assertTrue(a.verify_main(public,replay=False)['valid'])
                for mutation in ('driver_inventory','prior_registration','server_registration','provider_registration','report'):
                    changed=json.loads(json.dumps(proof));(public/'report.json').write_text('{}');prior.write_text('{}');server.write_text('{}');provider.write_text('{}')
                    if mutation=='driver_inventory':changed['driver_state_sha256'].pop('runs/swarm-ledger-efficient-v1-driver/state.json')
                    if mutation=='prior_registration':prior.write_text('{"changed":true}')
                    if mutation=='server_registration':server.write_text('{"changed":true}')
                    if mutation=='provider_registration':provider.write_text('{"changed":true}')
                    if mutation=='report':(public/'report.json').write_text('{"changed":true}')
                    sidecar.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):a.verify_main(public,replay=False)
    def test_hf_extra_fields_rejected_before_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            report=Path(d)/'report';report.write_text(json.dumps({'schema_version':2,'unexpected':'hidden'}))
            with patch.object(a,'verify'),patch.object(a,'HF_REPORT',report):
                with self.assertRaises(ValueError):a.verify_hf()

if __name__=='__main__':unittest.main()
