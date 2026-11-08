"""Synthetic timing arithmetic and metadata validation; no inference."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from analysis import collection_timing as t


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.base=datetime(2026,11,8,12,tzinfo=timezone.utc)
        self.now=self.base+timedelta(seconds=100)
        self.attempts=[];self.terminals=[]
        for index,profile in enumerate(t.PLANNED):
            begin=30 if index==5 else 1
            self.attempts.append(dict(id=profile,profile_id=profile,started=self.base.isoformat()))
            self.terminals.append(dict(id=profile,profile_id=profile,http_status=200,latency_seconds=1,
                started_utc=(self.base+timedelta(seconds=begin)).isoformat(),
                finished_utc=(self.base+timedelta(seconds=begin+1)).isoformat()))

    def test_interval_union_clips_overlap_and_adjacency(self):
        self.assertEqual(t.union([(-5,2),(1,5),(5,6),(8,20)],0,10),[(0,6),(8,10)])
        self.assertEqual(t.idle_gaps([(-5,2),(1,5),(5,6),(8,20)],0,10),[(6,8)])
        with self.assertRaises(ValueError):t.union([(3,2)],0,10)

    def test_busy_slots_global_idle_and_barrier_scenario(self):
        value=t.summarize(self.attempts,self.terminals,self.now)
        self.assertEqual(value['global_network_union_seconds'],2)
        self.assertEqual(sum(value['provider_busy_slot_seconds'].values()),6)
        self.assertEqual(value['internal_long_idle_count'],1)
        self.assertEqual(value['typical_long_idle_gap_seconds'],28)
        waves=value['remaining_completion_wave_scenario']['upper']
        expected=value['capacity_only_conditional_seconds']+waves*28
        self.assertEqual(value['capacity_plus_barrier_scenario_seconds'],expected)
        self.assertEqual(value['scenario_with_auxiliary_margin_overhead_seconds'],
                         (expected+t.AUXILIARY_SECONDS)*1.25+t.OVERHEAD_SECONDS)
        self.assertIn('already include historical barriers',value['limitations'])

    def test_stress_formula_is_no_smaller_than_median_scenario(self):
        value=t.summarize(self.attempts,self.terminals,self.now)
        stress=value['stress_scenario']
        expected=stress['capacity_only_conditional_seconds']+value['remaining_completion_wave_scenario']['upper']*28
        self.assertEqual(stress['capacity_plus_barrier_scenario_seconds'],expected)
        self.assertEqual(stress['scenario_with_auxiliary_margin_overhead_seconds'],
                         (expected+t.AUXILIARY_SECONDS)*1.25+t.OVERHEAD_SECONDS)
        self.assertGreaterEqual(stress['scenario_with_auxiliary_margin_overhead_seconds'],
                                value['scenario_with_auxiliary_margin_overhead_seconds'])
        self.assertIn('Not a 95% forecast interval',stress['method'])

    def test_empirical_quantile_nearest_rank_boundaries(self):
        self.assertEqual(t.nearest_rank(list(range(1,21)),.95),19)
        self.assertEqual(t.nearest_rank(list(range(1,21)),1),20)
        self.assertEqual(t.nearest_rank([8],.95),8)
        for values,fraction in (([],.95),([1],0),([1],1.1),([float('nan')],.95)):
            with self.assertRaises(ValueError):t.nearest_rank(values,fraction)

    def test_missing_latency_disables_stress_scenario(self):
        self.terminals[0]['latency_seconds']=None
        value=t.summarize(self.attempts,self.terminals,self.now)
        self.assertIsNone(value['stress_scenario']['collection_finish_utc'])
        self.assertIsNone(value['stress_scenario']['shared_resource_seconds'])
        self.assertEqual(value['profiles']['g26']['missing_latency_samples'],1)

    def test_missing_timestamps_disable_idle_estimate(self):
        self.terminals[0]['finished_utc']=None
        value=t.summarize(self.attempts,self.terminals,self.now)
        self.assertFalse(value['global_idle_intervals_available'])
        self.assertIsNone(value['typical_long_idle_gap_seconds'])
        self.assertIsNone(value['capacity_plus_barrier_scenario_seconds'])
        self.assertEqual(value['profiles']['g26']['missing_network_timestamps'],1)

    def test_inflight_masks_unknown_network_activity(self):
        value=t.summarize(self.attempts,self.terminals[:-1],self.now)
        self.assertEqual(value['in_flight'],1)
        self.assertEqual(value['global_idle_seconds'],0)

    def test_wave_scenarios_keep_100_and_107_boundary_distinction(self):
        self.assertEqual((t.wave_counts(0)['lower'],t.wave_counts(0)['upper']),(0,0))
        self.assertEqual((t.wave_counts(107)['lower'],t.wave_counts(107)['upper']),(0,2))
        self.assertEqual((t.wave_counts(108)['lower'],t.wave_counts(108)['upper']),(1,2))
        self.assertEqual((t.wave_counts(1000)['lower'],t.wave_counts(1000)['upper']),(9,10))

    def test_duplicates_and_bad_chronology_fail_closed(self):
        for attempts,terminals in ((self.attempts*2,self.terminals),
                (self.attempts,self.terminals*2),(self.attempts,self.terminals+[dict(self.terminals[0],id='foreign')]),
                (self.attempts,[dict(self.terminals[0],finished_utc=self.base.isoformat())])):
            with self.assertRaises(ValueError):t.summarize(attempts,terminals,self.now)

    def test_recent_start_counts_and_first_last_latency_windows(self):
        attempts=[];terminals=[]
        for index in range(201):
            identity='synthetic'+str(index);when=self.base+timedelta(seconds=index)
            attempts.append(dict(id=identity,profile_id='g26',started=when.isoformat()))
            terminals.append(dict(id=identity,profile_id='g26',http_status=200,latency_seconds=index+1,
                started_utc=when.isoformat(),finished_utc=when.isoformat()))
        value=t.summarize(attempts,terminals,self.base+timedelta(seconds=800))
        self.assertEqual(value['profiles']['g26']['first_100_mean_seconds'],50.5)
        self.assertEqual(value['profiles']['g26']['last_100_mean_seconds'],151.5)
        self.assertEqual(value['profiles']['g26']['stress_service_seconds'],151.5)
        self.assertEqual(value['profiles']['g26']['latest_ten_minutes_starts'],1)

    def test_reader_retains_only_safe_metadata_ignores_partial_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'responses.jsonl'
            row=dict(id='synthetic',profile_id='g26',transport=dict(latency_seconds=1,http_status=200,
                diagnostics=dict(started_utc=self.base.isoformat(),finished_utc=self.now.isoformat(),
                                 private_native_id='PRIVATE')),response='ANSWER')
            path.write_bytes((json.dumps(row)+'\n{"partial":').encode())
            safe=t.rows(path,True)
            self.assertEqual(len(safe),1)
            self.assertNotIn('PRIVATE',json.dumps(safe));self.assertNotIn('ANSWER',json.dumps(safe))
            path.write_text('{"id":"a","id":"b"}\n')
            with self.assertRaises(ValueError):t.rows(path,True)


if __name__=='__main__':unittest.main()
