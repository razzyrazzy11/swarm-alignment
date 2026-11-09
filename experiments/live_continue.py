"""Registered exact-unstarted continuation; known-usage truncations remain INVALID."""
import argparse,hashlib,json,random,shutil,subprocess
from datetime import datetime,timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from experiments.access import ROOT,ADAPTION,credentials,request_json
from experiments.pilot import scrub
from experiments.live_study import (config,read,rows,sha,durable,canonical,digest,rates,response,body_for,unsafe as original_gate,verify as verify_core,FREEZE,folder,audit_jobs,receiver_jobs,qualification_pass)
from experiments.live_study import HF
ID='live-audit-v2-continuation-v1'
REG=ROOT/('research/'+ID+'-freeze.json')
SOURCES=('experiments/live_continue.py','experiments/tests/test_live_continue.py','research/LIVE_CONTINUATION.md','research/live-audit-v2-freeze.json')
ARCHIVE=ROOT/'runs/live-audit-v2-audits-initial'
FILES=('plan.json','attempts.jsonl','responses.jsonl','summary.json')
def hashes(d):return {n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in FILES}
def continue_gate(row,gateways,incomplete):
    # Only the known-usage incomplete COUNT halt is overridden. Unknown usage,
    # auth/rate/model/token/cost/time/gateway gates and no-retry rules remain.
    return original_gate(row,gateways,0)
def freeze():
    verify_core();qualification_pass()
    if REG.exists() or subprocess.run(['git','rev-parse','--verify','--quiet','refs/tags/'+ID],cwd=ROOT,capture_output=True).returncode==0:raise ValueError('Continuation exists')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT).strip():raise ValueError('Commit continuation before registration')
    d=folder('audits');a=rows(d/'attempts.jsonl');r=rows(d/'responses.jsonl');s=read(d/'summary.json')
    if len(a)!=204 or len(r)!=204 or {x['id'] for x in a}!={x['id'] for x in r} or s['incomplete']!=3 or s['complete']:raise ValueError('Unexpected predecessor')
    if not all(x['known_usage'] for x in r):raise ValueError('Unexpected unknown liability')
    f=dict(created=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256={n:sha(ROOT/n) for n in SOURCES},core_freeze_sha256=sha(FREEZE),predecessor_hashes=hashes(d),original_planned=8064,previous_starts=204,unstarted=7860,override='Retain known-usage incomplete responses as INVALID without count halt. Fill bounded 4/2 sliding window from unchanged priority permutation; reserve all active liabilities. Other gates and scientific plan unchanged.')
    REG.write_text(json.dumps(f,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(tag=ID,freeze_sha256=sha(REG))
def verify():
    verify_core();f=read(REG)
    if f['source_sha256']!={n:sha(ROOT/n) for n in SOURCES} or f['core_freeze_sha256']!=sha(FREEZE):raise ValueError('Continuation source mismatch')
    for name,expected in {**f['source_sha256'],'research/'+REG.name:sha(REG)}.items():
        raw=subprocess.check_output(['git','show',ID+':'+name],cwd=ROOT).replace(b'\r\n',b'\n')
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Continuation tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],ID+'^{}'],cwd=ROOT,capture_output=True).returncode:raise ValueError('Continuation ancestry')
    return dict(valid=True,tag=ID,freeze_sha256=sha(REG))

def execute(jobs,out,resume=False):
    """Exact unstarted-complement resume only; unknown starts are never retried."""
    verify();c=config();keys=credentials()
    if out.exists() and not resume:raise ValueError('Output exists; explicit unstarted continuation required')
    for j in jobs:body_for(j)  # Validate every body before any start is journaled.
    plan=dict(freeze_sha256=sha(FREEZE),jobs_sha256=digest(jobs),ids=[j['id'] for j in jobs],planned=len(jobs))
    if len(plan['ids'])!=len(set(plan['ids'])):raise ValueError('Duplicate jobs')
    if out.exists():
        if read(out/'plan.json')!=plan:raise ValueError('Continuation plan changed')
    else:
        out.mkdir(parents=True);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    starts=rows(out/'attempts.jsonl');results=rows(out/'responses.jsonl');byid={r['id']:r for r in results};started={s['id'] for s in starts}
    if len(started)!=len(starts) or len(byid)!=len(results) or started!=set(byid) or not started<=set(plan['ids']):raise ValueError('Unknown, duplicated or unreturned start; never retry')
    spent={'adaption':Decimal(0),'hf':Decimal(0)}
    for r in results:spent[r['provider']]+=Decimal(r['estimated_cost'])
    gateways=sum(r['transport'].get('http_status') in (502,503,504) for r in results)
    incomplete=sum(r['response']['status']=='incomplete' for r in results)
    if any(continue_gate(r,gateways,incomplete) for r in results):raise ValueError('Prior safety gate remains active; do not resume around it')
    pending=[j for j in jobs if j['id'] not in started];halt=False
    # The unchanged permutation is a priority queue. Fill idle slots while a
    # slow request is outstanding; account for every active reservation.
    with (out/'attempts.jsonl').open('a',encoding='utf-8') as attempts,(out/'responses.jsonl').open('a',encoding='utf-8') as output:
      with ThreadPoolExecutor(max_workers=c['concurrency']) as pool:
        futures={};ordinal=0
        while pending or futures:
            if (out/'STOP').exists():halt=True
            while pending and not halt and len(futures)<c['concurrency']:
                hf_count=sum(v[1]=='hf' for v in futures.values())
                index=next((i for i,j in enumerate(pending) if j['model']!=c['hf_model'] or hf_count<c['hf_concurrency']),None)
                if index is None:break
                j=pending[index]
                ri,ro=rates(j['model']);provider,body=body_for(j)
                reserve=(c['input_byte_cap']*ri+c['max_output_tokens']*ro)/1000000
                active_reserved=sum((v[2] for v in futures.values() if v[1]==provider),Decimal(0))
                cap=Decimal(c['hf_phase_cap'] if provider=='hf' else c['adaption_phase_cap'])
                if spent[provider]+active_reserved+reserve>cap:
                    # Active liabilities may reconcile below their reservations.
                    # Wait for them before declaring the phase budget exhausted.
                    if not active_reserved:halt=True
                    break
                url=HF+'/chat/completions' if provider=='hf' else ADAPTION+'/responses';key=keys['HF_TOKEN' if provider=='hf' else 'ADAPTION_API_KEY']
                durable(attempts,dict(id=j['id'],request_sha256=digest(body),reserved_cost=str(reserve),provider=provider,started=datetime.now(timezone.utc).isoformat()))
                futures[pool.submit(request_json,url,key,body,timeout=120)]=(j,provider,reserve,ordinal)
                ordinal+=1;pending.pop(index)
            if not futures:break
            finished,_=wait(futures,return_when=FIRST_COMPLETED)
            for future in sorted(finished,key=lambda f:futures[f][3]):
                j,provider,reserve,_=futures.pop(future)
                try:transport,native=future.result()
                except Exception:transport,native={'http_status':None,'error':'unexpected_request_error'},None
                try:n,known=response(native,j['model'])
                except (ValueError,TypeError,KeyError,OverflowError):
                    n=dict(status='failed',output_text='',usage=None,returned_model=None);known=False
                    transport=dict(transport,error='normalization_failure')
                ri,ro=rates(j['model']);u=n['usage'];cost=(u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if known else reserve
                spent[provider]+=cost;is_gateway=transport.get('http_status') in (502,503,504);gateways+=int(is_gateway);incomplete+=int(n['status']=='incomplete')
                row=scrub(dict(id=j['id'],model=j['model'],metadata=j['metadata'],provider=provider,transport=transport,response=n,known_usage=known,estimated_cost=str(cost),native_response=native),keys.values())
                durable(output,row);results.append(row)
                if continue_gate(row,gateways,incomplete):halt=True
    summary=dict(operational_registration=ID,operational_freeze_sha256=sha(REG),planned=len(jobs),returned=len(results),complete=len(results)==len(jobs),halted=halt,unstarted=len(pending),gateway_errors=gateways,incomplete=incomplete,costs={p:str(v) for p,v in spent.items()},freeze_sha256=sha(FREEZE))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');return summary


def run(stage):
    verify();qualification_pass()
    if stage=='audits':
        if ARCHIVE.exists():raise ValueError('Continuation already started; inspect retained journals, do not duplicate')
        if hashes(folder('audits'))!=read(REG)['predecessor_hashes']:raise ValueError('Predecessor changed')
        shutil.copytree(folder('audits'),ARCHIVE)
        return execute(audit_jobs(),folder('audits'),resume=True)
    if not read(folder('audits')/'summary.json')['complete']:raise ValueError('Main audits incomplete')
    return execute(receiver_jobs(influence=True) if stage=='influence' else audit_jobs(influence=True),folder(stage))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','verify','run'));p.add_argument('--stage',choices=('audits','influence','influence-audits'));a=p.parse_args()
    if a.command=='run' and not a.stage:p.error('--stage required')
    print(json.dumps(freeze() if a.command=='freeze' else verify() if a.command=='verify' else run(a.stage),indent=2))
