"""Synthetic transport fixtures; no provider calls or actual model answers."""
import io,json,unittest
from urllib.error import HTTPError,URLError
from experiments import adaption_serving_transport as t

def native(status='completed',identity='test-response',model='test-model'):
    return dict(id=identity,model=model,status=status,output_text='{"note":"toy"}',usage={'input_tokens':4,'output_tokens':7})

def frame(kind,response=None,**fields):
    value=dict(type=kind,**fields)
    if response is not None:value['response']=response
    return ('event: '+kind+'\ndata: '+json.dumps(value,ensure_ascii=False)+'\n\n').encode()

class Clock:
    def __init__(self):self.value=0.
    def __call__(self):return self.value

class Reply:
    def __init__(self,chunks,clock=None,delay=0,mime='text/event-stream',error=None):
        self.chunks=list(chunks);self.clock=clock;self.delay=delay;self.status=200
        self.headers={'Content-Type':mime,'Authorization':'secret-key'};self.closed=False;self.timeouts=[];self.error=error
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True
    def settimeout(self,value):self.timeouts.append(value)
    def read1(self,count):
        if self.clock:self.clock.value+=self.delay
        if self.error:raise self.error
        if not self.chunks:return b''
        chunk=self.chunks.pop(0)
        if len(chunk)>count:self.chunks.insert(0,chunk[count:]);chunk=chunk[:count]
        return chunk
    read=read1

class Opener:
    def __init__(self,reply):self.reply=reply;self.calls=[]
    def open(self,request,timeout):
        self.calls.append((request,timeout))
        if isinstance(self.reply,BaseException):raise self.reply
        return self.reply

class TransportTests(unittest.TestCase):
    def run_request(self,chunks,**kwargs):
        clock=Clock();reply=Reply(chunks,clock,delay=1,**kwargs);opener=Opener(reply)
        result=t.request({'model':'test-model','instructions':'frozen','input':'toy','temperature':0},'secret-key',True,opener=opener,monotonic=clock,wall=lambda:0)
        return result,opener,reply
    def test_complete_native_preserved_fragmented_utf8_and_crlf(self):
        n=native();n['output_text']='café'
        raw=frame('response.created',{'id':n['id'],'model':n['model']})+frame('response.completed',n)+b'data: [DONE]\r\n\r\n'
        chunks=[raw[i:i+1] for i in range(len(raw))]
        reply=Reply(chunks);opener=Opener(reply)
        status,value,private=t.request({'model':'test-model'},'secret-key',True,opener=opener)
        self.assertEqual(value,n);self.assertEqual(private['native_response'],n)
        self.assertEqual(status['terminal_event'],'response.completed');self.assertEqual(status['event_count'],2)
        self.assertEqual(len(opener.calls),1);self.assertTrue(reply.closed)
        self.assertNotIn('Authorization',private['headers'])
    def test_json_same_body_except_explicit_stream(self):
        body={'model':'test-model','input':'café','max_output_tokens':4096,'store':False};original=dict(body)
        reply=Reply([json.dumps(native()).encode()],mime='application/json');opener=Opener(reply)
        status,value,_=t.request(body,'secret-key',False,opener=opener)
        from experiments.swarm_ledger_study import canonical
        self.assertEqual(opener.calls[0][0].data,canonical(dict(body,stream=False)).encode())
        self.assertEqual(body,original);self.assertEqual(value,native());self.assertEqual(status['http_status'],200)
        self.assertIsNone(status['first_event_seconds'])
    def test_json_decode_error_keeps_http_status(self):
        opener=Opener(Reply([b'not-json'],mime='application/json'))
        status,value,_=t.request({'model':'test-model'},'secret-key',False,opener=opener)
        self.assertEqual(status['http_status'],200);self.assertIsNone(value)
        self.assertEqual(status['error'],'response_validation_error')
    def test_delta_and_done_are_not_completed_response(self):
        (status,value,private),opener,_=self.run_request([frame('response.output_text.delta',delta='partial'),b'data: [DONE]\n\n'])
        self.assertIsNone(value);self.assertEqual(status['error'],'response_validation_error')
        self.assertIn('partial',private['raw_text']);self.assertEqual(len(opener.calls),1)
    def test_incomplete_and_failed_are_actual_terminal_states(self):
        for label in ('incomplete','failed','cancelled'):
            with self.subTest(label=label):
                n=native(label);(status,value,_),_,_=self.run_request([frame('response.'+label,n)])
                self.assertEqual(value,n);self.assertEqual(status['response_status'],label)
    def test_conflicting_final_event_is_rejected(self):
        (status,value,_),_,_=self.run_request([frame('response.completed',native())+frame('response.failed',native('failed'))])
        self.assertIsNone(value);self.assertEqual(status['error'],'response_validation_error')
    def test_response_id_and_model_mismatch_rejected(self):
        for n in (native(identity='other'),native(model='other')):
            with self.subTest(n=n):
                (status,value,_),_,_=self.run_request([frame('response.created',native('in_progress'))+frame('response.completed',n)])
                self.assertIsNone(value);self.assertEqual(status['error'],'response_validation_error')
    def test_status_and_event_name_mismatch_rejected(self):
        for raw in (frame('response.completed',native('failed')),b'event: response.completed\ndata: {"type":"response.failed"}\n\n'):
            (status,value,_),_,_=self.run_request([raw]);self.assertIsNone(value)
            self.assertEqual(status['error'],'response_validation_error')
    def test_multiline_data_comments_unknown_events_and_bom(self):
        raw=b'\xef\xbb\xbf: heartbeat\r\nretry: 1\r\nid: ignored\r\nevent: custom\r\ndata: {"type":\r\ndata: "custom"}\r\n\r\n'+frame('response.completed',native())
        (status,value,_),_,_=self.run_request([raw]);self.assertEqual(value,native());self.assertEqual(status['event_count'],2)
    def test_truncated_final_frame_does_not_count_as_complete(self):
        (status,value,_),_,_=self.run_request([frame('response.completed',native()).rstrip(b'\n')])
        self.assertIsNone(value);self.assertEqual(status['error'],'response_validation_error')
    def test_malformed_utf8_or_json_rejected_without_messages(self):
        for raw in (b'data: \xff\n\n',b'data: invalid-secret-key\n\n'):
            (status,value,private),_,_=self.run_request([raw]);self.assertIsNone(value)
            self.assertNotIn('secret-key',json.dumps((status,private)))
            self.assertNotIn('exception_message',status['diagnostics'])
    def test_http504_is_not_retried_or_native(self):
        error=HTTPError(t.ENDPOINT,504,'secret-key',{'Content-Type':'text/html'},io.BytesIO(b'gateway secret-key'))
        opener=Opener(error);status,value,private=t.request({'model':'test-model'},'secret-key',True,opener=opener)
        self.assertEqual(status['http_status'],504);self.assertIsNone(value);self.assertEqual(len(opener.calls),1)
        self.assertEqual(private['error_body'],'gateway [REDACTED]')
    def test_invalid_retry_after_is_boolean_only_on_success_and_http_error(self):
        reply=Reply([json.dumps(native()).encode()],mime='application/json')
        reply.headers['Retry-After']='invalid-secret-key-header'
        error=HTTPError(t.ENDPOINT,504,'secret-key',{'Retry-After':'invalid-secret-key-header'},io.BytesIO(b'gateway'))
        for response in (reply,error):
            with self.subTest(response=type(response).__name__):
                opener=Opener(response)
                status,_,private=t.request({'model':'test-model'},'secret-key',False,opener=opener)
                self.assertIs(status['retry_after_invalid'],True)
                self.assertNotIn('Retry-After',private['headers'])
                self.assertNotIn('invalid-secret-key-header',json.dumps((status,private)))
                self.assertNotIn('secret-key',json.dumps((status,private)))
                self.assertEqual(len(opener.calls),1)
    def test_noevent_timeout_single_post_safe_exception(self):
        error=URLError(OSError(10054,'secret-key'));opener=Opener(Reply([],error=error))
        status,value,private=t.request({'model':'test-model'},'secret-key',True,opener=opener)
        self.assertIsNone(value);self.assertEqual(len(opener.calls),1)
        self.assertEqual(status['diagnostics']['exception_class'],'URLError')
        self.assertEqual(status['diagnostics']['errno'],10054)
        self.assertNotIn('secret-key',json.dumps((status,private)))
    def test_overall_deadline_shrinks_reads_and_rejects_late_final(self):
        clock=Clock();reply=Reply([frame('response.created',native('in_progress')),frame('response.completed',native())],clock,delay=100);opener=Opener(reply)
        status,value,_=t.request({'model':'test-model'},'secret-key',True,timeout=180,opener=opener,monotonic=clock,wall=lambda:0)
        self.assertIsNone(value);self.assertEqual(status['error'],'wall_timeout')
        self.assertEqual(reply.timeouts,[180,80]);self.assertEqual(len(opener.calls),1)
    def test_byte_event_and_content_type_caps(self):
        for kwargs,chunks in (({'max_bytes':8},[b'data: '+b'x'*30]),({'max_events':1},[frame('custom')+frame('response.completed',native())])):
            opener=Opener(Reply(chunks));status,value,_=t.request({'model':'test-model'},'secret-key',True,opener=opener,**kwargs)
            self.assertIsNone(value);self.assertEqual(status['error'],'response_validation_error')
        (status,value,_),_,_=self.run_request([json.dumps(native()).encode()],mime='application/json')
        self.assertIsNone(value);self.assertEqual(status['http_status'],200)
    def test_first_and_final_timings_are_recorded(self):
        (status,value,_),_,_=self.run_request([frame('response.created',native('in_progress')),frame('response.completed',native())])
        self.assertEqual(status['first_event_seconds'],1);self.assertEqual(status['first_data_seconds'],1)
        self.assertEqual(status['final_event_seconds'],2);self.assertEqual(status['latency_seconds'],2)
        self.assertEqual(status['stream_termination'],'semantic_terminal')
    def test_authoritative_terminal_closes_without_waiting_for_server_eof(self):
        clock=Clock();reply=Reply([frame('response.completed',native()),b'never-read'],clock,delay=1);opener=Opener(reply)
        status,value,_=t.request({'model':'test-model'},'secret-key',True,opener=opener,monotonic=clock,wall=lambda:0)
        self.assertEqual(value,native());self.assertEqual(clock.value,1)
        self.assertEqual(reply.chunks,[b'never-read']);self.assertTrue(reply.closed)
        self.assertEqual(status['stream_termination'],'semantic_terminal')

if __name__=='__main__':unittest.main()
