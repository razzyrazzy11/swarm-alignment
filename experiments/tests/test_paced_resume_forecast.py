from datetime import datetime,timezone
from decimal import Decimal
import unittest
from experiments import paced_resume_forecast as f


class ForecastTests(unittest.TestCase):
    def args(self):
        return [dict(collection_cutoff_utc='2026-11-09T05:59:00+00:00',candidates=[dict(native_per_model=2,ollama_per_model=2,
            cost_groups=[dict(phase='readers',profile_id='ds_low',calls=100,projected_peak_cost='20')])]),
            {('readers','ds_low'):50},dict(adaption=Decimal(0),hf=Decimal(0),ollama=Decimal(2)),
            dict(adaption='100',hf='100',ollama='100'),
            dict(stress_scenario={'scenario_with_auxiliary_margin_overhead_seconds':1000,'capacity_only_conditional_seconds':100}),
            datetime(2026,11,8,14,tzinfo=timezone.utc),Decimal(30)]

    def test_retained_spend_and_only_unstarted_cost(self):
        v=f.build(*self.args())
        self.assertEqual(v['projected_combined_peak_equivalent_cost']['ollama'],'12')
        self.assertEqual(Decimal(v['forecast_seconds']),Decimal(4720))
        self.assertTrue(v['deadline_feasible']);self.assertTrue(v['off_peak_wallet_gate_passed'])

    def test_budget_wallet_deadline_fail_closed(self):
        args=self.args();args[2]['ollama']=Decimal(99);args[5]=datetime(2026,11,9,7,55,tzinfo=timezone.utc);args[6]=Decimal(5)
        v=f.build(*args)
        self.assertFalse(v['deadline_feasible']);self.assertFalse(v['budget_feasible']);self.assertFalse(v['off_peak_wallet_gate_passed'])

    def test_unknown_cost_group_rejected(self):
        args=self.args();args[1][('influence','g26')]=1
        with self.assertRaises(ValueError):f.build(*args)

    def test_nonfinite_timing_rejected(self):
        args=self.args();args[4]['stress_scenario']['scenario_with_auxiliary_margin_overhead_seconds']=float('nan')
        with self.assertRaises(ValueError):f.build(*args)

    def test_new_operational_cutoff_preserves_old_anchor_and_paper_reserve(self):
        args=self.args();args[5]=datetime(2026,11,9,6,tzinfo=timezone.utc)
        v=f.build(*args)
        self.assertEqual(args[0]['collection_cutoff_utc'],'2026-11-09T05:59:00+00:00')
        self.assertEqual(v['original_collection_cutoff_utc'],args[0]['collection_cutoff_utc'])
        self.assertEqual(v['collection_cutoff_utc'],'2026-11-09T07:56:00+00:00')
        self.assertEqual(v['latest_dispatch_to_target_drain_seconds'],240)
        self.assertEqual(v['validation_paper_reserve_seconds'],14340)
        self.assertEqual(v['submission_deadline_utc'],'2026-11-09T11:59:00+00:00')
        self.assertTrue(v['deadline_feasible'])

    def test_native_pacing_increases_resource_max_when_native_is_critical(self):
        args=self.args();args[0]['candidates'][0]['cost_groups'].append(dict(phase='readers',profile_id='g26',calls=100,projected_peak_cost='1'))
        args[1][('readers','g26')]=100
        v=f.build(*args)
        self.assertEqual(v['reader_resource_max_after_pacing_seconds'],'320.0')
        self.assertEqual(Decimal(v['pacing_increment_with_headroom_seconds']),Decimal(275))
        self.assertEqual(Decimal(v['forecast_seconds']),Decimal('4995'))

    def test_calibration_pacing_is_not_hidden_in_old80second_allowance(self):
        args=self.args()
        for p in ('g26','g31'):
            args[0]['candidates'][0]['cost_groups'].append(dict(phase='calibration',profile_id=p,calls=40,projected_peak_cost='1'))
            args[1][('calibration',p)]=40
        v=f.build(*args)
        self.assertEqual(Decimal(v['paced_auxiliary_allowance_seconds']['calibration']),Decimal(128))
        self.assertEqual(Decimal(v['pacing_increment_with_headroom_seconds']),Decimal(60))
        self.assertEqual(Decimal(v['forecast_seconds']),Decimal(4780))


if __name__=='__main__':unittest.main()
