"""Prospective provider-availability continuation; all three stopped archives stay immutable.

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
from experiments import swarm_ledger_resume as prior
from experiments import swarm_ledger_resume_v2 as second

ROOT = s.ROOT
TAG = 'swarm-ledger-resume-v3'
FREEZE = ROOT/'research/swarm-ledger-resume-v3-freeze.json'
FORECAST = ROOT/'research/provider-resume-forecast.json'
SOURCES = ('experiments/swarm_ledger_resume_v3.py','experiments/tests/test_swarm_ledger_resume_v3.py',
 'research/SWARM_LEDGER_RESUME_V3_PROTOCOL.md','experiments/provider_resume_analysis.py',
 'experiments/tests/test_provider_resume_analysis.py','research/PROVIDER_RESUME_ANALYSIS_PROTOCOL.md',
 'experiments/provider_resume_forecast.py','experiments/tests/test_provider_resume_forecast.py',
 'experiments/provider_resume_supervisor.py','experiments/tests/test_provider_resume_supervisor.py',
 'research/PROVIDER_RESUME_OPERATIONS.md')
PHASES = ('readers','calibration','influence')
ROLES = ('principal','coordinator','x','y','reporter')
expect=s.expect; canonical=s.canonical; digest=s.digest; read=s.read; rows=s.rows
policy = dict(reset_window_utc=['04:55','05:05'], healthy_checks=2, healthy_interval_seconds=15,
              max_connectivity_wait_seconds=900, max_new_connection_failures=32,
              cutoff_utc='2026-11-09T05:59:00+00:00', retries=0,
              max_server500_failures=32, server500_cooldown_seconds=60,
              max_consecutive_provider_failures=8, availability_backoff_seconds=[60,120,240,480],
              availability_wait_bound_seconds=900)


def folder(phase=None):
    out=ROOT/'runs/swarm-ledger-resume-v3-main'
    return out/phase if phase else out


def original_folder(phase):return ROOT/('runs/'+s.config()['study_id']+'-main')/phase
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prior_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-resume-v1-main'
    return base/phase if phase else base


def second_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-resume-v2-main'
    return base/phase if phase else base


def snapshot_prefix():
    """Commit both stopped archives without printing any private receipt text."""
    metadata={};native=[]
    for main in (ROOT/('runs/'+s.config()['study_id']+'-main'),prior_folder(),second_folder()):
        paths=sorted(p for p in main.rglob('*') if p.is_file())
        expect(not any(p.is_symlink() for p in paths),'Stopped archive symlink refused')
        expect(not any(p.name=='collector.lock' for p in paths),'Stopped collector lock remains')
        for p in paths:
            name=p.relative_to(ROOT).as_posix();item=(name,raw_sha(p))
            if 'native' in p.parts:native.append(item)
            else:metadata[name]=item[1]
    for name in ('swarm-ledger-v1-main-driver','swarm-ledger-resume-v1-driver','swarm-ledger-resume-v2-driver'):
        state=ROOT/'runs'/name/'state.json'
        metadata[state.relative_to(ROOT).as_posix()]=raw_sha(state)
    return dict(metadata_sha256=metadata,native_files=len(native),native_inventory_sha256=digest(sorted(native)))


def stopped_prefix_gate():
    second.verify();second.stopped_prefix_gate()
    state=read(ROOT/'runs/swarm-ledger-resume-v2-driver/state.json')
    expect(state.get('status')=='stopped' and state.get('stage')=='readers','Expected actual stopped reader driver')
    expect(state.get('exit_code')==1,'Unexpected stopped continuation exit')
    d.process_dead(state['pid'],state['updated'])
    if state.get('child_pid') is not None:d.process_dead(state['child_pid'],state['updated'])
    expect(not list(second_folder().rglob('collector.lock')),'Prior continuation phase lock remains')
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
    for out,registration_path in ((original_folder(phase),s.freeze_path('main')),
                                  (prior_folder(phase),prior.FREEZE),(second_folder(phase),second.FREEZE),
                                  (folder(phase),FREEZE)):
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
    names=(s.freeze_path('main'),d.op_freeze('main'),prior.FREEZE,second.FREEZE)
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
    jobs=main_jobs('readers');pending=pending_jobs('readers',jobs)
    expect(len(jobs)==53760 and len(pending)==33834,'Stopped reader complement differs')
    for phase in ('calibration','influence'):
        expect(len(pending_jobs(phase,main_jobs(phase)))==240,'Auxiliary complement differs')
    value=dict(schema_version=1,tag=TAG,created=s.now(),policy=policy,
      source_sha256={name:s.sha(ROOT/name) for name in SOURCES},parent_registration_sha256=parent_anchors(),
      original_prefix=snapshot_prefix(),forecast_sha256=s.sha(FORECAST),
      reader_unstarted_descriptor_sha256=digest(pending),reader_unstarted=33834,
      remaining_calls=dict(readers=33834,calibration=240,influence=240,total=34314),
      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      timing='Operational continuation after retained HF429 availability stop; before resumed inference; scientific design/endpoints/scoring unchanged')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')
    return dict(created=True,tag=TAG,inference_calls=0)


def verify(check_prefix=True):
    second.verify(check_prefix=check_prefix)
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


FUNDING_OR_RATE_MARKERS=('billing','credit','payment','insufficient','quota','rate limit','rate_limit','token limit','authentication','unauthorized','forbidden')


def hf_engine_overloaded(status,private):
    """Exact observed HF429 schema; rate/quota/funding and unknown errors fail closed."""
    if status.get('http_status')!=429 or status.get('capture_failed') or status.get('connection_fault'):
        return False
    text=private.get('error_body','')
    if not isinstance(text,str) or len(text.encode('utf-8'))>16384:
        return False
    def unique_object(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate error envelope key')
            result[key]=value
        return result
    try:value=json.loads(text,object_pairs_hook=unique_object)
    except (ValueError,TypeError):return False
    if not isinstance(value,dict) or set(value)!={'error'} or not isinstance(value['error'],dict):return False
    error=value['error'];message=error.get('message')
    return (set(error)=={'type','code','param','message'} and error['type']=='invalid_request_error'
            and error['code']=='engine_overloaded' and error['param'] is None
            and isinstance(message,str) and 0<len(message)<=512 and ('overloaded' in message.lower() or 'busy' in message.lower())
            and not any(marker in message.lower() for marker in FUNDING_OR_RATE_MARKERS))


def availability_class(status,private,provider):
    if status.get('capture_failed'):return None
    if provider=='hf' and hf_engine_overloaded(status,private):return 'hf_engine_overloaded'
    if status.get('http_status') in (500,502,503,504):
        text=private.get('error_body','')
        if not isinstance(text,str) or any(marker in text.lower() for marker in FUNDING_OR_RATE_MARKERS):return None
        return 'http_server_failure'
    return None


def historical_hf_overload(row):
    """Read only failed private envelopes; never mutate retained terminal metadata."""
    if row['transport'].get('http_status')!=429 or s.profile(row['profile_id'])['provider']!='hf':return False
    name=digest(row['id'])+'.json';matches=[]
    for base in (ROOT/('runs/'+s.config()['study_id']+'-main'),prior_folder(),second_folder(),folder()):
        matches.extend(base.glob('*/native/'+name))
    expect(len(matches)==1,'Failed HF receipt must have exactly one archive owner')
    expect(raw_sha(matches[0])==row['native_receipt_sha256'],'Failed HF receipt hash changed')
    return hf_engine_overloaded(row['transport'],read(matches[0]))


def publish_availability(status,failure_class=None,consecutive_count=0,next_dispatch_epoch=None,episode_remaining_seconds=None):
    """Durable safe operational status; contains no request or native identifiers."""
    expect(status in ('waiting','recovered'),'Unknown availability status')
    out=folder();out.mkdir(parents=True,exist_ok=True)
    value=dict(status=status,updated=s.now(),failure_class=failure_class,consecutive_count=consecutive_count,episode_remaining_seconds=episode_remaining_seconds,
               next_dispatch_at=(datetime.fromtimestamp(next_dispatch_epoch,timezone.utc).isoformat() if next_dispatch_epoch is not None else None))
    s.atomic_metadata(out/'availability-state.json',value)


class ResumeTransport(s.Transport):
    """Original body/normalizer with new safe transport diagnostics, one POST only."""
    def __init__(self,keys,out,opener=None):
        super().__init__(keys,out,opener);self.dispatch_lock=threading.Lock()
    def metadata(self,url,keyname=None):
        allowed={'https://api.prod.adaptionlabs.ai/api/v1/models?type=hosted':'adaption',
                 'https://router.huggingface.co/v1/models':'hf','https://ollama.com/api/tags':'ollama',
                 'https://ollama.com/api/balance':'ollama'}
        expect(url in allowed,'Metadata endpoint refused')
        headers={'Authorization':'Bearer '+self.keys[keyname]} if keyname else {}
        started=time.monotonic();failures=0
        while True:
            expect(time.time()<datetime.fromisoformat(policy['cutoff_utc']).timestamp(),'Metadata collection cutoff reached')
            expect(time.monotonic()-started<policy['availability_wait_bound_seconds'],'Metadata availability wait exhausted')
            status,native,private=connectivity.safe_request(self.opener,Request(url,headers=headers,method='GET'),timeout=30)
            expect(time.time()<datetime.fromisoformat(policy['cutoff_utc']).timestamp(),'Metadata collection cutoff reached')
            expect(time.monotonic()-started<policy['availability_wait_bound_seconds'],'Metadata availability wait exhausted')
            if status.get('http_status')==200 and isinstance(native,dict):return native
            available=availability_class(status,private,allowed[url]) is not None or status.get('connection_fault') is True
            expect(available,'Metadata authentication/profile/JSON check failed')
            failures+=1
            expect(failures<=policy['max_consecutive_provider_failures'],'Metadata availability failure limit')
            delay=max(policy['availability_backoff_seconds'][min(failures-1,3)],retry_after_private(private))
            remaining=min(policy['availability_wait_bound_seconds']-(time.monotonic()-started),datetime.fromisoformat(policy['cutoff_utc']).timestamp()-time.time())
            expect(delay<remaining,'Metadata availability wait/cutoff exhausted')
            publish_availability('waiting',availability_class(status,private,allowed[url]) or 'connection_fault',failures,time.time()+delay)
            time.sleep(delay)

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
        if status.get('http_status')!=200 and any(marker in private.get('error_body','').lower() for marker in FUNDING_OR_RATE_MARKERS):
            status['fatal_provider_error']=True
        if p['provider']=='hf' and hf_engine_overloaded(status,private):
            status['provider_failure_class']='hf_engine_overloaded'
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
        status,native,private=connectivity.safe_request(transport.opener,request,timeout=30)
        if status.get('connection_fault') is True:return False
        provider={'ADAPTION_API_KEY':'adaption','HF_TOKEN':'hf','OLLAMA_API_KEY':'ollama'}[key]
        if availability_class(status,private,provider) is not None:return False
        expect(status.get('http_status')==200 and isinstance(native,dict),'Metadata authentication/profile/JSON check failed')
    return True


def readonly_readiness(transport=None):
    """Read-only catalog readiness plus unchanged route/model/price validation."""
    transport=transport or ResumeTransport(s.credentials(),folder()/'metadata')
    if not connectivity_probe(transport):return False
    s.check_metadata(transport)
    return True


def cost_baseline():
    """Every old failed/unknown terminal and excluded pilot remains charged."""
    combined={p:Decimal(0) for p in ('adaption','hf','ollama')};main=dict(combined);classes={'actors':Decimal(0),'readers':Decimal(0)}
    paths=set()
    for split in ('technical','development','main'):
        paths.update((ROOT/('runs/'+s.config()['study_id']+'-'+split)).glob('*/responses.jsonl'))
    paths.update(prior_folder().glob('*/responses.jsonl'));paths.update(second_folder().glob('*/responses.jsonl'));paths.update(folder().glob('*/responses.jsonl'));paths.update(d.pilot_spending_paths())
    for path in paths:
        is_main=path.parent.parent in (folder(),prior_folder(),second_folder()) or path.parent.parent.name==s.config()['study_id']+'-main'
        for row in rows(path):
            provider=s.profile(row['profile_id'])['provider'];amount=Decimal(row['estimated_cost']);combined[provider]+=amount
            if is_main:
                main[provider]+=amount
                if provider=='adaption':classes['readers' if row['metadata'].get('procedure') else 'actors']+=amount
    return combined,main,classes


def known_server_error(row):
    """HTTP500 is server delivery failure, never a successful reasoning answer."""
    if row['transport'].get('fatal_provider_error') is True:return False
    return (row['transport'].get('http_status')==500 or d.known_capacity_error(row)
            or (s.profile(row['profile_id'])['provider']=='hf'
                and row['transport'].get('http_status')==429
                and (row['transport'].get('provider_failure_class')=='hf_engine_overloaded' or historical_hf_overload(row))))


def retry_after_private(private):
    """Parse only bounded allowlisted Retry-After, never return private headers."""
    from email.utils import parsedate_to_datetime
    values=[value for key,value in private.get('headers',{}).items() if key.lower()=='retry-after']
    if not values:return 0
    expect(len(values)==1,'Multiple Retry-After values')
    text=str(values[0]).strip()
    try:delay=float(Decimal(text))
    except Exception:
        try:
            stamp=parsedate_to_datetime(text)
            if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
            delay=max(0,(stamp-datetime.now(timezone.utc)).total_seconds())
        except Exception:raise ValueError('Unclassified Retry-After; stop safely') from None
    import math
    expect(math.isfinite(delay) and 0<=delay<=min(900,d.config()['retry_after_limit_seconds']),'Retry-After exceeds registered wait bound')
    return delay


def server_error_delay(row,out,consecutive=1):
    private=read(out/'native'/(digest(row['id'])+'.json'))
    return max(policy['availability_backoff_seconds'][min(max(1,consecutive)-1,3)],retry_after_private(private))


def check_episode_bounds(episodes,at=None):
    """Finite live-v3 provider outage episodes; old archival wall time is irrelevant."""
    at=time.monotonic() if at is None else at
    for started in episodes.values():
        if started is not None:
            expect(0<=at-started<policy['availability_wait_bound_seconds'],'Provider availability episode exhausted')
    return True


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
        failures=sum(known_server_error(row) for row in historical)
        server500=sum(row['transport'].get('http_status')==500 for base in (prior_folder(),second_folder(),folder()) for path in base.glob('*/responses.jsonl') for row in rows(path))
        new_connections=sum(bool(row['transport'].get('connection_fault')) for base in (prior_folder(),second_folder(),folder()) for path in base.glob('*/responses.jsonl') for row in rows(path))
        expect(failures<=c['gateway_allowance'] and new_connections<=policy['max_new_connection_failures'] and server500<=policy['max_server500_failures'],'Retained failure allowance exhausted')
        reserved={p:Decimal(0) for p in combined};active={};per_model={};cooldown=0.;since_check=0;availability_pending=False
        consecutive={provider:0 for provider in combined};episodes={provider:None for provider in combined}
        for row in historical:
            provider=s.profile(row['profile_id'])['provider']
            if known_server_error(row):consecutive[provider]+=1
            elif row['transport'].get('http_status')==200 and row['known_usage'] and not row['anomaly']:consecutive[provider]=0
        expect(all(n<=policy['max_consecutive_provider_failures'] for n in consecutive.values()),'Retained consecutive failure allowance exhausted')
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
                    if not gate.dispatch_allowed() and not active:
                        gate.before_dispatch()
                        if availability_pending:s.check_metadata(transport)
                        check_episode_bounds(episodes)
                    if availability_pending and not active and gate.dispatch_allowed() and time.monotonic()>=cooldown:
                        check_episode_bounds(episodes);publish_availability('recovered',episode_remaining_seconds=min((policy['availability_wait_bound_seconds']-(time.monotonic()-start) for start in episodes.values() if start is not None),default=None));availability_pending=False
                    for j in list(pending):
                        if len(active)>=8 or time.monotonic()<cooldown or since_check>=c['metadata_recheck_calls'] or not gate.dispatch_allowed():break
                        p=s.profile(j['profile_id']);provider=p['provider'];key=(provider,p['model'])
                        if sum(s.profile(v['profile_id'])['provider']==provider for v in active.values())>=c['provider_max_active'][provider] or per_model.get(key,0)>=c['dispatch_model_limits'][provider]:continue
                        check_episode_bounds(episodes);d.dispatch_time_gate('main');amount=s.reservation(j)
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
                        since_check+=1;transient=known_server_error(row) and not row['transport'].get('capture_failed');connection=row['transport'].get('connection_fault') is True and not row['transport'].get('capture_failed')
                        if row['transport'].get('http_status')==500:server500+=1
                        if connection:
                            new_connections+=1;gate.connection_failed()
                            if new_connections>policy['max_new_connection_failures']:fatal=True
                        if transient:
                            failures+=1;consecutive[provider]+=1;gate.connection_failed()
                            if episodes[provider] is None:episodes[provider]=time.monotonic()
                            check_episode_bounds(episodes)
                            if consecutive[provider]>policy['max_consecutive_provider_failures']:fatal=True
                            delay=server_error_delay(row,out,consecutive[provider])
                            remaining=policy['availability_wait_bound_seconds']-(time.monotonic()-episodes[provider])
                            expect(delay<remaining,'Provider availability episode cannot fit cooldown')
                            cooldown=max(cooldown,time.monotonic()+delay);d.persist_cooldown(time.time()+delay)
                            publish_availability('waiting',row['transport'].get('provider_failure_class') or 'http_server_failure',consecutive[provider],time.time()+max(0,cooldown-time.monotonic()),remaining);availability_pending=True
                        http=row['transport'].get('http_status')
                        if http==200 and row['known_usage'] and not row['anomaly']:
                            consecutive[provider]=0;episodes[provider]=None
                        if row['transport'].get('capture_failed') or (not row['known_usage'] and not transient and not connection) or row['anomaly'] and row['known_usage'] or (http==500 and row['known_usage']) or failures>c['gateway_allowance'] or server500>policy['max_server500_failures'] or http in (401,402,403) or (http==429 and not transient):fatal=True
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
    with s.exclusive(ROOT/'runs/swarm-ledger-resume-v3-guard'),s.verified_config():
        d.capacity_cooldown();return _execute(phase,jobs,transport,gate)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('freeze','verify','run'));parser.add_argument('--phase',choices=PHASES)
    args=parser.parse_args();result=freeze() if args.command=='freeze' else {'valid':bool(verify())} if args.command=='verify' else run(args.phase)
    print(json.dumps(result))


if __name__=='__main__':main()
