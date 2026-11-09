import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import experiments
from experiments import offline_release_supervisor_v2 as s


class OfflineSupervisorTests(unittest.TestCase):
    def test_live_old_waiter_blocks_admission_before_directory_creation(self):
        from experiments import paced_resume_analysis as release
        recovery = SimpleNamespace(verify=lambda: None, require_unused_targets=lambda: None)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(s, 'ROOT', root), patch.object(experiments, 'offline_release_recovery_v2', recovery, create=True), patch.object(release, 'drivers') as drivers, patch.object(release, 'no_collectors') as locks, patch.object(release, 'terminated', side_effect=ValueError('old waiter live')) as dead:
                with self.assertRaises(ValueError): s.main()
                self.assertEqual(drivers.call_args_list[0].args, ('main',))
                self.assertEqual(drivers.call_args_list[1].args, ('hf',))
                locks.assert_called_once_with()
                dead.assert_called_once_with('runs/paced-resume-postprocess-driver/state.json', stopped=True)
            self.assertFalse((root/s.DRIVER).exists())

    def test_only_hf_command_and_figure_receipt_change(self):
        old = s.prior.processing_jobs()
        new = s.processing_jobs()
        self.assertEqual(tuple(x[0] for x in new), s.STAGES)
        self.assertEqual(new[0][1][-2:], ['experiments.offline_release_recovery_v2', 'export-hf'])
        for (stage, before), (_, after) in zip(old[1:], new[1:]):
            expected = [s.DRIVER+'/verified-public-input.json'
                        if x == 'runs/paced-resume-postprocess-driver/verified-public-input.json'
                        else x for x in before]
            self.assertEqual(after, expected, stage)

    def test_existing_directory_refused_before_admission(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/s.DRIVER).mkdir(parents=True)
            with patch.object(s, 'ROOT', root), patch.object(s, 'admission') as gate:
                with self.assertRaises(ValueError): s.main()
                gate.assert_not_called()

    def test_failed_admission_creates_no_driver(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(s, 'ROOT', root), patch.object(s, 'admission', side_effect=ValueError('blocked')):
                with self.assertRaises(ValueError): s.main()
            self.assertFalse((root/s.DRIVER).exists())

    def test_failure_retains_completed_prefix_and_never_repeats_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); freeze = root/'freeze.json'; freeze.write_text('{}')
            class Recovery: FREEZE = freeze
            seen=[]
            def child(folder, state, path, stage, command):
                seen.append(stage)
                if stage == 'main_export': raise ValueError('strict failure')
            with patch.object(s, 'ROOT', root), patch.object(s, 'admission', return_value=Recovery), patch.object(s.prior, 'child_run', side_effect=child):
                with self.assertRaises(ValueError): s.main()
            value=json.loads((root/s.DRIVER/'state.json').read_text())
            self.assertEqual(seen, ['hf_export','main_export'])
            self.assertEqual(value['completed_stages'], ['hf_export'])
            self.assertEqual(value['status'], 'stopped')
            self.assertEqual(value['kind'], 'offline_release_recovery_v2')
            self.assertFalse(value['paper_authored'])
            self.assertEqual(value['inference_calls'], 0)


if __name__ == '__main__': unittest.main()
