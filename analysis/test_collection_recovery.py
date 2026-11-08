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
    def test_rate_admission_clock_does_not_mislabel_old_internal_buffer_as_deadline(self):
        now=datetime(2026,11,9,6,tzinfo=timezone.utc)
        old=r.decide({'status':'running'},None,now,True)
        cutoff=datetime(2026,11,9,7,56,tzinfo=timezone.utc)
        new=r.decide({'status':'running'},None,now,True,cutoff=cutoff)
        self.assertEqual(old['action'],'check_cutoff_and_drain_no_new_dispatch')
        self.assertEqual(new['action'],'continue_metadata_monitoring')
        self.assertFalse(new['collector_restart_permitted']);self.assertFalse(new['inference_retry_permitted'])
        self.assertEqual(r.decide({'status':'running'},None,cutoff,True,cutoff=cutoff)['action'],'check_cutoff_and_drain_no_new_dispatch')
    def test_complete_requires_actual_termination_and_replay(self):
        v=r.decide({'status':'complete'},None,self.now,True)
        self.assertFalse(v['scientific_validation_complete'])
        self.assertEqual(v['action'],'wait_for_actual_termination_and_strict_replay')


if __name__=='__main__':unittest.main()
