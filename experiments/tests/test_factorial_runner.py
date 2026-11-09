import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from experiments import factorial_study as s


class FactorialRunnerTests(unittest.TestCase):
    def jobs(self,n=8,hf=False):
        c=s.config()
        return [s.job(str(i),c['hf_model'] if hf and i%2 else c['actor_model'],s.DIRECT,{'case':i},phase='fixture') for i in range(n)]

    def native(self,body,status='completed'):
        model=body['model'];text='{"status":"NONE","worker_id":null}'
        if 'messages' in body:
            return dict(model=model.rsplit(':',1)[0],choices=[dict(message=dict(content=text),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=10))
        return dict(model=model,status=status,output_text=text,usage=dict(input_tokens=10,output_tokens=10))

    def run_fake(self,jobs,request,out=None,**kw):
        if out is None:out=Path(self.temp.name)/'run'
        with patch.object(s,'verify',return_value={'valid':True}),patch.object(s,'credentials',return_value={'ADAPTION_API_KEY':'fixture-key-one','HF_TOKEN':'fixture-key-two'}),patch.object(s,'request_json',side_effect=request),patch.object(s,'sha',return_value='fixture-freeze'):
            return s.execute(jobs,out,**kw)

    def setUp(self):self.temp=tempfile.TemporaryDirectory()
    def tearDown(self):self.temp.cleanup()

    def test_same_packet_settings_only_procedure_instruction_changes(self):
        for model in s.config()['monitors']:
            packet={'public':{'authorized':True},'records':[]}
            a=s.body_for(s.job('a',model,s.DIRECT,packet))[1];b=s.body_for(s.job('b',model,s.PROCEDURE,packet))[1]
            if model==s.config()['hf_model']:
                self.assertEqual(a['messages'][1:],b['messages'][1:]);a.pop('messages');b.pop('messages')
            else:self.assertEqual(a['input'],b['input']);a.pop('instructions');b.pop('instructions')
            self.assertEqual(a,b)

    def test_boolean_choice_and_encoding_contract(self):
        self.assertFalse(s.decode_choice('{"choice":1,"note":"x"}')['valid'])
        self.assertTrue(s.decode_choice('```json\n{"choice":true,"note":"x"}\n```')['valid'])
        self.assertFalse(s.decode_choice('{"choice":true}')['valid'])

    def test_incomplete_actor_json_never_executes(self):
        model=s.config()['actor_model']
        row=dict(model=model,known_usage=True,transport={'http_status':200},response=dict(status='incomplete',returned_model=model,output_text='{"choice":true,"note":"ok"}'))
        self.assertFalse(s.actor_decision(row,'issue')['valid'])
        row['response']['output_text']='{"action":"write","claimed_done":true}'
        self.assertFalse(s.actor_decision(row,'settle')['valid'])

    def test_known_truncations_retained_no_retry_and_exact_resume(self):
        calls=[]
        def request(url,key,body,timeout):calls.append(body);return {'http_status':200},self.native(body,'incomplete')
        jobs=self.jobs(7);summary=self.run_fake(jobs,request)
        self.assertTrue(summary['complete']);self.assertEqual(summary['incomplete'],7)
        self.assertEqual(len(calls),7)
        self.run_fake(jobs,request,resume=True);self.assertEqual(len(calls),7)

    def test_fatal_auth_drains_already_started_requests(self):
        lock=threading.Lock();calls=[]
        def request(url,key,body,timeout):
            with lock:ordinal=len(calls);calls.append(body)
            time.sleep(.01)
            return ({'http_status':403},None) if ordinal==0 else ({'http_status':200},self.native(body))
        result=self.run_fake(self.jobs(12),request)
        self.assertTrue(result['halted']);self.assertFalse(result['complete'])
        p=Path(self.temp.name)/'run'
        self.assertEqual(len(s.rows(p/'attempts.jsonl')),len(s.rows(p/'responses.jsonl')))
        self.assertLess(len(calls),12)

    def test_unknown_start_refused_without_dispatch(self):
        jobs=self.jobs(1)
        self.run_fake(jobs,lambda u,k,b,timeout:({'http_status':200},self.native(b)))
        (Path(self.temp.name)/'run/responses.jsonl').write_text('')
        called=[]
        with self.assertRaises(ValueError):self.run_fake(jobs,lambda *args,**kwargs:called.append(True),resume=True)
        self.assertFalse(called)

    def test_all_bodies_validate_before_journaling(self):
        jobs=self.jobs(2);jobs[-1]['prompt']='X'*30000
        with self.assertRaises(ValueError):self.run_fake(jobs,lambda *a,**k:self.fail('must not dispatch'))
        self.assertFalse((Path(self.temp.name)/'run').exists())

    def test_global_four_hf_two_sliding_concurrency(self):
        lock=threading.Lock();active=0;hf=0;peak=0;hfpeak=0
        def request(url,key,body,timeout):
            nonlocal active,hf,peak,hfpeak
            is_hf='messages' in body
            with lock:active+=1;hf+=is_hf;peak=max(peak,active);hfpeak=max(hfpeak,hf)
            time.sleep(.02)
            with lock:active-=1;hf-=is_hf
            return {'http_status':200},self.native(body)
        result=self.run_fake(self.jobs(20,True),request)
        self.assertTrue(result['complete']);self.assertLessEqual(peak,4);self.assertLessEqual(hfpeak,2)
        self.assertGreater(peak,1)

    def test_gateway_unknown_reserved_but_other_unknown_stops(self):
        calls=[]
        def request(url,key,body,timeout):
            calls.append(1)
            return ({'http_status':502},None) if len(calls)==1 else ({'http_status':200},self.native(body))
        result=self.run_fake(self.jobs(6),request)
        self.assertTrue(result['complete']);self.assertEqual(result['gateway_errors'],1)
        result=self.run_fake(self.jobs(6),lambda *a,**k:({'http_status':200},{}),out=Path(self.temp.name)/'bad')
        self.assertTrue(result['halted'])

    def test_malformed_native_is_terminal_not_unresolved(self):
        with patch.object(s,'response',side_effect=AttributeError('bad native shape')):
            result=self.run_fake(self.jobs(3),lambda u,k,b,timeout:({'http_status':200},self.native(b)))
        self.assertTrue(result['halted'])
        p=Path(self.temp.name)/'run'
        self.assertEqual(len(s.rows(p/'attempts.jsonl')),len(s.rows(p/'responses.jsonl')))


if __name__=='__main__':unittest.main()
