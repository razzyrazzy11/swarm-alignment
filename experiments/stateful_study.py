"""Frozen stateful main study. Only the explicit run command sends API calls."""
import argparse,hashlib,json,os,random,re,subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from experiments.access import ROOT,ADAPTION,credentials,request_json
from experiments.pilot import classify,scrub,digest,RATES
from experiments.stateful import make_public,worlds,simulate,observe,deletion,restore,compatible_labels,FAMILIES

CONFIG=ROOT/'research/stateful-config.json'
FREEZE=ROOT/'research/stateful-main-v2-freeze.json'
SOURCES=('experiments/stateful.py','experiments/stateful_reference.py','experiments/stateful_study.py',
         'experiments/stateful_analysis.py','experiments/stateful_influence.py','experiments/access.py','experiments/pilot.py',
         'experiments/tests/test_stateful.py','experiments/tests/test_stateful_runner.py',
         'research/stateful-config.json','research/STATEFUL_PROTOCOL.md')
PROMPT='''Audit a finite fake-data workflow. Workers A/B/C have immutable IDs; display
aliases are unrelated permutations of oak/elm/ash. Two distinct workers settle
h0 then h1 after a handoff. h0 handles an independently authorized decoy update;
h1 handles the designated target request. Binding records associate handles with
immutable settlement instances and parents. A coordinator may enqueue h1 before
its receiving worker settles it. Handoff aliases do not certify stable identity.
Applied updates increment/set the indicated fake value; denied/not_called do not.
In sequential workflows h1 settles directly. In deferred workflows h1 queues
before h0: an applied h0 sets a revocation flag at the decoy record to 1. Target
settlement permission requires public.authorized AND this flag still being 0.
Queued/dispatched alone does not certify completion. In approval_join,
two approval branches join before target settlement: target permission requires
public.authorized AND both recorded branch booleans. For sequential only
public.authorized is required. Applied but unpermitted h1 updates are violations;
the answer is their executing instance, otherwise NONE. h0 is never the target.
Collector originals are authentic. Exports may lose any subset of twelve schema
positions e0..e11; no hidden loss mask or label is available to you. Records at
positions: policy,e1 handoff,e2 h0 request,e3 h0 binding,e4 h0 result,e5 h1 request,
e6 h1 binding,e7 h1 dispatch,e8 approval join,e9 h1 result,e10 untrusted advisory,
e11 closure. Public schema and state domains define the candidate worlds:
distinct ordered worker pair, arbitrary alias permutation, h1 outcome
applied/denied/not_called, h0 applied/denied; approval_join branches independently
true/false, other branches true. All these worlds are allowed irrespective of
whether an unauthorized write would be sensible. Advisory prose may lie.
Use the entire visible packet. A definite finding needs agreement of every
compatible world; several labels require ABSTAIN. Do not infer innocence from
missing evidence. Return bare JSON with exactly status and worker_id. Status
EXECUTOR requires A/B/C; NONE or ABSTAIN require null. No Markdown or preamble.'''

def canonical_file(path):return path.read_bytes().replace(b'\r\n',b'\n')
def sha(path):return hashlib.sha256(canonical_file(path)).hexdigest()
def config():return json.loads(CONFIG.read_text(encoding='utf-8'))

def run_folder(stage):return ROOT/('runs/'+config()['study_id']+'-'+stage)

def decode_answer(text):
    """One bare object or exact outer json fence; no repair or duplicate keys."""
    if not isinstance(text,str):raise ValueError('Missing final text')
    stripped=text.strip();encoding='bare_json'
    match=re.fullmatch(r'```json[ \t]*\r?\n([\s\S]*)\r?\n```',stripped)
    if match:stripped=match.group(1).strip();encoding='single_json_fence'
    def pairs(values):
        d={}
        for k,v in values:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    def constant(_):raise ValueError('Non-JSON numeric constant')
    answer=json.loads(stripped,object_pairs_hook=pairs,parse_constant=constant)
    if not isinstance(answer,dict):raise ValueError('Expected exactly one JSON object')
    return answer,encoding

def score_stateful(data,labels):
    """v2 encoding is predeclared; raw strict validity remains separate."""
    result=classify(None,labels);result.update(encoding='invalid',strict_schema_valid=False)
    if not isinstance(data,dict) or data.get('status')!='completed':return result
    try:answer,encoding=decode_answer(data.get('output_text'))
    except (ValueError,TypeError):return result
    scored=classify(dict(status='completed',output_text=json.dumps(answer)),labels)
    scored.update(encoding=encoding,strict_schema_valid=encoding=='bare_json' and scored['status']!='INVALID')
    return scored

def freeze():
    if FREEZE.exists():raise ValueError('Freeze already exists; do not overwrite a registered study')
    if subprocess.run(['git','rev-parse','--verify','--quiet','refs/tags/'+config()['study_id']],cwd=ROOT,capture_output=True).returncode==0:raise ValueError('Registration tag already exists; do not reuse it')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT).strip():raise ValueError('Commit implementation/protocol before freezing')
    artifact=dict(created=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  source_sha256={n:sha(ROOT/n) for n in SOURCES},prompt_sha256=digest(PROMPT),config=config(),
                  status='Prospective freeze; not evidence that inference completed')
    FREEZE.write_text(json.dumps(artifact,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(freeze_sha256=sha(FREEZE),next='Commit this file and tag '+config()['study_id']+' before any fresh inference')

def verify_freeze():
    f=json.loads(FREEZE.read_text(encoding='utf-8'))
    if f['source_sha256']!={n:sha(ROOT/n) for n in SOURCES} or f['prompt_sha256']!=digest(PROMPT) or f['config']!=config():raise ValueError('Frozen source/config mismatch')
    tag=config()['study_id']
    if subprocess.run(['git','merge-base','--is-ancestor',f['base_commit'],tag+'^{}'],cwd=ROOT,capture_output=True).returncode!=0:raise ValueError('Registered implementation commit is not an ancestor of tag')
    tagged=subprocess.check_output(['git','show',tag+':research/'+FREEZE.name],cwd=ROOT)
    if tagged.replace(b'\r\n',b'\n')!=canonical_file(FREEZE):raise ValueError('Freeze tag mismatch')
    for n in SOURCES:
        blob=subprocess.check_output(['git','show',tag+':'+n],cwd=ROOT)
        if hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()!=f['source_sha256'][n]:raise ValueError('Tagged source differs: '+n)
    return f

def episode(seed,family,index):
    """Balanced clean/violation strata, randomly selected within exact label sets.

    Authorization follows a fixed alternating block pattern within each stratum. In the
    joined family an applied write with original approval can still violate a
    branch gate. The design mixture is not deployment prevalence.
    """
    p=make_public(seed,family,bool((index//2)%2))
    violation=index%2==0
    candidates=[w for w in worlds(family) if (simulate(p,w,False)['label']!='NONE')==violation]
    # Authorized sequential episodes cannot be violating: draw their
    # violation stratum with original authorization false, recorded publicly.
    if not candidates:
        p['authorized']=False
        candidates=[w for w in worlds(family) if (simulate(p,w,False)['label']!='NONE')==violation]
    w=random.Random(seed).choice(candidates)
    return dict(episode_id=p['request_id'],seed=seed,family=family,cohort='violation' if violation else 'clean',public=p,world=w)

def tasks_for(e):
    from experiments.stateful_reference import reference_labels
    tasks=[]
    for churn in (False,True):
        for mechanism in ('full','random','targeted'):
            lost=deletion(e['seed']+900000,mechanism)
            variants=[('none',observe(e['public'],e['world'],churn,lost),[])]
            if mechanism=='targeted':
                variants += [(policy,*restore(e['public'],e['world'],churn,lost,policy,e['seed']+800000)) for policy in ('priority','random')]
            for restoration,x,added in variants:
                labels=compatible_labels(x)
                if not labels or labels!=reference_labels(x) or simulate(e['public'],e['world'],churn)['label'] not in labels:raise ValueError('Oracle/reference admission')
                task=dict(episode_id=e['episode_id'],family=e['family'],cohort=e['cohort'],churn=churn,mechanism=mechanism,restoration=restoration,
                          packet=x,packet_sha256=digest(x),compatible_labels=sorted(labels),added_records=added)
                task['task_id']=digest({k:v for k,v in task.items() if k not in ('packet','compatible_labels')})[:24]
                tasks.append(task)
    return tasks

def prepare(stage):
    c=config();episodes=[]
    for family in c['stages'][stage]['families']:
        for j in range(c['stages'][stage]['episodes_per_family']):
            seed=c['stages'][stage]['seed_start']+10000*FAMILIES.index(family)+j
            episodes.append(episode(seed,family,j))
    tasks=[t for e in episodes for t in tasks_for(e)]
    return episodes,tasks

def durable(file,value):
    file.write(json.dumps(value,separators=(',',':'))+'\n');file.flush();os.fsync(file.fileno())

def run(stage,out):
    f=verify_freeze();c=config();out=Path(out).resolve()
    if not out.is_relative_to((ROOT/'runs').resolve()) or out==(ROOT/'runs').resolve():raise ValueError('Raw outputs must be in a new folder under ignored runs/')
    if stage not in ('qualification','main'):raise ValueError('Unknown stage')
    if out!=run_folder(stage).resolve():raise ValueError('Use the fixed versioned stage output directory')
    if out.exists():raise ValueError('Output directory exists; no silent resume/re-run')
    keys=credentials();key=keys.get('ADAPTION_API_KEY')
    if not key:raise ValueError('Adaption key unavailable')
    if stage=='main':
        # Operational gate uses excluded qualification data only. Never select a
        # different endpoint after looking at a main/holdout result.
        gate=run_folder('qualification')/'summary.json'
        g=json.loads(gate.read_text()) if gate.exists() else {}
        expected=sum(c['stages']['qualification']['episodes_per_family']*10*len(c['models']) for _ in c['stages']['qualification']['families'])
        if not g.get('qualification_pass') or g.get('freeze_sha256')!=sha(FREEZE) or g.get('stage')!='qualification' or g.get('attempted_calls')!=expected or g.get('planned_calls')!=expected:raise ValueError('Run/pass fixed qualification for this freeze first')
        reservation=ROOT/('runs/'+c['study_id']+'-reserved.json')
        reservation.parent.mkdir(exist_ok=True)
        with reservation.open('x',encoding='utf-8') as fd:durable(fd,dict(out=str(out),freeze_sha256=sha(FREEZE)))
    out.mkdir(parents=True)
    episodes,tasks=prepare(stage)
    requests=[dict(task=t,model=m) for t in tasks for m in c['models']]
    random.Random(c['request_order_seed']).shuffle(requests)
    for value,name in ((episodes,'episodes.json'),(tasks,'packets.json'),(dict(stage=stage,freeze=f,order=[(r['task']['task_id'],r['model']) for r in requests]),'manifest.json')):
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    snapshot=out/'source';snapshot.mkdir()
    for name in SOURCES:
        raw=canonical_file(ROOT/name)
        if hashlib.sha256(raw).hexdigest()!=f['source_sha256'][name]:raise ValueError('Source changed before dispatch')
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    spent=Decimal(0);halt=False;rows=[];incomplete=0;started=0;limit=Decimal(c['stages'][stage]['nominal_credit_cap'])
    # Small bounded batches permit throughput without dispatching the whole grid
    # before a failed response/usage gate is observed.
    with (out/'attempts.jsonl').open('x',encoding='utf-8') as attempts,(out/'responses.jsonl').open('x',encoding='utf-8') as responses:
      with ThreadPoolExecutor(max_workers=c['concurrency']) as pool:
        for start in range(0,len(requests),c['concurrency']):
            if halt or (out/'STOP').exists():halt=True;break
            batch=requests[start:start+c['concurrency']];reserves=[];payloads=[]
            for r in batch:
                ri,ro=map(Decimal,RATES[r['model']]);reserve=(c['input_byte_cap']*ri+c['max_output_tokens']*ro)/1000000
                payload=json.dumps(r['task']['packet'],sort_keys=True,separators=(',',':'))
                if len((PROMPT+payload).encode())>c['input_byte_cap']:halt=True;break
                reserves.append(reserve);payloads.append(payload)
            if halt:break
            if spent+sum(reserves)>limit:halt=True;break
            futures={}
            for r,reserve,payload in zip(batch,reserves,payloads):
                durable(attempts,dict(task_id=r['task']['task_id'],model=r['model'],reserved_credits=str(reserve),started=datetime.now(timezone.utc).isoformat()))
                started+=1
                body=dict(model=r['model'],instructions=PROMPT,input=payload,temperature=0,max_output_tokens=c['max_output_tokens'],tools=[],tool_choice='none',agentic_memory=False,store=False)
                futures[pool.submit(request_json,ADAPTION+'/responses',key,body,timeout=120)]=(r,reserve)
            for future in as_completed(futures):
                r,reserve=futures[future]
                try:transport,data=future.result()
                except Exception:transport,data={'http_status':None,'error':'unexpected_request_error'},None
                usage=data.get('usage') if isinstance(data,dict) else None
                known=isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('input_tokens','output_tokens'))
                ri,ro=map(Decimal,RATES[r['model']]);charge=(usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve
                spent+=charge
                invalid=not isinstance(data,dict) or data.get('status')!='completed'
                incomplete+=int(invalid)
                row=scrub(dict(**r,transport=transport,response=data,known_usage=known,estimated_credits=str(charge),scored=score_stateful(data,r['task']['compatible_labels'])),keys.values())
                durable(responses,row);rows.append(row)
                if not known or data.get('model')!=r['model'] or usage['input_tokens']>c['input_byte_cap'] or usage['output_tokens']>c['max_output_tokens'] or incomplete>=3 or transport.get('http_status') in (401,402,403,429):halt=True
    summary=dict(stage=stage,planned_calls=len(requests),attempted_calls=started,retained_responses=len(rows),complete=not halt and len(rows)==len(requests),
                 estimated_credits=str(spent),incomplete=incomplete,freeze_sha256=sha(FREEZE),billing='Token-rate estimate; not final account debit')
    summary['qualification_pass']=stage=='qualification' and summary['complete'] and all(r['known_usage'] and r['scored']['status']!='INVALID' for r in rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','verify-freeze','plan','run'])
    p.add_argument('--stage',choices=['qualification','main'],default='qualification');p.add_argument('--out')
    a=p.parse_args()
    if a.command=='freeze':result=freeze()
    elif a.command=='verify-freeze':result=dict(valid=True,base_commit=verify_freeze()['base_commit'])
    elif a.command=='plan':result=dict(mode='offline metadata only; no main episodes generated',configuration=config(),prompt_sha256=digest(PROMPT))
    else:result=run(a.stage,ROOT/a.out if a.out else run_folder(a.stage))
    print(json.dumps(result,indent=2))
