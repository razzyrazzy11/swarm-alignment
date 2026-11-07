"""Synthetic serving metadata only: no keys, model outputs, billing or inference."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments import swarm_ledger_forecast as f


def fixture():
    config=f.s.config();groups=[]
    reader_latency={'g26':10,'g31':12,'q397':40,'glm52':30,'hf_text':10,'hf_schema':10,'ds_off':2,'ds_low':10}
    for p in config['worker_profiles']:
        for phase,n in f.DEV_COUNTS.items():
            groups.append(dict(profile_id=p,phase=phase,count=n,known_usage_count=n,unknown_usage_count=0,
                               mean_latency_seconds='8',max_known_input_tokens=100,max_known_output_tokens=10,
                               known_transient_count=0,known_transient_rate='0',max_retry_after_seconds='0'))
    for p in config['reader_profiles']:
        groups.append(dict(profile_id=p,phase='readers',count=32,known_usage_count=32,unknown_usage_count=0,
                           mean_latency_seconds=str(reader_latency[p]),max_known_input_tokens=100,max_known_output_tokens=10,
                           known_transient_count=0,known_transient_rate='0',max_retry_after_seconds='0'))
    inputs=dict(science_config=config,development_groups=groups,collection_cutoff_utc=f.CUTOFF,
                development_freeze_sha256='1'*64,pilot_freeze_sha256='2'*64,driver_state_sha256='3'*64,
                journal_sha256={},max_ollama_combined_peak_cap='50.00',native_candidates=[4,8,16])
    pilots=[]
    for k,rates in [(4,{'q397':'.1','glm52':'.2'}),(8,{'q397':'.125','glm52':'.25'}),(16,{'q397':'.16','glm52':'.30'})]:
        pilots.append(dict(level=k,planned=64,started=64,terminal=64,eligible=True,event_metrics={'complete':True},
                           profiles={p:dict(complete=True,requests_per_second=rate,elapsed_seconds=str(Decimal(32)/Decimal(rate)),
                                            known_transient_count=0,known_transient_rate='0',max_retry_after_seconds='0') for p,rate in rates.items()}))
    return inputs,dict(native_candidates=pilots,selected_ollama_per_model=3,ollama_pilot={'complete':True})


class ForecastTests(unittest.TestCase):
    def setUp(self):self.inputs,self.pilot=fixture();self.at='2026-11-07T00:00:00+00:00'
    def build(self,wallet=100):return f.build(self.inputs,self.pilot,self.at,Decimal(str(wallet)))

    def test_fixed_main_counts_and_classes(self):
        result=self.build();self.assertEqual(result['workload']['actor_calls_including_influence'],9200)
        self.assertEqual(result['workload']['reader_calls_including_calibration'],64320)
        groups=result['cost_groups']
        for p in self.inputs['science_config']['worker_profiles']:
            self.assertEqual(sum(g['calls'] for g in groups if g['profile_id']==p and g['phase'] in f.ACTOR_COUNTS),2300)
        readers={g['profile_id']:g['calls'] for g in groups if g['phase']=='readers'}
        self.assertEqual(readers['g26'],12800);self.assertEqual(readers['hf_text'],5120)
        for c in result['candidates']:
            self.assertEqual(Decimal(c['projected_native_actor_peak_cost'])+Decimal(c['projected_native_reader_peak_cost']),
                             Decimal(c['projected_main_peak_costs']['adaption']))

    def test_phase_barriers_shared_model_capacity_and_safety_arithmetic(self):
        result=self.build();c=next(c for c in result['candidates'] if c['native_per_model']==4 and c['ollama_per_model']==2)
        phases={p['phase']:p for p in c['phase_bounds']}
        # Both HF formats share the two-slot model; never divide each in parallel.
        self.assertEqual(Decimal(phases['readers']['hf_seconds']),Decimal(5120*10*2)/2)
        self.assertEqual(Decimal(phases['readers']['ollama_seconds']),Decimal(5120*2+12800*10)/2)
        self.assertEqual(Decimal(c['base_seconds']),sum(Decimal(p['bottleneck_seconds']) for p in phases.values()))
        self.assertEqual(Decimal(c['forecast_seconds']),Decimal(c['base_seconds'])*Decimal('1.25')+1800)
        self.assertEqual(Decimal(phases['readers']['native_seconds']),128000)
        self.assertGreater(Decimal(c['native_critical_seconds']),Decimal(phases['readers']['native_seconds']))

    def test_measured_throughput_floor_prevents_linear_speedup_assumption(self):
        result=self.build();c=next(c for c in result['candidates'] if c['native_per_model']==8 and c['ollama_per_model']==3)
        readers=next(p for p in c['phase_bounds'] if p['phase']=='readers')
        # Q397 DEV mean40/8=5s, but measured pilot floor1/.125=8s dominates.
        self.assertEqual(Decimal(readers['native_seconds']),Decimal(12800*8))
        # Pilot sample count can change without a stale /12 or /32 assumption.
        self.pilot['native_candidates'][1].update(planned=128,started=128,terminal=128)
        changed=self.build();same=next(c for c in changed['candidates'] if c['native_per_model']==8 and c['ollama_per_model']==3)
        self.assertEqual(c['base_seconds'],same['base_seconds'])

    def test_ollama_three_slots_apply_to_sum_of_both_thinking_profiles(self):
        for g in self.inputs['development_groups']:
            if g['phase']=='readers' and g['profile_id'] in ('ds_off','ds_low'):g['mean_latency_seconds']='100'
        rows=self.build()['candidates'];two=next(c for c in rows if c['native_per_model']==8 and c['ollama_per_model']==2)
        three=next(c for c in rows if c['native_per_model']==8 and c['ollama_per_model']==3)
        self.assertGreater(Decimal(two['base_seconds']),Decimal(three['base_seconds']))

    def test_native_sixteen_per_model_still_shares_sixteen_provider_slots(self):
        for group in self.inputs['development_groups']:
            if group['phase']=='readers' and group['profile_id'] in ('g26','g31','q397','glm52'):group['mean_latency_seconds']='100'
        for profile in self.pilot['native_candidates'][2]['profiles'].values():profile['requests_per_second']='100'
        candidate=next(c for c in self.build()['candidates'] if c['native_per_model']==16 and c['ollama_per_model']==2)
        phase=next(p for p in candidate['phase_bounds'] if p['phase']=='readers')
        self.assertEqual(Decimal(phase['native_service_seconds']),Decimal(35840*100)/16)

    def test_reporter_known_errors_add_global_backoff_before_safety_margin(self):
        original=self.build();g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='g26' and g['phase']=='reporter')
        g.update(known_usage_count=76,unknown_usage_count=4,known_transient_count=4,known_transient_rate='.05',max_retry_after_seconds='120')
        changed=self.build();before=original['candidates'][0];after=changed['candidates'][0]
        phase=next(p for p in after['phase_bounds'] if p['phase']=='reporter')
        self.assertEqual(Decimal(phase['global_cooldown_seconds']),Decimal(640)*Decimal('.05')*120)
        self.assertEqual(Decimal(after['base_seconds'])-Decimal(before['base_seconds']),3840)
        self.assertEqual(Decimal(after['native_critical_seconds'])-Decimal(before['native_critical_seconds']),3840)
        self.assertEqual(Decimal(after['forecast_seconds'])-Decimal(before['forecast_seconds']),4800)
        self.assertGreater(Decimal(after['projected_main_peak_costs']['adaption']),Decimal(before['projected_main_peak_costs']['adaption']))
        self.assertEqual(after['projected_main_peak_costs']['hf'],before['projected_main_peak_costs']['hf'])
        self.assertEqual(after['projected_main_peak_costs']['ollama'],before['projected_main_peak_costs']['ollama'])

    def test_big_native_reader_uses_worse_dev_or_pilot_rate_and_retry_after(self):
        original=self.build();p=self.pilot['native_candidates'][0]['profiles']['q397']
        p.update(known_transient_count=1,known_transient_rate='.03125',max_retry_after_seconds='300')
        after=self.build()['candidates'][0];reader=next(v for v in after['phase_bounds'] if v['phase']=='readers')
        self.assertEqual(Decimal(reader['global_cooldown_seconds']),Decimal(12800)*Decimal('.03125')*300)
        actor=next(v for v in after['phase_bounds'] if v['phase']=='reporter')
        self.assertEqual(Decimal(actor['global_cooldown_seconds']),0)
        g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='q397' and g['phase']=='readers')
        g.update(known_usage_count=28,unknown_usage_count=4,known_transient_count=4,known_transient_rate='.125',max_retry_after_seconds='60')
        reader=next(v for v in self.build()['candidates'][0]['phase_bounds'] if v['phase']=='readers')
        self.assertEqual(Decimal(reader['global_cooldown_seconds']),Decimal(12800)*Decimal('.125')*300)

    def test_other_provider_errors_pause_native_work_in_same_phase(self):
        original=self.build()['candidates'][0]
        for profile,retry in [('ds_low','0'),('hf_text','90')]:
            g=next(g for g in self.inputs['development_groups'] if g['profile_id']==profile and g['phase']=='readers')
            g.update(known_usage_count=31,unknown_usage_count=1,known_transient_count=1,known_transient_rate='.03125',max_retry_after_seconds=retry)
        changed=self.build()['candidates'][0];reader=next(v for v in changed['phase_bounds'] if v['phase']=='readers')
        self.assertEqual(Decimal(reader['global_cooldown_seconds']),38400)
        self.assertEqual(Decimal(reader['provider_cooldown_seconds']['ollama']),24000)
        self.assertEqual(Decimal(reader['provider_cooldown_seconds']['hf']),14400)
        self.assertGreater(Decimal(changed['native_critical_seconds']),Decimal(original['native_critical_seconds']))

    def test_metadata_aggregate_classifies_only_registered_transient_errors(self):
        rows=[]
        for i,(status,overload) in enumerate([(200,False),(504,False),(429,True),(429,False)]):
            rows.append(dict(id=str(i),profile_id='g26',known_usage=status==200,
                             response={'usage':{'input_tokens':1,'output_tokens':1} if status==200 else None},
                             transport={'http_status':status,'service_overload':overload,'latency_seconds':1}))
        group=f.aggregate(rows,'reporter',{'1':300,'2':30})[0]
        self.assertEqual(group['known_transient_count'],2);self.assertEqual(group['known_transient_rate'],'0.5')
        self.assertEqual(group['max_retry_after_seconds'],'300')
        with self.assertRaises(ValueError):f.aggregate(rows,'reporter',{'1':901})

    def test_projected_unknown_errors_retain_full_request_reservation(self):
        g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='g26' and g['phase']=='reporter')
        g.update(known_usage_count=76,unknown_usage_count=4,known_transient_count=4,known_transient_rate='.05')
        value=self.build();shared=next(c for c in value['cost_groups'] if c['profile_id']=='g26' and c['phase']=='reporter')
        row=next(c for c in value['candidates'][0]['cost_groups'] if c['profile_id']=='g26' and c['phase']=='reporter')
        known=Decimal(shared['margined_known_row_cost']);reserve=Decimal(shared['full_unknown_row_reservation'])
        expected=640*(Decimal('.95')*known+Decimal('.05')*reserve)
        self.assertEqual(Decimal(row['projected_peak_cost']),expected)
        self.assertGreater(expected,640*known)

    def test_pilot_max_error_rate_changes_candidate_native_cost(self):
        self.pilot['native_candidates'][1]['profiles']['q397'].update(known_transient_count=1,known_transient_rate='.03125')
        candidates=self.build()['candidates'];four=next(c for c in candidates if c['native_per_model']==4 and c['ollama_per_model']==2)
        eight=next(c for c in candidates if c['native_per_model']==8 and c['ollama_per_model']==2)
        self.assertGreater(Decimal(eight['projected_native_reader_peak_cost']),Decimal(four['projected_native_reader_peak_cost']))
        self.assertEqual(eight['projected_native_actor_peak_cost'],four['projected_native_actor_peak_cost'])

    def test_already_full_known_margin_does_not_double_reserve(self):
        for g in self.inputs['development_groups']:
            if g['profile_id']=='g26':g.update(max_known_input_tokens=22000,max_known_output_tokens=3000)
        before=self.build()['candidates'][0]['projected_main_peak_costs']['adaption']
        g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='g26' and g['phase']=='reporter')
        g.update(known_usage_count=76,unknown_usage_count=4,known_transient_count=4,known_transient_rate='.05')
        self.assertEqual(Decimal(self.build()['candidates'][0]['projected_main_peak_costs']['adaption']),Decimal(before))

    def test_weighted_unknown_costs_feed_wallet_gate_and_provider_caps(self):
        for g in self.inputs['development_groups']:
            if g['profile_id'] in ('ds_off','ds_low'):g['max_known_output_tokens']=900
        self.assertTrue(self.build(25)['candidates'][0]['off_peak_wallet_gate_passed'])
        g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='ds_low' and g['phase']=='readers')
        g.update(known_usage_count=31,unknown_usage_count=1,known_transient_count=1,known_transient_rate='.03125')
        self.assertFalse(self.build(25)['candidates'][0]['off_peak_wallet_gate_passed'])
        g=next(g for g in self.inputs['development_groups'] if g['profile_id']=='hf_text' and g['phase']=='readers')
        g.update(known_usage_count=1,unknown_usage_count=31,known_transient_count=31,known_transient_rate='.96875')
        with self.assertRaisesRegex(ValueError,'provider/class cap'):self.build()

    def test_token_margins_clip_at_frozen_caps_and_costs_are_provider_separate(self):
        for g in self.inputs['development_groups']:
            if g['profile_id']=='g26':g.update(max_known_input_tokens=22000,max_known_output_tokens=3000)
        result=self.build();g26=[g for g in result['cost_groups'] if g['profile_id']=='g26']
        self.assertTrue(all(g['projected_input_tokens']=='24000' and g['projected_output_tokens']=='4096' for g in g26))
        c=result['candidates'][0]
        self.assertEqual(set(c['projected_main_peak_costs']),{'adaption','hf','ollama'})
        self.assertLess(Decimal(c['projected_main_peak_costs']['hf']),Decimal('2.39'))

    def test_unknown_latencies_retained_and_response_text_never_returned(self):
        rows=[dict(profile_id='g26',known_usage=True,response={'usage':{'input_tokens':100,'output_tokens':20},'output_text':'DO-NOT-LEAK'},
                   transport={'latency_seconds':100},metadata={'action_delta':2}),
              dict(profile_id='g26',known_usage=False,response={'usage':None,'output_text':'DO-NOT-LEAK'},transport={'latency_seconds':.2})]
        metadata=f.aggregate(rows,'y')[0]
        self.assertEqual(Decimal(metadata['mean_latency_seconds']),Decimal('50.1'));self.assertEqual(metadata['unknown_usage_count'],1)
        self.assertNotIn('DO-NOT-LEAK',json.dumps(metadata));self.assertNotIn('action_delta',metadata)
        self.inputs['development_groups'][0]['output_text']='DO-NOT-LEAK'
        with self.assertRaisesRegex(ValueError,'allowlist'):self.build()

    def test_wallet_privacy_original_cap_then_conditional_extension(self):
        value=self.build(98765.432109);text=json.dumps(value)
        self.assertNotIn('98765.432109',text);self.assertNotIn('wallet_available',text)
        self.assertTrue(all(c['ollama_combined_peak_cap']=='25.00' for c in value['candidates']))
        for g in self.inputs['development_groups']:
            if g['profile_id'] in ('ds_off','ds_low'):g['max_known_output_tokens']=900
        extended=self.build(25)
        self.assertTrue(all(c['ollama_combined_peak_cap']=='50.00' and c['main_ollama_peak_cap']=='49.70' for c in extended['candidates']))
        self.assertTrue(all(c['off_peak_wallet_gate_passed'] for c in extended['candidates']))
        self.assertFalse(any(c['off_peak_wallet_gate_passed'] for c in self.build(24)['candidates']))

    def test_full_window_offpeak_required_even_without_cap_extension(self):
        self.at='2026-11-06T13:00:00+00:00';value=self.build()
        self.assertFalse(value['off_peak_window_verified']);self.assertFalse(any(c['off_peak_wallet_gate_passed'] for c in value['candidates']))
        start=datetime(2026,11,6,18,tzinfo=timezone.utc);end=datetime(2026,11,9,18,tzinfo=timezone.utc)
        self.assertFalse(f.off_peak_window(start,end))

    def test_ineligible_capacity_level_omitted_no_invented_throughput(self):
        bad=self.pilot['native_candidates'][1];bad.update(eligible=False,terminal=3,started=3);bad['profiles']={}
        self.pilot['native_candidates'][2].update(eligible=False,started=0,terminal=0,profiles={})
        value=self.build();self.assertEqual(len(value['candidates']),2)
        self.assertEqual(value['eligible_native_levels'],[4]);self.assertEqual(value['excluded_native_levels'],[8,16])
        self.pilot['native_candidates'][0]['eligible']=False
        with self.assertRaisesRegex(ValueError,'No fully eligible'):self.build()

    def test_missing_profiles_unknown_only_groups_and_invalid_latency_rejected(self):
        original=deepcopy(self.inputs)
        self.inputs['development_groups'].pop()
        with self.assertRaises(ValueError):self.build()
        self.inputs=deepcopy(original);self.inputs['science_config']['profiles'].pop()
        with self.assertRaises(ValueError):self.build()
        self.inputs=deepcopy(original);self.inputs['development_groups'][0]['known_usage_count']=0
        self.inputs['development_groups'][0]['unknown_usage_count']=20
        with self.assertRaises(ValueError):self.build()
        self.inputs=deepcopy(original);self.inputs['development_groups'][0]['mean_latency_seconds']='NaN'
        with self.assertRaises(ValueError):self.build()


class WalletIntegrationTests(unittest.TestCase):
    def test_one_shared_cache_check_not_one_get_per_candidate(self):
        from experiments import swarm_ledger_dispatch as op
        inputs,pilot=fixture()
        for stale,expected_gets in ((False,0),(True,1)):
            with self.subTest(stale=stale),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);guard=root/('runs/'+inputs['science_config']['study_id']+'-guard');guard.mkdir(parents=True)
                cache=guard/'balance-private.json';cache.write_text(json.dumps({'epoch':datetime.now(timezone.utc).timestamp()-(61 if stale else 0),'available':'100','spent':'0'}))
                calls=[]
                class Transport:
                    def __init__(self,*args):pass
                    def metadata(self,url,keyname):
                        calls.append((url,keyname));return {'included':{'balance_usd':'100'},'purchased':{'balance_usd':'0'}}
                with patch.object(f.s,'ROOT',root),patch.object(f.s,'folder',side_effect=lambda split:root/split),\
                     patch.object(f,'admitted_inputs',return_value=(inputs,[])),patch.object(op,'pilot_metadata',return_value=pilot),\
                     patch.object(op,'config',return_value={'study_id':'fixture-op','pilot_phase_order':[]}),\
                     patch.object(f.s,'credentials',return_value={}),patch.object(f.s,'Transport',Transport):
                    out=root/'forecast.json';result=f.create(root/'state.json',out)
                self.assertTrue(result['wallet_gate_passed']);self.assertEqual(len(calls),expected_gets)
                public=out.read_text();self.assertNotIn('available_after_known_spending',public)
                self.assertTrue((root/'runs/fixture-op-forecast/wallet-private.json').exists())

    def test_metadata_artifact_is_accepted_by_operational_contract(self):
        from experiments import swarm_ledger_dispatch as op
        inputs,pilot=fixture();value=f.build(inputs,pilot,'2026-11-07T00:00:00+00:00',100)
        config=dict(native_candidates=[4,8,16],collection_deadline_utc=f.CUTOFF,max_ollama_combined_peak_equivalent_cap='50.00',off_peak_only=True)
        development=f.s.freeze_path('development');pilot_path=Path('synthetic-pilot-freeze.json')
        with patch.object(op,'config',return_value=config),patch.object(op,'op_freeze',return_value=pilot_path),\
             patch.object(op,'sha',side_effect=lambda path:'1'*64 if path==development else '2'*64):
            self.assertEqual(len(op.validate_forecast(value)['candidates']),6)


if __name__=='__main__':unittest.main()
