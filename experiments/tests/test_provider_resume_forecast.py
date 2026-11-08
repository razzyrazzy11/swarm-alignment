from datetime import datetime,timezone
from decimal import Decimal
import unittest
from experiments import provider_resume_forecast as f


class ForecastTests(unittest.TestCase):
    def args(self):
        return [dict(collection_cutoff_utc='2026-11-09T05:59:00+00:00',candidates=[dict(native_per_model=2,ollama_per_model=2,
            cost_groups=[dict(phase='readers',profile_id='ds_low',calls=100,projected_peak_cost='20')])]),
            {('readers','ds_low'):50},dict(adaption=Decimal(0),hf=Decimal(0),ollama=Decimal(2)),
            dict(adaption='100',hf='100',ollama='100'),
            dict(stress_scenario={'scenario_with_auxiliary_margin_overhead_seconds':1000}),
            datetime(2026,11,8,14,tzinfo=timezone.utc),Decimal(30)]

    def test_retained_spend_and_only_unstarted_cost(self):
        v=f.build(*self.args())
        self.assertEqual(v['projected_combined_peak_equivalent_cost']['ollama'],'12')
        self.assertEqual(v['forecast_seconds'],'3820')
        self.assertTrue(v['deadline_feasible']);self.assertTrue(v['off_peak_wallet_gate_passed'])

    def test_budget_wallet_deadline_fail_closed(self):
        args=self.args();args[2]['ollama']=Decimal(99);args[5]=datetime(2026,11,9,5,58,tzinfo=timezone.utc);args[6]=Decimal(5)
        v=f.build(*args)
        self.assertFalse(v['deadline_feasible']);self.assertFalse(v['budget_feasible']);self.assertFalse(v['off_peak_wallet_gate_passed'])

    def test_unknown_cost_group_rejected(self):
        args=self.args();args[1][('influence','g26')]=1
        with self.assertRaises(ValueError):f.build(*args)

    def test_nonfinite_timing_rejected(self):
        args=self.args();args[4]['stress_scenario']['scenario_with_auxiliary_margin_overhead_seconds']=float('nan')
        with self.assertRaises(ValueError):f.build(*args)


if __name__=='__main__':unittest.main()
