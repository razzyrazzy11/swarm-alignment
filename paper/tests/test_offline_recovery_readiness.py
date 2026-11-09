"""Synthetic admission/provenance guards; no empirical reports or answers read."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
import experiments
from experiments import paced_resume_analysis as paced
from analysis import ledger_complete_figures as figures
from paper import completion_handoff as handoff
from paper import complete_report_contract as contract
from paper import prepare_complete as prep
from test_complete_report_contract import fixture


class OfflineRecoveryReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.paper = self.root / 'paper'
        self.paper.mkdir()
        research = self.root / 'research'
        research.mkdir()
        for name in ('offline-release-recovery-v1-freeze.json',
                     'swarm-ledger-paced-v1-freeze.json',
                     'swarm-ledger-resume-v3-freeze.json',
                     'hf-offline-release-recovery-proof.json'):
            (research/name).write_text('{"fixture":true}\n', encoding='utf-8')
        source = self.root/'experiments/offline_release_supervisor.py'
        source.parent.mkdir()
        source.write_text('# Synthetic source only\n', encoding='utf-8')
        self.state_path = self.root/'runs/offline-release-recovery-driver/state.json'
        self.state_path.parent.mkdir(parents=True)
        self.state = dict(status='complete', completed_stages=list(prep.STAGES),
                          child_pid=None, exit_code=0, inference_calls=0,
                          paper_authored=False, visual_qa_complete=False,
                          kind='offline_release_recovery',
                          supervisor_sha256=self.sha(source),
                          recovery_freeze_sha256=self.sha(research/'offline-release-recovery-v1-freeze.json'))
        self.save()
        self.recovery = SimpleNamespace(verify=Mock(), verify_projection=Mock(), verify_hf=Mock())

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def save(self):
        self.state_path.write_text(json.dumps(self.state), encoding='utf-8')

    @contextmanager
    def admission(self):
        with ExitStack() as stack:
            module=getattr(self,'recovery_module','offline_release_recovery')
            stack.enter_context(patch.dict(sys.modules, {'experiments.'+module: self.recovery}))
            stack.enter_context(patch.object(experiments, module, self.recovery, create=True))
            self.terminated = stack.enter_context(patch.object(paced, 'terminated'))
            self.drivers = stack.enter_context(patch.object(paced, 'drivers'))
            stack.enter_context(patch.object(paced, 'verify_hf', side_effect=AssertionError('Use registered companion gate')))
            self.load = stack.enter_context(patch.object(prep.contract, 'load_completed', return_value=({'synthetic': True}, {})))
            self.figure = stack.enter_context(patch.object(figures, 'verify_only'))
            stack.enter_context(patch.object(prep, 'verify_sensitivity', return_value='synthetic-sensitivity'))
            yield

    def enable_v2(self):
        self.recovery_module='offline_release_recovery_v2'
        freeze=self.root/'research/offline-release-recovery-v2-freeze.json'
        freeze.write_text('{"synthetic_v2":true}\n',encoding='utf-8')
        (self.root/'research/hf-offline-release-recovery-v2-proof.json').write_text('{"synthetic_v2":true}\n',encoding='utf-8')
        source=self.root/'experiments/offline_release_supervisor_v2.py'
        source.write_text('# Synthetic V2 source only\n',encoding='utf-8')
        self.state_path=self.root/'runs/offline-release-recovery-v2-driver/state.json'
        self.state_path.parent.mkdir(parents=True)
        self.state.update(kind='offline_release_recovery_v2',supervisor_sha256=self.sha(source),
                          recovery_freeze_sha256=self.sha(freeze))
        self.save()

    def test_v2_marker_rejects_complete_v1_waiter_instead_of_falling_back(self):
        self.enable_v2()
        self.state_path.unlink()
        with self.admission():
            with self.assertRaisesRegex(ValueError,'Actual complete postprocessor'):
                prep.ready(self.paper)
            self.load.assert_not_called()

    def test_v2_admits_only_new_success_and_both_failed_predecessors_dead(self):
        self.enable_v2()
        with self.admission():
            prep.ready(self.paper)
            self.assertEqual([(c.args,c.kwargs) for c in self.terminated.call_args_list],[
                (('runs/paced-resume-postprocess-driver/state.json',),{'stopped':True}),
                (('runs/offline-release-recovery-driver/state.json',),{'stopped':True}),
                (('runs/offline-release-recovery-v2-driver/state.json',),{'complete':True})])
            self.assertEqual(self.figure.call_args.args[1],self.root/'runs/offline-release-recovery-v2-driver/verified-public-input.json')
            self.recovery.verify_hf.assert_called_once_with()
        with self.admission():
            def old_v1_not_dead(path,**kwargs):
                if path=='runs/offline-release-recovery-driver/state.json':
                    raise ValueError('Synthetic V1 owner still live')
            self.terminated.side_effect=old_v1_not_dead
            with self.assertRaisesRegex(ValueError,'V1 owner still live'):
                prep.ready(self.paper)
            self.load.assert_not_called()

    def test_v2_rejects_v1_identity_even_when_all_stages_complete(self):
        self.enable_v2()
        for key,value in [('kind','offline_release_recovery'),
                          ('supervisor_sha256',self.sha(self.root/'experiments/offline_release_supervisor.py')),
                          ('recovery_freeze_sha256',self.sha(self.root/'research/offline-release-recovery-v1-freeze.json')),
                          ('completed_stages',list(prep.STAGES[:-1]))]:
            with self.subTest(key=key):
                baseline=deepcopy(self.state)
                self.state[key]=value
                self.save()
                with self.admission():
                    with self.assertRaises(ValueError):prep.ready(self.paper)
                    self.load.assert_not_called()
                self.state=baseline
                self.save()

    def test_v2_handoff_prioritizes_new_adapter_and_receipt_over_v1(self):
        self.enable_v2()
        jobs=[(stage,['python','-m','synthetic']) for stage in handoff.STAGES]
        jobs[0]=('hf_export',['python','-m','experiments.offline_release_recovery_v2','export-hf'])
        jobs[1]=('main_export',['python','-m','experiments.paced_resume_analysis','export-main'])
        jobs[3]=('figure_input',['python','runs/offline-release-recovery-v2-driver/verified-public-input.json'])
        modules={'experiments.paced_resume_analysis':SimpleNamespace(verify=Mock(),verify_main=lambda output,replay=True:None),
                 'experiments.offline_release_recovery_v2':self.recovery,
                 'experiments.offline_release_supervisor_v2':SimpleNamespace(STAGES=handoff.STAGES,processing_jobs=lambda:jobs),
                 'paper.prepare_complete':prep}
        with patch.object(handoff.importlib,'import_module',side_effect=lambda name:modules[name]):
            result=handoff.pipeline(self.root)
            self.assertEqual(result['offline_recovery_registration'],'research/offline-release-recovery-v2-freeze.json')
            self.assertEqual(result['offline_hf_projection_proof'],'research/hf-offline-release-recovery-v2-proof.json')
            self.assertEqual(result['postprocessor_state'],'runs/offline-release-recovery-v2-driver/state.json')
            jobs[0]=('hf_export',['python','-m','experiments.offline_release_recovery','export-hf'])
            with self.assertRaisesRegex(ValueError,'HF admission command differs'):handoff.pipeline(self.root)

    def test_old_waiter_cannot_replace_missing_new_successful_waiter(self):
        self.state_path.unlink()
        old = self.root/'runs/paced-resume-postprocess-driver/state.json'
        old.parent.mkdir(parents=True)
        old.write_text(json.dumps(dict(status='complete', completed_stages=list(prep.STAGES), child_pid=None)))
        with self.admission():
            with self.assertRaisesRegex(ValueError, 'Actual complete postprocessor'):
                prep.ready(self.paper)
            self.load.assert_not_called()

    def test_bad_stage_child_or_identity_blocks_before_aggregate(self):
        cases = [('completed_stages', list(prep.STAGES[:-1])),
                 ('completed_stages', list(reversed(prep.STAGES))), ('child_pid', 123),
                 ('kind', 'paced'), ('exit_code', 1), ('inference_calls', 1),
                 ('inference_calls', False), ('paper_authored', True),
                 ('visual_qa_complete', True), ('supervisor_sha256', 'wrong'),
                 ('recovery_freeze_sha256', 'wrong')]
        baseline = deepcopy(self.state)
        for key, value in cases:
            with self.subTest(field=key, value=value):
                self.state = deepcopy(baseline)
                self.state[key] = value
                self.save()
                with self.admission():
                    with self.assertRaises(ValueError):
                        prep.ready(self.paper)
                    self.load.assert_not_called()

    def test_old_failure_must_be_stopped_and_dead_before_new_admission(self):
        with self.admission():
            self.terminated.side_effect = ValueError('Old waiter not stopped/dead')
            with self.assertRaisesRegex(ValueError, 'not stopped/dead'):
                prep.ready(self.paper)
            self.terminated.assert_called_once_with('runs/paced-resume-postprocess-driver/state.json', stopped=True)
            self.load.assert_not_called()

    def test_complete_recovery_keeps_all_replays_and_new_receipt(self):
        with self.admission():
            report, bindings = prep.ready(self.paper)
            self.load.assert_called_once_with(self.paper, replay=True)
            self.assertEqual(self.terminated.call_args_list[0].kwargs, {'stopped': True})
            self.assertEqual(self.terminated.call_args_list[1].args, ('runs/offline-release-recovery-driver/state.json',))
            self.assertEqual(self.terminated.call_args_list[1].kwargs, {'complete': True})
            self.assertEqual([call.args for call in self.drivers.call_args_list], [('main',), ('hf',)])
            self.recovery.verify.assert_called_once_with()
            self.recovery.verify_projection.assert_called_once_with(replay=False)
            self.recovery.verify_hf.assert_called_once_with()
            self.assertEqual(self.figure.call_args.args[1], self.root/'runs/offline-release-recovery-driver/verified-public-input.json')
            self.assertEqual(bindings['generator_sensitivity_report_sha256'], 'synthetic-sensitivity')
            self.assertEqual(report, {'synthetic': True})

    def test_changed_state_during_termination_proof_blocks_aggregate(self):
        with self.admission():
            def changed(*args, **kwargs):
                if kwargs.get('complete'):
                    self.state['inference_calls'] = 1
                    self.save()
            self.terminated.side_effect = changed
            with self.assertRaisesRegex(ValueError, 'state changed'):
                prep.ready(self.paper)
            self.load.assert_not_called()

    def test_handoff_uses_registered_hf_command_and_fresh_receipt(self):
        jobs = [(stage, ['python', '-m', 'synthetic']) for stage in handoff.STAGES]
        jobs[0] = ('hf_export', ['python', '-m', 'experiments.offline_release_recovery', 'export-hf'])
        jobs[1] = ('main_export', ['python', '-m', 'experiments.paced_resume_analysis', 'export-main'])
        jobs[3] = ('figure_input', ['python', 'runs/offline-release-recovery-driver/verified-public-input.json'])
        modules = {'experiments.paced_resume_analysis': SimpleNamespace(verify=Mock(), verify_main=lambda output, replay=True: None),
                   'experiments.offline_release_recovery': self.recovery,
                   'experiments.offline_release_supervisor': SimpleNamespace(STAGES=handoff.STAGES, processing_jobs=lambda: jobs),
                   'paper.prepare_complete': prep}
        with patch.object(handoff.importlib, 'import_module', side_effect=lambda name: modules[name]):
            result = handoff.pipeline(self.root)
            self.assertEqual(result['postprocessor_state'], 'runs/offline-release-recovery-driver/state.json')
            self.assertEqual(result['figure_receipt'], 'runs/offline-release-recovery-driver/verified-public-input.json')
            self.assertEqual(result['main_proof'], 'research/swarm-ledger-paced-resume-release-proof.json')
            self.assertEqual(result['hf_analysis_module'], 'experiments.offline_release_recovery')
            jobs[0] = ('hf_export', ['python', '-m', 'experiments.paced_resume_analysis', 'export-hf'])
            with self.assertRaisesRegex(ValueError, 'HF admission command differs'):
                handoff.pipeline(self.root)

    def test_public_manuscript_bindings_include_recovery_freeze_and_proof(self):
        from experiments import swarm_ledger_complete_analysis as analysis
        report, _ = fixture()
        public = self.root/'data/swarm-ledger-v1-public'
        public.mkdir(parents=True)
        for name in ('manifest.json', 'report.json', 'registration.json', 'operational-registration.json'):
            (public/name).write_text('{"synthetic":true}\n', encoding='utf-8')
        manifest = dict(registration_sha256='synthetic-science', operational_registration_sha256='synthetic-operation')
        module=getattr(self,'recovery_module','offline_release_recovery')
        with patch.dict(sys.modules, {'experiments.'+module: self.recovery}), \
                patch.object(experiments, module, self.recovery, create=True), \
                patch.object(paced, 'verify_main'), patch.object(analysis, 'verify_public'), \
                patch.object(analysis, 'load_public_artifacts', return_value=(None, report, manifest)):
            _, bindings = contract.load_completed(self.paper, replay=True)
        for name in ('offline-release-recovery-v1-freeze.json', 'hf-offline-release-recovery-proof.json'):
            self.assertEqual(bindings[name], self.sha(self.root/'research'/name))
        if module.endswith('_v2'):
            for name in ('offline-release-recovery-v2-freeze.json','hf-offline-release-recovery-v2-proof.json'):
                self.assertEqual(bindings[name],self.sha(self.root/'research'/name))
        self.recovery.verify.assert_called_once_with()
        self.recovery.verify_projection.assert_called_once_with(replay=False)

    def test_v2_manuscript_binds_new_proof_and_registration(self):
        self.enable_v2()
        self.test_public_manuscript_bindings_include_recovery_freeze_and_proof()


if __name__ == '__main__':
    unittest.main()
