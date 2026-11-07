"""Prospective fixed-capacity resource forecast for the complete six-reader study.

Pure build uses allowlisted serving metadata, never accuracy or final answers.
Historical failed pilots contribute costs/provenance only, never throughput.
Private wallet amounts affect only a Boolean and are never serialized.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from experiments import swarm_ledger_study as s
from experiments.swarm_ledger_forecast_v2 import (CUTOFF, PHASES, ACTOR_COUNTS,
 DEV_COUNTS, SAFETY, OVERHEAD, expect, number, raw_sha, utc, off_peak_window,
 known_transient, transient_classes, validate_classes, aggregate)

def main_counts(config):
    out=[]
    for p in config['worker_profiles']:
        for phase,count in ACTOR_COUNTS.items():out.append((p,phase,count,'y' if phase=='influence' else phase))
    for p in config['reader_profiles']:
        out.append((p,'readers',5120+(7680 if p in config['auxiliary_reader_profiles'] else 0),'readers'))
        out.append((p,'calibration',40,'readers'))
    expect(sum(n for _,phase,n,_ in out if phase in ACTOR_COUNTS)==9200 and
           sum(n for _,phase,n,_ in out if phase not in ACTOR_COUNTS)==54000,'Fixed MAIN workload differs')
    return out


def effective_error(job,phase=None,pilot=None):
    rate=Decimal(0);pause=Decimal(0)
    for kind,item in job['transient_classes'].items():
        r=number(item['rate'],'DEV transient class rate')
        base=Decimal(15 if job['provider']=='adaption' and kind=='gateway_5xx' else 60)
        delay=max(base,number(item['max_retry_after_seconds'],'DEV Retry-After'))
        rate+=r;pause+=r*delay
    expect(rate<=1,'Component-wise transient rate envelope exceeds one')
    return rate,pause


def pilot_cost_lineage(inputs):
    metadata=inputs['pilot_cost_metadata']
    expect(set(metadata)=={'estimated_cost_by_provider','baselines'},'Historical pilot cost allowlist differs')
    expect(set(metadata['estimated_cost_by_provider'])=={'adaption','hf','ollama'},'Historical provider grid differs')
    expect(len(metadata['baselines'])==2,'Both historical pilot baselines required')
    for baseline in metadata['baselines']:
        expect(set(baseline)=={'path','sha256','registration_tag','registration_sha256'},'Pilot baseline allowlist differs')
        for key in ('sha256','registration_sha256'):
            expect(isinstance(baseline[key],str) and len(baseline[key])==64 and all(c in '0123456789abcdef' for c in baseline[key]),'Invalid pilot baseline digest')
    expect(len({b['path'] for b in metadata['baselines']})==2,'Duplicate historical pilot baseline')
    for provider,value in metadata['estimated_cost_by_provider'].items():
        expect(number(value,'historical pilot spending')<=number(inputs['pilot_cost_caps'][provider],'historical pilot cap'),'Historical pilot cap exceeded')
    return metadata


def build(inputs,generated_at,wallet_available_private):
    """Pure projection. Private wallet amount influences only a Boolean gate."""
    lineage=pilot_cost_lineage(inputs)
    expect(inputs['pilot_metadata_sha256']==s.digest(lineage),'Historical pilot metadata hash differs')
    expect(inputs['native_gateway_backoff_seconds']==15 and inputs['default_gateway_backoff_seconds']==60,
           'Future registered backoff policy differs')
    expect(inputs['main_known_gateway_allowance']==1024,'Registered main gateway allowance differs')
    config=inputs['science_config'];at=utc(generated_at);cutoff=utc(inputs['collection_cutoff_utc'])
    expect(inputs['collection_cutoff_utc']==CUTOFF and at<cutoff,'Registered collection cutoff differs or elapsed')
    profiles={p['id']:p for p in config['profiles']}
    expect(len(config['worker_profiles'])==4 and len(config['reader_profiles'])==6 and
           config['auxiliary_reader_profiles']==['g26','g31','ds_low'],'Fixed scientific profile grid differs')
    expect(len(set(config['worker_profiles']))==4 and len(set(config['reader_profiles']))==6 and
           set(config['worker_profiles']+config['reader_profiles'])<=set(profiles),'Missing or duplicate scientific profile')
    expect(all(profiles[p]['provider']=='adaption' for p in config['worker_profiles']) and
           sorted(profiles[p]['provider'] for p in config['reader_profiles'])==['adaption']*2+['hf']*2+['ollama']*2,
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
    expected.update({(p,'readers'):32 for p in ('g26','g31','q397','glm52','hf_text','hf_schema','ds_off','ds_low')})
    expect(set(groups)==set(expected) and all(groups[k]['count']==n for k,n in expected.items()),'Complete DEV serving grid required')
    expect(inputs['native_candidates']==[2], 'Fixed native capacity differs')
    expect(inputs.get('provider_cap',8)==8 and inputs.get('global_cap',8)==8,
           'Fixed provider/global capacity differs')
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
    expect(original==100 and extended==100 and original-engineering==Decimal('99.70'),'Ollama registered cap envelope differs')
    window=off_peak_window(at,cutoff);available=number(wallet_available_private,'private wallet metadata')
    candidates=[]
    for k in (2,):
        pilot={'profiles':{}}
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
        for ollama in (2,):
            base=Decimal(0);critical=Decimal(0);phase_details=[]
            for phase in PHASES:
                jobs=schedule[phase];native=[j for j in jobs if j['provider']=='adaption']
                native_busy=sum((j['mean_latency']*j['count'] for j in native),Decimal(0))
                model_bounds=[j['count']*j['mean_latency']/k for j in native]
                native_bound=max([native_busy/8,sum(j['count'] for j in native)*Decimal('1.0')]+model_bounds)
                hf=sum((j['mean_latency']*j['count'] for j in jobs if j['provider']=='hf'),Decimal(0))/2
                ds=sum((j['mean_latency']*j['count'] for j in jobs if j['provider']=='ollama'),Decimal(0))/ollama
                cooldowns={p:Decimal(0) for p in ('adaption','hf','ollama')};failure_counts={p:Decimal(0) for p in cooldowns}
                for j in jobs:
                    rate,pause=effective_error(j,phase,pilot)
                    projected_errors=j['count']*rate;failure_counts[j['provider']]+=projected_errors
                    cooldowns[j['provider']]+=j['count']*pause
                cooldown=sum(cooldowns.values(),Decimal(0))
                global_bound=sum((j['mean_latency']*j['count'] for j in jobs),Decimal(0))/8
                service=max(native_bound,hf,ds,global_bound)
                bound=service+cooldown;base+=bound;critical+=native_bound+cooldown
                phase_details.append(dict(phase=phase,global_service_seconds=str(global_bound),native_seconds=str(native_bound+cooldown),hf_seconds=str(hf+cooldown),
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
                historical_pilot_metadata_sha256=inputs['pilot_freeze_sha256'],safety_multiplier=1.25,overhead_seconds=1800,
                collection_cutoff_utc=CUTOFF,candidates=candidates,development_serving_metadata=inputs['development_groups'],
                journal_sha256=inputs['journal_sha256'],driver_state_sha256=inputs['driver_state_sha256'],
                pilot_cost_lineage=lineage,
                main_known_gateway_allowance=inputs['main_known_gateway_allowance'],
                known_gateway_projection_caveat='Projected phase counts are engineering expectations, not a guarantee against exhausting the registered terminal-error allowance.',
                pilot_metadata_sha256=inputs['pilot_metadata_sha256'],science_config_sha256=s.digest(config),forecast_source_sha256=s.sha(__file__),cost_groups=cost_groups,
                fixed_native_levels=[2],capacity_pilot_extrapolation_used=False,dispatch_limits=dict(native_per_model=2,native_provider=8,global_cap=8,hf=2,ollama=2,native_dispatch_interval_seconds=1),
                workload=dict(actor_calls_including_influence=9200,reader_calls_including_calibration=54000,total_calls=63200,scientific_main_blocks=640),
                accuracy_used_for_selection=False,cost_basis='Frozen peak rates: callsÃ—[(1âˆ’effective known-transient rate)Ã—margined known row cost +rateÃ—full unknown row reservation]. DEV input1.25/output2 margins clipped to original ceilings; All disjoint transient rates use original DEV groups only; unused historical reader groups remain archived. Estimates/reservations, not invoices.',
                future_backoff_policy=dict(adaption_gateway_502_503_504_seconds=15,other_known_transients_seconds=60,max_retry_after_seconds=900),
                rate_source='https://ollama.com/pricing',off_peak_window_verified=window,
                backoff_assumptions='Disjoint gateway5xx/explicit-overload429 DEV rates by profile/phase; Failed capacity-pilot rates and throughput are never extrapolated. Future Adaption502/503/504 floor15 seconds;429 and other providers60, each max with observed valid Retry-After up to900. Historical DEV waits used60; future policy is prospective. Sum callsÃ—class-rateÃ—class-delay globally per phase before1.25+1800. Episodes may coalesce. All original terminal actor latencies, including failed slow reporters, enter DEV means. Summed pauses may deliberately double-count waiting. This engineering envelope is neither a calibrated wallclock estimate nor a statistical upper confidence bound or completion guarantee.')



def admitted_inputs(state_path):
    from experiments import swarm_ledger_complete_dispatch as op
    from experiments import swarm_ledger_complete as complete
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
    cfg=complete.config();o=op.config()
    inputs=dict(science_config=cfg,development_groups=groups,development_freeze_sha256=s.sha(s.freeze_path('development')),
                pilot_freeze_sha256=s.digest(op.pilot_public_metadata()),driver_state_sha256=gate['driver_state_sha256'],journal_sha256=journals,
                collection_cutoff_utc=o['collection_deadline_utc'],max_ollama_combined_peak_cap=o['max_ollama_combined_peak_equivalent_cap'],
                native_candidates=[2],native_gateway_backoff_seconds=o['native_gateway_backoff_seconds'],
                default_gateway_backoff_seconds=o['default_gateway_backoff_seconds'],main_known_gateway_allowance=o['main_known_gateway_allowance'])
    all_science=engineering['technical_rows']+engineering['development_actor_rows']+engineering['development_reader_rows']
    return inputs,all_science


def create(state_path,output):
    from experiments import swarm_ledger_complete_dispatch as op
    from experiments import swarm_ledger_complete as complete
    output=Path(output);expect(not output.exists(),'Forecast exists; use a new prospective artifact path')
    with s.exclusive(s.ROOT/('runs/'+s.config()['study_id']+'-guard')):
        main=s.folder('main')
        expect(not any(p.stat().st_size for p in main.glob('*/attempts.jsonl')),'MAIN already started; prospective forecast prohibited')
        inputs,science_rows=admitted_inputs(state_path);op.verify_pilot_history()
        inputs['pilot_cost_metadata']=op.pilot_public_metadata()
        inputs['pilot_metadata_sha256']=s.digest(inputs['pilot_cost_metadata'])
        inputs['pilot_cost_caps']={'adaption':'10','hf':'0','ollama':'.10'}
        journal_paths={name:s.folder(name.split('/')[0])/name.split('/')[1]/name.split('/')[2]
                       for name in inputs['journal_sha256']}
        for path in op.pilot_spending_paths():
            relative='pilot_spending/'+str(path.relative_to(s.ROOT)).replace('\\','/')
            journal_paths[relative]=path;inputs['journal_sha256'][relative]=raw_sha(path) if path.exists() else None
        # Validate all serving metadata before touching billing; a deliberately
        # ample private placeholder tests structure only and is never emitted.
        build(inputs,s.now(),Decimal('1E30'))
        spent=sum((number(r['estimated_cost'],'scientific spending') for r in science_rows if s.profile(r['profile_id'])['provider']=='ollama'),Decimal(0))
        spent+=number(inputs['pilot_cost_metadata']['estimated_cost_by_provider']['ollama'],'combined v1/v2 pilot spending')
        cache=s.ROOT/('runs/'+s.config()['study_id']+'-guard/balance-private.json')
        if cache.exists():
            saved=s.read(cache);expect(number(saved['spent'],'cached spending')<=spent,'Wallet spending baseline regressed')
            expect(saved['epoch']<=datetime.now(timezone.utc).timestamp(),'Wallet cache clock is in the future')
        transport=s.Transport(s.credentials(),s.ROOT/('runs/'+op.config()['study_id']+'-forecast'))
        guard=s.BalanceGuard(transport);guard.check(spent,Decimal(0))
        available=guard.available-(spent-guard.at_poll)
        value=build(inputs,s.now(),available)
        private=s.ROOT/('runs/'+op.config()['study_id']+'-forecast/wallet-private.json');private.parent.mkdir(parents=True,exist_ok=True)
        private.write_text(json.dumps(dict(generated_at=value['generated_at'],available_after_known_spending=str(available),
                                          spent_peak_estimate=str(spent),cache_source_sha256=raw_sha(cache)),indent=2)+'\n',encoding='utf-8')
        expect(inputs['journal_sha256']=={name:raw_sha(path) if path.exists() else None for name,path in journal_paths.items()},
               'Serving journals changed during forecast')
        expect(op.verify_pilot_history()==inputs['pilot_cost_metadata'],'V1/V2 pilot cost baseline changed during forecast')
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x',encoding='utf-8',newline='\n') as file:json.dump(value,file,indent=2);file.write('\n')
        return dict(created=True,candidates=len(value['candidates']),wallet_gate_passed=all(c['off_peak_wallet_gate_passed'] for c in value['candidates']),
                    forecast_sha256=raw_sha(output),scope='DEV/pilot serving metadata only; no scientific outcomes used')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--development-state',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(create(args.development_state,args.output),indent=2))


if __name__=='__main__':main()


