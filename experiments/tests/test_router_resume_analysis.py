"""Operational admission invariants; no empirical outcome inspection or API calls."""
from pathlib import Path
import tempfile,json,unittest
from unittest.mock import patch
from experiments import router_resume_analysis as a

class ResumeAnalysisTests(unittest.TestCase):
    def test_union_preserves_failed_terminals(self):
        failed={'id':'a','http_status':None,'estimated_cost':'1'}
        result=a.disjoint_union([[failed],[{'id':'b','http_status':200}]],['a','b'])
        self.assertIs(result[0],failed)
        self.assertIsNone(result[0]['http_status'])
    def test_union_rejects_duplicate_missing_and_extra(self):
        for groups,wanted in (([[{'id':'a'}],[{'id':'a'}]],['a']),([[{'id':'a'}]],['a','b']),([[{'id':'a'},{'id':'b'}]],['a'])):
            with self.assertRaises(ValueError):a.disjoint_union(groups,wanted)
    def test_actual_complete_driver_required_no_state_edit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'state.json';p.write_text(json.dumps({'status':'stopped'}));raw=p.read_bytes()
            with patch.object(a,'ROOT',root):
                with self.assertRaises(ValueError):a.terminated('state.json',True)
            self.assertEqual(p.read_bytes(),raw)
    def test_real_canonical_driver_paths(self):
        seen=[]
        with patch.object(a,'terminated',side_effect=lambda p,c:seen.append((p,c)) or 'hash'):
            a.drivers('hf')
        self.assertIn(('runs/hf-completion-driver-v1/state.json',False),seen)
        self.assertIn(('runs/hf-completion-v3-driver/state.json',True),seen)
        self.assertFalse(any('hf-completion-v1-driver' in p for p,_ in seen))
    def test_main_output_cannot_overwrite(self):
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
    def test_stale_collector_lock_blocks_release(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'runs/x/collector.lock';p.parent.mkdir(parents=True);p.write_text('owned')
            with patch.object(a,'ROOT',root):
                with self.assertRaises(ValueError):a.no_collectors()
            self.assertTrue(p.exists())
    def test_main_public_proof_binds_manifest_report_and_new_registration(self):
        from experiments import swarm_ledger_resume as resume
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);public=root/'public';public.mkdir()
            for p in (public/'manifest.json',public/'report.json',root/'analysis.json',root/'resume.json'):p.write_text('{}')
            proof=dict(schema_version=1,analysis_tag=a.TAG,analysis_freeze_sha256=a.s.sha(root/'analysis.json'),
                continuation_freeze_sha256=a.s.sha(root/'resume.json'),driver_state_sha256={
                  'runs/swarm-ledger-v1-main-driver/state.json':'a'*64,'runs/swarm-ledger-resume-v1-driver/state.json':'b'*64},
                public_manifest_sha256=a.sha(public/'manifest.json'),public_report_sha256=a.sha(public/'report.json'),
                unchanged_scientific_serializer=True,verification={'valid':True},inference_calls=0)
            sidecar=root/'proof.json';sidecar.write_text(json.dumps(proof))
            with patch.object(a,'verify'),patch.object(a,'MAIN_PROOF',sidecar),patch.object(a,'FREEZE',root/'analysis.json'),patch.object(resume,'FREEZE',root/'resume.json'):
                self.assertTrue(a.verify_main(public,replay=False)['valid'])
                (public/'report.json').write_text('{"changed":true}')
                with self.assertRaises(ValueError):a.verify_main(public,replay=False)
    def test_hf_report_rejects_unregistered_extra_field_before_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            report=Path(d)/'report';report.write_text(json.dumps({'schema_version':2,'unexpected':'hidden'}))
            with patch.object(a,'verify'),patch.object(a,'HF_REPORT',report):
                with self.assertRaises(ValueError):a.verify_hf()

if __name__=='__main__':unittest.main()
