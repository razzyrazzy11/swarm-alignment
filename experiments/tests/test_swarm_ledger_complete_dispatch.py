"""Offline fixed-capacity and durable-accounting regressions."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments import swarm_ledger_complete_dispatch as d
from experiments import swarm_ledger_study as old


def fake_job():
    job=deepcopy(next(j for j in old.technical_jobs() if j['profile_id']=='g26'));job['id']='complete-test-job';return job

def native_row(out,job,http=200):
    p=old.profile(job['profile_id']);native={'model':p['model'],'status':'completed','output_text':'not a verdict','usage':{'input_tokens':10,'output_tokens':5}}
    receipt={'native_response':native} if http==200 else {'error_body':'temporary capacity','headers':{}}
    path=out/'native'/(old.digest(job['id'])+'.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(receipt))
    response,known,anomaly=old.normalize(native if http==200 else None,p)
    return {'id':job['id'],'profile_id':job['profile_id'],'metadata':job['metadata'],'transport':{'http_status':http,'latency_seconds':1},'response':response,'known_usage':known,'anomaly':anomaly,'native_receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'estimated_cost':str(old.actual_cost(job,response) if known else old.reservation(job))}

def execution_fixture():
    c=old.config();c['gateway_allowance']=1024;c['max_active']=8;c['provider_max_active']={'adaption':8,'hf':2,'ollama':2};c['dispatch_model_limits']={'adaption':2,'hf':2,'ollama':2};c['combined_caps']['adaption']='830.25';c['_operational_config_sha256']=d.sha(d.CONFIG);return c

class FixedDispatchTests(unittest.TestCase):
    def test_forecast_source_hash_and_fixed_gate_tampering_fail_closed(self):
        from experiments.swarm_ledger_complete_forecast import build
        from experiments.tests.test_swarm_ledger_complete_forecast import fixture
        inputs=fixture();inputs['science_config']=d.s.config();inputs['development_freeze_sha256']=old.sha(old.freeze_path('development'))
        value=build(inputs,'2026-11-07T00:00:00+00:00',Decimal('100'))
        with patch.object(d,'pilot_public_metadata',return_value=value['pilot_cost_lineage']):
            self.assertTrue(d.validate_forecast(deepcopy(value))['candidates'][0]['deadline_feasible'])
            for field in ('science_config_sha256','forecast_source_sha256'):
                changed=deepcopy(value);changed[field]='0'*64
                with self.assertRaisesRegex(ValueError,'configuration/source drift'):d.validate_forecast(changed)
            changed=deepcopy(value);changed['candidates'][0]['phase_bounds'][0]['projected_known_transient_total']='1200'
            with self.assertRaisesRegex(ValueError,'transient arithmetic'):d.validate_forecast(changed)
            changed=deepcopy(value);changed['candidates'][0]['native_per_model']=8
            with self.assertRaisesRegex(ValueError,'capacity escalation'):d.validate_forecast(changed)

    def test_windows_metadata_sharing_retry_never_repeats_wallet_or_inference(self):
        actual_replace=Path.replace;failures={'remaining':2,'replacements':0}
        def sharing_retry(path,target):
            failures['replacements']+=1
            if failures['remaining']:
                failures['remaining']-=1;raise PermissionError('fixture sharing violation')
            return actual_replace(path,target)
        class Wallet:
            calls=0
            def metadata(self,*args):self.calls+=1;return {'included':{'balance_usd':'100'},'purchased':{'balance_usd':'0'}}
        class Reply:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return json.dumps({'status':'completed','model':old.profile('g26')['model'],'output_text':'x','usage':{'input_tokens':10,'output_tokens':5}}).encode()
        class Opener:
            calls=0
            def open(self,*args,**kwargs):self.calls+=1;return Reply()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);wallet=Wallet();opener=Opener();out=root/'phase';out.mkdir()
            with patch.object(d,'ROOT',root),patch.object(Path,'replace',sharing_retry),patch.object(d.s.time,'sleep'):
                d.BalanceGuard(wallet,'main').check(Decimal('.8143088'),Decimal('1'));self.assertEqual(wallet.calls,1)
                failures['remaining']=2;d.persist_cooldown(100);d.persist_cooldown(80)
                checkpoint=root/('runs/'+old.config()['study_id']+'-guard/dispatch-cooldown-private.json')
                self.assertEqual(old.read(checkpoint)['not_before_epoch'],100)
                # Expired metadata-only fixture, then a new dispatch bookkeeping write.
                failures['remaining']=2
                transport=d.PacedTransport({'ADAPTION_API_KEY':'fixture-only'},out,opener)
                result=transport.request(fake_job());self.assertEqual(opener.calls,1);self.assertEqual(result['transport']['http_status'],200)
                self.assertGreaterEqual(failures['replacements'],9)

    def test_fixed_capacity_and_canonical_main_paths(self):
        c=d.config();self.assertEqual((c['native_per_model'],c['native_provider_max_active'],c['total_max_active'],c['ollama_max_active']),(2,8,8,2))
        self.assertEqual(d.folder('main'),old.folder('main'))
        self.assertNotEqual(d.op_freeze(),old.freeze_path('main'))
        with self.assertRaises(ValueError):d.folder('pilot')
        with self.assertRaises(ValueError):d.op_freeze('pilot')

    def test_wallet_cache_uses_only_local_root_and_carries_spending_once(self):
        class Fake:
            calls=0
            def metadata(self,url,key):self.calls+=1;return {'included':{'balance_usd':'100'},'purchased':{'balance_usd':'0'}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fake=Fake()
            with patch.object(d,'ROOT',root):
                guard=d.BalanceGuard(fake,'main');guard.check(Decimal('.8143088'),Decimal('1'))
                self.assertTrue((root/('runs/'+old.config()['study_id']+'-guard/balance-private.json')).exists())
                guard.check(Decimal('1.8143088'),Decimal('1'));self.assertEqual(fake.calls,1)
                with self.assertRaisesRegex(ValueError,'credit floor'):guard.check(Decimal('100'),Decimal('1'))

    def test_backoff_exact_classes_and_larger_retry_after(self):
        row={'profile_id':'g26','transport':{'http_status':504}};self.assertEqual(d.gateway_backoff_seconds(row),15)
        row['transport'].update(http_status=429,service_overload=True);self.assertEqual(d.gateway_backoff_seconds(row),60)
        row={'profile_id':'ds_low','transport':{'http_status':504}};self.assertEqual(d.gateway_backoff_seconds(row),60)
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);job=fake_job();row=native_row(out,job,504);path=out/'native'/(old.digest(job['id'])+'.json');receipt=old.read(path);receipt['headers']={'Retry-After':'120'};path.write_text(json.dumps(receipt));row['native_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(max(d.gateway_backoff_seconds(row),d.retry_after_delay(row,out)),120)

    def test_pid_reuse_is_proved_by_current_creation_time(self):
        with patch.object(d.os,'name','nt'):
            for stamp,passed in [('2026-11-07T17:00:00+00:00',True),('2026-11-07T15:00:00+00:00',False)]:
                result=subprocess.CompletedProcess([],0,stdout=stamp.encode(),stderr=b'')
                with patch.object(d.subprocess,'run',return_value=result):
                    if passed:self.assertTrue(d.process_dead(123,'2026-11-07T16:00:00+00:00'))
                    else:
                        with self.assertRaises(ValueError):d.process_dead(123,'2026-11-07T16:00:00+00:00')

    def test_budget_carry_precedes_send(self):
        class Fake:
            calls=0
            def request(self,j):self.calls+=1;raise AssertionError('Over-budget send')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}');cfg=execution_fixture();cfg['combined_caps']['adaption']='0.81';fake=Fake()
            with patch.object(d,'ROOT',root),patch.object(d,'registration'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'execution_config',return_value=cfg),patch.object(d,'check_metadata'),patch.object(d,'dispatch_time_gate'),patch.object(d,'verify_pilot_history',return_value={'estimated_cost_by_provider':{'adaption':'.8143088','hf':'0','ollama':'0'}}):
                with self.assertRaisesRegex(ValueError,'Combined provider cap'):d._execute([fake_job()],'main','readers',fake)
                self.assertEqual(fake.calls,0)
                self.assertFalse((d.folder('main')/'readers/attempts.jsonl').exists())

    def test_native_receipts_commit_before_completed_replay_without_retry(self):
        class Fake:
            calls=0
            def request(self,j):self.calls+=1;return native_row(d.folder('main')/'readers',j)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}');fake=Fake();job=fake_job()
            with patch.object(d,'ROOT',root),patch.object(d,'registration'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'execution_config',return_value=execution_fixture()),patch.object(d,'check_metadata'),patch.object(d,'dispatch_time_gate'),patch.object(d,'verify_pilot_history',return_value={'estimated_cost_by_provider':{'adaption':'.8143088','hf':'0','ollama':'0'}}):
                self.assertTrue(d._execute([job],'main','readers',fake)['complete']);self.assertTrue(d._execute([job],'main','readers',fake)['complete']);self.assertEqual(fake.calls,1)
                path=d.folder('main')/'readers/native'/(old.digest(job['id'])+'.json');path.write_text('{}')
                with self.assertRaisesRegex(ValueError,'Native receipt hash'):d._execute([job],'main','readers',fake)

    def test_unknown_send_blocks_next_phase(self):
        class Fake:
            def request(self,j):raise RuntimeError('fixture')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);freeze=root/'freeze.json';freeze.write_text('{}')
            with patch.object(d,'ROOT',root),patch.object(d,'registration'),patch.object(d,'freeze_path',return_value=freeze),patch.object(d,'execution_config',return_value=execution_fixture()),patch.object(d,'check_metadata'),patch.object(d,'dispatch_time_gate'),patch.object(d,'verify_pilot_history',return_value={'estimated_cost_by_provider':{'adaption':'.8143088','hf':'0','ollama':'0'}}):
                with self.assertRaisesRegex(ValueError,'Collector stopped'):d._execute([fake_job()],'main','readers',Fake())
                with self.assertRaisesRegex(ValueError,'unresolved send'):d._execute([fake_job()],'main','calibration',Fake())

if __name__=='__main__':unittest.main()
