"""Toy aggregate fixtures only. No MAIN output, credentials or public export read."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
PAPER=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PAPER));sys.path.insert(0,str(PAPER.parent))
import complete_report_contract as c
import verify


def fixture():
    # Field names/denominators match the frozen complete-analysis synthetic
    # public-replay test; these zero-valued toy aggregates are never exported.
    effect=dict(estimate=0.0,lower=0.0,upper=0.0,blocks=640,strata=40,draws=10000)
    fields=('answerable','admitted','semantic_valid','strict_json','correct_supported','correct_definite',
            'gated_correct_definite','exact_executor','any_executor','unsafe_none','false_executor','abstain','invalid')
    conditions={}
    for p in c.READERS:
        for v,method,n in [('full','direct',2560),('full','procedure',2560)]+[(v,'direct',1280) for v in c.VIEWS if p in c.AUXILIARY]:
            conditions[p+':'+v+':'+method]=dict(responses=n,independent_blocks=640,actual_positive=0,actual_negative=n,
                 numerators={key:n if key in ('admitted','invalid') else 0 for key in fields})
    acq={p+':'+v+'-selective_loss':{key:deepcopy(effect) for key in ('oracle_answerability','correct_definite','correct_supported_including_required_abstention')}
           for p in c.AUXILIARY for v in ('receipt_only7','random_loss','selective_random2','selective_metadata2','selective_contract2')}
    for p in c.AUXILIARY:
        for left,right in (('selective_metadata2','selective_random2'),('selective_contract2','selective_metadata2')):
            acq[p+':'+left+'-'+right]={key:deepcopy(effect) for key in ('oracle_answerability','correct_definite','correct_supported_including_required_abstention')}
    coverage={phase:dict(planned=n,started=n,terminal=n,unstarted=0,complete=True) for phase,n in
       dict(principal=640,coordinator=640,x=2560,y=2560,reporter=2560,readers=53760,calibration=240,influence=240).items()}
    report=dict(study_id='swarm-ledger-v1',registration_prefix='swarm-ledger-complete-v1',main_reader_profiles=list(c.READERS),
       auxiliary_reader_profiles=list(c.AUXILIARY),source_blocks=640,assigned_trajectories=2560,reader_responses=53760,
       calibration={'responses':240},primary=effect,coverage=coverage,conditions=conditions,acquisition_direct=acq,
       secondary_procedure_effects={p:deepcopy(effect) for p in c.READERS if p!='g26'})
    content=dict(ledger_registration=c.REGISTRATION,title='Track 4: Toy fake-data study',
      abstract='Adaption, Hugging Face and Ollama read bounded fake-data evidence.',
      sections=[['Results',list(c.expected_anchors(report).values())]],
      appendix=[['Limitations and Dual-Use / Ethical Considerations',['Toy limitations.']]],references=[])
    content.update(c.expected_fields(report))
    return report,content


class CompleteReportContractTests(unittest.TestCase):
    def setUp(self):self.report,self.content=fixture()
    def test_compact_tables_preserve_all_condition_denominators(self):
        self.assertTrue(c.validate_manuscript(self.content,self.report))
        self.assertEqual(len(self.content['table1']),7);self.assertEqual(len(self.content['table2']),7)
        self.assertEqual(len(self.content['table3']),4)
        self.assertEqual(len(self.content['ledger_results']['conditions']),30)
        self.assertEqual(sum(v['responses'] for v in self.content['ledger_results']['conditions'].values()),53760)
    def test_changed_primary_interval_and_prose_cannot_silently_drift(self):
        self.content['sections'][0][1][1]=self.content['sections'][0][1][1].replace('+0.00','+0.01',1)
        with self.assertRaisesRegex(ValueError,'anchor: primary'):c.validate_manuscript(self.content,self.report)
        self.report,self.content=fixture();self.content['ledger_results']['primary']['lower']=-.01
        with self.assertRaisesRegex(ValueError,'aggregate differs: ledger_results'):c.validate_manuscript(self.content,self.report)
    def test_delivery_schema_and_reasoning_are_separate(self):
        row=self.content['table2'][1];self.assertEqual(row[2],'12800 / 0 / 0')
        self.assertEqual(self.content['table1'][1][1],'0 / 0')
        self.content['table2'][1][2]='12800 / 12800 / 12800'
        with self.assertRaisesRegex(ValueError,'table2'):c.validate_manuscript(self.content,self.report)
    def test_caption_can_hold_verified_anchor_but_not_metadata_only(self):
        sentence=self.content['sections'][0][1].pop(1)
        with self.assertRaisesRegex(ValueError,'anchor: primary'):c.validate_manuscript(self.content,self.report)
        self.content['figures']=[{'caption':sentence}]
        self.assertTrue(c.validate_manuscript(self.content,self.report))
    def test_partial_terminal_and_calibration_or_legacy_pool_rejected(self):
        for change in ('partial','pool','calibration','profile'):
            r=deepcopy(self.report)
            if change=='partial':r['coverage']['readers']['complete']=False
            elif change=='pool':r['source_blocks']=832
            elif change=='calibration':r['calibration']['responses']=0
            else:r['main_reader_profiles'].append('q397')
            with self.assertRaises(ValueError):c.validate_report(r)
    def test_denominator_and_condition_omission_rejected(self):
        self.report['conditions']['g26:full:direct']['responses']=2559
        with self.assertRaisesRegex(ValueError,'denominator'):c.validate_report(self.report)
        self.report,_=fixture();self.report['conditions'].pop('hf_schema:full:procedure')
        with self.assertRaisesRegex(ValueError,'condition grid'):c.validate_report(self.report)
    def test_missing_track_fake_scope_and_appendix_rejected(self):
        for change in ('track','fake','appendix'):
            content=deepcopy(self.content)
            if change=='track':content['title']='Toy study'
            elif change=='fake':content['title']=content['title'].replace('fake-data','bounded');content['abstract']=content['abstract'].replace('fake-data','bounded')
            else:content['appendix']=[]
            with self.assertRaises(ValueError):c.validate_manuscript(content,self.report)
    def test_only_explicit_new_flag_routes_new_public_replay(self):
        with patch.object(c,'load_completed',return_value=(self.report,{})) as load:
            verify.validate_source(self.content);verify.validate_results(PAPER,self.content)
            load.assert_called_once_with(PAPER,replay=True)
        self.content['ledger_registration']='unregistered-test'
        with self.assertRaisesRegex(ValueError,'Unknown'):verify.validate_source(self.content)
    def test_absent_completed_release_cannot_publish_planned_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Completed public release'):c.load_completed(Path(tmp)/'paper')
    def test_loader_calls_frozen_replay_and_binds_actual_artifact_bytes(self):
        from experiments import swarm_ledger_complete_analysis as a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'paper';root.mkdir();directory=Path(tmp)/'data/swarm-ledger-v1-public';directory.mkdir(parents=True)
            names=('manifest.json','report.json','registration.json','operational-registration.json')
            for name in names:(directory/name).write_text('{}',encoding='utf-8')
            manifest=dict(registration_sha256='a'*64,operational_registration_sha256='b'*64)
            with patch.object(a,'verify_public',return_value={'valid':True}) as replay,patch.object(a,'load_public_artifacts',return_value=({},self.report,manifest)):
                _,anchors=c.load_completed(root)
                replay.assert_called_once_with(directory)
            self.assertEqual(anchors['report.json'],hashlib.sha256(b'{}').hexdigest())
            self.assertEqual(anchors['scientific_registration_sha256'],'a'*64)
    def test_rate_provenance_is_required_before_any_public_replay(self):
        from experiments import swarm_ledger_complete_analysis as a
        from experiments import rate_resume_analysis as rate
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'paper';root.mkdir()
            directory=Path(tmp)/'data/swarm-ledger-v1-public';directory.mkdir(parents=True)
            research=Path(tmp)/'research';research.mkdir()
            (research/'swarm-ledger-rate-v1-freeze.json').write_text('{}')
            (research/'swarm-ledger-efficient-v1-freeze.json').write_text('{}')
            with patch.object(rate,'verify_main',side_effect=ValueError('missing new rate proof')),patch.object(a,'verify_public') as replay,patch.object(a,'load_public_artifacts') as load:
                with self.assertRaisesRegex(ValueError,'new rate proof'):c.load_completed(root)
                replay.assert_not_called();load.assert_not_called()
    def test_rate_loader_binds_new_lineage_and_uses_rate_proof(self):
        from experiments import swarm_ledger_complete_analysis as a
        from experiments import rate_resume_analysis as rate
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'paper';root.mkdir()
            directory=Path(tmp)/'data/swarm-ledger-v1-public';directory.mkdir(parents=True)
            for name in ('manifest.json','report.json','registration.json','operational-registration.json'):(directory/name).write_text('{}')
            research=Path(tmp)/'research';research.mkdir()
            lineage=('rate-resume-analysis-v1-freeze.json','swarm-ledger-rate-v1-freeze.json','swarm-ledger-rate-resume-release-proof.json')
            for name in lineage:(research/name).write_text('{}')
            manifest=dict(registration_sha256='a'*64,operational_registration_sha256='b'*64)
            with patch.object(rate,'verify_main') as proof,patch.object(a,'verify_public'),patch.object(a,'load_public_artifacts',return_value=({},self.report,manifest)):
                _,bindings=c.load_completed(root)
            proof.assert_called_once_with(directory,replay=False)
            self.assertTrue(all(bindings[name]==hashlib.sha256(b'{}').hexdigest() for name in lineage))
    def test_no_private_data_providers_or_placeholders_in_contract(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
            self.assertTrue(c.validate_manuscript(self.content,self.report))
        self.assertEqual(self.content['evidence_status']['training_runs'],0)

if __name__=='__main__':unittest.main()
