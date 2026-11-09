"""Bounded single-attempt JSON/SSE Responses transport for an excluded pilot.

No provider call, credential load, or file mutation occurs on import. The caller
owns reservation-before-send, receipt durability and frozen model/usage scoring.
"""
import codecs
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException, IncompleteRead
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from experiments.collection_connectivity import _safe_headers, _exception_fields
from experiments.swarm_ledger_study import NoRedirect

ENDPOINT='https://api.prod.adaptionlabs.ai/api/v1/responses'
TERMINALS={'response.completed':'completed','response.incomplete':'incomplete',
           'response.failed':'failed','response.cancelled':'cancelled'}

class StreamValidationError(ValueError):pass
class WallTimeout(TimeoutError):pass

def _scrub(value,key):
    if isinstance(value,str):return value.replace(key,'[REDACTED]') if key else value
    if isinstance(value,list):return [_scrub(x,key) for x in value]
    if isinstance(value,dict):return {_scrub(k,key):_scrub(v,key) for k,v in value.items()}
    return value

def _remaining_timeout(reply,seconds):
    """Narrow each real urllib socket read to the remaining overall budget.

    DNS/platform open may not be preemptible by Python. Monotonic checks reject
    over-budget results; no helper thread or second POST is ever launched.
    """
    candidates=[reply]
    current=reply
    for _ in range(4):
        current=getattr(current,'fp',None)
        if current is None:break
        candidates.extend((current,getattr(current,'raw',None)))
    for candidate in candidates:
        sock=getattr(candidate,'_sock',None)
        if sock is not None and callable(getattr(sock,'settimeout',None)):
            sock.settimeout(seconds);return
    # Explicit injected test/socket wrappers may expose settimeout themselves.
    if callable(getattr(reply,'settimeout',None)):reply.settimeout(seconds)

def _headers_and_retry_flag(headers,status):
    """Retain only a Boolean when a raw Retry-After fails safe validation."""
    safe=_safe_headers(headers)
    supplied=headers is not None and headers.get('Retry-After') is not None
    if supplied and 'Retry-After' not in safe:status['retry_after_invalid']=True
    return safe

class SSEParser:
    """Incremental UTF8 and SSE framing; a final response object is mandatory."""
    def __init__(self,max_events=10000):
        if type(max_events) is not int or not 1<=max_events<=10000:raise ValueError('Bounded event limit required')
        self.decoder=codecs.getincrementaldecoder('utf-8')('strict')
        self.buffer='';self.data=[];self.event='';self.count=0;self.max_events=max_events
        self.native=None;self.terminal_event=None;self.seen_id=None;self.seen_model=None
        self.done=False;self.first=True

    def _dispatch(self):
        if not self.data:self.event='';return []
        text='\n'.join(self.data);event=self.event;self.data=[];self.event=''
        if text=='[DONE]':self.done=True;return [('done',None)]
        if self.done:raise StreamValidationError('Data after DONE')
        self.count+=1
        if self.count>self.max_events:raise StreamValidationError('Event cap exceeded')
        payload=json.loads(text)
        if not isinstance(payload,dict):raise StreamValidationError('SSE data must be an object')
        kind=payload.get('type',event)
        if not isinstance(kind,str):raise StreamValidationError('Invalid SSE event type')
        if event and payload.get('type') and event!=payload['type']:raise StreamValidationError('SSE event/type disagreement')
        response=payload.get('response')
        if response is not None:
            if not isinstance(response,dict):raise StreamValidationError('Invalid response envelope')
            for name,attribute in (('id','seen_id'),('model','seen_model')):
                current=response.get(name)
                if current is not None:
                    if not isinstance(current,str) or not current:raise StreamValidationError('Invalid response identity')
                    previous=getattr(self,attribute)
                    if previous is not None and current!=previous:raise StreamValidationError('Conflicting response identity/model')
                    setattr(self,attribute,current)
        if kind in TERMINALS:
            if self.native is not None:raise StreamValidationError('Repeated or contradictory final event')
            if not isinstance(response,dict) or response.get('status')!=TERMINALS[kind]:raise StreamValidationError('Terminal status disagreement')
            if self.seen_id is not None and response.get('id')!=self.seen_id:raise StreamValidationError('Final response identity missing')
            if self.seen_model is not None and response.get('model')!=self.seen_model:raise StreamValidationError('Final response model missing')
            self.native=response;self.terminal_event=kind
        if kind=='error':raise StreamValidationError('Provider stream error')
        return [('event',kind)]

    def _line(self,line):
        if self.first:line=line.lstrip('\ufeff');self.first=False
        if line=='':return self._dispatch()
        if line.startswith(':'):return []
        field,sep,value=line.partition(':')
        if sep and value.startswith(' '):value=value[1:]
        if field=='data':self.data.append(value)
        elif field=='event':self.event=value
        # id/retry/unknown SSE fields affect neither model identity nor retries.
        return []

    def feed(self,raw,final=False):
        self.buffer+=self.decoder.decode(raw,final=final);events=[]
        while True:
            cr=self.buffer.find('\r');lf=self.buffer.find('\n')
            positions=[x for x in (cr,lf) if x>=0]
            if not positions:break
            pos=min(positions)
            if self.buffer[pos]=='\r' and pos==len(self.buffer)-1 and not final:break
            width=2 if self.buffer[pos:pos+2]=='\r\n' else 1
            line,self.buffer=self.buffer[:pos],self.buffer[pos+width:]
            events.extend(self._line(line))
        # SSE does not dispatch an unterminated event just because EOF occurs.
        if final and (self.buffer or self.data):raise StreamValidationError('Truncated final SSE frame')
        return events

    def result(self):
        if self.native is None:raise StreamValidationError('No terminal response object')
        return self.native

def request(body,key,stream,timeout=180,opener=None,monotonic=time.monotonic,
            wall=time.time,max_bytes=2097152,max_events=10000):
    """One POST only; returns (safe status, exact native terminal, private receipt).

    first_data_seconds is the first noncomment SSE data frame; first_event_seconds
    is the first decoded JSON event. JSON mode leaves these SSE metrics null.
    Private raw_text is bounded and key-scrubbed, including partial streams.
    A complete semantic terminal frame ends the response after processing the
    current read chunk. Conflicting finals already in that chunk are rejected;
    later chunks are not read. This avoids erasing a genuine completed response
    merely because a provider leaves the SSE connection open after completion.
    """
    if not isinstance(body,dict) or type(stream) is not bool:raise ValueError('Body and literal streaming mode required')
    if not isinstance(key,str) or not key:raise ValueError('Credential required')
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or not 0<timeout<=180:raise ValueError('Bounded timeout required')
    if type(max_bytes) is not int or not 1<=max_bytes<=2097152:raise ValueError('Bounded byte cap required')
    prepared=dict(body);prepared['stream']=stream
    req=Request(ENDPOINT,data=json.dumps(prepared,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8'),
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    opener=opener or build_opener(NoRedirect())
    start,started_wall=monotonic(),wall();deadline=start+timeout
    status=dict(http_status=None,latency_seconds=None,first_event_seconds=None,first_data_seconds=None,
                first_byte_seconds=None,final_event_seconds=None,event_count=0,terminal_event=None,response_status=None,
                stream_termination=None,post_terminal_unparsed=False)
    stage='open';raw=bytearray();native=None;headers={};private={};diagnostic={}
    parser=SSEParser(max_events) if stream else None
    def remaining():
        seconds=deadline-monotonic()
        if seconds<=0:raise WallTimeout('Overall request deadline')
        return seconds
    try:
        with opener.open(req,timeout=remaining()) as reply:
            status['http_status']=reply.status
            headers=_headers_and_retry_flag(reply.headers,status)
            if type(reply.status) is not int or not 200<=reply.status<300:raise StreamValidationError('Unexpected HTTP success status')
            mime=headers.get('Content-Type','')
            if stream and mime!='text/event-stream':raise StreamValidationError('Expected SSE content type')
            if not stream and mime not in ('application/json','application/problem+json'):raise StreamValidationError('Expected JSON content type')
            while True:
                stage='read';left=remaining();_remaining_timeout(reply,left)
                reader=getattr(reply,'read1',None) or reply.read
                chunk=reader(min(4096,max_bytes+1-len(raw)))
                remaining()
                if not chunk:break
                if not isinstance(chunk,bytes):raise StreamValidationError('Expected response bytes')
                if status['first_byte_seconds'] is None:status['first_byte_seconds']=round(monotonic()-start,6)
                raw.extend(chunk);stage='size_check'
                if len(raw)>max_bytes:raise StreamValidationError('Response byte cap exceeded')
                if stream:
                    stage='sse_decode'
                    events=parser.feed(chunk)
                    for event,kind in events:
                        if status['first_data_seconds'] is None:status['first_data_seconds']=round(monotonic()-start,6)
                        if event=='event' and status['first_event_seconds'] is None:status['first_event_seconds']=round(monotonic()-start,6)
                        if kind in TERMINALS:status['final_event_seconds']=round(monotonic()-start,6)
                    if parser.native is not None:
                        status['stream_termination']='semantic_terminal'
                        status['post_terminal_unparsed']=bool(parser.buffer or parser.data or parser.event)
                        break
                    if parser.done:
                        status['stream_termination']='done_without_terminal'
                        break
            if stream:
                stage='sse_final'
                if parser.native is None:parser.feed(b'',final=True)
                native=parser.result()
                status['terminal_event']=parser.terminal_event
            else:
                stage='json_decode';native=json.loads(bytes(raw))
                if not isinstance(native,dict):raise StreamValidationError('Native response must be an object')
                status['final_event_seconds']=round(monotonic()-start,6)
            remaining();status['response_status']=native.get('status');stage='complete'
    except HTTPError as error:
        status.update(http_status=error.code,error='HTTPError');headers=_headers_and_retry_flag(error.headers,status)
        try:
            stage='http_error_read';remaining();_remaining_timeout(error,remaining())
            raw.extend(error.read(min(16384,max_bytes)));remaining()
            private['error_body']=bytes(raw).decode('utf-8',errors='replace');stage='http_error'
        except (OSError,ValueError,HTTPException) as capture:
            status['capture_failed']=True;diagnostic.update(_exception_fields(capture))
    except (URLError,OSError,ValueError,HTTPException) as error:
        status['error']='wall_timeout' if isinstance(error,WallTimeout) else 'transport_error' if isinstance(error,(URLError,OSError,HTTPException)) else 'response_validation_error'
        diagnostic.update(_exception_fields(error));native=None
        if isinstance(error,IncompleteRead) and isinstance(error.partial,bytes):
            raw.extend(error.partial[:max(0,max_bytes+1-len(raw))])
    finally:
        if parser is not None:status['event_count']=parser.count
        diagnostic.update(stage=stage,body_bytes=len(raw),body_sha256=hashlib.sha256(raw).hexdigest(),
            started_utc=datetime.fromtimestamp(started_wall,timezone.utc).isoformat(),finished_utc=datetime.fromtimestamp(wall(),timezone.utc).isoformat())
        status['latency_seconds']=round(monotonic()-start,6);status['diagnostics']=diagnostic
        private.update(headers=headers,raw_text=bytes(raw[:max_bytes]).decode('utf-8',errors='replace'))
        if native is not None:private['native_response']=native
    return _scrub(status,key),_scrub(native,key),_scrub(private,key)
