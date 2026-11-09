from datetime import datetime,timedelta,timezone
import unittest
from analysis import collection_recovery as r


class RecoveryTests(unittest.TestCase):
    def setUp(self):self.now=datetime(2026,11,8,16,tzinfo=timezone.utc)
    def test_live_bounded_pause_owned_by_collector(self):
        v=r.decide({'status':'running'},dict(status='waiting',updated=self.now.isoformat(),episode_remaining_seconds=100),self.now,True)
        self.assertEqual(v['action'],'wait_for_registered_automatic_resume')
        self.assertFalse(v['attention']);self.assertFalse(v['inference_retry_permitted'])
    def test_provider_hold_is_not_reported_as_global_stall(self):
        value=r.decide({'status':'running'},dict(status='waiting',provider='adaption',failure_class='adaption_rate_limit',updated=self.now.isoformat(),episode_remaining_seconds=100,next_dispatch_at='later'),self.now,True)
        self.assertFalse(value['attention']);self.assertEqual(value['provider'],'adaption')
        self.assertIn('other providers may continue',value['scope'])
        self.assertFalse(value['inference_retry_permitted'])
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

    def startup_fixture(self):
        created=(self.now-timedelta(minutes=10)).isoformat()
        return dict(pid=123,created_utc=created,launched_utc=created,kind='collect',source_tag='swarm-ledger-paced-v1'),dict(pid=123,created_utc=created)
    def test_exact_live_startup_identity_gets_bounded_wait_without_permission(self):
        manifest,observed=self.startup_fixture();value=r.startup_decision(manifest,observed,self.now)
        self.assertEqual(value['action'],'wait_for_registered_startup');self.assertFalse(value['attention'])
        self.assertFalse(value['collector_launch_permitted']);self.assertFalse(value['collector_restart_permitted'])
        self.assertFalse(value['inference_retry_permitted']);self.assertFalse(value['scientific_validation_complete'])
    def test_missing_dead_or_mismatching_startup_identity_requires_attention(self):
        manifest,observed=self.startup_fixture()
        for supplied,actual in ((None,None),(manifest,None),(manifest,dict(observed,pid=124)),
                                (manifest,dict(observed,created_utc=self.now.isoformat())),
                                (dict(manifest,source_tag='old'),observed)):
            value=r.startup_decision(supplied,actual,self.now)
            self.assertTrue(value['attention']);self.assertFalse(value['collector_launch_permitted'])
    def test_expired_startup_or_cutoff_requires_attention_without_restart(self):
        manifest,observed=self.startup_fixture()
        value=r.startup_decision(manifest,observed,self.now+timedelta(minutes=20))
        self.assertEqual(value['action'],'inspect_unexplained_30_minute_startup');self.assertTrue(value['attention'])
        value=r.startup_decision(manifest,observed,self.now,cutoff=self.now)
        self.assertTrue(value['attention']);self.assertFalse(value['collector_restart_permitted'])
    def test_native_creation_identity_retains_seventh_fractional_digit(self):
        manifest,observed=self.startup_fixture()
        manifest['created_utc']='2026-11-08T15:50:00.1234567Z'
        observed['created_utc']='2026-11-08T15:50:00.1234568Z'
        self.assertTrue(r.startup_decision(manifest,observed,self.now)['attention'])


if __name__=='__main__':unittest.main()
