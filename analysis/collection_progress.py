"""Operational reader progress projections; never inspect response answers.

This is an unfrozen reporting helper, not a dispatcher or scientific analysis.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path

PLANNED = dict(g26=12800, g31=12800, ds_low=12800,
               hf_text=5120, hf_schema=5120, ds_off=5120)
PROVIDER = dict(g26='adaption', g31='adaption', ds_low='ollama',
                ds_off='ollama', hf_text='hf', hf_schema='hf')
CUTOFF = datetime(2026, 11, 9, 5, 59, tzinfo=timezone.utc)
DEADLINE = datetime(2026, 11, 9, 11, 59, tzinfo=timezone.utc)
AUXILIARY_SECONDS = 80 + 1286.812875
OVERHEAD_SECONDS = 3300


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(value):
    require(isinstance(value, str), 'Timestamp must be a string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timestamp must have timezone')
    return result.astimezone(timezone.utc)


def read_metadata(path, terminal=False):
    """Drop only a concurrently incomplete final line; retain no answer fields."""
    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    if lines and not lines[-1].endswith(b'\n'):
        lines.pop()
    result = []
    for line in lines:
        require(bool(line.strip()), 'Blank complete journal record')
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                require(key not in result, 'Duplicate JSON object key')
                result[key] = value
            return result
        row = json.loads(line, object_pairs_hook=unique_object)
        require(type(row) is dict, 'Journal record must be an object')
        safe = {key: row.get(key) for key in ('id', 'profile_id')}
        if terminal:
            transport = row.get('transport')
            require(type(transport) is dict, 'Terminal transport required')
            safe.update(latency_seconds=transport.get('latency_seconds'),
                        http_status=transport.get('http_status'),
                        known_usage=row.get('known_usage'), anomaly=row.get('anomaly'))
        else:
            safe['started'] = row.get('started')
        result.append(safe)
    return result


def project(attempts, terminals, now):
    require(now.tzinfo is not None, 'Current time must have timezone')
    now = now.astimezone(timezone.utc)
    started = {}
    for row in attempts:
        identity, profile = row.get('id'), row.get('profile_id')
        require(type(identity) is str and bool(identity), 'Invalid attempt identity')
        require(profile in PLANNED, 'Foreign attempt profile')
        require(identity not in started, 'Duplicate attempt identity')
        when = stamp(row.get('started'))
        require(when <= now, 'Attempt timestamp lies in future')
        started[identity] = (profile, when)
    observed = {p: [] for p in PLANNED}
    counts, statuses, unknown, anomalies = Counter(), Counter(), Counter(), Counter()
    seen = set()
    for row in terminals:
        identity, profile = row.get('id'), row.get('profile_id')
        require(type(identity) is str and bool(identity), 'Invalid terminal identity')
        require(profile in PLANNED, 'Foreign terminal profile')
        require(identity not in seen, 'Duplicate terminal identity')
        require(identity in started and started[identity][0] == profile,
                'Terminal must match a started identity and profile')
        seen.add(identity)
        latency = row.get('latency_seconds')
        require(latency is None or (type(latency) in (int, float)
                and math.isfinite(latency) and latency >= 0), 'Invalid latency')
        http = row.get('http_status')
        require(http is None or (type(http) is int and 100 <= http <= 599), 'Invalid HTTP status')
        require(type(row.get('known_usage')) is bool, 'Invalid usage flag')
        require(row.get('anomaly') is None or type(row['anomaly']) is bool, 'Invalid anomaly flag')
        counts[profile] += 1
        statuses[str(http)] += 1
        unknown[profile] += not row['known_usage']
        anomalies[profile] += bool(row.get('anomaly'))
        if latency is not None:
            observed[profile].append(latency)
    start_counts = Counter(p for p, _ in started.values())
    require(all(start_counts[p] <= PLANNED[p] for p in PLANNED), 'Started count exceeds plan')
    elapsed = (now - min((t for _, t in started.values()), default=now)).total_seconds()
    profiles, service_load, linear = {}, {}, []
    for profile, planned in PLANNED.items():
        completed, remaining = counts[profile], planned - counts[profile]
        rate = completed / elapsed if elapsed > 0 else 0
        seconds = remaining / rate if rate else (0 if remaining == 0 else None)
        mean = sum(observed[profile]) / len(observed[profile]) if observed[profile] else None
        load = remaining * mean if mean is not None else (0 if remaining == 0 else None)
        profiles[profile] = dict(planned=planned, started=start_counts[profile], terminal=completed,
            in_flight=start_counts[profile]-completed, remaining=remaining,
            observed_calls_per_minute=rate*60, linear_remaining_seconds=seconds,
            observed_mean_service_seconds=mean, latency_samples=len(observed[profile]),
            missing_latency=completed-len(observed[profile]), unknown_usage=unknown[profile],
            anomalies=anomalies[profile])
        service_load[profile] = load
        linear.append(seconds)
    old_seconds = max(linear) if all(x is not None for x in linear) else None
    conservative = ((old_seconds + AUXILIARY_SECONDS)*1.25 + OVERHEAD_SECONDS
                    if old_seconds is not None else None)
    resources = None
    if all(x is not None for x in service_load.values()):
        resources = dict(native_g26_model=service_load['g26']/2,
            native_g31_model=service_load['g31']/2,
            hf_shared_provider=(service_load['hf_text']+service_load['hf_schema'])/2,
            ollama_shared_provider=(service_load['ds_off']+service_load['ds_low'])/2,
            global_eight_slots=sum(service_load.values())/8,
            native_one_second_start_spacing=max(0, sum(profiles[p]['remaining']
                for p in ('g26','g31'))-1))
    bound = max(resources.values()) if resources else None
    def finish(seconds):
        return (now + timedelta(seconds=seconds)).isoformat() if seconds is not None else None
    finish_dt = now + timedelta(seconds=conservative) if conservative is not None else None
    optimistic_dt = now + timedelta(seconds=bound) if bound is not None else None
    return dict(schema_version=1, checked_at=now.isoformat(), reader_elapsed_seconds=elapsed,
        profiles=profiles, http_counts=dict(statuses), total_in_flight=len(started)-len(seen),
        cumulative_reader_seconds=old_seconds, cumulative_reader_finish_utc=finish(old_seconds),
        conservative_collection_seconds=conservative, conservative_collection_finish_utc=finish(conservative),
        conservative_margin_to_cutoff_hours=(CUTOFF-finish_dt).total_seconds()/3600 if finish_dt else None,
        conservative_hours_remaining_to_submission=(DEADLINE-finish_dt).total_seconds()/3600 if finish_dt else None,
        shared_capacity_resource_seconds=resources, optimistic_conditional_reader_seconds=bound,
        optimistic_conditional_reader_finish_utc=finish(bound),
        optimistic_conditional_reader_margin_to_cutoff_hours=(CUTOFF-optimistic_dt).total_seconds()/3600 if optimistic_dt else None,
        optimistic_conditional_reader_hours_remaining_to_submission=(DEADLINE-optimistic_dt).total_seconds()/3600 if optimistic_dt else None,
        collection_cutoff_utc=CUTOFF.isoformat(), submission_deadline_utc=DEADLINE.isoformat(),
        auxiliary_seconds=AUXILIARY_SECONDS, margin_multiplier=1.25, overhead_seconds=OVERHEAD_SECONDS,
        method='Cumulative per-profile rates retain the prior conservative extrapolation. Shared-capacity loads use observed mean service time weighted by remaining jobs, including in-flight jobs; HF and Ollama profiles share two slots each, native models two each, global eight, native starts one second apart.',
        limits='The resource maximum is a capacity-only conditional scenario estimate under unchanged future mean service times, not a hard wall-clock bound or completion guarantee. In-flight jobs are charged a full observed mean service time, so this is not a mathematical lower bound. It omits queueing, future failures, pacing/backoffs and auxiliary work. Missing latency samples are disclosed; no projection changes any guard or schedule. No answer accuracy is inspected.')


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempts', type=Path, default=root/'runs/swarm-ledger-resume-v1-main/readers/attempts.jsonl')
    parser.add_argument('--responses', type=Path, default=root/'runs/swarm-ledger-resume-v1-main/readers/responses.jsonl')
    parser.add_argument('--output-dir', type=Path, default=root/'runs/experiment-sanity-check')
    args = parser.parse_args()
    # Read terminals first: a concurrent new terminal must already have a start.
    terminals = read_metadata(args.responses, terminal=True)
    attempts = read_metadata(args.attempts)
    result = project(attempts, terminals, datetime.now(timezone.utc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    name = 'capacity-projection-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
    with (args.output_dir/name).open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    with (args.output_dir/'capacity-projection-history.jsonl').open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(result, allow_nan=False)+'\n')
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
