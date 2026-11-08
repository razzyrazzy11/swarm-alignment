"""Fail-closed handoff checks without inference or empirical report reads."""
from pathlib import Path
import json,tempfile,unittest,zipfile
from unittest.mock import patch
from paper import completion_handoff as h

class CompletionHandoffTests(unittest.TestCase):
    def output(self,root,name='packet.json'):
        return Path(root)/'runs/paper-completion-handoff'/name
    def test_private_exclusive_write_never_overwrites(self):
        with tempfile.TemporaryDirectory() as root:
            path=self.output(root);h.write_new(path,{'test':1},root);raw=path.read_bytes()
            with self.assertRaises(ValueError):h.write_new(path,{'test':2},root)
            self.assertEqual(path.read_bytes(),raw)
    def test_public_paper_sensitive_and_parent_alias_destinations_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            for path in (Path(root)/'paper/content.json',Path(root)/'data/test.json',
                         self.output(root,'id_rsa.json'),self.output(root,'.env.json'),
                         self.output(root)/'../alias.json'):
                with self.assertRaises(ValueError):h.private_target(path,root)
    def test_symlink_alias_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.object(Path,'is_symlink',return_value=True):
                with self.assertRaises(ValueError):h.private_target(self.output(root),root)
    def test_commit_drift_rejected_before_pipeline_or_reports(self):
        with tempfile.TemporaryDirectory() as root:
            for name in h.SOURCE_FILES:
                path=Path(root)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('local')
            with patch.object(h.subprocess,'check_output',return_value=b'committed'),patch.object(h,'pipeline') as pipeline:
                with self.assertRaises(ValueError):h.diagnose(root)
                pipeline.assert_not_called()
    def test_template_drift_rejected_without_candidate_gate(self):
        with tempfile.TemporaryDirectory() as root:
            paper=Path(root)/'paper';paper.mkdir();(paper/'official-template.docx').write_bytes(b'changed')
            with patch.object(h,'committed_sources',return_value={}),patch.object(h,'pipeline') as pipeline:
                with self.assertRaises(ValueError):h.diagnose(root)
                pipeline.assert_not_called()
    def test_frozen_analysis_drift_blocks_pipeline_without_candidate(self):
        from experiments import provider_resume_analysis as analysis
        from paper import prepare_complete as prepare
        with tempfile.TemporaryDirectory() as root:
            research=Path(root)/'research';research.mkdir()
            (research/'swarm-ledger-resume-v3-freeze.json').write_text('{}')
            with patch.object(analysis,'verify',side_effect=ValueError('registration drift')),patch.object(prepare,'candidate') as candidate:
                with self.assertRaises(ValueError):h.pipeline(root)
                candidate.assert_not_called()
    def test_candidate_calls_existing_gate_and_preserves_paper(self):
        from paper import prepare_complete as prepare
        with tempfile.TemporaryDirectory() as root:
            current=Path(root)/'paper/content.json';current.parent.mkdir();current.write_text('historical')
            path=self.output(root,'candidate.json')
            with patch.object(prepare,'candidate',side_effect=ValueError('incomplete actual data')) as gate:
                with self.assertRaises(ValueError):h.create_candidate(path,root)
                gate.assert_called_once_with(Path(root)/'paper')
            self.assertFalse(path.exists());self.assertEqual(current.read_text(),'historical')
    def test_existing_candidate_refused_before_any_readiness_call(self):
        from paper import prepare_complete as prepare
        with tempfile.TemporaryDirectory() as root:
            path=self.output(root,'candidate.json');path.parent.mkdir(parents=True);path.write_text('keep')
            with patch.object(prepare,'candidate') as gate:
                with self.assertRaises(ValueError):h.create_candidate(path,root)
                gate.assert_not_called()
            self.assertEqual(path.read_text(),'keep')
    def test_handoff_has_explicit_unknowns_and_no_visual_attestation(self):
        from paper import prepare_complete as prepare
        with tempfile.TemporaryDirectory() as root:
            paper=Path(root)/'paper';paper.mkdir();template=paper/'official-template.docx'
            with zipfile.ZipFile(template,'w') as archive:
                for name in ('word/document.xml','word/styles.xml','word/fontTable.xml'):archive.writestr(name,'placeholder')
            (paper/'complete-draft.json').write_text(json.dumps(dict(preparation_status='RESULT-BLIND DRAFT — NOT FOR SUBMISSION',pending_results='pending',abstract='PENDING')))
            with patch.object(h,'TEMPLATE_SHA',h.sha(template)),patch.object(h,'committed_sources',return_value={}),patch.object(h,'pipeline',return_value={'stages':list(h.STAGES)}),patch.object(prepare,'ready') as ready,patch.object(prepare,'candidate') as candidate:
                value=h.diagnose(root)
                ready.assert_not_called();candidate.assert_not_called()
            self.assertFalse(value['empirical_reports_read']);self.assertFalse(value['visual_qa_complete'])
            self.assertFalse(value['paper_integration_complete']);self.assertFalse(value['scientific_validation_complete'])
            self.assertEqual([step['step'] for step in value['authoring_steps']],list(range(1,8)))
            self.assertEqual(len(value['author_slots']),14)
            self.assertTrue(all(slot['status'].startswith('UNRESOLVED') for slot in value['author_slots']))

if __name__=='__main__':unittest.main()
