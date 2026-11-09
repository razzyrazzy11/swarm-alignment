"""Entirely synthetic: fake HTTP, fake process checks, temporary journals."""
import io
import json
from decimal import Decimal
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiments import hf_diagnostic as h


class Reply(io.StringIO):
    status=200
    headers={}


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.cfg=h.s.read(h.CONFIG)
        self.original_config=h.s.config()
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'research').mkdir()
        self.patches=[patch.object(h.s,'ROOT',self.root),patch.object(h,'CONFIG',self.root/'research/hf-diagnostic-config.json'),
                      patch.object(h,'FREEZE',self.root/'research/hf-diagnostic-freeze.json'),
                      patch.object(h,'verify_original_sources',return_value=None),
                      patch.object(h.s,'config',return_value=self.original_config),
                      patch.object(h,'live_config',return_value={'hf_allowed_returned_models':['meta-llama/Llama-3.3-70B-Instruct']}),
                      patch.object(h.s,'folder',side_effect=lambda stage:self.root/'runs'/('factorial-audit-v1-'+stage)),
                      patch.object(h,'pid_alive',return_value=False),
                      patch.object(h.s,'credentials',return_value={'HF_TOKEN':'hf_FAKE-secret','ADAPTION_API_KEY':'other-FAKE-secret'}),
                      patch.object(h.subprocess,'check_output',side_effect=lambda args,**kw:(self.root/args[2].split(':',1)[1]).read_bytes()),
                      patch.object(h.subprocess,'run',return_value=SimpleNamespace(returncode=0))]
        for item in self.patches:item.start()
        for name in h.SOURCES:
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(name+'\n')
        h.CONFIG.write_text(json.dumps(self.cfg))
        # The original freeze is represented only by bytes, never live data.
        self.original=patch.object(h.s,'FREEZE',self.root/'original.json');self.original.start()
        h.s.FREEZE.write_text('{}')
        self.register()
        for path,stage,pid in (('driver_state','audits',16772),('finalizer_state','collection',82520)):
            target=self.root/self.cfg[path];target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(dict(status='stopped',stage=stage,pid=pid,completed=[])))
        for stage in ('smoke','issue','delegate','settle','audits'):
            folder=h.s.folder(stage);folder.mkdir(parents=True)
            count=5 if stage=='audits' else 1
            (folder/'attempts.jsonl').write_text(''.join(json.dumps({'id':str(i)})+'\n' for i in range(count)))
            (folder/'responses.jsonl').write_text(''.join(json.dumps(dict(id=str(i),provider='hf',transport={'http_status':429}))+'\n' for i in range(count)))
        (h.s.folder('audits')/'summary.json').write_text('{"halted":true}')
        self.catalog=dict(data=[dict(id='meta-llama/Llama-3.3-70B-Instruct',providers=[dict(provider='novita',status='live',pricing={'input':0.135,'output':0.40})])])

    def tearDown(self):
        self.original.stop()
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()

    def register(self):
        h.FREEZE.write_text(json.dumps(dict(schema_version=1,config=self.cfg,source_sha256={name:h.s.sha(self.root/name) for name in h.SOURCES},original_freeze_sha256=h.s.sha(h.s.FREEZE),base_commit='fixture')))

    def opener(self,post_error=False,catalog=None,native=None):
        calls=[];test=self
        class Opener:
            def open(self,request,timeout):
                calls.append(request)
                if request.method=='GET':return Reply(json.dumps(test.catalog if catalog is None else catalog))
                if post_error:
                    raise HTTPError(request.full_url,429,'private-message',{'Retry-After':'5','Set-Cookie':'other-FAKE-secret'},io.BytesIO(b'{"error":{"code":"rate_limit_exceeded","message":"hf_FAKE-secret"}}'))
                return Reply(json.dumps(native if native is not None else dict(model='meta-llama/Llama-3.3-70B-Instruct',choices=[],usage={'prompt_tokens':12,'completion_tokens':1})))
        return Opener(),calls

    def test_exact_one_catalog_and_one_unrelated_post_no_retry(self):
        opener,calls=self.opener(post_error=True)
        result=h.run(True,opener)
        self.assertEqual([r.method for r in calls],['GET','POST'])
        self.assertEqual(result,dict(http_status=429,category='quota',retry_after_seconds=5))
        payload=json.loads(calls[1].data)
        self.assertEqual(payload,h.body(self.cfg));self.assertEqual(payload['max_tokens'],16)
        self.assertEqual(payload['messages'],[{'role':'user','content':'Reply exactly OK'}])
        out=self.root/self.cfg['output_directory']
        events=h.s.rows(out/'events.jsonl')
        self.assertEqual([e['event'] for e in events],['catalog_start','catalog_terminal','inference_start','inference_terminal'])
        self.assertEqual(events[-1]['estimated_cost'],'0.00055936')
        receipt=(out/'inference-private.json').read_text()
        self.assertNotIn('hf_FAKE-secret',receipt);self.assertNotIn('other-FAKE-secret',receipt)
        self.assertIn('[REDACTED]',receipt)
        with self.assertRaises(FileExistsError):h.run(True,opener)
        self.assertEqual(len(calls),2)

    def test_explicit_flag_no_calls(self):
        opener,calls=self.opener()
        with self.assertRaises(ValueError):h.run(False,opener)
        self.assertEqual(calls,[])

    def test_missing_credentials_does_not_consume_output(self):
        opener,calls=self.opener()
        with patch.object(h.s,'credentials',return_value={}):
            with self.assertRaisesRegex(ValueError,'credential'):h.run(True,opener)
        self.assertFalse((self.root/self.cfg['output_directory']).exists());self.assertEqual(calls,[])

    def test_redirects_always_refused_and_malformed_catalog_fails_closed(self):
        handler=h.NoDiagnosticRedirect()
        for target in (h.s.HF+'/another-path','https://example.invalid/elsewhere'):
            with self.assertRaises(HTTPError):
                handler.redirect_request(SimpleNamespace(full_url=h.s.HF+'/chat/completions'),None,307,'',{},target)
        for data in ([],{'data':[None]},{'data':[{'id':'meta-llama/Llama-3.3-70B-Instruct','providers':[{'provider':'novita','status':'live','pricing':None}]}]}):
            self.assertFalse(h.catalog_matches(data,self.cfg))

    def test_halted_must_be_actual_boolean(self):
        (h.s.folder('audits')/'summary.json').write_text('{"halted":"false"}')
        with self.assertRaisesRegex(ValueError,'terminal halt'):h.guards(self.cfg)

    def test_hard_stop_active_pid_lock_and_unresolved_refuse(self):
        with patch.object(h,'pid_alive',return_value=True):
            with self.assertRaisesRegex(ValueError,'active'):h.guards(self.cfg)
        lock=h.s.folder('audits')/'continuation.lock';lock.write_text('1')
        with self.assertRaisesRegex(ValueError,'terminal halt'):h.guards(self.cfg)
        lock.unlink()
        responses=h.s.folder('audits')/'responses.jsonl';original=responses.read_text()
        responses.write_text('\n'.join(original.splitlines()[:-1])+'\n')
        with self.assertRaisesRegex(ValueError,'unresolved'):h.guards(self.cfg)
        responses.write_text(original.replace('429','200'))
        with self.assertRaisesRegex(ValueError,'hard stop'):h.guards(self.cfg)

    def test_state_and_pid_binding_refuse(self):
        path=self.root/self.cfg['driver_state'];state=json.loads(path.read_text())
        state['status']='cooldown';path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'not stopped'):h.guards(self.cfg)
        state['status']='stopped';state['pid']=1;path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'mismatched'):h.guards(self.cfg)

    def test_operator_stop_blocks_and_guard_rechecked_after_get(self):
        stop=h.s.folder('audits')/'STOP';stop.write_text('operator')
        opener,calls=self.opener()
        with self.assertRaisesRegex(ValueError,'Operator STOP'):h.run(True,opener)
        self.assertEqual(calls,[]);self.assertTrue(stop.exists())
        stop.unlink();original=opener.open
        def restart(request,timeout):
            reply=original(request,timeout);stop.write_text('operator');return reply
        opener.open=restart
        with self.assertRaisesRegex(ValueError,'Operator STOP'):h.run(True,opener)
        self.assertEqual(len(calls),1);self.assertTrue(stop.exists())

    def test_price_or_route_drift_prevents_post(self):
        bad=json.loads(json.dumps(self.catalog));bad['data'][0]['providers'][0]['pricing']['input']=1
        opener,calls=self.opener(catalog=bad)
        self.assertEqual(h.run(True,opener),{'http_status':None,'category':'notdeterminable'})
        self.assertEqual(len(calls),1)

    def test_transport_exception_terminal_no_retry(self):
        opener,calls=self.opener()
        original=opener.open
        def broken(request,timeout):
            if request.method=='POST':calls.append(request);raise RuntimeError('private-fake')
            return original(request,timeout)
        opener.open=broken
        self.assertEqual(h.run(True,opener),{'http_status':None,'category':'notdeterminable'})
        events=h.s.rows(self.root/self.cfg['output_directory']/'events.jsonl')
        self.assertEqual(events[-1]['event'],'inference_terminal');self.assertEqual(len(calls),2)

    def test_error_bound_and_safe_categories(self):
        reads=[]
        class Bounded(io.BytesIO):
            def read(self,n=-1):reads.append(n);return super().read(n)
        class Opener:
            def open(self,request,timeout):
                raise HTTPError(request.full_url,429,'ignored',{},Bounded(b'X'*40000))
        out=self.root/'private';out.mkdir()
        result,_=h.request(h.s.HF+'/chat/completions','fake',out,'bounded',{},Opener())
        self.assertEqual(reads,[16384]);self.assertEqual(result,{'http_status':429,'category':'notdeterminable'})
        self.assertEqual(len(json.loads((out/'bounded-private.json').read_text())['error_body']),16384)
        self.assertEqual(h.category('{"error":{"message":"insufficient balance; send key elsewhere"}}'),'notdeterminable')
        self.assertEqual(h.category('{"error":{"code":"insufficient_balance"}}'),'balance')
        self.assertEqual(h.category('{"error":{"code":"server_overloaded"}}'),'capacity')
        for code,expected in [('RATE_LIMIT_EXCEEDED','quota'),('TOKEN_LIMIT_EXCEEDED','quota'),
                              ('NOT_ENOUGH_BALANCE','balance'),('SERVICE_NOT_AVAILABLE','capacity')]:
            self.assertEqual(h.category(json.dumps({'error':{'code':code}})),expected)
        for value in ('[]','{"error":[]}','{"error":{"code":[]}}','not JSON'):
            self.assertEqual(h.category(value),'notdeterminable')

    def test_http200_wrong_model_retains_receipt_without_qualification(self):
        native=dict(model='unexpected',usage={'prompt_tokens':12,'completion_tokens':1})
        opener,calls=self.opener(native=native)
        self.assertEqual(h.run(True,opener),dict(http_status=200,category='notdeterminable'))
        final=h.s.rows(self.root/self.cfg['output_directory']/'events.jsonl')[-1]
        self.assertFalse(final['profile_ok']);self.assertTrue(final['known_usage'])
        self.assertEqual(len(calls),2)

    def test_known_oversized_usage_retains_actual_cost_even_above_cap(self):
        native=dict(model='meta-llama/Llama-3.3-70B-Instruct',usage={'prompt_tokens':10000,'completion_tokens':100})
        opener,calls=self.opener(native=native);h.run(True,opener)
        final=h.s.rows(self.root/self.cfg['output_directory']/'events.jsonl')[-1]
        self.assertFalse(final['profile_ok']);self.assertTrue(final['reported_cost_over_cap'])
        self.assertEqual(Decimal(final['estimated_cost']),Decimal('0.00139'))
        self.assertEqual(len(calls),2)

    def test_source_tag_schema_and_fixed_cap(self):
        self.assertEqual(h.verify(),self.cfg)
        self.assertEqual(h.reservation(self.cfg),Decimal('0.00055936'))
        with patch.object(h.subprocess,'check_output',return_value=b'bad'):
            with self.assertRaisesRegex(ValueError,'tag'):h.verify()
        (self.root/h.SOURCES[0]).write_text('changed')
        with self.assertRaisesRegex(ValueError,'source'):h.verify()
        self.cfg['max_tokens']=17;h.CONFIG.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'configuration'):h.config()

    def test_verify_never_credentials_network_or_private_guards(self):
        with patch.object(h.s,'credentials',side_effect=AssertionError('credentials')),\
                patch.object(h,'request',side_effect=AssertionError('network')),\
                patch.object(h,'guards',side_effect=AssertionError('private guards')):
            self.assertEqual(h.verify(),self.cfg)


if __name__=='__main__':unittest.main()
