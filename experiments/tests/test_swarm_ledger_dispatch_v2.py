"""Offline scheduling-amendment checks. No credentials or provider requests."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from experiments import swarm_ledger_dispatch_v2 as d
from experiments import swarm_ledger_study as s


def native_row(out,job,http=200):
    p=s.profile(job['profile_id'])
    if p['provider']=='ollama':
        native={'model':p['model'],'done':True,'done_reason':'stop','message':{'content':'not a verdict'},'prompt_eval_count':10,'eval_count':5}
    else:native={'model':p['model'],'status':'completed','output_text':'not a verdict','usage':{'input_tokens':10,'output_tokens':5}}
    receipt={'native_response':native} if http==200 else {'error_body':'temporary capacity','headers':{}}
    path=out/'native'/(s.digest(job['id'])+'.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(receipt),encoding='utf-8')
    response,known,anomaly=s.normalize(native if http==200 else None,p)
    return {'id':job['id'],'profile_id':job['profile_id'],'metadata':job['metadata'],'transport':{'http_status':http,'latency_seconds':3.5},
            'response':response,'known_usage':known,'anomaly':anomaly,'native_receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'estimated_cost':str(s.actual_cost(job,response) if known else s.reservation(job))}


def write_phase(out,jobs,failed=False):
    out.mkdir(parents=True,exist_ok=True)
    chosen=jobs[:4] if failed else jobs
    for i,j in enumerate(chosen):
        s.durable(out/'attempts.jsonl',{'id':j['id'],'profile_id':j['profile_id'],'request_sha256':s.digest(s.body_for(j)),
                  'reserved_cost':str(s.reservation(j)),'started':datetime.fromtimestamp(100+i,tz=timezone.utc).isoformat()})
        s.durable(out/'responses.jsonl',native_row(out,j,503 if failed else 200))
        lag=3.5 if out.name=='native4' else 2.5
        s.durable(out/'dispatch-events.jsonl',{'event':'client_transport_dispatch','id':j['id'],'provider':s.profile(j['profile_id'])['provider'],'epoch':100+i})
        s.durable(out/'dispatch-events.jsonl',{'event':'client_transport_finish','id':j['id'],'provider':s.profile(j['profile_id'])['provider'],'epoch':100+i+lag})
    if failed:(out/'stop.json').write_text(json.dumps({'reason':'provider_or_capture_integrity'}))


def forecast_fixture():
    baseline=d.prior_public_baseline()
    lineage={'estimated_cost_by_provider':baseline['estimated_cost_by_provider'],'prior_estimated_cost_by_provider':baseline['estimated_cost_by_provider'],'current_estimated_cost_by_provider':{p:'0' for p in ('adaption','hf','ollama')},'prior_registration_tag':baseline['registration_tag'],'prior_registration_sha256':baseline['registration_sha256'],'prior_baseline_sha256':s.sha(s.ROOT/d.config()['prior_pilot_baseline']),'prior_private_file_raw_sha256':baseline['private_file_raw_sha256']}
    return {'main_known_gateway_allowance':1024,'pilot_cost_lineage':lineage,'schema_version':1,'generated_at':'2026-11-07T15:00:00+00:00',
            'development_freeze_sha256':s.sha(s.freeze_path('development')),'pilot_freeze_sha256':'pilot-hash',
            'safety_multiplier':1.25,'overhead_seconds':1800,'collection_cutoff_utc':d.config()['collection_deadline_utc'],
            'candidates':[{'native_per_model':n,'ollama_per_model':3,'base_seconds':'1000','native_critical_seconds':'900','forecast_seconds':'3050',
                           'gateway_allowance_feasible':True,'phase_bounds':[{'phase':phase,'projected_known_transient_terminals':{'adaption':'0','hf':'0','ollama':'0'},'projected_known_transient_total':'0'} for phase in ('principal','coordinator','x','y','reporter','readers','calibration','influence')],
                           'projected_main_peak_costs':{'adaption':'30','hf':'1.0','ollama':'10'},
                           'projected_native_actor_peak_cost':'10','projected_native_reader_peak_cost':'20','off_peak_wallet_gate_passed':True,
                           'ollama_combined_peak_cap':'25.00','main_ollama_peak_cap':'24.70'} for n in (4,8)]}


class DispatchPlanTests(unittest.TestCase):
    def test_registration_anchor_hashes_normalize_crlf_without_altering_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'registration.json';original=b'{\r\n  "example": true\r\n}\r\n';path.write_bytes(original)
            self.assertEqual(d.sha(path),hashlib.sha256(original.replace(b'\r\n',b'\n')).hexdigest())
            self.assertEqual(path.read_bytes(),original)

    def test_distinct_excluded_pilot_and_unchanged_old_bodies(self):
        before=s.config();a=d.pilot_jobs(4);b=d.pilot_jobs(8);c=d.pilot_jobs(16)
        self.assertEqual((len(a),len(b),len(c),len(d.ollama_pilot_jobs())),(64,64,64,6))
        self.assertFalse({j['id'] for j in a}&{j['id'] for j in b})
        self.assertEqual(len({j['id'] for j in a+b+c}),192)
        self.assertLessEqual(sum(s.reservation(j) for j in a+b+c),Decimal(d.config()['pilot_caps']['adaption']))
        self.assertLessEqual(sum(s.reservation(j) for j in d.ollama_pilot_jobs()),Decimal(d.config()['pilot_caps']['ollama']))
        for x,y in zip(a,b):
            self.assertEqual(d.body_for(x),s.body_for(x));self.assertEqual(s.body_for(x),s.body_for(y))
            self.assertTrue(x['metadata']['excluded_from_scientific_results'])
            self.assertEqual(set(json.loads(x['messages'][1]['content'])),{'public','manifest','records'})
        cfg=d.execution_config('pilot','native8')
        self.assertEqual(cfg['dispatch_model_limits'],{'adaption':8,'hf':2,'ollama':3})
        self.assertEqual(cfg['max_active'],21);self.assertEqual(s.config(),before)
        larger=d.execution_config('pilot','native16')
        self.assertEqual(larger['dispatch_model_limits']['adaption'],16)
        self.assertEqual(larger['provider_max_active']['adaption'],16)

    def test_offpeak_calendar_and_registered_cutoff(self):
        self.assertTrue(d.off_peak(datetime(2026,11,7,14,tzinfo=timezone.utc)))
        self.assertTrue(d.off_peak(datetime(2026,11,9,11,tzinfo=timezone.utc)))
        self.assertFalse(d.off_peak(datetime(2026,11,9,12,tzinfo=timezone.utc)))

    def test_native_health_requires_all_cases_and_at_most_one_known_error_per_profile(self):
        jobs=d.pilot_jobs(4)
        with tempfile.TemporaryDirectory() as directory:
            terminal=[native_row(Path(directory),job) for job in jobs]
            self.assertTrue(d.native_health(jobs,terminal)[0])
            for identity in ('q397','glm52'):
                row=next(r for r in terminal if r['profile_id']==identity)
                row['transport']['http_status']=503;row['known_usage']=False;row['anomaly']=True
            healthy,summary=d.native_health(jobs,terminal)
            self.assertTrue(healthy);self.assertTrue(all(v['admitted']==31 for v in summary.values()))
            self.assertFalse(d.native_health(jobs,terminal[:-1])[0])
            more=next(r for r in terminal if r['profile_id']=='q397' and r['transport']['http_status']==200)
            more['transport']['http_status']=503;more['known_usage']=False;more['anomaly']=True
            self.assertFalse(d.native_health(jobs,terminal)[0])
            more['transport']['http_status']=200
            self.assertFalse(d.native_health(jobs,terminal)[0])

    def test_pilot_includes_group_budget_breach_and_matched_permitted_case(self):
        jobs=[j for j in d.pilot_jobs(4) if j['profile_id']=='q397']
        for index,budget,delta_y,breach in ((3,3,2,True),(7,4,2,False),(11,2,1,True)):
            job=next(j for j in jobs if j['metadata']['case_index']==index)
            packet=json.loads(job['messages'][1]['content'])
            by_kind={r['kind']:r['payload'] for r in packet['records'] if r['trusted']}
            self.assertEqual(packet['public']['budget'],budget)
            self.assertEqual(by_kind['x_commit']['delta'],2);self.assertEqual(by_kind['y_commit']['delta'],delta_y)
            self.assertTrue(by_kind['issue']['issued']);self.assertTrue(by_kind['grant_y']['granted'])
            self.assertEqual(by_kind['y_clock']['settled_at'],125);self.assertFalse(by_kind['revocation']['revoked'])
            expected={by_kind['y_binding']['instance']} if breach else {'NONE'}
            self.assertEqual(set(s.engine.labels(packet)),expected)

    def test_forecast_margin_and_cap_arithmetic(self):
        value=forecast_fixture()
        with (patch.object(d,'op_freeze',return_value=Path('pilot')),
              patch.object(d,'sha',side_effect=lambda path:'pilot-hash' if str(path)=='pilot' else s.sha(path))):
            self.assertTrue(d.validate_forecast(value)['candidates'][0]['deadline_feasible'])
            bad=deepcopy(value);bad['candidates'][0]['main_ollama_peak_cap']='25.00'
            with self.assertRaisesRegex(ValueError,'main spending ceiling'):d.validate_forecast(bad)
            bad=deepcopy(value);bad['candidates'][0]['forecast_seconds']='1000'
            with self.assertRaisesRegex(ValueError,'margin arithmetic'):d.validate_forecast(bad)

    def test_retry_after_is_honored_up_to_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);native=out/'native';native.mkdir()
            job_id='retry';path=native/(s.digest(job_id)+'.json')
            row={'id':job_id,'transport':{'http_status':503}}
            path.write_text(json.dumps({'headers':{'Retry-After':'120'}}))
            self.assertEqual(d.retry_after_delay(row,out),120)
            path.write_text(json.dumps({'headers':{'Retry-After':'901'}}))
            with self.assertRaises(ValueError):d.retry_after_delay(row,out)

    def test_historical_http_date_retry_after_uses_receipt_time_not_now(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);path=out/'native'/(s.digest('historical')+'.json');path.parent.mkdir()
            row={'id':'historical','transport':{'http_status':503}}
            headers={'Date':'Sat, 07 Nov 2026 14:00:00 GMT','Retry-After':'Sat, 07 Nov 2026 14:02:00 GMT'}
            path.write_text(json.dumps({'headers':headers}));row['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(d.retry_after_metadata_delay(row,out),120)
            headers.pop('Date');path.write_text(json.dumps({'headers':headers}));row['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            anchor=datetime(2026,11,7,14,tzinfo=timezone.utc).timestamp()
            self.assertEqual(d.retry_after_metadata_delay(row,out,fallback_epoch=anchor),120)
            with self.assertRaises(ValueError):d.retry_after_metadata_delay(row,out)
            s.durable(out/'dispatch-events.jsonl',{'event':'client_transport_finish','id':'historical','epoch':anchor})
            self.assertEqual(d.retry_after_metadata_delay(row,out),120)
            path.write_text(json.dumps({'headers':{'Retry-After':'NaN'}}))
            with self.assertRaises(ValueError):d.retry_after_delay(row,out)

    def test_forecast_cannot_extend_cap_without_need_and_wallet_gate(self):
        with (patch.object(d,'op_freeze',return_value=Path('pilot')),
              patch.object(d,'sha',side_effect=lambda path:'pilot-hash' if str(path)=='pilot' else s.sha(path))):
            value=forecast_fixture();item=value['candidates'][0]
            item.update(ollama_combined_peak_cap='100.00',main_ollama_peak_cap='99.70')
            with self.assertRaisesRegex(ValueError,'Unnecessary'):d.validate_forecast(value)
            item['projected_main_peak_costs']['ollama']='35'
            self.assertTrue(d.validate_forecast(value)['candidates'][0]['deadline_feasible'])
            item['off_peak_wallet_gate_passed']=False
            with self.assertRaisesRegex(ValueError,'wallet gate'):d.validate_forecast(value)

    def test_known_failed_higher_candidate_can_qualify_lower(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);selection=root/'selection.json';forecast=root/'forecast.json'
            cfg=d.config();baseline=d.prior_public_baseline();source=s.ROOT/cfg['prior_pilot_baseline'];target=root/cfg['prior_pilot_baseline'];target.parent.mkdir(parents=True);target.write_bytes(source.read_bytes())
            with (patch.object(d,'ROOT',root),patch.object(d,'prior_public_baseline',return_value=baseline),patch.object(d,'verify_prior_pilot_private',return_value=baseline),patch.object(d,'SELECTION',selection),patch.object(d,'verify',return_value={}),
                  patch.object(d,'op_freeze',return_value=Path('pilot')),patch.object(d,'sha',side_effect=lambda path:'pilot-hash' if str(path)=='pilot' else s.sha(path))):
                write_phase(d.folder('pilot')/'native4',d.pilot_jobs(4))
                write_phase(d.folder('pilot')/'native8',d.pilot_jobs(8),failed=True)
                write_phase(d.folder('pilot')/'ollama3',d.ollama_pilot_jobs())
                plan=forecast_fixture();plan['candidates']=[v for v in plan['candidates'] if v['native_per_model']==4]
                forecast.write_text(json.dumps(plan))
                result=d.select(forecast)
                self.assertEqual(result['selected_native_per_model'],4)
                self.assertEqual(result['selected_ollama_per_model'],3)
                higher=next(x for x in result['native_candidates'] if x['level']==8)
                self.assertEqual(len(higher['unstarted_ids']),60)
                self.assertIsNone(higher['forecast']);self.assertFalse(higher['deadline_feasible'])
                with patch.object(d,'pilot_cost_metadata',return_value=result['forecast']['pilot_cost_lineage']):self.assertTrue(d.pilot_integrity(result))
                (d.folder('pilot')/'native8/stop.json').write_text(json.dumps({'reason':'metadata_integrity'}))
                with self.assertRaises(ValueError):d.pilot_integrity(result)

    def test_pilot_ramp_requires_completed_lower_group_and_blocks_its_fatal_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(d,'ROOT',Path(directory)):
                with self.assertRaisesRegex(ValueError,'Complete lower-load'):d.pilot_phase_gate('native8')
                out=d.folder('pilot')/'native4';write_phase(out,d.pilot_jobs(4))
                self.assertTrue(d.pilot_phase_gate('native8'))
                (out/'stop.json').write_text(json.dumps({'reason':'provider_or_capture_integrity'}))
                with self.assertRaisesRegex(ValueError,'Fatal lower-load'):d.pilot_phase_gate('native8')

    def test_stopped_eight_blocks_sixteen_but_allows_recorded_skip_to_ollama(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(d,'ROOT',Path(directory)):
                write_phase(d.folder('pilot')/'native4',d.pilot_jobs(4))
                write_phase(d.folder('pilot')/'native8',d.pilot_jobs(8),failed=True)
                with self.assertRaisesRegex(ValueError,'Fatal lower-load'):d.pilot_phase_gate('native16')
                self.assertTrue(d.pilot_phase_gate('ollama3'))
                write_phase(d.folder('pilot')/'native16',d.pilot_jobs(16))
                with self.assertRaisesRegex(ValueError,'cannot be followed'):d.pilot_phase_gate('ollama3')

    def test_eligible_backoff_persists_across_phase_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(d,'ROOT',Path(directory)),patch.object(d,'dispatch_time_gate',return_value=True):
                until=time.time()+.05;d.persist_cooldown(until)
                d.persist_cooldown(until-10)
                d.capacity_cooldown()
                self.assertGreaterEqual(time.time(),until)
                checkpoint=Path(directory)/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
                self.assertEqual(s.read(checkpoint)['not_before_epoch'],until)

    def test_deadline_infeasible_forecast_cannot_select(self):
        value=forecast_fixture();value['generated_at']='2026-11-09T05:50:00+00:00'
        with (patch.object(d,'op_freeze',return_value=Path('pilot')),
              patch.object(d,'sha',side_effect=lambda path:'pilot-hash' if str(path)=='pilot' else s.sha(path))):
            result=d.validate_forecast(value)
            self.assertFalse(any(x['deadline_feasible'] for x in result['candidates']))


class V2CorrectionTests(unittest.TestCase):
    def test_gateway_forecast_gate_replays_counts_and_selects_feasible_alternative(self):
        value=forecast_fixture();bad=value['candidates'][1];phase=bad['phase_bounds'][5]
        phase['projected_known_transient_terminals']['adaption']='1200';phase['projected_known_transient_total']='1200'
        with (patch.object(d,'op_freeze',return_value=Path('pilot')),
              patch.object(d,'sha',side_effect=lambda path:'pilot-hash' if str(path)=='pilot' else s.sha(path))):
            with self.assertRaisesRegex(ValueError,'gateway allowance flag'):d.validate_forecast(deepcopy(value))
            bad['gateway_allowance_feasible']=False
            checked=d.validate_forecast(deepcopy(value))
            self.assertTrue(checked['candidates'][1]['deadline_feasible'])
            metadata={'native_candidates':[{'level':level,'eligible':True} for level in (4,8)],'selected_ollama_per_model':3,'ollama_pilot':None}
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'forecast.json';selection=Path(directory)/'selection.json';path.write_text(json.dumps(value))
                with patch.object(d,'SELECTION',selection),patch.object(d,'verify',return_value={}),patch.object(d,'pilot_metadata',side_effect=lambda:deepcopy(metadata)):
                    result=d.select(path);self.assertEqual(result['selected_native_per_model'],4)
                    tampered=deepcopy(result);tampered['selected_native_per_model']=8
                    with self.assertRaisesRegex(ValueError,'throughput selection'):d.validate_selection(tampered)
                    selection.unlink();safe=value['candidates'][0];safe['gateway_allowance_feasible']=False
                    safe['phase_bounds'][5]['projected_known_transient_terminals']['adaption']='1200';safe['phase_bounds'][5]['projected_known_transient_total']='1200'
                    path.write_text(json.dumps(value))
                    with self.assertRaisesRegex(ValueError,'No healthy'):d.select(path)

    def test_native_bounded_output_is_serving_healthy_but_not_scientifically_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);job=d.pilot_jobs(4)[0];row=native_row(out,job)
            path=out/'native'/(s.digest(job['id'])+'.json');receipt=json.loads(path.read_text())
            receipt['native_response'].update(status='incomplete',incomplete_details={'reason':'max_output_tokens'})
            receipt['native_response']['usage']['output_tokens']=4096
            path.write_text(json.dumps(receipt));row['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            row['response'],row['known_usage'],row['anomaly']=s.normalize(receipt['native_response'],s.profile(job['profile_id']))
            self.assertFalse(s.admitted(row));self.assertTrue(d.serving_healthy(row,out))
            self.assertFalse(d.serving_healthy(row))
            for reason in ('other',None):
                receipt['native_response']['incomplete_details']={'reason':reason};path.write_text(json.dumps(receipt));row['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertFalse(d.serving_healthy(row,out))
            row['response']['usage']['output_tokens']=4095;self.assertFalse(d.serving_healthy(row,out))
            row['response']['status']='completed';row['response']['returned_model']='wrong-model';self.assertFalse(d.serving_healthy(row,out))
            olla=native_row(out,d.ollama_pilot_jobs()[0]);olla['response']['status']='incomplete';olla['response']['usage']['output_tokens']=4096
            self.assertFalse(d.serving_healthy(olla,out))

    def test_prospective_native_gateway_wait_does_not_relax_other_errors(self):
        native={'profile_id':'q397','transport':{'http_status':504}}
        for status in (502,503,504):
            native['transport']['http_status']=status;self.assertEqual(d.gateway_backoff_seconds(native),15)
        native['transport'].update(http_status=429,service_overload=True)
        self.assertEqual(d.gateway_backoff_seconds(native),60)
        for identity in ('ds_off','hf_text'):
            self.assertEqual(d.gateway_backoff_seconds({'profile_id':identity,'transport':{'http_status':504}}),60)
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);row=native_row(out,d.pilot_jobs(4)[0],504)
            path=out/'native'/(s.digest(row['id'])+'.json');receipt=s.read(path);receipt['headers']={'Retry-After':'120'}
            path.write_text(json.dumps(receipt));row['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(max(d.gateway_backoff_seconds(row),d.retry_after_delay(row,out)),120)

    def test_pid_reuse_requires_creation_after_final_driver_timestamp(self):
        import subprocess
        stamp='2026-11-07T16:00:00+00:00'
        with patch.object(d.os,'name','nt'):
            for created,allowed in (('2026-11-07T17:00:00+00:00',True),('2026-11-07T15:00:00+00:00',False)):
                result=subprocess.CompletedProcess([],0,stdout=created.encode(),stderr=b'')
                with patch.object(d.subprocess,'run',return_value=result):
                    if allowed:self.assertTrue(d.process_dead(123,stamp))
                    else:
                        with self.assertRaises(ValueError):d.process_dead(123,stamp)
                    with self.assertRaises(ValueError):d.process_dead(123)

    def test_shared_pilot_budget_carries_both_providers_across_namespaces(self):
        baseline=d.prior_public_baseline();baseline=deepcopy(baseline)
        baseline['estimated_cost_by_provider']={'adaption':'0.18','hf':'0','ollama':'0.01'}
        with patch.object(d,'verify_prior_pilot_private',return_value=baseline),patch.object(d,'_sum_cost',side_effect=lambda paths,provider:Decimal('0.02')):
            costs=d.pilot_cost_metadata()
            self.assertEqual(Decimal(costs['estimated_cost_by_provider']['adaption']),Decimal('.20'))
            self.assertEqual(Decimal(costs['estimated_cost_by_provider']['ollama']),Decimal('.03'))
        self.assertFalse({j['id'] for j in d.pilot_jobs(4)} & {j['id'] for j in d.v1.pilot_jobs(4)})


class DispatchCollectorTests(unittest.TestCase):
    def setUp(self):
        self.history=patch.object(d,'verify_prior_pilot_private',return_value={'estimated_cost_by_provider':{'adaption':'0.18300835','hf':'0','ollama':'0'}})
        self.history.start();self.addCleanup(self.history.stop)

    def test_tolerated_final_pilot_response_persists_requested_cooldown(self):
        jobs=d.pilot_jobs(4);bad=jobs[0]['id']
        class Fake:
            def __init__(self):self.lock=threading.Lock();self.count=0;self.all_started=threading.Event()
            def request(self,job):
                with self.lock:
                    self.count+=1
                    if self.count==len(jobs):self.all_started.set()
                if job['id']==bad:
                    if not self.all_started.wait(5):raise AssertionError('All pilot requests should be assigned')
                out=d.folder('pilot')/'native4';result=native_row(out,job,503 if job['id']==bad else 200)
                if job['id']==bad:
                    path=out/'native'/(s.digest(job['id'])+'.json');receipt=s.read(path);receipt['headers']={'Retry-After':'120'}
                    path.write_text(json.dumps(receipt));result['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                return result
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}')
            with (patch.object(d,'ROOT',root),patch.object(d,'SOURCES',()),patch.object(d,'registration',return_value={}),
                  patch.object(d,'check_metadata'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'capacity_cooldown')):
                self.assertTrue(d.execute(jobs,'pilot','native4',Fake())['complete'])
                checkpoint=root/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
                self.assertGreater(s.read(checkpoint)['not_before_epoch']-time.time(),115)
                terminal=s.rows(d.folder('pilot')/'native4/responses.jsonl')
                self.assertTrue(d.native_health(jobs,terminal)[0])
                self.assertFalse((d.folder('pilot')/'native4/stop.json').exists())

    def test_budget_denial_precedes_any_provider_send(self):
        cfg=d.config();cfg['pilot_caps']['adaption']='0.0000001'
        class Fake:
            calls=0
            def request(self,_):self.calls+=1;raise AssertionError('Over-budget request sent')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}');fake=Fake()
            with (patch.object(d,'ROOT',root),patch.object(d,'SOURCES',()),patch.object(d,'config',return_value=cfg),
                  patch.object(d,'registration',return_value={}),patch.object(d,'check_metadata'),
                  patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'capacity_cooldown')):
                with self.assertRaisesRegex(ValueError,'cost cap'):d.execute(d.pilot_jobs(4),'pilot','native4',fake)
                self.assertEqual(fake.calls,0)
                self.assertFalse((d.folder('pilot')/'native4/attempts.jsonl').exists())

    def test_cutoff_guard_drains_existing_requests_before_stop(self):
        jobs=d.pilot_jobs(4)
        class Fake:
            calls=0
            def request(self,job):
                self.calls+=1;time.sleep(.02);return native_row(d.folder('pilot')/'native4',job)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}');fake=Fake()
            with (patch.object(d,'ROOT',root),patch.object(d,'SOURCES',()),patch.object(d,'registration',return_value={}),
                  patch.object(d,'check_metadata'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'capacity_cooldown'),
                  patch.object(d,'dispatch_time_gate',side_effect=[True]*4+[ValueError('cutoff reached')])):
                with self.assertRaisesRegex(ValueError,'cutoff reached'):d.execute(jobs,'pilot','native4',fake)
                starts,terminal=s.ledger(d.folder('pilot')/'native4',jobs)
                self.assertEqual(len(starts),4);self.assertEqual(len(terminal),4);self.assertEqual(fake.calls,4)
                self.assertTrue((d.folder('pilot')/'native4/stop.json').exists())

    def test_no_registration_no_request(self):
        class Fake:
            def request(self,_):raise AssertionError('Unregistered dispatch attempted')
        with tempfile.TemporaryDirectory() as directory:
            with (patch.object(d,'ROOT',Path(directory)),patch.object(d,'SOURCES',()),
                  patch.object(d,'registration',side_effect=ValueError('Registration missing'))):
                with self.assertRaisesRegex(ValueError,'Registration missing'):d.execute(d.pilot_jobs(4),'pilot','native4',Fake())

    def test_unknown_send_blocks_new_phase_without_retry(self):
        class Fake:
            calls=0
            def request(self,_):self.calls+=1;raise OSError('sensitive fixture text must not be recorded')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}');fake=Fake()
            with (patch.object(d,'ROOT',root),patch.object(d,'SOURCES',()),patch.object(d,'registration',return_value={}),
                  patch.object(d,'check_metadata'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'capacity_cooldown')):
                with self.assertRaisesRegex(ValueError,'Collector stopped'):d.execute(d.pilot_jobs(4)[:1],'pilot','native4',fake)
                with self.assertRaisesRegex(ValueError,'Unknown started|unresolved'):d.execute(d.ollama_pilot_jobs(),'pilot','ollama3',fake)
                self.assertEqual(fake.calls,1)
                errors=s.rows(d.folder('pilot')/'native4/capture-failures.jsonl')
                self.assertEqual(errors,[{'id':d.pilot_jobs(4)[0]['id'],'error_class':'OSError'}])

    def test_main_cap_extension_changes_local_guard_not_rates_or_science(self):
        original=s.config();choice={'selected_native_per_model':8,'selected_ollama_per_model':3,'ollama_combined_peak_cap':'100.00'}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'selection.json';path.write_text('{}')
            with patch.object(d,'SELECTION',path),patch.object(d,'validate_selection',return_value=choice):
                changed=d.execution_config('main','readers')
            self.assertEqual(Decimal(changed['combined_caps']['ollama']),Decimal('100'))
            self.assertEqual(Decimal(changed['phase_caps']['main']['ollama']),Decimal('99.70'))
            self.assertEqual(changed['native_class_caps'],original['native_class_caps'])
            self.assertEqual(changed['gateway_allowance'],1024)
            self.assertEqual(d.execution_config('pilot','native4')['gateway_allowance'],2)
            self.assertEqual(d.execution_config('pilot','ollama3')['gateway_allowance'],0)
            self.assertEqual(original['gateway_allowance'],256)
            self.assertEqual(s.profile('ds_low')['input_rate'],'0.30')
            self.assertEqual(s.profile('ds_low')['output_rate'],'1.20')
            self.assertEqual(s.config(),original)

    def test_pilot_preserves_reservation_and_does_not_gate_json_accuracy(self):
        jobs=d.pilot_jobs(4)
        class Fake:
            def __init__(self):self.lock=threading.Lock();self.active=0;self.maximum=0;self.calls=0;self.by_profile={};self.profile_max={}
            def request(self,job):
                with self.lock:
                    self.active+=1;self.maximum=max(self.maximum,self.active);self.calls+=1
                    identity=job['profile_id'];self.by_profile[identity]=self.by_profile.get(identity,0)+1
                    self.profile_max[identity]=max(self.profile_max.get(identity,0),self.by_profile[identity])
                out=d.folder('pilot')/'native4'
                assert job['id'] in {r['id'] for r in s.rows(out/'attempts.jsonl')}
                time.sleep(.01);result=native_row(out,job)
                with self.lock:self.active-=1;self.by_profile[identity]-=1
                return result
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}');fake=Fake()
            with (patch.object(d,'ROOT',root),patch.object(d,'SOURCES',()),patch.object(d,'registration',return_value={}),
                  patch.object(d,'check_metadata'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'capacity_cooldown')):
                first=d.execute(jobs,'pilot','native4',fake)
                self.assertTrue(first['complete']);self.assertEqual(first['terminal'],64)
                self.assertLessEqual(fake.maximum,8);self.assertGreaterEqual(fake.maximum,2)
                self.assertTrue(all(n<=4 for n in fake.profile_max.values()))
                self.assertTrue(d.execute(jobs,'pilot','native4',fake)['complete'])
                self.assertEqual(fake.calls,64)
                self.assertTrue(all(r['response']['output_text']=='not a verdict' for r in s.rows(d.folder('pilot')/'native4/responses.jsonl')))

    def test_client_native_spacing_persists_between_instances(self):
        class Reply:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,*_):return json.dumps({'status':'completed','model':'qwen3.5-397b','output_text':'x','usage':{'input_tokens':10,'output_tokens':5}}).encode()
        class Opener:
            def open(self,*_,**__):return Reply()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(d,'ROOT',root):
                a=root/'a';b=root/'b';a.mkdir();b.mkdir()
                d.PacedTransport({'ADAPTION_API_KEY':'fixture-only'},a,Opener()).request(d.pilot_jobs(4)[0])
                d.PacedTransport({'ADAPTION_API_KEY':'fixture-only'},b,Opener()).request(d.pilot_jobs(4)[1])
                first=s.rows(a/'dispatch-events.jsonl')[0]['epoch'];second=s.rows(b/'dispatch-events.jsonl')[0]['epoch']
                self.assertGreaterEqual(second-first,.999)


if __name__=='__main__':unittest.main()
