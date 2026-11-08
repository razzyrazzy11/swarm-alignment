import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from experiments import server_resume_supervisor as sup


class SupervisorTests(unittest.TestCase):
    def test_processing_order_and_new_receipt(self):
        jobs=sup.processing_jobs()
        self.assertEqual(tuple(k for k,_ in jobs),sup.STAGES)
        self.assertIn('runs/server-resume-postprocess-driver/verified-public-input.json',jobs[3][1])
        self.assertIn('experiments.server_resume_analysis',jobs[0][1])

    def test_failed_child_terminal_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(sup.subprocess,'Popen') as popen:
            folder=Path(tmp);state={};path=folder/'state.json'
            popen.return_value=Mock(pid=123,wait=Mock(return_value=1))
            with self.assertRaises(ValueError):sup.child_run(folder,state,path,'readers',['fake'])
            self.assertEqual(popen.call_count,1)
            self.assertEqual(state['status'],'stopped')
            self.assertIsNone(state['child_pid'])
            self.assertEqual(json.loads(path.read_text())['reason'],'phase_failed_no_retry')

    def test_existing_logs_block_duplicate_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(sup.subprocess,'Popen') as popen:
            folder=Path(tmp);(folder/'readers.stdout.log').write_text('preserve')
            with self.assertRaises(FileExistsError):sup.child_run(folder,{},folder/'state.json','readers',['fake'])
            popen.assert_not_called()

    def test_complete_state_waits_for_actual_exit(self):
        from experiments import server_resume_analysis as release
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'runs/server-resume-postprocess-driver';folder.mkdir(parents=True)
            actual=root/'runs/swarm-ledger-resume-v2-driver';actual.mkdir()
            (actual/'state.json').write_text(json.dumps({'status':'complete'}))
            with patch.object(sup,'ROOT',root),patch.object(release,'drivers',side_effect=[ValueError('still live'),{},{}]) as drivers,patch.object(release,'no_collectors'),patch.object(sup.time,'sleep'),patch.object(sup,'processing_jobs',return_value=[]):
                state={'completed_stages':[]}
                sup.postprocess(folder,state,folder/'state.json')
                self.assertEqual(drivers.call_count,3)

    def test_save_failure_drains_owned_child(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(sup.subprocess,'Popen') as popen,patch.object(sup,'save',side_effect=OSError('disk')):
            child=Mock(pid=123,wait=Mock(return_value=0));popen.return_value=child
            folder=Path(tmp)
            with self.assertRaises(OSError):sup.child_run(folder,{},folder/'state.json','readers',['fake'])
            child.wait.assert_called_once()


if __name__=='__main__':unittest.main()
