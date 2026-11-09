"""Offline regressions for immutable-prefix, no-retry MAIN continuation."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments import swarm_ledger_resume as r
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
        self.old=self.root/'old-freeze.json';self.old.write_text('{}');self.new=self.root/'new-freeze.json';self.new.write_text('{"new":true}')
        self.patches=[patch.object(r,'ROOT',self.root),patch.object(r,'FREEZE',self.new),patch.object(r.s,'freeze_path',return_value=self.old)]
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


if __name__=='__main__':unittest.main()
