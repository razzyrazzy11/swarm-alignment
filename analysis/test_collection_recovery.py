from datetime import datetime,timedelta,timezone
import unittest
from analysis import collection_recovery as r


class RecoveryTests(unittest.TestCase):
    def setUp(self):self.now=datetime(2026,11,8,16,tzinfo=timezone.utc)
    def test_live_bounded_pause_owned_by_collector(self):
        v=r.decide({'status':'running'},dict(status='waiting',updated=self.now.isoformat(),episode_remaining_seconds=100),self.now,True)
        self.assertEqual(v['action'],'wait_for_registered_automatic_resume')
        self.assertFalse(v['attention']);self.assertFalse(v['inference_retry_permitted'])
    def test_dead_or_stopped_never_restarted(self):
        for driver,alive in (({'status':'stopped'},False),({'status':'running'},False)):
            v=r.decide(driver,None,self.now,alive)
            self.assertTrue(v['attention']);self.assertFalse(v['collector_restart_permitted'])
    def test_expired_pause_requires_inspection_not_retry(self):
        v=r.decide({'status':'running'},dict(status='waiting',updated=self.now.isoformat(),episode_remaining_seconds=100),self.now+timedelta(seconds=101),True)
        self.assertEqual(v['action'],'inspect_expired_recovery_budget');self.assertTrue(v['attention'])
    def test_cutoff_blocks_new_dispatch(self):
        v=r.decide({'status':'running'},None,r.CUTOFF,True)
        self.assertTrue(v['attention']);self.assertFalse(v['inference_retry_permitted'])
    def test_complete_requires_actual_termination_and_replay(self):
        v=r.decide({'status':'complete'},None,self.now,True)
        self.assertFalse(v['scientific_validation_complete'])
        self.assertEqual(v['action'],'wait_for_actual_termination_and_strict_replay')


if __name__=='__main__':unittest.main()
