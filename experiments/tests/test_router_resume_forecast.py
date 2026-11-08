from datetime import datetime,timezone
from decimal import Decimal
import unittest
from experiments import router_resume_forecast as f

class ForecastTests(unittest.TestCase):
    def original(self):return {'collection_cutoff_utc':'2026-11-09T05:59:00+00:00','candidates':[dict(native_per_model=2,ollama_per_model=2,
        cost_groups=[dict(phase='reporter',profile_id='g26',projected_peak_cost='1'),dict(phase='readers',profile_id='ds_low',projected_peak_cost='20'),dict(phase='principal',profile_id='g26',projected_peak_cost='99')],
        phase_bounds=[dict(phase='reporter',bottleneck_seconds='100'),dict(phase='readers',bottleneck_seconds='200')])]}
    def test_whole_reporter_bound_margin_and_offpeak_floor(self):
        v=f.build(self.original(),dict(adaption=Decimal(1),hf=Decimal(0),ollama=Decimal(0)),datetime(2026,11,8,tzinfo=timezone.utc),Decimal('16'))
        self.assertEqual(v['forecast_seconds'],'3675.00');self.assertEqual(v['projected_remaining_peak_equivalent_cost']['adaption'],'1')
        self.assertTrue(v['off_peak_wallet_gate_passed']);self.assertTrue(v['deadline_feasible'])
    def test_deadline_and_wallet_fail_closed(self):
        v=f.build(self.original(),dict(adaption=Decimal(1),hf=Decimal(0),ollama=Decimal(0)),datetime(2026,11,9,5,58,tzinfo=timezone.utc),Decimal('15'))
        self.assertFalse(v['deadline_feasible']);self.assertFalse(v['off_peak_wallet_gate_passed'])
    def test_existing_spend_not_reset(self):
        v=f.build(self.original(),dict(adaption=Decimal(821),hf=Decimal(0),ollama=Decimal(0)),datetime(2026,11,8,tzinfo=timezone.utc),Decimal(100))
        self.assertFalse(v['budget_feasible'])
if __name__=='__main__':unittest.main()
