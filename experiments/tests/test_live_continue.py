"""Continuation keeps all failures and skips every previously started identity."""
import tempfile,unittest,threading,time
from pathlib import Path
from unittest.mock import patch
from experiments import live_continue as c
from experiments.live_study import job,config

class LiveContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.out=Path(self.tmp.name)/'out'
        self.model=config()['actor_model'];self.jobs=[job(str(i),self.model,'test',{}) for i in range(5)]
    def answer(self,status='incomplete'):
        return {'http_status':200},dict(status=status,output_text='',model=self.model,usage=dict(input_tokens=10,output_tokens=4096))
    def run_mock(self,fn,resume=False):
        with patch.object(c,'verify',return_value={'valid':True}),patch.object(c,'sha',return_value='fixture-sha'),patch.object(c,'credentials',return_value={'ADAPTION_API_KEY':'test-key','HF_TOKEN':'test-hf'}),patch.object(c,'request_json',side_effect=fn):
            return c.execute(self.jobs,self.out,resume)
    def test_known_usage_truncations_retained_and_completed_not_retried(self):
        calls=[]
        def send(*args,**kw):calls.append(args[2]['input']);return self.answer()
        result=self.run_mock(send)
        self.assertTrue(result['complete']);self.assertEqual(result['incomplete'],5)
        before=len(calls);result=self.run_mock(send,resume=True)
        self.assertTrue(result['complete']);self.assertEqual(len(calls),before)
        self.assertEqual(len(c.rows(self.out/'responses.jsonl')),5)
    def test_auth_or_unknown_usage_still_stops_and_drains(self):
        def send(*args,**kw):return {'http_status':403},None
        result=self.run_mock(send)
        self.assertTrue(result['halted']);self.assertEqual(result['returned'],4);self.assertEqual(result['unstarted'],1)
        with self.assertRaisesRegex(ValueError,'Prior safety gate'):self.run_mock(send,resume=True)
    def test_unknown_started_request_cannot_be_retried(self):
        self.run_mock(lambda *a,**k:self.answer())
        p=self.out/'responses.jsonl';lines=p.read_text().splitlines();p.write_text('\n'.join(lines[:-1])+'\n')
        with self.assertRaisesRegex(ValueError,'unreturned start'):self.run_mock(lambda *a,**k:self.answer(),resume=True)

    def test_all_request_bodies_are_checked_before_any_dispatch(self):
        self.jobs[-1]['payload']={'oversize':'x'*30000};called=[]
        def send(*a,**kw):called.append(True);return self.answer()
        with self.assertRaisesRegex(ValueError,'Input byte bound'):self.run_mock(send)
        self.assertEqual(called,[])

    def test_malformed_native_response_is_terminal_and_stops_not_lost(self):
        def send(*a,**kw):return {'http_status':200},dict(status='completed',model=self.model,output=None,usage=dict(input_tokens=10,output_tokens=10))
        result=self.run_mock(send);self.assertTrue(result['halted']);self.assertEqual(result['returned'],4)
        self.assertTrue(all(r['transport']['error']=='normalization_failure' and not r['known_usage'] for r in c.rows(self.out/'responses.jsonl')))

    def test_slow_request_does_not_block_free_slots(self):
        released=threading.Event();lock=threading.Lock();calls=[];timed_out=[]
        def send(*args,**kw):
            with lock:
                index=len(calls);calls.append(index)
                if len(calls)>=5:released.set()
            if index==0 and not released.wait(2):timed_out.append(True)
            return self.answer()
        result=self.run_mock(send)
        self.assertTrue(result['complete']);self.assertEqual(timed_out,[])

    def test_active_reservations_wait_for_reconciliation_without_overspend(self):
        cfg=config();ri,ro=c.rates(self.model);reserve=(cfg['input_byte_cap']*ri+cfg['max_output_tokens']*ro)/1000000
        cfg['adaption_phase_cap']=str(reserve*__import__('decimal').Decimal('2.5'))
        with patch.object(c,'config',return_value=cfg):result=self.run_mock(lambda *a,**k:self.answer())
        self.assertTrue(result['complete']);self.assertLessEqual(__import__('decimal').Decimal(result['costs']['adaption']),reserve*__import__('decimal').Decimal('2.5'))

    def test_global_four_and_hf_two_limits_are_respected(self):
        cfg=config();hf=cfg['hf_model'];self.jobs=[job(str(i),hf if i<5 else self.model,'test',{}) for i in range(10)]
        lock=threading.Lock();active=[0,0];peak=[0,0]
        def send(url,key,body,**kw):
            ishf='huggingface' in url
            with lock:
                active[0]+=1;active[1]+=int(ishf);peak[0]=max(peak[0],active[0]);peak[1]=max(peak[1],active[1])
            time.sleep(.01)
            with lock:active[0]-=1;active[1]-=int(ishf)
            if ishf:return {'http_status':200},dict(model=cfg['hf_allowed_returned_models'][0],choices=[dict(finish_reason='stop',message={'content':'{}'})],usage=dict(prompt_tokens=10,completion_tokens=10))
            return {'http_status':200},dict(model=self.model,status='completed',output_text='{}',usage=dict(input_tokens=10,output_tokens=10))
        result=self.run_mock(send);self.assertTrue(result['complete']);self.assertLessEqual(peak[0],4);self.assertLessEqual(peak[1],2)

if __name__=='__main__':unittest.main()
