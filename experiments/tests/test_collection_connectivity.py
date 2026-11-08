import io
import json
import ssl
import unittest
from http.client import BadStatusLine, IncompleteRead
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request

from experiments.collection_connectivity import (
    ConnectivityGate, ConnectivityUnavailable, blackout_end, safe_request,
)


class Clock:
    def __init__(self, iso='2026-11-08T03:00:00+00:00'):
        self.value = datetime.fromisoformat(iso).timestamp()
        self.sleeps = []
    def __call__(self):return self.value
    def sleep(self, seconds):self.sleeps.append(seconds);self.value += seconds


class Reply:
    status = 200
    def __init__(self, raw=b'{"ok":true}', error=None, headers=None):
        self.raw, self.error = raw, error
        self.headers = headers or {'Content-Type':'application/json'}
    def __enter__(self):return self
    def __exit__(self, *_):return False
    def read(self, count):
        if self.error:raise self.error
        return self.raw[:count]


class Opener:
    def __init__(self, result):self.result=result;self.calls=0
    def open(self, request, timeout):
        self.calls += 1
        if isinstance(self.result, BaseException):raise self.result
        return self.result


class ConnectivityTests(unittest.TestCase):
    def gate(self, probe=lambda:True, clock=None, **kw):
        clock = clock or Clock()
        return ConnectivityGate(probe, clock=clock, sleep=clock.sleep, **kw), clock

    def test_two_healthy_checks_then_no_extra_probes(self):
        calls=[];gate,clock=self.gate(lambda:calls.append(clock()) or True)
        self.assertFalse(gate.dispatch_allowed())
        result=gate.before_dispatch()
        self.assertEqual(result,dict(ready=True,probes=2,waited_seconds=15.))
        self.assertEqual(calls[1]-calls[0],15)
        self.assertTrue(gate.dispatch_allowed())
        self.assertEqual(gate.before_dispatch()['probes'],0)
        self.assertEqual(len(calls),2)

    def test_connection_failure_requires_new_pair_without_replaying_inference(self):
        calls=[];gate,clock=self.gate(lambda:calls.append(1) or True)
        gate.before_dispatch();gate.connection_failed()
        self.assertFalse(gate.dispatch_allowed());gate.before_dispatch()
        self.assertEqual(len(calls),4)

    def test_blackout_drains_and_rechecks_after_window(self):
        clock=Clock('2026-11-08T04:54:00+00:00');calls=[]
        gate,_=self.gate(lambda:calls.append(clock()) or True,clock)
        gate.before_dispatch();clock.value=datetime.fromisoformat('2026-11-08T04:55:00+00:00').timestamp()
        self.assertFalse(gate.dispatch_allowed());gate.before_dispatch()
        end=datetime.fromisoformat('2026-11-08T05:05:00+00:00').timestamp()
        self.assertEqual(calls[-2:],[end,end+15])
        self.assertTrue(all(not blackout_end(x) for x in calls))

    def test_failed_probe_resets_consecutive_successes(self):
        sequence=iter([True,False,True,True]);gate,clock=self.gate(lambda:next(sequence))
        result=gate.before_dispatch()
        self.assertEqual(result['probes'],4);self.assertEqual(result['waited_seconds'],45)

    def test_retry_after_skipping_whole_reset_window_still_requires_new_health(self):
        clock=Clock('2026-11-08T04:54:00+00:00');calls=[]
        gate,_=self.gate(lambda:calls.append(clock()) or True,clock)
        gate.before_dispatch()
        clock.value=datetime.fromisoformat('2026-11-08T05:09:00+00:00').timestamp()
        self.assertFalse(gate.dispatch_allowed())
        self.assertEqual(gate.before_dispatch()['probes'],2)
        self.assertEqual(len(calls),4)

    def test_pause_is_finite_even_with_never_healthy_probe(self):
        gate,clock=self.gate(lambda:False,pause_seconds=45)
        with self.assertRaisesRegex(ConnectivityUnavailable,'pause exhausted'):gate.before_dispatch()
        self.assertEqual(sum(clock.sleeps),45)

    def test_cutoff_during_blackout_never_dispatches(self):
        clock=Clock('2026-11-08T04:59:50+00:00');calls=[]
        gate,_=self.gate(lambda:calls.append(1) or True,clock,deadline='2026-11-08T05:00:00+00:00')
        with self.assertRaises(ConnectivityUnavailable):gate.before_dispatch()
        self.assertEqual(calls,[]);self.assertEqual(sum(clock.sleeps),10)
        self.assertFalse(gate.dispatch_allowed())

    def test_catalog_auth_or_model_validation_error_is_not_an_outage(self):
        def invalid():raise ValueError('Catalog validation refused')
        gate,clock=self.gate(invalid)
        with self.assertRaisesRegex(ValueError,'validation refused'):gate.before_dispatch()
        self.assertEqual(clock.sleeps,[])

    def test_request_success_once_and_no_secret_headers(self):
        opener=Opener(Reply(headers={'Content-Type':'application/json; charset=utf-8',
            'Authorization':'secret-token','X-Request-ID':'private-id','Content-Length':'11'}))
        request=Request('https://example.invalid',data=b'{}',method='POST',headers={'Authorization':'secret-token'})
        status,native,private=safe_request(opener,request,timeout=120)
        self.assertEqual(opener.calls,1);self.assertEqual(native,{'ok':True})
        self.assertEqual(status['http_status'],200);self.assertFalse(status['connection_fault'])
        self.assertEqual(status['diagnostics']['stage'],'complete')
        self.assertEqual(set(private['headers']),{'Content-Type','Content-Length'})
        self.assertNotIn('secret-token',json.dumps(status)+json.dumps(private))
        self.assertNotIn('private-id',json.dumps(status)+json.dumps(private))

    def test_http_status_survives_json_failure_and_no_raw_fragments_escape(self):
        opener=Opener(Reply(b'not-json-secret-token'))
        status,native,private=safe_request(opener,Request('https://example.invalid'),timeout=120)
        self.assertEqual(status['http_status'],200);self.assertIsNone(native)
        self.assertFalse(status['connection_fault']);self.assertEqual(private,{})
        self.assertEqual(status['diagnostics']['stage'],'json_decode')
        self.assertEqual(status['diagnostics']['exception_class'],'JSONDecodeError')
        self.assertNotIn('secret-token',json.dumps(status))
        self.assertEqual(opener.calls,1)

    def test_body_cap_failure_is_not_a_network_outage(self):
        status,native,private=safe_request(Opener(Reply(b'12345')),Request('https://example.invalid'),timeout=120,max_bytes=4)
        self.assertEqual(status['http_status'],200);self.assertFalse(status['connection_fault'])
        self.assertEqual(status['diagnostics']['stage'],'size_check')
        self.assertEqual(status['diagnostics']['body_bytes'],5);self.assertIsNone(native)

    def test_network_error_keeps_only_safe_class_and_errno_no_retry(self):
        error=URLError(OSError(10054,'secret-token connection detail'))
        opener=Opener(error)
        status,native,private=safe_request(opener,Request('https://example.invalid'),timeout=120)
        self.assertTrue(status['connection_fault']);self.assertEqual(status['http_status'],None)
        self.assertEqual(status['diagnostics']['errno'],10054)
        self.assertEqual(status['diagnostics']['exception_class'],'URLError')
        self.assertNotIn('secret-token',json.dumps(status));self.assertEqual(opener.calls,1)
        self.assertIsNone(native);self.assertEqual(private,{})

    def test_read_network_failure_preserves_received_status(self):
        status,_,_=safe_request(Opener(Reply(error=OSError(10054,'secret'))),Request('https://example.invalid'),timeout=120)
        self.assertEqual(status['http_status'],200);self.assertTrue(status['connection_fault'])
        self.assertEqual(status['diagnostics']['stage'],'read')

    def test_tls_certificate_failure_is_fatal_not_connectivity_recovery(self):
        status,_,_=safe_request(Opener(URLError(ssl.SSLError('secretTLS'))),Request('https://example.invalid'),timeout=120)
        self.assertFalse(status['connection_fault']);self.assertEqual(status['diagnostics']['reason_class'],'SSLError')
        self.assertNotIn('secretTLS',json.dumps(status))

    def test_incomplete_read_is_recorded_without_partial_text_or_retry(self):
        opener=Opener(Reply(error=IncompleteRead(b'private-fragment',20)))
        status,native,private=safe_request(opener,Request('https://example.invalid'),timeout=120)
        self.assertEqual(status['http_status'],200);self.assertTrue(status['connection_fault'])
        self.assertEqual(status['diagnostics']['body_bytes'],16)
        self.assertEqual(status['diagnostics']['exception_class'],'IncompleteRead')
        self.assertNotIn('private-fragment',json.dumps(status));self.assertIsNone(native)
        self.assertEqual(opener.calls,1)

    def test_bad_status_line_is_fatal_protocol_error_not_connectivity(self):
        status,_,_=safe_request(Opener(BadStatusLine('secret-status')),Request('https://example.invalid'),timeout=120)
        self.assertFalse(status['connection_fault'])
        self.assertEqual(status['diagnostics']['exception_class'],'BadStatusLine')
        self.assertNotIn('secret-status',json.dumps(status))

    def test_http_error_retains_bounded_private_body_and_allowlisted_retry_after(self):
        error=HTTPError('https://example.invalid',429,'private reason',
            {'Retry-After':'60','Authorization':'secret','X-Request-ID':'private'},io.BytesIO(b'{"error":"server overload"}'))
        opener=Opener(error)
        status,native,private=safe_request(opener,Request('https://example.invalid'),timeout=120)
        self.assertEqual(status['http_status'],429);self.assertEqual(status['error'],'HTTPError')
        self.assertFalse(status['connection_fault']);self.assertIsNone(native)
        self.assertEqual(private['headers'],{'Retry-After':'60'})
        self.assertIn('server overload',private['error_body']);self.assertEqual(opener.calls,1)
        self.assertNotIn('private',json.dumps(status));self.assertNotIn('secret',json.dumps(status))


if __name__=='__main__':unittest.main()
