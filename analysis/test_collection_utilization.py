"""Synthetic interval sweeps, clipping and censoring; no empirical outcomes."""
from datetime import datetime,timedelta,timezone
import json,unittest
from analysis import collection_utilization as u

class UtilizationTests(unittest.TestCase):
    def setUp(self):self.base=datetime(2026,11,8,12,tzinfo=timezone.utc)
    def time(self,seconds):return self.base+timedelta(seconds=seconds)
    def test_sweep_clips_boundaries_and_integrates_slots(self):
        value=u.sweep([(self.time(-5),self.time(5)),(self.time(5),self.time(15))],self.time(0),self.time(10),2)
        self.assertEqual(value['slot_busy_seconds'],10)
        self.assertEqual(value['mean_active'],1)
        self.assertEqual(value['time_at_active_0_1_2_seconds'],{'0':0,'1':10,'2':0})
        self.assertEqual(value['intervals_extending_before_window'],1)
        self.assertEqual(value['intervals_extending_after_window'],1)
        self.assertEqual(value['maximum_observed_active'],1)
    def test_sweep_cap_overlap_is_not_hidden_in_mean(self):
        value=u.sweep([(self.time(0),self.time(10)),(self.time(2),self.time(8)),(self.time(4),self.time(6))],self.time(0),self.time(10),2)
        self.assertEqual(value['observed_cap_violation_seconds'],2)
        self.assertEqual(value['maximum_observed_active'],3)
        self.assertEqual(value['slot_busy_seconds'],18)
    def fixture(self):
        attempts=[dict(id='a',profile_id='ds_low',started=self.time(0).isoformat()),dict(id='b',profile_id='g26',started=self.time(0).isoformat())]
        rows=[dict(id='a',profile_id='ds_low',latency_seconds=10,http_status=200,started_utc=self.time(0).isoformat(),finished_utc=self.time(10).isoformat()),
              dict(id='b',profile_id='g26',latency_seconds=20,http_status=200,started_utc=self.time(10).isoformat(),finished_utc=self.time(30).isoformat())]
        return attempts,rows
    def test_ollama_idle_other_busy_is_descriptive_with_separate_global_idle(self):
        attempts,rows=self.fixture();value=u.summarize(attempts,rows,self.time(60))['windows']['15']
        self.assertEqual(value['ollama_idle_while_other_provider_busy_completed_intervals_only']['seconds'],20)
        self.assertEqual(value['global_reader_idle_completed_intervals_only']['total_seconds'],30)
        self.assertEqual(value['profiles']['ds_low']['mean_full_network_service_seconds'],10)
        self.assertEqual(value['completed_service_profile_mix']['ds_low'],.5)
    def test_right_censoring_is_unknown_not_observed_busy(self):
        attempts,rows=self.fixture();attempts.append(dict(id='c',profile_id='ds_low',started=self.time(5).isoformat()))
        value=u.summarize(attempts,rows,self.time(60));window=value['windows']['15']
        self.assertEqual(value['right_censored_inflight_total'],1)
        self.assertEqual(window['providers']['ollama']['slot_busy_seconds'],10)
        self.assertEqual(window['profiles']['ds_low']['oldest_inflight_age_seconds'],55)
        self.assertEqual(window['global_reader_idle_excluding_unknown_dispatch_windows']['total_seconds'],0)
        self.assertEqual(window['ollama_idle_while_other_provider_busy_excluding_unknown_ollama_windows']['seconds'],0)
    def test_completed_call_missing_timing_masks_unknown_without_fabricated_slots(self):
        attempts,rows=self.fixture();rows[0].pop('started_utc')
        value=u.summarize(attempts,rows,self.time(60))
        self.assertEqual(value['missing_completed_network_timestamps_total'],1)
        self.assertEqual(value['right_censored_inflight_total'],0)
        self.assertEqual(value['windows']['15']['providers']['ollama']['slot_busy_seconds'],0)
    def test_window_edge_uses_clipped_slots_but_full_service_duration(self):
        attempts,rows=self.fixture();now=self.time(920)
        # Last15min starts at t20: the g26 interval straddles the left edge.
        value=u.summarize(attempts,rows,now)['windows']['15']
        profile=value['profiles']['g26']
        self.assertEqual(profile['slot_busy_seconds'],10)
        self.assertEqual(profile['mean_full_network_service_seconds'],20)
        self.assertEqual(profile['intervals_extending_before_window'],1)
    def test_duplicate_or_future_intervals_fail_closed(self):
        attempts,rows=self.fixture()
        with self.assertRaises(ValueError):u.summarize(attempts*2,rows,self.time(60))
        with self.assertRaises(ValueError):u.summarize(attempts,rows*2,self.time(60))
        rows[0]['finished_utc']=self.time(61).isoformat()
        with self.assertRaises(ValueError):u.summarize(attempts,rows,self.time(60))
    def test_no_id_output_eta_or_admission_clearance(self):
        attempts,rows=self.fixture();attempts[0]['id']='PRIVATE_NATIVE_LIKE_ID';rows[0]['id']='PRIVATE_NATIVE_LIKE_ID'
        value=u.summarize(attempts,rows,self.time(60));text=json.dumps(value)
        self.assertNotIn('PRIVATE_NATIVE_LIKE_ID',text)
        self.assertFalse(value['completion_eta_computed']);self.assertFalse(value['admission_clearance'])
        self.assertFalse(value['scientific_outcomes_read'])
    def test_adaption_fraction_uses_provider_guard_not_reachable_reader_throughput(self):
        attempts,rows=self.fixture();value=u.summarize(attempts,rows,self.time(60))['windows']['15']['providers']
        native=value['adaption']
        self.assertEqual(native['registered_capacity'],8)
        self.assertEqual(native['reader_model_constraints']['reader_model_guard_ceiling'],4)
        self.assertIn('provider concurrency guard',native['denominator_scope'])
        self.assertIn('not achievable',native['denominator_scope'])
        self.assertFalse(native['remaining_job_eligibility_inferred'])
        self.assertEqual(value['ollama']['registered_capacity'],2)
        self.assertEqual(value['hf']['registered_capacity'],2)
    def test_linear_difference_handles_disjoint_and_spanning_own_intervals(self):
        own=[(self.time(2),self.time(8)),(self.time(12),self.time(30))]
        other=[(self.time(0),self.time(5)),(self.time(7),self.time(15)),(self.time(20),self.time(40))]
        value=u.idle_while_other_busy(own,other,[],self.time(0),self.time(40))
        self.assertEqual(value['seconds'],2+4+10)

if __name__=='__main__':unittest.main()
