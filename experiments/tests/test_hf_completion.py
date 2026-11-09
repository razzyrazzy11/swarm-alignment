"""Synthetic safety/recovery tests; no keys, serving calls or empirical answers."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments import hf_completion as h


class Clock:
    def __init__(self):self.t=0
    def __call__(self):return self.t
    def sleep(self,n):self.t+=n


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.original=self.root/'original';self.original.mkdir()
        self.clock=Clock();cfg=h.s.config()
        self.jobs=[h.s.job(str(i),cfg['hf_model'],'Synthetic fixture',{'i':i}) for i in range(12)]
        self.registration=dict(pending=[h.descriptor(j) for j in self.jobs],historical_429_ids=list('abcde'))
        self.catalog=self.root/'catalog.json';self.catalog.write_text('{}')
        self.freeze=self.root/'freeze.json';self.freeze.write_text('{}')
        self.patches=[patch.object(h,'ROOT',self.root),patch.object(h,'CATALOG',self.catalog),
                      patch.object(h,'FREEZE',self.freeze),patch.object(h,'config',side_effect=lambda:dict(h.FIXED)),
                      patch.object(h,'verify',side_effect=lambda:self.registration),
                      patch.object(h,'original_prefix',side_effect=lambda **kw:(self.jobs,list('abcde'))),
                      patch.object(h,'metadata',return_value={}),
                      patch.object(h,'keys',return_value={'HF_TOKEN':'fake-HF','ADAPTION_API_KEY':'fake-AD','OLLAMA_API_KEY':'fake-OL'}),
                      patch.object(h.s,'folder',return_value=self.original)]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def transport(self,codes=None,finish='stop',model=None):
        test=self;codes=list(codes or [200]*len(self.jobs))
        class Transport:
            def __init__(self):
                self.calls=[];self.opener=SimpleNamespace(last_open_started=None,service_overload=False,
                                                        capture_failed=False,retry_after_delay=0,last_receipt=None)
            def __call__(self,url,key,body,timeout):
                self.calls.append((test.clock(),body));self.opener.last_open_started=test.clock()
                test.clock.sleep(2);code=codes.pop(0)
                self.opener.service_overload=code=='overload';self.opener.last_receipt=None
                if code!=200:
                    code=429 if code=='overload' else code
                    record=dict(http_status=code,error_body=json.dumps({'error':'Server overloaded'} if self.opener.service_overload else {'error':'limit'}))
                    directory=h.folder()/'private-errors';directory.mkdir(exist_ok=True)
                    path=directory/f'error-{len(self.calls):06d}.json';path.write_text(json.dumps(record))
                    self.opener.last_receipt=dict(file='private-errors/'+path.name,sha256=h.raw_sha(path))
                    return dict(http_status=code,error='HTTPError'),None
                native=dict(model=model or body['model'].rsplit(':',1)[0],
                            choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason=finish)],
                            usage=dict(prompt_tokens=10,completion_tokens=10))
                return dict(http_status=200),native
        return Transport()

    def run_fixture(self,transport,resume=False):
        return h.execute(resume,transport,self.clock,self.clock.sleep)

    def test_exact_bodies_actual_spacing_and_original_untouched(self):
        marker=self.original/'history';marker.write_text('immutable')
        t=self.transport();result=self.run_fixture(t)
        self.assertTrue(result['complete']);self.assertEqual(result['returned'],12)
        self.assertEqual([body for _,body in t.calls],[h.s.body_for(j)[1] for j in self.jobs])
        self.assertTrue(all(b[0]-a[0]>=30 for a,b in zip(t.calls,t.calls[1:])))
        self.assertEqual(marker.read_text(),'immutable')
        self.assertEqual(result['historical_429_preserved'],5)
        self.assertFalse((self.original/'continuation.lock').exists())

    def test_overload_backoff_circuit_and_full_reservation(self):
        t=self.transport(['overload']*8+[200]*4);result=self.run_fixture(t)
        self.assertTrue(result['complete']);self.assertEqual(result['new_transient_errors'],8)
        self.assertGreaterEqual(t.calls[8][0]-t.calls[7][0],602)
        self.assertGreaterEqual(t.calls[1][0]-t.calls[0][0],62)
        rows=h.s.rows(h.folder()/'responses.jsonl')
        self.assertEqual(rows[0]['estimated_cost'],str(h.reservation(self.jobs[0])))
        self.assertEqual(len(h.supplement_ledger(h.folder(),self.jobs,h.s.read(h.folder()/'plan.json'))[1]),12)

    def test_unknown_429_auth_payment_and_profile_drift_halt_without_retry(self):
        for code,model in [(429,None),(401,None),(402,None),(200,'wrong-model')]:
            with self.subTest(code=code,model=model):
                out=h.folder()
                if out.exists():
                    # Each case owns a separate temporary root; no filesystem deletion.
                    self.root=self.root/'next';self.root.mkdir()
                    self.patches.append(patch.object(h,'ROOT',self.root));self.patches[-1].start()
                t=self.transport([code],model=model);result=self.run_fixture(t)
                self.assertTrue(result['halted']);self.assertEqual(len(t.calls),1)
                with self.assertRaises(ValueError):self.run_fixture(self.transport(),True)

    def test_known_truncation_is_retained_not_score_selected(self):
        t=self.transport(finish='length');result=self.run_fixture(t)
        self.assertTrue(result['complete']);self.assertEqual(len(t.calls),12)

    def test_budget_gate_before_first_start(self):
        with patch.object(h,'config',return_value={**h.FIXED,'new_estimated_cost_cap':'0.00001'}):
            t=self.transport();result=self.run_fixture(t)
        self.assertEqual(result['stop_reason'],'budget');self.assertEqual(t.calls,[])
        self.assertEqual(h.s.rows(h.folder()/'attempts.jsonl'),[])

    def test_new_allowance_is_separate_and_never_resets_old_errors(self):
        with patch.object(h,'config',return_value={**h.FIXED,'new_transient_allowance':8}):
            t=self.transport(['overload']*12);result=self.run_fixture(t)
        self.assertEqual(len(t.calls),8);self.assertEqual(result['new_transient_errors'],8)
        self.assertEqual(result['historical_429_preserved'],5)
        self.assertEqual(result['stop_reason'],'transient_allowance')

    def test_start_pacing_uses_actual_opener_after_slow_journal(self):
        original=h.s.durable
        def delayed(file,value):
            if file.name.endswith('attempts.jsonl'):self.clock.sleep(41)
            original(file,value)
        t=self.transport()
        with patch.object(h.s,'durable',side_effect=delayed):self.run_fixture(t)
        self.assertTrue(all(b[0]-a[0]>=30 for a,b in zip(t.calls,t.calls[1:])))

    def test_operator_stop_and_resume_only_never_started(self):
        t=self.transport();original=t.__class__.__call__
        def stopping(obj,*args,**kw):
            result=original(obj,*args,**kw)
            if len(obj.calls)==2:(h.folder()/'STOP').write_text('stop')
            return result
        with patch.object(t.__class__,'__call__',stopping):first=self.run_fixture(t)
        self.assertEqual(first['returned'],2);self.assertEqual(first['stop_reason'],'operator_stop')
        (h.folder()/'STOP').unlink();t2=self.transport();second=self.run_fixture(t2,True)
        self.assertTrue(second['complete']);self.assertEqual(len(t2.calls),10)
        self.assertEqual(t2.calls[0][1],h.s.body_for(self.jobs[2])[1])

    def test_unresolved_start_and_private_capture_tampering_fail_closed(self):
        t=self.transport(['overload']+[200]*11);self.run_fixture(t)
        path=next((h.folder()/'private-errors').glob('*.json'));path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'capture changed'):self.run_fixture(self.transport(),True)
        path.write_text('{}')
        with (h.folder()/'attempts.jsonl').open('a') as f:f.write(json.dumps({'id':'unresolved'})+'\n')
        with self.assertRaisesRegex(ValueError,'Unresolved'):self.run_fixture(self.transport(),True)

    def test_existing_original_lock_is_preserved(self):
        lock=self.original/'continuation.lock';lock.write_text('other-owner')
        with self.assertRaises(ValueError):self.run_fixture(self.transport())
        self.assertEqual(lock.read_text(),'other-owner')

    def test_reordered_terminal_journal_is_rejected(self):
        self.run_fixture(self.transport());path=h.folder()/'responses.jsonl'
        lines=path.read_text().splitlines();lines[0],lines[1]=lines[1],lines[0]
        path.write_text('\n'.join(lines)+'\n')
        with self.assertRaisesRegex(ValueError,'dispatch order'):self.run_fixture(self.transport(),True)


class ErrorCaptureTests(unittest.TestCase):
    def test_only_explicit_overload_exempted(self):
        self.assertTrue(h.explicit_overload(429,'{"error":"Server overloaded, retry"}'))
        self.assertTrue(h.explicit_overload(429,'{"error":{"code":"server_overload"}}'))
        for status,body in [(429,'rate limit'),(429,'{"error":"quota exceeded"}'),
                            (429,'{"error":"not server overload"}'),(503,'{"error":"Server overloaded"}')]:
            self.assertFalse(h.explicit_overload(status,body))

    def test_error_receipt_scrubs_all_keys_and_honors_retry_after(self):
        with tempfile.TemporaryDirectory() as temp:
            body=b'{"error":"Server overloaded","echo":"secret-HF secret-AD secret-OL"}'
            error=HTTPError('https://example.invalid',429,'busy',{'Retry-After':'121'},io.BytesIO(body))
            backend=SimpleNamespace(open=lambda *a,**kw:(_ for _ in ()).throw(error))
            opener=h.CapturingOpener(Path(temp),['secret-HF','secret-AD','secret-OL'],lambda:7,backend)
            with self.assertRaises(HTTPError):opener.open(None)
            self.assertTrue(opener.service_overload);self.assertFalse(opener.capture_failed)
            self.assertEqual(opener.last_open_started,7);self.assertEqual(opener.retry_after_delay,121)
            text=next(Path(temp).glob('*.json')).read_text()
            for key in ('secret-HF','secret-AD','secret-OL'):self.assertNotIn(key,text)
            self.assertIsNotNone(opener.last_receipt)

    def test_capture_failure_cannot_be_exempted(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'file';path.write_text('cannot-create-directory-here')
            error=HTTPError('https://example.invalid',429,'busy',{},io.BytesIO(b'{"error":"Server overloaded"}'))
            backend=SimpleNamespace(open=lambda *a,**kw:(_ for _ in ()).throw(error))
            opener=h.CapturingOpener(path,[],lambda:0,backend)
            with self.assertRaises(HTTPError):opener.open(None)
            self.assertTrue(opener.capture_failed);self.assertIsNone(opener.last_receipt)


class PublicVerificationTests(unittest.TestCase):
    def test_public_verification_never_reads_keys_raw_ledgers_or_calls_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);freeze=root/'research/registration.json';freeze.parent.mkdir();freeze.write_bytes(b'x')
            checkpoint=root/h.CHECKPOINT;checkpoint.write_bytes(b'x')
            original=root/'original.json';original.write_bytes(b'x')
            names=('source.py',);(root/names[0]).write_bytes(b'x')
            pending=[dict(id=str(i),model='m',provider='hf',metadata={},request_sha256='q') for i in range(1898)]
            record=dict(schema_version=1,tag=h.TAG,base_commit='base',source_sha256={'source.py':'hash'},
                        checkpoint_sha256='hash',original_freeze_sha256='hash',snapshot_tag=h.SNAPSHOT,
                        snapshot_manifest_sha256='manifesthash',historical_429_ids=list('abcde'),pending=pending,timing='after outcomes')
            def forbidden(*args,**kwargs):raise AssertionError('private or network access')
            patches=[patch.object(h,'ROOT',root),patch.object(h,'FREEZE',freeze),patch.object(h,'SOURCES',names),
                     patch.object(h.s,'FREEZE',original),patch.object(h.s,'read',return_value=record),
                     patch.object(h.s,'sha',return_value='hash'),patch.object(h,'config',return_value=h.FIXED),
                     patch.object(h.c,'verify_original_sources'),patch.object(h,'blob',return_value=b'x'),
                     patch.object(h.subprocess,'run',return_value=SimpleNamespace(returncode=0)),
                     patch.object(h,'snapshot',return_value=({}, {j['id']:j for j in pending},'manifesthash')),
                     patch.object(h,'keys',side_effect=forbidden),patch.object(h,'original_prefix',side_effect=forbidden),
                     patch.object(h,'metadata',side_effect=forbidden),patch.object(h,'urlopen',side_effect=forbidden)]
            for p in patches:p.start()
            try:
                self.assertIs(h.verify(),record)
                record['pending'][0]['request_sha256']='changed'
                # The snapshot is an independent immutable commitment.
                with patch.object(h,'snapshot',return_value=({}, {**{j['id']:j for j in pending},'0':{**pending[0],'request_sha256':'original'}},'manifesthash')):
                    with self.assertRaises(ValueError):h.verify()
            finally:
                for p in reversed(patches):p.stop()


if __name__=='__main__':unittest.main()
