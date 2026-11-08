from datetime import datetime,timedelta,timezone
import unittest
from analysis import collection_headroom as h


class HeadroomTests(unittest.TestCase):
    def fixture(self):
        now=datetime(2026,11,8,15,tzinfo=timezone.utc);attempts=[];rows=[]
        for index,profile in enumerate(h.timing.PLANNED):
            for n in range(25):
                identity=profile+str(n);start=now-timedelta(seconds=800-n*30)
                attempts.append(dict(id=identity,profile_id=profile,started=start.isoformat()))
                rows.append(dict(id=identity,profile_id=profile,http_status=200,latency_seconds=1,
                    started_utc=(start+timedelta(seconds=index)).isoformat(),finished_utc=(start+timedelta(seconds=index+1)).isoformat()))
        return attempts,rows,now

    def test_all_profiles_and_extra_pause_allowance(self):
        attempts,rows,now=self.fixture();v=h.diagnose(attempts,rows,now)
        self.assertEqual(v['remaining_server500_pause_seconds'],1920)
        item=v['window_sensitivities']['15'];self.assertTrue(item['available'])
        self.assertEqual(set(item['sample_counts']),set(h.timing.PLANNED))
        self.assertEqual((h.timing.stamp(item['with_remaining_server500_at60s_utc'])-h.timing.stamp(item['conditional_finish_utc'])).total_seconds(),1920)

    def test_sparse_window_not_promoted_to_forecast(self):
        attempts,rows,now=self.fixture();v=h.diagnose(attempts,rows,now+timedelta(minutes=20))
        item=v['window_sensitivities']['15'];self.assertFalse(item['available'])
        self.assertNotIn('conditional_finish_utc',item)

    def test_failure_retained_and_censored_counts_visible(self):
        attempts,rows,now=self.fixture();rows[0]['http_status']=500;rows.pop()
        v=h.diagnose(attempts,rows,now)
        self.assertEqual(v['remaining_server500_pause_seconds'],1860)
        self.assertEqual(v['window_sensitivities']['15']['in_flight_started_in_window']['ds_off'],1)
        self.assertEqual(v['all_in_flight_by_profile']['ds_off']['count'],1)
        self.assertGreater(v['all_in_flight_by_profile']['ds_off']['oldest_age_seconds'],0)

    def test_old_censored_request_stays_visible_outside_windows(self):
        attempts,rows,now=self.fixture();rows.pop()
        v=h.diagnose(attempts,rows,now+timedelta(hours=2))
        self.assertEqual(v['window_sensitivities']['15']['in_flight_started_in_window']['ds_off'],0)
        self.assertEqual(v['all_in_flight_by_profile']['ds_off']['count'],1)
        self.assertGreater(v['all_in_flight_by_profile']['ds_off']['oldest_age_seconds'],7200)

    def test_invalid_identity_and_nan_not_silently_dropped(self):
        attempts,rows,now=self.fixture();rows[0]['latency_seconds']=float('nan')
        with self.assertRaises(ValueError):h.diagnose(attempts,rows,now)
        attempts,rows,now=self.fixture();attempts.append(attempts[0])
        with self.assertRaises(ValueError):h.diagnose(attempts,rows,now)

    def test_preserves_other_views_and_does_not_claim_probability(self):
        v=h.diagnose(*self.fixture())
        self.assertIn('last100_conditional_stress_finish',v)
        self.assertIn('not confidence intervals',v['interpretation'])
        self.assertFalse(v['independent_scientific_results_read'])


if __name__=='__main__':unittest.main()
