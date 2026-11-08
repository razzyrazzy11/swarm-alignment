"""Prospective paced continuation; six stopped archives stay immutable.

No provider calls, credentials or empirical outcomes are accessed on import.
Only exact unstarted identities may be collected in the separate new journals.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib, json, subprocess, threading, time
from pathlib import Path
from urllib.request import Request

from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_complete_dispatch as d
from experiments import collection_connectivity as connectivity
from experiments import swarm_ledger_resume as prior
from experiments import swarm_ledger_resume_v2 as second
from experiments import swarm_ledger_resume_v3 as third
from experiments import swarm_ledger_efficient as fourth
from experiments import swarm_ledger_rate as fifth

ROOT = s.ROOT
TAG = 'swarm-ledger-paced-v1'
FREEZE = ROOT/'research/swarm-ledger-paced-v1-freeze.json'
FORECAST = ROOT/'research/paced-resume-forecast.json'
SOURCES = ('experiments/swarm_ledger_paced.py','experiments/tests/test_swarm_ledger_paced.py',
 'research/SWARM_LEDGER_PACED_PROTOCOL.md','experiments/paced_resume_analysis.py',
 'experiments/tests/test_paced_resume_analysis.py','research/PACED_RESUME_ANALYSIS_PROTOCOL.md',
 'experiments/paced_resume_forecast.py','experiments/tests/test_paced_resume_forecast.py',
 'experiments/paced_resume_supervisor.py','experiments/tests/test_paced_resume_supervisor.py',
 'research/PACED_RESUME_OPERATIONS.md')
PHASES = ('readers','calibration','influence')
ROLES = ('principal','coordinator','x','y','reporter')
expect=s.expect; canonical=s.canonical; digest=s.digest; read=s.read; rows=s.rows
policy = dict(reset_window_utc=['04:55','05:05'], healthy_checks=2, healthy_interval_seconds=15,
              max_connectivity_wait_seconds=900, max_new_connection_failures=32,
              cutoff_utc='2026-11-09T07:56:00+00:00',
              target_drained_utc='2026-11-09T08:00:00+00:00',
              submission_deadline_utc='2026-11-09T11:59:00+00:00', retries=0,
              max_server500_failures=32, server500_cooldown_seconds=60,
              max_consecutive_provider_failures=8, availability_backoff_seconds=[60,120,240,480],
              availability_wait_bound_seconds=900, native_model_spacing_seconds=3.2,
              native_global_spacing_seconds=1.6, scoped_cooldown_class='adaption_rate_limit')


def folder(phase=None):
    out=ROOT/'runs/swarm-ledger-paced-v1-main'
    return out/phase if phase else out


def original_folder(phase):return ROOT/('runs/'+s.config()['study_id']+'-main')/phase
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prior_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-resume-v1-main'
    return base/phase if phase else base


def second_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-resume-v2-main'
    return base/phase if phase else base


def third_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-resume-v3-main'
    return base/phase if phase else base


def fourth_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-efficient-v1-main'
    return base/phase if phase else base


def fifth_folder(phase=None):
    base=ROOT/'runs/swarm-ledger-rate-v1-main'
    return base/phase if phase else base


def snapshot_prefix():
    """Commit both stopped archives without printing any private receipt text."""
    metadata={};native=[]
    for main in (ROOT/('runs/'+s.config()['study_id']+'-main'),prior_folder(),second_folder(),third_folder(),fourth_folder(),fifth_folder()):
        paths=sorted(p for p in main.rglob('*') if p.is_file())
        expect(not any(p.is_symlink() for p in paths),'Stopped archive symlink refused')
        expect(not any(p.name=='collector.lock' for p in paths),'Stopped collector lock remains')
        for p in paths:
            name=p.relative_to(ROOT).as_posix();item=(name,raw_sha(p))
            if 'native' in p.parts:native.append(item)
            else:metadata[name]=item[1]
    for name in ('swarm-ledger-v1-main-driver','swarm-ledger-resume-v1-driver','swarm-ledger-resume-v2-driver','swarm-ledger-resume-v3-driver','swarm-ledger-efficient-v1-driver','swarm-ledger-rate-v1-driver'):
        state=ROOT/'runs'/name/'state.json'
        metadata[state.relative_to(ROOT).as_posix()]=raw_sha(state)
    return dict(metadata_sha256=metadata,native_files=len(native),native_inventory_sha256=digest(sorted(native)))


def stopped_prefix_gate():
    fifth.verify();fifth.stopped_prefix_gate()
    state=read(ROOT/'runs/swarm-ledger-rate-v1-driver/state.json')
    expect(state.get('status')=='stopped' and state.get('stage')=='readers','Expected actual stopped rate reader driver')
    expect(state.get('exit_code') in (None,0),'Controlled rate stop cannot hide a failed phase')
    out=fifth_folder('readers')
    expect((out/'STOP').is_file() and not (out/'stop.json').exists(),'Controlled STOP without fatal stop required')
    availability=fifth_folder()/'availability-state.json'
    if availability.exists():validate_predecessor_episode_at_stop(state,read(availability))
    expect(not rows(out/'capture-failures.jsonl'),'Rate predecessor capture failure refused')
    d.process_dead(state['pid'],state['updated'])
    if state.get('child_pid') is not None:d.process_dead(state['child_pid'],state['updated'])
    expect(not list(fifth_folder().rglob('collector.lock')),'Rate predecessor phase lock remains')
    expect(not (ROOT/'runs/swarm-ledger-rate-v1-guard/collector.lock').exists(),'Rate predecessor global lock remains')
    with s.verified_config():
        jobs=main_jobs('readers');starts,terminal=_phase_ledger(out,jobs,fifth.FREEZE)
        validate_controlled_rate_rows(starts,terminal)
    return True


def validate_predecessor_episode_at_stop(state,availability):
    """A prospective handoff cannot excuse an old episode already expired at stop."""
    if availability.get('status')!='waiting' or availability.get('episode_remaining_seconds') is None:return True
    import math
    remaining=availability['episode_remaining_seconds']
    expect(type(remaining) in (int,float) and math.isfinite(remaining) and 0<=remaining<=900,'Predecessor episode budget invalid')
    stopped=datetime.fromisoformat(state['updated'].replace('Z','+00:00'))
    published=datetime.fromisoformat(availability['updated'].replace('Z','+00:00'))
    expect(stopped.tzinfo is not None and published.tzinfo is not None and stopped.utcoffset().total_seconds()==published.utcoffset().total_seconds()==0,'Predecessor episode UTC timestamps required')
    expect(published<=stopped,'Predecessor availability published after terminal stop')
    expect(stopped<published+timedelta(seconds=remaining),'Predecessor admission episode exhausted at terminal stop')
    return True


def validate_controlled_rate_rows(starts,terminal):
    expect(len(starts)==len(terminal) and {row['id'] for row in starts}=={row['id'] for row in terminal},'Rate predecessor unresolved identity')
    expect(len({row['id'] for row in starts})==len(starts) and len({row['id'] for row in terminal})==len(terminal),'Rate predecessor duplicate identity')
    for row in terminal:
        status=row['transport'];http=status.get('http_status')
        expect(not status.get('capture_failed'),'Rate predecessor capture failed')
        if http==200:
            expect(row['known_usage'] is True and not row['anomaly'] and not status.get('fatal_provider_error'),'Rate predecessor normalization anomaly')
        else:
            expect(row['known_usage'] is False and row['anomaly'] is True,'Unexpected failed predecessor usage')
            expect(known_server_error(row) or (status.get('connection_fault') is True and http is None),'Unclassified predecessor failure')
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
                                  (third_folder(phase),third.FREEZE),(fourth_folder(phase),fourth.FREEZE),(fifth_folder(phase),fifth.FREEZE),(folder(phase),FREEZE)):
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
    names=(s.freeze_path('main'),d.op_freeze('main'),prior.FREEZE,second.FREEZE,third.FREEZE,fourth.FREEZE,fifth.FREEZE)
    return {p.relative_to(ROOT).as_posix():s.sha(p) for p in names}


def validate_resume_forecast(value,at=None):
    at=datetime.now(timezone.utc) if at is None else at
    expect(type(value.get('schema_version')) is int and value['schema_version']==1,'Remaining forecast schema')
    expect(all(value.get(k) is True for k in ('deadline_feasible','budget_feasible','off_peak_wallet_gate_passed')),'Remaining workload forecast gate failed')
    cutoff=value.get('collection_cutoff_utc',value.get('cutoff_utc'))
    expect(cutoff==policy['cutoff_utc'],'Remaining forecast cutoff changed')
    expect(value.get('pacing_minima_seconds')==dict(native_global='1.6',native_model='3.2'),'Prospective pacing forecast differs')
    duration=Decimal(str(value.get('forecast_seconds')))
    expect(duration.is_finite() and duration>0,'Invalid remaining forecast duration')
    expect(at.timestamp()+float(duration)<datetime.fromisoformat(cutoff).timestamp(),'Remaining workload no longer fits cutoff')
    return value


def validate_complement_forecast(value,remaining,descriptors):
    expect(value.get('remaining_calls')==remaining,'Forecast remaining complement differs')
    expect(value.get('unstarted_descriptor_sha256')==descriptors,'Forecast unstarted request descriptor differs')
    return True


def freeze():
    expect(not FREEZE.exists(),'Continuation registration already exists')
    expect(not any(folder().rglob('attempts.jsonl')),'Continuation attempts already exist')
    s.registration('main');d.verify('main');stopped_prefix_gate()
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit continuation sources before registration')
    expect(FORECAST.is_file(),'Prospective remaining-workload forecast required');validate_resume_forecast(read(FORECAST))
    remaining={};descriptors={}
    with s.verified_config():
        for phase in PHASES:
            jobs=main_jobs(phase);pending=pending_jobs(phase,jobs)
            expect(len(jobs)==(53760 if phase=='readers' else 240),'Original full plan count differs')
            remaining[phase]=len(pending);descriptors[phase]=digest(pending)
    expect(remaining['readers']>0 and sum(remaining.values())>0,'No MAIN reader complement remains')
    validate_complement_forecast(read(FORECAST),remaining,descriptors)
    value=dict(schema_version=1,tag=TAG,created=s.now(),policy=policy,
      source_sha256={name:s.sha(ROOT/name) for name in SOURCES},parent_registration_sha256=parent_anchors(),
      original_prefix=snapshot_prefix(),forecast_sha256=s.sha(FORECAST),
      reader_unstarted_descriptor_sha256=descriptors['readers'],reader_unstarted=remaining['readers'],
      unstarted_descriptor_sha256=descriptors,remaining_calls=dict(remaining,total=sum(remaining.values())),
      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      timing='Operational continuation after controlled rate drain; stricter native pacing and scoped Adaption-rate wait; before resumed inference; scientific design/endpoints/scoring unchanged')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')
    return dict(created=True,tag=TAG,inference_calls=0)


def verify(check_prefix=True):
    fifth.verify(check_prefix=check_prefix)
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


RATE_FORBIDDEN_MARKERS=('billing','credit','payment','insufficient','quota','authentication','authorization','permission','api key','api_key','unauthorized','forbidden','account suspended','access denied')


def adaption_rate_limit(status,private):
    """Precise observed rate schema and agreed bounded wait; None means fatal."""
    if status.get('http_status')!=429 or status.get('capture_failed') or status.get('connection_fault'):return None
    text=private.get('error_body','')
    if not isinstance(text,str) or not 0<len(text.encode('utf-8'))<=16384:return None
    def unique_object(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate rate-envelope key')
            result[key]=value
        return result
    try:value=json.loads(text,object_pairs_hook=unique_object)
    except (ValueError,TypeError):return None
    if not isinstance(value,dict) or set(value)!={'error'} or not isinstance(value['error'],dict):return None
    error=value['error'];message=error.get('message')
    if (set(error)!={'type','code','param','message'} or error['type']!='rate_limit_error'
            or error['code']!='rate_limit_exceeded' or error['param'] is not None
            or not isinstance(message,str) or not 0<len(message)<=512
            or any(marker in message.lower() for marker in RATE_FORBIDDEN_MARKERS)
            or 'rate limit' not in message.lower()):return None
    headers=private.get('headers',{})
    if not isinstance(headers,dict):return None
    values=[value for key,value in headers.items() if key.lower()=='retry-after']
    if len(values)!=1:return None
    try:
        delay=Decimal(str(values[0]).strip())
        if not delay.is_finite() or not 0<delay<=min(900,d.config()['retry_after_limit_seconds']):return None
    except Exception:return None
    import re
    message_lower=message.lower()
    waits=re.findall(r'retry\s+after\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b',message_lower)
    if message_lower.count('retry after')!=1 or len(waits)!=1:return None
    if Decimal(waits[0])!=delay:return None
    return float(delay)


def historical_adaption_rate(row):
    if row['transport'].get('http_status')!=429 or s.profile(row['profile_id'])['provider']!='adaption':return False
    name=digest(row['id'])+'.json';matches=[]
    for base in (ROOT/('runs/'+s.config()['study_id']+'-main'),prior_folder(),second_folder(),third_folder(),fourth_folder(),fifth_folder(),folder()):
        matches.extend(base.glob('*/native/'+name))
    expect(len(matches)==1,'Rate receipt must have exactly one archive owner')
    expect(raw_sha(matches[0])==row['native_receipt_sha256'],'Rate receipt hash changed')
    return adaption_rate_limit(row['transport'],read(matches[0])) is not None


def availability_class(status,private,provider):
    if status.get('capture_failed'):return None
    if provider=='adaption' and adaption_rate_limit(status,private) is not None:return 'adaption_rate_limit'
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
    for base in (ROOT/('runs/'+s.config()['study_id']+'-main'),prior_folder(),second_folder(),third_folder(),fourth_folder(),fifth_folder(),folder()):
        matches.extend(base.glob('*/native/'+name))
    expect(len(matches)==1,'Failed HF receipt must have exactly one archive owner')
    expect(raw_sha(matches[0])==row['native_receipt_sha256'],'Failed HF receipt hash changed')
    return hf_engine_overloaded(row['transport'],read(matches[0]))


def publish_availability(status,failure_class=None,consecutive_count=0,next_dispatch_epoch=None,episode_remaining_seconds=None,provider=None):
    """Durable safe operational status; contains no request or native identifiers."""
    expect(status in ('waiting','recovered'),'Unknown availability status')
    out=folder();out.mkdir(parents=True,exist_ok=True)
    value=dict(status=status,updated=s.now(),provider=provider,failure_class=failure_class,consecutive_count=consecutive_count,episode_remaining_seconds=episode_remaining_seconds,
               next_dispatch_at=(datetime.fromtimestamp(next_dispatch_epoch,timezone.utc).isoformat() if next_dispatch_epoch is not None else None))
    s.atomic_metadata(out/'availability-state.json',value)


class NativePacer:
    """Atomic client-send claims; release the clock lock before every wait."""
    def __init__(self,*,clock=time.time,sleep=time.sleep):
        self.clock,self.sleep=clock,sleep;self.lock=threading.Lock()
        self.global_path=ROOT/('runs/'+s.config()['study_id']+'-guard/native-dispatch-private.json')
        self.model_path=folder()/'native-model-clock-private.json'
        self.allowed_models={digest(profile['model']) for profile in s.config()['profiles'] if profile['provider']=='adaption'}
        self.last_global=read(self.global_path)['epoch'] if self.global_path.exists() else 0
        self.last_models=read(self.model_path).get('models',{}) if self.model_path.exists() else {}
        now=self.clock();self._validate(now)
    def _validate(self,now):
        import math
        expect(type(self.last_global) in (int,float) and math.isfinite(self.last_global) and 0<=self.last_global<=now+60,'Native global clock drift')
        expect(isinstance(self.last_models,dict),'Native model clock schema')
        for key,value in self.last_models.items():
            expect(isinstance(key,str) and key in self.allowed_models,'Native model clock key')
            expect(type(value) in (int,float) and math.isfinite(value) and 0<value<=now+60,'Native model clock drift')
    def ready_at(self,model):
        with self.lock:
            expect(digest(model) in self.allowed_models,'Unregistered native pacing model')
            now=self.clock();self._validate(now)
            previous=self.last_models.get(digest(model),self.last_global if not self.last_models else 0)
            return max(self.last_global+policy['native_global_spacing_seconds'],previous+policy['native_model_spacing_seconds'])
    def ready(self,model):return self.clock()>=self.ready_at(model)
    def claim(self,model):
        expect(digest(model) in self.allowed_models,'Unregistered native pacing model')
        while True:
            with self.lock:
                now=self.clock();self._validate(now)
                previous=self.last_models.get(digest(model),self.last_global if not self.last_models else 0)
                wait_until=max(self.last_global+policy['native_global_spacing_seconds'],previous+policy['native_model_spacing_seconds'])
                delay=max(0,wait_until-now)
                expect(delay<=60+max(policy['native_model_spacing_seconds'],policy['native_global_spacing_seconds']),'Native pacing wait clock drift')
                if delay==0:
                    self.last_global=now;self.last_models[digest(model)]=now
                    self.global_path.parent.mkdir(parents=True,exist_ok=True);self.model_path.parent.mkdir(parents=True,exist_ok=True)
                    s.atomic_metadata(self.global_path,dict(epoch=now))
                    s.atomic_metadata(self.model_path,dict(models=self.last_models.copy()))
                    return now
            self.sleep(min(1,delay))


class ResumeTransport(s.Transport):
    """Original body/normalizer with new safe transport diagnostics, one POST only."""
    def __init__(self,keys,out,opener=None):
        super().__init__(keys,out,opener);self.dispatch_lock=threading.Lock();self.pacer=NativePacer()
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
        req=Request(p['endpoint'],data=canonical(s.body_for(j)).encode(),method='POST',
                    headers={'Authorization':'Bearer '+self.keys[keyname],'Content-Type':'application/json'})
        if p['provider']=='adaption':self.pacer.claim(p['model'])
        status,native,private=connectivity.safe_request(self.opener,req,timeout=s.config()['request_timeout_seconds'])
        if status.get('http_status') in (429,502,503,504):status['service_overload']=s.service_overload(status['http_status'],private.get('error_body',''))
        if status.get('http_status')!=200 and any(marker in private.get('error_body','').lower() for marker in FUNDING_OR_RATE_MARKERS):
            status['fatal_provider_error']=True
        if p['provider']=='adaption' and adaption_rate_limit(status,private) is not None:
            status.pop('fatal_provider_error',None)
            status['provider_failure_class']='adaption_rate_limit'
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


class GlobalReadinessRequired(ValueError):pass


def native_readiness_probe(transport):
    """Adaption-only retryable rate check; other readiness faults retain global scope."""
    expect(bool(transport.keys.get('ADAPTION_API_KEY')),'Missing native metadata credential')
    request=Request('https://api.prod.adaptionlabs.ai/api/v1/models?type=hosted',headers={'Authorization':'Bearer '+transport.keys['ADAPTION_API_KEY']},method='GET')
    status,native,private=connectivity.safe_request(transport.opener,request,timeout=30)
    if status.get('connection_fault') is True:raise GlobalReadinessRequired('Native health connectivity requires global gate')
    if adaption_rate_limit(status,private) is not None:return False
    if availability_class(status,private,'adaption') is not None:raise GlobalReadinessRequired('Native health server failure requires global gate')
    expect(status.get('http_status')==200 and isinstance(native,dict),'Native metadata authentication/profile/JSON check failed')
    available={item['id'] for item in native.get('data',[]) if isinstance(item,dict) and 'id' in item}
    expect({profile['model'] for profile in s.config()['profiles'] if profile['provider']=='adaption'}<=available,'Native model drift')
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
    paths.update(prior_folder().glob('*/responses.jsonl'));paths.update(second_folder().glob('*/responses.jsonl'));paths.update(third_folder().glob('*/responses.jsonl'));paths.update(fourth_folder().glob('*/responses.jsonl'));paths.update(fifth_folder().glob('*/responses.jsonl'));paths.update(folder().glob('*/responses.jsonl'));paths.update(d.pilot_spending_paths())
    for path in paths:
        is_main=path.parent.parent in (folder(),prior_folder(),second_folder(),third_folder(),fourth_folder(),fifth_folder()) or path.parent.parent.name==s.config()['study_id']+'-main'
        for row in rows(path):
            provider=s.profile(row['profile_id'])['provider'];amount=Decimal(row['estimated_cost']);combined[provider]+=amount
            if is_main:
                main[provider]+=amount
                if provider=='adaption':classes['readers' if row['metadata'].get('procedure') else 'actors']+=amount
    return combined,main,classes


def known_server_error(row):
    """HTTP500 is server delivery failure, never a successful reasoning answer."""
    if row['transport'].get('http_status')==429 and s.profile(row['profile_id'])['provider']=='adaption' and historical_adaption_rate(row):
        return True
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
    rate_wait=adaption_rate_limit(row['transport'],private) if s.profile(row['profile_id'])['provider']=='adaption' else None
    return max(policy['availability_backoff_seconds'][min(max(1,consecutive)-1,3)],retry_after_private(private),rate_wait or 0)


def check_episode_bounds(episodes,at=None):
    """Finite live-v3 provider outage episodes; old archival wall time is irrelevant."""
    at=time.monotonic() if at is None else at
    for started in episodes.values():
        if started is not None:
            expect(0<=at-started<policy['availability_wait_bound_seconds'],'Provider availability episode exhausted')
    return True


def dispatch_time_gate(split='main',at=None):
    """New prospective admission clock; historical operational sources stay fixed."""
    expect(split=='main','Rate continuation is MAIN only')
    at=datetime.now(timezone.utc) if at is None else at
    expect(at.tzinfo is not None and at.utcoffset().total_seconds()==0,'UTC dispatch time required')
    expect(at<datetime.fromisoformat(policy['cutoff_utc']),'Registered rate-continuation last dispatch reached')
    if d.config()['off_peak_only']:expect(d.off_peak(at),'Off-peak-only operational allowance cannot be used now')
    return True


def capacity_cooldown():
    """Same persisted wait, checked against the new admission clock, never a POST retry."""
    until=0
    checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
    if checkpoint.exists():until=max(until,read(checkpoint)['not_before_epoch'])
    expect(type(until) in (int,float),'Capacity cooldown clock invalid')
    while time.time()<until:
        dispatch_time_gate('main');time.sleep(min(1,until-time.time()))


class EligibilityCache:
    """Immutable descriptors and exact counts; no queue reordering or cap changes."""
    def __init__(self,pending):
        self.descriptors={}
        self.pending_counts={}
        self.active_providers={provider:0 for provider in ('adaption','hf','ollama')}
        for job in pending:
            identity=job['profile_id']
            if identity not in self.descriptors:
                profile=s.profile(identity)
                self.descriptors[identity]=(profile['provider'],(profile['provider'],profile['model']))
            provider,key=self.descriptors[identity]
            self.pending_counts[key]=self.pending_counts.get(key,0)+1
    def descriptor(self,job):return self.descriptors[job['profile_id']]
    def any_eligible(self,per_model,config,ready=None):
        return any(count>0 and self.active_providers[key[0]]<config['provider_max_active'][key[0]]
                   and per_model.get(key,0)<config['dispatch_model_limits'][key[0]]
                   and (ready is None or ready(key[0],key))
                   for key,count in self.pending_counts.items())
    def admitted(self,job):
        provider,key=self.descriptor(job)
        expect(self.pending_counts[key]>0,'Pending eligibility count underflow')
        self.pending_counts[key]-=1;self.active_providers[provider]+=1
    def completed(self,job):
        provider,key=self.descriptor(job)
        expect(self.active_providers[provider]>0,'Active provider count underflow')
        self.active_providers[provider]-=1


def _execute(phase,jobs,transport=None,gate=None,native_gate=None):
    """Disjoint continuation only; no mutation of original stopped phase."""
    c=d.execution_config('main',phase);out=folder(phase);ordered=sorted(jobs,key=lambda j:j['id'])
    with s.exclusive(out):
        plan=dict(jobs_sha256=digest(ordered),ids=[j['id'] for j in ordered],freeze_sha256=s.sha(FREEZE))
        if (out/'plan.json').exists():expect(read(out/'plan.json')==plan,'Continuation phase plan drift')
        else:
            with (out/'plan.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream)
        expect(not (out/'stop.json').exists(),'Continuation stopped; new amendment required')
        pending=pending_jobs(phase,ordered);eligibility=EligibilityCache(pending)
        transport=transport or ResumeTransport(s.credentials(),out)
        gate=gate or connectivity.ConnectivityGate(lambda:connectivity_probe(transport),deadline=policy['cutoff_utc'])
        native_gate=native_gate or connectivity.ConnectivityGate(lambda:native_readiness_probe(transport),deadline=policy['cutoff_utc'])
        gate.before_dispatch(force_health=True);s.check_metadata(transport)
        combined,spent,classes=cost_baseline();balance=d.BalanceGuard(transport,'main')
        historical,_=union_phase(phase,ordered,False)
        failures=sum(known_server_error(row) for row in historical)
        server500=sum(row['transport'].get('http_status')==500 for base in (prior_folder(),second_folder(),third_folder(),fourth_folder(),fifth_folder(),folder()) for path in base.glob('*/responses.jsonl') for row in rows(path))
        new_connections=sum(bool(row['transport'].get('connection_fault')) for base in (prior_folder(),second_folder(),third_folder(),fourth_folder(),fifth_folder(),folder()) for path in base.glob('*/responses.jsonl') for row in rows(path))
        expect(failures<=c['gateway_allowance'] and new_connections<=policy['max_new_connection_failures'] and server500<=policy['max_server500_failures'],'Retained failure allowance exhausted')
        reserved={p:Decimal(0) for p in combined};active={};per_model={};cooldown=0.;since_check=0;availability_pending=False
        consecutive={provider:0 for provider in combined};episodes={provider:None for provider in combined}
        provider_cooldown={provider:0. for provider in combined};native_needs_health=False
        hold_path=folder()/'provider-cooldown-private.json'
        inherited_hold=read(hold_path) if hold_path.exists() else None
        def ready(provider,key):
            if provider=='adaption':
                if native_needs_health or time.monotonic()<provider_cooldown[provider]:return False
                pacer=getattr(transport,'pacer',None)
                if pacer is not None and not pacer.ready(key[1]):return False
            return True
        def next_wait_seconds():
            now=time.monotonic();wall=time.time();delay=1.
            for key,count in eligibility.pending_counts.items():
                if count<=0 or key[0]!='adaption':continue
                if eligibility.active_providers['adaption']>=c['provider_max_active']['adaption'] or per_model.get(key,0)>=c['dispatch_model_limits']['adaption']:continue
                if native_needs_health and eligibility.active_providers['adaption']>0:continue
                wake=max(cooldown,provider_cooldown['adaption'])
                pacer=getattr(transport,'pacer',None)
                if pacer is not None:wake=max(wake,now+max(0,pacer.ready_at(key[1])-wall))
                delay=min(delay,max(.01,wake-now))
            return max(.01,min(1.,delay))
        for row in historical:
            provider=s.profile(row['profile_id'])['provider']
            if known_server_error(row):consecutive[provider]+=1
            elif row['transport'].get('http_status')==200 and row['known_usage'] and not row['anomaly']:consecutive[provider]=0
        expect(all(n<=policy['max_consecutive_provider_failures'] for n in consecutive.values()),'Retained consecutive failure allowance exhausted')
        if inherited_hold is not None:
            import math
            expect(inherited_hold.get('provider')=='adaption' and type(inherited_hold.get('needs_health')) is bool,'Provider hold schema')
            epoch=inherited_hold.get('not_before_epoch');now_wall=time.time();now_mono=time.monotonic()
            expect(type(epoch) in (int,float) and math.isfinite(epoch) and 0<=epoch<=now_wall+900,'Provider hold clock drift')
            provider_cooldown['adaption']=now_mono+max(0,epoch-now_wall)
            native_needs_health=inherited_hold['needs_health']
            count=inherited_hold.get('consecutive')
            expect(type(count) is int and 0<=count<=policy['max_consecutive_provider_failures'],'Provider hold streak')
            consecutive['adaption']=max(consecutive['adaption'],count)
            episode=inherited_hold.get('episode_started_epoch')
            if episode is not None:
                expect(type(episode) in (int,float) and math.isfinite(episode) and episode<=now_wall,'Provider episode clock drift')
                episodes['adaption']=now_mono-(now_wall-episode)
                check_episode_bounds(episodes)
        def save_native_hold():
            now_wall=time.time();now_mono=time.monotonic();episode=episodes['adaption']
            value=dict(provider='adaption',needs_health=native_needs_health,consecutive=consecutive['adaption'],
                       not_before_epoch=now_wall+max(0,provider_cooldown['adaption']-now_mono),
                       episode_started_epoch=(now_wall-(now_mono-episode) if episode is not None else None))
            s.atomic_metadata(hold_path,value)

        def stop(reason):
            path=out/'stop.json'
            if not path.exists():s.atomic_metadata(path,dict(reason=reason,stopped=s.now(),freeze_sha256=s.sha(FREEZE)))
        def record(future,j):
            row=s.apply_host_action(future.result());amount=s.actual_cost(j,row['response']) if row['known_usage'] else s.reservation(j)
            row['estimated_cost']=str(amount);s.durable(out/'responses.jsonl',row)
            provider,_=eligibility.descriptor(j);combined[provider]+=amount;spent[provider]+=amount
            if provider=='adaption':classes['readers' if j['metadata'].get('procedure') else 'actors']+=amount
            return row
        def drain():
            for future,j in list(active.items()):
                eligibility.completed(j)
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
                    if native_needs_health and eligibility.active_providers['adaption']==0 and time.monotonic()>=provider_cooldown['adaption'] and gate.dispatch_allowed():
                        try:
                            native_gate.before_dispatch(force_health=True);s.check_metadata(transport);check_episode_bounds(episodes)
                            native_needs_health=False;save_native_hold();publish_availability('recovered',provider='adaption')
                        except GlobalReadinessRequired:
                            gate.connection_failed();availability_pending=True
                    if availability_pending and not active and gate.dispatch_allowed() and time.monotonic()>=cooldown:
                        check_episode_bounds(episodes);publish_availability('recovered',episode_remaining_seconds=min((policy['availability_wait_bound_seconds']-(time.monotonic()-start) for start in episodes.values() if start is not None),default=None));availability_pending=False
                    scan=(len(active)<8 and time.monotonic()>=cooldown and since_check<c['metadata_recheck_calls']
                          and gate.dispatch_allowed() and eligibility.any_eligible(per_model,c,ready))
                    for j in (list(pending) if scan else ()):
                        if len(active)>=8 or time.monotonic()<cooldown or since_check>=c['metadata_recheck_calls'] or not gate.dispatch_allowed():break
                        provider,key=eligibility.descriptor(j)
                        if eligibility.active_providers[provider]>=c['provider_max_active'][provider] or per_model.get(key,0)>=c['dispatch_model_limits'][provider] or not ready(provider,key):continue
                        check_episode_bounds(episodes);dispatch_time_gate('main');amount=s.reservation(j)
                        expect(spent[provider]+reserved[provider]+amount<=Decimal(c['phase_caps']['main'][provider]),'Provider MAIN cost cap')
                        expect(combined[provider]+reserved[provider]+amount<=Decimal(c['combined_caps'][provider]),'Combined cost cap')
                        if provider=='adaption':expect(classes['readers' if j['metadata'].get('procedure') else 'actors']+reserved[provider]+amount<=Decimal(c['native_class_caps']['readers' if j['metadata'].get('procedure') else 'actors']),'Native class cap')
                        if provider=='ollama':balance.check(combined[provider],reserved[provider]+amount)
                        s.durable(out/'attempts.jsonl',dict(id=j['id'],profile_id=j['profile_id'],request_sha256=digest(s.body_for(j)),reserved_cost=str(amount),started=s.now()))
                        reserved[provider]+=amount;per_model[key]=per_model.get(key,0)+1
                        active[pool.submit(transport.request,j)]=j;pending.remove(j);eligibility.admitted(j)
                        if not eligibility.any_eligible(per_model,c,ready):break
                    if not active:
                        if since_check>=c['metadata_recheck_calls']:
                            gate.before_dispatch(force_health=True);s.check_metadata(transport);since_check=0
                        elif pending:time.sleep(min(1,max(.01,cooldown-time.monotonic())))
                        continue
                    completed,_=wait(active,timeout=next_wait_seconds(),return_when=FIRST_COMPLETED);fatal=False
                    for future in completed:
                        j=active.pop(future);provider,key=eligibility.descriptor(j);eligibility.completed(j)
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
                            failures+=1;consecutive[provider]+=1
                            scoped=(provider=='adaption' and row['transport'].get('http_status')==429 and historical_adaption_rate(row))
                            if scoped:native_gate.connection_failed();native_needs_health=True
                            else:gate.connection_failed()
                            if episodes[provider] is None:episodes[provider]=time.monotonic()
                            check_episode_bounds(episodes)
                            if consecutive[provider]>policy['max_consecutive_provider_failures']:fatal=True
                            delay=server_error_delay(row,out,consecutive[provider])
                            remaining=policy['availability_wait_bound_seconds']-(time.monotonic()-episodes[provider])
                            expect(delay<remaining,'Provider availability episode cannot fit cooldown')
                            if scoped:
                                provider_cooldown[provider]=max(provider_cooldown[provider],time.monotonic()+delay)
                                save_native_hold()
                                publish_availability('waiting','adaption_rate_limit',consecutive[provider],time.time()+delay,remaining,provider=provider)
                            else:
                                cooldown=max(cooldown,time.monotonic()+delay);d.persist_cooldown(time.time()+delay)
                                publish_availability('waiting',row['transport'].get('provider_failure_class') or 'http_server_failure',consecutive[provider],time.time()+max(0,cooldown-time.monotonic()),remaining);availability_pending=True
                        http=row['transport'].get('http_status')
                        if http==200 and row['known_usage'] and not row['anomaly']:
                            consecutive[provider]=0;episodes[provider]=None
                            if provider=='adaption' and hold_path.exists():save_native_hold()
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
    with s.verified_config():
        for previous in PHASES[:PHASES.index(phase)]:union_phase(previous,main_jobs(previous),True)
        jobs=main_jobs(phase)
        with s.exclusive(ROOT/'runs/swarm-ledger-paced-v1-guard'):
            capacity_cooldown();return _execute(phase,jobs,transport,gate)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('freeze','verify','run'));parser.add_argument('--phase',choices=PHASES)
    args=parser.parse_args();result=freeze() if args.command=='freeze' else {'valid':bool(verify())} if args.command=='verify' else run(args.phase)
    print(json.dumps(result))


if __name__=='__main__':main()
