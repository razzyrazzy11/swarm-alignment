"""Unfrozen metadata-only latency-window sensitivity; never directs collection."""
import argparse
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
from analysis import collection_timing as timing


def diagnose(attempts, terminals, now, windows=(15,30,60), minimum=20):
    timing.require(type(minimum) is int and minimum>0,'Invalid minimum sample count')
    base=timing.summarize(attempts,terminals,now)
    starts={r['id']:timing.stamp(r['started']) for r in attempts}
    remaining={p:r['remaining'] for p,r in base['profiles'].items()}
    gap=base['stress_scenario']['empirical_nearest_rank_p95_idle_seconds']
    pauses=max(0,32-base['http_counts'].get('500',0))*60
    terminal_ids={r['id'] for r in terminals}
    censored_all={p:[] for p in timing.PLANNED}
    for row in attempts:
        if row['id'] not in terminal_ids:
            censored_all[row['profile_id']].append((now-starts[row['id']]).total_seconds())
    scenarios={}
    for minutes in windows:
        timing.require(type(minutes) is int and minutes>0,'Invalid window')
        after=now-timedelta(minutes=minutes)
        values={p:[] for p in timing.PLANNED}
        for row in terminals:
            if starts[row['id']]>=after and row['latency_seconds'] is not None:
                values[row['profile_id']].append(row['latency_seconds'])
        counts={p:len(v) for p,v in values.items()}
        incomplete=[p for p in counts if remaining[p] and counts[p]<minimum]
        means={p:sum(v)/len(v) if v else None for p,v in values.items()}
        censored={p:0 for p in timing.PLANNED}
        for row in attempts:
            if row['id'] not in terminal_ids and starts[row['id']]>=after:censored[row['profile_id']]+=1
        item=dict(sample_counts=counts,in_flight_started_in_window=censored,window_mean_seconds=means,
                  available=not incomplete and gap is not None and base['stress_scenario']['unavailable_reason'] is None)
        if item['available']:
            service={p:max(base['profiles'][p]['mean_latency_seconds'],means[p] or 0)*remaining[p]
                if remaining[p] else 0 for p in timing.PLANNED}
            resource=dict(g26=service['g26']/2,g31=service['g31']/2,
                hf=(service['hf_text']+service['hf_schema'])/2,
                ollama=(service['ds_low']+service['ds_off'])/2,
                global_eight=sum(service.values())/8,
                native_spacing=max(0,remaining['g26']+remaining['g31']-1))
            seconds=(max(resource.values())+timing.wave_counts(sum(remaining.values()))['upper']*gap+
                     timing.AUXILIARY_SECONDS)*1.25+timing.OVERHEAD_SECONDS
            item.update(resource_seconds=resource,
                conditional_finish_utc=(now+timedelta(seconds=seconds)).isoformat(),
                with_remaining_server500_at60s_utc=(now+timedelta(seconds=seconds+pauses)).isoformat(),
                margin_after_remaining_server500_at60s_hours=(timing.CUTOFF-now).total_seconds()/3600-(seconds+pauses)/3600)
        else:item['unavailable_profiles']=incomplete
        scenarios[str(minutes)]=item
    short=base['stress_scenario']['collection_finish_utc']
    return dict(schema_version=1,checked_at=now.isoformat(),independent_scientific_results_read=False,
        baseline_median_conditional_finish=base['scenario_collection_finish_utc'],
        last100_conditional_stress_finish=short,
        last100_with_remaining_server500_at60s_utc=(timing.stamp(short)+timedelta(seconds=pauses)).isoformat() if short else None,
        remaining_server500_pause_seconds=pauses,
        all_in_flight_by_profile={p:dict(count=len(v),oldest_age_seconds=max(v) if v else None) for p,v in censored_all.items()},
        window_sensitivities=scenarios,
        interpretation='Compare cumulative/last100 and15/30/60minute metadata windows; no preferred window selected from outcome accuracy. A short-window spike is not by itself sustained deterioration. These are conditional service scenarios, not confidence intervals, bounds, probabilities or clearance to change a cutoff.',
        limitations='Completed-call latency means can omit slow in-flight calls; window counts and all in-flight counts/oldest ages are disclosed. No future task-mix, provider outage or drain-duration model is identified. Recovery downtime already elapsed is not added again. Existing auxiliary allowance,25%headroom,3300s overhead and empirical p95-idle proxy remain. Remaining500 sensitivity adds each unused500 allowance at its60s default cooldown only: longer Retry-After, additional health-check waits and future outages are not all bounded by this scenario. It is an additional stress, not an expectation. Does not replace frozen protocol or scientific replay.')


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=root/'runs/experiment-sanity-check')
    args=parser.parse_args()
    directories=[root/'runs'/batch/'readers' for batch in ('swarm-ledger-resume-v1-main','swarm-ledger-resume-v2-main','swarm-ledger-resume-v3-main')]
    terminal=[r for directory in directories for r in timing.rows(directory/'responses.jsonl',True)]
    attempts=[r for directory in directories for r in timing.rows(directory/'attempts.jsonl')]
    value=diagnose(attempts,terminal,datetime.now(timezone.utc))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    name='headroom-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
    with (args.output_dir/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
    with (args.output_dir/'headroom-history.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(value,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps(value,allow_nan=False))


if __name__=='__main__':main()
