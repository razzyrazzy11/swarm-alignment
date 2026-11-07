"""Synthetic-only scheduling checks; no credentials or network are used."""
import io
import json
from decimal import Decimal
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments import factorial_continue as c


class Clock:
    def __init__(self): self.now = 0; self.sleeps = []
    def __call__(self): return self.now
    def sleep(self, duration): self.sleeps.append(duration); self.now += duration


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root/'runs'/'fixture-audits'
        self.out.mkdir(parents=True)
        self.config = c.s.config()
        self.jobs = [c.s.job(str(i), self.config['hf_model'], 'Fixture only', {'i':i}) for i in range(8)]
        self.patches = [patch.object(c.s, 'ROOT', self.root),
                        patch.object(c.s, 'FREEZE', self.root/'research'/'freeze.json'),
                        patch.object(c.s, 'verify', return_value={'valid':True}),
                        patch.object(c.s, 'verify_core', return_value={'valid':True}),
                        patch.object(c.s, 'SOURCES', ()),
                        patch.object(c.subprocess,'run',return_value=SimpleNamespace(returncode=0)),
                        patch.object(c.s, 'config', return_value=self.config),
                        patch.object(c.s, 'folder', return_value=self.out),
                        patch.object(c.s, 'audit_jobs', return_value=self.jobs),
                        patch.object(c.s, 'credentials', return_value={'HF_TOKEN':'fake-credential'})]
        for item in self.patches: item.start()
        (self.root/'research').mkdir()
        c.s.FREEZE.write_text(json.dumps(dict(config=self.config,source_sha256={},base_commit='fixture')))
        for name in c.SOURCES:
            target = self.root/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(name+'\n')
        self.ordered, self.plan = c.shuffled_plan(self.jobs)
        (self.out/'plan.json').write_text(json.dumps(self.plan))
        self.regpath = self.root/'registration.json'
        self.historical = self.ordered[0]['id']
        self.write_initial()
        self.register()
        self.tag = patch.object(c.subprocess, 'check_output', side_effect=lambda args, **kw: (self.root/args[2].split(':',1)[1]).read_bytes())
        self.tag.start()

    def tearDown(self):
        self.tag.stop()
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def native(self, body):
        return dict(model=body['model'].rsplit(':',1)[0], choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'), finish_reason='stop')], usage=dict(prompt_tokens=10,completion_tokens=10))

    def write_initial(self, code=429):
        job = self.ordered[0]; provider, body = c.s.body_for(job)
        native = None
        normal, known = c.s.safe_response(native,job['model'])
        ri,ro = c.s.rates(job['model'])
        reserve=(self.config['input_byte_cap']*ri+self.config['max_output_tokens']*ro)/1000000
        attempt=dict(id=job['id'],provider=provider,request_sha256=c.s.digest(body),reserved_cost=str(reserve),started='fixture')
        row=dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,transport={'http_status':code,'error':'HTTPError'},response=normal,known_usage=known,estimated_cost=str(reserve),native_response=None)
        (self.out/'attempts.jsonl').write_text(json.dumps(attempt)+'\n')
        (self.out/'responses.jsonl').write_text(json.dumps(row)+'\n')

    def register(self):
        starts=c.s.rows(self.out/'attempts.jsonl'); results=c.s.rows(self.out/'responses.jsonl')
        self.reg=dict(schema_version=1,registration_tag='fixture-tag',original_freeze_sha256=c.s.sha(c.s.FREEZE),source_sha256={n:c.s.sha(self.root/n) for n in c.SOURCES},output_directory=self.out.relative_to(self.root).as_posix(),starting=dict(attempts_sha256=c.raw_sha(self.out/'attempts.jsonl'),responses_sha256=c.raw_sha(self.out/'responses.jsonl'),attempt_count=len(starts),response_count=len(results),started_ids_sha256=c.s.digest(sorted(r['id'] for r in starts)),terminal_ids_sha256=c.s.digest(sorted(r['id'] for r in results)),plan_sha256=c.raw_sha(self.out/'plan.json')),historical_429_ids=[r['id'] for r in results if r['transport']['http_status']==429],jobs_ids_sha256=c.s.digest(sorted(self.plan['ids'])),limits=c.LIMITS.copy())
        self.regpath.write_text(json.dumps(self.reg))

    def run_fake(self, codes=None, callback=None):
        clock=Clock(); calls=[]; codes=iter(codes or [])
        def transport(url,key,body,timeout):
            calls.append((clock(),json.loads(json.dumps(body))))
            if callback: callback(clock,calls)
            status=next(codes,200)
            return ({'http_status':status,'latency_seconds':0,**({'error':'HTTPError'} if status!=200 else {})},self.native(body) if status==200 else None)
        transport.delay=0
        result=c.execute(self.regpath,transport=transport,clock=clock,sleep=clock.sleep)
        return result,calls,clock

    def test_429_next_id_never_retry_and_prefix_preserved(self):
        olda=(self.out/'attempts.jsonl').read_bytes(); oldr=(self.out/'responses.jsonl').read_bytes()
        summary,calls,clock=self.run_fake([429,200])
        starts=c.s.rows(self.out/'attempts.jsonl'); results=c.s.rows(self.out/'responses.jsonl')
        self.assertTrue(summary['complete']);self.assertEqual(len(calls),7)
        self.assertEqual(len(set(r['id'] for r in starts)),8)
        self.assertEqual({r['id'] for r in starts},{r['id'] for r in results})
        self.assertEqual(sum(r['transport']['http_status']==429 for r in results),2)
        self.assertTrue((self.out/'attempts.jsonl').read_bytes().startswith(olda))
        self.assertTrue((self.out/'responses.jsonl').read_bytes().startswith(oldr))
        self.assertGreaterEqual(calls[0][0],300);self.assertGreaterEqual(calls[1][0]-calls[0][0],300)
        for first,second in zip(calls,calls[1:]):self.assertGreaterEqual(second[0]-first[0],12)
        self.assertLessEqual(max(clock.sleeps),1)
        self.assertEqual(set(summary),{'planned','returned','complete','halted','unstarted','gateway_errors','incomplete','costs','freeze_sha256'})

    def test_max_five_429_includes_initial(self):
        summary,calls,_=self.run_fake([429]*8)
        self.assertTrue(summary['halted']);self.assertEqual(len(calls),4)
        self.assertEqual(summary['returned'],5);self.assertEqual(summary['unstarted'],3)

    def test_retry_after_above300_respected_and429_known_usage_stops(self):
        clock=Clock();calls=[]
        def request(url,key,body,timeout):
            calls.append(clock())
            if len(calls)==1:return {'http_status':429,'error':'HTTPError'},None
            return {'http_status':200},self.native(body)
        request.delay=601
        result=c.execute(self.regpath,transport=request,clock=clock,sleep=clock.sleep)
        self.assertTrue(result['complete']);self.assertGreaterEqual(calls[1]-calls[0],601)
        self.write_initial();self.register();clock=Clock();calls=[]
        def anomalous(url,key,body,timeout):
            calls.append(True)
            data=self.native(body);data['model']='wrong-family'
            return {'http_status':429,'error':'HTTPError'},data
        result=c.execute(self.regpath,transport=anomalous,clock=clock,sleep=clock.sleep)
        self.assertTrue(result['halted']);self.assertEqual(len(calls),1)

    def test_exclusive_run_prevents_second_operator(self):
        with c.exclusive_run(self.out):
            with self.assertRaisesRegex(ValueError,'already active'):
                with c.exclusive_run(self.out):self.fail('second operator')
        self.assertFalse((self.out/'continuation.lock').exists())

    def test_non429_fatal_not_exempt(self):
        for status in (401,402,403,400,None):
            with self.subTest(status=status):
                self.write_initial();self.register()
                summary,calls,_=self.run_fake([status])
                self.assertTrue(summary['halted']);self.assertEqual(len(calls),1)
        self.write_initial(403);self.register()
        with self.assertRaisesRegex(ValueError,'Prior non-429'):self.run_fake()

    def test_unknown_usage_model_and_token_limit_stop_without_retry(self):
        for fault in ('unknown','model','input','output'):
            with self.subTest(fault=fault):
                self.write_initial();self.register();clock=Clock();calls=[]
                def request(url,key,body,timeout):
                    calls.append(True);native=self.native(body)
                    if fault=='unknown':native.pop('usage')
                    elif fault=='model':native['model']='unexpected'
                    elif fault=='input':native['usage']['prompt_tokens']=self.config['input_byte_cap']+1
                    else:native['usage']['completion_tokens']=self.config['max_output_tokens']+1
                    return {'http_status':200},native
                result=c.execute(self.regpath,transport=request,clock=clock,sleep=clock.sleep)
                self.assertTrue(result['halted']);self.assertEqual(len(calls),1)

    def test_pause_stop_before_journal_no_call(self):
        old=(self.out/'attempts.jsonl').read_bytes(); clock=Clock()
        def sleep(seconds):
            clock.sleep(seconds);(self.out/'STOP').write_text('stop')
        with patch.object(c.s,'credentials',side_effect=AssertionError('no key read')):
            result=c.execute(self.regpath,transport=lambda *a,**kw:self.fail('no network'),clock=clock,sleep=sleep)
        self.assertTrue(result['halted']);self.assertEqual((self.out/'attempts.jsonl').read_bytes(),old)

    def test_budget_includes_reserved_unknown(self):
        # One legitimate reserve below $2 plus another would cross the cap.
        rate=Decimal('1500000')/Decimal(self.config['input_byte_cap']+self.config['max_output_tokens'])
        with patch.object(c.s,'rates',return_value=(rate,rate)):
            self.write_initial();self.register()
            summary,calls,_=self.run_fake()
        self.assertTrue(summary['halted']);self.assertEqual(calls,[])

    def test_unknown_cost_cannot_be_discounted(self):
        rows=c.s.rows(self.out/'responses.jsonl');rows[0]['estimated_cost']='0'
        (self.out/'responses.jsonl').write_text(json.dumps(rows[0])+'\n');self.register()
        with self.assertRaisesRegex(ValueError,'full reservation'):self.run_fake()

    def test_known_cost_must_match_usage(self):
        self.run_fake()
        rows=c.s.rows(self.out/'responses.jsonl')
        rows[-1]['estimated_cost']='0'
        (self.out/'responses.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        self.register()
        with self.assertRaisesRegex(ValueError,'known usage cost'):c.verify(self.regpath)

    def test_prefix_plan_body_duplicates_and_sources_rejected(self):
        # Each failure is offline, before credentials or transport.
        (self.out/'attempts.jsonl').write_text((self.out/'attempts.jsonl').read_text()*2)
        with self.assertRaisesRegex(ValueError,'duplicate'):c.verify(self.regpath)
        self.write_initial();self.register()
        (self.out/'responses.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError,'Unresolved'):c.verify(self.regpath)
        self.write_initial();self.register()
        starts=c.s.rows(self.out/'attempts.jsonl');starts[0]['request_sha256']='bad'
        (self.out/'attempts.jsonl').write_text(json.dumps(starts[0])+'\n')
        with self.assertRaisesRegex(ValueError,'body drift'):c.verify(self.regpath)
        self.write_initial();self.register()
        target=self.out/'responses.jsonl';target.write_text(target.read_text().rstrip()+'  \n')
        with self.assertRaisesRegex(ValueError,'checkpoint'):c.verify(self.regpath)
        self.write_initial();self.register()
        (self.root/c.SOURCES[0]).write_text('changed')
        with self.assertRaisesRegex(ValueError,'sources'):c.verify(self.regpath)

    def test_tag_and_job_plan_drift_rejected(self):
        with patch.object(c.subprocess,'check_output',return_value=b'bad'):
            with self.assertRaisesRegex(ValueError,'tag'):c.verify(self.regpath,tagged=True)
        (self.out/'plan.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'request plan'):c.verify(self.regpath)

    def test_public_verify_never_requires_private_jobs_or_ledgers(self):
        with patch.object(c.s,'audit_jobs',side_effect=AssertionError('private jobs')),\
                patch.object(c.s,'rows',side_effect=AssertionError('private ledger')),\
                patch.object(c.s,'contexts',side_effect=AssertionError('private context')),\
                patch.object(c.s,'verify',side_effect=AssertionError('private verify')):
            registration,out=c.verify_sources(self.regpath)
        self.assertEqual(registration,self.reg);self.assertEqual(out,self.out)

    def test_original_body_and_serving_profile_unchanged(self):
        config=json.dumps(self.config,sort_keys=True)
        _,calls,_=self.run_fake()
        expected=[c.s.body_for(job)[1] for job in self.ordered[1:]]
        self.assertEqual([body for _,body in calls],expected)
        self.assertEqual(json.dumps(self.config,sort_keys=True),config)


class TransportTests(unittest.TestCase):
    def test_retry_after_and_numeric(self):
        self.assertEqual(c.retry_after('12'),12)
        self.assertEqual(c.retry_after('Thu, 01 Jan 1970 00:01:00 GMT',now=0),60)
        for value in (None,'bad','-1','nan','inf','Thu, 01 Jan 1970 00:00:00 GMT'):
            self.assertIsNone(c.retry_after(value,now=1))

    def test_transport_shape_serialization_and_numeric_sidecar(self):
        with tempfile.TemporaryDirectory() as temporary:
            sidecar=Path(temporary)/'rate.jsonl'; requests=[]
            class Opener:
                def open(self,request,timeout):
                    requests.append(request)
                    raise HTTPError(request.full_url,429,'private error',{'Retry-After':'601','Set-Cookie':'secret','RateLimit-Reset':'7'},None)
            transport=c.Transport(sidecar,opener=Opener(),monotonic=lambda:1,wall=lambda:0)
            body={'model':'fixture','unicode':'é'}
            public,native=transport(c.s.HF+'/chat/completions','fake-secret',body)
            self.assertEqual(public,{'http_status':429,'latency_seconds':0,'error':'HTTPError'})
            self.assertIsNone(native);self.assertEqual(transport.delay,601)
            self.assertEqual(requests[0].data,json.dumps(body).encode())
            self.assertEqual(requests[0].get_header('User-agent'),'swarm-alignment-pilot/0.1')
            meta=json.loads(sidecar.read_text());self.assertEqual(meta,{'http_status':429,'retry_after_seconds':601,'ratelimit_reset':7})
            self.assertNotIn('secret',sidecar.read_text());self.assertNotIn('Cookie',sidecar.read_text())

    def test_transport_serializes_actual_opens(self):
        with tempfile.TemporaryDirectory() as temporary:
            active=0;peak=0;lock=threading.Lock()
            class Reply(io.StringIO):
                status=200;headers={}
            class Opener:
                def open(self,request,timeout):
                    nonlocal active,peak
                    with lock:active+=1;peak=max(peak,active)
                    time.sleep(.005)
                    with lock:active-=1
                    return Reply('{}')
            transport=c.Transport(Path(temporary)/'sidecar',opener=Opener())
            threads=[threading.Thread(target=transport,args=(c.s.HF+'/chat/completions','fixture',{})) for _ in range(3)]
            for thread in threads:thread.start()
            for thread in threads:thread.join()
            self.assertEqual(peak,1)


if __name__=='__main__':unittest.main()
