"""Explicitly registered operational continuation, never retries started cases."""
import argparse,hashlib,json,shutil,subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from experiments.access import ROOT,ADAPTION,credentials,request_json
from experiments.pilot import RATES,scrub
from experiments.stateful_study import (verify_freeze as verify_core,config,PROMPT,FREEZE as CORE_FREEZE,
    sha,canonical_file,durable,score_stateful)

ID='stateful-main-v2-continuation-v1'
FREEZE=ROOT/('research/'+ID+'-freeze.json')
ORIGINAL=ROOT/'runs/stateful-main-v2-main'
OUT=ROOT/('runs/'+ID)
FILES=('manifest.json','episodes.json','packets.json','attempts.jsonl','responses.jsonl','summary.json')
SOURCES=('experiments/stateful_continue.py','experiments/tests/test_stateful_continue.py','research/STATEFUL_CONTINUATION.md','research/stateful-main-v2-freeze.json')

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines()]
def rawsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def freeze():
    f=verify_core()
    if FREEZE.exists() or subprocess.run(['git','rev-parse','--verify','--quiet','refs/tags/'+ID],cwd=ROOT,capture_output=True).returncode==0:raise ValueError('Continuation registration exists')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT).strip():raise ValueError('Commit continuation before registration')
    summary=read(ORIGINAL/'summary.json');attempts=rows(ORIGINAL/'attempts.jsonl');responses=rows(ORIGINAL/'responses.jsonl')
    if summary['complete'] or len(attempts)!=3028 or len(responses)!=3028:raise ValueError('Unexpected predecessor stage')
    uncertain=[r for r in responses if not r['known_usage']]
    if len(uncertain)!=1 or uncertain[0]['transport'].get('http_status')!=502:raise ValueError('Unexpected predecessor stop reason')
    artifact=dict(created=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        predecessor_hashes={n:rawsha(ORIGINAL/n) for n in FILES},source_sha256={n:sha(ROOT/n) for n in SOURCES},core_freeze_sha256=sha(CORE_FREEZE),
        planned_total=3840,previous_starts=3028,new_starts=812,total_gateway_allowance=3,nominal_credit_cap='20',core_config=f['config'])
    FREEZE.write_text(json.dumps(artifact,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(freeze_sha256=sha(FREEZE),tag=ID)

def verify():
    verify_core();f=read(FREEZE)
    if f['source_sha256']!={n:sha(ROOT/n) for n in SOURCES} or f['core_freeze_sha256']!=sha(CORE_FREEZE):raise ValueError('Continuation source mismatch')
    if subprocess.check_output(['git','show',ID+':research/'+FREEZE.name],cwd=ROOT).replace(b'\r\n',b'\n')!=canonical_file(FREEZE):raise ValueError('Continuation tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],ID+'^{}'],cwd=ROOT,capture_output=True).returncode!=0:raise ValueError('Continuation ancestry mismatch')
    for name,expected in f['source_sha256'].items():
        blob=subprocess.check_output(['git','show',ID+':'+name],cwd=ROOT).replace(b'\r\n',b'\n')
        if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('Tagged continuation source mismatch')
    return f

def remaining(manifest,attempts,tasks):
    started={(r['task_id'],r['model']) for r in attempts}
    if len(started)!=len(attempts):raise ValueError('Duplicate predecessor start')
    order=[tuple(v) for v in manifest['order']]
    if len(order)!=3840 or len(set(order))!=3840 or not started<=set(order):raise ValueError('Invalid original order')
    byid={t['task_id']:t for t in tasks}
    return [(byid[t],m) for t,m in order if (t,m) not in started]

def run():
    f=verify();c=config()
    if OUT.exists():raise ValueError('Continuation output exists; no rerun')
    if {n:rawsha(ORIGINAL/n) for n in FILES}!=f['predecessor_hashes']:raise ValueError('Predecessor changed')
    original_attempts=rows(ORIGINAL/'attempts.jsonl');original_rows=rows(ORIGINAL/'responses.jsonl')
    if {(r['task']['task_id'],r['model']) for r in original_rows}!={(r['task_id'],r['model']) for r in original_attempts}:raise ValueError('Unreturned predecessor start; do not retry uncertain requests')
    pending=remaining(read(ORIGINAL/'manifest.json'),original_attempts,read(ORIGINAL/'packets.json'))
    if len(pending)!=f['new_starts']:raise ValueError('Continuation count mismatch')
    keys=credentials();key=keys.get('ADAPTION_API_KEY')
    if not key:raise ValueError('Adaption key unavailable')
    OUT.mkdir(parents=True)
    (OUT/'manifest.json').write_text(json.dumps(dict(registration=f,core_freeze=read(CORE_FREEZE),order=[(t['task_id'],m) for t,m in pending]),indent=2)+'\n',encoding='utf-8')
    snapshot=OUT/'source';snapshot.mkdir()
    for name,expected in f['source_sha256'].items():
        raw=canonical_file(ROOT/name)
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Source changed before continuation')
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    spent=Decimal(read(ORIGINAL/'summary.json')['estimated_credits']);gateway=sum(r['transport'].get('http_status') in (502,503,504) for r in original_rows)
    incompletes=sum(isinstance(r.get('response'),dict) and r['response'].get('status')=='incomplete' for r in original_rows)
    new=[];halt=False;started=0
    with (OUT/'attempts.jsonl').open('x',encoding='utf-8') as attempts,(OUT/'responses.jsonl').open('x',encoding='utf-8') as responses:
      with ThreadPoolExecutor(max_workers=c['concurrency']) as pool:
        for offset in range(0,len(pending),c['concurrency']):
            if halt or (OUT/'STOP').exists():halt=True;break
            batch=pending[offset:offset+c['concurrency']];reserves=[];bodies=[]
            for t,m in batch:
                ri,ro=map(Decimal,RATES[m]);reserves.append((c['input_byte_cap']*ri+c['max_output_tokens']*ro)/1000000)
                payload=json.dumps(t['packet'],sort_keys=True,separators=(',',':'))
                if len((PROMPT+payload).encode())>c['input_byte_cap']:halt=True;break
                bodies.append(dict(model=m,instructions=PROMPT,input=payload,temperature=0,max_output_tokens=c['max_output_tokens'],tools=[],tool_choice='none',agentic_memory=False,store=False))
            if halt or spent+sum(reserves)>Decimal(f['nominal_credit_cap']):halt=True;break
            futures={}
            for (t,m),reserve,body in zip(batch,reserves,bodies):
                durable(attempts,dict(task_id=t['task_id'],model=m,reserved_credits=str(reserve),started=datetime.now(timezone.utc).isoformat()));started+=1
                futures[pool.submit(request_json,ADAPTION+'/responses',key,body,timeout=120)]=(t,m,reserve)
            for future in as_completed(futures):
                t,m,reserve=futures[future]
                try:transport,data=future.result()
                except Exception:transport,data={'http_status':None,'error':'unexpected_request_error'},None
                u=data.get('usage') if isinstance(data,dict) else None
                known=isinstance(u,dict) and all(type(u.get(k)) is int and u[k]>=0 for k in ('input_tokens','output_tokens'))
                ri,ro=map(Decimal,RATES[m]);charge=(u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if known else reserve;spent+=charge
                is_gateway=transport.get('http_status') in (502,503,504);gateway+=int(is_gateway)
                incompletes+=int(isinstance(data,dict) and data.get('status')=='incomplete')
                row=scrub(dict(task=t,model=m,transport=transport,response=data,known_usage=known,estimated_credits=str(charge),scored=score_stateful(data,t['compatible_labels'])),keys.values())
                durable(responses,row);new.append(row)
                if (not known and not is_gateway) or gateway>f['total_gateway_allowance'] or incompletes>=3 or transport.get('http_status') in (401,402,403,429) or (known and (data.get('model')!=m or u['input_tokens']>c['input_byte_cap'] or u['output_tokens']>c['max_output_tokens'])):halt=True
    summary=dict(complete=not halt and len(new)==len(pending),planned_new_calls=len(pending),attempted_calls=started,retained_responses=len(new),
                 estimated_credits_total=str(spent),total_gateway_failures=gateway,model_incomplete=incompletes,freeze_sha256=sha(FREEZE))
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary

def combine():
    f=verify();s=read(OUT/'summary.json')
    if not s['complete']:raise ValueError('Continuation incomplete; do not publish a complete collection')
    if {n:rawsha(ORIGINAL/n) for n in FILES}!=f['predecessor_hashes']:raise ValueError('Predecessor altered')
    aa=rows(ORIGINAL/'attempts.jsonl')+rows(OUT/'attempts.jsonl');rr=rows(ORIGINAL/'responses.jsonl')+rows(OUT/'responses.jsonl')
    verify_union(read(ORIGINAL/'manifest.json')['order'],aa,rr)
    merged=ROOT/'runs/stateful-main-v2-main-combined';archive=ROOT/'runs/stateful-main-v2-main-initial'
    runs=(ROOT/'runs').resolve()
    if not runs.is_relative_to(ROOT.resolve()) or any(p.resolve().parent!=runs for p in (ORIGINAL,merged,archive)) or merged.exists() or archive.exists():raise ValueError('Unsafe or existing archive/merged paths')
    merged.mkdir()
    for name in ('episodes.json','packets.json'):
        shutil.copyfile(ORIGINAL/name,merged/name)
    shutil.copytree(ORIGINAL/'source',merged/'source')
    manifest=read(ORIGINAL/'manifest.json');manifest['operational_continuation']=dict(registration=ID,freeze_sha256=sha(FREEZE),initial_path=archive.name,continuation_path=OUT.name,original_manifest_sha256=f['predecessor_hashes']['manifest.json'])
    (merged/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    for name in ('attempts.jsonl','responses.jsonl'):(merged/name).write_bytes((ORIGINAL/name).read_bytes()+(OUT/name).read_bytes())
    summary=dict(stage='main',planned_calls=3840,attempted_calls=3840,retained_responses=3840,complete=True,estimated_credits=s['estimated_credits_total'],
        incomplete=sum(not isinstance(r.get('response'),dict) or r['response'].get('status')!='completed' for r in rr),freeze_sha256=sha(CORE_FREEZE),qualification_pass=False,
        billing='Token-rate estimates include unknown-charge reservations; not final debit',operational_amendment=ID,original_stage_complete=False)
    (merged/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    # Both verified absolute paths stay in the same intended runs/ directory.
    # Preserve the untouched predecessor, then publish the audited union.
    ORIGINAL.rename(archive);merged.rename(ORIGINAL)
    return summary

def verify_union(order,attempts,responses):
    planned={tuple(x) for x in order};starts={(x['task_id'],x['model']) for x in attempts};answers={(x['task']['task_id'],x['model']) for x in responses}
    if len(order)!=3840 or len(planned)!=3840 or len(attempts)!=3840 or len(responses)!=3840 or starts!=answers or starts!=planned:raise ValueError('Merged collection is not exactly one terminal attempt per planned call')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','verify','run','combine']);a=p.parse_args()
    print(json.dumps(freeze() if a.command=='freeze' else verify() if a.command=='verify' else run() if a.command=='run' else combine(),indent=2))
