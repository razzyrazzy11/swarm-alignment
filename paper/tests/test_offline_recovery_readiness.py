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
            stack.enter_context(patch.dict(sys.modules, {'experiments.offline_release_recovery': self.recovery}))
            stack.enter_context(patch.object(experiments, 'offline_release_recovery', self.recovery, create=True))
            self.terminated = stack.enter_context(patch.object(paced, 'terminated'))
            self.drivers = stack.enter_context(patch.object(paced, 'drivers'))
            stack.enter_context(patch.object(paced, 'verify_hf', side_effect=AssertionError('Use registered companion gate')))
            self.load = stack.enter_context(patch.object(prep.contract, 'load_completed', return_value=({'synthetic': True}, {})))
            self.figure = stack.enter_context(patch.object(figures, 'verify_only'))
            stack.enter_context(patch.object(prep, 'verify_sensitivity', return_value='synthetic-sensitivity'))
            yield

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
        with patch.dict(sys.modules, {'experiments.offline_release_recovery': self.recovery}), \
                patch.object(experiments, 'offline_release_recovery', self.recovery, create=True), \
                patch.object(paced, 'verify_main'), patch.object(analysis, 'verify_public'), \
                patch.object(analysis, 'load_public_artifacts', return_value=(None, report, manifest)):
            _, bindings = contract.load_completed(self.paper, replay=True)
        for name in ('offline-release-recovery-v1-freeze.json', 'hf-offline-release-recovery-proof.json'):
            self.assertEqual(bindings[name], self.sha(self.root/'research'/name))
        self.recovery.verify.assert_called_once_with()
        self.recovery.verify_projection.assert_called_once_with(replay=False)


if __name__ == '__main__':
    unittest.main()
