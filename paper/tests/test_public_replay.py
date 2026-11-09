"""Synthetic admission commitments only; no actual issue, inference or replay."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from paper import public_replay as p


def write(root,name,value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')
    return path


class PublicReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.paper=self.root/'paper';self.paper.mkdir()

    def registration(self):
        for name in p.SOURCES:write(self.root,name,{'synthetic':'source'})
        for name in p.PARENTS:write(self.root,name,{'synthetic':'registration'})
        value=dict(schema_version=1,tag=p.TAG,created='2026-01-01T00:00:00+00:00',base_commit='a'*40,
            source_sha256={n:p.source_hash(self.root/n) for n in p.SOURCES},
            parent_registration_sha256={n:p.source_hash(self.root/n) for n in p.PARENTS},
            public_artifact_sha256={'data/toy.json':'b'*64},verified_figure_input_sha256='c'*64,
            owner_state_sha256='d'*64,owner_supervisor_sha256='e'*64,method=p.METHOD)
        write(self.root,p.FREEZE_NAME,value)
        return value

    def admission(self):
        write(self.root,p.FREEZE_NAME,{'synthetic':'freeze'})
        write(self.root,p.PARENTS[0],{'synthetic':'parent'})
        copy=write(self.root,p.FIGURE_INPUT_NAME,{'synthetic':'safe input'})
        freeze=dict(public_artifact_sha256={'data/toy.json':'b'*64},verified_figure_input_sha256=p.raw_hash(copy),
                    owner_state_sha256='d'*64,owner_supervisor_sha256='e'*64)
        lineage={p.PARENTS[0]:{'source_sha256':{'experiments/offline_release_supervisor_v2.py':'e'*64}}}
        owner=dict(kind='offline_release_recovery_v2',status='complete',completed_stages=list(p.STAGES),child_absent=True,
            exit_code=0,inference_calls=0,state_sha256='d'*64,supervisor_sha256='e'*64,
            recovery_freeze_sha256=p.source_hash(self.root/p.PARENTS[0]),terminated_verified_at_issuance=True)
        sources={'generator_sensitivity_report_sha256':'f'*64}
        proof={'failed_waiter_sha256':{'runs/toy/state.json':'a'*64}}
        value=dict(schema_version=1,kind='paper-public-release-admission',issued_at='2026-01-01T00:00:00+00:00',
            scope=p.SCOPE,registration_tag=p.TAG,registration_freeze_sha256=p.source_hash(self.root/p.FREEZE_NAME),
            public_artifact_sha256=freeze['public_artifact_sha256'],verified_figure_input_sha256=freeze['verified_figure_input_sha256'],
            preserved_owner=owner,provenance=proof,ledger_sources=sources)
        write(self.root,p.ADMISSION_NAME,value)
        for name,result in (('verify_registration',freeze),('_lineage',lineage),('_public_proofs',proof),
                            ('ledger_sources',sources),('_figure_receipt',{})):
            patcher=patch.object(p,name,return_value=result);patcher.start();self.addCleanup(patcher.stop)
        return value

    def test_registration_requires_exact_schema_source_and_frozen_artifact_map(self):
        value=self.registration()
        with patch.object(p,'_tag_files') as tag,patch.object(p,'public_artifact_hashes',return_value=value['public_artifact_sha256']):
            self.assertEqual(p.verify_registration(self.root),value)
            tag.assert_called_once()
            (self.root/p.SOURCES[0]).write_text('altered')
            with self.assertRaisesRegex(ValueError,'source drift'):p.verify_registration(self.root)

    def test_receipt_cannot_rewrite_its_artifact_commitments(self):
        self.admission()
        value=p.read(self.root/p.ADMISSION_NAME);value['public_artifact_sha256']['data/toy.json']='0'*64
        write(self.root,p.ADMISSION_NAME,value)
        with self.assertRaisesRegex(ValueError,'artifact commitments'):p.verify_admission_metadata(self.paper)

    def test_missing_and_unknown_public_receipts_fail_closed(self):
        self.admission();path=self.root/p.ADMISSION_NAME
        value=p.read(path);value['headers']={'secret':'not a real credential'};write(self.root,p.ADMISSION_NAME,value)
        with self.assertRaisesRegex(ValueError,'receipt schema'):p.verify_admission_metadata(self.paper)
        path.unlink()
        with self.assertRaisesRegex(ValueError,'Missing public commitment'):p.verify_admission_metadata(self.paper)

    def test_owner_completion_or_provenance_mutation_fails(self):
        value=self.admission()
        for mutation in ('stage','terminated','state','provenance','sources','native_scope','boolean_exit'):
            current=deepcopy(value)
            if mutation=='stage':current['preserved_owner']['completed_stages'].pop()
            elif mutation=='terminated':current['preserved_owner']['terminated_verified_at_issuance']=False
            elif mutation=='state':current['preserved_owner']['state_sha256']='0'*64
            elif mutation=='provenance':current['provenance']['unknown']='0'*64
            elif mutation=='sources':current['ledger_sources']['unknown']='0'*64
            elif mutation=='native_scope':current['scope']='Fresh native authenticity established'
            else:current['preserved_owner']['exit_code']=False
            write(self.root,p.ADMISSION_NAME,current)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):p.verify_admission_metadata(self.paper)

    def test_public_copy_must_match_frozen_exact_bytes(self):
        self.admission()
        with (self.root/p.FIGURE_INPUT_NAME).open('ab') as stream:stream.write(b' ')
        with self.assertRaisesRegex(ValueError,'input commitment'):p.verify_admission_metadata(self.paper)

    def test_public_consumer_never_needs_private_state_or_logs(self):
        value=self.admission()
        self.assertEqual(p.verify_admission_metadata(self.paper),value)
        self.assertFalse((self.root/'runs').exists())

    def test_safe_input_rejects_private_unknown_fields_before_any_copy(self):
        for where in ('top','runtime','verification'):
            value=dict(schema_version=1,kind='swarm-ledger-verified-public-input',inputs={'toy':'a'*64},
                scientific_sources={'experiments/toy.py':'b'*64},scientific_runtime=dict(verification=deepcopy(p.MAIN_VERIFICATION),
                python_executable='toy-python',python_version='3.12',python_implementation='CPython'))
            if where=='top':value['headers']={}
            elif where=='runtime':value['scientific_runtime']['native_response_id']='toy'
            else:value['scientific_runtime']['verification']['unknown']='toy'
            write(self.root,p.FIGURE_INPUT_NAME,value)
            with self.subTest(where=where),self.assertRaises(ValueError):p._figure_receipt(self.root,p.FIGURE_INPUT_NAME)

    def test_missing_or_mismatched_tag_blocks_registration(self):
        value=self.registration()
        with patch.object(p,'public_artifact_hashes',return_value=value['public_artifact_sha256']),\
             patch.object(p,'_tag_files',side_effect=ValueError('tag drift')):
            with self.assertRaisesRegex(ValueError,'tag drift'):p.verify_registration(self.root)

    def test_changed_registered_artifact_inventory_fails(self):
        self.registration()
        with patch.object(p,'_tag_files'),patch.object(p,'public_artifact_hashes',return_value={'data/extra.json':'a'*64}):
            with self.assertRaisesRegex(ValueError,'artifact drift'):p.verify_registration(self.root)

    def test_actual_tag_byte_comparison_rejects_altered_source(self):
        write(self.root,'paper/toy.py',{'synthetic':'current source'})
        with patch.object(p,'_git',return_value=b'different tagged source'):
            with self.assertRaisesRegex(ValueError,'tag drift'):
                p._tag_files(self.root,'toy-registration','a'*40,('paper/toy.py',))

    def test_public_proofs_require_exact_driver_hashes_artifacts_and_schema(self):
        from experiments import paced_resume_analysis as paced
        names={p.PARENTS[0],p.PARENTS[2],p.HF_SUPPLEMENT,'data/swarm-ledger-v1-public/manifest.json',
            'data/swarm-ledger-v1-public/report.json'}
        parent_map={'continuation_freeze_sha256':'swarm-ledger-paced-v1','prior_continuation_freeze_sha256':'swarm-ledger-resume-v1',
            'server_continuation_freeze_sha256':'swarm-ledger-resume-v2','provider_continuation_freeze_sha256':'swarm-ledger-resume-v3',
            'efficient_continuation_freeze_sha256':'swarm-ledger-efficient-v1','rate_continuation_freeze_sha256':'swarm-ledger-rate-v1'}
        names.update('research/'+name+'-freeze.json' for name in parent_map.values())
        for name in names:write(self.root,name,{'synthetic':'public bytes'})
        main=dict(schema_version=1,analysis_tag='paced-resume-analysis-v1',analysis_freeze_sha256=p.source_hash(self.root/p.PARENTS[2]),
            driver_state_sha256={name:'a'*64 for name in p.MAIN_DRIVERS},unchanged_scientific_serializer=True,
            verification=deepcopy(p.MAIN_VERIFICATION),inference_calls=0,
            public_manifest_sha256=p.raw_hash(self.root/'data/swarm-ledger-v1-public/manifest.json'),
            public_report_sha256=p.raw_hash(self.root/'data/swarm-ledger-v1-public/report.json'))
        main.update({key:p.source_hash(self.root/'research'/(name+'-freeze.json')) for key,name in parent_map.items()})
        raw={batch:{name:'b'*64 for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}
             for batch in ('hf-completion-v1','hf-completion-v2','hf-completion-v3')}
        drivers={name:'c'*64 for name in p.HF_DRIVERS}
        report={key:None for key in paced.HF_KEYS};report.update(raw_batches_sha256=raw,driver_state_sha256=drivers)
        write(self.root,p.HF_REPORT,report)
        rule='validated-next-delay-and-private-transport-to-frozen-public-schema-v2'
        hf=dict(schema_version=1,recovery_tag='offline-release-recovery-v2',recovery_freeze_sha256=p.source_hash(self.root/p.PARENTS[0]),
            paced_analysis_freeze_sha256=p.source_hash(self.root/p.PARENTS[2]),projection_rule=rule,
            public_report_sha256=p.raw_hash(self.root/p.HF_REPORT),public_supplement_sha256=p.raw_hash(self.root/p.HF_SUPPLEMENT),
            raw_batches_sha256=raw,driver_state_sha256=drivers,
            frozen_verification=dict(valid=True,original_terminals=11640,supplement_terminals=1898,inference_calls=0),inference_calls=0)
        lineage={p.PARENTS[0]:dict(projection_rule=rule,failed_waiter_sha256={name:'d'*64 for name in p.FAILED_V2})}
        write(self.root,p.MAIN_PROOF,main);write(self.root,p.HF_PROOF,hf)
        self.assertEqual(p._public_proofs(self.root,lineage)['hf_driver_state_sha256'],drivers)
        for change in ('unknown','driver','parent','artifact','nested'):
            value=deepcopy(main)
            if change=='unknown':value['private_native_identifier']='synthetic'
            elif change=='driver':value['driver_state_sha256']['runs/unknown/state.json']='e'*64
            elif change=='parent':value['continuation_freeze_sha256']='e'*64
            elif change=='artifact':value['public_report_sha256']='e'*64
            else:value['verification']['unknown']='synthetic'
            write(self.root,p.MAIN_PROOF,value)
            with self.subTest(change=change),self.assertRaises(ValueError):p._public_proofs(self.root,lineage)

    def test_issuer_private_gate_must_pass_before_output(self):
        from paper import prepare_complete
        with patch.object(p,'verify_registration',return_value={}) as registered,\
             patch.object(prepare_complete,'ready',side_effect=ValueError('private gate blocked')):
            with self.assertRaisesRegex(ValueError,'private gate blocked'):p.issue(self.paper)
            registered.assert_called_once_with(self.root,require_pushed=True)
        self.assertFalse((self.root/p.ADMISSION_NAME).exists());self.assertFalse((self.root/p.FIGURE_INPUT_NAME).exists())

    def test_issuer_refuses_existing_output_before_private_gate(self):
        from paper import prepare_complete
        write(self.root,p.FIGURE_INPUT_NAME,{})
        with patch.object(prepare_complete,'ready') as gate:
            with self.assertRaisesRegex(ValueError,'Never overwrite'):p.issue(self.paper)
            gate.assert_not_called()

    def test_crlf_owner_commitment_is_distinct_from_normalized_source_at_issue_and_consume(self):
        from paper import prepare_complete
        supervisor=self.root/'experiments/offline_release_supervisor_v2.py'
        supervisor.parent.mkdir(parents=True);supervisor.write_bytes(b'# synthetic owner\r\npass\r\n')
        raw_supervisor=p.raw_hash(supervisor);normalized=p.source_hash(supervisor)
        self.assertNotEqual(raw_supervisor,normalized)
        write(self.root,p.FREEZE_NAME,{'synthetic':'freeze'})
        write(self.root,p.PARENTS[0],{'synthetic':'recovery registration'})
        state=dict(kind='offline_release_recovery_v2',status='complete',completed_stages=list(p.STAGES),child_pid=None,
            exit_code=0,inference_calls=0,supervisor_sha256=raw_supervisor,recovery_freeze_sha256=p.source_hash(self.root/p.PARENTS[0]))
        write(self.root,p.OWNER_STATE,state)
        private=write(self.root,p.PRIVATE_FIGURE_INPUT,{'synthetic':'safe metadata only'})
        private.write_bytes(private.read_bytes().replace(b'\r\n',b'\n'))
        freeze=dict(public_artifact_sha256={'data/toy.json':'b'*64},verified_figure_input_sha256=p.raw_hash(private),
            owner_state_sha256=p.raw_hash(self.root/p.OWNER_STATE),owner_supervisor_sha256=raw_supervisor)
        lineage={p.PARENTS[0]:{'source_sha256':{'experiments/offline_release_supervisor_v2.py':normalized}}}
        bindings={'generator_sensitivity_report_sha256':'f'*64};proof={'synthetic_commitment':'a'*64}
        patches=(patch.object(p,'verify_registration',return_value=freeze),patch.object(p,'_lineage',return_value=lineage),
            patch.object(p,'_figure_receipt',return_value={}),patch.object(p,'_public_proofs',return_value=proof),
            patch.object(p,'ledger_sources',return_value=bindings),patch.object(prepare_complete,'ready',return_value=({},bindings)))
        active=[patcher.start() for patcher in patches]
        try:
            # Replacing the preserved RAW commitment with a normalized one must
            # fail before either public output is emitted.
            freeze['owner_supervisor_sha256']=normalized
            with self.assertRaisesRegex(ValueError,'Owner source identity'):p.issue(self.paper)
            self.assertFalse((self.root/p.ADMISSION_NAME).exists());self.assertFalse((self.root/p.FIGURE_INPUT_NAME).exists())
            freeze['owner_supervisor_sha256']=raw_supervisor
            self.assertTrue(p.issue(self.paper)['created'])
            receipt=p.read(self.root/p.ADMISSION_NAME)
            self.assertEqual(receipt['preserved_owner']['supervisor_sha256'],raw_supervisor)
            # Consumer has only public bytes; source/tag normalization remains
            # distinct from the preserved raw owner attestation.
            shutil_path=self.root/'runs'
            import shutil
            shutil.rmtree(shutil_path)
            supervisor.write_bytes(supervisor.read_bytes().replace(b'\r\n',b'\n'))
            self.assertEqual(p.source_hash(supervisor),normalized)
            self.assertEqual(p.verify_admission_metadata(self.paper),receipt)
            receipt['preserved_owner']['supervisor_sha256']=normalized
            write(self.root,p.ADMISSION_NAME,receipt)
            with self.assertRaisesRegex(ValueError,'owner attestation differs'):p.verify_admission_metadata(self.paper)
        finally:
            for patcher in reversed(patches):patcher.stop()

    def test_issuer_checks_safe_allowlist_before_emitting_any_output(self):
        from paper import prepare_complete
        freeze=self.registration()
        write(self.root,p.PRIVATE_FIGURE_INPUT,{'schema_version':1,'headers':{'toy':'not a credential'}})
        with patch.object(p,'verify_registration',return_value=freeze),patch.object(prepare_complete,'ready',return_value=({},{})),\
             patch.object(p,'_lineage',return_value={}),patch.object(p,'_owner_attestation',return_value={}):
            with self.assertRaisesRegex(ValueError,'Safe public figure input schema'):p.issue(self.paper)
        self.assertFalse((self.root/p.ADMISSION_NAME).exists());self.assertFalse((self.root/p.FIGURE_INPUT_NAME).exists())

    def test_malformed_assembled_admission_fails_in_memory_before_both_outputs(self):
        from paper import prepare_complete
        value=self.admission()
        raw=(self.root/p.FIGURE_INPUT_NAME).read_bytes().replace(b'\r\n',b'\n')
        (self.root/p.ADMISSION_NAME).unlink();(self.root/p.FIGURE_INPUT_NAME).unlink()
        private=self.root/p.PRIVATE_FIGURE_INPUT;private.parent.mkdir(parents=True);private.write_bytes(raw)
        owner=deepcopy(value['preserved_owner']);owner['completed_stages'].pop()
        with patch.object(prepare_complete,'ready',return_value=({},value['ledger_sources'])),\
             patch.object(p,'_owner_attestation',return_value=owner):
            with self.assertRaisesRegex(ValueError,'owner attestation differs'):p.issue(self.paper)
        self.assertFalse((self.root/p.ADMISSION_NAME).exists());self.assertFalse((self.root/p.FIGURE_INPUT_NAME).exists())

    def test_consumer_runs_frozen_hf_figures_and_sensitivity_after_metadata(self):
        from experiments import paced_resume_analysis as paced
        from analysis import ledger_complete_figures as figures
        from paper import prepare_complete
        value={'ledger_sources':{'generator_sensitivity_report_sha256':'f'*64}}
        events=[]
        with patch.object(p,'verify_admission_metadata',side_effect=lambda _:events.append('admission') or value),\
             patch.object(paced,'verify_hf',side_effect=lambda:events.append('hf')),\
             patch.object(figures,'verify_only',side_effect=lambda *a:events.append('figures')),\
             patch.object(prepare_complete,'verify_sensitivity',side_effect=lambda _:events.append('sensitivity') or 'f'*64):
            result=p.verify_public_admission(self.paper)
        self.assertEqual(events,['admission','hf','figures','sensitivity','admission'])
        self.assertTrue(result['valid']);self.assertEqual(result['inference_calls'],0)
        self.assertIn('private archive',result['native_authenticity'])

    def test_invalid_admission_prevents_every_mathematical_replay(self):
        from experiments import paced_resume_analysis as paced
        from analysis import ledger_complete_figures as figures
        from paper import prepare_complete
        with patch.object(p,'verify_admission_metadata',side_effect=ValueError('tampered admission')),\
             patch.object(paced,'verify_hf') as hf,patch.object(figures,'verify_only') as figures_check,\
             patch.object(prepare_complete,'verify_sensitivity') as sensitivity:
            with self.assertRaisesRegex(ValueError,'tampered admission'):p.verify_public_admission(self.paper)
            hf.assert_not_called();figures_check.assert_not_called();sensitivity.assert_not_called()

    def test_unsafe_paths_and_duplicate_or_nonfinite_json_rejected(self):
        for name in ('../secret','runs/private.json','C:/secret','research/../secret'):
            with self.subTest(name=name),self.assertRaises(ValueError):p.relative_file(self.root,name)
        path=self.root/'toy.json'
        for raw in ('{"a":1,"a":2}','{"a":NaN}'):
            path.write_text(raw)
            with self.assertRaises(ValueError):p.read(path)


if __name__=='__main__':unittest.main()
