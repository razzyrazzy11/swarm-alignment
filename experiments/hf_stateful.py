"""Separately registered, matched HF model-family/serving replication.

Selects frozen source indices without reading any Adaption model outputs.
"""
import argparse,hashlib,json,random,subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from experiments.access import ROOT,credentials,request_json
from experiments.pilot import scrub
from experiments.stateful import FAMILIES
from experiments.stateful_study import (config as core_config,verify_freeze as verify_core,
    SOURCES as CORE_SOURCES,FREEZE as CORE_FREEZE,PROMPT,episode,tasks_for,
    canonical_file,sha,durable,score_stateful)

CONFIG=ROOT/'research/hf-stateful-config.json'
FREEZE=ROOT/'research/stateful-hf-v1-freeze.json'
SOURCES=('experiments/hf_stateful.py','research/hf-stateful-config.json','research/hf-stateful-catalog.json','research/HF_STATEFUL_PROTOCOL.md',
         'experiments/stateful_release.py','experiments/tests/test_stateful_release.py','experiments/tests/test_hf_stateful.py',
         'research/stateful-main-v2-freeze.json')+CORE_SOURCES
ENDPOINT='https://router.huggingface.co/v1'

def config():return json.loads(CONFIG.read_text(encoding='utf-8'))

def selected_catalog(data,c):
    if c['model']!=c['catalog_model']+':'+c['provider']:raise ValueError('Model/provider mapping mismatch')
    if not isinstance(data,dict) or not isinstance(data.get('data'),list):raise ValueError('Catalog schema')
    rows=data['data'];found=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('id')!=c['catalog_model']:continue
        providers=row.get('providers')
        if not isinstance(providers,list):raise ValueError('Provider catalog schema')
        found.extend(p for p in providers if isinstance(p,dict) and p.get('provider')==c['provider'])
    if len(found)!=1 or found[0].get('status')!='live':raise ValueError('Pinned provider unavailable')
    price=found[0].get('pricing')
    if not isinstance(price,dict) or any(type(price.get(k)) not in (int,float,str) for k in ('input','output')):raise ValueError('Missing provider price')
    try:matches=Decimal(str(price['input']))==Decimal(str(c['input_usd_per_million'])) and Decimal(str(price['output']))==Decimal(str(c['output_usd_per_million']))
    except InvalidOperation:matches=False
    if not matches:raise ValueError('Live pricing differs from frozen rates')
    return found[0]

def catalog():
    key=credentials().get('HF_TOKEN')
    if not key:raise ValueError('HF token unavailable')
    transport,data=request_json(ENDPOINT+'/models',key)
    if transport.get('http_status')!=200:raise ValueError('HF catalog unavailable')
    selected=selected_catalog(data,config())
    if not FREEZE.exists():
        (ROOT/'research/hf-stateful-catalog.json').write_text(json.dumps(dict(checked=datetime.now(timezone.utc).isoformat(),model=config()['catalog_model'],provider=selected),indent=2)+'\n',encoding='utf-8')
    return dict(model=config()['catalog_model'],provider=selected['provider'],status=selected['status'],pricing=selected['pricing'])

def freeze():
    verify_core()
    if FREEZE.exists():raise ValueError('Registration exists')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT).strip():raise ValueError('Commit sources and protocol first')
    if subprocess.run(['git','rev-parse','--verify','--quiet','refs/tags/'+config()['study_id']],cwd=ROOT,capture_output=True).returncode==0:raise ValueError('Tag exists')
    f=dict(created=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           config=config(),source_sha256={n:sha(ROOT/n) for n in SOURCES},core_freeze_sha256=sha(CORE_FREEZE))
    FREEZE.write_text(json.dumps(f,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(freeze_sha256=sha(FREEZE),next='Commit and tag stateful-hf-v1 before inference')

def verify_freeze():
    verify_core();f=json.loads(FREEZE.read_text(encoding='utf-8'));tag=config()['study_id']
    if f['source_sha256']!={n:sha(ROOT/n) for n in SOURCES} or f['config']!=config() or f['core_freeze_sha256']!=sha(CORE_FREEZE):raise ValueError('HF/core source mismatch')
    if subprocess.check_output(['git','show',tag+':research/'+FREEZE.name],cwd=ROOT).replace(b'\r\n',b'\n')!=canonical_file(FREEZE):raise ValueError('HF tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],tag+'^{}'],cwd=ROOT,capture_output=True).returncode!=0:raise ValueError('HF registration ancestry mismatch')
    for name,expected in f['source_sha256'].items():
        blob=subprocess.check_output(['git','show',tag+':'+name],cwd=ROOT).replace(b'\r\n',b'\n')
        if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('HF tagged source mismatch')
    return f

def prepare():
    c=config();core=core_config();sources=[]
    indices=c['source_indices_per_family']
    if not isinstance(indices,list) or len(indices)!=8 or any(type(j) is not int or not 0<=j<core['stages']['main']['episodes_per_family'] for j in indices) or len(set(indices))!=len(indices):raise ValueError('Invalid/duplicate replication source indices')
    for family in core['stages']['main']['families']:
        for j in c['source_indices_per_family']:
            seed=core['stages']['main']['seed_start']+10000*FAMILIES.index(family)+j
            sources.append(episode(seed,family,j))
    return sources,[t for e in sources for t in tasks_for(e)]

def normalize(data):
    if not isinstance(data,dict):return dict(status='failed',output_text='')
    choices=data.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):return dict(status='failed',output_text='')
    choice=choices[0];message=choice.get('message') or {}
    text=message.get('content') if isinstance(message,dict) else None
    if not isinstance(text,str) or not text.strip():return dict(status='failed',output_text='')
    return dict(status='completed' if choice.get('finish_reason')=='stop' else 'incomplete',output_text=text)

def run():
    f=verify_freeze();c=config();out=ROOT/'runs/stateful-hf-v1'
    if out.exists():raise ValueError('HF output exists; no silent retry/resume')
    keys=credentials();key=keys.get('HF_TOKEN')
    if not key:raise ValueError('HF token unavailable')
    transport,data=request_json(ENDPOINT+'/models',key)
    if transport.get('http_status')!=200:raise ValueError('HF catalog unavailable before dispatch')
    live=selected_catalog(data,c)
    out.mkdir(parents=True);sources,tasks=prepare();order=tasks.copy();random.Random(c['request_order_seed']).shuffle(order)
    for name,value in (('episodes.json',sources),('packets.json',tasks),('manifest.json',dict(stage='hf_replication',freeze=f,live_provider=live,order=[(t['task_id'],c['model']) for t in order]))):
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    snapshot=out/'source';snapshot.mkdir()
    for name,expected in f['source_sha256'].items():
        raw=canonical_file(ROOT/name)
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('HF source changed before dispatch')
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    ri=Decimal(str(c['input_usd_per_million']));ro=Decimal(str(c['output_usd_per_million']));reserve=(c['input_byte_cap']*ri+c['max_output_tokens']*ro)/1000000
    spent=Decimal(0);rows=[];started=0;halt=False;incomplete=0
    with (out/'attempts.jsonl').open('x',encoding='utf-8') as attempts,(out/'responses.jsonl').open('x',encoding='utf-8') as responses:
      with ThreadPoolExecutor(max_workers=c['concurrency']) as pool:
        for offset in range(0,len(order),c['concurrency']):
            if halt or (out/'STOP').exists():halt=True;break
            batch=order[offset:offset+c['concurrency']]
            if spent+reserve*len(batch)>Decimal(c['nominal_usd_cap']):halt=True;break
            bodies=[]
            for t in batch:
                text=json.dumps(t['packet'],sort_keys=True,separators=(',',':'))
                if len((PROMPT+text).encode())>c['input_byte_cap']:halt=True;break
                bodies.append(dict(model=c['model'],messages=[dict(role='system',content=PROMPT),dict(role='user',content=text)],temperature=0,max_tokens=c['max_output_tokens'],stream=False))
            if halt:break
            futures={}
            for t,body in zip(batch,bodies):
                durable(attempts,dict(task_id=t['task_id'],model=c['model'],reserved_usd=str(reserve),started=datetime.now(timezone.utc).isoformat()));started+=1
                futures[pool.submit(request_json,ENDPOINT+'/chat/completions',key,body,timeout=120)]=t
            for future in as_completed(futures):
                t=futures[future]
                try:transport,data=future.result()
                except Exception:transport,data={'http_status':None,'error':'unexpected_request_error'},None
                u=data.get('usage') if isinstance(data,dict) else None
                known=isinstance(u,dict) and all(type(u.get(k)) is int and u[k]>=0 for k in ('prompt_tokens','completion_tokens'))
                charge=(u['prompt_tokens']*ri+u['completion_tokens']*ro)/1000000 if known else reserve;spent+=charge
                normalized=normalize(data);incomplete+=normalized['status']!='completed'
                row=scrub(dict(task=t,model=c['model'],transport=transport,response=data,normalized=normalized,known_usage=known,estimated_usd=str(charge),scored=score_stateful(normalized,t['compatible_labels'])),keys.values())
                durable(responses,row);rows.append(row)
                if not known or data.get('model') not in c['allowed_returned_models'] or u['prompt_tokens']>c['input_byte_cap'] or u['completion_tokens']>c['max_output_tokens'] or incomplete>=3 or transport.get('http_status') in (401,402,403,429):halt=True
    summary=dict(stage='hf_replication',complete=not halt and len(rows)==len(order),source_episodes=len(sources),planned_calls=len(order),attempted_calls=started,retained_responses=len(rows),
                 estimated_usd=str(spent),freeze_sha256=sha(FREEZE),invalid=sum(r['scored']['status']=='INVALID' for r in rows),incomplete=incomplete,
                 billing='Token-price estimate, not reconciled HF debit',scope='Matched secondary model-family/serving check on fixed main-source subset; not independent source replication or identical-checkpoint claim')
    summary['counts']={m:sum(r['scored'][m] for r in rows) for m in ('grounded_correct','supported_definite','unsupported_executor','unsupported_none','strict_schema_valid')}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['catalog','freeze','verify-freeze','plan','run']);a=p.parse_args()
    result=catalog() if a.command=='catalog' else freeze() if a.command=='freeze' else verify_freeze() if a.command=='verify-freeze' else run() if a.command=='run' else dict(configuration=config(),mode='offline metadata only')
    print(json.dumps(result,indent=2))
