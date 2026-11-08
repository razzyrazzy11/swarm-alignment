"""Synthetic pilot control tests; no API calls or empirical outcomes."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from collections import Counter
import json,ssl,tempfile,threading,time,unittest
from urllib.error import URLError
from experiments import adaption_serving_pilot as p

class Clock:
    def __init__(self):self.value=0.;self.lock=threading.Lock()
    def __call__(self):
        with self.lock:return self.value
    def sleep(self,n):
        with self.lock:self.value+=max(0,n)
class Gate:
    def __init__(self):self.checks=0;self.failures=0
    def before_dispatch(self,force_health=False):self.checks+=1
    def dispatch_allowed(self):return True
    def connection_failed(self):self.failures+=1

def native(body):return dict(model=body['model'],status='completed',output_text=json.dumps(dict(claimed_done=True,note='Scripted format only.')),
    usage=dict(input_tokens=10,output_tokens=12))

class PilotTests(unittest.TestCase):
    def test_exact_factorial_grid_and_determinism(self):
        a=p.plan();self.assertEqual(a,p.plan());self.assertEqual(len(a['jobs']),16)
        cells=Counter((x['profile_id'],x['metadata']['mode'],x['metadata']['concurrency']) for x in a['jobs'])
        self.assertEqual(len(cells),8);self.assertEqual(set(cells.values()),{2})
        self.assertTrue(all(x['id'].startswith(p.TAG+':') for x in a['jobs']))
    def test_generation_body_only_stream_differs(self):
        jobs=p.plan()['jobs']
        for profile in ('q27','q397'):
            for k in (1,2):
                for index in (0,1):
                    same=[x for x in jobs if x['profile_id']==profile and x['metadata']['concurrency']==k and x['metadata']['input_index']==index]
                    bodies=[dict(x['body']) for x in same];modes=[b.pop('stream') for b in bodies]
                    self.assertEqual(bodies[0],bodies[1]);self.assertEqual(set(modes),{True,False})
                    self.assertEqual(bodies[0]['max_output_tokens'],4096);self.assertIs(bodies[0]['store'],False)
    def test_full_reservations_fit_before_any_request(self):
        from decimal import Decimal
        v=p.plan();total=sum(Decimal(x['reserved_cost']) for x in v['jobs'])
        self.assertEqual(total,Decimal(v['full_reservation_credits']));self.assertLessEqual(total,Decimal('1'))
        self.assertLessEqual(total+Decimal(p.POLICY['prior_excluded_credits']),Decimal('10'))
    def test_primary_and_postprocess_must_be_complete_real_states(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in p.DRIVERS:
                q=root/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(dict(status='complete',pid=111,child_pid=None,updated='2026-01-01T00:00:00+00:00')))
            with patch.object(p,'ROOT',root),patch('experiments.swarm_ledger_complete_dispatch.process_dead') as dead:
                proof=p.primary_complete();self.assertEqual(len(proof),3);self.assertEqual(dead.call_count,3)
                q=root/p.DRIVERS[-1];v=json.loads(q.read_text());v['status']='processing';q.write_text(json.dumps(v))
                with self.assertRaises(ValueError):p.primary_complete()
    def test_stale_collector_lock_blocks_without_removal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in p.DRIVERS:
                q=root/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(dict(status='complete',pid=111,child_pid=None,updated='2026-01-01T00:00:00+00:00')))
            lock=root/'runs/other/collector.lock';lock.parent.mkdir(parents=True);lock.write_text('owner')
            with patch.object(p,'ROOT',root),patch('experiments.swarm_ledger_complete_dispatch.process_dead'):
                with self.assertRaises(ValueError):p.primary_complete()
            self.assertEqual(lock.read_text(),'owner')
    def test_run_refuses_before_primary_without_loading_credentials(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'ROOT',Path(d)),patch.object(p,'verify',return_value={}),patch.object(p,'primary_complete',side_effect=ValueError('priority')),patch.object(p.s,'credentials') as creds:
            with self.assertRaises(ValueError):p.run()
            creds.assert_not_called();self.assertFalse(p.folder().exists())
    def test_secondary_cutoff_has_full45minute_reserve(self):
        end=datetime.fromisoformat(p.POLICY['cutoff_utc'])
        self.assertTrue(p.fits_window(end-timedelta(seconds=2701)))
        self.assertFalse(p.fits_window(end-timedelta(seconds=2700)))
        self.assertEqual(p.POLICY['primary_cutoff_unchanged'],'2026-11-09T05:59:00+00:00')
    def test_catalog_tls_failure_is_not_outage_retry(self):
        class Opener:
            def open(self,*a,**kw):raise URLError(ssl.SSLError('secret must not escape'))
        with self.assertRaisesRegex(ValueError,'Catalog TLS failure'):p.catalog_probe('privatekey',Opener())
    def test_watchdog_state_requires_actual_parent_child(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);q=root/p.POLICY['watchdog_driver_state'];q.parent.mkdir(parents=True)
            q.write_text(json.dumps(dict(status='running',pid=999,child_pid=998,watchdog_deadline_utc='2026-11-09T09:30:00+00:00')))
            with patch.object(p,'ROOT',root):
                with self.assertRaises(ValueError):p.watchdog_ready()
    def run_fixture(self,error=False):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name);out=root/'runs'/p.TAG;out.mkdir(parents=True)
        freeze=root/'freeze.json';freeze.write_text('{}');clock=Clock();gate=Gate();calls=[];active=[0,0];lock=threading.Lock()
        def request(body,key,stream,timeout):
            with lock:active[0]+=1;active[1]=max(active[1],active[0]);calls.append((body,stream,timeout))
            time.sleep(.001)
            with lock:active[0]-=1
            if error and len(calls)==1:return dict(http_status=504,error='HTTPError',latency_seconds=60),None,dict(error_body='Gateway time-out',headers={'Retry-After':'2'})
            n=native(body);return dict(http_status=200,latency_seconds=2),n,dict(native_response=n,headers={})
        with patch.object(p,'ROOT',root),patch.object(p,'FREEZE',freeze):summary=p._run(p.plan(),'privatekey',request,gate,clock,clock.sleep)
        return root,summary,calls,active,gate
    def test_one_shot_matrix_captures16_distinct_attempts(self):
        root,summary,calls,active,gate=self.run_fixture()
        self.assertTrue(summary['complete']);self.assertEqual(len(calls),16);self.assertLessEqual(active[1],2);self.assertEqual(gate.checks,4)
        rows=p.s.rows(root/'runs'/p.TAG/'attempts.jsonl');self.assertEqual(len({r['id'] for r in rows}),16)
        self.assertTrue(all(r['submitted_active_at_dispatch']<=r['metadata']['concurrency'] for r in rows))
    def test_failed_delivery_kept_once_full_reservation_no_retries(self):
        root,summary,calls,active,gate=self.run_fixture(error=True)
        rows=p.s.rows(root/'runs'/p.TAG/'responses.jsonl');bad=[r for r in rows if r['transport']['http_status']==504]
        self.assertTrue(summary['complete']);self.assertEqual(len(calls),16);self.assertEqual(len(bad),1)
        self.assertFalse(bad[0]['known_usage']);self.assertEqual(bad[0]['transport']['retry_after_seconds'],2)
        attempts={r['id']:r for r in p.s.rows(root/'runs'/p.TAG/'attempts.jsonl')}
        self.assertEqual(bad[0]['estimated_cost'],attempts[bad[0]['id']]['reserved_cost'])
    def test_fatal_group_stops_later_probes_and_drains_each_send_once(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'runs'/p.TAG;out.mkdir(parents=True);freeze=root/'freeze.json';freeze.write_text('{}')
            designed=p.plan();designed['schedule'].sort(key=lambda g:-g['concurrency']);clock=Clock();gate=Gate();calls=[];writes=[];real=p.s.durable
            def request(body,key,stream,timeout):
                calls.append(1)
                if len(calls)==1:return dict(http_status=401,error='HTTPError'),None,dict(headers={})
                time.sleep(.01);n=native(body);return dict(http_status=200),n,dict(native_response=n,headers={})
            def durable(path,value):
                if path.name=='responses.jsonl':
                    writes.append(value['id'])
                    if len(writes)==2:raise OSError('synthetic capture failure')
                return real(path,value)
            with patch.object(p,'ROOT',root),patch.object(p,'FREEZE',freeze),patch.object(p.s,'durable',side_effect=durable):
                with self.assertRaisesRegex(ValueError,'Capture failed'):p._run(designed,'key',request,gate,clock,clock.sleep)
            self.assertEqual(gate.checks,1);self.assertEqual(len(calls),2);self.assertEqual(len(writes),2);self.assertEqual(len(set(writes)),2)
            self.assertEqual(len(p.s.rows(out/'attempts.jsonl')),2);self.assertEqual(len(p.s.rows(out/'responses.jsonl')),1)
    def test_no_pilot_summary_can_hide_repeated_identity(self):
        designed=p.plan();ids=[j['id'] for j in designed['jobs']];self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(all(j['request_sha256']==p.s.digest(j['body']) for j in designed['jobs']))
    def prepare_analysis(self,error=False):
        root,summary,*_=self.run_fixture(error);out=root/'runs'/p.TAG
        (out/'plan.json').write_text(json.dumps(p.plan()));(out/'summary.json').write_text(json.dumps(summary))
        return root,out
    def test_analysis_replays_native_cost_and_retains_failure_counts(self):
        root,out=self.prepare_analysis(error=True)
        with patch.object(p,'ROOT',root),patch.object(p,'FREEZE',root/'freeze.json'),patch.object(p,'REPORT',root/'report.json'),patch.object(p,'verify'),patch.object(p,'analysis_idle',return_value={'status':'processing'}):
            self.assertTrue(p.analyze()['exported'])
        report=json.loads((root/'report.json').read_text());self.assertEqual(sum(c['terminals'] for c in report['cells'].values()),16)
        self.assertEqual(sum(c['http_504'] for c in report['cells'].values()),1);self.assertEqual(report['independent_fixed_inputs'],2)
        self.assertEqual(report['unresolved_started_requests'],0);self.assertEqual(report['inference_calls'],0)
    def test_analysis_rejects_cost_tamper(self):
        root,out=self.prepare_analysis(error=True);rows=p.s.rows(out/'responses.jsonl');rows[0]['estimated_cost']='0'
        (out/'responses.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
        with patch.object(p,'ROOT',root),patch.object(p,'FREEZE',root/'freeze.json'),patch.object(p,'REPORT',root/'report.json'),patch.object(p,'verify'),patch.object(p,'analysis_idle',return_value={'status':'processing'}):
            with self.assertRaises(ValueError):p.analyze()
        self.assertFalse((root/'report.json').exists())
    def test_watchdog_partial_does_not_invent_terminal_and_holds_reservation(self):
        root,out=self.prepare_analysis();(out/'summary.json').unlink();rows=p.s.rows(out/'responses.jsonl')
        (out/'responses.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows[:-1]))
        state=dict(status='stopped',reason='watchdog_timeout',pilot_child_pid=999,updated='2026-01-01T00:00:00+00:00')
        with patch.object(p,'ROOT',root),patch.object(p,'FREEZE',root/'freeze.json'),patch.object(p,'REPORT',root/'report.json'),patch.object(p,'verify'),patch.object(p,'analysis_idle',return_value=state),patch('experiments.swarm_ledger_complete_dispatch.process_dead'):
            p.analyze()
        report=json.loads((root/'report.json').read_text());self.assertEqual(report['status'],'partial_interrupted')
        self.assertEqual(report['summary']['terminal'],15);self.assertEqual(report['unresolved_started_requests'],1)
        self.assertFalse(report['summary']['complete']);self.assertFalse(report['collector_summary_present'])
        self.assertGreater(float(report['unresolved_full_reservation_credits']),0)

if __name__=='__main__':unittest.main()
