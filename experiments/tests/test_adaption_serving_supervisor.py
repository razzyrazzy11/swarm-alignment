from pathlib import Path
import json,tempfile,time,unittest
from unittest.mock import patch
from experiments import adaption_serving_supervisor as w
from experiments import adaption_serving_pilot as p

class SupervisorTests(unittest.TestCase):
    def test_late_primary_defers_without_any_child_or_api(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);job=root/'job'
            with patch.object(w,'ROOT',root),patch.object(w,'JOB',job),patch.object(w,'CUTOFF',time.time()-1),patch.object(p,'verify'),patch.object(w.subprocess,'Popen') as spawn:
                w.main()
            value=json.loads((job/'state.json').read_text())
            self.assertEqual(value['status'],'deferred');self.assertFalse(value['inference_attempted']);spawn.assert_not_called()
    def test_failed_primary_blocks_pilot_without_changing_source_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);job=root/'job';original=root/p.DRIVERS[0];original.parent.mkdir(parents=True)
            original.write_text('{"status":"stopped"}');raw=original.read_bytes()
            with patch.object(w,'ROOT',root),patch.object(w,'JOB',job),patch.object(w,'CUTOFF',time.time()+10000),patch.object(p,'verify'),patch.object(w.subprocess,'Popen') as spawn:
                w.main()
            value=json.loads((job/'state.json').read_text())
            self.assertEqual(value['status'],'blocked');self.assertEqual(original.read_bytes(),raw);spawn.assert_not_called()
    def test_existing_supervisor_state_prevents_second_launch(self):
        with tempfile.TemporaryDirectory() as d:
            job=Path(d);(job/'state.json').write_text('{"status":"running"}')
            with patch.object(w,'JOB',job),patch.object(w.subprocess,'Popen') as spawn:
                with self.assertRaises(ValueError):w.main()
            spawn.assert_not_called()
    def test_metadata_failure_still_bounds_only_the_owned_child(self):
        class Child:
            killed=False
            waits=0
            def wait(self,timeout=None):
                self.waits+=1
                if self.waits==1:raise w.subprocess.TimeoutExpired('synthetic-owned-child',timeout)
                return -9
            def kill(self):self.killed=True
        child=Child();killed,code=w.drain_with_deadline(child,time.time()+1)
        self.assertTrue(killed);self.assertTrue(child.killed);self.assertEqual(code,-9);self.assertEqual(child.waits,2)
    def test_already_terminated_child_is_not_killed(self):
        class Child:
            def wait(self,timeout=None):return 0
            def kill(self):raise AssertionError('Must not kill a completed child')
        self.assertEqual(w.drain_with_deadline(Child(),time.time()+1),(False,0))
if __name__=='__main__':unittest.main()
