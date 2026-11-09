"""Fixed-capacity collection for the prospectively registered six-reader study.

Original scientific and failed-pilot sources remain immutable. No credentials,
private data or provider requests are accessed during import/public verification.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import hashlib,json,os,subprocess,threading,time
from pathlib import Path
from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_study as old
from experiments import swarm_ledger_dispatch_v2 as previous
ROOT=old.ROOT
CONFIG=ROOT/'research/swarm-ledger-complete-dispatch-config.json'
FORECAST=ROOT/'research/swarm-ledger-complete-forecast.json'
SOURCES=('experiments/swarm_ledger_complete_dispatch.py','experiments/tests/test_swarm_ledger_complete_dispatch.py',
 'research/SWARM_LEDGER_COMPLETE_DISPATCH_PROTOCOL.md','research/swarm-ledger-complete-dispatch-config.json',
 'experiments/swarm_ledger_complete_forecast.py','experiments/tests/test_swarm_ledger_complete_forecast.py',
 'research/swarm-ledger-dispatch-v1-stop.json','research/swarm-ledger-dispatch-v2-stop.json')
canonical=old.canonical;digest=old.digest;read=old.read;sha=old.sha;now=old.now;expect=old.expect
profile=old.profile;body_for=old.body_for;reservation=old.reservation;actual_cost=old.actual_cost
rows=old.rows;durable=old.durable;admitted=old.admitted;Transport=old.Transport
apply_host_action=old.apply_host_action;ledger=old.ledger;exclusive=old.exclusive
PHASES=('principal','coordinator','x','y','reporter','readers','calibration','influence')

def process_dead(pid,state_updated=None):
    expect(type(pid) is int and pid>0,'Driver process identity unavailable')
    if os.name=='nt':
        command=(f'try {{ $taskProcess=Get-Process -Id {pid} -ErrorAction Stop; '
                 '$taskProcess.StartTime.ToUniversalTime().ToString("o"); exit 0 } '
                 'catch { if ($_.CategoryInfo.Category -eq "ObjectNotFound") { exit 3 }; exit 4 }')
        result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True)
        if result.returncode==3:return True
        expect(result.returncode==0 and state_updated is not None,'Development process remains active or lookup failed')
        try:
            created=datetime.fromisoformat(result.stdout.decode().strip().replace('Z','+00:00'))
            updated=datetime.fromisoformat(state_updated.replace('Z','+00:00'))
        except (ValueError,AttributeError):raise ValueError('Cannot establish PID creation identity') from None
        expect(created.tzinfo is not None and updated.tzinfo is not None and created>updated,'Owned process remains active or PID reuse unproven')
    else:
        try:os.kill(pid,0)
        except ProcessLookupError:return True
        except (OSError,PermissionError):raise ValueError('Cannot verify development process exit') from None
        raise ValueError('Development process remains active')
    return True


def development_gate(state_path):
    """No accuracy selection: validate complete serving/host-evidence provenance."""
    state=read(Path(state_path))
    expect(state.get('status')=='complete' and state.get('last_completed_stage')=='readers','Development driver not complete')
    summary=state.get('summary',{})
    expect(summary.get('planned')==256 and summary.get('terminal')==256 and summary.get('complete') is True,'Development reader graph incomplete')
    process_dead(state.get('pid'),state.get('updated'));process_dead(state.get('child_pid'),state.get('updated'))
    from experiments import swarm_ledger_analysis as analysis
    with s.verified_config():coverage,_=analysis.validate_pre_main()
    expected={'technical':10,'development:principal':80,'development:coordinator':80,
              'development:x':320,'development:y':320,'development:reporter':320,'development:readers':256}
    for phase,n in expected.items():
        item=coverage[phase]
        expect(item['planned']==n and item['terminal']==n and item['complete'] is True,'Development/technical serving graph differs')
    return {'complete':True,'coverage':coverage,'driver_state_sha256':sha(state_path)}


def known_capacity_error(row):
    http=row['transport'].get('http_status')
    return http in (502,503,504) or (http==429 and row['transport'].get('service_overload') is True)


def gateway_backoff_seconds(row):
    """Prospective wait for a terminal response, never a retry of its identity."""
    c=config();provider=profile(row['profile_id'])['provider']
    return c['native_gateway_backoff_seconds'] if provider=='adaption' and row['transport'].get('http_status') in (502,503,504) else c['default_gateway_backoff_seconds']


def capacity_cooldown():
    until=0
    checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
    if checkpoint.exists():until=max(until,read(checkpoint)['not_before_epoch'])
    expect(type(until) in (int,float),'Capacity cooldown clock invalid')
    while time.time()<until:
        dispatch_time_gate('main');time.sleep(min(1,until-time.time()))


def persist_cooldown(until):
    checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
    previous=read(checkpoint).get('not_before_epoch',0) if checkpoint.exists() else 0
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    s.atomic_metadata(checkpoint,{'not_before_epoch':max(previous,until)})


def off_peak(at):return at.weekday()>=5 or at.hour<12 or at.hour>=18


def dispatch_time_gate(split):
    if split!='main':return True
    c=config();at=datetime.now(timezone.utc)
    expect(at<datetime.fromisoformat(c['collection_deadline_utc']),'Registered collection cutoff reached')
    if c['off_peak_only']:expect(off_peak(at),'Off-peak-only operational allowance cannot be used now')
    return True


def retry_after_delay(row,out):
    status=row['transport'].get('http_status')
    if status not in (502,503,504) and not row['transport'].get('service_overload'):return 0
    receipt=read(out/'native'/(digest(row['id'])+'.json'))
    values=[v for k,v in receipt.get('headers',{}).items() if k.lower()=='retry-after']
    if not values:return 0
    expect(len(values)==1,'Multiple Retry-After values')
    text=str(values[0]).strip()
    try:delay=float(Decimal(text))
    except Exception:
        try:
            date=parsedate_to_datetime(text)
            if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
            delay=max(0,(date-datetime.now(timezone.utc)).total_seconds())
        except Exception:raise ValueError('Unclassified Retry-After; stop safely') from None
    expect(0<=delay<=config()['retry_after_limit_seconds'],'Retry-After exceeds registered wait bound; stop instead of ignoring it')
    return delay


def retry_after_metadata_delay(row,out,fallback_epoch=None):
    """Original requested interval for historical forecasts, independent of now.

    Prefer the response's Date header. Otherwise use the recorded operational
    finish event, then a caller-supplied receive-time estimate for older DEV data.
    This reads only timing headers from the hashed private receipt.
    """
    if not known_capacity_error(row):return 0
    path=out/'native'/(digest(row['id'])+'.json');raw=path.read_bytes()
    expect(hashlib.sha256(raw).hexdigest()==row['native_receipt_sha256'],'Retry-After native receipt hash drift')
    receipt=json.loads(raw);headers=receipt.get('headers',{})
    values=[v for k,v in headers.items() if k.lower()=='retry-after']
    if not values:return 0
    expect(len(values)==1,'Multiple Retry-After metadata values')
    text=str(values[0]).strip()
    try:delay=float(Decimal(text))
    except Exception:
        try:
            target=parsedate_to_datetime(text)
            if target.tzinfo is None:target=target.replace(tzinfo=timezone.utc)
            dates=[v for k,v in headers.items() if k.lower()=='date']
            anchor=None
            if len(dates)==1:
                try:
                    received=parsedate_to_datetime(str(dates[0]))
                    if received.tzinfo is None:received=received.replace(tzinfo=timezone.utc)
                    anchor=received.timestamp()
                except Exception:pass
            if anchor is None:
                finishes=[e['epoch'] for e in rows(out/'dispatch-events.jsonl')
                          if e.get('event')=='client_transport_finish' and e.get('id')==row['id']]
                anchor=finishes[-1] if finishes else fallback_epoch
            expect(anchor is not None,'Historical Retry-After receive timestamp unavailable')
            delay=max(0,target.timestamp()-anchor)
        except (TypeError,ValueError,OverflowError):raise ValueError('Invalid historical Retry-After metadata') from None
    expect(0<=delay<=config()['retry_after_limit_seconds'],'Historical Retry-After outside registered bound')
    return delay


def _sum_cost(paths,provider):
    return sum((Decimal(r['estimated_cost']) for p in paths for r in rows(p) if profile(r['profile_id'])['provider']==provider),Decimal(0))


class PacedTransport(s.Transport):
    """One-second client dispatch gate; no assertion about server arrival time."""
    def __init__(self,keys,out,opener=None):
        super().__init__(keys,out,opener)
        self.native_lock=threading.Lock();self.event_lock=threading.Lock()
        self.gap=config()['native_dispatch_spacing_seconds']
    def event(self,value):
        with self.event_lock:durable(self.out/'dispatch-events.jsonl',value)
    def request(self,j):
        provider=profile(j['profile_id'])['provider']
        capacity_cooldown()
        if provider=='adaption':
            with self.native_lock:
                capacity_cooldown()
                checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/native-dispatch-private.json')
                if checkpoint.exists():
                    last=read(checkpoint)['epoch'];expect(type(last) in (int,float),'Native dispatch clock metadata')
                    expect(last<=time.time()+60,'Native dispatch clock continuity unknown')
                    deadline=time.monotonic()+max(0,last+self.gap-time.time())
                    while time.monotonic()<deadline:time.sleep(min(.25,deadline-time.monotonic()))
                epoch=time.time();stamp=now()
                self.event({'event':'client_transport_dispatch','id':j['id'],'provider':provider,'when':stamp,'epoch':epoch})
                checkpoint.parent.mkdir(parents=True,exist_ok=True)
                s.atomic_metadata(checkpoint,{'epoch':epoch})
        else:self.event({'event':'client_transport_dispatch','id':j['id'],'provider':provider,'when':now(),'epoch':time.time()})
        try:result=super().request(j)
        except Exception as error:
            self.event({'event':'client_transport_exception','id':j['id'],'provider':provider,'when':now(),'error_class':type(error).__name__})
            raise
        self.event({'event':'client_transport_finish','id':j['id'],'provider':provider,'when':now(),'epoch':time.time()})
        return result


def check_metadata(transport):return s.check_metadata(transport)


def _execute(jobs,split,phase,transport=None):
    """Durable reservations precede sends; terminal failures are never retried."""
    registration(split);out=folder(split)/phase;c=execution_config(split,phase);ordered=sorted(jobs,key=lambda j:j['id'])
    # A fatal or unresolved send in another phase cannot be bypassed by starting
    # a different phase and dropping its outstanding financial reservation.
    for attempts in ROOT.glob('runs/'+c['study_id']+'-*/*/attempts.jsonl'):
        phase_out=attempts.parent
        if phase_out==out:continue
        started=rows(attempts);terminal=rows(phase_out/'responses.jsonl')
        expect(len({x['id'] for x in started})==len(started) and len({x['id'] for x in terminal})==len(terminal),'Other phase duplicate journal')
        expect({x['id'] for x in started}=={x['id'] for x in terminal},'Other phase unresolved send blocks the whole study')
        expect(not (phase_out/'stop.json').exists() or (False),'Other phase fatal stop requires prospective operational amendment')
    plan={'jobs_sha256':digest(ordered),'ids':[j['id'] for j in ordered],'freeze_sha256':sha(freeze_path(split))}
    expect(len(plan['ids'])==len(set(plan['ids'])),'Duplicate planned request')
    with exclusive(out):
        if (out/'plan.json').exists():expect(read(out/'plan.json')==plan,'Phase plan drift')
        else:
            with (out/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f);f.flush();os.fsync(f.fileno())
        starts,results=ledger(out,ordered);done={x['id'] for x in starts};pending=[j for j in ordered if j['id'] not in done]
        expect(not (out/'stop.json').exists(),'Phase previously stopped: a prospective operational amendment is required')
        backoff_not_before=0
        def stop(reason):
            path=out/'stop.json'
            if not path.exists():
                with path.open('x',encoding='utf-8') as f:
                    json.dump({'reason':reason,'stopped':now(),'freeze_sha256':sha(freeze_path(split)),
                               'retry_after_not_before_epoch':backoff_not_before},f);f.flush();os.fsync(f.fileno())
        transport=transport or PacedTransport(s.credentials(),out)
        def recheck():
            try:
                s.check_config_file();expect(sha(CONFIG)==c['_operational_config_sha256'],'Operational config drift');check_metadata(transport)
            except Exception:
                if (out/'attempts.jsonl').exists():stop('metadata_integrity')
                raise
        recheck();balance=BalanceGuard(transport,split)
        spent={p:Decimal(0) for p in ('adaption','hf','ollama')}
        baseline=verify_pilot_history()
        combined={p:Decimal(baseline['estimated_cost_by_provider'][p]) for p in spent};native_classes={'actors':Decimal(0),'readers':Decimal(0)}
        for previous in ROOT.glob('runs/'+c['study_id']+'-*/*/responses.jsonl'):
            for row in rows(previous):
                provider=profile(row['profile_id'])['provider'];amount=Decimal(row['estimated_cost']);combined[provider]+=amount
                if provider=='adaption' and previous.parent.parent.name==c['study_id']+'-main':native_classes['readers' if row['metadata'].get('procedure') else 'actors']+=amount
        for previous in folder(split).glob('*/responses.jsonl'):
            for row in rows(previous):spent[profile(row['profile_id'])['provider']]+=Decimal(row['estimated_cost'])
        active={};reserved={p:Decimal(0) for p in spent};per_model={};failures=sum(r['transport'].get('http_status') in (502,503,504) or r['transport'].get('service_overload',False) for r in results);cooldown=0;since_check=0
        if failures:cooldown=time.monotonic()+c['gateway_backoff_seconds']
        expect(failures<=c['gateway_allowance'],'Historical gateway allowance exhausted')
        def capture_failure(j,error):
            # Never expose exception text: provider libraries may include URLs,
            # headers or body fragments. Keep the start unresolved and reserved.
            durable(out/'capture-failures.jsonl',{'id':j['id'],'error_class':type(error).__name__})
        def drain():
            for future,j in list(active.items()):
                try:
                    row=apply_host_action(future.result());cost=actual_cost(j,row['response']) if row['known_usage'] else reservation(j)
                    row['estimated_cost']=str(cost);durable(out/'responses.jsonl',row)
                except Exception as error:capture_failure(j,error)
            active.clear()
        with ThreadPoolExecutor(max_workers=c['max_active']) as pool:
            while pending or active:
                if (out/'STOP').exists():pending=[]
                for j in list(pending):
                    if len(active)>=c['max_active'] or time.monotonic()<cooldown or since_check>=c['metadata_recheck_calls']:break
                    p=profile(j['profile_id']);provider=p['provider'];key=(provider,p['model'])
                    limit=c['provider_max_active'][provider]
                    if sum(profile(v['profile_id'])['provider']==provider for v in active.values())>=limit or per_model.get(key,0)>=c['dispatch_model_limits'][provider]:continue
                    amount=reservation(j);cap=Decimal(c['phase_caps'][split][provider])
                    try:
                        dispatch_time_gate(split)
                        expect(spent[provider]+reserved[provider]+amount<=cap,'Provider split cost cap reached')
                        expect(combined[provider]+reserved[provider]+amount<=Decimal(c['combined_caps'][provider]),'Combined provider cap reached')
                        if provider=='adaption' and split=='main':
                            category='readers' if j['metadata'].get('procedure') else 'actors'
                            expect(native_classes[category]+reserved[provider]+amount<=Decimal(c['native_class_caps'][category]),'Native class cap reached')
                        if provider=='ollama':balance.check(combined[provider],reserved[provider]+amount)
                    except Exception as error:
                        drain();stop('budget_or_credit_guard');raise
                    durable(out/'attempts.jsonl',dict(id=j['id'],profile_id=j['profile_id'],request_sha256=digest(body_for(j)),reserved_cost=str(amount),started=now()))
                    reserved[provider]+=amount;per_model[key]=per_model.get(key,0)+1
                    active[pool.submit(transport.request,j)]=j;pending.remove(j)
                if not active:
                    if since_check>=c['metadata_recheck_calls']:recheck();since_check=0
                    elif pending:time.sleep(min(1,max(.01,cooldown-time.monotonic())))
                    continue
                completed,_=wait(active,return_when=FIRST_COMPLETED)
                fatal=False;fatal_reason='provider_or_capture_integrity'
                for future in completed:
                    j=active.pop(future);p=profile(j['profile_id']);provider=p['provider'];key=(provider,p['model']);per_model[key]-=1
                    amount=reservation(j);reserved[provider]-=amount
                    try:row=apply_host_action(future.result())
                    except Exception as error:
                        # A sent request may have reached the provider. Keep its start
                        # unresolved; drain other futures, then refuse automatic resume.
                        capture_failure(j,error);fatal=True;continue
                    cost=actual_cost(j,row['response']) if row['known_usage'] else amount
                    row['estimated_cost']=str(cost);durable(out/'responses.jsonl',row);spent[provider]+=cost;combined[provider]+=cost
                    if provider=='adaption' and split=='main':native_classes['readers' if j['metadata'].get('procedure') else 'actors']+=cost
                    since_check+=1
                    http=row['transport'].get('http_status');transient=http in (502,503,504) or (http==429 and row['transport'].get('service_overload'))
                    if transient:
                        failures+=1
                        try:delay=retry_after_delay(row,out)
                        except ValueError:delay=0;fatal=True;fatal_reason='retry_after_invalid_or_excessive'
                        wait_seconds=max(gateway_backoff_seconds(row),delay)
                        cooldown=max(cooldown,time.monotonic()+wait_seconds)
                        backoff_not_before=max(backoff_not_before,time.time()+wait_seconds)
                        persist_cooldown(backoff_not_before)
                    if (not row['known_usage'] and not transient) or row['anomaly'] and row['known_usage'] or failures>c['gateway_allowance'] or http in (401,402,403) or (http==429 and not transient):fatal=True
                if fatal:
                    # Submit no new requests; all already submitted receipts are saved.
                    drain()
                    stop(fatal_reason)
                    raise ValueError('Collector stopped on provider integrity/budget condition; inspect private journals')
                if since_check>=c['metadata_recheck_calls'] and not active:
                    recheck();since_check=0
        _,results=ledger(out,ordered)
        return {'planned':len(ordered),'terminal':len(results),'complete':len(results)==len(ordered)}


def main_jobs(phase):
    contexts=s.contexts('main');record=s.registration('main')
    expect(s.digest(contexts)==record['contexts_sha256'],'Scientific main context drift')
    previous={}
    for role in ('principal','coordinator','x','y','reporter'):
        for row in rows(s.folder('main')/role/'responses.jsonl'):previous[row['id']]=row
    if phase=='readers':return s.reader_jobs(s.source_worlds(contexts,previous))
    if phase=='calibration':return s.reader_jobs(s.calibration_sources())
    if phase=='influence':return s.influence_jobs(contexts,previous)
    return s.actor_jobs(phase,contexts,previous)



def config():
    c=read(CONFIG)
    expect(c['native_per_model']==2 and c['native_provider_max_active']==8 and c['total_max_active']==8,'Fixed native/global capacity differs')
    expect(c['hf_max_active']==c['ollama_max_active']==2,'Fixed matched-family capacity differs')
    expect(c['native_dispatch_spacing_seconds']==1 and c['native_gateway_backoff_seconds']==15 and c['default_gateway_backoff_seconds']==60,'Registered pacing/backoff differs')
    expect(c['main_known_gateway_allowance']==1024 and c['retry_after_limit_seconds']==900 and c['retries']==0,'Finite no-retry error guard differs')
    expect(c['max_ollama_combined_peak_equivalent_cap']=='100.00','Conditional spending bound differs')
    return c

def folder(split):
    expect(split=='main','This amendment has no new development or pilot requests')
    return ROOT/('runs/'+old.config()['study_id']+'-main')

def op_freeze(stage='main'):
    expect(stage=='main','Main-only operational registration')
    return ROOT/('research/'+config()['study_id']+'-main-freeze.json')

def freeze_path(split):
    expect(split=='main','Main-only collection')
    return s.freeze_path('main')

def pilot_spending_paths():
    return sorted({p for module in (previous.v1,previous) for p in (ROOT/('runs/'+module.config()['study_id']+'-pilot')).glob('*/responses.jsonl')})

def pilot_public_metadata():
    previous.verify('pilot')
    baselines=[read(ROOT/name) for name in config()['prior_baselines']]
    totals={p:Decimal(0) for p in ('adaption','hf','ollama')}
    for value,module,n in zip(baselines,(previous.v1,previous),(17,44)):
        registration=module.verify('pilot')
        expect(value['registration_tag']==registration['tag'] and value['registration_sha256']==sha(module.op_freeze('pilot')),'Failed pilot registration drift')
        expect(value['source_sha256']==registration['source_sha256'] and value['started']==value['terminal']==len(value['records'])==n,'Failed pilot source/terminal count drift')
        for provider in totals:
            amount=Decimal(value['estimated_cost_by_provider'][provider]);expect(amount.is_finite() and amount>=0,'Invalid historical cost')
            totals[provider]+=amount
    expect(totals['adaption']==Decimal('0.8143088') and totals['hf']==totals['ollama']==0,'Historical combined spending differs')
    return {'estimated_cost_by_provider':{p:str(v) for p,v in totals.items()},
            'baselines':[{'path':name,'sha256':sha(ROOT/name),'registration_tag':value['registration_tag'],'registration_sha256':value['registration_sha256']} for name,value in zip(config()['prior_baselines'],baselines)]}

def verify_pilot_history():
    """Narrow immutable excluded-pilot proof; no permission to resume either pilot."""
    previous.verify_prior_pilot_private();metadata=pilot_public_metadata()
    value=read(ROOT/config()['prior_baselines'][1]);out=ROOT/('runs/'+previous.config()['study_id']+'-pilot/native4')
    paths={'plan':out/'plan.json','attempts':out/'attempts.jsonl','responses':out/'responses.jsonl','stop':out/'stop.json','dispatch_events':out/'dispatch-events.jsonl',
           'driver_state':ROOT/('runs/'+previous.config()['study_id']+'-pilot-driver/state.json'),
           'recovery_driver_state':ROOT/('runs/'+previous.config()['study_id']+'-pilot-recovery-driver/state.json')}
    for name,path in paths.items():expect(hashlib.sha256(path.read_bytes()).hexdigest()==value['private_file_raw_sha256'][name],'V2 historical private file drift: '+name)
    jobs=previous.phase_jobs('native4');starts,terminal=old.ledger(out,jobs)
    expect(len(starts)==len(terminal)==44 and not rows(out/'capture-failures.jsonl'),'Failed V2 unresolved/capture history')
    expected={'jobs_sha256':digest(sorted(jobs,key=lambda j:j['id'])),'ids':[j['id'] for j in sorted(jobs,key=lambda j:j['id'])],'freeze_sha256':sha(previous.op_freeze('pilot'))}
    expect(read(out/'plan.json')==expected,'Failed V2 request plan drift')
    expect(read(out/'stop.json')['reason']==value['stop_reason']=='provider_or_capture_integrity','Only attested serving stop excepted')
    state=read(paths['driver_state']);expect(state['status']=='stopped','Failed V2 driver resumed')
    process_dead(state['pid'],state['updated']);process_dead(state['child_pid'],state['updated'])
    recovery=read(paths['recovery_driver_state']);expect(recovery['status']=='stopped' and recovery['child_pid']==state['child_pid'],'Historical recovery-driver identity drift')
    process_dead(recovery['pid'],recovery['updated']);process_dead(recovery['child_pid'],recovery['updated'])
    projected=[];costs={p:Decimal(0) for p in ('adaption','hf','ollama')};unknown=0
    for row in terminal:
        transient=known_capacity_error(row)
        expect(previous.serving_healthy(row,out) or transient,'Unclassified failed V2 result')
        if transient:
            expect(row['transport'].get('http_status')==504 and row['known_usage'] is False,'Historical failure class differs')
            unknown+=1
        p=profile(row['profile_id']);costs[p['provider']]+=Decimal(row['estimated_cost'])
        projected.append({'id':row['id'],'profile_id':row['profile_id'],'http_status':row['transport']['http_status'],'known_usage':row['known_usage'],'anomaly':row['anomaly'],
                          'response_status':row['response']['status'],'returned_model':row['response']['returned_model'],'usage':row['response']['usage'],'estimated_cost':row['estimated_cost'],'native_receipt_sha256':row['native_receipt_sha256']})
    expect(projected==value['records'] and unknown==5,'Historical V2 row metadata differs')
    expect(all(costs[p]==Decimal(value['estimated_cost_by_provider'][p]) for p in costs),'Historical V2 spending differs')
    for other in out.parent.iterdir():
        if other.is_dir() and other!=out:expect(not rows(other/'attempts.jsonl') and not rows(other/'responses.jsonl') and not (other/'stop.json').exists(),'Other excluded pilot phase ran')
    return metadata

def registration(split):
    expect(split=='main','Main-only collection')
    return verify('main')

def validate_forecast(value):
    c=config();expect(value['schema_version']==1 and value['safety_multiplier']==1.25 and value['overhead_seconds']==1800,'Forecast safety margins differ')
    expect(value['collection_cutoff_utc']==c['collection_deadline_utc'] and value['main_known_gateway_allowance']==1024,'Forecast deadline/error allowance differs')
    expect(value['development_freeze_sha256']==sha(old.freeze_path('development')),'Forecast engineering anchor differs')
    expect(value['pilot_cost_lineage']==pilot_public_metadata(),'Forecast excluded-pilot spending differs')
    expect(value['science_config_sha256']==digest(s.config()) and value['forecast_source_sha256']==sha(ROOT/'experiments/swarm_ledger_complete_forecast.py'),'Forecast configuration/source drift')
    expect(value['pilot_metadata_sha256']==digest(value['pilot_cost_lineage']),'Forecast pilot metadata commitment drift')
    expect(value['fixed_native_levels']==[2] and value['capacity_pilot_extrapolation_used'] is False and value['accuracy_used_for_selection'] is False,'Capacity/accuracy selection prohibited')
    expect(value['dispatch_limits']=={'native_per_model':2,'native_provider':8,'global_cap':8,'hf':2,'ollama':2,'native_dispatch_interval_seconds':1},'Forecast concurrency differs')
    expect(value['workload']=={'actor_calls_including_influence':9200,'reader_calls_including_calibration':54000,'total_calls':63200,'scientific_main_blocks':640},'Forecast full workload differs')

    generated=datetime.fromisoformat(value['generated_at']);cutoff=datetime.fromisoformat(c['collection_deadline_utc'])
    expect(generated.tzinfo is not None and generated<cutoff,'Forecast clock invalid')
    expect(len(value['candidates'])==1,'Fixed-capacity forecast must have exactly one candidate')
    item=value['candidates'][0];expect(item['native_per_model']==item['ollama_per_model']==2,'Unregistered capacity escalation')
    base=Decimal(str(item['base_seconds']));duration=Decimal(str(item['forecast_seconds']))
    expect(base.is_finite() and base>=0 and duration==base*Decimal('1.25')+1800,'Forecast duration arithmetic')
    phases=item['phase_bounds'];expect(len(phases)==8 and {p['phase'] for p in phases}==set(PHASES),'Forecast phase inventory')
    gate=True
    for phase in phases:
        values=[Decimal(str(phase['projected_known_transient_terminals'][p])) for p in ('adaption','hf','ollama')];total=Decimal(str(phase['projected_known_transient_total']))
        expect(all(x.is_finite() and x>=0 for x in (*values,total)) and total==sum(values,Decimal(0)),'Forecast transient arithmetic')
        gate=gate and total<=1024
    expect(item['gateway_allowance_feasible'] is gate and gate,'Forecast fixed gateway allowance would halt collection')
    clock=generated.timestamp()+float(duration)<cutoff.timestamp();expect(item['deadline_feasible'] is clock and clock,'Full workload does not fit collection deadline')
    science=s.config();combined=Decimal(item['ollama_combined_peak_cap']);engineering=Decimal(science['phase_caps']['technical']['ollama'])+Decimal(science['phase_caps']['development']['ollama'])
    expect(combined in (Decimal(science['combined_caps']['ollama']),Decimal(c['max_ollama_combined_peak_equivalent_cap'])) and Decimal(item['main_ollama_peak_cap'])==combined-engineering,'Forecast scientific spending ceiling differs')
    costs={p:Decimal(str(item['projected_main_peak_costs'][p])) for p in ('adaption','hf','ollama')}
    expect(all(v.is_finite() and v>=0 for v in costs.values()),'Forecast costs invalid')
    actor=Decimal(item['projected_native_actor_peak_cost']);reader=Decimal(item['projected_native_reader_peak_cost'])
    expect(actor.is_finite() and reader.is_finite() and min(actor,reader)>=0 and abs(actor+reader-costs['adaption'])<=Decimal('.000001'),'Forecast native class sum')
    expect(actor<=Decimal(science['native_class_caps']['actors']) and reader<=Decimal(science['native_class_caps']['readers']),'Forecast native class cap')
    expect(costs['adaption']<=Decimal(science['phase_caps']['main']['adaption']) and costs['hf']<=Decimal(science['phase_caps']['main']['hf']) and costs['ollama']<=Decimal(item['main_ollama_peak_cap']),'Forecast main cap exceeded')
    expect(item['off_peak_wallet_gate_passed'] is True,'Fresh full-workload wallet proof required')
    if combined>Decimal(science['combined_caps']['ollama']):expect(c['off_peak_only'] is True and costs['ollama']>Decimal(science['phase_caps']['main']['ollama']),'Unnecessary spending extension')
    return value

def execution_config(split,phase):
    expect(split=='main' and phase in PHASES,'Registered main phase required')
    c=s.config();o=config();choice=validate_forecast(read(FORECAST))['candidates'][0]
    c['max_active']=8;c['provider_max_active']={'adaption':8,'hf':2,'ollama':2};c['dispatch_model_limits']={'adaption':2,'hf':2,'ollama':2};c['gateway_allowance']=1024
    c['combined_caps']['adaption']=str(Decimal(c['combined_caps']['adaption'])+Decimal(o['pilot_caps']['adaption']))
    c['combined_caps']['ollama']=str(Decimal(choice['ollama_combined_peak_cap'])+Decimal(o['pilot_caps']['ollama']))
    c['phase_caps']['main']['ollama']=choice['main_ollama_peak_cap'];c['_operational_config_sha256']=sha(CONFIG)
    return c

class BalanceGuard:
    """Same shared wallet accounting, with explicit local ROOT for isolation."""
    def __init__(self,transport,split):
        expect(split=='main','No new pilot');self.transport=transport;self.last=None;self.available=None;self.at_poll=Decimal(0)
    def check(self,spent,reserved):
        c=s.config()
        if self.last is None or time.monotonic()-self.last>=c['balance_poll_seconds']:
            path=ROOT/('runs/'+c['study_id']+'-guard/balance-private.json')
            cached=read(path) if path.exists() else None
            if cached and 0<=time.time()-cached['epoch']<c['balance_poll_seconds']:
                self.available=Decimal(cached['available']);self.at_poll=Decimal(cached['spent'])
                self.last=time.monotonic()-(time.time()-cached['epoch'])
            else:
                data=self.transport.metadata('https://ollama.com/api/balance','OLLAMA_API_KEY')
                try:self.available=Decimal(str(data['included']['balance_usd']))+Decimal(str(data['purchased']['balance_usd']))
                except (KeyError,TypeError,ArithmeticError):raise ValueError('Ollama balance schema unknown') from None
                expect(self.available.is_finite(),'Nonfinite balance');self.last=time.monotonic();self.at_poll=spent
                path.parent.mkdir(parents=True,exist_ok=True)
                s.atomic_metadata(path,{'epoch':time.time(),'available':str(self.available),'spent':str(spent)})
        expect(self.available-(spent-self.at_poll)-reserved>Decimal(c['remaining_credit_floor']),'Ollama credit floor reached')


def freeze(stage='main'):
    c=config();expect(stage=='main' and c['status']=='READY_FOR_REGISTRATION','Main operational registration remains draft')
    expect(not op_freeze().exists(),'Operational registration exists');s.registration('main')
    forecast=validate_forecast(read(FORECAST));verify_pilot_history()
    expect(time.time()+float(forecast['candidates'][0]['forecast_seconds'])<datetime.fromisoformat(c['collection_deadline_utc']).timestamp(),'Whole workload no longer fits')
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit new operational sources first')
    value={'schema_version':1,'stage':'main','created':now(),'config':c,'source_sha256':{name:sha(ROOT/name) for name in SOURCES},
           'scientific_main_freeze_sha256':sha(s.freeze_path('main')),'forecast_sha256':sha(FORECAST),'pilot_cost_lineage':pilot_public_metadata(),
           'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'tag':c['study_id']+'-main',
           'anchor_hash_semantics':'sha256_bytes_with_crlf_normalized_to_lf'}
    with op_freeze().open('x',encoding='utf-8',newline='\n') as file:json.dump(value,file,indent=2);file.write('\n')
    return {'created':True,'tag':value['tag']}

def verify(stage='main'):
    """Public-only source/registration verification, with no private data or API."""
    expect(stage=='main','Main-only operational registration');value=read(op_freeze());s.registration('main')
    expect(value['config']==config() and value['stage']=='main' and value['source_sha256']=={name:sha(ROOT/name) for name in SOURCES},'Operational source drift')
    expect(value['scientific_main_freeze_sha256']==sha(s.freeze_path('main')) and value['forecast_sha256']==sha(FORECAST),'Operational scientific/forecast anchor drift')
    expect(value['pilot_cost_lineage']==pilot_public_metadata(),'Operational excluded-pilot lineage drift');validate_forecast(read(FORECAST))
    names=[*SOURCES,str(op_freeze().relative_to(ROOT)).replace('\\','/'),str(FORECAST.relative_to(ROOT)).replace('\\','/')]
    for name in names:
        blob=subprocess.check_output(['git','show',value['tag']+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Operational registration tag drift')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],value['tag']+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Operational ancestry drift')
    return value

def execute(jobs,split,phase,transport=None):
    expect(split=='main' and phase in PHASES,'Main-only registered phase')
    with exclusive(ROOT/('runs/'+old.config()['study_id']+'-guard')):
        expected={name:sha(ROOT/name) for name in SOURCES}
        try:
            with s.verified_config():
                verify_pilot_history();capacity_cooldown();return _execute(jobs,split,phase,transport)
        finally:expect(expected=={name:sha(ROOT/name) for name in SOURCES},'Operational source changed during collection')

def run(split,phase):
    expect(split=='main','No new pilot/development collection');jobs=main_jobs(phase);verify('main')
    if not any(old.folder('main').glob('*/attempts.jsonl')):
        duration=validate_forecast(read(FORECAST))['candidates'][0]['forecast_seconds']
        expect(time.time()+float(duration)<datetime.fromisoformat(config()['collection_deadline_utc']).timestamp(),'Whole workload no longer fits cutoff')
    return execute(jobs,'main',phase)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['freeze','verify','run']);parser.add_argument('--split',default='main',choices=['main']);parser.add_argument('--phase')
    args=parser.parse_args();result=run('main',args.phase) if args.command=='run' else (freeze() if args.command=='freeze' else verify())
    print(json.dumps(result))

if __name__=='__main__':main()
