"""Separately frozen capacity canary. Offline verification uses public metadata."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

from experiments import hf_diagnostic as h
from experiments import hf_capacity as v1
from experiments import factorial_study as s
from experiments.factorial_continue import wait_until, Stopped

CONFIG=s.ROOT/'research/hf-capacity-v2-config.json'
FREEZE=s.ROOT/'research/hf-capacity-v2-freeze.json'
RESULTS=s.ROOT/'research/hf-capacity-v2-results.json'
SOURCES=('experiments/hf_capacity_v2.py','experiments/tests/test_hf_capacity_v2.py',
         'research/HF_CAPACITY_V2_PROTOCOL.md','research/hf-capacity-v2-config.json',
         'experiments/hf_capacity.py')
JOB_FIELDS={'localid','started_at','finished_at','start_offset_seconds','terminal',
            'http_status','category','known_usage','input_tokens','output_tokens',
            'returned_model','finish_stop','content_ok','shape_ok','estimated_cost','profile_ok'}


def config():
    c=s.read(CONFIG)
    expected=dict(capacity_id='hf-capacity-v2',registration_tag='hf-capacity-v2',
                  model='meta-llama/Llama-3.3-70B-Instruct:novita',hf_input_rate='0.135',
                  hf_output_rate='0.40',n=24,temperature=0,max_tokens=4096,stream=False,
                  input_byte_cap=24000,minimum_input_tokens=1579,maximum_input_tokens=24000,filler_repeats=2091,
                  initial_pause_seconds=60,minimum_start_interval_seconds=30,
                  cap_usd='0.12',retries=0,output_directory='runs/hf-capacity-v2')
    if s.canonical(c)!=s.canonical(expected):raise ValueError('Capacity configuration changed')
    old=s.config()
    if c['model']!=old['hf_model'] or any(Decimal(c[k])!=Decimal(old[k]) for k in ('hf_input_rate','hf_output_rate')):
        raise ValueError('Original capacity serving profile changed')
    if reserve(c)*c['n']>Decimal(c['cap_usd']):raise ValueError('Capacity reservation exceeds cap')
    return c


def reserve(c):return (c['input_byte_cap']*Decimal(c['hf_input_rate'])+c['max_tokens']*Decimal(c['hf_output_rate']))/1000000
def identity(i):return f'capacity2-{i:02d}'
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()


TimedOpener=v1.TimedOpener


def body(c,i):
    prompt=identity(i)+'\n'+('a '*c['filler_repeats'])+'\nReply exactly OK'
    result=dict(model=c['model'],messages=[dict(role='user',content=prompt)],
                temperature=c['temperature'],max_tokens=c['max_tokens'],stream=c['stream'])
    if len(json.dumps(result).encode())>c['input_byte_cap']:raise ValueError('Capacity input byte cap')
    return result


def plan(c):
    return dict(freeze_sha256=s.sha(FREEZE),planned=c['n'],
                requests=[dict(localid=identity(i),request_sha256=s.digest(body(c,i))) for i in range(c['n'])])


def freeze():
    v1.verify();c=config()
    if FREEZE.exists():raise ValueError('Capacity freeze already exists')
    if subprocess.check_output(['git','status','--porcelain'],cwd=s.ROOT).strip():raise ValueError('Commit capacity sources first')
    record=dict(schema_version=1,config=c,source_sha256={name:s.sha(s.ROOT/name) for name in SOURCES},
                original_freeze_sha256=s.sha(s.FREEZE),
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip())
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,registration_tag=c['registration_tag'])


def verify():
    v1.verify();c=config();f=s.read(FREEZE)
    if set(f)!={'schema_version','config','source_sha256','original_freeze_sha256','base_commit'}:
        raise ValueError('Capacity freeze schema')
    if (type(f['schema_version']) is not int or f['schema_version']!=1 or
            s.canonical(f['config'])!=s.canonical(c) or f['original_freeze_sha256']!=s.sha(s.FREEZE) or
            f['source_sha256']!={name:s.sha(s.ROOT/name) for name in SOURCES}):raise ValueError('Capacity source/freeze mismatch')
    for name in (*SOURCES,'research/'+FREEZE.name):
        blob=subprocess.check_output(['git','show',c['registration_tag']+':'+name],cwd=s.ROOT)
        if blob.replace(b'\r\n',b'\n')!=(s.ROOT/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Capacity registration tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],c['registration_tag']+'^{}'],cwd=s.ROOT,capture_output=True).returncode:
        raise ValueError('Capacity registration ancestry')
    return c


def receipt(public,native,c):
    u=native.get('usage') if isinstance(native,dict) else None
    known=isinstance(u,dict) and all(type(u.get(k)) is int and u[k]>=0 for k in ('prompt_tokens','completion_tokens'))
    choices=native.get('choices') if isinstance(native,dict) else None
    choice=choices[0] if isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict) else {}
    message=choice.get('message');text=message.get('content') if isinstance(message,dict) else None
    model=native.get('model') if isinstance(native,dict) else None
    allowed=h.live_config()['hf_allowed_returned_models']
    model=model if isinstance(model,str) and model in allowed else '<unexpected>'
    finish=choice.get('finish_reason')=='stop'
    content=isinstance(text,str) and text.strip()=='OK'
    ri,ro=Decimal(c['hf_input_rate']),Decimal(c['hf_output_rate'])
    cost=(u['prompt_tokens']*ri+u['completion_tokens']*ro)/1000000 if known else reserve(c)
    result=dict(http_status=public.get('http_status'),category=public.get('category','notdeterminable'),
                known_usage=known,input_tokens=u['prompt_tokens'] if known else None,
                output_tokens=u['completion_tokens'] if known else None,returned_model=model,
                finish_stop=finish,content_ok=content,shape_ok=isinstance(message,dict) and isinstance(text,str),estimated_cost=str(cost))
    result['profile_ok']=profile(result,c)
    return result


def profile(row,c):
    return (row['http_status']==200 and row['known_usage'] is True and
            type(row['input_tokens']) is int and c['minimum_input_tokens']<=row['input_tokens']<=c['maximum_input_tokens'] and
            type(row['output_tokens']) is int and 0<=row['output_tokens']<=c['max_tokens'] and
            row['returned_model'] in h.live_config()['hf_allowed_returned_models'] and
            row['finish_stop'] is True and row['shape_ok'] is True)


def run(authorized=False,opener=None,clock=None,sleep=None):
    if not authorized:raise ValueError('Explicit --run required')
    c=verify();h.guards(h.config());clock=clock or time.monotonic;sleep=sleep or time.sleep
    keys=s.credentials();key=keys.get('HF_TOKEN')
    if not key:raise ValueError('HF credential unavailable')
    out=(s.ROOT/c['output_directory']).resolve()
    if not out.is_relative_to((s.ROOT/'runs').resolve()):raise ValueError('Ignored capacity output required')
    out.mkdir(parents=True,exist_ok=False)
    (out/'plan.json').write_text(json.dumps(plan(c),indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'attempts.jsonl').touch();(out/'responses.jsonl').touch()
    stop=out/'STOP';origin=clock();halted=False;reason='';cost=Decimal(0)
    wire=TimedOpener(opener,clock,stop)
    with (out/'events.jsonl').open('x',encoding='utf-8') as events:
        s.durable(events,dict(event='catalog_start',at=utc()))
        try:public,data=h.request(s.HF+'/models',key,out,'catalog',opener=wire,secrets=keys.values())
        except Exception:public,data=dict(http_status=None,category='notdeterminable'),None
        s.durable(events,dict(event='catalog_terminal',at=utc(),http_status=public.get('http_status')))
        if public.get('http_status')!=200 or not h.catalog_matches(data,c):halted=True;reason='catalog_gate'
        next_start=origin+c['initial_pause_seconds']
        with (out/'attempts.jsonl').open('a',encoding='utf-8') as attempts,(out/'responses.jsonl').open('a',encoding='utf-8') as responses:
            for i in range(c['n']):
                if halted:break
                try:wait_until(next_start,stop,clock,sleep)
                except Stopped:halted=True;reason='operator_stop';break
                try:h.guards(h.config())
                except Exception:halted=True;reason='main_guard';break
                if stop.exists():halted=True;reason='operator_stop';break
                if cost+reserve(c)>Decimal(c['cap_usd']):halted=True;reason='budget';break
                payload=body(c,i);start=clock();at=utc()
                s.durable(attempts,dict(localid=identity(i),started_at=at,start_offset_seconds=start-origin,
                                        request_sha256=s.digest(payload),reserved_cost=str(reserve(c))))
                dispatched=clock()
                wire.last=None
                try:public,native=h.request(s.HF+'/chat/completions',key,out,identity(i),payload,opener=wire,secrets=keys.values())
                except Exception:public,native=dict(http_status=None,category='notdeterminable'),None
                if wire.last is None:public,native=dict(http_status=None,category='notdeterminable'),None
                row=receipt(public,native,c)
                actual=wire.last if wire.last is not None else dispatched
                row.update(localid=identity(i),started_at=at,finished_at=utc(),start_offset_seconds=actual-origin,terminal=True)
                s.durable(responses,row);cost+=Decimal(row['estimated_cost'])
                next_start=max(clock(),actual+c['minimum_start_interval_seconds'])
                if not row['profile_ok'] or cost>Decimal(c['cap_usd']):halted=True;reason='bad_receipt'
    if stop.exists():halted=True;reason='operator_stop'
    summary=dict(halted=halted,stop_reason=reason,freeze_sha256=s.sha(FREEZE))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    return export()


totals=v1.totals


def export(path=None,write=True):
    c=verify();out=s.ROOT/c['output_directory'];starts=s.rows(out/'attempts.jsonl');responses=s.rows(out/'responses.jsonl')
    if s.read(out/'plan.json')!=plan(c):raise ValueError('Capacity plan/freeze mismatch')
    if [r['localid'] for r in starts]!=[identity(i) for i in range(len(starts))] or len(starts)>c['n']:
        raise ValueError('Capacity starts not exact planned prefix')
    byid={r['localid']:r for r in responses}
    if len(byid)!=len(responses) or not set(byid)<={r['localid'] for r in starts}:raise ValueError('Duplicate/orphan capacity terminal')
    jobs=[]
    for i,start in enumerate(starts):
        if start['request_sha256']!=s.digest(body(c,i)) or Decimal(start['reserved_cost'])!=reserve(c):raise ValueError('Capacity body/reserve drift')
        if start['localid'] in byid:
            row=byid[start['localid']]
            if row['started_at']!=start['started_at'] or row['start_offset_seconds']<start['start_offset_seconds']:
                raise ValueError('Capacity start/terminal mismatch')
        else:
            row=dict(localid=start['localid'],started_at=start['started_at'],start_offset_seconds=start['start_offset_seconds'],
                     finished_at=None,terminal=False,http_status=None,category='notdeterminable',known_usage=False,
                     input_tokens=None,output_tokens=None,returned_model='<unexpected>',finish_stop=False,
                     content_ok=False,shape_ok=False,estimated_cost=str(reserve(c)),profile_ok=False)
        if set(row)!=JOB_FIELDS:raise ValueError('Unexpected private fields in capacity terminal')
        jobs.append(row)
    summary=s.read(out/'summary.json') if (out/'summary.json').exists() else {'halted':True,'stop_reason':'interrupted','freeze_sha256':s.sha(FREEZE)}
    if set(summary)!={'halted','stop_reason','freeze_sha256'}:raise ValueError('Capacity summary schema')
    if summary['freeze_sha256']!=s.sha(FREEZE):raise ValueError('Capacity summary freeze mismatch')
    if (out/'STOP').exists():summary={**summary,'halted':True,'stop_reason':'operator_stop'}
    record=dict(schema_version=1,capacity_id=c['capacity_id'],freeze_sha256=s.sha(FREEZE),
                raw_sha256=dict(attempts=raw_sha(out/'attempts.jsonl'),responses=raw_sha(out/'responses.jsonl')),
                halted=summary['halted'],stop_reason=summary['stop_reason'],jobs=jobs,**totals(jobs,c,summary['halted']))
    validate(record,c)
    if write:(RESULTS if path is None else Path(path)).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    return record


def validate(report,c):
    if set(report)!=({'schema_version','capacity_id','freeze_sha256','raw_sha256','halted','stop_reason','jobs'}|set(totals([],c,True))):
        raise ValueError('Unexpected public capacity fields')
    if type(report.get('schema_version')) is not int or report['schema_version']!=1 or report['capacity_id']!=c['capacity_id']:
        raise ValueError('Capacity report schema')
    if report['freeze_sha256']!=s.sha(FREEZE) or type(report['halted']) is not bool:raise ValueError('Capacity report freeze/halt')
    if set(report['raw_sha256'])!={'attempts','responses'}:raise ValueError('Unexpected raw hash fields')
    if report['stop_reason'] not in ('','catalog_gate','operator_stop','main_guard','budget','bad_receipt','interrupted'):
        raise ValueError('Unexpected stop reason')
    if (not report['halted'] and report['stop_reason']!='') or (report['halted'] and report['stop_reason']==''):
        raise ValueError('Contradictory capacity halt/reason')
    for key in ('attempts','responses'):
        value=report['raw_sha256'][key]
        if not isinstance(value,str) or len(value)!=64 or any(x not in '0123456789abcdef' for x in value):raise ValueError('Capacity raw hash')
    jobs=report['jobs']
    if len(jobs)>c['n'] or [r['localid'] for r in jobs]!=[identity(i) for i in range(len(jobs))]:raise ValueError('Capacity public IDs')
    bad_seen=False
    for row in jobs:
        if set(row)!=JOB_FIELDS:raise ValueError('Unexpected capacity job fields')
        for key in ('terminal','known_usage','finish_stop','content_ok','shape_ok','profile_ok'):
            if type(row[key]) is not bool:raise ValueError('Capacity public boolean')
        if not row['terminal'] and (row['known_usage'] or row['profile_ok'] or row['http_status'] is not None):
            raise ValueError('Unresolved capacity start cannot have a receipt')
        if bad_seen:raise ValueError('Capacity continued after failure')
        offset=row['start_offset_seconds']
        if type(offset) not in (int,float) or not math.isfinite(offset) or offset<0:raise ValueError('Capacity offset')
        if row['category'] not in ('quota','balance','capacity','notdeterminable'):raise ValueError('Capacity category')
        if row['http_status'] is not None and (type(row['http_status']) is not int or not 100<=row['http_status']<=599):
            raise ValueError('Capacity HTTP status')
        try:
            start=datetime.fromisoformat(row['started_at'])
            if start.tzinfo is None:raise ValueError('Naive start')
            if row['terminal']:
                end=datetime.fromisoformat(row['finished_at'])
                if end.tzinfo is None or end<start:raise ValueError('Invalid finish')
            elif row['finished_at'] is not None:raise ValueError('Unresolved finish')
        except (TypeError,ValueError):raise ValueError('Capacity timestamp') from None
        if row['returned_model'] not in (*h.live_config()['hf_allowed_returned_models'],'<unexpected>'):raise ValueError('Unsafe model string')
        if row['known_usage']:
            if any(type(row[k]) is not int or row[k]<0 for k in ('input_tokens','output_tokens')):raise ValueError('Capacity usage')
            cost=(row['input_tokens']*Decimal(c['hf_input_rate'])+row['output_tokens']*Decimal(c['hf_output_rate']))/1000000
        else:
            if row['input_tokens'] is not None or row['output_tokens'] is not None:raise ValueError('Unknown usage counts')
            cost=reserve(c)
        if Decimal(row['estimated_cost'])!=cost or row['profile_ok']!=profile(row,c):raise ValueError('Capacity cost/profile drift')
        if not row['terminal'] or not row['profile_ok']:bad_seen=True
    expected=totals(jobs,c,report['halted'])
    if any(type(report[k]) is not type(v) or report[k]!=v for k,v in expected.items()):raise ValueError('Capacity aggregate replay mismatch')
    return report


def verify_results(path=None,private=False):
    c=verify()
    record=validate(s.read(RESULTS if path is None else Path(path)),c)
    if private and export(write=False)!=record:raise ValueError('Capacity public/private replay mismatch')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('freeze','verify','run','export','verify-results'))
    p.add_argument('--run',action='store_true',dest='authorized');a=p.parse_args()
    if a.command=='run':r=run(a.authorized)
    elif a.command=='verify':verify();r={'valid':True}
    elif a.command=='verify-results':r=verify_results()
    else:r=globals()[a.command]()
    print(json.dumps({k:r[k] for k in ('valid','created','registration_tag','planned','returned','unstarted','complete','passed') if k in r}))


if __name__=='__main__':main()
