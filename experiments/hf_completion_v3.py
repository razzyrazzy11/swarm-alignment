"""Prospective router-aware continuation of only157 original unstarted HF calls.

Import/verify make no provider calls. Frozen predecessors are never modified.
"""
import argparse
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json,os,ssl,subprocess,time
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request,build_opener
from urllib.error import HTTPError,URLError
from experiments import hf_completion as h, hf_completion_v2 as v2
from experiments import factorial_study as s, factorial_continue as c
from experiments.swarm_ledger_dispatch_v2 import process_dead
from experiments import collection_connectivity as net

ROOT=s.ROOT
TAG='hf-completion-v3'
FREEZE=ROOT/'research/hf-completion-v3-freeze.json'
SOURCES=('experiments/hf_completion_v3.py','experiments/tests/test_hf_completion_v3.py',
 'research/HF_COMPLETION_V3_PROTOCOL.md','experiments/collection_connectivity.py',
 'experiments/tests/test_collection_connectivity.py','research/COLLECTION_CONNECTIVITY_PROTOCOL.md',
 'experiments/swarm_ledger_dispatch_v2.py','experiments/router_resume_analysis.py',
 'experiments/tests/test_router_resume_analysis.py','research/ROUTER_RESUME_ANALYSIS_PROTOCOL.md')
FIXED=dict(study_id=TAG,prior_terminals=1741,remaining=157,total_terminals=1898,
 min_start_interval_seconds=30,transient_backoff_seconds=60,circuit_consecutive_transients=8,
 circuit_pause_seconds=600,new_transient_allowance=256,new_estimated_cost_cap='2.50',
 timeout_seconds=120,retries=0,max_active=1,metadata_recheck_calls=100,
 collection_deadline_utc='2026-11-09T05:59:00+00:00',reset_avoidance_utc='04:55-05:05',
 connectivity_pause_seconds=900,healthy_probe_separation_seconds=15)
expect=h.expect
def folder():return ROOT/('runs/'+TAG)
def now():return datetime.now(timezone.utc).isoformat()

def driver_proof(owned_lock=False):
    from experiments import hf_completion_analysis as a
    names=('runs/factorial-driver-v1/state.json',a.DRIVER,'runs/hf-completion-v2-driver/state.json')
    proof={}
    for i,name in enumerate(names):
        path=ROOT/name;raw=path.read_bytes();state=json.loads(raw)
        expect(state.get('status') in ('stopped','complete'),'Previous collection remains active')
        stamp=datetime.fromisoformat(state['updated'].replace('Z','+00:00'))
        expect(stamp.tzinfo is not None and stamp.utcoffset().total_seconds()==0 and stamp<=datetime.now(timezone.utc),'Actual final UTC state required')
        process_dead(state['pid'],state['updated'])
        if i:process_dead(state['child_pid'],state['updated'])
        expect(path.read_bytes()==raw,'Driver state changed');proof[name]=hashlib.sha256(raw).hexdigest()
    locks=[s.folder('audits')/x for x in ('collector.lock','continuation-pacing.lock','continuation.lock')]
    locks += [h.folder()/'collector.lock',v2.folder()/'collector.lock']
    if owned_lock:locks.remove(s.folder('audits')/'continuation.lock')
    expect(not any(p.exists() for p in locks),'Prior active or stale lock; never remove it')
    return proof

def original_jobs(owned_lock=False):
    """Unchanged frozen request construction, with explicit creation-safe guards."""
    from experiments import hf_completion_analysis as a
    a.verify_registration();c.verify_original_sources();s.verify();driver_proof(owned_lock)
    cfg=h.config();checkpoint=s.read(ROOT/h.CHECKPOINT)
    for relative,value in checkpoint['raw_prefixes'].items():
        stage,name=relative.split('/',1);path=s.folder(stage)/name
        expect(path.stat().st_size==value['bytes'] and h.raw_sha(path)==value['sha256'],'Original raw checkpoint changed')
    jobs,plan=c.shuffled_plan(s.audit_jobs());out=s.folder('audits')
    expect(s.read(out/'plan.json')==plan,'Original plan changed')
    starts,rows,started=c.ledger(out,jobs,plan)
    expect(len(starts)==len(rows)==cfg['historical_audit_terminals'],'Original terminal count changed')
    expect(sum(x['provider']=='hf' for x in rows)==cfg['historical_hf_terminals'],'Original HF count changed')
    expect(sum(x['transport'].get('http_status')==429 for x in rows)==cfg['historical_429_count'],'Original HTTP429 history changed')
    pending=[j for j in jobs if j['id'] not in started];_,published,_=h.snapshot()
    expect(len(pending)==cfg['original_unstarted'],'Original unstarted complement changed')
    expect(all(all(h.descriptor(j)[k]==published[j['id']][k] for k in h.descriptor(j)) for j in pending),'Original body commitment changed')
    return pending

def private_prefix(owned_lock=False):
    """Strict immutable union; no score or answer text is exported."""
    jobs=original_jobs(owned_lock);one=h.verify();two=v2.verify()
    plan1=dict(freeze_sha256=s.sha(h.FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),pending_sha256=s.digest(one['pending']))
    a,b,seen=h.supplement_ledger(h.folder(),jobs,plan1)
    expect(len(a)==len(b)==9,'First completion prefix changed')
    expect({n:h.raw_sha(h.folder()/n) for n in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}==two['prior_raw_sha256'],'First nine bytes changed from V2 registration')
    remaining=[j for j in jobs if j['id'] not in seen]
    expect([h.descriptor(j) for j in remaining]==two['pending'],'V2 registered complement changed')
    plan2=dict(freeze_sha256=s.sha(v2.FREEZE),ids=[j['id'] for j in remaining],planned=len(remaining),pending_sha256=s.digest(two['pending']))
    aa,bb,seen2=v2.supplement_ledger(v2.folder(),remaining,plan2)
    expect(len(aa)==len(bb)==1732,'Stopped V2 terminal prefix changed')
    expect(not seen&seen2,'Predecessor identity overlap')
    summary=s.read(v2.folder()/'summary.json')
    expect(summary['complete'] is False and summary['halted'] is True and summary['stop_reason']=='fatal_transport_profile_or_capture' and summary['unstarted']==157,'V2 stop attestation differs')
    cost1=sum((Decimal(x['estimated_cost']) for x in b),Decimal(0));cost2=sum((Decimal(x['estimated_cost']) for x in bb),Decimal(0))
    expect(Decimal(summary['prior_estimated_cost'])==cost1 and Decimal(summary['new_estimated_cost'])==cost2 and Decimal(summary['combined_estimated_cost'])==cost1+cost2,'Prior summary costs differ')
    expect(sum(x['transport'].get('http_status') is None for x in bb)==1,'Original uncertain terminal count changed')
    transients=two['prior_transients']+sum(h.transient(x) for x in bb)
    expect(transients==summary['new_transient_errors']==75,'Prior transient accounting differs')
    paths=[]
    for out in (h.folder(),v2.folder()):
        paths += [out/x for x in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')]
        paths += sorted((out/'private-errors').glob('*.json'))
    proof={p.relative_to(ROOT).as_posix():h.raw_sha(p) for p in paths}
    proof.update(driver_proof(owned_lock))
    pending=[j for j in remaining if j['id'] not in seen2]
    expect(len(pending)==157,'Exact new complement differs')
    return pending,b+bb,proof,transients

def freeze():
    expect(not FREEZE.exists(),'Continuation registration exists')
    jobs,prior,proof,transients=private_prefix()
    for name in SOURCES:
        expect(h.blob(name,'HEAD').replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit sources before registration')
    value=dict(schema_version=1,tag=TAG,config=FIXED,created=now(),
      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      source_sha256={n:s.sha(ROOT/n) for n in SOURCES},parent_registration_sha256={p.name:s.sha(p) for p in (h.FREEZE,v2.FREEZE)},
      prior_raw_sha256=proof,prior_ids=[x['id'] for x in prior],prior_transients=transients,
      prior_estimated_cost=str(sum((Decimal(x['estimated_cost']) for x in prior),Decimal(0))),
      pending=[h.descriptor(j) for j in jobs],timing='After router outage and metadata-only integrity replay; all prior failures retained; no unstarted answer inspection or replacement')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    return dict(created=True,tag=TAG,remaining=157,inference_calls=0)

def verify():
    h.verify();v2.verify();value=s.read(FREEZE)
    expect(set(value)=={'schema_version','tag','config','created','base_commit','source_sha256','parent_registration_sha256','prior_raw_sha256','prior_ids','prior_transients','prior_estimated_cost','pending','timing'},'V3 registration schema')
    expect(value['schema_version']==1 and value['tag']==TAG and value['config']==FIXED,'V3 identity/configuration differs')
    expect(value['source_sha256']=={n:s.sha(ROOT/n) for n in SOURCES},'V3 source changed')
    expect(value['parent_registration_sha256']=={p.name:s.sha(p) for p in (h.FREEZE,v2.FREEZE)},'V3 parent registration changed')
    for n in (*SOURCES,FREEZE.relative_to(ROOT).as_posix()):
        expect(h.blob(n,TAG).replace(b'\r\n',b'\n')==(ROOT/n).read_bytes().replace(b'\r\n',b'\n'),'V3 tag differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'V3 ancestry')
    old={x['id']:x for x in h.verify()['pending']};prior=set(value['prior_ids']);pending={x['id'] for x in value['pending']}
    expect(len(value['prior_ids'])==len(prior)==1741 and len(value['pending'])==len(pending)==157 and not prior&pending and prior|pending==set(old),'V3 exact disjoint complement differs')
    expect(all(x==old[x['id']] for x in value['pending']),'V3 body or endpoint commitment changed')
    expect(value['prior_transients']==75 and Decimal(value['prior_estimated_cost']).is_finite() and Decimal(value['prior_estimated_cost'])>=0,'V3 prior accounting differs')
    return value

def plan_for(jobs,registration):
    return dict(freeze_sha256=s.sha(FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),pending_sha256=s.digest(registration['pending']))

def supplement_ledger(out,jobs,plan):
    return v2.supplement_ledger(out,jobs,plan)

def connectivity_failure(row):
    return row['transport'].get('connection_fault') is True and not row.get('capture_failed') and not row['known_usage'] and row.get('native_response') is None

def fatal(row):return False if connectivity_failure(row) else h.fatal(row)

class SafeTransport:
    def __init__(self,out,secrets,clock=time.monotonic,opener=None):
        self.out=Path(out);self.secrets=secrets;self.clock=clock
        self.backend=opener or build_opener(h.SameOriginRedirect())
        self.opener=SimpleNamespace(last_open_started=None,service_overload=False,capture_failed=False,retry_after_delay=0.,last_receipt=None)
        self.ordinal=len(list((self.out/'private-errors').glob('error-*.json')))
    def __call__(self,url,key,body,timeout=120):
        expect(url==s.HF+'/chat/completions','HF-only continuation transport')
        request=Request(url,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'swarm-alignment-pilot/0.1'},method='POST')
        state=self.opener;state.last_open_started=self.clock();state.service_overload=False;state.capture_failed=False;state.retry_after_delay=0.;state.last_receipt=None
        public,native,private=net.safe_request(self.backend,request,timeout=timeout,max_bytes=2097152)
        state.capture_failed=bool(public.get('capture_failed'))
        if public.get('error')=='HTTPError':
            state.retry_after_delay=c.retry_after(private.get('headers',{}).get('Retry-After')) or 0.
            state.service_overload=v2.explicit_overload(public['http_status'],private.get('error_body',''))
            try:
                directory=self.out/'private-errors';directory.mkdir(exist_ok=True)
                path=directory/f'error-{self.ordinal:06d}.json';self.ordinal+=1
                record=s.scrub(dict(http_status=public['http_status'],error_body=private.get('error_body',''),byte_cap=16384),self.secrets)
                with path.open('x',encoding='utf-8') as stream:stream.write(json.dumps(record)+'\n');stream.flush();os.fsync(stream.fileno())
                state.last_receipt=dict(file='private-errors/'+path.name,sha256=h.raw_sha(path))
            except Exception:state.capture_failed=True
        return public,native

def append(path,value):
    with Path(path).open('a',encoding='utf-8',newline='\n') as stream:s.durable(stream,value)

def probe_catalog(secret):
    request=Request(s.HF+'/models',headers={'Authorization':'Bearer '+secret['HF_TOKEN']},method='GET')
    try:
        with build_opener(h.SameOriginRedirect()).open(request,timeout=30) as reply:
            expect(reply.status==200,'HF catalog status drift');raw=reply.read(2097153)
            expect(len(raw)<=2097152,'HF catalog body cap exceeded');data=json.loads(raw)
        expect(h.catalog_record(data)==s.read(h.CATALOG)['route'],'HF route/model/price drift')
        return True
    except HTTPError:raise ValueError('Authenticated HF catalog access failed') from None
    except ssl.SSLError:raise ValueError('HF catalog TLS validation failed') from None
    except URLError as error:
        if isinstance(error.reason,ssl.SSLError):raise ValueError('HF catalog TLS validation failed') from None
        return False
    except (OSError,TimeoutError):return False

def execute(resume=False,transport=None,clock=None,sleep=None,gate=None):
    registration=verify();clock=clock or time.monotonic;sleep=sleep or time.sleep
    jobs,prior,proof,transients=private_prefix()
    expect(proof==registration['prior_raw_sha256'] and [h.descriptor(j) for j in jobs]==registration['pending'],'Stopped prefix or complement changed')
    out=folder();plan=plan_for(jobs,registration)
    if out.exists() and not resume:raise ValueError('V3 already exists; no automatic repeat')
    if not out.exists():out.mkdir(parents=True);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')
    with h.exclusive(out):
        expect(driver_proof(True)=={k:v for k,v in proof.items() if k.endswith('state.json')},'Prior driver state changed')
        starts,rows,started=supplement_ledger(out,jobs,plan)
        expect(not any(fatal(x) for x in rows),'V3 prior fatal terminal; new amendment required')
        if (out/'summary.json').exists():
            old=s.read(out/'summary.json');expect(not old['halted'] or old['stop_reason']=='operator_stop','V3 stopped; new amendment required')
        prior_cost=Decimal(registration['prior_estimated_cost']);spent=sum((Decimal(x['estimated_cost']) for x in rows),Decimal(0))
        transient_count=transients+sum(h.transient(x) for x in rows)
        expect(transient_count<256 and prior_cost+spent<=Decimal('2.50'),'V3 aggregate limits exhausted')
        pending=[j for j in jobs if j['id'] not in started];secret=h.keys()
        gate=gate or net.ConnectivityGate(lambda:probe_catalog(secret),deadline=FIXED['collection_deadline_utc'],pause_seconds=900)
        transport=transport or SafeTransport(out,list(secret.values()),clock)
        stop=out/'STOP';next_start=clock()+30;streak=0;since_metadata=0;halted=False;reason=''
        if rows:
            elapsed=max(0,time.time()-datetime.fromisoformat(rows[-1]['finished']).timestamp())
            next_start=max(next_start,clock()+max(0,rows[-1]['next_delay_seconds']-elapsed))
            if connectivity_failure(rows[-1]):gate.connection_failed()
        for row in reversed(rows):
            if not h.transient(row):break
            streak+=1
        streak%=8
        while pending and not halted:
            try:
                c.wait_until(next_start,stop,clock,sleep)
                gate.before_dispatch(force_health=since_metadata>=100)
                if since_metadata>=100:since_metadata=0
            except c.Stopped:halted=True;reason='operator_stop';break
            except Exception:halted=True;reason='connectivity_or_catalog_preflight';break
            job=pending[0];reserve=h.reservation(job)
            if prior_cost+spent+reserve>Decimal('2.50'):halted=True;reason='budget';break
            if stop.exists():halted=True;reason='operator_stop';break
            provider,body=s.body_for(job)
            append(out/'attempts.jsonl',dict(id=job['id'],request_sha256=s.digest(body),provider=provider,reserved_cost=str(reserve),started=now()))
            try:public,native=transport(s.HF+'/chat/completions',secret['HF_TOKEN'],body,timeout=120)
            except Exception:public,native=dict(http_status=None,error='unexpected_request_error'),None
            normal,known=s.safe_response(native,job['model']);ri,ro=s.rates(job['model']);usage=normal.get('usage')
            cost=(usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve;spent+=cost
            op=getattr(transport,'opener',None)
            row=dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,transport=public,response=normal,
              known_usage=known,estimated_cost=str(cost),native_response=native,service_overload=bool(getattr(op,'service_overload',False)),
              capture_failed=bool(getattr(op,'capture_failed',False)),error_receipt=getattr(op,'last_receipt',None),finished=now())
            opened=c.numeric(getattr(op,'last_open_started',None));base=clock() if opened is None else opened;wait_after=0.
            if h.transient(row):
                transient_count+=1;streak+=1;wait_after=max(60,c.numeric(getattr(op,'retry_after_delay',0)) or 0)
                if streak>=8:wait_after=max(wait_after,600);streak=0
            else:streak=0
            if connectivity_failure(row):gate.connection_failed();wait_after=max(wait_after,60)
            if wait_after>900:halted=True;reason='retry_after_exceeds_bound'
            next_start=max(base+30,clock()+wait_after);row['next_delay_seconds']=max(0,next_start-clock())
            row=s.scrub(row,secret.values());append(out/'responses.jsonl',row);rows.append(row);pending.pop(0);since_metadata+=1
            if fatal(row):halted=True;reason='fatal_transport_profile_or_capture'
            elif transient_count>=256:halted=True;reason='transient_allowance'
            elif prior_cost+spent>Decimal('2.50'):halted=True;reason='provider_cost_overrun'
        summary=dict(planned=len(jobs),returned=len(rows),unstarted=len(pending),complete=len(rows)==len(jobs),halted=halted,
          stop_reason=reason,new_transient_errors=transient_count,prior_terminals=len(prior),prior_estimated_cost=str(prior_cost),
          new_estimated_cost=str(spent),combined_estimated_cost=str(prior_cost+spent),freeze_sha256=s.sha(FREEZE))
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        return summary

def private_completed(owned_lock=False):
    """Three-journal union for a separately registered unchanged-analysis release."""
    registration=verify();jobs,prior,proof,transients=private_prefix(owned_lock)
    expect(proof==registration['prior_raw_sha256'],'Prior bytes changed')
    starts,new,seen=supplement_ledger(folder(),jobs,plan_for(jobs,registration))
    expect(len(starts)==len(new)==157,'V3 not terminal-complete')
    summary=s.read(folder()/'summary.json');cost=sum((Decimal(x['estimated_cost']) for x in new),Decimal(0))
    expect(set(summary)=={'planned','returned','unstarted','complete','halted','stop_reason','new_transient_errors','prior_terminals','prior_estimated_cost','new_estimated_cost','combined_estimated_cost','freeze_sha256'},'V3 final summary schema')
    expect(summary['complete'] is True and summary['planned']==summary['returned']==157 and summary['unstarted']==0 and summary['freeze_sha256']==s.sha(FREEZE),'V3 final summary incomplete')
    expect(summary['prior_terminals']==1741 and Decimal(summary['prior_estimated_cost'])==Decimal(registration['prior_estimated_cost']),'V3 prior summary differs')
    expect(Decimal(summary['new_estimated_cost'])==cost and Decimal(summary['combined_estimated_cost'])==Decimal(registration['prior_estimated_cost'])+cost,'V3 final cost summary differs')
    combined=prior+new;expect(len(combined)==len({x['id'] for x in combined})==1898,'Full supplement union differs')
    totaltransients=transients+sum(h.transient(x) for x in new)
    expect(summary['new_transient_errors']==totaltransients,'V3 final transient summary differs')
    merged=dict(planned=1898,returned=1898,unstarted=0,complete=True,halted=summary['halted'],stop_reason=summary['stop_reason'],
      new_transient_errors=totaltransients,historical_429_preserved=5,new_estimated_cost=str(sum((Decimal(x['estimated_cost']) for x in combined),Decimal(0))),
      historical_hf_cost='0.880229785',freeze_sha256=s.sha(h.FREEZE),cost_basis='token-rate estimate or full unknown reservation, not reconciled invoice',
      original_audit_returned=11640,original_hf_returned=3880)
    commitments={'hf-completion-v1':{n:h.raw_sha(h.folder()/n) for n in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')},
      'hf-completion-v2':{n:h.raw_sha(v2.folder()/n) for n in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')},
      'hf-completion-v3':{n:h.raw_sha(folder()/n) for n in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}}
    return combined,{x['id']:x['request_sha256'] for x in h.verify()['pending']},merged,commitments

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','verify','run'));p.add_argument('--continue-unstarted',action='store_true');args=p.parse_args()
    result=execute(args.continue_unstarted) if args.command=='run' else freeze() if args.command=='freeze' else dict(valid=bool(verify()),inference_calls=0)
    print(json.dumps(result,indent=2))
