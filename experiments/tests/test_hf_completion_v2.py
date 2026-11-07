"""Synthetic recovery checks; no empirical journals, credentials or API calls."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments import hf_completion_v2 as v
from experiments.tests.test_hf_completion import Clock


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.original=self.root/'original';self.original.mkdir();self.clock=Clock()
        self.freeze=self.root/'freeze.json';self.freeze.write_text('{}')
        self.catalog=self.root/'catalog.json';self.catalog.write_text('{}')
        self.jobs=[v.s.job(str(i),v.s.config()['hf_model'],'Synthetic',dict(i=i)) for i in range(10)]
        self.registration=dict(pending=[v.h.descriptor(j) for j in self.jobs],prior_raw_sha256={},prior_estimated_cost='.01')
        self.patches=[patch.object(v,'ROOT',self.root),patch.object(v,'FREEZE',self.freeze),
            patch.object(v,'verify',side_effect=lambda:self.registration),
            patch.object(v,'prior_prefix',side_effect=lambda *a,**k:(self.jobs,[],{},1)),
            patch.object(v.h,'CATALOG',self.catalog),patch.object(v.h,'metadata',return_value={}),
            patch.object(v.h,'keys',return_value={'HF_TOKEN':'synthetic-key'}),
            patch.object(v.s,'folder',return_value=self.original)]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def transport(self,codes=None):
        codes=list(codes or [200]*len(self.jobs));test=self
        class Transport:
            def __init__(self):
                self.calls=[];self.opener=SimpleNamespace(last_open_started=None,service_overload=False,
                    capture_failed=False,retry_after_delay=5,last_receipt=None)
            def __call__(self,url,key,body,timeout):
                self.calls.append((test.clock(),body));self.opener.last_open_started=test.clock();test.clock.sleep(2)
                code=codes.pop(0);self.opener.service_overload=code=='overload';self.opener.last_receipt=None
                if code!=200:
                    code=429 if code=='overload' else code
                    record=dict(http_status=code,error_body=json.dumps(dict(type='server_overload',message='server overload, retry') if self.opener.service_overload else dict(error='quota')))
                    directory=v.folder()/'private-errors';directory.mkdir(exist_ok=True)
                    path=directory/f'error-{len(self.calls):06d}.json';path.write_text(json.dumps(record))
                    self.opener.last_receipt=dict(file='private-errors/'+path.name,sha256=v.h.raw_sha(path))
                    return dict(http_status=code,error='HTTPError'),None
                native=dict(model=body['model'].rsplit(':',1)[0],choices=[dict(message=dict(content='{"status":"NONE","worker_id":null}'),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=10))
                return dict(http_status=200),native
        return Transport()

    def run_fixture(self,t,resume=False):return v.execute(resume,t,self.clock,self.clock.sleep)

    def test_spacing_exact_bodies_and_prior_journal_untouched(self):
        marker=self.original/'prior-journal';marker.write_text('immutable-nine')
        t=self.transport();result=self.run_fixture(t)
        self.assertTrue(result['complete']);self.assertEqual(result['new_transient_errors'],1)
        self.assertEqual([body for _,body in t.calls],[v.s.body_for(j)[1] for j in self.jobs])
        self.assertTrue(all(b[0]-a[0]>=30 for a,b in zip(t.calls,t.calls[1:])))
        self.assertEqual(marker.read_text(),'immutable-nine')

    def test_top_level_overloads_backoff_circuit_and_full_reservation(self):
        t=self.transport(['overload']*8+[200]*2);result=self.run_fixture(t)
        self.assertTrue(result['complete']);self.assertEqual(result['new_transient_errors'],9)
        self.assertGreaterEqual(t.calls[1][0]-t.calls[0][0],62)
        self.assertGreaterEqual(t.calls[8][0]-t.calls[7][0],602)
        rows=v.s.rows(v.folder()/'responses.jsonl')
        self.assertEqual(rows[0]['estimated_cost'],str(v.h.reservation(self.jobs[0])))
        v.supplement_ledger(v.folder(),self.jobs,v.s.read(v.folder()/'plan.json'))

    def test_unknown_429_halts_without_retry_or_resume(self):
        t=self.transport([429]);result=self.run_fixture(t)
        self.assertTrue(result['halted']);self.assertEqual(len(t.calls),1)
        with self.assertRaises(ValueError):self.run_fixture(self.transport(),True)

    def test_combined_prior_cost_gate_and_unresolved_start(self):
        self.registration['prior_estimated_cost']='2.50'
        t=self.transport();result=self.run_fixture(t)
        self.assertEqual(result['stop_reason'],'budget');self.assertEqual(t.calls,[])
        with (v.folder()/'attempts.jsonl').open('a') as file:file.write('{"id":"unresolved"}\n')
        with self.assertRaisesRegex(ValueError,'Unresolved'):self.run_fixture(self.transport(),True)

    def test_changed_prior_prefix_stops_before_request(self):
        with patch.object(v,'prior_prefix',return_value=(self.jobs,[],{'changed':'hash'},1)):
            t=self.transport()
            with self.assertRaises(ValueError):self.run_fixture(t)
            self.assertEqual(t.calls,[])

    def test_top_level_error_capture_is_private_and_scrubbed(self):
        body=b'{"type":"server_overload","message":"server overload, trace_id: private secret"}'
        error=HTTPError('https://example.invalid',429,'busy',{'Retry-After':'5'},io.BytesIO(body))
        backend=SimpleNamespace(open=lambda *a,**kw:(_ for _ in ()).throw(error))
        opener=v.CapturingOpener(self.root/'private-errors',['secret'],lambda:7,backend)
        with self.assertRaises(HTTPError):opener.open(None)
        self.assertTrue(opener.service_overload);self.assertFalse(opener.capture_failed)
        self.assertEqual(opener.retry_after_delay,5)
        self.assertEqual(opener.last_receipt['file'],'private-errors/error-000000.json')
        self.assertNotIn('secret',(self.root/opener.last_receipt['file']).read_text())
        error.close()

    def test_classifier_is_narrow_and_preserves_original_profiles(self):
        self.assertTrue(v.explicit_overload(429,'{"type":"server_overload","message":"server overload, try later"}'))
        self.assertTrue(v.explicit_overload(429,'{"error":{"code":"server_overload"}}'))
        for status,body in ((429,'{"type":"rate_limit","message":"quota"}'),(429,'{"type":"server_overload","message":"quota"}'),(429,'{"message":"server overload"}'),(503,'{"type":"server_overload","message":"server overload"}')):
            self.assertFalse(v.explicit_overload(status,body))


if __name__=='__main__':unittest.main()
