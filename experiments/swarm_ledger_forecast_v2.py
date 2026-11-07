"""V2 pre-MAIN resource forecast; preserved v1 pilot history is not reset.

No answers, action deltas, accuracy or account amounts enter the forecast.
The CLI validates finished DEV/pilot receipts before one shared-cache wallet
check. Import and pure build never load keys or contact a provider.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from experiments import swarm_ledger_study as s

CUTOFF='2026-11-09T05:59:00+00:00'
PHASES=('principal','coordinator','x','y','reporter','readers','calibration','influence')
ACTOR_COUNTS={'principal':160,'coordinator':160,'x':640,'y':640,'reporter':640,'influence':60}
DEV_COUNTS={'principal':20,'coordinator':20,'x':80,'y':80,'reporter':80}
SAFETY=Decimal('1.25');OVERHEAD=Decimal(1800)


def expect(ok,message):
    if not ok:raise ValueError(message)

def number(value,label):
    try:result=Decimal(str(value))
    except Exception:raise ValueError('Invalid '+label) from None
    expect(result.is_finite() and result>=0,'Invalid '+label);return result

def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def utc(value):
    at=datetime.fromisoformat(value) if isinstance(value,str) else value
    expect(isinstance(at,datetime) and at.tzinfo is not None,'Timezone-aware forecast time required')
    return at.astimezone(timezone.utc)

def off_peak_window(start,end):
    """Official pricing: weekends, or outside weekday 12:00–18:00 UTC."""
    expect(start<=end and end-start<=timedelta(days=7),'Forecast collection window invalid')
    def allowed(at):return at.weekday()>=5 or at.hour<12 or at.hour>=18
    if not allowed(start) or not allowed(end):return False
    cursor=start.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
    while cursor<end:
        if not allowed(cursor):return False
        cursor+=timedelta(hours=1)
    return True


def known_transient(row):
    code=row['transport'].get('http_status')
    return code in (502,503,504) or code==429 and row['transport'].get('service_overload') is True


def transient_classes(items,retry_after_by_id=None):
    result={}
    for kind in ('gateway_5xx','overload_429'):
        selected=[r for r in items if known_transient(r) and
                  (r['transport']['http_status'] in (502,503,504))==(kind=='gateway_5xx')]
        waits=[number((retry_after_by_id or {}).get(r.get('id'),0),'Retry-After') for r in selected]
        expect(all(v<=900 for v in waits),'Retry-After exceeds registered wait envelope')
        result[kind]=dict(count=len(selected),rate=str(Decimal(len(selected))/len(items)),
                          max_retry_after_seconds=str(max(waits,default=Decimal(0))))
    return result


def validate_classes(observation,n=None):
    classes=observation['transient_classes']
    expect(set(classes)=={'gateway_5xx','overload_429'},'Transient class grid differs')
    count=0;rate=Decimal(0);delay=Decimal(0)
    for item in classes.values():
        expect(set(item)=={'count','rate','max_retry_after_seconds'},'Transient class allowlist differs')
        expect(type(item['count']) is int and item['count']>=0,'Transient class count invalid')
        r=number(item['rate'],'transient class rate');d=number(item['max_retry_after_seconds'],'transient class Retry-After')
        expect(r<=1 and d<=900 and (item['count']>0 or r==d==0),'Transient class metadata invalid')
        if n is not None:expect(r==Decimal(item['count'])/n,'Transient class rate/count differs')
        count+=item['count'];rate+=r;delay=max(delay,d)
    expect(count==observation['known_transient_count'] and rate==number(observation['known_transient_rate'],'total transient rate') and
           delay==number(observation['max_retry_after_seconds'],'total Retry-After'),'Transient class totals differ')


def aggregate(rows,phase,retry_after_by_id=None):
    """Read only serving fields; all terminal latencies contribute to the mean."""
    grouped=defaultdict(list)
    for row in rows:grouped[row['profile_id']].append(row)
    out=[]
    for identity,items in sorted(grouped.items()):
        latencies=[number(r['transport'].get('latency_seconds'),'DEV latency') for r in items]
        usages=[]
        for row in items:
            expect(type(row['known_usage']) is bool,'DEV known-usage flag invalid')
            if row['known_usage']:
                usage=row['response']['usage']
                expect(isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0
                       for k in ('input_tokens','output_tokens')),'DEV known usage invalid')
                usages.append(usage)
        expect(usages,'No known DEV usage for a required serving group')
        failures=[r for r in items if known_transient(r)]
        waits=[number((retry_after_by_id or {}).get(r.get('id'),0),'DEV Retry-After') for r in failures]
        expect(all(v<=900 for v in waits),'DEV Retry-After exceeds registered wait envelope')
        out.append(dict(profile_id=identity,phase=phase,count=len(items),known_usage_count=len(usages),
                        unknown_usage_count=len(items)-len(usages),mean_latency_seconds=str(sum(latencies)/len(items)),
                        max_known_input_tokens=max(u['input_tokens'] for u in usages),
                        max_known_output_tokens=max(u['output_tokens'] for u in usages),known_transient_count=len(failures),
                        known_transient_rate=str(Decimal(len(failures))/len(items)),
                        max_retry_after_seconds=str(max(waits,default=Decimal(0))),
                        transient_classes=transient_classes(items,retry_after_by_id)))
    return out


def main_counts(config):
    out=[]
    for p in config['worker_profiles']:
        for phase,count in ACTOR_COUNTS.items():out.append((p,phase,count,'y' if phase=='influence' else phase))
    for p in config['reader_profiles']:
        out.append((p,'readers',5120+(7680 if p in config['auxiliary_reader_profiles'] else 0),'readers'))
        out.append((p,'calibration',40,'readers'))
    expect(sum(n for _,phase,n,_ in out if phase in ACTOR_COUNTS)==9200 and
           sum(n for _,phase,n,_ in out if phase not in ACTOR_COUNTS)==64320,'Fixed MAIN workload differs')
    return out


def effective_error(job,phase,pilot):
    rate=Decimal(0);pause=Decimal(0)
    for kind,item in job['transient_classes'].items():
        r=number(item['rate'],'DEV transient class rate')
        base=Decimal(15 if job['provider']=='adaption' and kind=='gateway_5xx' else 60)
        delay=max(base,number(item['max_retry_after_seconds'],'DEV Retry-After'))
        if phase in ('readers','calibration') and job['profile_id'] in pilot['profiles']:
            observed=pilot['profiles'][job['profile_id']]['transient_classes'][kind]
            r=max(r,number(observed['rate'],'pilot transient class rate'))
            delay=max(delay,number(observed['max_retry_after_seconds'],'pilot Retry-After'))
        rate+=r;pause+=r*delay
    expect(rate<=1,'Component-wise transient rate envelope exceeds one')
    return rate,pause


def pilot_cost_lineage(inputs):
    """Preserve the verified failed v1 pilot's costs inside the common cap."""
    metadata=inputs['pilot_cost_metadata'];expected={'estimated_cost_by_provider','prior_estimated_cost_by_provider',
        'current_estimated_cost_by_provider','prior_registration_tag','prior_registration_sha256',
        'prior_baseline_sha256','prior_private_file_raw_sha256'}
    expect(set(metadata)==expected,'V1/V2 pilot cost metadata allowlist differs')
    expect(metadata['prior_registration_tag']=='swarm-ledger-dispatch-v1-pilot','Prior pilot registration differs')
    for field in ('estimated_cost_by_provider','prior_estimated_cost_by_provider','current_estimated_cost_by_provider'):
        expect(set(metadata[field])=={'adaption','hf','ollama'},'Pilot provider cost grid differs')
    for provider in ('adaption','hf','ollama'):
        previous=number(metadata['prior_estimated_cost_by_provider'][provider],'prior pilot cost')
        current=number(metadata['current_estimated_cost_by_provider'][provider],'current pilot cost')
        total=number(metadata['estimated_cost_by_provider'][provider],'combined pilot cost')
        expect(previous+current==total,'Prior pilot spending omitted or changed')
        expect(total<=number(inputs['pilot_cost_caps'][provider],'combined pilot cap'),'Combined v1/v2 pilot cap exceeded')
    return metadata


def build(inputs,pilot_metrics,generated_at,wallet_available_private):
    """Pure projection. Private wallet amount influences only a Boolean gate."""
    lineage=pilot_cost_lineage(inputs)
    expect(inputs['native_gateway_backoff_seconds']==15 and inputs['default_gateway_backoff_seconds']==60,
           'Future registered backoff policy differs')
    expect(inputs['main_known_gateway_allowance']==1024,'Registered main gateway allowance differs')
    config=inputs['science_config'];at=utc(generated_at);cutoff=utc(inputs['collection_cutoff_utc'])
    expect(inputs['collection_cutoff_utc']==CUTOFF and at<cutoff,'Registered collection cutoff differs or elapsed')
    profiles={p['id']:p for p in config['profiles']}
    expect(len(config['worker_profiles'])==4 and len(config['reader_profiles'])==8 and
           config['auxiliary_reader_profiles']==['g26','q397','ds_low'],'Fixed scientific profile grid differs')
    expect(len(set(config['worker_profiles']))==4 and len(set(config['reader_profiles']))==8 and
           set(config['worker_profiles']+config['reader_profiles'])<=set(profiles),'Missing or duplicate scientific profile')
    expect(all(profiles[p]['provider']=='adaption' for p in config['worker_profiles']) and
           sorted(profiles[p]['provider'] for p in config['reader_profiles'])==['adaption']*4+['hf']*2+['ollama']*2,
           'Scientific provider grid differs')
    groups={}
    for g in inputs['development_groups']:
        expect(set(g)=={'profile_id','phase','count','known_usage_count','unknown_usage_count','mean_latency_seconds',
                        'max_known_input_tokens','max_known_output_tokens','known_transient_count','known_transient_rate',
                        'max_retry_after_seconds','transient_classes'},'DEV metadata allowlist differs')
        key=(g['profile_id'],g['phase']);expect(key not in groups,'Duplicate DEV serving group')
        expect(g['profile_id'] in profiles,'Unknown DEV profile')
        n=g['count'];known=g['known_usage_count'];unknown=g['unknown_usage_count']
        expect(all(type(x) is int and x>=0 for x in (n,known,unknown)) and n>0 and known>0 and known+unknown==n,
               'DEV serving count/unknown coverage invalid')
        expect(all(type(g[k]) is int and g[k]>=0 for k in ('max_known_input_tokens','max_known_output_tokens')),
               'DEV usage maximum invalid')
        expect(type(g['known_transient_count']) is int and 0<=g['known_transient_count']==unknown and
               number(g['known_transient_rate'],'DEV transient rate')==Decimal(g['known_transient_count'])/n,
               'DEV transient count/rate differs')
        expect(number(g['max_retry_after_seconds'],'DEV Retry-After')<=900,'DEV Retry-After exceeds envelope')
        validate_classes(g,n)
        number(g['mean_latency_seconds'],'DEV mean latency');groups[key]=g
    expected={(p,phase):n for p in config['worker_profiles'] for phase,n in DEV_COUNTS.items()}
    expected.update({(p,'readers'):32 for p in config['reader_profiles']})
    expect(set(groups)==set(expected) and all(groups[k]['count']==n for k,n in expected.items()),'Complete DEV serving grid required')
    levels=inputs['native_candidates']
    expect(isinstance(levels,list) and levels and all(type(v) is int and 0<v<=16 for v in levels) and
           levels==sorted(set(levels)),'Registered native candidate grid invalid')
    pilots=pilot_metrics['native_candidates']
    expect({p['level'] for p in pilots}==set(levels) and len(pilots)==len(levels),'Native pilot grid differs')
    healthy=[]
    for p in pilots:
        expect(type(p['eligible']) is bool,'Native pilot eligibility flag invalid')
        if not p['eligible']:continue
        expect(type(p['planned']) is int and p['planned']>0 and p['planned']==p['started']==p['terminal'] and
               p['event_metrics']['complete'] is True,'Healthy pilot count differs')
        expect(set(p['profiles'])=={'q397','glm52'},'Healthy pilot profiles differ')
        for item in p['profiles'].values():
            validate_classes(item)
            expect(item['complete'] is True and number(item['requests_per_second'],'pilot throughput')>0,'Healthy pilot throughput unavailable')
            expect(number(item['known_transient_rate'],'pilot transient rate')<=1 and
                   number(item['max_retry_after_seconds'],'pilot Retry-After')<=900,'Pilot backoff metadata invalid')
        healthy.append(p)
    expect(healthy,'No fully eligible native capacity level; do not start MAIN')
    schedule=defaultdict(list);cost_groups=[]
    for identity,phase,n,source_phase in main_counts(config):
        p=profiles[identity];g=groups[(identity,source_phase)]
        in_tokens=min(Decimal(config['input_byte_cap']),Decimal(g['max_known_input_tokens'])*SAFETY)
        out_tokens=min(Decimal(p['max_output_tokens']),Decimal(g['max_known_output_tokens'])*2)
        ri=number(p['input_rate'],'frozen input rate');ro=number(p['output_rate'],'frozen output rate')
        known_row_cost=(in_tokens*ri+out_tokens*ro)/1000000
        unknown_reservation=(Decimal(config['input_byte_cap'])*ri+Decimal(p['max_output_tokens'])*ro)/1000000
        provider=p['provider'];expect(provider in ('adaption','hf','ollama'),'Unknown scientific provider')
        schedule[phase].append(dict(profile_id=identity,provider=provider,count=n,mean_latency=number(g['mean_latency_seconds'],'DEV latency'),
                                    transient_rate=number(g['known_transient_rate'],'DEV transient rate'),
                                    max_retry_after=number(g['max_retry_after_seconds'],'DEV Retry-After'),
                                    transient_classes=g['transient_classes'],
                                    known_row_cost=known_row_cost,unknown_reservation=unknown_reservation))
        cost_groups.append(dict(profile_id=identity,phase=phase,calls=n,usage_source_phase=source_phase,
                                projected_input_tokens=str(in_tokens),projected_output_tokens=str(out_tokens),
                                margined_known_row_cost=str(known_row_cost),full_unknown_row_reservation=str(unknown_reservation)))
    engineering=number(config['phase_caps']['technical']['ollama'],'technical Ollama cap')+number(config['phase_caps']['development']['ollama'],'DEV Ollama cap')
    original=number(config['combined_caps']['ollama'],'original combined Ollama cap')
    extended=number(inputs['max_ollama_combined_peak_cap'],'extended combined Ollama cap')
    expect(original==25 and extended==100 and original-engineering==Decimal('24.70'),'Ollama registered cap envelope differs')
    window=off_peak_window(at,cutoff);available=number(wallet_available_private,'private wallet metadata')
    candidates=[]
    for pilot in sorted(healthy,key=lambda p:p['level']):
        k=pilot['level'];floors={p:Decimal(1)/number(v['requests_per_second'],'pilot throughput') for p,v in pilot['profiles'].items()}
        projected={p:Decimal(0) for p in ('adaption','hf','ollama')};classes={'actors':Decimal(0),'readers':Decimal(0)};weighted_cost_groups=[]
        for phase in PHASES:
            for job in schedule[phase]:
                rate,_=effective_error(job,phase,pilot)
                cost=job['count']*((1-rate)*job['known_row_cost']+rate*job['unknown_reservation'])
                projected[job['provider']]+=cost
                if job['provider']=='adaption':classes['actors' if phase in ACTOR_COUNTS else 'readers']+=cost
                weighted_cost_groups.append(dict(profile_id=job['profile_id'],phase=phase,calls=job['count'],
                                                effective_known_transient_rate=str(rate),projected_peak_cost=str(cost)))
        chosen=original if projected['ollama']<=original-engineering else extended
        expect(projected['ollama']<=chosen-engineering,'Projected Ollama workload exceeds registered conditional ceiling')
        expect(classes['actors']<=number(config['native_class_caps']['actors'],'actor cap') and
               classes['readers']<=number(config['native_class_caps']['readers'],'reader cap') and
               projected['adaption']<=number(config['phase_caps']['main']['adaption'],'native main cap') and
               projected['hf']<=number(config['phase_caps']['main']['hf'],'HF main cap'),'Projected workload exceeds registered provider/class cap')
        wallet_gate=window and available>projected['ollama']/2+Decimal(5)+Decimal('0.10')
        for ollama in (2,3):
            base=Decimal(0);critical=Decimal(0);phase_details=[]
            for phase in PHASES:
                jobs=schedule[phase];native=[j for j in jobs if j['provider']=='adaption']
                native_busy=sum((j['mean_latency']*j['count'] for j in native),Decimal(0))
                model_bounds=[j['count']*max(j['mean_latency']/k,floors.get(j['profile_id'],Decimal(0))) for j in native]
                native_bound=max([native_busy/16,sum(j['count'] for j in native)*Decimal('1.0')]+model_bounds)
                hf=sum((j['mean_latency']*j['count'] for j in jobs if j['provider']=='hf'),Decimal(0))/2
                ds=sum((j['mean_latency']*j['count'] for j in jobs if j['provider']=='ollama'),Decimal(0))/ollama
                cooldowns={p:Decimal(0) for p in ('adaption','hf','ollama')};failure_counts={p:Decimal(0) for p in cooldowns}
                for j in jobs:
                    rate,pause=effective_error(j,phase,pilot)
                    projected_errors=j['count']*rate;failure_counts[j['provider']]+=projected_errors
                    cooldowns[j['provider']]+=j['count']*pause
                cooldown=sum(cooldowns.values(),Decimal(0));service=max(native_bound,hf,ds)
                bound=service+cooldown;base+=bound;critical+=native_bound+cooldown
                phase_details.append(dict(phase=phase,native_seconds=str(native_bound+cooldown),hf_seconds=str(hf+cooldown),
                                          ollama_seconds=str(ds+cooldown),native_service_seconds=str(native_bound),
                                          hf_service_seconds=str(hf),ollama_service_seconds=str(ds),
                                          global_cooldown_seconds=str(cooldown),provider_cooldown_seconds={p:str(v) for p,v in cooldowns.items()},
                                          projected_known_transient_terminals={p:str(v) for p,v in failure_counts.items()},
                                          projected_known_transient_total=str(sum(failure_counts.values(),Decimal(0))),
                                          bottleneck_service_seconds=str(service),bottleneck_seconds=str(bound)))
            duration=base*SAFETY+OVERHEAD
            gateway_gate=all(number(p['projected_known_transient_total'],'projected phase errors')<=inputs['main_known_gateway_allowance'] for p in phase_details)
            candidates.append(dict(native_per_model=k,ollama_per_model=ollama,base_seconds=str(base),native_critical_seconds=str(critical),
                                   forecast_seconds=str(duration),projected_main_peak_costs={p:str(v) for p,v in projected.items()},
                                   projected_native_actor_peak_cost=str(classes['actors']),projected_native_reader_peak_cost=str(classes['readers']),
                                   off_peak_wallet_gate_passed=bool(wallet_gate),ollama_combined_peak_cap=str(chosen),main_ollama_peak_cap=str(chosen-engineering),
                                   phase_bounds=phase_details,cost_groups=weighted_cost_groups,
                                   gateway_allowance_feasible=gateway_gate,
                                   deadline_feasible=at.timestamp()+float(duration)<cutoff.timestamp()))
    return dict(schema_version=1,generated_at=at.isoformat(),development_freeze_sha256=inputs['development_freeze_sha256'],
                pilot_freeze_sha256=inputs['pilot_freeze_sha256'],safety_multiplier=1.25,overhead_seconds=1800,
                collection_cutoff_utc=CUTOFF,candidates=candidates,development_serving_metadata=inputs['development_groups'],
                journal_sha256=inputs['journal_sha256'],driver_state_sha256=inputs['driver_state_sha256'],
                pilot_cost_lineage=lineage,
                main_known_gateway_allowance=inputs['main_known_gateway_allowance'],
                known_gateway_projection_caveat='Projected phase counts are engineering expectations, not a guarantee against exhausting the registered terminal-error allowance.',
                pilot_metadata_sha256=s.digest(pilot_metrics),cost_groups=cost_groups,
                eligible_native_levels=[p['level'] for p in healthy],excluded_native_levels=[p['level'] for p in pilots if not p['eligible']],
                workload=dict(actor_calls_including_influence=9200,reader_calls_including_calibration=64320,scientific_main_blocks=640),
                accuracy_used_for_selection=False,cost_basis='Frozen peak rates: calls×[(1−effective known-transient rate)×margined known row cost +rate×full unknown row reservation]. DEV input1.25/output2 margins clipped to original ceilings; big-native reader class rates=max DEV/pilot, summed across disjoint classes. Estimates/reservations, not invoices.',
                future_backoff_policy=dict(adaption_gateway_502_503_504_seconds=15,other_known_transients_seconds=60,max_retry_after_seconds=900),
                rate_source='https://ollama.com/pricing',off_peak_window_verified=window,
                backoff_assumptions='Disjoint gateway5xx/explicit-overload429 DEV rates by profile/phase; Q397/GLM52 reader rates use component-wise max DEV/pilot. Future Adaption502/503/504 floor15 seconds;429 and other providers60, each max with observed valid Retry-After up to900. Historical DEV waits used60; future policy is prospective. Sum calls×class-rate×class-delay globally per phase before1.25+1800. Episodes may coalesce. Pilot elapsed spans can already include cooldown, so adding projected pauses can deliberately double-count waiting. This engineering envelope is neither a calibrated wallclock estimate nor a statistical upper confidence bound or completion guarantee.')


def admitted_inputs(state_path):
    from experiments import swarm_ledger_dispatch_v2 as op
    from experiments import swarm_ledger_analysis as analysis
    gate=op.development_gate(state_path)
    _,engineering=analysis.validate_pre_main();development=engineering['development_actor_rows'];groups=[];journals={}
    for phase in (*DEV_COUNTS,'readers'):
        items=engineering['development_reader_rows'] if phase=='readers' else [r for r in development if r['metadata']['stage']==phase]
        out=s.folder('development')/phase;attempts={r['id']:r for r in s.rows(out/'attempts.jsonl')};delays={}
        for row in items:
            if known_transient(row):
                fallback=utc(attempts[row['id']]['started']).timestamp()+float(number(row['transport']['latency_seconds'],'DEV latency'))
                delays[row['id']]=op.retry_after_metadata_delay(row,out,fallback_epoch=fallback)
        groups.extend(aggregate(items,phase,delays))
    for split,phases in (('technical',('technical',)),('development',(*DEV_COUNTS,'readers'))):
        for phase in phases:
            out=s.folder(split)/phase
            for name in ('plan.json','attempts.jsonl','responses.jsonl'):
                journals[split+'/'+phase+'/'+name]=raw_sha(out/name)
    cfg=s.config();o=op.config()
    inputs=dict(science_config=cfg,development_groups=groups,development_freeze_sha256=s.sha(s.freeze_path('development')),
                pilot_freeze_sha256=s.sha(op.op_freeze('pilot')),driver_state_sha256=gate['driver_state_sha256'],journal_sha256=journals,
                collection_cutoff_utc=o['collection_deadline_utc'],max_ollama_combined_peak_cap=o['max_ollama_combined_peak_equivalent_cap'],
                native_candidates=o['native_candidates'],native_gateway_backoff_seconds=o['native_gateway_backoff_seconds'],
                default_gateway_backoff_seconds=o['default_gateway_backoff_seconds'],main_known_gateway_allowance=o['main_known_gateway_allowance'])
    all_science=engineering['technical_rows']+engineering['development_actor_rows']+engineering['development_reader_rows']
    return inputs,all_science


def create(state_path,output):
    from experiments import swarm_ledger_dispatch_v2 as op
    output=Path(output);expect(not output.exists(),'Forecast exists; use a new prospective artifact path')
    with s.exclusive(s.ROOT/('runs/'+s.config()['study_id']+'-guard')),s.verified_config():
        main=s.folder('main')
        expect(not any(p.stat().st_size for p in main.glob('*/attempts.jsonl')),'MAIN already started; prospective forecast prohibited')
        inputs,science_rows=admitted_inputs(state_path);pilot=op.pilot_metadata()
        inputs['pilot_cost_metadata']=op.pilot_cost_metadata()
        inputs['pilot_cost_caps']=op.config()['pilot_caps']
        journal_paths={name:s.folder(name.split('/')[0])/name.split('/')[1]/name.split('/')[2]
                       for name in inputs['journal_sha256']}
        for phase in op.config()['pilot_phase_order']:
            for name in ('plan.json','attempts.jsonl','responses.jsonl','dispatch-events.jsonl'):
                relative='pilot/'+phase+'/'+name;path=op.folder('pilot')/phase/name
                journal_paths[relative]=path;inputs['journal_sha256'][relative]=raw_sha(path) if path.exists() else None
        for path in op.pilot_spending_paths():
            relative='pilot_spending/'+str(path.relative_to(s.ROOT)).replace('\\','/')
            journal_paths[relative]=path;inputs['journal_sha256'][relative]=raw_sha(path) if path.exists() else None
        # Validate all serving metadata before touching billing; a deliberately
        # ample private placeholder tests structure only and is never emitted.
        build(inputs,pilot,s.now(),Decimal('1E30'))
        spent=sum((number(r['estimated_cost'],'scientific spending') for r in science_rows if s.profile(r['profile_id'])['provider']=='ollama'),Decimal(0))
        spent+=number(inputs['pilot_cost_metadata']['estimated_cost_by_provider']['ollama'],'combined v1/v2 pilot spending')
        cache=s.ROOT/('runs/'+s.config()['study_id']+'-guard/balance-private.json')
        if cache.exists():
            saved=s.read(cache);expect(number(saved['spent'],'cached spending')<=spent,'Wallet spending baseline regressed')
            expect(saved['epoch']<=datetime.now(timezone.utc).timestamp(),'Wallet cache clock is in the future')
        transport=s.Transport(s.credentials(),s.ROOT/('runs/'+op.config()['study_id']+'-forecast'))
        guard=s.BalanceGuard(transport);guard.check(spent,Decimal(0))
        available=guard.available-(spent-guard.at_poll)
        value=build(inputs,pilot,s.now(),available)
        private=s.ROOT/('runs/'+op.config()['study_id']+'-forecast/wallet-private.json');private.parent.mkdir(parents=True,exist_ok=True)
        private.write_text(json.dumps(dict(generated_at=value['generated_at'],available_after_known_spending=str(available),
                                          spent_peak_estimate=str(spent),cache_source_sha256=raw_sha(cache)),indent=2)+'\n',encoding='utf-8')
        expect(inputs['journal_sha256']=={name:raw_sha(path) if path.exists() else None for name,path in journal_paths.items()},
               'Serving journals changed during forecast')
        expect(op.pilot_cost_metadata()==inputs['pilot_cost_metadata'],'V1/V2 pilot cost baseline changed during forecast')
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x',encoding='utf-8',newline='\n') as file:json.dump(value,file,indent=2);file.write('\n')
        return dict(created=True,candidates=len(value['candidates']),wallet_gate_passed=all(c['off_peak_wallet_gate_passed'] for c in value['candidates']),
                    forecast_sha256=raw_sha(output),scope='DEV/pilot serving metadata only; no scientific outcomes used')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--development-state',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(create(args.development_state,args.output),indent=2))


if __name__=='__main__':main()
