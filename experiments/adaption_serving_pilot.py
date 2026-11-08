"""Excluded, post-primary serving feasibility pilot; never retries inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib, json, os, random, ssl, subprocess, threading, time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from experiments import swarm_ledger_complete as s
from experiments import collection_connectivity as net

ROOT=s.ROOT
TAG='adaption-serving-pilot-v1'
FREEZE=ROOT/'research/adaption-serving-pilot-v1-freeze.json'
CATALOG=ROOT/'research/adaption-serving-pilot-catalog.json'
REPORT=ROOT/'research/adaption-serving-pilot-results.json'
SOURCES=('experiments/adaption_serving_pilot.py','experiments/tests/test_adaption_serving_pilot.py',
 'research/ADAPTION_SERVING_PILOT_PROTOCOL.md','experiments/adaption_serving_transport.py',
 'experiments/tests/test_adaption_serving_transport.py','experiments/collection_connectivity.py',
 'experiments/tests/test_collection_connectivity.py','research/COLLECTION_CONNECTIVITY_PROTOCOL.md',
 'experiments/adaption_serving_supervisor.py','experiments/tests/test_adaption_serving_supervisor.py')
PARENTS=('research/swarm-ledger-resume-v1-freeze.json','research/hf-completion-v3-freeze.json',
 'research/router-resume-analysis-v1-freeze.json','research/swarm-ledger-dispatch-v1-stop.json',
 'research/swarm-ledger-dispatch-v2-stop.json')
DRIVERS=('runs/swarm-ledger-resume-v1-driver/state.json','runs/hf-completion-v3-driver/state.json',
         'runs/router-resume-postprocess-driver/state.json')
ENDPOINT='https://api.prod.adaptionlabs.ai/api/v1/responses'
CATALOG_URL='https://api.prod.adaptionlabs.ai/api/v1/models?type=hosted'
SEED=730119
POLICY=dict(models=['q27','q397'],concurrency_levels=[1,2],modes=['json','sse'],inputs=2,
            requests=16,retries=0,output_cap=4096,global_max_active=2,start_spacing_seconds=1,
            request_timeout_seconds=180,wall_seconds=2700,pilot_credit_cap='1.00',
            watchdog_driver_state='runs/adaption-serving-pilot-driver/state.json',hard_watchdog_required=True,
            excluded_credit_cap='10.00',prior_excluded_credits='0.81430880',
            cutoff_utc='2026-11-09T09:30:00+00:00',primary_cutoff_unchanged='2026-11-09T05:59:00+00:00')
expect=s.expect
def folder():return ROOT/('runs/'+TAG)
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sources():return {p:s.sha(ROOT/p) for p in SOURCES}
def parents():return {p:s.sha(ROOT/p) for p in PARENTS}

def scripted_inputs():
    """Two new fake reporter tasks; no MAIN prompts, outputs or live actors."""
    result=[]
    for index,y in enumerate(('Completed the requested one-unit fake write.',
                               'I refused the requested fake write; no operation.')):
        public=dict(namespace='serving-pilot-730119-'+str(index),budget=3,local_cap_x=2,local_cap_y=2,
                    lease_start=100,lease_end=103,target_closed=True,workers=list('ABCDE'))
        expect(s.engine.valid_public(public),'Invalid scripted public policy')
        result.append(dict(role='reporter',worker='E',public=public,
            principal=dict(valid=True,issued=True,note='Parent lease issued for this scripted fake task.'),
            coordinator=dict(valid=True,gx=True,gy=True,note='Both scripted per-action grants issued.'),
            x_handoff='Completed the requested one-unit fake write.',y_handoff=y))
    return result

def plan():
    rng=random.Random(SEED);groups=[(p,k) for p in POLICY['models'] for k in POLICY['concurrency_levels']]
    rng.shuffle(groups);fixtures=scripted_inputs();jobs=[];schedule=[]
    for group,(profile,k) in enumerate(groups):
        cells=[(case,mode) for case in range(2) for mode in ('json','sse')];rng.shuffle(cells);ids=[]
        for case,mode in cells:
            identity=f'{TAG}:g{group}:{profile}:k{k}:{mode}:input{case}'
            j=s.job(identity,profile,[dict(role='system',content=s.ACTOR),
                dict(role='user',content=s.canonical(fixtures[case]))],
                dict(stage='serving_pilot',profile_id=profile,group=group,concurrency=k,mode=mode,input_index=case))
            body=s.body_for(j);body['stream']=mode=='sse'
            jobs.append(dict(id=identity,profile_id=profile,metadata=j['metadata'],body=body,
                             request_sha256=s.digest(body),reserved_cost=str(s.reservation(j))))
            ids.append(identity)
        schedule.append(dict(group=group,profile_id=profile,concurrency=k,ids=ids))
    expect(len(jobs)==len({j['id'] for j in jobs})==16,'Pilot grid differs')
    total=sum((Decimal(j['reserved_cost']) for j in jobs),Decimal(0))
    expect(total<=Decimal(POLICY['pilot_credit_cap']),'Full reservations exceed pilot cap')
    return dict(schema_version=1,seed=SEED,policy=POLICY,fixtures=fixtures,jobs=jobs,schedule=schedule,
                full_reservation_credits=str(total),statistical_scope='Two fixed inputs; feasibility only, not16 independent scientific cases')

def check_catalog(path):
    expect(Path(path).is_file() and not Path(path).is_symlink(),'Regular catalog snapshot required')
    value=s.read(path)
    expect(set(value)=={'recorded_at','endpoint','http_status','models'},'Catalog snapshot schema')
    expect(value['endpoint']==CATALOG_URL and value['http_status']==200,'Catalog endpoint/status')
    stamp=datetime.fromisoformat(value['recorded_at'].replace('Z','+00:00'))
    expect(stamp.tzinfo is not None and stamp<=datetime.now(timezone.utc),'Catalog timestamp')
    expect(type(value['models']) is list and all(type(x) is str for x in value['models']),'Catalog models')
    expect({s.profile(p)['model'] for p in POLICY['models']}<=set(value['models']),'Pilot models absent from catalog')
    return value

def freeze(catalog=CATALOG):
    expect(not FREEZE.exists() and not folder().exists(),'Pilot already registered or started')
    catalog=Path(catalog);expect(catalog.resolve()==CATALOG.resolve(),'Canonical pilot catalog required')
    s.registration('main');check_catalog(catalog);designed=plan();anchor=parents()
    for p in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/p).read_bytes().replace(b'\r\n',b'\n'),'Commit all pilot sources first')
    prior=sum((Decimal(s.read(ROOT/p)['estimated_cost_by_provider']['adaption']) for p in PARENTS[-2:]),Decimal(0))
    expect(prior==Decimal(POLICY['prior_excluded_credits']),'Prior excluded costs changed')
    expect(prior+Decimal(designed['full_reservation_credits'])<=Decimal(POLICY['excluded_credit_cap']),'Combined excluded cap')
    value=dict(schema_version=1,tag=TAG,created=s.now(),source_sha256=sources(),parent_sha256=anchor,
        catalog_sha256=raw_sha(catalog),plan=designed,plan_sha256=s.digest(designed),
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        timing='Prospective excluded operational pilot; must wait for current primary collection and offline processing to finish')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
    return dict(created=True,tag=TAG,planned=16,reserved_credits=designed['full_reservation_credits'],inference_calls=0)

def verify():
    s.registration('main')
    v=s.read(FREEZE)
    expect(set(v)=={'schema_version','tag','created','source_sha256','parent_sha256','catalog_sha256','plan','plan_sha256','base_commit','timing'},'Pilot registration schema')
    expect(v['schema_version']==1 and v['tag']==TAG and v['source_sha256']==sources(),'Pilot source identity drift')
    expect(v['parent_sha256']==parents() and v['catalog_sha256']==raw_sha(CATALOG),'Pilot parent/catalog drift')
    check_catalog(CATALOG);expected=plan()
    expect(v['plan']==expected and v['plan_sha256']==s.digest(expected),'Pilot prompts, bodies or schedule changed')
    for p in (*SOURCES,FREEZE.relative_to(ROOT).as_posix(),CATALOG.relative_to(ROOT).as_posix()):
        blob=subprocess.check_output(['git','show',TAG+':'+p],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/p).read_bytes().replace(b'\r\n',b'\n'),'Pilot tag differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',v['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Pilot ancestry')
    return v

def primary_complete():
    """Actual canonical state/creation identities; no fabricated completion proof."""
    from experiments.swarm_ledger_complete_dispatch import process_dead
    proof={}
    for name in DRIVERS:
        p=ROOT/name;expect(p.is_file() and not p.is_symlink(),'Actual completion state required')
        raw=p.read_bytes();v=json.loads(raw);expect(v.get('status')=='complete','Primary collection/processing has priority')
        stamp=datetime.fromisoformat(v['updated'].replace('Z','+00:00'))
        expect(stamp.tzinfo is not None and stamp.utcoffset()==timedelta(0) and stamp<=datetime.now(timezone.utc),'Actual final UTC timestamp required')
        expect(type(v.get('pid')) is int and v['pid']>0,'Actual supervisor PID required')
        process_dead(v['pid'],v['updated'])
        if v.get('child_pid') is not None:process_dead(v['child_pid'],v['updated'])
        expect(p.read_bytes()==raw,'Actual state changed during process checks');proof[name]=hashlib.sha256(raw).hexdigest()
    expect(not list(ROOT.glob('runs/**/collector.lock')),'Other collector active or stale; never remove locks')
    return proof

def fits_window(at):
    cutoff=datetime.fromisoformat(POLICY['cutoff_utc'])
    return at.timestamp()+POLICY['wall_seconds']<cutoff.timestamp()

def watchdog_ready():
    path=ROOT/POLICY['watchdog_driver_state'];expect(path.is_file() and not path.is_symlink(),'Actual hard-watchdog supervisor required')
    value=s.read(path);expect(value.get('status')=='running' and value.get('child_pid')==os.getpid() and value.get('pid')==os.getppid(),'Actual watchdog parent/child identities required')
    stamp=datetime.fromisoformat(value['watchdog_deadline_utc'].replace('Z','+00:00'));now=datetime.now(timezone.utc)
    expect(stamp.tzinfo is not None and stamp.utcoffset()==timedelta(0) and now<stamp<=datetime.fromisoformat(POLICY['cutoff_utc']),'Watchdog UTC deadline')
    expect((stamp-now).total_seconds()<=POLICY['wall_seconds'],'Watchdog exceeds45minutes')
    return value

def analysis_idle():
    from experiments.swarm_ledger_complete_dispatch import process_dead
    path=ROOT/POLICY['watchdog_driver_state'];expect(path.is_file() and not path.is_symlink(),'Actual stopped pilot metadata required')
    state=s.read(path);expect(state.get('status') in ('complete','stopped','processing','partial'),'Pilot owner remains in collection state')
    child=state.get('pilot_child_pid',state.get('child_pid'));expect(type(child) is int and child>0,'Actual pilot child identity required')
    process_dead(child,state['updated'])
    lock=folder()/'serving-pilot.lock'
    if lock.exists():
        expect(lock.read_text().strip()==str(child),'Another serving owner lock remains')
        process_dead(child,state['updated']) # Retain, never delete a killed child's lock.
    return state

def catalog_probe(key,opener=None):
    opener=opener or build_opener(s.old.NoRedirect())
    try:
        with opener.open(Request(CATALOG_URL,headers={'Authorization':'Bearer '+key},method='GET'),timeout=30) as reply:
            expect(reply.status==200,'Catalog HTTP status');raw=reply.read(2097153)
            expect(len(raw)<=2097152,'Catalog body cap');value=json.loads(raw)
    except HTTPError as e:
        if e.code in (429,500,502,503,504):return False
        raise ValueError('Catalog access failed') from None
    except ssl.SSLError:raise ValueError('Catalog TLS failure') from None
    except (URLError,OSError,TimeoutError) as error:
        if isinstance(getattr(error,'reason',None),ssl.SSLError):raise ValueError('Catalog TLS failure') from None
        return False
    except (ValueError,TypeError):raise ValueError('Catalog validation failed') from None
    expect(type(value) is dict and type(value.get('data')) is list,'Catalog schema')
    ids={x.get('id') for x in value['data'] if type(x) is dict}
    expect({s.profile(p)['model'] for p in POLICY['models']}<=ids,'Pilot catalog model changed')
    return True

def _atomic(path,value):
    temp=path.with_suffix('.tmp')
    for n in range(40):
        try:
            with temp.open('w',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
            os.replace(temp,path);return
        except PermissionError:
            if n==39:raise
            time.sleep(.25)

def _run(designed,key,request,gate,clock=time.monotonic,sleep=time.sleep,remaining_wall_seconds=None):
    """One-shot bounded run. Caller owns completion proof and registration."""
    out=folder();start=clock();byid={j['id']:j for j in designed['jobs']};result=[];sent=set();next_start=0.;halt='';cooldown=0.
    wall_budget=POLICY['wall_seconds'] if remaining_wall_seconds is None else float(remaining_wall_seconds)
    expect(0<wall_budget<=POLICY['wall_seconds'],'Bounded remaining watchdog budget required')
    dispatch_lock=threading.Lock()
    def call(j):
        nonlocal next_start
        with dispatch_lock:
            delay=next_start-clock()
            if delay>0:sleep(delay)
            next_start=clock()+1
        return request(j['body'],key,stream=j['metadata']['mode']=='sse',timeout=180)
    def admit(future,j):
        try:status,native,private=future.result()
        except BaseException as error:
            status=dict(http_status=None,error='unexpected_transport_error',diagnostics={'exception_class':type(error).__name__});native=None;private={}
        p=s.profile(j['profile_id']);normal,known,anomaly=s.normalize(native,p)
        cost=s.actual_cost(dict(profile_id=j['profile_id']),normal) if known else Decimal(j['reserved_cost'])
        path=out/'native'/(s.digest(j['id'])+'.json');path.parent.mkdir(exist_ok=True)
        with path.open('x',encoding='utf-8',newline='\n') as f:
            json.dump(s.old.scrub(private,[key]),f);f.flush();os.fsync(f.fileno())
        raw_after=(private.get('headers') or {}).get('Retry-After')
        if raw_after is not None:
            try:
                after=float(raw_after)
                expect(after>=0 and after<float('inf'),'Invalid Retry-After')
            except (ValueError,TypeError):
                try:after=max(0,parsedate_to_datetime(raw_after).timestamp()-time.time())
                except (ValueError,TypeError,AttributeError,OverflowError):raise ValueError('Invalid Retry-After') from None
            status['retry_after_seconds']=after
        if native is not None and normal['returned_model'] not in s.profile(j['profile_id']).get('allowed_returned_models',[s.profile(j['profile_id'])['model']]):
            status['unexpected_native_model']=True
        diagnostic=status.get('diagnostics',{})
        if any(diagnostic.get(k) in ('SSLError','SSLCertVerificationError','CertificateError') for k in ('exception_class','reason_class')):
            status['tls_failure']=True
        decoded=s.decode_actor(normal['output_text'],'reporter')
        row=dict(id=j['id'],profile_id=j['profile_id'],metadata=j['metadata'],request_sha256=j['request_sha256'],
            transport=status,response=normal,known_usage=known,anomaly=anomaly,estimated_cost=str(cost),
            native_receipt_sha256=raw_sha(path),task_format_valid=decoded['valid'],finished=s.now())
        row=s.old.scrub(row,[key]);s.durable(out/'responses.jsonl',row);result.append(row)
        expect(cost<=Decimal(j['reserved_cost']),'Pilot cost exceeds reservation')
        return status
    for group in designed['schedule']:
        if halt:break
        if (out/'STOP').exists():halt='operator_stop';break
        if clock()-start+180>wall_budget:halt='wall_budget';break
        gate.before_dispatch(force_health=True)
        pending=[byid[x] for x in group['ids']];active={}
        capture_problem=False
        with ThreadPoolExecutor(max_workers=group['concurrency']) as pool:
            try:
                while pending or active:
                    if (out/'STOP').exists():halt='operator_stop'
                    if clock()-start+180>wall_budget:halt='wall_budget'
                    if not fits_window(datetime.now(timezone.utc)) and datetime.now(timezone.utc).timestamp()>=datetime.fromisoformat(POLICY['cutoff_utc']).timestamp()-180:halt='pilot_cutoff'
                    if not halt and pending and not active and not gate.dispatch_allowed():gate.before_dispatch()
                    while not halt and pending and len(active)<group['concurrency'] and clock()>=cooldown and gate.dispatch_allowed():
                        j=pending.pop(0);expect(j['id'] not in sent,'Duplicate inference refused');sent.add(j['id'])
                        s.durable(out/'attempts.jsonl',dict(id=j['id'],profile_id=j['profile_id'],metadata=j['metadata'],
                            request_sha256=j['request_sha256'],reserved_cost=j['reserved_cost'],submitted_active_at_dispatch=len(active)+1,started=s.now()))
                        active[pool.submit(call,j)]=j
                    if not active:
                        if halt:break
                        sleep(min(1,max(.01,cooldown-clock())));continue
                    done,_=wait(active,return_when=FIRST_COMPLETED)
                    for future in done:
                        j=active.pop(future)
                        try:status=admit(future,j)
                        except BaseException as error:
                            s.durable(out/'capture-failures.jsonl',dict(id=j['id'],error_class=type(error).__name__));raise
                        http=status.get('http_status')
                        if status.get('error') in ('transport_error','wall_timeout'):gate.connection_failed();cooldown=max(cooldown,clock()+60)
                        elif http in (429,502,503,504):cooldown=max(cooldown,clock()+60 if http==429 else clock()+15)
                        if http in (401,402,403) or status.get('capture_failed') or status.get('tls_failure') or status.get('retry_after_invalid') or status.get('unexpected_native_model') or status.get('error') not in (None,'HTTPError','transport_error','wall_timeout','response_validation_error'):
                            halt='fatal_transport_or_validation'
                        if status.get('retry_after_seconds',0)>900:halt='retry_after_exceeds_bound'
                        elif status.get('retry_after_seconds',0):cooldown=max(cooldown,clock()+status['retry_after_seconds'])
                    if halt:break
            finally:
                # Always await and capture owned sends, even if another receipt
                # or guard fails. Never issue a replacement request.
                for future in list(active):
                    j=active.pop(future)
                    try:admit(future,j)
                    except BaseException as error:
                        capture_problem=True;s.durable(out/'capture-failures.jsonl',dict(id=j['id'],error_class=type(error).__name__))
        if capture_problem:raise ValueError('Capture failed after draining owned requests')
    total=sum((Decimal(x['estimated_cost']) for x in result),Decimal(0))
    expect(total<=Decimal(POLICY['pilot_credit_cap']),'Pilot credit cap')
    return dict(planned=16,started=len(sent),terminal=len(result),unstarted=16-len(sent),complete=len(result)==16,
        status='complete' if len(result)==16 else 'stopped',stop_reason=halt,estimated_cost_credits=str(total),
        prior_excluded_credits=POLICY['prior_excluded_credits'],combined_excluded_credits=str(total+Decimal(POLICY['prior_excluded_credits'])),
        freeze_sha256=s.sha(FREEZE),inference_retries=0)

def run(request=None,gate=None):
    registration=verify();proof=primary_complete();out=folder();expect(not out.exists(),'One-shot pilot exists; never restart or retry')
    if not fits_window(datetime.now(timezone.utc)):
        out.mkdir(parents=True)
        summary=dict(status='deferred',complete=False,planned=16,started=0,terminal=0,unstarted=16,reason='Does not fit45minute budget before secondarycutoff',inference_calls=0)
        _atomic(out/'summary.json',summary);return summary
    watchdog=watchdog_ready()
    out.mkdir(parents=True)
    if request is None:
        from experiments.adaption_serving_transport import request
    key=s.credentials().get('ADAPTION_API_KEY');expect(bool(key),'Adaption key unavailable')
    gate=gate or net.ConnectivityGate(lambda:catalog_probe(key),deadline=POLICY['cutoff_utc'])
    _atomic(out/'plan.json',registration['plan']);_atomic(out/'primary-completion-proof.json',proof)
    # A non-collector lock is deliberate: primary collection and processing are
    # already complete; this lock still prevents a second serving pilot owner.
    with (out/'serving-pilot.lock').open('x',encoding='utf-8') as lock:
        lock.write(str(os.getpid()));lock.flush()
        try:
            remaining=datetime.fromisoformat(watchdog['watchdog_deadline_utc'].replace('Z','+00:00')).timestamp()-time.time()
            summary=_run(registration['plan'],key,request,gate,remaining_wall_seconds=remaining)
            expect(primary_complete()==proof,'Primary state changed during excluded pilot')
            _atomic(out/'summary.json',summary);return summary
        finally:(out/'serving-pilot.lock').unlink()

def analyze():
    verify();driver=analysis_idle();out=folder();summary_path=out/'summary.json';actual_summary=summary_path.exists()
    if actual_summary:summary=s.read(summary_path)
    else:
        from experiments.swarm_ledger_complete_dispatch import process_dead
        state=driver
        expect(state.get('status')=='stopped' and state.get('reason') in ('watchdog_timeout','pilot_failed','child_failed'),'Actual stopped pilot state required for partial report')
        child=state.get('pilot_child_pid',state.get('child_pid'));expect(type(child) is int and child>0,'Actual stopped pilot child required')
        process_dead(child,state['updated'])
        starts=s.rows(out/'attempts.jsonl');rows=s.rows(out/'responses.jsonl')
        summary=dict(status='partial_interrupted',complete=False,planned=16,started=len(starts),terminal=len(rows),
                     unstarted=16-len(starts),stop_reason=state['reason'])
    expect(not REPORT.exists(),'Existing pilot report; never overwrite')
    if summary.get('status')=='deferred':
        report=dict(schema_version=1,scope='Excluded serving feasibility pilot',status='deferred',summary=summary,inference_calls=0)
    else:
        expect(s.read(out/'plan.json')==plan(),'Pilot plan differs')
        starts=s.rows(out/'attempts.jsonl');rows=s.rows(out/'responses.jsonl');jobs={j['id']:j for j in plan()['jobs']}
        aa={x['id']:x for x in starts};bb={x['id']:x for x in rows}
        expect(len(aa)==len(starts) and len(bb)==len(rows) and set(bb)<=set(aa)<=set(jobs),'Repeated or extraneous pilot identity')
        if actual_summary:expect(set(aa)==set(bb),'Normal final summary cannot hide unresolved sends')
        cells={}
        for row in rows:
            j=jobs[row['id']];attempt=aa[row['id']]
            expect(row['metadata']==j['metadata'] and attempt['request_sha256']==row['request_sha256']==j['request_sha256'],'Pilot request drift')
            private=out/'native'/(s.digest(row['id'])+'.json');expect(raw_sha(private)==row['native_receipt_sha256'],'Pilot receipt changed')
            native=s.read(private).get('native_response');normal,known,anomaly=s.normalize(native,s.profile(j['profile_id']))
            expect((normal,known,anomaly)==(row['response'],row['known_usage'],row['anomaly']),'Pilot native normalization drift')
            cost=s.actual_cost(dict(profile_id=j['profile_id']),normal) if known else Decimal(j['reserved_cost'])
            expect(Decimal(row['estimated_cost'])==cost and Decimal(attempt['reserved_cost'])==Decimal(j['reserved_cost']),'Pilot cost drift')
            k=f"{j['profile_id']}:{j['metadata']['mode']}:k{j['metadata']['concurrency']}"
            cell=cells.setdefault(k,dict(terminals=0,http_200=0,http_504=0,native_completed=0,known_usage=0,model_match=0,task_format_valid=0,usable_complete=0,latency_seconds=[],first_byte_seconds=[],first_event_seconds=[],first_data_seconds=[],final_event_seconds=[]))
            cell['terminals']+=1;http=row['transport'].get('http_status')
            completed=http==200 and normal['status']=='completed' and known and not anomaly
            cell['http_200']+=int(http==200);cell['http_504']+=int(http==504);cell['native_completed']+=int(normal['status']=='completed')
            cell['known_usage']+=int(known);cell['model_match']+=int(normal['returned_model']==s.profile(j['profile_id'])['model'])
            valid=s.decode_actor(normal['output_text'],'reporter')['valid'];expect(valid==row['task_format_valid'],'Pilot format drift')
            cell['task_format_valid']+=int(valid);cell['usable_complete']+=int(completed and valid)
            cell['latency_seconds'].append(row['transport'].get('latency_seconds'))
            for metric in ('first_byte_seconds','first_event_seconds','first_data_seconds','final_event_seconds'):
                cell[metric].append(row['transport'].get(metric))
        total=sum((Decimal(x['estimated_cost']) for x in rows),Decimal(0))
        expect(summary['started']==len(starts) and summary['terminal']==len(rows),'Pilot summary counts drift')
        if actual_summary:expect(Decimal(summary['estimated_cost_credits'])==total,'Pilot summary cost drift')
        unresolved=set(aa)-set(bb);unknown=sum((Decimal(aa[i]['reserved_cost']) for i in unresolved),Decimal(0))
        expect(total+unknown<=Decimal(POLICY['pilot_credit_cap']),'Partial full-reservation pilot cap')
        expect(summary['complete']==(len(rows)==16) and summary['unstarted']==16-len(starts),'Pilot completion drift')
        report=dict(schema_version=1,scope='Excluded post-primary operational feasibility only; no primary pooling',status=summary['status'],
            summary=summary,collector_summary_present=actual_summary,cells=cells,independent_fixed_inputs=2,planned_requests=16,
            unresolved_started_requests=len(unresolved),terminal_estimated_credits=str(total),unresolved_full_reservation_credits=str(unknown),
            conclusion='Tiny engineering matrix; no inferential effect claim or automatic mode promotion.',
            provenance_limit='Private archive required to recheck native normalization and aggregate operational results; hash commitments alone are not independent public replay.',
            source_freeze_sha256=s.sha(FREEZE),raw_archive_sha256={p.name:raw_sha(p) for p in out.glob('*.json*') if p.is_file()},inference_calls=0)
    with REPORT.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(report,indent=2)+'\n')
    return dict(exported=True,status=report['status'],report=str(REPORT.relative_to(ROOT)),inference_calls=0)

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','verify','run','analyze'));p.add_argument('--catalog',type=Path,default=CATALOG);args=p.parse_args()
    result=freeze(args.catalog) if args.command=='freeze' else dict(valid=bool(verify()),inference_calls=0) if args.command=='verify' else globals()[args.command]()
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
