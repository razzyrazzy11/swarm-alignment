"""Metadata-only network timing diagnosis; no request, outcome, or guard changes."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
from statistics import median
from analysis.collection_progress import PLANNED, PROVIDER, CUTOFF, DEADLINE
from analysis.collection_progress import AUXILIARY_SECONDS, OVERHEAD_SECONDS, require, stamp


def union(intervals, start, end):
    """Clip and merge half-open intervals; adjacency creates no idle gap."""
    require(start <= end, 'Invalid observation window')
    clipped = []
    for left, right in intervals:
        require(left <= right, 'Reversed network interval')
        left, right = max(left, start), min(right, end)
        if left < right:
            clipped.append((left, right))
    result = []
    for left, right in sorted(clipped):
        if result and left <= result[-1][1]:
            result[-1] = (result[-1][0], max(right, result[-1][1]))
        else:
            result.append((left, right))
    return result


def idle_gaps(intervals, start, end):
    cursor, result = start, []
    for left, right in union(intervals, start, end):
        if cursor < left:
            result.append((cursor, left))
        cursor = right
    if cursor < end:
        result.append((cursor, end))
    return result


def wave_counts(remaining):
    require(type(remaining) is int and remaining >= 0, 'Invalid remaining call count')
    return dict(lower=max(0, math.ceil(remaining/107)-1), upper=math.ceil(remaining/100),
        explanation='At most seven other active requests can complete when the 100-completion drain threshold is crossed. The lower count omits the possible last boundary check; the upper includes it. This is an operational wave scenario, not a guarantee about future failures or dispatch.')


def nearest_rank(values, fraction):
    """Empirical nearest-rank quantile, not a forecast confidence interval."""
    require(bool(values), 'Quantile requires observations')
    require(type(fraction) in (int,float) and 0 < fraction <= 1, 'Invalid quantile fraction')
    require(all(type(value) in (int,float) and math.isfinite(value) for value in values),
            'Invalid quantile observation')
    return sorted(values)[math.ceil(len(values)*fraction)-1]


def rows(path, terminal=False):
    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    if lines and not lines[-1].endswith(b'\n'):
        lines.pop()
    result = []
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    for line in lines:
        raw = json.loads(line, object_pairs_hook=unique)
        require(type(raw) is dict, 'Record must be an object')
        safe = {key: raw.get(key) for key in ('id', 'profile_id')}
        if terminal:
            transport = raw.get('transport')
            require(type(transport) is dict, 'Terminal transport required')
            diagnostic = transport.get('diagnostics', {})
            require(type(diagnostic) is dict, 'Invalid diagnostic metadata')
            safe.update(latency_seconds=transport.get('latency_seconds'), http_status=transport.get('http_status'),
                started_utc=diagnostic.get('started_utc'), finished_utc=diagnostic.get('finished_utc'))
        else:
            safe['started'] = raw.get('started')
        result.append(safe)
    return result


def summarize(attempts, terminals, now):
    require(now.tzinfo is not None, 'Current time must be aware')
    now = now.astimezone(timezone.utc)
    starts, seen = {}, set()
    for row in attempts:
        identity, profile = row.get('id'), row.get('profile_id')
        require(type(identity) is str and identity and identity not in starts, 'Invalid/duplicate attempt identity')
        require(profile in PLANNED, 'Foreign attempt profile')
        when = stamp(row.get('started'))
        require(when <= now, 'Future attempt start')
        starts[identity] = (profile, when)
    counts, statuses, missing = Counter(), Counter(), Counter()
    latencies = {p: [] for p in PLANNED}
    intervals, provider_busy = [], Counter()
    for row in terminals:
        identity, profile = row.get('id'), row.get('profile_id')
        require(type(identity) is str and identity not in seen, 'Invalid/duplicate terminal identity')
        require(identity in starts and profile == starts[identity][0], 'Terminal is not a matching started identity')
        seen.add(identity)
        latency, http = row.get('latency_seconds'), row.get('http_status')
        require(latency is None or (type(latency) in (int, float) and math.isfinite(latency) and latency >= 0), 'Invalid latency')
        require(http is None or (type(http) is int and 100 <= http <= 599), 'Invalid HTTP status')
        counts[profile] += 1
        statuses[str(http)] += 1
        if latency is not None:
            latencies[profile].append((starts[identity][1], latency))
        left, right = row.get('started_utc'), row.get('finished_utc')
        if left is None or right is None:
            missing[profile] += 1
            continue
        left, right = stamp(left), stamp(right)
        require(starts[identity][1] <= left <= right <= now, 'Invalid network chronology')
        intervals.append((left, right))
        provider_busy[PROVIDER[profile]] += (right-left).total_seconds()
    start_counts = Counter(profile for profile, _ in starts.values())
    require(all(start_counts[p] <= PLANNED[p] for p in PLANNED), 'Started count exceeds plan')
    profiles, loads, stress_loads = {}, {}, {}
    for profile, planned in PLANNED.items():
        values = [value for _, value in sorted(latencies[profile])]
        mean = sum(values)/len(values) if values else None
        recent_mean = sum(values[-100:])/len(values[-100:]) if values else None
        stress_mean = max(mean,recent_mean) if values else None
        remaining = planned-counts[profile]
        profiles[profile] = dict(started=start_counts[profile], terminal=counts[profile], remaining=remaining,
            latency_samples=len(values), first_100_mean_seconds=sum(values[:100])/len(values[:100]) if values else None,
            last_100_mean_seconds=recent_mean,
            first_last_sample_size=min(100,len(values)), mean_latency_seconds=mean,
            missing_latency_samples=counts[profile]-len(values),
            stress_service_seconds=stress_mean,
            missing_network_timestamps=missing[profile],
            latest_ten_minutes_starts=sum(p == profile and when >= now-timedelta(minutes=10) for p,when in starts.values()))
        loads[profile] = remaining*mean if mean is not None else (0 if remaining == 0 else None)
        stress_loads[profile] = remaining*stress_mean if stress_mean is not None else (0 if remaining == 0 else None)
    remaining = sum(PLANNED.values())-len(seen)
    waves = wave_counts(remaining)
    start = min((when for _,when in starts.values()), default=now)
    # In-flight network endpoints are unknown. Their whole dispatch-to-now window
    # masks potential idle; this cannot manufacture a gap while sends are active.
    censored = [(when, now) for identity,(_,when) in starts.items() if identity not in seen]
    merged = union(intervals+censored, start, now)
    gaps = idle_gaps(intervals+censored, start, now) if not sum(missing.values()) else None
    # A leading/trailing observation boundary is not a completed health barrier.
    internal = [(left,right) for left,right in (gaps or []) if left > start and right < now]
    long = [(right-left).total_seconds() for left,right in internal if (right-left).total_seconds() >= 15]
    typical = median(long) if long else None
    def resource_times(work):
        if not all(load is not None for load in work.values()):
            return None
        return dict(native_g26=work['g26']/2, native_g31=work['g31']/2,
            hf_shared=(work['hf_text']+work['hf_schema'])/2,
            ollama_shared=(work['ds_low']+work['ds_off'])/2,
            global_eight_slots=sum(work.values())/8,
            native_one_second_starts=max(0,profiles['g26']['remaining']+profiles['g31']['remaining']-1))
    resources = resource_times(loads)
    capacity = max(resources.values()) if resources else None
    scenario = capacity+waves['upper']*typical if capacity is not None and typical is not None else None
    conservative = (scenario+AUXILIARY_SECONDS)*1.25+OVERHEAD_SECONDS if scenario is not None else None
    finish = now+timedelta(seconds=conservative) if conservative is not None else None
    stress_resources = resource_times(stress_loads) if all(
        profile['missing_latency_samples']==0 for profile in profiles.values()) else None
    stress_capacity = max(stress_resources.values()) if stress_resources else None
    stress_gap = nearest_rank(long,.95) if long else None
    stress_scenario = stress_capacity+waves['upper']*stress_gap if stress_capacity is not None and stress_gap is not None else None
    stress_conservative = ((stress_scenario+AUXILIARY_SECONDS)*1.25+OVERHEAD_SECONDS
                           if stress_scenario is not None else None)
    stress_finish = now+timedelta(seconds=stress_conservative) if stress_conservative is not None else None
    return dict(schema_version=1,checked_at=now.isoformat(),profiles=profiles,http_counts=dict(statuses),
        observation_start_utc=start.isoformat(),observation_end_utc=now.isoformat(),
        provider_busy_slot_seconds=dict(provider_busy),
        global_network_union_seconds=sum((right-left).total_seconds() for left,right in union(intervals,start,now)),
        global_observed_or_inflight_mask_seconds=sum((right-left).total_seconds() for left,right in merged),
        in_flight=len(starts)-len(seen),global_idle_intervals_available=gaps is not None,
        global_idle_interval_count=len(gaps) if gaps is not None else None,
        global_idle_seconds=sum((right-left).total_seconds() for left,right in gaps) if gaps is not None else None,
        internal_long_idle_threshold_seconds=15,internal_long_idle_count=len(long) if gaps is not None else None,
        internal_long_idle_seconds=sum(long) if gaps is not None else None,
        typical_long_idle_gap_seconds=typical,remaining_completion_wave_scenario=waves,
        shared_resource_seconds=resources,capacity_only_conditional_seconds=capacity,
        capacity_plus_barrier_scenario_seconds=scenario,
        scenario_with_auxiliary_margin_overhead_seconds=conservative,
        scenario_collection_finish_utc=finish.isoformat() if finish else None,
        scenario_margin_to_cutoff_hours=(CUTOFF-finish).total_seconds()/3600 if finish else None,
        scenario_hours_to_submission=(DEADLINE-finish).total_seconds()/3600 if finish else None,
        stress_scenario=dict(
            label='STRESS: recent service worsening and empirical long-pause sensitivity',
            method='Each profile uses max(all observed mean latency,last 100 mean latency); idle gap uses empirical nearest-rank p95 of completed internal >=15s gaps. Apply upper wave count, auxiliary work, 25% margin and 3300s overhead. Not a 95% forecast interval, probabilistic coverage claim, bound or completion guarantee; unobserved outages are not covered.',
            shared_resource_seconds=stress_resources, capacity_only_conditional_seconds=stress_capacity,
            empirical_nearest_rank_p95_idle_seconds=stress_gap,
            capacity_plus_barrier_scenario_seconds=stress_scenario,
            scenario_with_auxiliary_margin_overhead_seconds=stress_conservative,
            collection_finish_utc=stress_finish.isoformat() if stress_finish else None,
            margin_to_cutoff_hours=(CUTOFF-stress_finish).total_seconds()/3600 if stress_finish else None,
            hours_to_submission=(DEADLINE-stress_finish).total_seconds()/3600 if stress_finish else None,
            unavailable_reason='Missing latency samples, missing timestamps, or no completed long idle gaps' if stress_conservative is None else None),
        limitations='Conditional timing scenario, not a bound or completion guarantee. Median completed internal >=15s global-idle gap proxies the two-probe health barrier; network idleness alone does not establish its cause. Draining and scheduling overhead are not fully captured. Service means use completed calls and can be biased downward by in-flight/right-censored slow calls; the recent task mix may differ from remaining work. In-flight jobs receive full mean service load and mask possible idle. Missing timestamps disable idle estimates. Existing cumulative-rate projections already include historical barriers: do not add this overhead to them. The stress scenario is not a probabilistic 95% forecast interval. No outcome accuracy is read.')


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=root/'runs/swarm-ledger-resume-v1-main/readers')
    parser.add_argument('--additional-directory',type=Path,action='append',default=[])
    parser.add_argument('--output-dir',type=Path,default=root/'runs/experiment-sanity-check')
    args=parser.parse_args()
    directories=[args.directory]+args.additional_directory
    terminal=[r for directory in directories for r in rows(directory/'responses.jsonl',True)]
    attempts=[r for directory in directories for r in rows(directory/'attempts.jsonl')]
    value=summarize(attempts,terminal,datetime.now(timezone.utc))
    value['metadata_batches']=[str(directory) for directory in directories]
    args.output_dir.mkdir(parents=True,exist_ok=True)
    name='timing-diagnosis-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
    with (args.output_dir/name).open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(value,handle,indent=2,allow_nan=False);handle.write('\n')
    with (args.output_dir/'timing-diagnosis-history.jsonl').open('a',encoding='utf-8',newline='\n') as handle:
        handle.write(json.dumps(value,allow_nan=False)+'\n');handle.flush();os.fsync(handle.fileno())
    print(json.dumps(value,allow_nan=False))


if __name__=='__main__':main()
