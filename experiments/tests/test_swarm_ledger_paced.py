"""Offline regressions for immutable-prefix, no-retry MAIN continuation."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments import swarm_ledger_paced as r
from experiments.tests.test_swarm_ledger_complete_dispatch import fake_job,native_row,execution_fixture


def make_job(identity):
    value=fake_job();value['id']=identity;return value


def write_phase(out,jobs,registration,terminals):
    out.mkdir(parents=True,exist_ok=True)
    ordered=sorted(jobs,key=lambda j:j['id'])
    (out/'plan.json').write_text(json.dumps(dict(jobs_sha256=r.digest(ordered),ids=[j['id'] for j in ordered],freeze_sha256=r.s.sha(registration))))
    for job,http in terminals:
        row=native_row(out,job,http)
        r.s.durable(out/'attempts.jsonl',dict(id=job['id'],profile_id=job['profile_id'],request_sha256=r.digest(r.s.body_for(job)),reserved_cost=str(r.s.reservation(job)),started='2026-11-08T00:00:00+00:00'))
        r.s.durable(out/'responses.jsonl',row)


class UnionTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.old=self.root/'old-freeze.json';self.old.write_text('{}');self.v1=self.root/'v1-freeze.json';self.v1.write_text('{"v1":true}');self.v2=self.root/'v2-freeze.json';self.v2.write_text('{"v2":true}');self.v3=self.root/'v3-freeze.json';self.v3.write_text('{"v3":true}');self.v4=self.root/'v4-freeze.json';self.v4.write_text('{"v4":true}');self.v5=self.root/'v5-freeze.json';self.v5.write_text('{"v5":true}');self.new=self.root/'new-freeze.json';self.new.write_text('{"new":true}')
        self.patches=[patch.object(r,'ROOT',self.root),patch.object(r,'FREEZE',self.new),patch.object(r.s,'freeze_path',return_value=self.old),patch.object(r.prior,'FREEZE',self.v1),patch.object(r.second,'FREEZE',self.v2),patch.object(r.third,'FREEZE',self.v3),patch.object(r.fourth,'FREEZE',self.v4),patch.object(r.fifth,'FREEZE',self.v5)]
        for p in self.patches:p.start()
        self.jobs=[make_job('old-failed'),make_job('new-good')]
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temporary.cleanup()
    def test_union_retains_failed_original_full_reservation(self):
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],504)])
        write_phase(r.folder('reporter'),self.jobs,self.new,[(self.jobs[1],200)])
        rows,coverage=r.union_phase('reporter',self.jobs)
        self.assertEqual(coverage,dict(planned=2,started=2,terminal=2,unstarted=0,unknown_usage=1,complete=True))
        self.assertEqual(rows[0]['estimated_cost'],str(r.s.reservation(self.jobs[0])))
        self.assertEqual(rows[0]['transport']['http_status'],504)
    def test_pending_is_unstarted_not_unsuccessful(self):
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],504)])
        self.assertEqual([j['id'] for j in r.pending_jobs('reporter',self.jobs)],['new-good'])
        with self.assertRaisesRegex(ValueError,'incomplete'):r.union_phase('reporter',self.jobs)
    def test_duplicate_send_across_journals_rejected(self):
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],200)])
        write_phase(r.folder('reporter'),self.jobs,self.new,[(self.jobs[0],200)])
        with self.assertRaisesRegex(ValueError,'Repeated'):r.union_phase('reporter',self.jobs,False)
    def test_changed_body_or_native_bytes_rejected(self):
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],200)])
        changed=deepcopy(self.jobs);changed[0]['messages'][0]['content']+='changed'
        with self.assertRaisesRegex(ValueError,'plan/body'):r.union_phase('reporter',changed,False)
        native=next((r.original_folder('reporter')/'native').glob('*.json'));native.write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt hash'):r.union_phase('reporter',self.jobs,False)
    def test_unresolved_start_blocks_union(self):
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],200)])
        (r.original_folder('reporter')/'responses.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError,'Unknown started'):r.union_phase('reporter',self.jobs,False)
    def test_original_snapshot_commits_native_and_metadata_separately(self):
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],200)])
        state=self.root/'runs/swarm-ledger-v1-main-driver/state.json';state.parent.mkdir();state.write_text('{"status":"stopped"}')
        priorstate=self.root/'runs/swarm-ledger-resume-v1-driver/state.json';priorstate.parent.mkdir();priorstate.write_text('{"status":"stopped"}')
        secondstate=self.root/'runs/swarm-ledger-resume-v2-driver/state.json';secondstate.parent.mkdir();secondstate.write_text('{"status":"stopped"}')
        thirdstate=self.root/'runs/swarm-ledger-resume-v3-driver/state.json';thirdstate.parent.mkdir();thirdstate.write_text('{"status":"stopped"}')
        fourthstate=self.root/'runs/swarm-ledger-efficient-v1-driver/state.json';fourthstate.parent.mkdir();fourthstate.write_text('{"status":"stopped"}')
        fifthstate=self.root/'runs/swarm-ledger-rate-v1-driver/state.json';fifthstate.parent.mkdir();fifthstate.write_text('{"status":"stopped"}')
        before=r.snapshot_prefix();native=next((r.original_folder('reporter')/'native').glob('*.json'));native.write_text('{}')
        after=r.snapshot_prefix()
        self.assertEqual(before['metadata_sha256'],after['metadata_sha256'])
        self.assertNotEqual(before['native_inventory_sha256'],after['native_inventory_sha256'])
    def test_costs_include_original_new_and_engineering_once(self):
        def cost(path,value):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(dict(profile_id='g26',estimated_cost=str(value),metadata={'stage':'reporter'}))+'\n')
        cost(r.original_folder('reporter')/'responses.jsonl',2)
        cost(r.folder('reporter')/'responses.jsonl',3)
        cost(self.root/'runs/swarm-ledger-v1-development/reporter/responses.jsonl',5)
        with patch.object(r.d,'pilot_spending_paths',return_value=[]):combined,main,classes=r.cost_baseline()
        self.assertEqual(combined['adaption'],Decimal(10));self.assertEqual(main['adaption'],Decimal(5));self.assertEqual(classes['actors'],Decimal(5))
    def test_connection_failure_is_retained_once_and_only_unstarted_continue(self):
        self.jobs=[make_job(x) for x in ('old-failed','new-connection','new-good','new-later')]
        write_phase(r.original_folder('reporter'),self.jobs,self.old,[(self.jobs[0],504)])
        original=(r.original_folder('reporter')/'responses.jsonl').read_bytes()
        class Gate:
            healthy=False;failures=0;checks=0
            def before_dispatch(self,**kwargs):self.checks+=1;self.healthy=True
            def dispatch_allowed(self):return self.healthy
            def connection_failed(self):self.failures+=1;self.healthy=False
        class Transport:
            calls=[]
            def request(self,job):
                self.calls.append(job['id']);out=r.folder('reporter')
                row=native_row(out,job,None if job['id']=='new-connection' else 200)
                if job['id']=='new-connection':row['transport']['connection_fault']=True
                return row
        gate=Gate();transport=Transport();cfg=execution_fixture();cfg['metadata_recheck_calls']=100000
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]):
            result=r._execute('reporter',self.jobs,transport,gate)
        self.assertTrue(result['complete']);self.assertEqual(result['terminal'],4)
        self.assertEqual(sorted(transport.calls),['new-connection','new-good','new-later']);self.assertEqual(len(transport.calls),3)
        self.assertEqual(gate.failures,1);self.assertGreaterEqual(gate.checks,2)
        self.assertEqual((r.original_folder('reporter')/'responses.jsonl').read_bytes(),original)
        allrows,_=r.union_phase('reporter',self.jobs)
        failed=next(row for row in allrows if row['id']=='new-connection')
        self.assertFalse(failed['known_usage']);self.assertEqual(Decimal(failed['estimated_cost']),r.s.reservation(next(j for j in self.jobs if j['id']=='new-connection')))
    def test_unclassified_parse_failure_stops_without_resending(self):
        self.jobs=[make_job('new-parse')]
        class Gate:
            def before_dispatch(self,**kwargs):pass
            def dispatch_allowed(self):return True
            def connection_failed(self):raise AssertionError('Parse failure must not be classified as connectivity')
        class Transport:
            calls=0
            def request(self,job):self.calls+=1;return native_row(r.folder('reporter'),job,None)
        transport=Transport();cfg=execution_fixture()
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]):
            with self.assertRaisesRegex(ValueError,'Continuation stopped'):r._execute('reporter',self.jobs,transport,Gate())
        self.assertEqual(transport.calls,1);self.assertTrue((r.folder('reporter')/'stop.json').exists())
    def test_http503_capture_failure_is_fatal_even_when_capacity_class_matches(self):
        self.jobs=[make_job('capture-failed')]
        class Gate:
            def before_dispatch(self,**kwargs):pass
            def dispatch_allowed(self):return True
            def connection_failed(self):raise AssertionError('Capture failure is fatal')
        class Transport:
            calls=0
            def request(self,job):
                self.calls+=1;row=native_row(r.folder('reporter'),job,503)
                row['transport']['capture_failed']=True;return row
        transport=Transport();cfg=execution_fixture()
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]),patch.object(r.d,'persist_cooldown'):
            with self.assertRaisesRegex(ValueError,'Continuation stopped'):r._execute('reporter',self.jobs,transport,Gate())
        self.assertEqual(transport.calls,1);self.assertTrue((r.folder('reporter')/'stop.json').exists())

    def test_three_archive_union_retains_500_and_complement(self):
        self.jobs=[make_job(x) for x in ('old-good','v1-500','v2-good')]
        write_phase(r.original_folder('readers'),self.jobs,self.old,[(self.jobs[0],200)])
        write_phase(r.prior_folder('readers'),self.jobs,self.v1,[(self.jobs[1],500)])
        self.assertEqual([j['id'] for j in r.pending_jobs('readers',self.jobs)],['v2-good'])
        write_phase(r.folder('readers'),self.jobs,self.new,[(self.jobs[2],200)])
        values,coverage=r.union_phase('readers',self.jobs)
        self.assertTrue(coverage['complete']);self.assertEqual(coverage['unknown_usage'],1)
        failed=next(x for x in values if x['id']=='v1-500')
        self.assertEqual(Decimal(failed['estimated_cost']),r.s.reservation(self.jobs[1]))
        self.assertEqual(failed['transport']['http_status'],500)

    def test_duplicate_v1_v2_rejected(self):
        write_phase(r.prior_folder('readers'),self.jobs,self.v1,[(self.jobs[0],500)])
        write_phase(r.folder('readers'),self.jobs,self.new,[(self.jobs[0],200)])
        with self.assertRaisesRegex(ValueError,'Repeated'):r.union_phase('readers',self.jobs,False)

    def test_prior_archive_costs_count_once_including_unknown_reservation(self):
        write_phase(r.prior_folder('readers'),self.jobs,self.v1,[(self.jobs[0],500)])
        with patch.object(r.d,'pilot_spending_paths',return_value=[]):combined,main,classes=r.cost_baseline()
        self.assertEqual(combined['adaption'],r.s.reservation(self.jobs[0]))
        self.assertEqual(main['adaption'],r.s.reservation(self.jobs[0]))

    def test_500_recovery_never_reissues_and_rechecks_health(self):
        self.jobs=[make_job(x) for x in ('new-500','new-good')]
        class Gate:
            healthy=False; failures=0; checks=0
            def before_dispatch(self,**kwargs):self.checks+=1;self.healthy=True
            def dispatch_allowed(self):return self.healthy
            def connection_failed(self):self.failures+=1;self.healthy=False
        class Transport:
            def __init__(self):self.calls=[]
            def request(self,job):self.calls.append(job['id']);return native_row(r.folder('readers'),job,500 if job['id']=='new-500' else 200)
        transport=Transport();gate=Gate();cfg=execution_fixture();cfg['metadata_recheck_calls']=100000
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]),patch.object(r,'server_error_delay',return_value=0),patch.object(r.d,'persist_cooldown'):
            result=r._execute('readers',self.jobs,transport,gate)
        self.assertTrue(result['complete']);self.assertEqual(sorted(transport.calls),['new-500','new-good'])
        self.assertEqual(gate.failures,1)
        values,_=r.union_phase('readers',self.jobs)
        failed=next(x for x in values if x['id']=='new-500')
        self.assertEqual(Decimal(failed['estimated_cost']),r.s.reservation(self.jobs[0]))

    def test_retained_500_allowance_exhaustion_stops_before_send(self):
        write_phase(r.prior_folder('readers'),self.jobs,self.v1,[(self.jobs[0],500)])
        class Gate:
            def before_dispatch(self,**kwargs):pass
        class Transport:
            def request(self,job):raise AssertionError('No send allowed')
        cfg=execution_fixture();limited=dict(r.policy,max_server500_failures=0)
        with patch.object(r,'policy',limited),patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'pilot_spending_paths',return_value=[]):
            with self.assertRaisesRegex(ValueError,'allowance exhausted'):r._execute('readers',self.jobs,Transport(),Gate())

    def test_500_cooldown_and_retry_after_parser_are_bounded(self):
        job=self.jobs[0];out=r.folder('readers');row=native_row(out,job,500)
        self.assertEqual(r.server_error_delay(row,out),60)
        path=out/'native'/(r.digest(job['id'])+'.json')
        path.write_text(json.dumps({'headers':{'Retry-After':'120'}}))
        self.assertEqual(r.server_error_delay(row,out),120)
        path.write_text(json.dumps({'headers':{'Retry-After':'999999'}}))
        with self.assertRaisesRegex(ValueError,'bound'):r.server_error_delay(row,out)
        self.assertEqual(row['transport']['http_status'],500)


    def test_500_known_usage_is_fatal_even_without_anomaly_flag(self):
        self.jobs=[make_job('bad-known500')]
        class Gate:
            def before_dispatch(self,**kwargs):pass
            def dispatch_allowed(self):return True
            def connection_failed(self):pass
        class Transport:
            def request(self,job):
                row=native_row(r.folder('readers'),job,200)
                row['transport']['http_status']=500;row['anomaly']=False
                return row
        cfg=execution_fixture()
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]),patch.object(r,'server_error_delay',return_value=0),patch.object(r.d,'persist_cooldown'):
            with self.assertRaisesRegex(ValueError,'Continuation stopped'):r._execute('readers',self.jobs,Transport(),Gate())

    def test_500_pauses_unstarted_until_new_health_cycle(self):
        self.jobs=[make_job(x) for x in ('a500','bgood')]
        events=[]
        class Gate:
            healthy=False
            def before_dispatch(self,**kwargs):events.append('healthy');self.healthy=True
            def dispatch_allowed(self):return self.healthy
            def connection_failed(self):events.append('pause');self.healthy=False
        class Transport:
            def request(self,job):
                events.append(job['id'])
                return native_row(r.folder('readers'),job,500 if job['id']=='a500' else 200)
        cfg=execution_fixture();cfg['provider_max_active']['adaption']=1
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]),patch.object(r,'server_error_delay',return_value=0),patch.object(r.d,'persist_cooldown'):
            self.assertTrue(r._execute('readers',self.jobs,Transport(),Gate())['complete'])
        self.assertEqual(events,['healthy','a500','pause','healthy','bgood'])

    def test_provider_cap_stops_before_any_send(self):
        self.jobs=[make_job('unaffordable')]
        class Gate:
            def before_dispatch(self,**kwargs):pass
            def dispatch_allowed(self):return True
        class Transport:
            def request(self,job):raise AssertionError('Cap must precede inference')
        cfg=execution_fixture();cfg['phase_caps']['main']['adaption']='0'
        with patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata'),patch.object(r.d,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]):
            with self.assertRaisesRegex(ValueError,'Provider MAIN cost cap'):r._execute('readers',self.jobs,Transport(),Gate())
        self.assertFalse((r.folder('readers')/'attempts.jsonl').exists())


    def test_four_batch_union_exact_remaining_and_no_reissued_ids(self):
        self.jobs=[make_job(name) for name in ('a','b','c','d')]
        for out,registration,job,status in ((r.original_folder('readers'),self.old,self.jobs[0],200),(r.prior_folder('readers'),self.v1,self.jobs[1],500),(r.second_folder('readers'),self.v2,self.jobs[2],504)):
            write_phase(out,self.jobs,registration,[(job,status)])
        self.assertEqual([job['id'] for job in r.pending_jobs('readers',self.jobs)],['d'])
        write_phase(r.folder('readers'),self.jobs,self.new,[(self.jobs[3],200)])
        values,coverage=r.union_phase('readers',self.jobs)
        self.assertTrue(coverage['complete']);self.assertEqual(len(values),4);self.assertEqual(coverage['unknown_usage'],2)
        write_phase(r.folder('calibration'),self.jobs,self.new,[(self.jobs[0],200)])
        write_phase(r.second_folder('calibration'),self.jobs,self.v2,[(self.jobs[0],200)])
        with self.assertRaisesRegex(ValueError,'Repeated'):r.union_phase('calibration',self.jobs,False)



class BuilderAndTransportTests(unittest.TestCase):
    def test_reader_jobs_use_full_authentic_actor_union(self):
        roles=[];previous_seen=[]
        def actor(role,ctx,previous):roles.append(role);return [{'id':role}]
        def union(role,jobs,require_complete):return ([{'id':role,'marker':'retained:'+role}],{'complete':True})
        def worlds(ctx,previous):previous_seen.append(previous.copy());return ['world']
        with patch.object(r.s,'contexts',return_value=['context']),patch.object(r,'read',return_value={'contexts_sha256':r.digest(['context'])}),patch.object(r.s,'actor_jobs',side_effect=actor),patch.object(r,'union_phase',side_effect=union),patch.object(r.s,'source_worlds',side_effect=worlds),patch.object(r.s,'reader_jobs',return_value=['exact-reader-job']):
            self.assertEqual(r.main_jobs('readers'),['exact-reader-job'])
        self.assertEqual(roles,list(r.ROLES));self.assertEqual(set(previous_seen[0]),set(r.ROLES));self.assertEqual(previous_seen[0]['reporter']['marker'],'retained:reporter')
    def test_safe_transport_sends_once_with_frozen_body_and_codec(self):
        class Reply:
            status=200;headers={'Content-Type':'application/json'}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return json.dumps({'model':r.s.profile('g26')['model'],'status':'completed','output_text':'not a verdict','usage':{'input_tokens':10,'output_tokens':5}}).encode()
        class Opener:
            calls=0;data=None
            def open(self,req,**kwargs):self.calls+=1;self.data=req.data;return Reply()
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);opener=Opener();job=make_job('single-send')
            with patch.object(r,'ROOT',out):result=r.ResumeTransport({'ADAPTION_API_KEY':'fixture-only'},out,opener).request(job)
            self.assertEqual(opener.calls,1);self.assertEqual(json.loads(opener.data),r.s.body_for(job))
            receipt=r.read(out/'native'/(r.digest(job['id'])+'.json'))
            response,known,anomaly=r.s.normalize(receipt['native_response'],r.s.profile('g26'))
            self.assertEqual((result['response'],result['known_usage'],result['anomaly']),(response,known,anomaly))
            self.assertNotIn('fixture-only',json.dumps(receipt));self.assertEqual(result['native_receipt_sha256'],r.raw_sha(out/'native'/(r.digest(job['id'])+'.json')))
    def test_metadata_probe_does_not_accept_missing_catalog(self):
        class Transport:
            keys={'ADAPTION_API_KEY':'fixture','HF_TOKEN':'fixture','OLLAMA_API_KEY':'fixture'}
            opener=object()
        with patch.object(r.connectivity,'safe_request',return_value=({'connection_fault':True},None,{})):
            self.assertFalse(r.connectivity_probe(Transport()))
        with patch.object(r.connectivity,'safe_request',return_value=({'http_status':401},None,{})):
            with self.assertRaisesRegex(ValueError,'authentication'):r.connectivity_probe(Transport())
    def test_remaining_forecast_refuses_failed_or_late_gate(self):
        value=dict(schema_version=1,deadline_feasible=True,budget_feasible=True,off_peak_wallet_gate_passed=True,
                   collection_cutoff_utc=r.policy['cutoff_utc'],forecast_seconds=100,pacing_minima_seconds={'native_global':'1.6','native_model':'3.2'})
        at=datetime(2026,11,8,tzinfo=timezone.utc);self.assertEqual(r.validate_resume_forecast(value,at),value)
        for key in ('deadline_feasible','budget_feasible','off_peak_wallet_gate_passed'):
            bad=deepcopy(value);bad[key]=False
            with self.assertRaisesRegex(ValueError,'gate failed'):r.validate_resume_forecast(bad,at)
        with self.assertRaisesRegex(ValueError,'no longer fits'):r.validate_resume_forecast(value,datetime.fromisoformat(r.policy['cutoff_utc'])-timedelta(minutes=1))


class AvailabilityTests(unittest.TestCase):
    def envelope(self,message='Engine overloaded, try later',**changes):
        error=dict(type='invalid_request_error',code='engine_overloaded',param=None,message=message)
        error.update(changes);return {'error_body':json.dumps({'error':error})}
    def test_hf_overload_exact_schema_not_rate_funding_or_unknown(self):
        status={'http_status':429}
        self.assertTrue(r.hf_engine_overloaded(status,self.envelope()))
        self.assertTrue(r.hf_engine_overloaded(status,self.envelope('Engine busy, retry later')))
        self.assertEqual(r.availability_class(status,self.envelope(),'hf'),'hf_engine_overloaded')
        self.assertIsNone(r.availability_class(status,self.envelope(),'ollama'))
        for text in ('Billing overloaded','Engine overloaded: insufficient credits','Engine overloaded quota','Engine overloaded rate limit','Unknown error'):
            self.assertFalse(r.hf_engine_overloaded(status,self.envelope(text)))
        for change in ({'code':'insufficient_quota'},{'type':'rate_limit_error'},{'param':'token_limit'}):
            self.assertFalse(r.hf_engine_overloaded(status,self.envelope(**change)))
        for status in ({'http_status':200},{'http_status':429,'capture_failed':True},{'http_status':429,'connection_fault':True}):
            self.assertFalse(r.hf_engine_overloaded(status,self.envelope()))
    def test_new_transport_overload_classifies_without_post_retry(self):
        from urllib.error import HTTPError
        from io import BytesIO
        body=self.envelope()['error_body'].encode()
        class Opener:
            calls=0
            def open(self,request,**kwargs):
                self.calls+=1
                raise HTTPError(request.full_url,429,'fixture',{},BytesIO(body))
        with tempfile.TemporaryDirectory() as directory:
            job=make_job('hf429fixture');job['profile_id']='hf_schema';opener=Opener()
            row=r.ResumeTransport({'HF_TOKEN':'fixture-only'},Path(directory),opener).request(job)
            self.assertEqual(opener.calls,1);self.assertFalse(row['known_usage'])
            self.assertEqual(row['transport']['provider_failure_class'],'hf_engine_overloaded')
            self.assertTrue(r.known_server_error(row))
            self.assertNotIn('fixture-only',json.dumps(row))

    def test_two_historical_busy_envelopes_classify_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            values=[]
            for name in ('first-failure','second-failure'):
                path=r.second_folder('readers')/'native'/(r.digest(name)+'.json');path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(self.envelope('Engine busy, retry later')))
                values.append((path,path.read_bytes(),dict(id=name,profile_id='hf_schema',native_receipt_sha256=r.raw_sha(path),transport={'http_status':429})))
            self.assertEqual(sum(r.historical_hf_overload(row) for _,_,row in values),2)
            self.assertTrue(all(path.read_bytes()==before for path,before,_ in values))

    def test_new_500_funding_error_is_not_availability(self):
        from urllib.error import HTTPError
        from io import BytesIO
        class Opener:
            calls=0
            def open(self,request,**kwargs):
                self.calls+=1
                raise HTTPError(request.full_url,500,'fixture',{},BytesIO(b'{"error":"insufficient credits"}'))
        with tempfile.TemporaryDirectory() as directory:
            job=make_job('funding500');job['profile_id']='hf_schema';opener=Opener()
            row=r.ResumeTransport({'HF_TOKEN':'fixture-only'},Path(directory),opener).request(job)
            self.assertTrue(row['transport']['fatal_provider_error']);self.assertFalse(r.known_server_error(row))
            self.assertEqual(opener.calls,1);self.assertFalse(row['known_usage'])
        for status in (500,502,503,504):
            self.assertIsNone(r.availability_class({'http_status':status},{'error_body':'quota exceeded'},'hf'))

    def test_duplicate_keys_any_level_refused(self):
        valid=self.envelope()['error_body']
        for text in ('{"error":{},'+valid[1:],valid.replace('"code":','"code":"quota", "code":')):
            self.assertFalse(r.hf_engine_overloaded({'http_status':429},{'error_body':text}))
    def test_metadata_transient_read_only_backoff_then_success(self):
        with tempfile.TemporaryDirectory() as directory:
            transport=r.ResumeTransport({},Path(directory),object())
            replies=[({'http_status':429},None,self.envelope()),({'http_status':200},{'data':[]},{})]
            with patch.object(r.connectivity,'safe_request',side_effect=replies) as request,patch.object(r.time,'sleep') as sleep,patch.object(r,'publish_availability'):
                self.assertEqual(transport.metadata('https://router.huggingface.co/v1/models'),{'data':[]})
            self.assertEqual(request.call_count,2);self.assertEqual(sleep.call_args.args,(60,))
            self.assertTrue(all(call.args[1].method=='GET' for call in request.call_args_list))
    def test_metadata_funding_fails_without_sleep_or_retry(self):
        transport=r.ResumeTransport({},Path('.'),object())
        with patch.object(r.connectivity,'safe_request',return_value=({'http_status':429},None,self.envelope(code='insufficient_quota'))) as request,patch.object(r.time,'sleep') as sleep:
            with self.assertRaisesRegex(ValueError,'authentication/profile'):transport.metadata('https://router.huggingface.co/v1/models')
        self.assertEqual(request.call_count,1);sleep.assert_not_called()
    def test_late_metadata_success_is_not_admission(self):
        transport=r.ResumeTransport({},Path('.'),object());deadline=r.datetime.fromisoformat(r.policy['cutoff_utc']).timestamp()
        with patch.object(r.time,'time',side_effect=[deadline-1,deadline]),patch.object(r.connectivity,'safe_request',return_value=({'http_status':200},{'data':[]},{})):
            with self.assertRaisesRegex(ValueError,'cutoff'):transport.metadata('https://router.huggingface.co/v1/models')
        with patch.object(r.time,'monotonic',side_effect=[0,0,901]),patch.object(r.connectivity,'safe_request',return_value=({'http_status':200},{'data':[]},{})):
            with self.assertRaisesRegex(ValueError,'wait exhausted'):transport.metadata('https://router.huggingface.co/v1/models')
    def test_exponential_backoff_and_safe_status_without_private_data(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            out=r.folder('readers');job=make_job('fixture');row=native_row(out,job,503)
            self.assertEqual([r.server_error_delay(row,out,n) for n in (1,2,3,4,5,8)],[60,120,240,480,480,480])
            r.publish_availability('waiting','hf_engine_overloaded',2,1000)
            value=r.read(r.folder()/'availability-state.json')
            self.assertEqual(set(value),{'status','updated','failure_class','consecutive_count','next_dispatch_at','episode_remaining_seconds','provider'})
    def test_provider_episode_clock_starts_new_and_expires_before_post(self):
        self.assertTrue(r.check_episode_bounds({'hf':None},at=999999))
        self.assertTrue(r.check_episode_bounds({'hf':100},at=999))
        with self.assertRaisesRegex(ValueError,'episode exhausted'):r.check_episode_bounds({'hf':100},at=1000)
        with self.assertRaisesRegex(ValueError,'episode exhausted'):r.check_episode_bounds({'hf':100},at=99)
        self.assertTrue(r.check_episode_bounds({'hf':None},at=1000))

    def test_metadata_probe_recognized_availability_is_false_auth_fatal(self):
        class Transport:
            keys={'ADAPTION_API_KEY':'fixture','HF_TOKEN':'fixture','OLLAMA_API_KEY':'fixture'};opener=object()
        with patch.object(r.connectivity,'safe_request',side_effect=[({'http_status':200},{},{}),({'http_status':429},None,self.envelope())]):
            self.assertFalse(r.connectivity_probe(Transport()))
        with patch.object(r.connectivity,'safe_request',return_value=({'http_status':403},None,{})):
            with self.assertRaisesRegex(ValueError,'authentication/profile'):r.connectivity_probe(Transport())



class EligibilityTests(unittest.TestCase):
    def profiles(self):
        return dict(a={'provider':'adaption','model':'a'},b={'provider':'adaption','model':'b'},
                    h={'provider':'hf','model':'shared'},hs={'provider':'hf','model':'shared'},
                    o={'provider':'ollama','model':'shared'},ol={'provider':'ollama','model':'shared'})
    def simulate(self,seed,n=250):
        import random
        rng=random.Random(seed);profiles=self.profiles();keys=list(profiles)
        jobs=[dict(id=str(i).zfill(5),profile_id=rng.choice(keys)) for i in range(n)]
        cfg={'provider_max_active':{'adaption':8,'hf':2,'ollama':2},'dispatch_model_limits':{'adaption':2,'hf':2,'ollama':2}}
        old_pending=list(jobs);new_pending=list(jobs);old_active=[];new_active=[];per_model={};admitted=[]
        with patch.object(r.s,'profile',side_effect=lambda identity:profiles[identity]) as lookup:
            cache=r.EligibilityCache(new_pending)
            self.assertLessEqual(lookup.call_count,6)
            steps=0
            while old_pending or old_active:
                steps+=1;self.assertLess(steps,n*4+20)
                enabled=(steps%7!=0)  # Fixed pause/cooldown event in both implementations.
                expected=[]
                if enabled:
                    for job in list(old_pending):
                        if len(old_active)>=8:break
                        profile=profiles[job['profile_id']];provider=profile['provider'];key=(provider,profile['model'])
                        provider_active=sum(profiles[value['profile_id']]['provider']==provider for value in old_active)
                        model_active=sum((profiles[value['profile_id']]['provider'],profiles[value['profile_id']]['model'])==key for value in old_active)
                        if provider_active>=cfg['provider_max_active'][provider] or model_active>=cfg['dispatch_model_limits'][provider]:continue
                        old_active.append(job);old_pending.remove(job);expected.append(job['id'])
                actual=[]
                if enabled and len(new_active)<8 and cache.any_eligible(per_model,cfg):
                    for job in list(new_pending):
                        if len(new_active)>=8:break
                        provider,key=cache.descriptor(job)
                        if cache.active_providers[provider]>=cfg['provider_max_active'][provider] or per_model.get(key,0)>=cfg['dispatch_model_limits'][provider]:continue
                        new_active.append(job);new_pending.remove(job);cache.admitted(job);per_model[key]=per_model.get(key,0)+1;actual.append(job['id'])
                        if not cache.any_eligible(per_model,cfg):break
                self.assertEqual(actual,expected)
                self.assertEqual([v['id'] for v in old_active],[v['id'] for v in new_active])
                self.assertEqual(len(new_active),sum(cache.active_providers.values()))
                self.assertEqual(sum(cache.pending_counts.values()),len(new_pending))
                admitted.extend(actual)
                if old_active:
                    index=rng.randrange(len(old_active));old_active.pop(index);job=new_active.pop(index)
                    provider,key=cache.descriptor(job);cache.completed(job);per_model[key]-=1
            self.assertEqual(len(admitted),n);self.assertEqual(len(set(admitted)),n)
            self.assertLessEqual(lookup.call_count,6)  # No profile reloads during eligibility scans.
    def test_fixed_and_random_completion_order_equivalence(self):
        for seed in range(32):self.simulate(seed)
    def test_saturation_is_constant_profile_work_and_empty_keys_do_not_block(self):
        profiles=self.profiles();jobs=[dict(id=str(i),profile_id='h') for i in range(20000)]
        cfg={'provider_max_active':{'adaption':8,'hf':2,'ollama':2},'dispatch_model_limits':{'adaption':2,'hf':2,'ollama':2}}
        with patch.object(r.s,'profile',side_effect=lambda identity:profiles[identity]) as lookup:
            cache=r.EligibilityCache(jobs);cache.admitted(jobs[0]);cache.admitted(jobs[1])
            for _ in range(100):self.assertFalse(cache.any_eligible({('hf','shared'):2},cfg))
            self.assertEqual(lookup.call_count,1)
            cache.pending_counts[('hf','shared')]=0;cache.completed(jobs[0]);cache.completed(jobs[1])
            self.assertFalse(cache.any_eligible({},cfg))
    def test_five_batch_union_preserves_every_terminal_and_complement(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            jobs=[make_job(str(index)) for index in range(5)]
            registrations=[]
            for index in range(5):
                path=Path(directory)/('freeze'+str(index)+'.json');path.write_text(json.dumps({'batch':index}));registrations.append(path)
            with patch.object(r.s,'freeze_path',return_value=registrations[0]),patch.object(r.prior,'FREEZE',registrations[1]),patch.object(r.second,'FREEZE',registrations[2]),patch.object(r.third,'FREEZE',registrations[3]),patch.object(r,'FREEZE',registrations[4]):
                outputs=[r.original_folder('readers'),r.prior_folder('readers'),r.second_folder('readers'),r.third_folder('readers'),r.folder('readers')]
                for index in range(4):write_phase(outputs[index],jobs,registrations[index],[(jobs[index],500 if index==1 else 200)])
                self.assertEqual([job['id'] for job in r.pending_jobs('readers',jobs)],['4'])
                write_phase(outputs[4],jobs,registrations[4],[(jobs[4],200)])
                values,coverage=r.union_phase('readers',jobs)
                self.assertEqual(len(values),5);self.assertTrue(coverage['complete']);self.assertEqual(coverage['unknown_usage'],1)

    def test_body_normalizer_and_nonpacing_policy_preserved(self):
        self.assertEqual(r.policy,{**r.fifth.policy,'native_global_spacing_seconds':1.6,'native_model_spacing_seconds':3.2,'scoped_cooldown_class':'adaption_rate_limit'})
        self.assertIs(r.s.body_for,r.fifth.s.body_for);self.assertIs(r.s.normalize,r.fifth.s.normalize)

    def test_dynamic_forecast_complement_must_match_descriptors(self):
        counts={'readers':123,'calibration':240,'influence':240};descriptors={phase:phase for phase in counts}
        value={'remaining_calls':counts,'unstarted_descriptor_sha256':descriptors}
        self.assertTrue(r.validate_complement_forecast(value,counts,descriptors))
        for bad in ({**value,'remaining_calls':{**counts,'readers':124}},{**value,'unstarted_descriptor_sha256':{**descriptors,'readers':'wrong'}}):
            with self.assertRaisesRegex(ValueError,'differs'):r.validate_complement_forecast(bad,counts,descriptors)
    def test_verified_snapshot_preserves_all_six_request_bodies(self):
        jobs=[]
        for profile in ('g26','g31','hf_text','hf_schema','ds_off','ds_low'):
            job=make_job(profile);job['profile_id']=profile;jobs.append(job)
        expected=[r.s.body_for(job) for job in jobs]
        with r.s.verified_config():actual=[r.s.body_for(job) for job in jobs]
        self.assertEqual(expected,actual)



class RateTests(unittest.TestCase):
    def envelope(self,wait='60',message=None,**changes):
        error=dict(type='rate_limit_error',code='rate_limit_exceeded',param=None,
                   message=message or ('Rate limit exceeded, retry after '+wait+' seconds'))
        error.update(changes)
        return {'error_body':json.dumps({'error':error}),'headers':{'Retry-After':wait}}
    def test_exact_bounded_wait_matches_message_and_header(self):
        for wait in ('0.1','1','60','120.5','900'):
            self.assertEqual(r.adaption_rate_limit({'http_status':429},self.envelope(wait)),float(wait))
        for wait in ('0','-1','901','NaN','Infinity','bad'):
            self.assertIsNone(r.adaption_rate_limit({'http_status':429},self.envelope(wait)))
        for message in ('Rate limit exceeded','Rate limit exceeded retry after 59 seconds','Rate limit exceeded retry after 61 seconds','Rate limit exceeded retry after 60 seconds and retry after 60 seconds','Rate limit exceeded retry after 60','Quota rate limit exceeded retry after 60 seconds','Billing rate limit retry after 60 seconds'):
            self.assertIsNone(r.adaption_rate_limit({'http_status':429},self.envelope(message=message)))
        for changes in ({'type':'invalid_request_error'},{'code':'insufficient_quota'},{'param':'token_limit'}):
            self.assertIsNone(r.adaption_rate_limit({'http_status':429},self.envelope(**changes)))
        for marker in ('authorization','permission','api key','api_key'):
            self.assertIsNone(r.adaption_rate_limit({'http_status':429},self.envelope(message='Rate limit '+marker+' retry after 60 seconds')))
        private=self.envelope();private['headers']={}
        self.assertIsNone(r.adaption_rate_limit({'http_status':429},private))
        private=self.envelope();private['headers']['retry-after']='60'
        self.assertIsNone(r.adaption_rate_limit({'http_status':429},private))
    def test_duplicate_json_and_capture_faults_are_fatal(self):
        private=self.envelope();private['error_body']=private['error_body'].replace('"code":','"code":"quota", "code":')
        self.assertIsNone(r.adaption_rate_limit({'http_status':429},private))
        for status in ({'http_status':200},{'http_status':429,'capture_failed':True},{'http_status':429,'connection_fault':True}):
            self.assertIsNone(r.adaption_rate_limit(status,self.envelope()))
        self.assertEqual(r.availability_class({'http_status':429},self.envelope(),'adaption'),'adaption_rate_limit')
        self.assertIsNone(r.availability_class({'http_status':429},self.envelope(),'hf'))
    def test_new_rate_transport_single_post_only_and_exact_fatal_flag_override(self):
        from urllib.error import HTTPError
        from io import BytesIO
        owner=self
        class Opener:
            calls=0
            def open(self,request,**kwargs):
                self.calls+=1;private=owner.envelope()
                raise HTTPError(request.full_url,429,'fixture',private['headers'],BytesIO(private['error_body'].encode()))
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            out=r.folder('readers');job=make_job('rate');opener=Opener()
            row=r.ResumeTransport({'ADAPTION_API_KEY':'fixture-only'},out,opener).request(job)
            self.assertEqual(opener.calls,1);self.assertFalse(row['known_usage'])
            self.assertEqual(row['transport']['provider_failure_class'],'adaption_rate_limit')
            self.assertNotIn('fatal_provider_error',row['transport']);self.assertTrue(r.known_server_error(row))
            # The same old row may have its historical fatal flag; amendment must
            # count its terminal failure without editing it or dropping its cost.
            row['transport']['fatal_provider_error']=True
            before=deepcopy(row);self.assertTrue(r.known_server_error(row));self.assertEqual(row,before)
    def stopped_fixture(self,out):
        good=dict(transport={'http_status':200},known_usage=True,anomaly=False)
        terminal=[deepcopy(good) for _ in range(1495)]
        for name in ('rate-one','rate-two'):
            path=out/'native'/(r.digest(name)+'.json');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(self.envelope()))
            terminal.append(dict(id=name,profile_id='g31',transport={'http_status':429,'fatal_provider_error':True},known_usage=False,anomaly=True,native_receipt_sha256=r.raw_sha(path)))
        return [{} for _ in range(1497)],terminal
    def test_six_batch_union_and_cost_complement(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            jobs=[make_job(str(index)) for index in range(6)];registrations=[]
            for index in range(6):
                path=Path(directory)/('freeze'+str(index)+'.json');path.write_text(json.dumps({'batch':index}));registrations.append(path)
            with patch.object(r.s,'freeze_path',return_value=registrations[0]),patch.object(r.prior,'FREEZE',registrations[1]),patch.object(r.second,'FREEZE',registrations[2]),patch.object(r.third,'FREEZE',registrations[3]),patch.object(r.fourth,'FREEZE',registrations[4]),patch.object(r,'FREEZE',registrations[5]):
                outputs=[r.original_folder('readers'),r.prior_folder('readers'),r.second_folder('readers'),r.third_folder('readers'),r.fourth_folder('readers'),r.folder('readers')]
                for index in range(5):write_phase(outputs[index],jobs,registrations[index],[(jobs[index],429 if index==4 else 200)])
                self.assertEqual([job['id'] for job in r.pending_jobs('readers',jobs)],['5'])
                write_phase(outputs[5],jobs,registrations[5],[(jobs[5],200)])
                values,coverage=r.union_phase('readers',jobs)
                self.assertEqual(len(values),6);self.assertTrue(coverage['complete']);self.assertEqual(coverage['unknown_usage'],1)
                with patch.object(r.d,'pilot_spending_paths',return_value=[]):combined,main,_=r.cost_baseline()
                self.assertEqual(combined['adaption'],sum(Decimal(row['estimated_cost']) for row in values));self.assertEqual(main,combined)



class ProspectiveCutoffTests(unittest.TestCase):
    def test_new_admission_after_old_buffer_before_new_boundary(self):
        paths=(Path(r.d.__file__),r.d.CONFIG,Path(r.connectivity.__file__))
        before={str(path):path.read_bytes() for path in paths}
        self.assertTrue(r.dispatch_time_gate(at=datetime(2026,11,9,6,30,tzinfo=timezone.utc)))
        self.assertTrue(r.dispatch_time_gate(at=datetime(2026,11,9,7,55,59,tzinfo=timezone.utc)))
        for at in (datetime(2026,11,9,7,56,tzinfo=timezone.utc),datetime(2026,11,9,8,tzinfo=timezone.utc),datetime(2026,11,9,11,59,tzinfo=timezone.utc)):
            with self.assertRaisesRegex(ValueError,'last dispatch'):r.dispatch_time_gate(at=at)
        self.assertEqual(before,{str(path):path.read_bytes() for path in paths})
        self.assertEqual(r.d.config()['collection_deadline_utc'],'2026-11-09T05:59:00+00:00')
        self.assertEqual(r.connectivity.DEADLINE,'2026-11-09T05:59:00+00:00')
    def test_offpeak_restriction_and_capacity_are_not_relaxed(self):
        with patch.object(r.d,'validate_forecast',return_value=r.read(r.d.FORECAST)):
            baseline=r.d.execution_config('main','readers')
        with patch.object(r,'policy',{**r.policy,'cutoff_utc':'2026-11-09T14:00:00+00:00'}):
            with self.assertRaisesRegex(ValueError,'Off-peak'):r.dispatch_time_gate(at=datetime(2026,11,9,13,tzinfo=timezone.utc))
        with patch.object(r.d,'validate_forecast',return_value=r.read(r.d.FORECAST)):
            current=r.d.execution_config('main','readers')
        for key in ('max_active','provider_max_active','dispatch_model_limits','gateway_allowance','phase_caps','combined_caps','native_class_caps'):
            self.assertEqual(baseline[key],current[key])
    def test_cooldown_uses_new_local_clock_and_never_inference(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            checkpoint=Path(directory)/('runs/'+r.s.config()['study_id']+'-guard/dispatch-cooldown-private.json');checkpoint.parent.mkdir(parents=True);checkpoint.write_text('{"not_before_epoch":10}')
            with patch.object(r.time,'time',side_effect=[5,5,10]),patch.object(r.time,'sleep') as sleep,patch.object(r,'dispatch_time_gate') as newgate,patch.object(r.d,'dispatch_time_gate',side_effect=AssertionError('Old cutoff must not run')),patch.object(r.ResumeTransport,'request') as inference:
                r.capacity_cooldown()
            newgate.assert_called_once_with('main');sleep.assert_called_once_with(1);inference.assert_not_called()
            with patch.object(r.time,'time',return_value=5),patch.object(r,'dispatch_time_gate',side_effect=ValueError('new cutoff')),patch.object(r.ResumeTransport,'request') as inference:
                with self.assertRaisesRegex(ValueError,'new cutoff'):r.capacity_cooldown()
            inference.assert_not_called()



class PacedClockTests(unittest.TestCase):
    def models(self):return r.s.profile('g26')['model'],r.s.profile('g31')['model']
    def test_atomic_global_and_model_floors_persist_and_no_lock_during_sleep(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            state={'now':1000.};holder={};sleeps=[]
            def sleep(delay):
                self.assertTrue(holder['pacer'].lock.acquire(False),'Clock lock held during wait')
                holder['pacer'].lock.release();sleeps.append(delay);state['now']+=delay
            pacer=r.NativePacer(clock=lambda:state['now'],sleep=sleep);holder['pacer']=pacer;a,b=self.models()
            stamps=[(model,pacer.claim(model)) for model in (a,b,a,b,a,b)]
            for (_,left),(_,right) in zip(stamps,stamps[1:]):self.assertGreaterEqual(right-left+1e-9,1.6)
            for model in (a,b):
                values=[when for identity,when in stamps if identity==model]
                for left,right in zip(values,values[1:]):self.assertGreaterEqual(right-left+1e-9,3.2)
            self.assertTrue(sleeps);self.assertFalse(pacer.ready(b))
            restored=r.NativePacer(clock=lambda:state['now'],sleep=sleep)
            self.assertEqual(restored.last_models,pacer.last_models);self.assertEqual(restored.last_global,pacer.last_global)
    def test_waiting_model_does_not_hold_up_ready_other_model(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            state={'now':1000.,'interleave':False};holder={};events=[];a,b=self.models()
            def sleep(delay):
                self.assertTrue(holder['pacer'].lock.acquire(False));holder['pacer'].lock.release()
                if state['interleave']:
                    state['interleave']=False;events.append(('b',holder['pacer'].claim(b)))
                state['now']+=delay
            pacer=r.NativePacer(clock=lambda:state['now'],sleep=sleep);holder['pacer']=pacer
            events.append(('a1',pacer.claim(a)));state['interleave']=True;events.append(('a2',pacer.claim(a)))
            self.assertEqual([name for name,_ in events],['a1','b','a2'])
            self.assertGreaterEqual(events[2][1]-events[0][1]+1e-9,3.2)
    def test_scheduler_cutoff_blocks_new_work_but_admitted_claim_drains(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            now=r.datetime.fromisoformat(r.policy['cutoff_utc']).timestamp()+1;pacer=r.NativePacer(clock=lambda:now,sleep=lambda _:None)
            with self.assertRaisesRegex(ValueError,'last dispatch'):r.dispatch_time_gate(at=datetime.fromtimestamp(now,timezone.utc))
            self.assertEqual(pacer.claim(self.models()[0]),now)
            pacer.model_path.parent.mkdir(parents=True,exist_ok=True);pacer.model_path.write_text(json.dumps({'models':{'x'*64:now}}))
            with self.assertRaisesRegex(ValueError,'clock key'):r.NativePacer(clock=lambda:now)
    def test_forecast_requires_exact_new_pacing_minima(self):
        value=dict(schema_version=1,deadline_feasible=True,budget_feasible=True,off_peak_wallet_gate_passed=True,collection_cutoff_utc=r.policy['cutoff_utc'],forecast_seconds=100,pacing_minima_seconds={'native_global':'1.6','native_model':'3.2'})
        at=datetime(2026,11,8,tzinfo=timezone.utc);self.assertEqual(r.validate_resume_forecast(value,at),value)
        for bad in ({},{'native_global':'1.0','native_model':'3.2'},{'native_global':'1.6','native_model':'3'}):
            with self.assertRaisesRegex(ValueError,'pacing'):r.validate_resume_forecast({**value,'pacing_minima_seconds':bad},at)



class ScopedExecuteTests(unittest.TestCase):
    def response(self,out,job,http=200):
        profile=r.s.profile(job['profile_id'])
        if http==200:
            if profile['provider']=='ollama':native={'model':profile['model'],'done':True,'done_reason':'stop','message':{'content':'fixture'},'prompt_eval_count':10,'eval_count':5}
            else:native={'model':profile['model'],'status':'completed','output_text':'fixture','usage':{'input_tokens':10,'output_tokens':5}}
            private={'native_response':native}
        else:
            native=None;private={'headers':{}}
            if http==429:private=RateTests().envelope()
        path=out/'native'/(r.digest(job['id'])+'.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(private))
        response,known,anomaly=r.s.normalize(native,profile)
        return dict(id=job['id'],profile_id=job['profile_id'],metadata=job['metadata'],transport={'http_status':http},response=response,known_usage=known,anomaly=anomaly,native_receipt_sha256=r.raw_sha(path),estimated_cost=str(r.s.actual_cost(job,response) if known else r.s.reservation(job)))
    def run_fixture(self,http=None,timer=False,barrier=100000):
        from concurrent.futures import Future
        temporary=tempfile.TemporaryDirectory();root=Path(temporary.name);freeze=root/'freeze.json';freeze.write_text('{}')
        clock={'now':0.};events=[];owner=self
        jobs=[make_job('a0'),make_job('a1'),make_job('o0'),make_job('o1')]
        if timer:jobs=[make_job('a0'),make_job('o0'),make_job('o1')]
        for job in jobs:
            if job['id'].startswith('o'):job['profile_id']='ds_low'
        class Gate:
            healthy=True
            def __init__(self,name):self.name=name;self.failures=0
            def before_dispatch(self,**kwargs):events.append((self.name+'_health',clock['now']));self.healthy=True
            def dispatch_allowed(self):return self.healthy
            def connection_failed(self):events.append((self.name+'_pause',clock['now']));self.failures+=1;self.healthy=False
        global_gate=Gate('global');native_gate=Gate('native')
        class Pacer:
            def ready(self,model):return clock['now']>=3.2
            def ready_at(self,model):return 1003.2
        class Transport:
            def request(self,job):
                events.append(('send_'+job['id'],clock['now']))
                return owner.response(r.folder('readers'),job,http if job['id']=='a0' and http else 200)
        transport=Transport()
        if timer:transport.pacer=Pacer()
        class Pool:
            def __init__(self,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def submit(self,function,job):
                future=Future();future.job_id=job['id'];future.payload=function(job)
                if not timer or job['id']!='o0':future.set_result(future.payload)
                return future
        def wait(active,timeout=None,**kwargs):
            self.assertIsNotNone(timeout);self.assertGreater(timeout,0);self.assertLessEqual(timeout,1)
            if timer:
                clock['now']+=timeout
                for future in active:
                    if future.job_id=='o0' and clock['now']>=10 and not future.done():future.set_result(future.payload);events.append(('o0_complete',clock['now']))
            complete=[future for future in active if future.done()]
            return ({sorted(complete,key=lambda future:future.job_id)[0]} if complete else set(),set())
        def sleep(delay):clock['now']+=max(delay,60)
        cfg=execution_fixture();cfg['provider_max_active']['adaption']=1;cfg['provider_max_active']['ollama']=1;cfg['metadata_recheck_calls']=barrier
        class Balance:
            def __init__(self,*args):pass
            def check(self,*args):pass
        with patch.object(r,'ROOT',root),patch.object(r,'FREEZE',freeze),patch.object(r.d,'execution_config',return_value=cfg),patch.object(r.s,'check_metadata',side_effect=lambda _:events.append(('pins',clock['now']))),patch.object(r,'dispatch_time_gate'),patch.object(r.d,'pilot_spending_paths',return_value=[]),patch.object(r.d,'BalanceGuard',Balance),patch.object(r,'ThreadPoolExecutor',Pool),patch.object(r,'wait',side_effect=wait),patch.object(r.time,'monotonic',side_effect=lambda:clock['now']),patch.object(r.time,'time',side_effect=lambda:1000+clock['now']),patch.object(r.time,'sleep',side_effect=sleep),patch.object(r.d,'persist_cooldown') as global_hold:
            result=r._execute('readers',jobs,transport,global_gate,native_gate)
            values,_=r.union_phase('readers',jobs)
            holds=global_hold.call_count
        temporary.cleanup();return events,result,values,global_gate,native_gate,holds
    def test_exact_adaption_rate_keeps_ollama_eligible_without_global_pause(self):
        events,result,values,global_gate,native_gate,holds=self.run_fixture(http=429)
        self.assertTrue(result['complete']);self.assertEqual(global_gate.failures,0);self.assertEqual(native_gate.failures,1);self.assertEqual(holds,0)
        times=dict(events);self.assertEqual(times['send_o1'],0);self.assertGreaterEqual(times['send_a1'],60)
        self.assertLess(events.index(('send_o1',0)),next(index for index,event in enumerate(events) if event[0]=='native_health'))
        failed=next(row for row in values if row['id']=='a0');self.assertFalse(failed['known_usage']);self.assertEqual(Decimal(failed['estimated_cost']),r.s.reservation(make_job('a0')))
    def test_nonrate_server_failure_still_globally_holds_future_ollama(self):
        events,result,_,global_gate,native_gate,holds=self.run_fixture(http=503)
        self.assertTrue(result['complete']);self.assertEqual(global_gate.failures,1);self.assertEqual(native_gate.failures,0);self.assertEqual(holds,1)
        self.assertGreaterEqual(dict(events)['send_o1'],60)
    def test_native_ready_timer_reevaluates_before_long_ollama_completes(self):
        events,result,_,_,_,_=self.run_fixture(timer=True)
        self.assertTrue(result['complete']);times=dict(events)
        self.assertLess(times['send_a0'],times['o0_complete']);self.assertAlmostEqual(times['send_a0'],3.2)
    def test_completion_recheck_still_drains_all_active_before_new_dispatch(self):
        events,result,_,_,_,_=self.run_fixture(timer=True,barrier=1)
        self.assertTrue(result['complete']);times=dict(events)
        self.assertGreaterEqual(times['send_o1'],times['o0_complete'])
        between=[event for event in events if event[0]=='global_health' and event[1]>=times['o0_complete']]
        self.assertTrue(between)



class SevenBatchAdmissionTests(unittest.TestCase):
    def test_seven_batch_union_disjoint_complement_and_failed_reservation(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            jobs=[make_job(str(index)) for index in range(7)];registrations=[]
            for index in range(7):
                path=Path(directory)/('freeze'+str(index)+'.json');path.write_text(json.dumps({'batch':index}));registrations.append(path)
            with patch.object(r.s,'freeze_path',return_value=registrations[0]),patch.object(r.prior,'FREEZE',registrations[1]),patch.object(r.second,'FREEZE',registrations[2]),patch.object(r.third,'FREEZE',registrations[3]),patch.object(r.fourth,'FREEZE',registrations[4]),patch.object(r.fifth,'FREEZE',registrations[5]),patch.object(r,'FREEZE',registrations[6]):
                outputs=[r.original_folder('readers'),r.prior_folder('readers'),r.second_folder('readers'),r.third_folder('readers'),r.fourth_folder('readers'),r.fifth_folder('readers'),r.folder('readers')]
                for index in range(6):write_phase(outputs[index],jobs,registrations[index],[(jobs[index],500 if index==1 else 200)])
                self.assertEqual([job['id'] for job in r.pending_jobs('readers',jobs)],['6'])
                write_phase(outputs[6],jobs,registrations[6],[(jobs[6],200)])
                values,coverage=r.union_phase('readers',jobs)
                self.assertEqual(len(values),7);self.assertTrue(coverage['complete']);self.assertEqual(coverage['unknown_usage'],1)
                self.assertEqual(Decimal(values[1]['estimated_cost']),r.s.reservation(jobs[1]))
                write_phase(outputs[6],jobs,registrations[6],[(jobs[5],200)])
                with self.assertRaisesRegex(ValueError,'Repeated|Duplicate'):r.union_phase('readers',jobs)
    def test_controlled_null_child_stop_is_required_and_fatal_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            root=Path(directory);path=root/'runs/swarm-ledger-rate-v1-driver/state.json';path.parent.mkdir(parents=True)
            state=dict(status='stopped',stage='readers',pid=123,child_pid=None,updated='2026-11-08T20:00:00+00:00');path.write_text(json.dumps(state))
            out=r.fifth_folder('readers');out.mkdir(parents=True);(out/'STOP').write_text('controlled')
            terminal=[dict(id='retained',transport={'http_status':200},known_usage=True,anomaly=False)]
            with patch.object(r.fifth,'verify'),patch.object(r.fifth,'stopped_prefix_gate'),patch.object(r.d,'process_dead') as dead,patch.object(r,'main_jobs',return_value=[]),patch.object(r,'_phase_ledger',return_value=([{'id':'retained'}],terminal)):
                self.assertTrue(r.stopped_prefix_gate());dead.assert_called_once_with(123,state['updated'])
                (out/'stop.json').write_text('{"reason":"fatal"}')
                with self.assertRaisesRegex(ValueError,'Controlled STOP'):r.stopped_prefix_gate()
                (out/'stop.json').unlink();(out/'capture-failures.jsonl').write_text('{"id":"bad"}\n')
                with self.assertRaisesRegex(ValueError,'capture'):r.stopped_prefix_gate()
    def test_unresolved_duplicate_and_unclassified_predecessor_failures_refused(self):
        good=dict(id='one',profile_id='g26',transport={'http_status':200},known_usage=True,anomaly=False)
        self.assertTrue(r.validate_controlled_rate_rows([{'id':'one'}],[good]))
        with self.assertRaisesRegex(ValueError,'unresolved'):r.validate_controlled_rate_rows([{'id':'one'},{'id':'two'}],[good])
        with self.assertRaisesRegex(ValueError,'duplicate'):r.validate_controlled_rate_rows([{'id':'one'},{'id':'one'}],[good,good])
        bad=dict(good,transport={'http_status':401},known_usage=False,anomaly=True)
        with self.assertRaisesRegex(ValueError,'Unclassified'):r.validate_controlled_rate_rows([{'id':'one'}],[bad])



class PredecessorEpisodeHandoffTests(unittest.TestCase):
    def test_episode_live_at_stop_not_expired_by_later_engineering_gap(self):
        state={'updated':'2026-11-08T20:01:00+00:00'}
        availability={'status':'waiting','updated':'2026-11-08T20:00:00+00:00','episode_remaining_seconds':120}
        with patch.object(r,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime(2026,11,9,3,tzinfo=timezone.utc)
            self.assertTrue(r.validate_predecessor_episode_at_stop(state,availability))
        state['updated']='2026-11-08T20:02:00+00:00'
        with self.assertRaisesRegex(ValueError,'exhausted at terminal stop'):r.validate_predecessor_episode_at_stop(state,availability)
        with self.assertRaisesRegex(ValueError,'exhausted at terminal stop'):r.validate_predecessor_episode_at_stop({'updated':availability['updated']},{**availability,'episode_remaining_seconds':0})
    def test_exhausted_episode_at_actual_stop_refused_even_with_controlled_stop(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            state={'status':'stopped','stage':'readers','pid':123,'child_pid':None,'updated':'2026-11-08T20:02:01+00:00'}
            path=Path(directory)/'runs/swarm-ledger-rate-v1-driver/state.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(state))
            out=r.fifth_folder('readers');out.mkdir(parents=True);(out/'STOP').write_text('controlled')
            (r.fifth_folder()/'availability-state.json').write_text(json.dumps({'status':'waiting','updated':'2026-11-08T20:00:00+00:00','episode_remaining_seconds':120}))
            with patch.object(r.fifth,'verify'),patch.object(r.fifth,'stopped_prefix_gate'),patch.object(r.d,'process_dead'):
                with self.assertRaisesRegex(ValueError,'exhausted at terminal stop'):r.stopped_prefix_gate()
    def test_malformed_predecessor_budget_cannot_admit(self):
        state={'updated':'2026-11-08T20:01:00+00:00'}
        for value in (-1,901,float('nan'),True,'120'):
            with self.assertRaisesRegex(ValueError,'budget invalid'):r.validate_predecessor_episode_at_stop(state,{'status':'waiting','updated':'2026-11-08T20:00:00+00:00','episode_remaining_seconds':value})



if __name__=='__main__':unittest.main()
