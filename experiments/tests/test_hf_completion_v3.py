"""Synthetic router-recovery checks; no credentials, private runs or network."""
import io,json,ssl,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError,HTTPError
from experiments import hf_completion_v3 as v
from experiments.tests.test_hf_completion import Clock

class Gate:
    def __init__(self):self.calls=[];self.failures=0
    def before_dispatch(self,force_health=False):self.calls.append(force_health);return dict(ready=True)
    def connection_failed(self):self.failures+=1

class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.original=self.root/'old';self.original.mkdir()
        self.freeze=self.root/'freeze.json';self.freeze.write_text('{}');self.clock=Clock();self.gate=Gate()
        self.jobs=[v.s.job(str(i),v.s.config()['hf_model'],'Synthetic',dict(i=i)) for i in range(4)]
        self.prior=[dict(id='old',estimated_cost='.01')]
        self.registration=dict(pending=[v.h.descriptor(j) for j in self.jobs],prior_raw_sha256={},prior_estimated_cost='.01')
        self.patches=[patch.object(v,'ROOT',self.root),patch.object(v,'FREEZE',self.freeze),
          patch.object(v,'verify',side_effect=lambda:self.registration),patch.object(v,'private_prefix',side_effect=lambda *a,**kw:(self.jobs,self.prior,{},75)),
          patch.object(v,'driver_proof',return_value={}),patch.object(v.h,'keys',return_value={'HF_TOKEN':'synthetic-secret'}),
          patch.object(v.s,'folder',return_value=self.original)]
        for item in self.patches:item.start()
    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()
    def transport(self,codes=None):
        codes=list(codes or [200]*4);test=self
        class Transport:
            def __init__(self):self.calls=[];self.opener=SimpleNamespace(last_open_started=None,service_overload=False,capture_failed=False,retry_after_delay=0,last_receipt=None)
            def __call__(self,url,key,body,timeout):
                self.calls.append((test.clock(),body));self.opener.last_open_started=test.clock();test.clock.sleep(2);kind=codes.pop(0)
                if kind=='connection':return dict(http_status=None,error='connectivity_error',connection_fault=True),None
                if kind=='json':return dict(http_status=200,error='json_decode_error',connection_fault=False),None
                if kind==401:return dict(http_status=401,error='HTTPError'),None
                native=dict(model=body['model'].rsplit(':',1)[0],choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=10))
                return dict(http_status=200),native
        return Transport()
    def run_fixture(self,transport,resume=False):return v.execute(resume,transport,self.clock,self.clock.sleep,self.gate)
    def test_unchanged_bodies_spacing_and_old_prefix(self):
        marker=self.original/'immutable';marker.write_text('keep')
        t=self.transport();summary=self.run_fixture(t)
        self.assertTrue(summary['complete']);self.assertEqual(summary['new_transient_errors'],75)
        self.assertEqual([b for _,b in t.calls],[v.s.body_for(j)[1] for j in self.jobs])
        self.assertTrue(all(b[0]-a[0]>=30 for a,b in zip(t.calls,t.calls[1:])))
        self.assertEqual(marker.read_text(),'keep');v.supplement_ledger(v.folder(),self.jobs,v.s.read(v.folder()/'plan.json'))
    def test_connection_failure_retained_no_repeat_and_next_identity(self):
        t=self.transport([200,'connection',200,200]);summary=self.run_fixture(t)
        self.assertTrue(summary['complete']);self.assertEqual(len(t.calls),4);self.assertEqual(self.gate.failures,1)
        rows=v.s.rows(v.folder()/'responses.jsonl');self.assertFalse(rows[1]['known_usage'])
        self.assertEqual(rows[1]['estimated_cost'],str(v.h.reservation(self.jobs[1])))
        self.assertGreaterEqual(t.calls[2][0]-t.calls[1][0],62)
        v.supplement_ledger(v.folder(),self.jobs,v.s.read(v.folder()/'plan.json'))
        with self.assertRaises(ValueError):self.run_fixture(self.transport())
    def test_json_failure_and_auth_are_fatal_not_connectivity(self):
        for code in ('json',401):
            with self.subTest(code=code):
                if v.folder().exists():
                    import shutil;shutil.rmtree(v.folder())
                t=self.transport([code]);summary=self.run_fixture(t)
                self.assertTrue(summary['halted']);self.assertEqual(len(t.calls),1);self.assertEqual(self.gate.failures,0)
    def test_aggregate_cost_prevents_send(self):
        self.registration['prior_estimated_cost']='2.50';t=self.transport()
        summary=self.run_fixture(t);self.assertEqual(summary['stop_reason'],'budget');self.assertEqual(t.calls,[])
    def test_changed_prefix_and_unresolved_start_block_before_send(self):
        t=self.transport()
        with patch.object(v,'private_prefix',return_value=(self.jobs,self.prior,{'different':'hash'},75)):
            with self.assertRaises(ValueError):self.run_fixture(t)
        self.assertEqual(t.calls,[])
        self.run_fixture(self.transport())
        with (v.folder()/'attempts.jsonl').open('a') as f:f.write('{"id":"ambiguous"}\n')
        with self.assertRaises(ValueError):self.run_fixture(self.transport(),True)
    def test_preflight_outage_sends_nothing_and_keeps_all_unstarted(self):
        self.gate.before_dispatch=lambda **kw:(_ for _ in ()).throw(ValueError('Synthetic bounded outage'))
        t=self.transport();summary=self.run_fixture(t)
        self.assertEqual(t.calls,[]);self.assertEqual(summary['unstarted'],4);self.assertEqual(summary['stop_reason'],'connectivity_or_catalog_preflight')
    def test_unknown_error_cannot_claim_connectivity(self):
        response,_=v.s.safe_response(None,self.jobs[0]['model'])
        row=dict(provider='hf',model=self.jobs[0]['model'],transport=dict(http_status=None,error='unexpected_request_error'),known_usage=False,native_response=None,capture_failed=False,response=response)
        self.assertTrue(v.fatal(row));row['transport']['connection_fault']=True;self.assertFalse(v.fatal(row))
        row['capture_failed']=True;self.assertTrue(v.fatal(row))

class TransportTests(unittest.TestCase):
    def test_catalog_tls_is_fatal_not_outage_and_secret_safe(self):
        for error in (ssl.SSLError('synthetic-secret'),URLError(ssl.SSLError('synthetic-secret'))):
            backend=SimpleNamespace(open=lambda *a,**kw:(_ for _ in ()).throw(error))
            with patch.object(v,'build_opener',return_value=backend):
                with self.assertRaisesRegex(ValueError,'TLS validation failed') as caught:v.probe_catalog({'HF_TOKEN':'synthetic-secret'})
                self.assertNotIn('synthetic-secret',str(caught.exception))
    def test_catalog_body_cap_is_fatal_before_json_or_route_parsing(self):
        class Reply(io.BytesIO):status=200
        backend=SimpleNamespace(open=lambda *a,**kw:Reply(b' '*2097153))
        with patch.object(v,'build_opener',return_value=backend):
            with self.assertRaisesRegex(ValueError,'body cap exceeded'):v.probe_catalog({'HF_TOKEN':'fixture'})
    def test_single_attempt_exact_bytes_and_safe_decode_error(self):
        with tempfile.TemporaryDirectory() as temp:
            calls=[];body={'model':'synthetic','messages':[{'role':'user','content':'fixture'}]}
            class Reply(io.BytesIO):
                status=200;headers={'Content-Type':'text/html'}
            def send(req,timeout):calls.append(req);return Reply(b'<bad>')
            t=v.SafeTransport(temp,['synthetic-secret'],opener=SimpleNamespace(open=send))
            public,native=t(v.s.HF+'/chat/completions','synthetic-secret',body)
            self.assertEqual(len(calls),1);self.assertEqual(calls[0].data,json.dumps(body).encode())
            self.assertEqual(public['http_status'],200);self.assertIsNone(native);self.assertFalse(public['connection_fault'])
            self.assertNotIn('synthetic-secret',json.dumps(public));self.assertNotIn('<bad>',json.dumps(public))
    def test_connection_type_preserved_no_exception_message(self):
        with tempfile.TemporaryDirectory() as temp:
            calls=[]
            def send(*args,**kw):calls.append(1);raise URLError(OSError(10051,'private synthetic-secret host'))
            t=v.SafeTransport(temp,['synthetic-secret'],opener=SimpleNamespace(open=send))
            public,native=t(v.s.HF+'/chat/completions','synthetic-secret',{'model':'fixture'})
            self.assertEqual(calls,[1]);self.assertTrue(public['connection_fault']);self.assertIsNone(native)
            self.assertNotIn('synthetic-secret',json.dumps(public));self.assertNotIn('private',json.dumps(public))
    def test_error_receipt_matches_frozen_classifier_and_honors_retry_after(self):
        with tempfile.TemporaryDirectory() as temp:
            raw=b'{"type":"server_overload","message":"server overload, fixture"}'
            def send(*args,**kw):raise HTTPError('https://example.invalid',429,'busy',{'Retry-After':'77'},io.BytesIO(raw))
            t=v.SafeTransport(temp,[],opener=SimpleNamespace(open=send));public,native=t(v.s.HF+'/chat/completions','fixture',{})
            self.assertEqual(public['error'],'HTTPError');self.assertTrue(t.opener.service_overload);self.assertEqual(t.opener.retry_after_delay,77)
            receipt=t.opener.last_receipt;self.assertEqual(v.h.raw_sha(Path(temp)/receipt['file']),receipt['sha256'])
            self.assertNotIn('headers',json.dumps(public))

class UnionTests(unittest.TestCase):
    def test_complete_union_preserves_failed_terminals_and_rejects_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);freeze=root/'freeze.json';freeze.write_text('{}')
            old1=root/'v1';old2=root/'v2';new=root/'runs'/v.TAG
            for out in (old1,old2,new):
                out.mkdir(parents=True)
                for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json'):(out/name).write_text('{}\n')
            prior=[dict(id='old'+str(i),estimated_cost='.001',transport=dict(http_status=200)) for i in range(1741)]
            prior[-1]['transport']=dict(http_status=None,error='transport_or_json_error')
            fresh=[dict(id='new'+str(i),estimated_cost='.001',transport=dict(http_status=200)) for i in range(157)]
            registration=dict(prior_raw_sha256={},prior_estimated_cost='1.741',pending=[])
            summary=dict(planned=157,prior_terminals=1741,prior_estimated_cost='1.741',complete=True,returned=157,unstarted=0,freeze_sha256=v.s.sha(freeze),new_estimated_cost='.157',
              combined_estimated_cost='1.898',new_transient_errors=75,halted=False,stop_reason='')
            (new/'summary.json').write_text(json.dumps(summary))
            patches=[patch.object(v,'ROOT',root),patch.object(v,'FREEZE',freeze),patch.object(v,'verify',return_value=registration),
              patch.object(v,'private_prefix',return_value=([],prior,{},75)),patch.object(v,'supplement_ledger',return_value=([{}]*157,fresh,set())),
              patch.object(v.h,'folder',return_value=old1),patch.object(v.v2,'folder',return_value=old2),
              patch.object(v.h,'verify',return_value={'pending':[dict(id=x['id'],request_sha256='fixture') for x in prior+fresh]})]
            for item in patches:item.start()
            try:
                combined,body,merged,commitments=v.private_completed()
                self.assertEqual(len(combined),1898);self.assertEqual(combined[1740],prior[-1]);self.assertEqual(len(body),1898)
                self.assertEqual(merged['new_estimated_cost'],'1.898');self.assertEqual(merged['new_transient_errors'],75)
                self.assertEqual(set(commitments),{'hf-completion-v1','hf-completion-v2','hf-completion-v3'})
                fresh[0]['id']=prior[-1]['id']
                with self.assertRaisesRegex(ValueError,'union differs'):v.private_completed()
            finally:
                for item in reversed(patches):item.stop()

if __name__=='__main__':unittest.main()
