"""Prospective scheduling amendment; frozen scientific sources remain untouched.

All scientific bodies, identities, receipts and scores come from the original
registered module. Only this module's local scheduling settings can differ.
Import/public verification do not load credentials or contact a provider.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import threading
import time

from experiments import swarm_ledger_study as s

ROOT=s.ROOT
CONFIG=ROOT/'research/swarm-ledger-dispatch-config.json'
SELECTION=ROOT/'research/swarm-ledger-dispatch-selection.json'
SOURCES=('experiments/swarm_ledger_dispatch.py','experiments/tests/test_swarm_ledger_dispatch.py',
         'experiments/swarm_ledger_forecast.py','experiments/tests/test_swarm_ledger_forecast.py',
         'research/SWARM_LEDGER_DISPATCH_PROTOCOL.md','research/swarm-ledger-dispatch-config.json',
         'research/SWARM_LEDGER_THROUGHPUT_REVIEW.md')
canonical=s.canonical;digest=s.digest;read=s.read;sha=s.sha;now=s.now;expect=s.expect
profile=s.profile;body_for=s.body_for;reservation=s.reservation;actual_cost=s.actual_cost
rows=s.rows;durable=s.durable;admitted=s.admitted;Transport=s.Transport
apply_host_action=s.apply_host_action;ledger=s.ledger;exclusive=s.exclusive

def config():
    c=read(CONFIG)
    expect(c['native_candidates']==[4,8,16] and c['native_pilot_cases_per_level']==32,'Registered native capacity grid')
    expect(c['minimum_native_admitted_per_profile']==31 and c['native_known_error_allowance_per_group']==2,'Registered native serving-health tolerance')
    expect(c['main_known_gateway_allowance']==1024,'Registered main-only known-gateway allowance')
    expect(c['native_pilot_profiles']==['q397','glm52'],'Registered native capacity profiles')
    expect(c['native_provider_max_active']==16 and c['total_max_active']==21,'Registered concurrency envelope')
    expect(c['hf_max_active']==2 and c['ollama_max_active'] in (2,3),'Provider capacity bound')
    expect(c['retries']==0,'Retries must remain disabled')
    expect(c['native_dispatch_spacing_seconds']==1.0,'Registered native client dispatch spacing')
    expect(c['selection_rule']=='lowest_forecast_native_critical_seconds_healthy_complete','Unknown prospective selection rule')
    return c

def op_freeze(stage):
    expect(stage in ('pilot','main'),'Unknown operational registration')
    return ROOT/('research/'+config()['study_id']+'-'+stage+'-freeze.json')

def folder(split):
    if split=='pilot':return ROOT/('runs/'+config()['study_id']+'-pilot')
    expect(split=='main','Main-only scientific amendment')
    return ROOT/('runs/'+s.config()['study_id']+'-main')

def freeze_path(split):return op_freeze('pilot') if split=='pilot' else s.freeze_path('main')

def process_dead(pid):
    expect(type(pid) is int and pid>0,'Driver process identity unavailable')
    if os.name=='nt':
        command=(f'try {{ Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 }} '
                 'catch { if ($_.CategoryInfo.Category -eq "ObjectNotFound") { exit 3 }; exit 4 }')
        result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True)
        expect(result.returncode==3,'Development process remains active or lookup failed')
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
    process_dead(state.get('pid'));process_dead(state.get('child_pid'))
    from experiments import swarm_ledger_analysis as analysis
    with s.verified_config():coverage,_=analysis.validate_pre_main()
    expected={'technical':10,'development:principal':80,'development:coordinator':80,
              'development:x':320,'development:y':320,'development:reporter':320,'development:readers':256}
    for phase,n in expected.items():
        item=coverage[phase]
        expect(item['planned']==n and item['terminal']==n and item['complete'] is True,'Development/technical serving graph differs')
    return {'complete':True,'coverage':coverage,'driver_state_sha256':sha(state_path)}

def pilot_jobs(level):
    c=config();expect(level in c['native_candidates'],'Unregistered native pilot level')
    out=[];cases=[];rng=random.Random(c['pilot_seed'])
    for i in range(c['native_pilot_cases_per_level']):
        namespace=digest([c['study_id'],'distinct_capacity_case',i])[:32]
        p=dict(namespace=namespace,budget=(2,3,4)[i%3],local_cap_x=2,local_cap_y=2,
               lease_start=123,lease_end=126,target_closed=True,workers=list('ABCDE'))
        route=rng.sample(list('ABCDE'),5)
        w=dict(issued=i%4!=0,gx=True,gy=i%5!=0,dx=i%3,dy=(i//3)%3,
               time_y=126 if i%4==1 else 125,revoked=i%4==2,x_worker=route[2],y_worker=route[3],
               notes=['Neutral bounded capacity-check note. '*2]*5)
        if i in (3,7,11):
            p['budget']={3:3,7:4,11:2}[i]
            w.update(issued=True,gx=True,gy=True,dx=2,dy=1 if i==11 else 2,time_y=125,revoked=False)
        packet=s.engine.observe(p,w,range(16));procedure='direct' if i%2==0 else 'procedure'
        messages=[{'role':'system','content':s.DIRECT if procedure=='direct' else s.PROCEDURE},
                  {'role':'user','content':s.engine.serialize(packet,layout='canonical' if i%2==0 else 'shuffled')}]
        cases.append((i,procedure,messages))
    for identity in c['native_pilot_profiles']:
        for i,procedure,messages in cases:
            out.append(s.job(f"{c['study_id']}:native{level}:{identity}:{i:02d}",identity,deepcopy(messages),
                             {'stage':'dispatch_pilot','capacity_level':level,'case_index':i,'procedure':procedure,'excluded_from_scientific_results':True}))
    return out

def ollama_pilot_jobs():
    c=config();out=[]
    for i in range(c['ollama_pilot_cases']):
        identity='ds_off' if i%2==0 else 'ds_low'
        out.append(s.job(f"{c['study_id']}:ollama3:{i:02d}",identity,
                         [{'role':'system','content':'A neutral technical capacity check. Return a short JSON object about a color.'},
                          {'role':'user','content':canonical({'neutral_words':['blue','green','white']*500})}],
                         {'stage':'dispatch_pilot','capacity_level':3,'case_index':i,'excluded_from_scientific_results':True}))
    return out

def phase_jobs(phase):
    if phase=='ollama3':return ollama_pilot_jobs()
    expect(phase in tuple('native'+str(level) for level in config()['native_candidates']),'Unknown pilot group')
    return pilot_jobs(int(phase[6:]))

def pilot_phase_gate(phase):
    order=config()['pilot_phase_order'];expect(phase in order,'Unregistered pilot phase')
    stopped_native_level=None
    for previous in order[:order.index(phase)]:
        out=folder('pilot')/previous;jobs=phase_jobs(previous)
        starts,terminal=ledger(out,jobs)
        expect(len(starts)==len(terminal),'Unresolved previous pilot phase')
        if stopped_native_level is not None:
            expect(not starts and not terminal,'A stopped lower load cannot be followed by higher-load calls')
            continue
        if (out/'stop.json').exists():
            expect(not phase.startswith('native') and previous.startswith('native') and capacity_failure_allowed(out),'Fatal lower-load pilot stop blocks further ramp')
            stopped_native_level=int(previous[6:])
        else:expect(len(terminal)==len(jobs),'Complete lower-load pilot required before ramp')
    return True

def registration(stage):return verify(stage)

def freeze(stage):
    c=config();expect(c['status']=='READY_FOR_REGISTRATION','Operational config remains draft')
    expect(not op_freeze(stage).exists(),'Operational registration exists')
    s.registration('technical');s.registration('development')
    if stage=='main':
        s.registration('main');verify('pilot');choice=validate_selection(read(SELECTION));pilot_integrity(choice)
        duration=next(r['forecast']['forecast_seconds'] for r in choice['native_candidates'] if r['level']==choice['selected_native_per_model'])
        expect(time.time()+float(duration)<datetime.fromisoformat(c['collection_deadline_utc']).timestamp(),'Complete main workload no longer fits the collection window')
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit operational sources before registration')
    value=dict(schema_version=1,stage=stage,created=now(),config=c,
               anchor_hash_semantics='sha256_bytes_with_crlf_normalized_to_lf',source_sha256={p:sha(ROOT/p) for p in SOURCES},
               scientific_technical_freeze_sha256=sha(s.freeze_path('technical')),
               scientific_development_freeze_sha256=sha(s.freeze_path('development')),
               scientific_source_sha256=read(s.freeze_path('development'))['source_sha256'],
               base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),tag=c['study_id']+'-'+stage)
    if stage=='pilot':
        value['pilot_jobs']={phase:[{'id':j['id'],'request_sha256':digest(body_for(j))} for j in phase_jobs(phase)] for phase in c['pilot_phase_order']}
    else:value.update(scientific_main_freeze_sha256=sha(s.freeze_path('main')),selection_sha256=sha(SELECTION),pilot_freeze_sha256=sha(op_freeze('pilot')))
    with op_freeze(stage).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    return {'created':True,'tag':value['tag'],'stage':stage}

def verify(stage):
    """Public-only verification: no keys, private journals or provider requests."""
    c=config();value=read(op_freeze(stage))
    expect(value['anchor_hash_semantics']=='sha256_bytes_with_crlf_normalized_to_lf','Operational anchor hash semantics drift')
    s.registration('technical');s.registration('development')
    if stage=='main':s.registration('main')
    expect(value['stage']==stage and value['config']==c and value['source_sha256']=={p:sha(ROOT/p) for p in SOURCES},'Operational source drift')
    expect(value['scientific_technical_freeze_sha256']==sha(s.freeze_path('technical')) and value['scientific_development_freeze_sha256']==sha(s.freeze_path('development')),'Scientific anchor drift')
    expect(value['scientific_source_sha256']==read(s.freeze_path('development'))['source_sha256'],'Scientific source commitment drift')
    for name,expected in value['scientific_source_sha256'].items():expect(sha(ROOT/name)==expected,'Frozen scientific source changed')
    paths=list(SOURCES)+[str(op_freeze(stage).relative_to(ROOT)).replace('\\','/')]
    if stage=='main':
        expect(value['scientific_main_freeze_sha256']==sha(s.freeze_path('main')) and value['selection_sha256']==sha(SELECTION) and value['pilot_freeze_sha256']==sha(op_freeze('pilot')),'Main operational anchor drift')
        paths.append(str(SELECTION.relative_to(ROOT)).replace('\\','/'));validate_selection(read(SELECTION))
    for name in paths:
        blob=subprocess.check_output(['git','show',value['tag']+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Operational tag drift')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],value['tag']+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Operational ancestry drift')
    return value

def validate_selection(value):
    c=config();expect(value['selected_native_per_model'] in c['native_candidates'],'Native selection unavailable')
    expect(value['selected_ollama_per_model'] in (2,3) and value['selected_ollama_per_model']<=c['ollama_max_active'],'Ollama selection bound')
    candidates=value['native_candidates'];eligible=[r for r in candidates if r['eligible'] and r.get('deadline_feasible') is True]
    expect(eligible,'No admissible native capacity candidate')
    selected=min(eligible,key=lambda x:(Decimal(str(x['forecast']['native_critical_seconds'])),x['level']))
    expect(selected['level']==value['selected_native_per_model'],'Prospective throughput selection drift')
    combined=Decimal(value['ollama_combined_peak_cap']);base=s.config()
    expect(combined in (Decimal(base['combined_caps']['ollama']),Decimal(c['max_ollama_combined_peak_equivalent_cap'])),'Unregistered Ollama cap selection')
    engineering=Decimal(base['phase_caps']['technical']['ollama'])+Decimal(base['phase_caps']['development']['ollama'])
    expect(Decimal(value['main_ollama_peak_cap'])==combined-engineering,'Main/combined Ollama cap mismatch')
    expect(value['accuracy_used_for_selection'] is False,'Accuracy-based capacity selection prohibited')
    forecast=validate_forecast(deepcopy(value['forecast']))
    for candidate in candidates:
        if not candidate['eligible']:
            expect(candidate['forecast'] is None and candidate['deadline_feasible'] is False,'Ineligible candidate cannot acquire an invented forecast')
            continue
        matches=[r for r in forecast['candidates'] if r['native_per_model']==candidate['level'] and r['ollama_per_model']==value['selected_ollama_per_model']]
        expect(len(matches)==1 and candidate['forecast']==matches[0] and candidate['deadline_feasible']==matches[0]['deadline_feasible'],'Selection forecast replay drift')
    return value

def event_metrics(out,expected_ids,model_limit,subset=False):
    events=rows(out/'dispatch-events.jsonl')
    if subset:events=[r for r in events if r['id'] in expected_ids]
    dispatch={};finish={}
    for item in events:
        if item['event']=='client_transport_dispatch':
            expect(item['id'] not in dispatch,'Duplicate dispatch event');dispatch[item['id']]=item['epoch']
        elif item['event']=='client_transport_finish':
            expect(item['id'] not in finish,'Duplicate finish event');finish[item['id']]=item['epoch']
    complete=set(dispatch)==set(finish)==set(expected_ids)
    peak=0;active=0
    for _,change in sorted([(v,1) for v in dispatch.values()]+[(v,-1) for v in finish.values()],key=lambda x:(x[0],x[1])):
        active+=change;peak=max(peak,active);expect(active>=0,'Finish precedes dispatch')
    expect(peak<=model_limit,'Observed client concurrency exceeds prospective limit')
    native=[e['epoch'] for e in events if e['event']=='client_transport_dispatch' and e['provider']=='adaption']
    expect(all(b-a>=config()['native_dispatch_spacing_seconds']-.001 for a,b in zip(native,native[1:])),'Native client dispatch spacing violated')
    elapsed=max(finish.values())-min(dispatch.values()) if complete and finish else None
    return {'complete':complete,'peak_client_concurrency':peak,'elapsed_seconds':elapsed,
            'dispatch_events_sha256':sha(out/'dispatch-events.jsonl') if events else None}

def known_capacity_error(row):
    http=row['transport'].get('http_status')
    return http in (502,503,504) or (http==429 and row['transport'].get('service_overload') is True)

def native_health(jobs,terminal):
    c=config();summary={};good=len(terminal)==len(jobs)
    for identity in c['native_pilot_profiles']:
        assigned={j['id'] for j in jobs if j['profile_id']==identity}
        observed=[r for r in terminal if r['id'] in assigned]
        healthy=sum(admitted(r) for r in observed);errors=sum(known_capacity_error(r) for r in observed)
        summary[identity]={'planned':len(assigned),'terminal':len(observed),'admitted':healthy,'known_capacity_errors':errors}
        good=good and len(observed)==len(assigned) and healthy>=c['minimum_native_admitted_per_profile'] and errors<=1
        good=good and all(admitted(r) or known_capacity_error(r) for r in observed)
    return good,summary

def pilot_metadata():
    """Private serving replay for the forecaster; no answers or accuracy returned."""
    verify('pilot');pilot_phase_gate('ollama3');c=config();candidates=[]
    for level in c['native_candidates']:
        phase='native'+str(level);out=folder('pilot')/phase;jobs=phase_jobs(phase)
        starts,terminal=ledger(out,jobs);expected={j['id'] for j in jobs}
        expect(not (out/'stop.json').exists() or capacity_failure_allowed(out),'Pilot stopped for a non-capacity integrity condition')
        expect({r['id'] for r in terminal}<=expected,'Pilot identity drift')
        metrics=event_metrics(out,expected,min(config()['native_provider_max_active'],level*len(config()['native_pilot_profiles'])))
        per_profile={}
        for identity in config()['native_pilot_profiles']:
            ids={j['id'] for j in jobs if j['profile_id']==identity}
            item=event_metrics(out,ids,level,subset=True)
            item['requests_per_second']=len(ids)/item['elapsed_seconds'] if item['complete'] and item['elapsed_seconds'] else 0
            per_profile[identity]=item
        healthy,health=native_health(jobs,terminal)
        for identity in per_profile:
            per_profile[identity].update(health[identity])
            observed=[r for r in terminal if r['profile_id']==identity]
            errors=[r for r in observed if known_capacity_error(r)]
            per_profile[identity]['known_transient_count']=len(errors)
            per_profile[identity]['known_transient_rate']=str(Decimal(len(errors))/len(observed)) if observed else None
            per_profile[identity]['max_retry_after_seconds']=max((retry_after_metadata_delay(r,out) for r in errors),default=0)
        eligible=healthy and metrics['complete'] and all(v['complete'] for v in per_profile.values())
        elapsed=metrics['elapsed_seconds']
        throughput=len(terminal)/elapsed if eligible and elapsed and elapsed>0 else 0
        candidates.append({'level':level,'planned':len(jobs),'started':len(starts),'terminal':len(terminal),'eligible':eligible,
                           'elapsed_seconds':elapsed,'requests_per_second':throughput,
                           'event_metrics':metrics,
                           'profiles':per_profile,
                           'unstarted_ids':sorted(expected-{r['id'] for r in starts}),
                           'request_hashes':[digest(body_for(j)) for j in jobs],
                           'native_receipt_hashes':[r['native_receipt_sha256'] for r in terminal],
                           'journal_sha256':sha(out/'responses.jsonl') if (out/'responses.jsonl').exists() else None})
    ollama=2
    ollama_summary=None
    if c['ollama_pilot_cases']:
        jobs=ollama_pilot_jobs();_,terminal=ledger(folder('pilot')/'ollama3',jobs)
        out=folder('pilot')/'ollama3'
        expect(not (out/'stop.json').exists() or capacity_failure_allowed(out),'Ollama pilot stopped for a non-capacity integrity condition')
        metrics=event_metrics(out,{j['id'] for j in jobs},3)
        if len(terminal)==len(jobs) and all(admitted(r) for r in terminal) and metrics['complete']:ollama=3
        ollama_summary={'planned':len(jobs),'terminal':len(terminal),'unstarted_ids':sorted({j['id'] for j in jobs}-{r['id'] for r in terminal}),
                        'journal_sha256':sha(out/'responses.jsonl') if terminal else None,'event_metrics':metrics}
    return {'native_candidates':candidates,'selected_ollama_per_model':ollama,'ollama_pilot':ollama_summary}

def select(forecast_path):
    """Serving metadata only: no verdict parsing or accuracy selection."""
    metadata=pilot_metadata();c=config();candidates=metadata['native_candidates']
    ollama=metadata['selected_ollama_per_model'];ollama_summary=metadata['ollama_pilot']
    forecast=validate_forecast(read(forecast_path))
    for candidate in candidates:
        if not candidate['eligible']:
            candidate['forecast']=None;candidate['deadline_feasible']=False
            continue
        matches=[r for r in forecast['candidates'] if r['native_per_model']==candidate['level'] and r['ollama_per_model']==ollama]
        expect(len(matches)==1,'Forecast must cover every native candidate at selected Ollama load')
        candidate['forecast']=matches[0];candidate['deadline_feasible']=matches[0]['deadline_feasible']
    eligible=[r for r in candidates if r['eligible'] and r['deadline_feasible']]
    expect(eligible,'No healthy deadline-feasible native candidate; do not start main')
    best=min(eligible,key=lambda x:(Decimal(str(x['forecast']['native_critical_seconds'])),x['level']))
    value={'schema_version':1,'created':now(),'selection_rule':c['selection_rule'],'pilot_freeze_sha256':sha(op_freeze('pilot')),
           'selected_native_per_model':best['level'],'selected_ollama_per_model':ollama,'native_candidates':candidates,
           'ollama_combined_peak_cap':best['forecast']['ollama_combined_peak_cap'],
           'main_ollama_peak_cap':best['forecast']['main_ollama_peak_cap'],
           'ollama_pilot':ollama_summary,
           'forecast_sha256':sha(forecast_path),'forecast':forecast,'accuracy_used_for_selection':False}
    validate_selection(value)
    with SELECTION.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    return value

def capacity_failure_allowed(out):
    """Only a known higher-load capacity failure can justify a lower load."""
    if out.name not in ('native8','native16','ollama3'):return False
    if read(out/'stop.json').get('reason')!='provider_or_capture_integrity':return False
    if rows(out/'capture-failures.jsonl'):return False
    starts=rows(out/'attempts.jsonl');terminal=rows(out/'responses.jsonl')
    if {r['id'] for r in starts}!={r['id'] for r in terminal}:return False
    failed=False
    for row in terminal:
        http=row['transport'].get('http_status')
        if http==200:
            if not admitted(row):return False
        elif http in (502,503,504) or (http==429 and row['transport'].get('service_overload') is True):failed=True
        else:return False
    return failed

def pilot_integrity(selection):
    """Private pre-dispatch replay; public verify deliberately does not read runs."""
    pilot_phase_gate('ollama3')
    for candidate in selection['native_candidates']:
        phase='native'+str(candidate['level']);out=folder('pilot')/phase
        _,terminal=ledger(out,phase_jobs(phase))
        expect([r['native_receipt_sha256'] for r in terminal]==candidate['native_receipt_hashes'],'Pilot native receipts changed after selection')
        actual=sha(out/'responses.jsonl') if (out/'responses.jsonl').exists() else None
        expect(actual==candidate['journal_sha256'],'Pilot journal changed after selection')
        expect(not (out/'stop.json').exists() or capacity_failure_allowed(out),'Pilot fatal stop cannot be bypassed')
    if config()['ollama_pilot_cases']:
        out=folder('pilot')/'ollama3';ledger(out,ollama_pilot_jobs())
        expect(not (out/'stop.json').exists() or capacity_failure_allowed(out),'Ollama fatal stop cannot be bypassed')
        actual=sha(out/'responses.jsonl') if (out/'responses.jsonl').exists() else None
        expect(actual==selection['ollama_pilot']['journal_sha256'],'Ollama pilot changed after selection')
    return True

def capacity_cooldown():
    until=max((read(path).get('retry_after_not_before_epoch',0) for path in folder('pilot').glob('*/stop.json')),default=0)
    checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
    if checkpoint.exists():until=max(until,read(checkpoint)['not_before_epoch'])
    expect(type(until) in (int,float),'Capacity cooldown clock invalid')
    while time.time()<until:
        dispatch_time_gate('main');time.sleep(min(1,until-time.time()))

def persist_cooldown(until):
    checkpoint=ROOT/('runs/'+s.config()['study_id']+'-guard/dispatch-cooldown-private.json')
    previous=read(checkpoint).get('not_before_epoch',0) if checkpoint.exists() else 0
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    temporary=checkpoint.with_suffix('.tmp')
    with temporary.open('w',encoding='utf-8') as file:
        json.dump({'not_before_epoch':max(previous,until)},file);file.flush();os.fsync(file.fileno())
    temporary.replace(checkpoint)

def validate_forecast(value):
    c=config();expect(value['schema_version']==1 and value['safety_multiplier']==1.25 and value['overhead_seconds']==1800,'Prospective forecast margins')
    expect(value['development_freeze_sha256']==sha(s.freeze_path('development')) and value['pilot_freeze_sha256']==sha(op_freeze('pilot')),'Forecast provenance drift')
    expect(value['collection_cutoff_utc']==c['collection_deadline_utc'],'Forecast cutoff mismatch')
    generated=datetime.fromisoformat(value['generated_at']);cutoff=datetime.fromisoformat(c['collection_deadline_utc'])
    expect(generated.tzinfo is not None and generated<cutoff,'Forecast clock invalid')
    for item in value['candidates']:
        expect(item['native_per_model'] in c['native_candidates'] and item['ollama_per_model'] in (2,3),'Forecast candidate grid')
        base=Decimal(str(item['base_seconds']));duration=Decimal(str(item['forecast_seconds']))
        critical=Decimal(str(item['native_critical_seconds']));expect(critical.is_finite() and 0<=critical<=base,'Native critical-service forecast invalid')
        expect(base.is_finite() and base>=0 and duration.is_finite() and duration==base*Decimal('1.25')+1800,'Forecast margin arithmetic')
        item['deadline_feasible']=generated.timestamp()+float(duration)<cutoff.timestamp()
        combined=Decimal(item['ollama_combined_peak_cap']);science=s.config()
        expect(combined in (Decimal(science['combined_caps']['ollama']),Decimal(c['max_ollama_combined_peak_equivalent_cap'])),'Forecast spending ceiling')
        engineering=Decimal(science['phase_caps']['technical']['ollama'])+Decimal(science['phase_caps']['development']['ollama'])
        expect(Decimal(item['main_ollama_peak_cap'])==combined-engineering,'Forecast main spending ceiling')
        costs={k:Decimal(str(item['projected_main_peak_costs'][k])) for k in ('adaption','hf','ollama')}
        expect(all(v.is_finite() and v>=0 for v in costs.values()),'Forecast cost values')
        actor=Decimal(str(item['projected_native_actor_peak_cost']));reader=Decimal(str(item['projected_native_reader_peak_cost']))
        expect(actor.is_finite() and reader.is_finite() and actor>=0 and reader>=0,'Native class forecast values')
        expect(actor<=Decimal(science['native_class_caps']['actors']) and reader<=Decimal(science['native_class_caps']['readers']),'Native class forecast exceeds cap')
        expect(abs(actor+reader-costs['adaption'])<=Decimal('0.000001'),'Native class forecast sum mismatch')
        expect(costs['adaption']<=Decimal(science['phase_caps']['main']['adaption']) and costs['hf']<=Decimal(science['phase_caps']['main']['hf']),'Forecast exceeds native/HF main cap')
        expect(costs['ollama']<=Decimal(item['main_ollama_peak_cap']),'Forecast exceeds selected Ollama main cap')
        expect(item['off_peak_wallet_gate_passed'] is True,'Off-peak whole-workload wallet gate not established')
        if combined>Decimal(science['combined_caps']['ollama']):
            expect(c['off_peak_only'] is True and costs['ollama']>Decimal(science['phase_caps']['main']['ollama']),'Unnecessary or non-off-peak cap extension')
    return value

def execution_config(split,phase):
    c=s.config();o=config()
    if split=='pilot':
        c['study_id']=o['study_id'];c['phase_caps']={'pilot':o['pilot_caps']};c['combined_caps']=o['pilot_caps']
        c['max_active']=o['total_max_active'];c['provider_max_active']={'adaption':16,'hf':2,'ollama':3}
        c['dispatch_model_limits']={'adaption':int(phase[6:]) if phase.startswith('native') else 8,'hf':2,'ollama':3}
        c['gateway_allowance']=o['native_known_error_allowance_per_group'] if phase.startswith('native') else 0
    else:
        choice=validate_selection(read(SELECTION));c['max_active']=o['total_max_active']
        c['gateway_allowance']=o['main_known_gateway_allowance']
        c['provider_max_active']={'adaption':16,'hf':2,'ollama':choice['selected_ollama_per_model']}
        c['dispatch_model_limits']={'adaption':choice['selected_native_per_model'],'hf':2,'ollama':choice['selected_ollama_per_model']}
        if choice.get('ollama_combined_peak_cap') is not None:
            ceiling=Decimal(choice['ollama_combined_peak_cap']);original=Decimal(c['combined_caps']['ollama'])
            expect(ceiling>=original and o['off_peak_only'] is True,'Conditional peak-equivalent allowance')
            expect(ceiling<=Decimal(o['max_ollama_combined_peak_equivalent_cap']),'Peak-equivalent cap exceeds prospective bound')
            c['combined_caps']['ollama']=str(ceiling)
            c['phase_caps']['main']['ollama']=str(ceiling-Decimal(c['phase_caps']['technical']['ollama'])-Decimal(c['phase_caps']['development']['ollama']))
    c['_operational_config_sha256']=sha(CONFIG)
    return c

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

class BalanceGuard(s.BalanceGuard):
    def __init__(self,transport,split):super().__init__(transport);self.split=split
    def check(self,spent,reserved):
        if self.split=='pilot':paths=ROOT.glob('runs/'+s.config()['study_id']+'-*/*/responses.jsonl')
        else:paths=folder('pilot').glob('*/responses.jsonl')
        return super().check(spent+_sum_cost(paths,'ollama'),reserved)

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
                temporary=checkpoint.with_suffix('.tmp')
                with temporary.open('w',encoding='utf-8') as file:json.dump({'epoch':epoch},file);file.flush();os.fsync(file.fileno())
                temporary.replace(checkpoint)
        else:self.event({'event':'client_transport_dispatch','id':j['id'],'provider':provider,'when':now(),'epoch':time.time()})
        try:result=super().request(j)
        except Exception as error:
            self.event({'event':'client_transport_exception','id':j['id'],'provider':provider,'when':now(),'error_class':type(error).__name__})
            raise
        self.event({'event':'client_transport_finish','id':j['id'],'provider':provider,'when':now(),'epoch':time.time()})
        return result

def check_metadata(transport):return s.check_metadata(transport)

def execute(jobs,split,phase,transport=None):
    # This is deliberately the original scientific guard, never a new parallel
    # collector lock that could race development or its budget reservations.
    with exclusive(ROOT/('runs/'+s.config()['study_id']+'-guard')):
        expected={name:sha(ROOT/name) for name in SOURCES}
        try:
            with s.verified_config():
                if split=='main':pilot_integrity(validate_selection(read(SELECTION)))
                else:pilot_phase_gate(phase)
                capacity_cooldown()
                return _execute(jobs,split,phase,transport)
        finally:expect(expected=={name:sha(ROOT/name) for name in SOURCES},'Operational source changed during collection')

# The collection loop below is a local copy of the registered implementation.
# Scheduling reads execution_config rather than changing scientific globals.

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
        expect(not (phase_out/'stop.json').exists() or (split=='pilot' and capacity_failure_allowed(phase_out)),'Other phase fatal stop requires prospective operational amendment')
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
        combined={p:Decimal(0) for p in spent};native_classes={'actors':Decimal(0),'readers':Decimal(0)}
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
                        cooldown=time.monotonic()+max(c['gateway_backoff_seconds'],delay)
                        backoff_not_before=time.time()+max(c['gateway_backoff_seconds'],delay)
                        persist_cooldown(backoff_not_before)
                    if (not row['known_usage'] and not transient) or row['anomaly'] and row['known_usage'] or failures>c['gateway_allowance'] or http in (401,402,403) or (http==429 and not transient):fatal=True
                    if split=='pilot':
                        if not admitted(row) and not (phase.startswith('native') and transient):fatal=True
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


def run(split,phase,driver_state=None):
    if split=='pilot':
        expect(driver_state is not None,'Explicit completed-development driver state required')
        development_gate(driver_state);pilot_phase_gate(phase);jobs=phase_jobs(phase)
        registered=verify('pilot')['pilot_jobs'][phase]
        expect(registered==[{'id':j['id'],'request_sha256':digest(body_for(j))} for j in jobs],'Pilot request commitment drift')
    else:
        jobs=main_jobs(phase);verify('main')
        if not any(s.folder('main').glob('*/attempts.jsonl')):
            choice=validate_selection(read(SELECTION))
            duration=next(r['forecast']['forecast_seconds'] for r in choice['native_candidates'] if r['level']==choice['selected_native_per_model'])
            expect(time.time()+float(duration)<datetime.fromisoformat(config()['collection_deadline_utc']).timestamp(),'Full main workload no longer fits cutoff')
    return execute(jobs,split,phase)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['freeze','verify','select','run'])
    parser.add_argument('--split',choices=['pilot','main'],required=True)
    parser.add_argument('--phase')
    parser.add_argument('--forecast')
    parser.add_argument('--development-driver-state')
    args=parser.parse_args()
    if args.command=='freeze':value=freeze(args.split)
    elif args.command=='verify':value={'valid':bool(verify(args.split))}
    elif args.command=='select':
        expect(args.forecast is not None,'Metadata-only deadline forecast required')
        value=select(Path(args.forecast))
    else:
        expect(args.phase is not None,'Explicit phase required')
        value=run(args.split,args.phase,args.development_driver_state)
    print(canonical(value))


if __name__=='__main__':main()
