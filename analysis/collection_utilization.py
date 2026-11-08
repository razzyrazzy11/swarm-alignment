"""Observed reader network utilization only; no ETA, inference or collector change.

Completed intervals are observed network occupancy. An unfinished request's
network interval is unknown and is never imputed as an active slot. Conservative
idle summaries mask its dispatch-to-observation window instead.
"""
import argparse
from collections import Counter
from datetime import datetime,timedelta,timezone
import json
import math
import os
from pathlib import Path
from analysis import collection_timing as timing
from analysis.collection_progress import registered_deadline_policy

ROOT=Path(__file__).resolve().parents[1]
BATCHES=('swarm-ledger-resume-v1-main','swarm-ledger-resume-v2-main','swarm-ledger-resume-v3-main',
         'swarm-ledger-efficient-v1-main','swarm-ledger-rate-v1-main','swarm-ledger-paced-v1-main')
CAPACITY={'adaption':8,'hf':2,'ollama':2}
READER_MODEL_CONSTRAINTS={
    'adaption':dict(reader_profiles=['g26','g31'],distinct_requested_models=2,per_model_guard=2,reader_model_guard_ceiling=4),
    'hf':dict(reader_profiles=['hf_text','hf_schema'],distinct_requested_models=1,per_model_guard=2,reader_model_guard_ceiling=2),
    'ollama':dict(reader_profiles=['ds_low','ds_off'],distinct_requested_models=1,per_model_guard=2,reader_model_guard_ceiling=2)}


def require(ok,message):
    if not ok:raise ValueError(message)


def capacity_basis(root):
    path=Path(root)/'research/swarm-ledger-complete-dispatch-config.json'
    value=json.loads(path.read_text(encoding='utf-8'))
    require(value.get('native_provider_max_active')==8 and value.get('native_per_model')==2
            and value.get('hf_max_active')==2 and value.get('ollama_max_active')==2
            and value.get('total_max_active')==8,'Registered concurrency guard differs')
    return dict(source='research/swarm-ledger-complete-dispatch-config.json',provider_guards=CAPACITY,
                source_scope='Guard values checked; frozen-source validation remains the separate health gate')


def sweep(intervals,start,end,capacity):
    """Half-open interval sweep; simultaneous ends/starts never create overlap."""
    require(start<=end and type(capacity) is int and capacity>0,'Invalid sweep window/capacity')
    events=Counter({start:0,end:0});clipped=[];before=after=0
    for left,right in intervals:
        require(left<=right,'Reversed network interval')
        if right<=start or left>=end or left==right:continue
        before+=left<start;after+=right>end
        left,right=max(start,left),min(end,right)
        clipped.append((left,right));events[left]+=1;events[right]-=1
    active=0;previous=start;occupancy=Counter();maximum=0
    for point in sorted(events):
        seconds=(point-previous).total_seconds()
        if seconds:
            occupancy[active]+=seconds;maximum=max(maximum,active)
        active+=events[point];previous=point
        require(active>=0,'Negative interval occupancy')
    require(active==0,'Unbalanced interval sweep')
    duration=(end-start).total_seconds();busy=sum(count*seconds for count,seconds in occupancy.items())
    return dict(observation_seconds=duration,completed_intervals_overlapping_window=len(clipped),
        intervals_extending_before_window=before,intervals_extending_after_window=after,
        slot_busy_seconds=busy,mean_active=busy/duration if duration else None,
        registered_capacity=capacity,observed_capacity_occupancy_fraction=busy/(capacity*duration) if duration else None,
        time_at_active_0_1_2_seconds={str(n):occupancy[n] for n in (0,1,2)},
        occupancy_seconds_by_active={str(n):seconds for n,seconds in sorted(occupancy.items())},
        maximum_observed_active=maximum,observed_cap_violation_seconds=sum(seconds for n,seconds in occupancy.items() if n>capacity))


def interval_union(intervals,start,end):return timing.union(intervals,start,end)


def length(intervals):return sum((right-left).total_seconds() for left,right in intervals)


def idle_summary(intervals,masks,start,end):
    # Masks exclude potentially in-flight network activity from identifiable idle;
    # they do not turn the unknown interval into an observed busy slot.
    gaps=timing.idle_gaps(intervals+masks,start,end)
    long=[(left,right) for left,right in gaps if (right-left).total_seconds()>=15]
    return dict(intervals_ge15_seconds=len(long),total_seconds=length(long),
                maximum_seconds=max(((b-a).total_seconds() for a,b in long),default=0))


def idle_while_other_busy(own,other,masks,start,end):
    busy=interval_union(other,start,end);own_or_unknown=interval_union(own+masks,start,end)
    result=[];index=0
    for left,right in busy:
        cursor=left
        while index<len(own_or_unknown) and own_or_unknown[index][1]<=left:index+=1
        current=index
        while current<len(own_or_unknown) and own_or_unknown[current][0]<right:
            a,b=own_or_unknown[current]
            if cursor<a:result.append((cursor,min(a,right)))
            cursor=max(cursor,b)
            if cursor>=right:break
            current+=1
        if cursor<right:result.append((cursor,right))
        index=current
    return dict(seconds=length(result),intervals=len(result),
        intervals_ge15_seconds=sum((b-a).total_seconds()>=15 for a,b in result))


def summarize(attempts,terminals,observed_at,windows=(15,30,60)):
    require(observed_at.tzinfo is not None,'Aware observation timestamp required')
    observed_at=observed_at.astimezone(timezone.utc);started={};seen=set();completed=[];missing=Counter()
    for row in attempts:
        identity=row.get('id');profile=row.get('profile_id');when=timing.stamp(row.get('started'))
        require(type(identity) is str and identity and identity not in started,'Invalid/duplicate start')
        require(profile in timing.PLANNED and when<=observed_at,'Foreign profile/future start')
        started[identity]=(profile,when)
    for row in terminals:
        identity=row.get('id');profile=row.get('profile_id')
        require(identity not in seen and identity in started and started[identity][0]==profile,'Duplicate/unstarted/profile-changed terminal')
        seen.add(identity);left=row.get('started_utc');right=row.get('finished_utc');latency=row.get('latency_seconds')
        require(latency is None or (type(latency) in (int,float) and math.isfinite(latency) and latency>=0),'Invalid service latency')
        if left is None or right is None:
            missing[profile]+=1;continue
        left,right=timing.stamp(left),timing.stamp(right)
        require(started[identity][1]<=left<=right<=observed_at,'Invalid completed network chronology')
        completed.append((identity,profile,left,right,latency))
    inflight={p:[] for p in timing.PLANNED};unknown={p:[] for p in timing.PLANNED}
    completed_with_timing={identity for identity,_,_,_,_ in completed}
    for identity,(profile,when) in started.items():
        if identity not in seen:inflight[profile].append((observed_at-when).total_seconds())
        if identity not in completed_with_timing:unknown[profile].append((when,observed_at))
    start_collection=min((when for _,when in started.values()),default=observed_at);results={}
    for minutes in windows:
        require(type(minutes) is int and minutes>0,'Invalid recent window')
        left=max(observed_at-timedelta(minutes=minutes),start_collection);right=observed_at
        provider_intervals={p:[] for p in CAPACITY};profile_intervals={p:[] for p in timing.PLANNED}
        for _,profile,a,b,_ in completed:
            provider_intervals[timing.PROVIDER[profile]].append((a,b));profile_intervals[profile].append((a,b))
        providers={p:sweep(values,left,right,CAPACITY[p]) for p,values in provider_intervals.items()}
        for provider,value in providers.items():
            value.update(denominator_scope='Registered provider concurrency guard, not achievable current-reader throughput',
                reader_model_constraints=READER_MODEL_CONSTRAINTS[provider],
                remaining_job_eligibility_inferred=False,
                constraint_limit='Model-guard ceiling is theoretical; pacing, shared guards, task availability and other waits can lower occupancy')
        profiles={}
        for profile,values in profile_intervals.items():
            value=sweep(values,left,right,2)
            service=[(b-a).total_seconds() for _,p,a,b,_ in completed if p==profile and left<b<=right]
            transport=[latency for _,p,_,b,latency in completed if p==profile and left<b<=right and latency is not None]
            value.update(service_samples_completed_in_window=len(service),
                mean_full_network_service_seconds=sum(service)/len(service) if service else None,
                transport_latency_samples=len(transport),mean_transport_latency_seconds=sum(transport)/len(transport) if transport else None,
                right_censored_inflight_count=len(inflight[profile]),
                oldest_inflight_age_seconds=max(inflight[profile]) if inflight[profile] else None,
                missing_completed_network_timestamps=missing[profile])
            profiles[profile]=value
        all_intervals=[interval for values in provider_intervals.values() for interval in values]
        all_unknown=[interval for values in unknown.values() for interval in values]
        ollama=provider_intervals['ollama'];other=provider_intervals['adaption']+provider_intervals['hf']
        ollama_unknown=[interval for profile,values in unknown.items() if timing.PROVIDER[profile]=='ollama' for interval in values]
        total=sum(value['service_samples_completed_in_window'] for value in profiles.values())
        results[str(minutes)]=dict(observation_start_utc=left.isoformat(),observation_end_utc=right.isoformat(),
            providers=providers,profiles=profiles,
            global_reader_observed=sweep(all_intervals,left,right,8),
            completed_service_profile_mix={p:value['service_samples_completed_in_window']/total if total else None for p,value in profiles.items()},
            global_reader_idle_completed_intervals_only=idle_summary(all_intervals,[],left,right),
            global_reader_idle_excluding_unknown_dispatch_windows=idle_summary(all_intervals,all_unknown,left,right),
            ollama_idle_while_other_provider_busy_completed_intervals_only=idle_while_other_busy(ollama,other,[],left,right),
            ollama_idle_while_other_provider_busy_excluding_unknown_ollama_windows=idle_while_other_busy(ollama,other,ollama_unknown,left,right))
    return dict(schema_version=1,checked_at=observed_at.isoformat(),windows=results,
        right_censored_inflight_total=sum(len(values) for values in inflight.values()),
        missing_completed_network_timestamps_total=sum(missing.values()),
        no_inference=True,scientific_outcomes_read=False,completion_eta_computed=False,admission_clearance=False,
        limits='Completed network intervals only. In-flight network intervals are unknown and never counted as observed active slots. Their dispatch windows, and completed calls missing network timestamps, mask conservative identifiable-idle summaries. Completed-only idle/occupancy can understate real occupancy. Idle is within these reader journals, not evidence of a global provider outage or the cause of a barrier/scheduler delay. Service means use calls finishing in the window at full duration; slot occupancy clips interval edges. No forecast, gain, scientific validity or admission clearance follows.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'runs/experiment-sanity-check')
    args=parser.parse_args();directories=[ROOT/'runs'/batch/'readers' for batch in BATCHES]
    terminals=[row for directory in directories for row in timing.rows(directory/'responses.jsonl',True)]
    attempts=[row for directory in directories for row in timing.rows(directory/'attempts.jsonl')]
    # Observation end is sampled after both snapshots, never before file reads.
    value=summarize(attempts,terminals,datetime.now(timezone.utc));value['registered_policy']=registered_deadline_policy(ROOT)
    value['capacity_basis']=capacity_basis(ROOT)
    target=args.output_dir.resolve();require(target.is_relative_to((ROOT/'runs').resolve()),'Write only private operational metadata')
    target.mkdir(parents=True,exist_ok=True)
    filename='utilization-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
    with (target/filename).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
    with (target/'utilization-history.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(value,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps(value,allow_nan=False))

if __name__=='__main__':main()
