"""Synthetic engineering metadata only; no API, credentials or model answers."""
from copy import deepcopy
from decimal import Decimal
import json
import unittest
from experiments import swarm_ledger_complete_forecast as f
from experiments.tests.test_swarm_ledger_forecast_v2 import fixture as historical_fixture, sync_classes


def fixture():
    inputs,_=historical_fixture()
    c=inputs['science_config'];c['reader_profiles']=['g26','g31','hf_text','hf_schema','ds_off','ds_low']
    c['auxiliary_reader_profiles']=['g26','g31','ds_low'];c['combined_caps']['ollama']='100'
    c['phase_caps']['main']['ollama']='99.70'
    inputs['native_candidates']=[2]
    inputs['pilot_cost_metadata']={'estimated_cost_by_provider':{'adaption':'.8143088','hf':'0','ollama':'0'},
      'baselines':[{'path':name,'sha256':str(i)*64,'registration_tag':'synthetic-'+name,'registration_sha256':str(i+2)*64} for i,name in enumerate(('v1','v2'),1)]}
    inputs['pilot_metadata_sha256']=f.s.digest(inputs['pilot_cost_metadata'])
    return inputs


class CompleteForecastTests(unittest.TestCase):
    def setUp(self):self.inputs=fixture()
    def build(self,wallet=100):return f.build(self.inputs,'2026-11-07T00:00:00+00:00',Decimal(str(wallet)))
    def test_complete_counts_and_single_unpiloted_fixed_configuration(self):
        out=self.build();self.assertEqual(out['workload'],dict(actor_calls_including_influence=9200,reader_calls_including_calibration=54000,total_calls=63200,scientific_main_blocks=640))
        self.assertEqual(len(out['candidates']),1);self.assertFalse(out['capacity_pilot_extrapolation_used'])
        self.assertEqual(out['dispatch_limits'],dict(native_per_model=2,native_provider=8,global_cap=8,hf=2,ollama=2,native_dispatch_interval_seconds=1))
        self.assertEqual(len(out['development_serving_metadata']),28)
        counts={p:sum(g['calls'] for g in out['cost_groups'] if g['profile_id']==p and g['phase'] not in f.ACTOR_COUNTS) for p in self.inputs['science_config']['reader_profiles']}
        self.assertEqual(counts,dict(g26=12840,g31=12840,hf_text=5160,hf_schema=5160,ds_off=5160,ds_low=12840))
    def test_unused_failed_reader_metadata_archived_but_not_extrapolated(self):
        before=self.build()['candidates']
        for g in self.inputs['development_groups']:
            if g['profile_id'] in ('q397','glm52') and g['phase']=='readers':g['mean_latency_seconds']='999999'
        out=self.build();self.assertEqual(before,out['candidates'])
        self.assertTrue(any(g['mean_latency_seconds']=='999999' for g in out['development_serving_metadata']))
    def test_global_capacity_and_model_limits_bound_every_phase(self):
        out=self.build();c=out['candidates'][0]
        for phase in c['phase_bounds']:
            self.assertGreaterEqual(Decimal(phase['bottleneck_service_seconds']),Decimal(phase['global_service_seconds']))
        # Four actor models each require640*8/2 seconds; provider/global8 agree.
        x=next(p for p in c['phase_bounds'] if p['phase']=='x')
        self.assertEqual(Decimal(x['native_service_seconds']),Decimal(2560))
    def test_slow_failed_actor_latency_is_retained_and_unknown_cost_reserved(self):
        before=self.build()['candidates'][0]
        g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='q397' and g['phase']=='reporter')
        g.update(known_usage_count=79,unknown_usage_count=1,known_transient_count=1,known_transient_rate=str(Decimal(1)/80),mean_latency_seconds='504');sync_classes(g)
        after=self.build()['candidates'][0]
        self.assertGreater(Decimal(after['forecast_seconds']),Decimal(before['forecast_seconds']))
        self.assertGreater(Decimal(after['projected_native_actor_peak_cost']),Decimal(before['projected_native_actor_peak_cost']))
        phase=next(p for p in after['phase_bounds'] if p['phase']=='reporter')
        self.assertEqual(Decimal(phase['global_cooldown_seconds']),Decimal(120))
    def test_retry_after_and_disjoint_classes(self):
        job=dict(provider='adaption',transient_classes={k:dict(rate='.1',max_retry_after_seconds='120') for k in ('gateway_5xx','overload_429')})
        self.assertEqual(f.effective_error(job),(Decimal('.2'),Decimal(24)))
    def test_wallet_is_boolean_private_and_strict(self):
        out=self.build();cost=Decimal(out['candidates'][0]['projected_main_peak_costs']['ollama'])
        threshold=cost/2+Decimal('5.10')
        self.assertFalse(self.build(threshold)['candidates'][0]['off_peak_wallet_gate_passed'])
        self.assertTrue(self.build(threshold+Decimal('.00001'))['candidates'][0]['off_peak_wallet_gate_passed'])
        amount='987654.123456789';self.assertNotIn(amount,json.dumps(self.build(amount)))
        self.assertEqual(out['candidates'][0]['main_ollama_peak_cap'],'99.70')
    def test_missing_history_and_wrong_capacity_fail_closed(self):
        self.inputs['pilot_cost_metadata']['baselines'].pop()
        with self.assertRaisesRegex(ValueError,'Both historical'):self.build()
        self.inputs=fixture();self.inputs['native_candidates']=[4]
        with self.assertRaisesRegex(ValueError,'Fixed native'):self.build()
    def test_missing_dev_group_and_mismatched_transient_counts_fail(self):
        self.inputs['development_groups'].pop()
        with self.assertRaisesRegex(ValueError,'Complete DEV'):self.build()
        self.inputs=fixture();self.inputs['development_groups'][0]['mean_latency_seconds']='NaN'
        with self.assertRaisesRegex(ValueError,'Invalid DEV'):self.build()
    def test_full_unknown_reservation_and_cost_cap_refusal(self):
        out=self.build();p=self.inputs['science_config']['profiles'][0]
        item=next(g for g in out['cost_groups'] if g['profile_id']==p['id'])
        full=(Decimal(self.inputs['science_config']['input_byte_cap'])*Decimal(p['input_rate'])+Decimal(p['max_output_tokens'])*Decimal(p['output_rate']))/1000000
        self.assertEqual(Decimal(item['full_unknown_row_reservation']),full)
        self.inputs['science_config']['native_class_caps']['actors']='0'
        with self.assertRaisesRegex(ValueError,'provider/class cap'):self.build()
    def test_dispatch_spacing_floor_and_metadata_hash_integrity(self):
        for g in self.inputs['development_groups']:g['mean_latency_seconds']='.001'
        phase=next(p for p in self.build()['candidates'][0]['phase_bounds'] if p['phase']=='x')
        self.assertEqual(Decimal(phase['native_service_seconds']),Decimal(2560))
        self.inputs['pilot_metadata_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'metadata hash'):self.build()
    def test_deadline_is_gate_not_claim_of_completion(self):
        out=f.build(self.inputs,'2026-11-09T05:58:59+00:00',100)
        self.assertFalse(out['candidates'][0]['deadline_feasible'])
        self.assertIn('not a guarantee',out['known_gateway_projection_caveat'])
    def test_gateway_allowance_exhaustion_is_visible(self):
        for g in self.inputs['development_groups']:
            if g['phase']=='readers' and g['profile_id']=='g26':
                g.update(known_usage_count=16,unknown_usage_count=16,known_transient_count=16,known_transient_rate='.5');sync_classes(g)
        # Resource cap may refuse the whole workload before scheduling if rates
        # demand too much reservation; increase only synthetic cap to isolate gate.
        self.inputs['science_config']['native_class_caps']['readers']='10000'
        self.inputs['science_config']['phase_caps']['main']['adaption']='11000'
        out=self.build();self.assertFalse(out['candidates'][0]['gateway_allowance_feasible'])

if __name__=='__main__':unittest.main()
