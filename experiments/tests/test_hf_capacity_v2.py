"""Synthetic capacity checks. No test reads live receipts or calls a service."""
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import json
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments import hf_capacity_v2 as q


class Clock:
    def __init__(self):self.now=0;self.sleeps=[]
    def __call__(self):return self.now
    def sleep(self,seconds):self.sleeps.append(seconds);self.now+=seconds


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.cfg=q.s.read(q.CONFIG);self.original=q.s.config();self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'research').mkdir();self.clock=Clock()
        self.patches=[patch.object(q.s,'ROOT',self.root),patch.object(q,'CONFIG',self.root/'research/hf-capacity-v2-config.json'),
                      patch.object(q,'FREEZE',self.root/'research/hf-capacity-v2-freeze.json'),
                      patch.object(q,'RESULTS',self.root/'research/hf-capacity-v2-results.json'),
                      patch.object(q.s,'FREEZE',self.root/'original.json'),patch.object(q.s,'config',return_value=self.original),
                      patch.object(q.v1,'verify',return_value={}),patch.object(q.h,'config',return_value={}),patch.object(q.h,'guards'),
                      patch.object(q.h,'live_config',return_value={'hf_allowed_returned_models':['meta-llama/Llama-3.3-70B-Instruct']}),
                      patch.object(q.s,'credentials',return_value={'HF_TOKEN':'fixture-key'}),
                      patch.object(q.subprocess,'check_output',side_effect=lambda args,**kw:(self.root/args[2].split(':',1)[1]).read_bytes()),
                      patch.object(q.subprocess,'run',return_value=SimpleNamespace(returncode=0)),
                      patch.object(q,'utc',side_effect=lambda:(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=self.clock.now)).isoformat())]
        for p in self.patches:p.start()
        for name in q.SOURCES:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name+'\n')
        q.CONFIG.write_text(json.dumps(self.cfg));q.s.FREEZE.write_text('{}')
        q.FREEZE.write_text(json.dumps(dict(schema_version=1,config=self.cfg,source_sha256={n:q.s.sha(self.root/n) for n in q.SOURCES},original_freeze_sha256=q.s.sha(q.s.FREEZE),base_commit='fixture')))
        self.catalog=dict(data=[dict(id='meta-llama/Llama-3.3-70B-Instruct',providers=[dict(provider='novita',status='live',pricing={'input':0.135,'output':0.40})])])

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def native(self):return dict(model='meta-llama/Llama-3.3-70B-Instruct',usage={'prompt_tokens':1600,'completion_tokens':1},choices=[dict(finish_reason='stop',message={'content':'OK'})])

    def run_fake(self,fault=None,after=None,catalog=None):
        calls=[]
        def request(url,key,out,label,payload=None,**kw):
            if payload is None:return {'http_status':200,'category':'notdeterminable'},self.catalog if catalog is None else catalog
            kw['opener'].mark_start()
            calls.append((self.clock(),payload));native=self.native();public={'http_status':200,'category':'notdeterminable'}
            if fault=='exception':raise RuntimeError('fixture transport failure')
            if fault=='429':public={'http_status':429,'category':'quota'};native=None
            elif fault=='unknown':native.pop('usage')
            elif fault=='small':native['usage']['prompt_tokens']=1578
            elif fault=='large':native['usage']['prompt_tokens']=24001
            elif fault=='output':native['usage']['completion_tokens']=4097
            elif fault=='overcost':native['usage']={'prompt_tokens':1000000,'completion_tokens':5000}
            elif fault=='model':native['model']='unsafe-provider-id'
            elif fault=='finish':native['choices'][0]['finish_reason']='length'
            elif fault=='content':native['choices'][0]['message']['content']='Not OK'
            elif fault=='malformed':native['choices']=[]
            if after:after(calls)
            return public,native
        with patch.object(q.h,'request',side_effect=request):
            result=q.run(True,clock=self.clock,sleep=self.clock.sleep)
        return result,calls

    def test_all24_paced_neutral_unique_bodies_and_public_replay(self):
        report,calls=self.run_fake()
        self.assertTrue(report['passed']);self.assertTrue(report['complete']);self.assertEqual(len(calls),24)
        self.assertGreaterEqual(calls[0][0],60)
        self.assertTrue(all(b[0]-a[0]>=30 for a,b in zip(calls,calls[1:])))
        self.assertLessEqual(max(self.clock.sleeps),1)
        prompts=[b['messages'][0]['content'] for _,b in calls]
        self.assertEqual(len(set(prompts)),24)
        for i,(_,b) in enumerate(calls):
            self.assertTrue(prompts[i].startswith(q.identity(i)+'\n'))
            self.assertEqual(b['max_tokens'],4096);self.assertLessEqual(len(json.dumps(b).encode()),24000)
        self.assertEqual(q.verify_results(),report)
        self.assertEqual(q.verify_results(private=True),report)
        self.assertNotIn(b'\r\n',q.RESULTS.read_bytes())

    def test_fail_first429_keeps_reservation_and23_unstarted(self):
        report,calls=self.run_fake('429')
        self.assertFalse(report['passed']);self.assertEqual(len(calls),1);self.assertEqual(report['unstarted'],23)
        self.assertEqual(Decimal(report['reserved_unknown_cost']),Decimal('0.0048784'))
        self.assertEqual(q.verify_results(),report)
        with self.assertRaises(FileExistsError):self.run_fake()

    def test_non_ok_wording_is_descriptive_and_all24_can_pass(self):
        report,calls=self.run_fake('content')
        self.assertTrue(report['passed']);self.assertEqual(len(calls),24)
        self.assertTrue(all(not row['content_ok'] and row['shape_ok'] and row['profile_ok'] for row in report['jobs']))
        self.assertEqual(q.verify_results(private=True),report)

    def test_nonstring_missing_message_remains_malformed(self):
        for message in (None,{}, {'content':None}, {'content':42}):
            native=self.native();native['choices'][0]['message']=message
            row=q.receipt({'http_status':200,'category':'notdeterminable'},native,self.cfg)
            self.assertFalse(row['shape_ok']);self.assertFalse(row['profile_ok'])

    def test_ids_and_source_chain_are_separate_from_v1(self):
        self.assertEqual(q.identity(0),'capacity2-00')
        self.assertNotEqual(q.body(self.cfg,0),q.v1.body({**self.cfg},0))
        self.assertIn('experiments/hf_capacity.py',q.SOURCES)

    def test_known_provider_overrun_is_not_discounted_to_reservation(self):
        report,calls=self.run_fake('overcost')
        self.assertEqual(len(calls),1);self.assertFalse(report['passed'])
        self.assertEqual(Decimal(report['known_cost']),Decimal('0.137'))
        self.assertGreater(Decimal(report['total_cost']),Decimal(self.cfg['cap_usd']))
        self.assertEqual(report['reserved_unknown_cost'],'0')

    def test_each_invalid_serving_receipt_stops(self):
        for fault in ('unknown','small','large','output','overcost','model','finish','malformed','exception'):
            cfg={**self.cfg,'output_directory':'runs/capacity-fault-'+fault}
            with self.subTest(fault=fault),patch.object(q,'verify',return_value=cfg):
                report,calls=self.run_fake(fault)
                self.assertEqual(len(calls),1);self.assertFalse(report['passed'])

    def test_budget_blocks_before_journal_and_unknown_exception_reserved(self):
        cfg={**self.cfg,'cap_usd':'0.005'}
        with patch.object(q,'verify',return_value=cfg):report,calls=self.run_fake()
        self.assertEqual(len(calls),1);self.assertEqual(report['stop_reason'],'budget')
        self.assertEqual(report['started'],1);self.assertEqual(report['unstarted'],23)

    def test_profile_and_known_usage_cost_independent(self):
        for fault in ('small','large','output','model','finish','malformed','unknown'):
            native=self.native()
            if fault=='small':native['usage']['prompt_tokens']=1578
            elif fault=='large':native['usage']['prompt_tokens']=24001
            elif fault=='output':native['usage']['completion_tokens']=4097
            elif fault=='model':native['model']='private-token-provider-id'
            elif fault=='finish':native['choices'][0]['finish_reason']='length'
            elif fault=='content':native['choices'][0]['message']['content']='other'
            elif fault=='malformed':native['choices']=[]
            else:native.pop('usage')
            row=q.receipt({'http_status':200,'category':'notdeterminable'},native,self.cfg)
            self.assertFalse(row['profile_ok'],fault)
            if fault=='model':self.assertEqual(row['returned_model'],'<unexpected>')
            if fault=='unknown':self.assertEqual(Decimal(row['estimated_cost']),q.reserve(self.cfg))

    def test_operator_stop_before_next_journal(self):
        def stop_after(calls):
            if len(calls)==1:(self.root/self.cfg['output_directory']/'STOP').write_text('operator')
        report,calls=self.run_fake(after=stop_after)
        self.assertEqual(len(calls),1);self.assertEqual(report['unstarted'],23)
        self.assertEqual(report['stop_reason'],'operator_stop')
        self.assertEqual(len(q.s.rows(self.root/self.cfg['output_directory']/'attempts.jsonl')),1)

    def test_initial_stop_no_dispatch_or_start(self):
        def sleep(seconds):
            self.clock.sleep(seconds);(self.root/self.cfg['output_directory']/'STOP').write_text('operator')
        with patch.object(q.h,'request',return_value=({'http_status':200,'category':'notdeterminable'},self.catalog)):
            report=q.run(True,clock=self.clock,sleep=sleep)
        self.assertEqual(report['started'],0);self.assertFalse(report['passed'])

    def test_slow_start_journal_does_not_shorten_dispatch_spacing(self):
        original=q.s.durable
        def slow(file,row):
            original(file,row)
            if file.name.endswith('attempts.jsonl') and row['localid']=='capacity2-00':self.clock.now+=10
        with patch.object(q.s,'durable',side_effect=slow):report,calls=self.run_fake()
        self.assertTrue(report['passed'])
        self.assertGreaterEqual(calls[1][0]-calls[0][0],30)

    def test_actual_opener_offsets_and_constructor_jitter_are_paced(self):
        calls=[];test=self;original_request=q.h.Request;post_count=0
        class Reply(io.BytesIO):status=200;headers={}
        class Opener:
            def open(self,request,timeout):
                if request.method=='GET':return Reply(json.dumps(test.catalog).encode())
                calls.append(test.clock());return Reply(json.dumps(test.native()).encode())
        def request(*args,**kwargs):
            nonlocal post_count
            if kwargs.get('method')=='POST':
                post_count+=1
                if post_count==1:test.clock.now+=15
            return original_request(*args,**kwargs)
        with patch.object(q.h,'Request',side_effect=request):
            report=q.run(True,opener=Opener(),clock=self.clock,sleep=self.clock.sleep)
        self.assertTrue(report['passed']);self.assertEqual(len(calls),24)
        self.assertTrue(all(b-a>=30 for a,b in zip(calls,calls[1:])))
        self.assertEqual([r['start_offset_seconds'] for r in report['jobs']],calls)

    def test_main_guard_rechecked_before_every_post(self):
        # Initial preflight, first POST, then a new main activity blocks POST 2.
        with patch.object(q.h,'guards',side_effect=[None,None,ValueError('active')]):
            report,calls=self.run_fake()
        self.assertEqual(len(calls),1);self.assertFalse(report['passed'])
        self.assertEqual(report['stop_reason'],'main_guard')

    def test_public_replay_rejects_changed_costs_ids_aggregates_and_secrets(self):
        report,_=self.run_fake()
        for mutation in ('cost','id','aggregate','secret'):
            altered=json.loads(json.dumps(report))
            if mutation=='cost':altered['jobs'][0]['estimated_cost']='0'
            elif mutation=='id':altered['jobs'][1]['localid']='capacity2-00'
            elif mutation=='aggregate':altered['passed']=False
            else:altered['jobs'][0]['native_response']={'private':'data'}
            with self.assertRaises(ValueError):q.validate(altered,self.cfg)
        with patch.object(q.s,'credentials',side_effect=AssertionError('credentials')),patch.object(q.s,'rows',side_effect=AssertionError('private ledgers')):
            self.assertEqual(q.verify_results(),report)

    def test_unresolved_start_reported_reserved_not_unstarted(self):
        out=self.root/self.cfg['output_directory'];out.mkdir(parents=True)
        (out/'plan.json').write_text(json.dumps(q.plan(self.cfg)))
        start=dict(localid='capacity2-00',started_at=q.utc(),start_offset_seconds=60,request_sha256=q.s.digest(q.body(self.cfg,0)),reserved_cost=str(q.reserve(self.cfg)))
        (out/'attempts.jsonl').write_text(json.dumps(start)+'\n');(out/'responses.jsonl').write_text('')
        report=q.export()
        self.assertEqual(report['unresolved'],1);self.assertEqual(report['unstarted'],23)
        self.assertFalse(report['passed']);self.assertEqual(Decimal(report['total_cost']),q.reserve(self.cfg))

    def test_catalog_drift_prevents_all_posts(self):
        report,calls=self.run_fake(catalog={'data':[]})
        self.assertEqual(calls,[]);self.assertEqual(report['returned'],0);self.assertFalse(report['passed'])

    def test_registration_sources_and_fixed_reservation(self):
        self.assertEqual(q.reserve(self.cfg)*24,Decimal('0.1170816'))
        self.assertEqual(q.verify(),self.cfg)
        (self.root/q.SOURCES[0]).write_text('changed')
        with self.assertRaisesRegex(ValueError,'source'):q.verify()

    def test_explicit_flag_tag_and_freeze_creation_guards(self):
        with self.assertRaisesRegex(ValueError,'Explicit'):q.run(False)
        with self.assertRaisesRegex(ValueError,'already exists'):q.freeze()
        with patch.object(q.subprocess,'check_output',return_value=b'bad'):
            with self.assertRaisesRegex(ValueError,'tag'):q.verify()
        q.FREEZE.unlink()
        with patch.object(q.subprocess,'check_output',return_value=b' M experiments/hf_capacity.py'):
            with self.assertRaisesRegex(ValueError,'Commit'):q.freeze()
        self.assertFalse(q.FREEZE.exists())

    def test_stop_during_last_receipt_cannot_pass(self):
        def stop(calls):
            if len(calls)==24:(self.root/self.cfg['output_directory']/'STOP').write_text('operator')
        report,calls=self.run_fake(after=stop)
        self.assertTrue(report['complete']);self.assertFalse(report['passed'])
        self.assertEqual(report['stop_reason'],'operator_stop')

    def test_private_preflight_detects_changed_journals_without_writing(self):
        self.run_fake();public=q.RESULTS.read_bytes()
        response=self.root/self.cfg['output_directory']/'responses.jsonl'
        response.write_text(response.read_text().replace('"input_tokens":1600','"input_tokens":1601',1))
        with self.assertRaises(ValueError):q.verify_results(private=True)
        self.assertEqual(q.RESULTS.read_bytes(),public)

    def test_stop_at_actual_opener_boundary_prevents_catalog(self):
        stop=self.root/'STOP';calls=[]
        class Opener:
            def open(self,*a,**kw):calls.append(True)
        wire=q.TimedOpener(Opener(),self.clock,stop);stop.write_text('operator')
        with self.assertRaises(q.Stopped):wire.open(None,120)
        self.assertEqual(calls,[]);self.assertIsNone(wire.last)


if __name__=='__main__':unittest.main()
