"""Synthetic final-continuation tests; no credentials or network."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments import factorial_paced as p


class Clock:
    def __init__(self):self.now=0;self.sleeps=[]
    def __call__(self):return self.now
    def sleep(self,n):self.sleeps.append(n);self.now+=n


class PacedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.out=self.root/'runs'/'fixture-audits';self.out.mkdir(parents=True)
        self.cfg=p.s.config()
        self.jobs=[p.s.job(str(i),self.cfg['hf_model'],'Synthetic only',{'index':i}) for i in range(10)]
        self.patches=[patch.object(p.s,'ROOT',self.root),patch.object(p.s,'FREEZE',self.root/'freeze.json'),
                      patch.object(p.s,'config',return_value=self.cfg),patch.object(p.s,'folder',return_value=self.out),
                      patch.object(p.s,'verify',return_value={'valid':True}),
                      patch.object(p.c,'verify_original_sources',return_value=None),
                      patch.object(p.s,'audit_jobs',return_value=self.jobs),
                      patch.object(p.s,'credentials',return_value={'HF_TOKEN':'fake-secret'})]
        for item in self.patches:item.start()
        p.s.FREEZE.write_text('{}')
        for name in p.SOURCES:
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(name+'\n')
        report=self.root/p.CAPACITY_REPORT
        report.write_text(json.dumps(dict(complete=True,passed=True,planned=24,returned=24,unstarted=0)))
        self.ordered,self.plan=p.c.shuffled_plan(self.jobs)
        (self.out/'plan.json').write_text(json.dumps(self.plan))
        self.starts=[];self.results=[]
        for job in self.ordered[:5]:
            provider,body=p.s.body_for(job);ri,ro=p.s.rates(job['model'])
            reserve=(self.cfg['input_byte_cap']*ri+self.cfg['max_output_tokens']*ro)/1000000
            normal,known=p.s.safe_response(None,job['model'])
            self.starts.append(dict(id=job['id'],provider=provider,request_sha256=p.s.digest(body),reserved_cost=str(reserve)))
            self.results.append(dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,
                                     response=normal,known_usage=known,estimated_cost=str(reserve),native_response=None,
                                     transport={'http_status':429,'error':'HTTPError'}))
        for name,rows in [('attempts.jsonl',self.starts),('responses.jsonl',self.results)]:
            (self.out/name).write_text(''.join(json.dumps(row)+'\n' for row in rows))
        self.regpath=self.root/'registration.json';self.register()
        self.tag=patch.object(p.subprocess,'check_output',side_effect=lambda args,**kw:(self.root/args[2].split(':',1)[1]).read_bytes())
        self.tag.start()

    def tearDown(self):
        self.tag.stop()
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()

    def register(self):
        started={row['id'] for row in self.starts}
        self.record=dict(schema_version=1,registration_tag='synthetic-tag',original_freeze_sha256=p.s.sha(p.s.FREEZE),
                         source_sha256={name:p.s.sha(self.root/name) for name in p.SOURCES},
                         output_directory=self.out.relative_to(self.root).as_posix(),
                         starting=dict(attempts_sha256=p.c.raw_sha(self.out/'attempts.jsonl'),
                                       responses_sha256=p.c.raw_sha(self.out/'responses.jsonl'),
                                       attempt_count=len(self.starts),response_count=len(self.results),started_ids_sha256=p.s.digest(sorted(started)),
                                       terminal_ids_sha256=p.s.digest(sorted(started)),plan_sha256=p.c.raw_sha(self.out/'plan.json')),
                         historical_429_ids=sorted(row['id'] for row in self.results if row['transport']['http_status']==429),limits=p.LIMITS.copy(),
                         jobs_ids_sha256=p.s.digest(sorted(self.plan['ids'])),capacity_tag=p.CAPACITY_TAG,
                         capacity_results_sha256=p.c.raw_sha(self.root/p.CAPACITY_REPORT))
        self.regpath.write_text(json.dumps(self.record))

    def public(self):
        cap=SimpleNamespace(verify_results=lambda **kwargs:json.loads((self.root/p.CAPACITY_REPORT).read_text()))
        return patch.object(p.importlib,'import_module',return_value=cap)

    def fixture_verify(self,*args,**kwargs):
        # Execution-unit fixture preserves five historical rate failures. Exact
        # real-size prefix admission has separate tests below.
        starts,rows,started=p.c.ledger(self.out,self.ordered,self.plan)
        return self.record,self.ordered,self.plan,self.out,rows,started

    def run_fake(self,codes=(),callback=None,delay=0):
        clock=Clock();calls=[];status=iter(codes)
        def transport(url,key,body,timeout):
            calls.append((clock(),json.loads(json.dumps(body))))
            if callback:callback(clock,calls)
            code=next(status,200)
            native=None if code!=200 else dict(model=body['model'].rsplit(':',1)[0],
                usage=dict(prompt_tokens=10,completion_tokens=10),
                choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason='stop')])
            return dict(http_status=code,**({'error':'HTTPError'} if code!=200 else {})),native
        transport.delay=delay
        with self.public(),patch.object(p,'verify',side_effect=self.fixture_verify):
            summary=p.execute(self.regpath,transport=transport,clock=clock,sleep=clock.sleep)
        return summary,calls,clock

    def test_spacing_prefix_body_and_export_shape(self):
        old=(self.out/'responses.jsonl').read_bytes()
        summary,calls,clock=self.run_fake()
        self.assertTrue(summary['complete']);self.assertFalse(summary['halted'])
        self.assertEqual(calls[0][0],600)
        self.assertTrue(all(b[0]-a[0]>=30 for a,b in zip(calls,calls[1:])))
        self.assertEqual([body for _,body in calls],[p.s.body_for(j)[1] for j in self.ordered[5:]])
        self.assertTrue((self.out/'responses.jsonl').read_bytes().startswith(old))
        self.assertEqual(set(summary),{'planned','returned','complete','halted','unstarted','gateway_errors','incomplete','costs','freeze_sha256'})
        self.assertLessEqual(max(clock.sleeps),1)

    def test_sixth_seventh_eighth_429_cooldowns_and_no_retries(self):
        summary,calls,_=self.run_fake([429,429,429])
        self.assertTrue(summary['halted']);self.assertEqual(len(calls),3)
        self.assertEqual([t for t,_ in calls],[600,1200,2400])
        rows=p.s.rows(self.out/'responses.jsonl')
        self.assertEqual(len({row['id'] for row in rows}),8)
        self.assertEqual(sum(row['transport']['http_status']==429 for row in rows),8)
        self.assertEqual(summary['unstarted'],2)

    def test_last_fatal_terminal_is_complete_but_still_halted(self):
        summary,calls,_=self.run_fake([200,200,429,429,429])
        self.assertTrue(summary['complete']);self.assertTrue(summary['halted'])
        self.assertEqual((summary['planned'],summary['returned'],summary['unstarted']),(10,10,0))
        self.assertEqual(len(calls),5)

    def test_after_rate_error_start_interval_remains_60(self):
        _,calls,_=self.run_fake([429,200,200])
        self.assertEqual([t for t,_ in calls],[600,1200,1260,1320,1380])

    def test_longer_retry_after_is_honored(self):
        _,calls,_=self.run_fake([429],delay=1601)
        self.assertEqual(calls[1][0]-calls[0][0],1601)

    def test_slow_journal_and_helper_construction_do_not_shorten_open_gap(self):
        clock=Clock();calls=[];actual_durable=p.s.durable;slow=[True]
        def durable(file,row):
            actual_durable(file,row)
            if 'request_sha256' in row and slow[0]:clock.now+=100
        def transport(url,key,body,timeout):
            if slow[0]:clock.now+=20;slow[0]=False
            transport.opener.last_open_started=clock()
            calls.append(clock())
            return {'http_status':200},dict(model=body['model'].rsplit(':',1)[0],
                usage=dict(prompt_tokens=10,completion_tokens=10),
                choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason='stop')])
        transport.opener=SimpleNamespace(last_open_started=None,capture_failed=False)
        with self.public(),patch.object(p,'verify',side_effect=self.fixture_verify),patch.object(p.s,'durable',side_effect=durable):
            summary=p.execute(self.regpath,transport=transport,clock=clock,sleep=clock.sleep)
        self.assertTrue(summary['complete']);self.assertEqual(calls[0],720)
        self.assertTrue(all(b-a>=30 for a,b in zip(calls,calls[1:])))

    def test_gateway_retry_after_before_next_id_without_retry(self):
        clock=Clock();calls=[]
        def transport(url,key,body,timeout):
            calls.append((clock(),body))
            code=503 if len(calls)==1 else 200
            transport.opener.retry_after_delay=75 if code==503 else 0
            native=None if code==503 else dict(model=body['model'].rsplit(':',1)[0],
                usage=dict(prompt_tokens=10,completion_tokens=10),
                choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason='stop')])
            return dict(http_status=code,**({'error':'HTTPError'} if code!=200 else {})),native
        transport.opener=SimpleNamespace(last_open_started=None,retry_after_delay=0,capture_failed=False)
        with self.public(),patch.object(p,'verify',side_effect=self.fixture_verify):
            summary=p.execute(self.regpath,transport=transport,clock=clock,sleep=clock.sleep)
        self.assertTrue(summary['complete']);self.assertEqual(summary['gateway_errors'],1)
        self.assertEqual([t for t,_ in calls],[600,675,705,735,765])
        self.assertEqual(len({row['id'] for row in p.s.rows(self.out/'responses.jsonl')}),10)

    def test_private_capacity_replay_requested_only_by_private_verify(self):
        seen=[]
        def validate(**kwargs):
            seen.append(kwargs)
            return dict(complete=True,passed=True,planned=24,returned=24,unstarted=0)
        cap=SimpleNamespace(verify_results=validate)
        with patch.object(p.importlib,'import_module',return_value=cap):
            p.verify_sources(self.regpath)
            self.assertEqual(seen,[{}])
            with self.assertRaisesRegex(ValueError,'starting checkpoint'):p.verify(self.regpath)
        self.assertEqual(seen,[{},{},{'private':True}])

    def test_stop_during_wait_never_creates_queued_start(self):
        (self.out/'STOP').write_text('operator')
        summary,calls,_=self.run_fake()
        self.assertTrue(summary['halted']);self.assertEqual(calls,[])
        self.assertEqual(len(p.s.rows(self.out/'attempts.jsonl')),5)

    def test_stop_created_during_credential_io_is_checked_before_start(self):
        def credentials():
            (self.out/'STOP').write_text('operator during credential read')
            return {'HF_TOKEN':'fake-secret'}
        with patch.object(p.s,'credentials',side_effect=credentials):
            summary,calls,_=self.run_fake()
        self.assertTrue(summary['halted']);self.assertEqual(calls,[])
        self.assertEqual(len(p.s.rows(self.out/'attempts.jsonl')),5)

    def test_auth_and_other_unknown_stop_without_retry(self):
        for code in (401,402,403,400):
            with self.subTest(code=code):
                self.set_ledger_initial()
                summary,calls,_=self.run_fake([code])
                self.assertTrue(summary['halted']);self.assertEqual(len(calls),1)

    def test_nonstandard_429_and_capture_failure_stop_after_terminal(self):
        for native,capture_failed in [({'unexpected':'native'},False),(None,True)]:
            with self.subTest(native=native,capture_failed=capture_failed):
                self.set_ledger_initial();clock=Clock();calls=[]
                def transport(*args,**kwargs):
                    calls.append(args)
                    return {'http_status':429,'error':'HTTPError'},native
                transport.opener=SimpleNamespace(capture_failed=capture_failed)
                with self.public(),patch.object(p,'verify',side_effect=self.fixture_verify):
                    summary=p.execute(self.regpath,transport=transport,clock=clock,sleep=clock.sleep)
                self.assertTrue(summary['halted']);self.assertEqual(len(calls),1)
                self.assertEqual(len(p.s.rows(self.out/'attempts.jsonl')),6)
                terminal=p.s.rows(self.out/'responses.jsonl')[-1]
                self.assertEqual(terminal['transport']['http_status'],429)
                self.assertEqual(terminal['transport']['error'],'HTTPError')

    def set_ledger_initial(self):
        for name,rows in [('attempts.jsonl',self.starts),('responses.jsonl',self.results)]:
            (self.out/name).write_text(''.join(json.dumps(row)+'\n' for row in rows))

    def test_historical_reserve_and_unresolved_ids_rejected(self):
        rows=p.s.rows(self.out/'responses.jsonl');rows[0]['estimated_cost']='0'
        (self.out/'responses.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with self.assertRaisesRegex(ValueError,'reservation'):self.run_fake()
        self.set_ledger_initial();(self.out/'attempts.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError,'Unresolved'):self.run_fake()

    def test_capacity_fail_or_report_drift_blocks_public_verification(self):
        cap=SimpleNamespace(verify_results=lambda:dict(complete=True,passed=False,planned=24,returned=24,unstarted=0))
        with patch.object(p.importlib,'import_module',return_value=cap):
            with self.assertRaisesRegex(ValueError,'capacity'):p.verify_sources(self.regpath)
        (self.root/p.CAPACITY_REPORT).write_text('{}')
        with self.public():
            with self.assertRaisesRegex(ValueError,'Capacity report changed'):p.verify_sources(self.regpath)

    def test_capacity_v2_dependency_identity(self):
        self.assertEqual(p.CAPACITY_TAG,'hf-capacity-v2')
        self.assertEqual(p.CAPACITY_REPORT,'research/hf-capacity-v2-results.json')
        with self.public() as imported:p.verify_capacity(self.record)
        imported.assert_called_once_with('experiments.hf_capacity_v2')

    def test_public_verify_uses_no_private_main_contexts_or_ledgers(self):
        with (self.public(),patch.object(p.s,'verify',side_effect=AssertionError('private contexts')),
              patch.object(p.s,'audit_jobs',side_effect=AssertionError('private jobs')),
              patch.object(p.s,'rows',side_effect=AssertionError('private rows')),
              patch.object(p.s,'credentials',side_effect=AssertionError('credentials'))):
            record,out=p.verify_sources(self.regpath)
        self.assertEqual(record,self.record);self.assertEqual(out,self.out)

    def test_private_verify_rejects_wrong_real_size_checkpoint(self):
        with self.public():
            with self.assertRaisesRegex(ValueError,'starting checkpoint'):p.verify(self.regpath)

    def test_real_size_admission_and_prefix_plan_drift_rejection(self):
        self.jobs[:]=[p.s.job(str(i),self.cfg['hf_model'],'Fixture only',{'i':i}) for i in range(11640)]
        self.ordered,self.plan=p.c.shuffled_plan(self.jobs)
        (self.out/'plan.json').write_text(json.dumps(self.plan))
        self.starts=[];self.results=[]
        for index,job in enumerate(self.ordered[:9742]):
            provider,body=p.s.body_for(job);ri,ro=p.s.rates(job['model'])
            reserve=(self.cfg['input_byte_cap']*ri+self.cfg['max_output_tokens']*ro)/1000000
            native=None if index<5 else dict(model=job['model'].rsplit(':',1)[0],
                usage=dict(prompt_tokens=10,completion_tokens=10),
                choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason='stop')])
            normal,known=p.s.safe_response(native,job['model'])
            self.starts.append(dict(id=job['id'],provider=provider,request_sha256=p.s.digest(body),reserved_cost=str(reserve)))
            self.results.append(dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,
                                     response=normal,known_usage=known,
                                     estimated_cost=str(reserve if not known else (10*ri+10*ro)/1000000),
                                     native_response=native,transport=dict(http_status=429,error='HTTPError') if index<5 else dict(http_status=200)))
        self.set_ledger_initial();self.register()
        with self.public():
            _,jobs,_,_,rows,started=p.verify(self.regpath)
            self.assertEqual((len(jobs),len(rows),len(jobs)-len(started)),(11640,9742,1898))
            target=self.out/'responses.jsonl';original=target.read_bytes()
            target.write_bytes(original+b'\n')
            # Trailing blank lines are invalid ledger syntax, not resumable data.
            with self.assertRaises(ValueError):p.verify(self.regpath)
            target.write_bytes(original)
            changed=self.plan.copy();changed['planned']=11641
            (self.out/'plan.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'plan changed'):p.verify(self.regpath)

    def test_budget_includes_all_historical_reserved_costs(self):
        cfg=self.cfg.copy();cfg['hf_phase_cap']='0.001'
        with patch.object(p.s,'config',return_value=cfg):
            with self.assertRaisesRegex(ValueError,'HF cap changed'):self.run_fake()
        # Budget exhaustion is tested at the execute seam after source checks.
        clock=Clock();calls=[]
        with self.public(),patch.object(p,'verify_sources',return_value=(self.record,self.out)),\
                patch.object(p,'verify',side_effect=self.fixture_verify),patch.object(p.s,'config',return_value=cfg):
            result=p.execute(self.regpath,transport=lambda *a,**k:calls.append(a),
                             clock=clock,sleep=clock.sleep)
        self.assertTrue(result['halted']);self.assertEqual(calls,[])

    def test_exclusive_locks_refuse_second_operator(self):
        with p.exclusive_run(self.out):
            self.assertTrue((self.out/'continuation.lock').exists())
            self.assertTrue((self.out/'continuation-pacing.lock').exists())
            with self.assertRaisesRegex(ValueError,'active or stale'): 
                with p.exclusive_run(self.out):pass
            with self.assertRaisesRegex(ValueError,'active or stale'):
                with p.c.exclusive_run(self.out):pass
        (self.out/'continuation.lock').write_text('older')
        with self.assertRaisesRegex(ValueError,'Earlier'): 
            with p.exclusive_run(self.out):pass

    def test_stale_pacing_marker_preserved_and_owned_shared_lock_released(self):
        marker=self.out/'continuation-pacing.lock';marker.write_text('stale')
        with self.assertRaisesRegex(ValueError,'Paced'):
            with p.exclusive_run(self.out):pass
        self.assertEqual(marker.read_text(),'stale')
        self.assertFalse((self.out/'continuation.lock').exists())


class ErrorCaptureTests(unittest.TestCase):
    def test_error_receipt_bounded_scrubbed_and_reraised(self):
        reads=[]
        class Bounded(io.BytesIO):
            def read(self,n=-1):reads.append(n);return super().read(n)
        error=HTTPError('https://router.huggingface.co/v1/chat/completions',429,'private',
                        {'Set-Cookie':'fake-secret'},Bounded(b'fake-secret'+b'x'*30000))
        class Opener:
            def open(self,*args,**kwargs):raise error
        with tempfile.TemporaryDirectory() as name:
            opener=p.CapturingOpener(name,secrets=['fake-secret'],opener=Opener())
            with self.assertRaises(HTTPError) as caught:opener.open(None)
            self.assertIs(caught.exception,error);self.assertEqual(reads,[16384])
            receipt=(Path(name)/'error-000.json').read_text()
            self.assertNotIn('fake-secret',receipt)
            self.assertEqual(json.loads(receipt)['http_status'],429)

    def test_capture_io_failure_preserves_original_http_error(self):
        error=HTTPError('https://router.huggingface.co/v1/chat/completions',429,'private',{},io.BytesIO(b'error'))
        class Opener:
            def open(self,*args,**kwargs):raise error
        with tempfile.TemporaryDirectory() as name:
            target=Path(name)/'is-file';target.write_text('block mkdir')
            opener=p.CapturingOpener(target,opener=Opener())
            with self.assertRaises(HTTPError) as caught:opener.open(None)
            self.assertIs(caught.exception,error);self.assertTrue(opener.capture_failed)


if __name__=='__main__':unittest.main()
