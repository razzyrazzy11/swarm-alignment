"""Offline regressions for immutable-prefix, no-retry MAIN continuation."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments import swarm_ledger_resume_v3 as r
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
        self.old=self.root/'old-freeze.json';self.old.write_text('{}');self.v1=self.root/'v1-freeze.json';self.v1.write_text('{"v1":true}');self.v2=self.root/'v2-freeze.json';self.v2.write_text('{"v2":true}');self.new=self.root/'new-freeze.json';self.new.write_text('{"new":true}')
        self.patches=[patch.object(r,'ROOT',self.root),patch.object(r,'FREEZE',self.new),patch.object(r.s,'freeze_path',return_value=self.old),patch.object(r.prior,'FREEZE',self.v1),patch.object(r.second,'FREEZE',self.v2)]
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
                   collection_cutoff_utc=r.policy['cutoff_utc'],forecast_seconds=100)
        at=datetime(2026,11,8,tzinfo=timezone.utc);self.assertEqual(r.validate_resume_forecast(value,at),value)
        for key in ('deadline_feasible','budget_feasible','off_peak_wallet_gate_passed'):
            bad=deepcopy(value);bad[key]=False
            with self.assertRaisesRegex(ValueError,'gate failed'):r.validate_resume_forecast(bad,at)
        with self.assertRaisesRegex(ValueError,'no longer fits'):r.validate_resume_forecast(value,datetime(2026,11,9,5,58,tzinfo=timezone.utc))


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
            self.assertEqual(set(value),{'status','updated','failure_class','consecutive_count','next_dispatch_at','episode_remaining_seconds'})
    def test_stopped_v2_null_child_is_not_invented_or_dereferenced(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'ROOT',Path(directory)):
            path=Path(directory)/'runs/swarm-ledger-resume-v2-driver/state.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(status='stopped',stage='readers',exit_code=1,pid=123,child_pid=None,updated='2026-11-08T14:58:00+00:00')))
            with patch.object(r.second,'verify'),patch.object(r.second,'stopped_prefix_gate'),patch.object(r.d,'process_dead') as dead:
                self.assertTrue(r.stopped_prefix_gate())
                dead.assert_called_once_with(123,'2026-11-08T14:58:00+00:00')
            lock=r.second_folder('readers')/'collector.lock';lock.parent.mkdir(parents=True);lock.write_text('fixture')
            with patch.object(r.second,'verify'),patch.object(r.second,'stopped_prefix_gate'),patch.object(r.d,'process_dead'):
                with self.assertRaisesRegex(ValueError,'lock remains'):r.stopped_prefix_gate()

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



if __name__=='__main__':unittest.main()
