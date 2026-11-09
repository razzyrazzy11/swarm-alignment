"""Separately registered Ollama readers. No network on import or public verify."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from experiments import factorial_study as s
from experiments.factorial_continue import verify_original_sources, retry_after

BASE='https://ollama.com'
CONFIG=s.ROOT/'research/ollama-config.json'
CATALOG=s.ROOT/'research/ollama-catalog.json'
FREEZE=s.ROOT/'research/ollama-reader-v1-freeze.json'
SOURCES=('experiments/ollama_study.py','experiments/tests/test_ollama_study.py',
         'research/ollama-config.json','research/ollama-catalog.json',
         'research/OLLAMA_PROTOCOL.md','research/FACTORIAL_REPORTING_AMENDMENT.md','experiments/factorial_continue.py')


def now():return datetime.now(timezone.utc).isoformat()
def folder(stage):
    if stage not in ('pilot','readers'):raise ValueError('Unknown Ollama stage')
    return s.ROOT/('runs/'+config()['study_id']+'-'+stage)


def config():
    c=s.read(CONFIG)
    expected=[dict(id='ds_off',model='deepseek-v4.1-flash:1017',think=False,views='all',input_rate='0.30',output_rate='1.20'),
              dict(id='ds_low',model='deepseek-v4.1-flash:1017',think='low',views='sufficient_calibration',input_rate='0.30',output_rate='1.20'),
              dict(id='gemma_bridge',model='gemma4:31b',think=False,views='sufficient_calibration',input_rate='0.14',output_rate='0.40')]
    fixed=dict(study_id='ollama-reader-v1',conditions=expected,order_seed=710033,input_byte_cap=24000,
               max_output_tokens=4096,max_active=2,pilot_stage_cap='0.10',readers_stage_cap='9.90',combined_cap='10.00',
               remaining_credit_floor='5.00',balance_poll_seconds=60,metadata_recheck_calls=100,gateway_allowance=8,
               gateway_backoff_seconds=60,request_timeout_seconds=180,retries=0,cost_basis='published_peak_uncached_estimate_not_invoice')
    if s.canonical(c)!=s.canonical(fixed):raise ValueError('Fixed Ollama configuration changed')
    return c


def condition(identity):
    matches=[c for c in config()['conditions'] if c['id']==identity]
    if len(matches)!=1:raise ValueError('Unknown condition')
    return matches[0]


def rates(job):
    c=condition(job['condition_id'])
    return Decimal(c['input_rate']),Decimal(c['output_rate'])


def allowed_returned_models(condition_id):return [condition(condition_id)['model']]


def plan_for(stage,job_list=None):
    ordered=sorted(jobs(stage) if job_list is None else job_list,key=lambda j:j['id'])
    random.Random(config()['order_seed']).shuffle(ordered)
    ids=[j['id'] for j in ordered]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate extension IDs')
    return dict(freeze_sha256=s.sha(FREEZE),jobs_sha256=s.digest(ordered),ids=ids,planned=len(ordered))


def reservation(job):
    c=config();ri,ro=rates(job)
    return (c['input_byte_cap']*ri+c['max_output_tokens']*ro)/1000000


def credentials(path=None):
    """Literal parser; never execute dotenv or print any credential."""
    path=s.ROOT/'.env' if path is None else Path(path)
    allowed={'OLLAMA_API_KEY','HF_TOKEN','ADAPTION_API_KEY'};values={}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):continue
            key,sep,value=line.partition('=');key=key.strip()
            if sep and key in allowed:
                value=value.strip()
                if len(value)>1 and value[0]==value[-1] and value[0] in ('"',"'"):value=value[1:-1]
                values[key]=value
    for key in allowed:
        if os.environ.get(key):values[key]=os.environ[key]
    values={k:v for k,v in values.items() if v and 'replace_locally' not in v and not v.startswith('YOUR_')}
    if not values.get('OLLAMA_API_KEY'):raise ValueError('OLLAMA_API_KEY unavailable')
    return values


def jobs_from_templates(templates):
    """Pure adapter: reporter may supply reconstructed public original HF jobs."""
    out=[];old_hf=s.config()['hf_model']
    for template in templates:
        if template['model']!=old_hf:raise ValueError('Adapter accepts original HF templates only')
        provider,old_body=s.body_for(template)
        if provider!='hf':raise ValueError('Original HF body expected')
        metadata=template['metadata'];view=metadata['view']
        prompts={'direct':s.DIRECT,'procedure':s.PROCEDURE}
        if metadata['procedure'] not in prompts or template['prompt']!=prompts[metadata['procedure']]:raise ValueError('Frozen reader instruction changed')
        if metadata['packet_sha256']!=s.digest(template['payload']):raise ValueError('Frozen packet commitment changed')
        for c in config()['conditions']:
            if c['views']!='all' and view!='sufficient' and not view.startswith('calibration_'):continue
            m={**metadata,'condition_id':c['id'],'phase':'readers'}
            identity=f"{config()['study_id']}:{c['id']}:{m['source_seed']}:{view}:{m['procedure']}"
            out.append(dict(id=identity,model=c['model'],condition_id=c['id'],messages=old_body['messages'],metadata=m))
    if len({j['id'] for j in out})!=len(out):raise ValueError('Duplicate adapted Ollama IDs')
    return out


def jobs(stage='readers'):
    if stage=='pilot':
        out=[]
        for c in config()['conditions']:
            for i,text in enumerate(('A synthetic serving check. Briefly describe a circle.',
                                      'A synthetic format check. Give a small JSON object about a neutral color.')):
                out.append(dict(id=f"{config()['study_id']}:pilot:{c['id']}:{i}",model=c['model'],condition_id=c['id'],
                                messages=[dict(role='user',content=text)],metadata=dict(condition_id=c['id'],phase='pilot',
                                source_seed=None,view='pilot',procedure='neutral',packet_sha256=s.digest(text))))
        return out
    if stage!='readers':raise ValueError('Unknown job stage')
    out=jobs_from_templates([j for j in s.audit_jobs() if j['model']==s.config()['hf_model']])
    counts={c['id']:sum(j['condition_id']==c['id'] for j in out) for c in config()['conditions']}
    if counts!={'ds_off':3880,'ds_low':424,'gemma_bridge':424}:raise ValueError('Original reader grid changed')
    return out


def body_for(job):
    c=condition(job['condition_id'])
    if job['model']!=c['model'] or job['metadata']['condition_id']!=c['id']:raise ValueError('Condition/model mismatch')
    body=dict(model=job['model'],messages=job['messages'],stream=False,think=c['think'],
              options=dict(temperature=0,num_predict=config()['max_output_tokens']))
    if len(json.dumps(body).encode())>config()['input_byte_cap']:raise ValueError('Native input byte cap')
    return body


def normalize(native,requested,think):
    native=native if isinstance(native,dict) else {}
    msg=native.get('message');text=msg.get('content') if isinstance(msg,dict) else None
    trace=msg.get('thinking') if isinstance(msg,dict) else None
    known=all(type(native.get(k)) is int and native[k]>=0 for k in ('prompt_eval_count','eval_count'))
    usage=dict(input_tokens=native['prompt_eval_count'],output_tokens=native['eval_count']) if known else dict(input_tokens=0,output_tokens=0)
    shape=isinstance(text,str) and native.get('done') is True
    reason=native.get('done_reason')
    status='completed' if shape and reason=='stop' else 'incomplete' if shape and reason=='length' else 'failed'
    returned=native.get('model') if isinstance(native.get('model'),str) else None
    anomaly=(not shape or reason not in ('stop','length') or returned!=requested or
             (trace is not None and not isinstance(trace,str)) or (think is False and isinstance(trace,str) and bool(trace.strip())))
    return dict(status=status,output_text=text if isinstance(text,str) else '',usage=usage,returned_model=returned),known,anomaly


def profile_ok(transport,response,known,anomaly):
    u=response['usage'];c=config()
    return (transport.get('http_status')==200 and known and not anomaly and response['status']=='completed'
            and type(u['input_tokens']) is int and 0<=u['input_tokens']<=c['input_byte_cap']
            and type(u['output_tokens']) is int and 0<=u['output_tokens']<=c['max_output_tokens'])


def admit_response(transport,response,known,anomaly):
    if profile_ok(transport,response,known,anomaly):return dict(response)
    return {**response,'status':'incomplete' if response['status']=='incomplete' else 'failed','output_text':''}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise HTTPError(req.full_url,code,'Redirect refused',headers,fp)


class Transport:
    def __init__(self,keys,out,opener=None,clock=None):
        self.keys=keys;self.out=Path(out);self.opener=opener or build_opener(NoRedirect());self.clock=clock or time.monotonic
        self.lock=threading.Lock();self.ordinal=0

    def request(self,path,body=None):
        if path not in ('/api/chat','/api/tags','/api/show','/api/balance'):raise ValueError('Ollama endpoint refused')
        if path in ('/api/tags','/api/balance') and body is not None:raise ValueError('Metadata GET required')
        if path in ('/api/chat','/api/show') and body is None:raise ValueError('POST body required')
        with self.lock:ordinal=self.ordinal;self.ordinal+=1
        request=Request(BASE+path,data=None if body is None else json.dumps(body).encode(),
                        headers={'Authorization':'Bearer '+self.keys['OLLAMA_API_KEY'],'Content-Type':'application/json',
                                 'User-Agent':'swarm-alignment-ollama/0.1'},method='GET' if body is None else 'POST')
        start=self.clock();native=None;private={};internal=dict(retry_after=0.0,service_overload=False,capture_failed=False)
        try:
            with self.opener.open(request,timeout=config()['request_timeout_seconds']) as reply:
                raw=reply.read(2097153)
                if len(raw)>2097152:raise ValueError('Native receipt too large')
                native=json.loads(raw);public=dict(http_status=reply.status,latency_seconds=round(self.clock()-start,3))
                private=dict(path=path,headers=dict(reply.headers),native_response=native)
        except HTTPError as exc:
            public=dict(http_status=exc.code,latency_seconds=round(self.clock()-start,3),error='HTTPError')
            try:
                raw=exc.read(16384).decode('utf-8',errors='replace')
                private=dict(path=path,headers=dict(exc.headers or {}),error_body=raw,error_body_byte_cap=16384)
                delay=retry_after((exc.headers or {}).get('Retry-After'))
                internal['retry_after']=delay or 0.0
                try:
                    parsed=json.loads(raw);message=parsed.get('error') if isinstance(parsed,dict) else None
                    if isinstance(message,dict):message=message.get('message')
                except ValueError:message=raw
                internal['service_overload']=(exc.code==429 and isinstance(message,str) and message.strip().lower().startswith('server overload'))
            except Exception:internal['capture_failed']=True;private=dict(path=path,error='private_error_capture_failed')
        except (URLError,TimeoutError,OSError,ValueError):
            public=dict(http_status=None,latency_seconds=round(self.clock()-start,3),error='transport_or_json_error')
            private=dict(path=path,error='transport_or_json_error')
        try:
            self.out.mkdir(parents=True,exist_ok=True)
            clean=s.scrub(private,self.keys.values())
            with (self.out/(f'{ordinal:06d}-private.json')).open('x',encoding='utf-8') as file:
                json.dump(clean,file,ensure_ascii=True);file.flush();os.fsync(file.fileno())
        except Exception:internal['capture_failed']=True
        return public,native,internal


def validate_catalog(data):
    if set(data.get('models',{}))!={c['model'] for c in config()['conditions']}:raise ValueError('Catalog model grid')
    for model,item in data['models'].items():
        if not isinstance(item.get('digest'),str) or not item['digest']:raise ValueError('Run metadata-only catalog before freeze to bind exact digest')
        if not isinstance(item.get('thinking'),dict) or not isinstance(item['thinking'].get('values'),list):raise ValueError('Missing think metadata')
        for c in config()['conditions']:
            if c['model']==model and not any(type(c['think']) is type(x) and c['think']==x for x in item['thinking']['values']):raise ValueError('Unsupported thinking mode')
        if item['context_length']<config()['max_output_tokens']+config()['input_byte_cap']:raise ValueError('Context capacity changed')


def metadata(transport,pinned=None):
    public,tags,extra=transport.request('/api/tags')
    if public.get('http_status')!=200 or extra['capture_failed'] or not isinstance(tags,dict):raise ValueError('Ollama catalog unavailable')
    expected=s.read(CATALOG) if pinned is None else pinned;models={}
    for name,old in expected['models'].items():
        found=[m for m in tags.get('models',[]) if isinstance(m,dict) and (m.get('name')==name or m.get('model')==name)]
        if len(found)!=1 or not isinstance(found[0].get('digest'),str):raise ValueError('Exact model tag missing')
        digest=found[0]['digest']
        if old.get('digest') is not None and digest!=old['digest']:raise ValueError('Model digest drift')
        if old.get('digest_prefix') is not None and not digest.startswith(old['digest_prefix']):raise ValueError('Model digest prefix drift')
        public,show,extra=transport.request('/api/show',dict(model=name))
        if public.get('http_status')!=200 or extra['capture_failed'] or not isinstance(show,dict):raise ValueError('Model show unavailable')
        contexts=[v for k,v in show.get('model_info',{}).items() if k.endswith('.context_length') and type(v) is int]
        item=dict(digest=digest,thinking=show.get('thinking'),context_length=max(contexts) if contexts else 0)
        if item['thinking']!=old['thinking'] or item['context_length']!=old['context_length']:raise ValueError('Model capability drift')
        models[name]=item
    result=dict(schema_version=1,checked=now(),mode='Verified read-only model metadata; no account balance published',models=models)
    validate_catalog(result);return result


def catalog():
    if FREEZE.exists():raise ValueError('Frozen catalog cannot be overwritten')
    out=s.ROOT/'runs/ollama-catalog-metadata'
    if out.exists():out=s.ROOT/('runs/ollama-catalog-metadata-'+str(time.time_ns()))
    transport=Transport(credentials(),out)
    record=metadata(transport)
    CATALOG.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(verified=True,models=record['models'],inference_calls=0)


def freeze():
    verify_original_sources();c=config();validate_catalog(s.read(CATALOG))
    if FREEZE.exists():raise ValueError('Ollama freeze exists')
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=s.ROOT)
        if blob.replace(b'\r\n',b'\n')!=(s.ROOT/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Commit each extension source before freeze')
    f=dict(schema_version=1,config=c,source_sha256={n:s.sha(s.ROOT/n) for n in SOURCES},original_freeze_sha256=s.sha(s.FREEZE),
           base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip())
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(f,indent=2)+'\n')
    return dict(created=True,tag=c['study_id'])


def verify():
    verify_original_sources();c=config();validate_catalog(s.read(CATALOG));f=s.read(FREEZE)
    if set(f)!={'schema_version','config','source_sha256','original_freeze_sha256','base_commit'} or type(f['schema_version']) is not int or f['schema_version']!=1:
        raise ValueError('Ollama freeze schema')
    if s.canonical(f['config'])!=s.canonical(c) or f['source_sha256']!={n:s.sha(s.ROOT/n) for n in SOURCES} or f['original_freeze_sha256']!=s.sha(s.FREEZE):raise ValueError('Ollama frozen source mismatch')
    for n in (*SOURCES,'research/'+FREEZE.name):
        blob=subprocess.check_output(['git','show',c['study_id']+':'+n],cwd=s.ROOT)
        if blob.replace(b'\r\n',b'\n')!=(s.ROOT/n).read_bytes().replace(b'\r\n',b'\n'):raise ValueError('Ollama tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],c['study_id']+'^{}'],cwd=s.ROOT,capture_output=True).returncode:raise ValueError('Ollama registration ancestry')
    return c


class Balance:
    def __init__(self,transport,out,clock,sleep=None,wall=None):
        self.transport=transport;self.out=out;self.clock=clock;self.last=None;self.available=None
        self.sleep=sleep or time.sleep;self.wall=wall or time.time
    def check(self,force=False):
        if not force and self.last is not None and self.clock()-self.last<config()['balance_poll_seconds']:return self.available
        account=s.ROOT/('runs/'+config()['study_id']+'-credit-guard');account.mkdir(parents=True,exist_ok=True)
        with exclusive(account):
            checkpoint=account/'balance-private.json'
            if checkpoint.exists():
                previous=s.read(checkpoint);delay=config()['balance_poll_seconds']-(self.wall()-previous['checked_epoch'])
                if delay>120:raise ValueError('Balance clock continuity unknown')
                deadline=self.clock()+max(0,delay)
                while self.clock()<deadline:
                    if (self.out/'STOP').exists():raise ValueError('Operator stop during credit wait')
                    self.sleep(min(1.0,deadline-self.clock()))
            if (self.out/'STOP').exists():raise ValueError('Operator stop before credit poll')
            self.last=self.clock();public,native,extra=self.transport.request('/api/balance')
            checkpoint.write_text(json.dumps(dict(checked_epoch=self.wall()))+'\n',encoding='utf-8')
        if public.get('http_status')!=200 or extra['capture_failed'] or not isinstance(native,dict):raise ValueError('Credit balance unknown')
        try:
            included=Decimal(str(native['included']['balance_usd']));purchased=Decimal(str(native['purchased']['balance_usd']))
            if not included.is_finite() or not purchased.is_finite():raise ValueError('Nonfinite balance')
            self.available=included+purchased
        except (KeyError,TypeError,ArithmeticError):raise ValueError('Credit balance schema unavailable') from None
        with (self.out/'balance-private.jsonl').open('a',encoding='utf-8') as file:
            s.durable(file,dict(checked=now(),included=str(included),purchased=str(purchased)))
        if self.available<=Decimal(config()['remaining_credit_floor']):raise ValueError('Credit floor reached')
        return self.available


def transient(row):
    return (row['transport'].get('http_status') in (502,503,504) or
            (row['transport'].get('http_status')==429 and row.get('service_overload') is True)) and not row['known_usage'] and row.get('native_response') is None and row['transport'].get('error')=='HTTPError'


def fatal(row):
    if row.get('capture_failed'):return True
    if transient(row):return False
    n=row['response'];c=config()
    return (row['transport'].get('http_status')!=200 or not row['known_usage'] or row['profile_anomaly'] or
            n['usage']['input_tokens']>c['input_byte_cap'] or n['usage']['output_tokens']>c['max_output_tokens'] or n['status'] not in ('completed','incomplete'))


@contextmanager
def exclusive(out):
    lock=out/'collector.lock'
    try:handle=lock.open('x',encoding='ascii')
    except FileExistsError:raise ValueError('Collector active or stale lock requires review') from None
    try:
        with handle:handle.write('1\n');handle.flush();yield
    finally:lock.unlink()


def pilot_pass():
    out=folder('pilot');summary=s.read(out/'summary.json');rows=s.rows(out/'responses.jsonl')
    if not summary['complete'] or summary['halted'] or len(rows)!=6 or any(not profile_ok(r['transport'],r['response'],r['known_usage'],r['profile_anomaly']) for r in rows):raise ValueError('Pilot serving/profile gate failed')
    return True


def execute(stage,resume=False,transport=None,clock=None,sleep=None):
    c=verify();s.verify()
    if stage=='readers':pilot_pass()
    clock=clock or time.monotonic;sleep=sleep or time.sleep
    js=sorted(jobs(stage),key=lambda j:j['id']);[body_for(j) for j in js]
    plan=plan_for(stage,js);random.Random(c['order_seed']).shuffle(js)
    if len(set(plan['ids']))!=len(js):raise ValueError('Duplicate extension IDs')
    out=folder(stage)
    if out.exists() and not resume:raise ValueError('Run exists; never retry')
    if not out.exists():
        out.mkdir(parents=True);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')
    with exclusive(out):
        if s.read(out/'plan.json')!=plan:raise ValueError('Changed extension plan')
        starts=s.rows(out/'attempts.jsonl');results=s.rows(out/'responses.jsonl')
        ids={r['id'] for r in results};started={r['id'] for r in starts};byid={j['id']:j for j in js}
        if len(ids)!=len(results) or len(started)!=len(starts) or started!=ids or not ids<=set(byid):raise ValueError('Unresolved/duplicate start; never retry')
        for a in starts:
            if a['request_sha256']!=s.digest(body_for(byid[a['id']])) or Decimal(a['reserved_cost'])!=reservation(byid[a['id']]):raise ValueError('Historical body/reserve drift')
        for r in results:
            j=byid[r['id']];ri,ro=rates(j);u=r['response']['usage']
            expected=(u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if r['known_usage'] else reservation(j)
            if Decimal(r['estimated_cost'])!=expected:raise ValueError('Historical cost mismatch')
        gateways=sum(transient(r) for r in results)
        if any(fatal(r) for r in results) or gateways>=c['gateway_allowance']:raise ValueError('Prior fatal gate remains active')
        if (out/'summary.json').exists() and s.read(out/'summary.json').get('halted'):raise ValueError('Prior halted stage cannot resume')
        cost=sum((Decimal(r['estimated_cost']) for r in results),Decimal(0))
        try:
            keys=credentials();transport=transport or Transport(keys,out/'private')
            metadata(transport,s.read(CATALOG));balance=Balance(transport,out,clock,sleep=sleep);balance.check(force=True)
        except Exception:
            summary=dict(planned=len(js),returned=len(results),unstarted=len(js)-len(results),complete=len(results)==len(js),halted=True,
                         stop_reason='startup_gate',gateway_errors=gateways,incomplete=sum(r['response']['status']=='incomplete' for r in results),
                         estimated_cost=str(cost),cost_basis=c['cost_basis'],freeze_sha256=s.sha(FREEZE))
            (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
            raise ValueError('Startup metadata/credit/private evidence gate failed') from None
        other=folder('pilot') if stage=='readers' else folder('readers')
        other_cost=sum((Decimal(r['estimated_cost']) for r in s.rows(other/'responses.jsonl')),Decimal(0))
        pending=[j for j in js if j['id'] not in ids];active={};halt=False;reason='';next_dispatch=clock();completed_since_metadata=0
        stop=out/'STOP'
        with (out/'attempts.jsonl').open('a',encoding='utf-8') as attempts,(out/'responses.jsonl').open('a',encoding='utf-8') as output:
            with ThreadPoolExecutor(max_workers=c['max_active']) as pool:
                while pending or active:
                    if stop.exists():halt=True;reason='operator_stop'
                    if not halt:
                        try:balance.check()
                        except Exception:halt=True;reason='credit_gate'
                    if not halt and completed_since_metadata>=c['metadata_recheck_calls'] and not active:
                        try:metadata(transport,s.read(CATALOG));completed_since_metadata=0
                        except Exception:halt=True;reason='metadata_drift'
                    dispatch_limit=min(c['max_active'],c['gateway_allowance']-gateways)
                    while pending and not halt and clock()>=next_dispatch and len(active)<dispatch_limit and completed_since_metadata<c['metadata_recheck_calls']:
                        j=pending[0];reserve=reservation(j);reserved=sum(v[1] for v in active.values())
                        if cost+reserved+reserve>Decimal(c[stage+'_stage_cap']) or other_cost+cost+reserved+reserve>Decimal(c['combined_cap']):
                            if not active:halt=True;reason='budget'
                            break
                        if stop.exists():halt=True;reason='operator_stop';break
                        body=body_for(j)
                        s.durable(attempts,dict(id=j['id'],request_sha256=s.digest(body),reserved_cost=str(reserve),provider='ollama',started=now()))
                        future=pool.submit(transport.request,'/api/chat',body)
                        active[future]=(j,reserve,len(results)+len(active));pending.pop(0)
                    if not active:
                        if halt or not pending:break
                        sleep(min(1.0,max(0.001,next_dispatch-clock())))
                        continue
                    finished,_=wait(active,timeout=1.0,return_when=FIRST_COMPLETED)
                    for future in sorted(finished,key=lambda f:active[f][2]):
                        j,reserve,_=active.pop(future)
                        try:public,native,extra=future.result()
                        except Exception:public,native,extra=dict(http_status=None,error='unexpected_request_error'),None,dict(retry_after=0,service_overload=False,capture_failed=True)
                        n,known,anomaly=normalize(native,j['model'],condition(j['condition_id'])['think']);ri,ro=rates(j);u=n['usage']
                        estimated=(u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if known else reserve;cost+=estimated
                        row=s.scrub(dict(id=j['id'],model=j['model'],metadata=j['metadata'],provider='ollama',transport=public,response=n,
                                         known_usage=known,estimated_cost=str(estimated),native_response=native,profile_anomaly=anomaly,
                                         service_overload=extra.get('service_overload',False),capture_failed=extra.get('capture_failed',False)),keys.values())
                        s.durable(output,row);results.append(row);completed_since_metadata+=1
                        if transient(row):
                            gateways+=1;next_dispatch=max(next_dispatch,clock()+max(c['gateway_backoff_seconds'],extra.get('retry_after',0)))
                        if fatal(row) or gateways>=c['gateway_allowance'] or (stage=='pilot' and not profile_ok(public,n,known,anomaly)):
                            halt=True;reason='serving_or_profile_gate'
                        if cost>Decimal(c[stage+'_stage_cap']) or other_cost+cost>Decimal(c['combined_cap']):halt=True;reason='budget_overrun'
        summary=dict(planned=len(js),returned=len(results),unstarted=len(pending),complete=len(results)==len(js),halted=halt,
                     stop_reason=reason,gateway_errors=gateways,incomplete=sum(r['response']['status']=='incomplete' for r in results),
                     estimated_cost=str(cost),cost_basis=c['cost_basis'],freeze_sha256=s.sha(FREEZE))
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        return summary


def collection_status():
    """Safe operational guard for exporters; no scientific response text emitted."""
    result={}
    for stage in ('pilot','readers'):
        out=folder(stage)
        if (out/'collector.lock').exists():raise ValueError('Ollama collection is active or lock unresolved')
        starts=s.rows(out/'attempts.jsonl');rows=s.rows(out/'responses.jsonl')
        a={r['id'] for r in starts};b={r['id'] for r in rows}
        if len(a)!=len(starts) or len(b)!=len(rows) or a!=b:raise ValueError('Ollama collection has unresolved/duplicate starts')
        summary=s.read(out/'summary.json') if (out/'summary.json').exists() else None
        result[stage]=dict(started=len(starts),returned=len(rows),complete=summary.get('complete',False) if summary else False,
                           halted=summary.get('halted',False) if summary else False,present=out.exists())
    return dict(stopped=True,stages=result)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('catalog','verify','freeze','run'))
    parser.add_argument('--stage',choices=('pilot','readers'));parser.add_argument('--continue-unstarted',action='store_true')
    args=parser.parse_args()
    if args.command=='run':
        if not args.stage:parser.error('--stage required')
        result=execute(args.stage,args.continue_unstarted)
    elif args.command=='verify':verify();result=dict(valid=True,mode='public source/tag verification; no private ledgers or calls')
    else:result=globals()[args.command]()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
