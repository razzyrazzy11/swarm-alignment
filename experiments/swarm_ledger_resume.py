"""Prospective router-aware MAIN continuation; original archives stay immutable.

No provider calls, credentials or empirical outcomes are accessed on import.
Only exact unstarted identities may be collected in the separate new journals.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, json, subprocess, threading, time
from pathlib import Path
from urllib.request import Request

from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_complete_dispatch as d
from experiments import collection_connectivity as connectivity

ROOT = s.ROOT
TAG = 'swarm-ledger-resume-v1'
FREEZE = ROOT/'research/swarm-ledger-resume-v1-freeze.json'
FORECAST = ROOT/'research/router-resume-forecast.json'
SOURCES = ('experiments/swarm_ledger_resume.py','experiments/tests/test_swarm_ledger_resume.py',
 'research/SWARM_LEDGER_RESUME_PROTOCOL.md','experiments/collection_connectivity.py',
 'experiments/tests/test_collection_connectivity.py','research/COLLECTION_CONNECTIVITY_PROTOCOL.md',
 'experiments/router_resume_analysis.py','experiments/tests/test_router_resume_analysis.py',
 'research/ROUTER_RESUME_ANALYSIS_PROTOCOL.md','experiments/router_resume_forecast.py',
 'experiments/tests/test_router_resume_forecast.py')
PHASES = ('reporter','readers','calibration','influence')
ROLES = ('principal','coordinator','x','y','reporter')
expect=s.expect; canonical=s.canonical; digest=s.digest; read=s.read; rows=s.rows
policy = dict(reset_window_utc=['04:55','05:05'], healthy_checks=2, healthy_interval_seconds=15,
              max_connectivity_wait_seconds=900, max_new_connection_failures=32,
              cutoff_utc='2026-11-09T05:59:00+00:00', retries=0)


def folder(phase=None):
    out=ROOT/'runs/swarm-ledger-resume-v1-main'
    return out/phase if phase else out


def original_folder(phase):return ROOT/('runs/'+s.config()['study_id']+'-main')/phase
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_prefix():
    """Commit original bytes, including native receipts, without exposing their text."""
    main=ROOT/('runs/'+s.config()['study_id']+'-main')
    paths=sorted(p for p in main.rglob('*') if p.is_file())
    expect(not any(p.is_symlink() for p in paths),'Original symlink refused')
    expect(not any(p.name=='collector.lock' for p in paths),'Original collector lock remains')
    native=[];metadata={}
    for p in paths:
        name=p.relative_to(ROOT).as_posix();item=(name,raw_sha(p))
        if 'native' in p.parts:native.append(item)
        else:metadata[name]=item[1]
    state=ROOT/'runs/swarm-ledger-v1-main-driver/state.json'
    metadata[state.relative_to(ROOT).as_posix()]=raw_sha(state)
    return dict(metadata_sha256=metadata,native_files=len(native),native_inventory_sha256=digest(native))


def stopped_prefix_gate():
    state=read(ROOT/'runs/swarm-ledger-v1-main-driver/state.json')
    expect(state.get('status')=='stopped' and state.get('stage')=='reporter','Expected actual stopped reporter driver')
    d.process_dead(state['pid'],state['updated']);d.process_dead(state['child_pid'],state['updated'])
    expect(not list((ROOT/('runs/'+s.config()['study_id']+'-main')).rglob('collector.lock')),'Original phase lock remains')
    return True


def _phase_ledger(out,jobs,registration_path):
    ordered=sorted(jobs,key=lambda j:j['id'])
    expect(len({j['id'] for j in ordered})==len(ordered),'Duplicate planned identity')
    plan=read(out/'plan.json')
    expect(plan==dict(jobs_sha256=digest(ordered),ids=[j['id'] for j in ordered],
                     freeze_sha256=s.sha(registration_path)),'Phase plan/body/registration drift')
    starts,terminal=s.ledger(out,ordered)
    for row in terminal:expect(s.apply_host_action(row)==row,'Bounded host-action replay differs')
    return starts,terminal


def union_phase(phase,jobs,require_complete=True):
    """Literal frozen ledgers, strict disjoint union, unchanged host/cost decoding."""
    expect(phase in d.PHASES,'Unknown phase')
    started=[];terminal=[];seen=set()
    for out,registration_path in ((original_folder(phase),s.freeze_path('main')),(folder(phase),FREEZE)):
        if not (out/'plan.json').exists():
            expect(not rows(out/'attempts.jsonl') and not rows(out/'responses.jsonl'),'Unplanned journal')
            continue
        attempts,results=_phase_ledger(out,jobs,registration_path)
        identities={a['id'] for a in attempts}
        expect(not seen&identities,'Repeated original/continuation request identity')
        seen|=identities;started.extend(attempts);terminal.extend(results)
    expect(len(seen)==len(started)==len(terminal),'Union unresolved or duplicate request')
    expect(seen<={j['id'] for j in jobs},'Unregistered union identity')
    complete=len(terminal)==len(jobs)
    if require_complete:expect(complete,'Registered union condition incomplete')
    return terminal,dict(planned=len(jobs),started=len(started),terminal=len(terminal),
        unstarted=len(jobs)-len(started),unknown_usage=sum(not r['known_usage'] for r in terminal),complete=complete)


def main_jobs(phase):
    """Rebuild original bodies from authentic prefix + continuation actor rows."""
    expect(phase in d.PHASES,'Unknown phase')
    contexts=s.contexts('main')
    expect(digest(contexts)==read(s.freeze_path('main'))['contexts_sha256'],'Original contexts changed')
    previous={}
    for role in ROLES:
        if role==phase:break
        jobs=s.actor_jobs(role,contexts,previous)
        admitted,_=union_phase(role,jobs,True)
        previous.update({row['id']:row for row in admitted})
    if phase=='readers':return s.reader_jobs(s.source_worlds(contexts,previous))
    if phase=='calibration':return s.reader_jobs(s.calibration_sources())
    if phase=='influence':return s.influence_jobs(contexts,previous)
    return s.actor_jobs(phase,contexts,previous)


def pending_jobs(phase,jobs):
    terminal,_=union_phase(phase,jobs,False)
    started={r['id'] for r in terminal}
    return [j for j in sorted(jobs,key=lambda j:j['id']) if j['id'] not in started]


def parent_anchors():
    names=(s.freeze_path('main'),d.op_freeze('main'))
    return {p.relative_to(ROOT).as_posix():s.sha(p) for p in names}


def validate_resume_forecast(value,at=None):
    at=datetime.now(timezone.utc) if at is None else at
    expect(type(value.get('schema_version')) is int and value['schema_version']==1,'Remaining forecast schema')
    expect(all(value.get(k) is True for k in ('deadline_feasible','budget_feasible','off_peak_wallet_gate_passed')),'Remaining workload forecast gate failed')
    cutoff=value.get('collection_cutoff_utc',value.get('cutoff_utc'))
    expect(cutoff==policy['cutoff_utc'],'Remaining forecast cutoff changed')
    duration=Decimal(str(value.get('forecast_seconds')))
    expect(duration.is_finite() and duration>0,'Invalid remaining forecast duration')
    expect(at.timestamp()+float(duration)<datetime.fromisoformat(cutoff).timestamp(),'Remaining workload no longer fits cutoff')
    return value


def freeze():
    expect(not FREEZE.exists(),'Continuation registration already exists')
    expect(not any(folder().rglob('attempts.jsonl')),'Continuation attempts already exist')
    s.registration('main');d.verify('main');stopped_prefix_gate()
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit continuation sources before registration')
    expect(FORECAST.is_file(),'Prospective remaining-workload forecast required');validate_resume_forecast(read(FORECAST))
    jobs=main_jobs('reporter');pending=pending_jobs('reporter',jobs)
    expect(len(jobs)==2560 and len(pending)==808,'Stopped reporter complement differs')
    value=dict(schema_version=1,tag=TAG,created=s.now(),policy=policy,
      source_sha256={name:s.sha(ROOT/name) for name in SOURCES},parent_registration_sha256=parent_anchors(),
      original_prefix=snapshot_prefix(),forecast_sha256=s.sha(FORECAST),
      reporter_unstarted_descriptor_sha256=digest(pending),reporter_unstarted=808,
      remaining_calls=dict(reporter=808,readers=53760,calibration=240,influence=240,total=55048),
      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      timing='Operational continuation after router reset; before resumed inference; scientific design/endpoints/scoring unchanged')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')
    return dict(created=True,tag=TAG,inference_calls=0)


def verify(check_prefix=True):
    value=read(FREEZE)
    expect(value['schema_version']==1 and value['tag']==TAG and value['policy']==policy,'Continuation registration/policy differs')
    expect(value['source_sha256']=={name:s.sha(ROOT/name) for name in SOURCES},'Continuation source drift')
    expect(value['parent_registration_sha256']==parent_anchors(),'Original registrations changed')
    expect(value['forecast_sha256']==s.sha(FORECAST),'Remaining forecast changed')
    if check_prefix:expect(value['original_prefix']==snapshot_prefix(),'Original stopped archive changed')
    for name in (*SOURCES,FREEZE.relative_to(ROOT).as_posix(),FORECAST.relative_to(ROOT).as_posix()):
        blob=subprocess.check_output(['git','show',TAG+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Continuation tag differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Continuation ancestry differs')
    return value


verify_registration=verify


class ResumeTransport(s.Transport):
    """Original body/normalizer with new safe transport diagnostics, one POST only."""
    def __init__(self,keys,out,opener=None):
        super().__init__(keys,out,opener);self.dispatch_lock=threading.Lock()
    def request(self,j):
        p=s.profile(j['profile_id']);keyname={'adaption':'ADAPTION_API_KEY','hf':'HF_TOKEN','ollama':'OLLAMA_API_KEY'}[p['provider']]
        expect(bool(self.keys.get(keyname)),'Missing provider credential')
        if p['provider']=='adaption':
            with self.dispatch_lock:
                checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/native-dispatch-private.json')
                if checkpoint.exists():
                    delay=max(0,read(checkpoint)['epoch']+1-time.time())
                    expect(delay<=61,'Native pacing clock drift')
                    if delay:time.sleep(delay)
                checkpoint.parent.mkdir(parents=True,exist_ok=True)
                s.atomic_metadata(checkpoint,dict(epoch=time.time()))
        req=Request(p['endpoint'],data=canonical(s.body_for(j)).encode(),method='POST',
                    headers={'Authorization':'Bearer '+self.keys[keyname],'Content-Type':'application/json'})
        status,native,private=connectivity.safe_request(self.opener,req,timeout=s.config()['request_timeout_seconds'])
        if status.get('http_status') in (429,502,503,504):status['service_overload']=s.service_overload(status['http_status'],private.get('error_body',''))
        receipt=self.out/'native';receipt.mkdir(parents=True,exist_ok=True)
        path=receipt/(digest(j['id'])+'.json')
        with path.open('x',encoding='utf-8') as stream:
            json.dump(s.old.scrub(private,self.keys.values()),stream);stream.flush()
            import os;os.fsync(stream.fileno())
        response,known,anomaly=s.normalize(native,p)
        return s.old.scrub(dict(id=j['id'],profile_id=j['profile_id'],metadata=j['metadata'],transport=status,
            response=response,known_usage=known,anomaly=anomaly,native_receipt_sha256=raw_sha(path)),self.keys.values())


def connectivity_probe(transport):
    for url,key in (('https://api.prod.adaptionlabs.ai/api/v1/models?type=hosted','ADAPTION_API_KEY'),
                    ('https://router.huggingface.co/v1/models','HF_TOKEN'),
                    ('https://ollama.com/api/tags','OLLAMA_API_KEY')):
        expect(bool(transport.keys.get(key)),'Missing metadata credential')
        request=Request(url,headers={'Authorization':'Bearer '+transport.keys[key]},method='GET')
        status,native,_=connectivity.safe_request(transport.opener,request,timeout=30)
        if status.get('connection_fault') is True:return False
        expect(status.get('http_status')==200 and isinstance(native,dict),'Metadata authentication/profile/JSON check failed')
    return True


def cost_baseline():
    """Every old failed/unknown terminal and excluded pilot remains charged."""
    combined={p:Decimal(0) for p in ('adaption','hf','ollama')};main=dict(combined);classes={'actors':Decimal(0),'readers':Decimal(0)}
    paths=set()
    for split in ('technical','development','main'):
        paths.update((ROOT/('runs/'+s.config()['study_id']+'-'+split)).glob('*/responses.jsonl'))
    paths.update(folder().glob('*/responses.jsonl'));paths.update(d.pilot_spending_paths())
    for path in paths:
        is_main=path.parent.parent==folder() or path.parent.parent.name==s.config()['study_id']+'-main'
        for row in rows(path):
            provider=s.profile(row['profile_id'])['provider'];amount=Decimal(row['estimated_cost']);combined[provider]+=amount
            if is_main:
                main[provider]+=amount
                if provider=='adaption':classes['readers' if row['metadata'].get('procedure') else 'actors']+=amount
    return combined,main,classes


def _execute(phase,jobs,transport=None,gate=None):
    """Disjoint continuation only; no mutation of original stopped phase."""
    c=d.execution_config('main',phase);out=folder(phase);ordered=sorted(jobs,key=lambda j:j['id'])
    with s.exclusive(out):
        plan=dict(jobs_sha256=digest(ordered),ids=[j['id'] for j in ordered],freeze_sha256=s.sha(FREEZE))
        if (out/'plan.json').exists():expect(read(out/'plan.json')==plan,'Continuation phase plan drift')
        else:
            with (out/'plan.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream)
        expect(not (out/'stop.json').exists(),'Continuation stopped; new amendment required')
        pending=pending_jobs(phase,ordered)
        transport=transport or ResumeTransport(s.credentials(),out)
        gate=gate or connectivity.ConnectivityGate(lambda:connectivity_probe(transport),deadline=policy['cutoff_utc'])
        gate.before_dispatch(force_health=True);s.check_metadata(transport)
        combined,spent,classes=cost_baseline();balance=d.BalanceGuard(transport,'main')
        historical,_=union_phase(phase,ordered,False)
        failures=sum(d.known_capacity_error(row) for row in historical)
        new_connections=sum(bool(row['transport'].get('connection_fault')) for path in folder().glob('*/responses.jsonl') for row in rows(path))
        expect(failures<=c['gateway_allowance'] and new_connections<=policy['max_new_connection_failures'],'Retained failure allowance exhausted')
        reserved={p:Decimal(0) for p in combined};active={};per_model={};cooldown=0.;since_check=0
        def stop(reason):
            path=out/'stop.json'
            if not path.exists():s.atomic_metadata(path,dict(reason=reason,stopped=s.now(),freeze_sha256=s.sha(FREEZE)))
        def record(future,j):
            row=s.apply_host_action(future.result());amount=s.actual_cost(j,row['response']) if row['known_usage'] else s.reservation(j)
            row['estimated_cost']=str(amount);s.durable(out/'responses.jsonl',row)
            provider=s.profile(j['profile_id'])['provider'];combined[provider]+=amount;spent[provider]+=amount
            if provider=='adaption':classes['readers' if j['metadata'].get('procedure') else 'actors']+=amount
            return row
        def drain():
            for future,j in list(active.items()):
                try:record(future,j)
                except Exception as error:s.durable(out/'capture-failures.jsonl',dict(id=j['id'],error_class=type(error).__name__))
            active.clear()
        with ThreadPoolExecutor(max_workers=8) as pool:
            try:
                while pending or active:
                    if (out/'STOP').exists():pending=[]
                    if not gate.dispatch_allowed() and not active:gate.before_dispatch()
                    for j in list(pending):
                        if len(active)>=8 or time.monotonic()<cooldown or since_check>=c['metadata_recheck_calls'] or not gate.dispatch_allowed():break
                        p=s.profile(j['profile_id']);provider=p['provider'];key=(provider,p['model'])
                        if sum(s.profile(v['profile_id'])['provider']==provider for v in active.values())>=c['provider_max_active'][provider] or per_model.get(key,0)>=c['dispatch_model_limits'][provider]:continue
                        d.dispatch_time_gate('main');amount=s.reservation(j)
                        expect(spent[provider]+reserved[provider]+amount<=Decimal(c['phase_caps']['main'][provider]),'Provider MAIN cost cap')
                        expect(combined[provider]+reserved[provider]+amount<=Decimal(c['combined_caps'][provider]),'Combined cost cap')
                        if provider=='adaption':expect(classes['readers' if j['metadata'].get('procedure') else 'actors']+reserved[provider]+amount<=Decimal(c['native_class_caps']['readers' if j['metadata'].get('procedure') else 'actors']),'Native class cap')
                        if provider=='ollama':balance.check(combined[provider],reserved[provider]+amount)
                        s.durable(out/'attempts.jsonl',dict(id=j['id'],profile_id=j['profile_id'],request_sha256=digest(s.body_for(j)),reserved_cost=str(amount),started=s.now()))
                        reserved[provider]+=amount;per_model[key]=per_model.get(key,0)+1
                        active[pool.submit(transport.request,j)]=j;pending.remove(j)
                    if not active:
                        if since_check>=c['metadata_recheck_calls']:
                            gate.before_dispatch(force_health=True);s.check_metadata(transport);since_check=0
                        elif pending:time.sleep(min(1,max(.01,cooldown-time.monotonic())))
                        continue
                    completed,_=wait(active,return_when=FIRST_COMPLETED);fatal=False
                    for future in completed:
                        j=active.pop(future);p=s.profile(j['profile_id']);provider=p['provider'];key=(provider,p['model'])
                        reserved[provider]-=s.reservation(j);per_model[key]-=1
                        try:row=record(future,j)
                        except Exception as error:
                            s.durable(out/'capture-failures.jsonl',dict(id=j['id'],error_class=type(error).__name__));fatal=True;continue
                        since_check+=1;transient=d.known_capacity_error(row);connection=row['transport'].get('connection_fault') is True
                        if connection:
                            new_connections+=1;gate.connection_failed()
                            if new_connections>policy['max_new_connection_failures']:fatal=True
                        if transient:
                            failures+=1;delay=max(d.gateway_backoff_seconds(row),d.retry_after_delay(row,out))
                            cooldown=max(cooldown,time.monotonic()+delay);d.persist_cooldown(time.time()+delay)
                        http=row['transport'].get('http_status')
                        if row['transport'].get('capture_failed') or (not row['known_usage'] and not transient and not connection) or row['anomaly'] and row['known_usage'] or failures>c['gateway_allowance'] or http in (401,402,403) or (http==429 and not transient):fatal=True
                    if fatal:
                        drain();stop('provider_capture_budget_or_outage_guard');raise ValueError('Continuation stopped; preserve all records')
                    if since_check>=c['metadata_recheck_calls'] and not active:
                        gate.before_dispatch(force_health=True);s.check_metadata(transport);since_check=0
            except BaseException:
                drain();stop('continuation_guard');raise
        terminal,coverage=union_phase(phase,ordered,False)
        return coverage


def run(phase,transport=None,gate=None):
    expect(phase in PHASES,'Only previously unstarted MAIN work may run')
    verify();stopped_prefix_gate();d.verify_pilot_history()
    for attempted in folder().glob('*/attempts.jsonl'):
        out=attempted.parent;started=rows(attempted);terminal=rows(out/'responses.jsonl')
        expect(len({x['id'] for x in started})==len(started) and {x['id'] for x in started}=={x['id'] for x in terminal},'Other continuation phase unresolved or duplicate')
        expect(not (out/'stop.json').exists(),'A stopped continuation phase blocks later phases')
    for previous in PHASES[:PHASES.index(phase)]:union_phase(previous,main_jobs(previous),True)
    jobs=main_jobs(phase)
    with s.exclusive(ROOT/'runs/swarm-ledger-resume-v1-guard'),s.verified_config():
        d.capacity_cooldown();return _execute(phase,jobs,transport,gate)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('freeze','verify','run'));parser.add_argument('--phase',choices=PHASES)
    args=parser.parse_args();result=freeze() if args.command=='freeze' else {'valid':bool(verify())} if args.command=='verify' else run(args.phase)
    print(json.dumps(result))


if __name__=='__main__':main()
