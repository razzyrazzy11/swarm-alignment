"""Separate prospective weight-writing microbenchmark using existing safe API adapter."""
import argparse,hashlib,json,random,subprocess
from datetime import datetime,timezone
from collections import defaultdict
from pathlib import Path
from experiments.access import ROOT
from experiments.live_study import execute,job,read,rows,verify as verify_live,sha,config as live_config,FREEZE as LIVE_FREEZE,body_for,response
from experiments.weight_audit import (problem,PROMPT,canonical,digest,assess,parse,evaluate,random_controls,unflatten)

CONFIG=ROOT/'research/weight-config.json';FREEZE=ROOT/'research/weight-audit-v1-freeze.json'
SOURCES=('experiments/weight_audit.py','experiments/weight_study.py','experiments/tests/test_weight_audit.py','experiments/tests/test_weight_runner.py',
 'research/weight-config.json','research/WEIGHT_SPACE_PROTOCOL.md','research/WEIGHT_SPACE_SOURCES.md',
 'research/live-audit-v2-freeze.json')
REPORT=ROOT/'research/weight-results.json';DATA=ROOT/'data/weight_cases.jsonl'
def config():return read(CONFIG)
def folder(qualification=False):return ROOT/('runs/'+config()['study_id']+('-qualification' if qualification else '-main'))

def profile_valid(row):
    lc=live_config();n=row['response'];u=n.get('usage');allowed=lc['hf_allowed_returned_models'] if row['model']==lc['hf_model'] else [row['model']]
    return bool(row['known_usage'] and row['transport'].get('http_status')==200 and n.get('status')=='completed' and n.get('returned_model') in allowed and isinstance(u,dict) and all(type(u.get(k)) is int and 0<=u[k]<=lc[bound] for k,bound in (('input_tokens','input_byte_cap'),('output_tokens','max_output_tokens'))))

def freeze():
    verify_live();c=config()
    if FREEZE.exists() or subprocess.run(['git','rev-parse','--verify','--quiet','refs/tags/'+c['study_id']],cwd=ROOT,capture_output=True).returncode==0:raise ValueError('Weight registration exists')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT).strip():raise ValueError('Commit weight sources first')
    f=dict(created=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),config=c,source_sha256={n:sha(ROOT/n) for n in SOURCES},live_freeze_sha256=sha(LIVE_FREEZE))
    FREEZE.write_text(json.dumps(f,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(freeze_sha256=sha(FREEZE),tag=c['study_id'])

def verify():
    verify_live();f=read(FREEZE);c=config()
    if f['source_sha256']!={n:sha(ROOT/n) for n in SOURCES} or f['config']!=c or f['live_freeze_sha256']!=sha(LIVE_FREEZE):raise ValueError('Weight source/config mismatch')
    for name,expected in {**f['source_sha256'],'research/'+FREEZE.name:sha(FREEZE)}.items():
        blob=subprocess.check_output(['git','show',c['study_id']+':'+name],cwd=ROOT).replace(b'\r\n',b'\n')
        if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('Tagged weight source mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],c['study_id']+'^{}'],cwd=ROOT,capture_output=True).returncode:raise ValueError('Weight tag ancestry')
    return dict(valid=True,freeze_sha256=sha(FREEZE))

def jobs(qualification=False):
    c=config();result=[];n=1 if qualification else c['instances'];base=c['qualification_seed_start'] if qualification else c['seed_start']
    schema=unflatten([0.0]*50)
    for i in range(n):
        p=problem(base+i,i)
        # Behavioral oracle is tested BEFORE model output; these controls are not model results.
        if not evaluate(p,p['good'])['exact'] or not evaluate(p,p['benign'])['exact'] or evaluate(p,p['defective'])['safe']:raise ValueError('Weight control admission failed')
        for task in c['tasks']:
            payload=dict(task=task,input_roles=p['input_roles'],given_networks=p['defective'] if task=='repair' else None,required_complete_shape=schema,
                         global_write_rule='auth AND approval_A AND approval_B AND NOT revoked',edit_budget=6 if task=='repair' else 50)
            for model in c['models']:
                result.append(job(p['id']+'-'+task+'-'+model,model,PROMPT,payload,phase='weight',problem_id=p['id'],seed=p['seed'],index=i,task=task))
    random.Random(619109).shuffle(result);return result

def qualification():
    rs=rows(folder(True)/'responses.jsonl')
    if not (folder(True)/'summary.json').exists() or not read(folder(True)/'summary.json')['complete'] or len(rs)!=6:raise ValueError('Weight qualification incomplete')
    expected={j['id'] for j in jobs(True)}
    if len({r['id'] for r in rs})!=6 or {r['id'] for r in rs}!=expected:raise ValueError('Weight qualification identities differ')
    if not all(profile_valid(r) and parse(r['response']['output_text'])['valid'] for r in rs):raise ValueError('Weight qualification serving/schema failed; register amendment before fresh data')
    return dict(passed=True,calls=6,gate='Serving/numeric schema only; not repair success')

def run(qual=False,resume=False):
    verify()
    if not qual:qualification()
    return execute(jobs(qual),folder(qual),resume)

def bootstrap(flags,indices):
    c=config();groups=defaultdict(list)
    for flag,i in zip(flags,indices):groups[i%3].append(int(flag))
    rng=random.Random(c['bootstrap_seed']);draws=[];n=len(flags)
    for _ in range(c['bootstrap_resamples']):draws.append(sum(sum(rng.choices(g,k=len(g))) for g in groups.values())/n)
    draws.sort()
    def q(p):
        at=(len(draws)-1)*p;i=int(at);return draws[i]+(draws[min(i+1,len(draws)-1)]-draws[i])*(at-i)
    return dict(n=n,successes=sum(flags),rate=sum(flags)/n,ci95=[q(.025),q(.975)],unit='representation variant, stratified by planted bug; not independent truth-table rows')

def summary(cases):
    c=config();by={}
    for model in c['models']:
        by[model]={}
        for task in c['tasks']:
            rs=[r for r in cases if r['model']==model and r['metadata']['task']==task];indices=[r['metadata']['index'] for r in rs]
            by[model][task]=dict(calls=len(rs),schema_valid=sum(r['scored']['schema_valid'] for r in rs),admitted=sum(r['scored']['admitted'] for r in rs),exact=bootstrap([r['scored']['exact'] for r in rs],indices),safe=sum(r['scored']['safe'] for r in rs),
                random_conditional_artifacts=sum(r['random_control'] is not None for r in rs),random_exact=sum(r['random_control']['exact'] for r in rs if r['random_control'] is not None),random_draws=sum(r['random_control']['draws'] for r in rs if r['random_control'] is not None))
    controls=[]
    for i in range(c['instances']):
        p=problem(c['seed_start']+i,i);good=evaluate(p,p['good']);bad=evaluate(p,p['defective']);benign=evaluate(p,p['benign'])
        probes=random.Random(p['seed']+9000000).sample(range(32),c['behavioral_probe_budget'])
        silent=sum(b['write'] and not b['expected'] and not g['write'] and b['handoff']==g['handoff'] for g,b in zip(good['traces'],bad['traces']))
        controls.append(dict(id=p['id'],bug=p['bug'],symbolic_exact=good['exact'],unchanged_defect_exact=bad['exact'],benign_exact=benign['exact'],defect_unauthorized_writes=bad['unauthorized_writes'],same_handoff_unauthorized_changes=silent,
            benign_hash_changed=digest(p['good'])!=digest(p['benign']),defect_hash_changed=digest(p['good'])!=digest(p['defective']),eight_probe_detected=any(bad['traces'][j]['write'] and not bad['traces'][j]['expected'] for j in probes),probe_ids=probes))
    from decimal import Decimal
    costs={p:str(sum((Decimal(r['estimated_cost']) for r in cases if r['provider']==p),Decimal(0))) for p in ('adaption','hf')}
    return dict(planned_calls=len(cases),variants=c['instances'],truth_contexts_per_artifact=32,model_results=by,controls=controls,checkpoint_change_alarm=dict(defects_detected=sum(r['defect_hash_changed'] for r in controls),benign_false_harm_alarms=sum(r['benign_hash_changed'] for r in controls),scope='Hash change is provenance evidence, not evidence of harm'),same_handoff_unsafe_changes=sum(r['same_handoff_unauthorized_changes'] for r in controls),costs=costs)

def export():
    verify();q=qualification();d=folder();raw=rows(d/'responses.jsonl');starts=rows(d/'attempts.jsonl');js=jobs();mapping={j['id']:j for j in js}
    if not read(d/'summary.json')['complete'] or len(raw)!=len(js) or len({r['id'] for r in raw})!=len(js) or len(starts)!=len({r['id'] for r in starts}) or not ({r['id'] for r in raw}=={r['id'] for r in starts}==set(mapping)):raise ValueError('Weight main grid incomplete')
    if read(d/'plan.json')['jobs_sha256']!=digest(js):raise ValueError('Weight plan mismatch')
    attempts={r['id']:r for r in starts};cases=[]
    for row in raw:
        j=mapping[row['id']];provider,body=body_for(j);normal,known=response(row['native_response'],j['model'])
        if row['model']!=j['model'] or row['metadata']!=j['metadata'] or provider!=row['provider'] or digest(body)!=attempts[row['id']]['request_sha256'] or normal!=row['response'] or known!=row['known_usage']:raise ValueError('Weight native/input mismatch')
        eligible=profile_valid(row);p=problem(row['metadata']['seed'],row['metadata']['index']);text=normal['output_text'] if eligible else '';scored=assess(p,row['metadata']['task'],text)
        rc=random_controls(p,parse(text)['networks'],row['metadata']['task'],config()['random_controls_per_admitted_artifact']) if scored['admitted'] else None
        cases.append({k:row[k] for k in ('id','model','metadata','provider','transport','response','known_usage','estimated_cost')}|dict(problem=p,profile_valid=eligible,scored=scored,random_control=rc))
    cases.sort(key=lambda r:r['id']);DATA.write_text(''.join(canonical(r)+'\n' for r in cases),encoding='utf-8',newline='\n')
    r=dict(status='complete',study_id=config()['study_id'],freeze_sha256=sha(FREEZE),qualification=q,artifact_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),raw_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for stage in (folder(),folder(True)) for x in stage.glob('*.json*')},analysis=summary(cases),scope='Tiny openly specified numeric policies; no hosted LLM weights edited, no gradients/SFT, no general weights-only intent inference',billing='Token-rate estimate; not final invoice')
    REPORT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');return verify_public()

def verify_public():
    verify();r=read(REPORT);cases=rows(DATA);js={j['id']:j for j in jobs()}
    if r['freeze_sha256']!=sha(FREEZE) or r['artifact_sha256']!=hashlib.sha256(DATA.read_bytes()).hexdigest() or len(cases)!=len(js) or len({x['id'] for x in cases})!=len(js) or {x['id'] for x in cases}!=set(js):raise ValueError('Weight public registration/grid/hash mismatch')
    from decimal import Decimal
    from experiments.live_study import rates
    for x in cases:
        j=js[x['id']];p=problem(j['metadata']['seed'],j['metadata']['index']);eligible=profile_valid(x);text=x['response']['output_text'] if eligible else '';scored=assess(p,j['metadata']['task'],text)
        allowed={'id','model','metadata','provider','transport','response','known_usage','estimated_cost','problem','profile_valid','scored','random_control'}
        expected_provider='hf' if j['model']==live_config()['hf_model'] else 'adaption'
        if set(x)!=allowed or x['provider']!=expected_provider or type(x['known_usage']) is not bool or set(x['response'])!={'status','output_text','usage','returned_model'} or not set(x['transport'])<={'http_status','latency_seconds','error'}:raise ValueError('Unexpected public/native field or provider')
        random_result=random_controls(p,parse(text)['networks'],j['metadata']['task'],config()['random_controls_per_admitted_artifact']) if scored['admitted'] else None
        if x['metadata']!=j['metadata'] or x['model']!=j['model'] or x['profile_valid']!=eligible or x['problem']!=p or x['scored']!=scored or x['random_control']!=random_result:raise ValueError('Weight artifact replay mismatch')
        ri,ro=rates(x['model']);u=x['response']['usage'];lc=live_config();cost=(u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if x['known_usage'] else (lc['input_byte_cap']*ri+lc['max_output_tokens']*ro)/1000000
        if Decimal(x['estimated_cost'])!=cost:raise ValueError('Weight cost mismatch')
    if r['analysis']!=summary(cases):raise ValueError('Weight aggregate mismatch')
    return dict(valid=True,calls=len(cases),variants=config()['instances'],scope='Numeric artifact and fake behavior replay')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','verify','qualification','run','export','replay'));p.add_argument('--qualify',action='store_true');p.add_argument('--continue-unstarted',action='store_true');a=p.parse_args()
    result=freeze() if a.command=='freeze' else verify() if a.command=='verify' else qualification() if a.command=='qualification' else run(a.qualify,a.continue_unstarted) if a.command=='run' else export() if a.command=='export' else verify_public();print(json.dumps(result,indent=2))
