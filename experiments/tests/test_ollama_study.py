"""Only synthetic inputs, fake HTTP and temporary journals; no live services."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments import ollama_study as o
REAL_METADATA=o.metadata


class Clock:
    def __init__(self):self.value=0;self.sleeps=[]
    def __call__(self):return self.value
    def sleep(self,seconds):self.sleeps.append(seconds);self.value+=seconds


class FakeTransport:
    def __init__(self,clock,fault=None):
        self.clock=clock;self.fault=fault;self.calls=[];self.balances=[];self.lock=threading.Lock();self.active=0;self.peak=0;self.two=threading.Event()
    def request(self,path,body=None):
        extra=dict(retry_after=0,service_overload=False,capture_failed=False)
        if path=='/api/balance':
            self.balances.append(self.clock());return {'http_status':200},{'included':{'balance_usd':20},'purchased':{'balance_usd':0}},extra
        assert path=='/api/chat'
        with self.lock:
            index=len(self.calls);self.calls.append(body);self.active+=1;self.peak=max(self.peak,self.active)
            if len(self.calls)>=2:self.two.set()
        if index<2 and self.fault is None:self.two.wait(1)
        time.sleep(.002)
        native=dict(model=body['model'],done=True,done_reason='stop',message=dict(content='arbitrary non-JSON final text',thinking='private trace' if body['think']=='low' else ''),prompt_eval_count=100,eval_count=10)
        public={'http_status':200}
        if self.fault=='unknown':native.pop('eval_count')
        elif self.fault=='model':native['model']='unexpected'
        elif self.fault=='thinking' and body['think'] is False:native['message']['thinking']='hidden private trace'
        elif self.fault=='incomplete':native['done_reason']='length'
        elif self.fault=='token':native['eval_count']=4097
        elif self.fault=='auth':public={'http_status':403,'error':'HTTPError'};native=None
        elif self.fault=='quota':public={'http_status':429,'error':'HTTPError'};native=None
        elif self.fault=='io':extra['capture_failed']=True
        elif self.fault=='gateway' or (self.fault=='first_gateway' and index==0):
            public={'http_status':503,'error':'HTTPError'};native=None;extra['retry_after']=75
        elif self.fault=='overload':
            public={'http_status':429,'error':'HTTPError'};native=None;extra['service_overload']=True
        with self.lock:self.active-=1
        return public,native,extra


class OllamaTests(unittest.TestCase):
    def setUp(self):
        self.cfg=o.s.read(o.CONFIG);self.old=o.s.config();self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.clock=Clock();(self.root/'research').mkdir()
        self.patches=[patch.object(o.s,'ROOT',self.root),patch.object(o,'CONFIG',self.root/'research/ollama-config.json'),
                      patch.object(o,'CATALOG',self.root/'research/ollama-catalog.json'),patch.object(o,'FREEZE',self.root/'research/ollama-reader-v1-freeze.json'),
                      patch.object(o.s,'FREEZE',self.root/'original.json'),patch.object(o.s,'config',return_value=self.old),
                      patch.object(o,'verify_original_sources'),patch.object(o.s,'verify'),patch.object(o,'metadata',return_value={}),
                      patch.object(o,'credentials',return_value={'OLLAMA_API_KEY':'fixture-O','HF_TOKEN':'fixture-H','ADAPTION_API_KEY':'fixture-A'}),
                      patch.object(o.subprocess,'check_output',side_effect=lambda args,**kw:(self.root/args[2].split(':',1)[1]).read_bytes()),
                      patch.object(o.subprocess,'run',return_value=SimpleNamespace(returncode=0)),
                      patch.object(o.time,'time',side_effect=self.clock)]
        for item in self.patches:item.start()
        for name in o.SOURCES:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name+'\n')
        o.CONFIG.write_text(json.dumps(self.cfg));o.s.FREEZE.write_text('{}')
        catalog=dict(models={c['model']:dict(digest='fixture-'+c['model'],thinking=dict(values=[False,'low','high','max'] if 'deepseek' in c['model'] else [False,True],default='high' if 'deepseek' in c['model'] else False),context_length=1048576 if 'deepseek' in c['model'] else 262144) for c in self.cfg['conditions']})
        o.CATALOG.write_text(json.dumps(catalog))
        record=dict(schema_version=1,config=self.cfg,source_sha256={n:o.s.sha(self.root/n) for n in o.SOURCES},original_freeze_sha256=o.s.sha(o.s.FREEZE),base_commit='fixture')
        o.FREEZE.write_text(json.dumps(record))

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()

    def jobs(self,n=12):
        result=[]
        for i in range(n):
            c=self.cfg['conditions'][i%3]
            result.append(dict(id='fixture:'+str(i),model=c['model'],condition_id=c['id'],messages=[dict(role='system',content=o.s.DIRECT),dict(role='user',content=str(i))],metadata=dict(condition_id=c['id'],phase='readers',source_seed=i,view='sufficient',procedure='direct',packet_sha256=o.s.digest(i))))
        return result

    def execute(self,n=12,fault=None,stage='readers',resume=False):
        transport=FakeTransport(self.clock,fault)
        js=self.jobs(n) if stage=='readers' else o.jobs('pilot')
        with patch.object(o,'jobs',return_value=js),patch.object(o,'pilot_pass',return_value=True):
            summary=o.execute(stage,resume,transport,self.clock,self.clock.sleep)
        return summary,transport

    def test_profile_final_only_thinking_modes_and_incomplete(self):
        native=dict(model='deepseek-v4.1-flash:1017',done=True,done_reason='stop',message={'content':'{"status":"NONE","worker_id":null}','thinking':'secret reasoning'},prompt_eval_count=12,eval_count=50)
        n,known,bad=o.normalize(native,native['model'],'low')
        self.assertTrue(known);self.assertFalse(bad);self.assertNotIn('reasoning',json.dumps(n));self.assertEqual(n['usage']['output_tokens'],50)
        self.assertTrue(o.profile_ok({'http_status':200},n,known,bad))
        _,_,bad=o.normalize(native,native['model'],False);self.assertTrue(bad)
        self.assertEqual(o.admit_response({'http_status':200},n,known,bad)['output_text'],'')
        native['done_reason']='length';n,known,bad=o.normalize(native,native['model'],'low')
        self.assertEqual(n['status'],'incomplete');self.assertFalse(o.profile_ok({'http_status':200},n,known,bad))

    def test_pilot_arbitrary_wording_not_accuracy_gate(self):
        summary,transport=self.execute(stage='pilot')
        self.assertTrue(summary['complete']);self.assertFalse(summary['halted']);self.assertEqual(len(transport.calls),6)
        self.assertTrue(o.pilot_pass())

    def test_two_active_shuffled_unique_plan_and_resume_no_retry(self):
        summary,transport=self.execute(15)
        self.assertTrue(summary['complete']);self.assertFalse(summary['halted']);self.assertLessEqual(transport.peak,2);self.assertGreater(transport.peak,1)
        out=o.folder('readers');starts=o.s.rows(out/'attempts.jsonl');rows=o.s.rows(out/'responses.jsonl')
        self.assertEqual(len({r['id'] for r in starts}),15);self.assertEqual({r['id'] for r in starts},{r['id'] for r in rows})
        again,second=self.execute(15,resume=True);self.assertTrue(again['complete']);self.assertEqual(second.calls,[])

    def test_known_length_retained_invalid_without_count_stop(self):
        summary,transport=self.execute(9,'incomplete')
        self.assertTrue(summary['complete']);self.assertFalse(summary['halted']);self.assertEqual(summary['incomplete'],9)
        for row in o.s.rows(o.folder('readers')/'responses.jsonl'):
            self.assertEqual(o.admit_response(row['transport'],row['response'],row['known_usage'],row['profile_anomaly'])['status'],'incomplete')

    def test_auth_unknown_model_token_io_and_other429_halt_and_drain(self):
        # Different output roots isolate each prospective synthetic run.
        for fault in ('auth','unknown','model','token','io','quota'):
            with self.subTest(fault=fault),patch.object(o,'folder',side_effect=lambda stage:self.root/'runs'/(fault+'-'+stage)):
                summary,transport=self.execute(12,fault)
                self.assertTrue(summary['halted']);self.assertLessEqual(len(transport.calls),2)
                out=o.folder('readers');self.assertEqual(len(o.s.rows(out/'attempts.jsonl')),len(o.s.rows(out/'responses.jsonl')))
                with self.assertRaises(ValueError):self.execute(12,resume=True)

    def test_gateways_have_no_id_retry_and_backoff(self):
        summary,transport=self.execute(7,'first_gateway')
        self.assertTrue(summary['complete']);self.assertFalse(summary['halted']);self.assertEqual(summary['gateway_errors'],1)
        self.assertGreaterEqual(self.clock.value,75)
        rows=o.s.rows(o.folder('readers')/'responses.jsonl');failed=[r for r in rows if o.transient(r)]
        self.assertEqual(len(failed),1);self.assertEqual(failed[0]['estimated_cost'],str(o.reservation(self.jobs()[0]) if failed[0]['metadata']['condition_id']=='ds_off' else o.reservation(next(j for j in self.jobs() if j['id']==failed[0]['id']))))

    def test_transient_limit_eight_with_active_error_reservations(self):
        summary,transport=self.execute(30,'gateway')
        self.assertTrue(summary['halted']);self.assertEqual(summary['gateway_errors'],8);self.assertEqual(len(transport.calls),8)

    def test_unresolved_or_duplicate_start_refuses_dispatch(self):
        self.execute(3)
        (o.folder('readers')/'responses.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError,'Unresolved'):self.execute(3,resume=True)

    def test_public_verify_has_no_jobs_ledger_or_credentials_dependency(self):
        with patch.object(o,'jobs',side_effect=AssertionError('private jobs')),patch.object(o.s,'rows',side_effect=AssertionError('private ledger')),patch.object(o,'credentials',side_effect=AssertionError('keys')):
            self.assertEqual(o.verify(),self.cfg)

    def test_public_adapter_same_messages_modes_and_commitments(self):
        templates=[]
        for view in ('complete','sufficient','calibration_closed_read'):
            for procedure,prompt in (('direct',o.s.DIRECT),('procedure',o.s.PROCEDURE)):
                payload={'view':view,'synthetic':True}
                templates.append(o.s.job('old-'+view+procedure,self.old['hf_model'],prompt,payload,source_seed=1,view=view,procedure=procedure,packet_sha256=o.s.digest(payload)))
        result=o.jobs_from_templates(templates)
        self.assertEqual(len(result),14)
        for job in result:
            original=next(t for t in templates if t['metadata']['view']==job['metadata']['view'] and t['metadata']['procedure']==job['metadata']['procedure'])
            expected=o.s.body_for(original)[1]['messages'];body=o.body_for(job)
            self.assertEqual(body['messages'],expected);self.assertFalse(body['stream']);self.assertEqual(body['options'],{'temperature':0,'num_predict':4096})
            self.assertNotIn('format',body);self.assertNotIn('tools',body);self.assertTrue(job['id'].startswith('ollama-reader-v1:'))
        templates[0]['prompt']='changed'
        with self.assertRaisesRegex(ValueError,'instruction'):o.jobs_from_templates(templates)

    def test_balance_floor_unknown_and_polling_guard(self):
        transport=FakeTransport(self.clock);out=self.root/'balance';out.mkdir()
        monitor=o.Balance(transport,out,self.clock,self.clock.sleep,self.clock)
        monitor.check();monitor.check();self.assertEqual(len(transport.balances),1)
        self.clock.value=61;monitor.check();self.assertEqual(len(transport.balances),2)
        def low(path,body=None):return {'http_status':200},{'included':{'balance_usd':5},'purchased':{'balance_usd':0}},{'capture_failed':False}
        self.clock.value=122;transport.request=low
        with self.assertRaisesRegex(ValueError,'floor'):monitor.check()

    def test_full_inflight_reservations_limit_concurrency_without_premature_stop(self):
        c={**self.cfg,'readers_stage_cap':'0.020','combined_cap':'0.020'}
        js=[j for j in self.jobs(15) if j['condition_id']=='ds_off']
        transport=FakeTransport(self.clock,'incomplete')
        with patch.object(o,'config',return_value=c),patch.object(o,'verify',return_value=c),\
                patch.object(o,'jobs',return_value=js),patch.object(o,'pilot_pass',return_value=True):
            summary=o.execute('readers',False,transport,self.clock,self.clock.sleep)
        self.assertTrue(summary['complete']);self.assertFalse(summary['halted'])
        self.assertEqual(transport.peak,1);self.assertEqual(len(transport.calls),5)

    def test_credit_floor_during_active_requests_stops_and_drains(self):
        test=self
        class FallingCredit(FakeTransport):
            def request(self,path,body=None):
                if path=='/api/balance' and len(self.calls)>=2:
                    self.balances.append(self.clock());return {'http_status':200},{'included':{'balance_usd':5},'purchased':{'balance_usd':0}},{'capture_failed':False}
                result=super().request(path,body)
                if path=='/api/chat':test.clock.value+=61
                return result
        transport=FallingCredit(self.clock)
        with patch.object(o,'jobs',return_value=self.jobs(20)),patch.object(o,'pilot_pass',return_value=True):
            summary=o.execute('readers',False,transport,self.clock,self.clock.sleep)
        self.assertTrue(summary['halted']);self.assertEqual(summary['stop_reason'],'credit_gate')
        self.assertLessEqual(len(transport.calls),2)
        out=o.folder('readers');self.assertEqual(len(o.s.rows(out/'attempts.jsonl')),len(o.s.rows(out/'responses.jsonl')))
        self.assertTrue(all(b-a>=60 for a,b in zip(transport.balances,transport.balances[1:])))

    def test_metadata_exact_advertised_digest_and_thinking_modes(self):
        pinned=o.s.read(o.CATALOG)
        class MetadataOnly:
            drift=False
            def request(self,path,body=None):
                if path=='/api/tags':
                    data={'models':[{'name':name,'digest':item['digest']+('-drift' if self.drift else '')} for name,item in pinned['models'].items()]}
                else:
                    item=pinned['models'][body['model']]
                    data={'thinking':item['thinking'],'model_info':{'fixture.context_length':item['context_length']}}
                return {'http_status':200},data,{'capture_failed':False}
        transport=MetadataOnly();result=REAL_METADATA(transport,pinned)
        self.assertEqual(result['models'],pinned['models'])
        transport.drift=True
        with self.assertRaisesRegex(ValueError,'digest drift'):REAL_METADATA(transport,pinned)
        altered=json.loads(json.dumps(pinned));altered['models']['deepseek-v4.1-flash:1017']['thinking']['values']=[0,'low']
        with self.assertRaisesRegex(ValueError,'thinking'):o.validate_catalog(altered)

    def test_collection_status_refuses_lock_and_unresolved(self):
        out=o.folder('readers');out.mkdir(parents=True);(out/'collector.lock').write_text('1')
        with self.assertRaisesRegex(ValueError,'active'):o.collection_status()
        (out/'collector.lock').unlink();(out/'attempts.jsonl').write_text('{"id":"a"}\n')
        with self.assertRaisesRegex(ValueError,'unresolved'):o.collection_status()


class TransportTests(unittest.TestCase):
    def test_error_bound_all_key_redaction_overload_and_numeric_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            reads=[]
            class Body(io.BytesIO):
                def read(self,n=-1):reads.append(n);return super().read(n)
            class Opener:
                def open(self,request,timeout):
                    raise HTTPError(request.full_url,429,'private',{'Retry-After':'92','Set-Cookie':'key-H'},Body(b'{"error":"server overload key-O key-A"}'))
            transport=o.Transport({'OLLAMA_API_KEY':'key-O','HF_TOKEN':'key-H','ADAPTION_API_KEY':'key-A'},Path(temp),Opener())
            public,native,internal=transport.request('/api/chat',{'model':'fixture'})
            self.assertEqual(reads,[16384]);self.assertIsNone(native);self.assertTrue(internal['service_overload']);self.assertEqual(internal['retry_after'],92)
            self.assertEqual(set(public),{'http_status','latency_seconds','error'})
            raw=(Path(temp)/'000000-private.json').read_text()
            for secret in ('key-O','key-H','key-A'):self.assertNotIn(secret,raw)
            self.assertIn('[REDACTED]',raw)

    def test_unknown429_not_reclassified_and_no_redirect(self):
        with tempfile.TemporaryDirectory() as temp:
            class Opener:
                def open(self,request,timeout):raise HTTPError(request.full_url,429,'',{},io.BytesIO(b'{"error":"request quota exceeded"}'))
            _,_,extra=o.Transport({'OLLAMA_API_KEY':'fixture'},Path(temp),Opener()).request('/api/chat',{})
            self.assertFalse(extra['service_overload'])
        with self.assertRaises(HTTPError):o.NoRedirect().redirect_request(SimpleNamespace(full_url=o.BASE+'/api/chat'),None,307,'',{},o.BASE+'/api/chat')

    def test_literal_credentials_and_environment_override(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env';path.write_text('OLLAMA_API_KEY="literal-value"\nEVIL=$(do_not_run)\nHF_TOKEN=private-H\n')
            with patch.dict(os.environ,{},clear=True):self.assertEqual(o.credentials(path)['OLLAMA_API_KEY'],'literal-value')
            with patch.dict(os.environ,{'OLLAMA_API_KEY':'environment-value'},clear=True):self.assertEqual(o.credentials(path)['OLLAMA_API_KEY'],'environment-value')


if __name__=='__main__':unittest.main()
