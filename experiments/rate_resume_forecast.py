"""Prospective rate-continuation forecast with an explicit authoring reserve."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import math
from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_complete_dispatch as dispatch

OUTPUT=s.ROOT/'research/rate-resume-forecast.json'
PHASES=('readers','calibration','influence')
COLLECTION_CUTOFF_UTC='2026-11-09T07:56:00+00:00'
TARGET_DRAINED_UTC='2026-11-09T08:00:00+00:00'
SUBMISSION_DEADLINE_UTC='2026-11-09T11:59:00+00:00'


def build(original, remaining, spent, caps, timing, now, wallet_available):
    candidate=original['candidates'][0]
    s.expect(candidate['native_per_model']==candidate['ollama_per_model']==2,'Registered capacity differs')
    costs={p:Decimal(0) for p in ('adaption','hf','ollama')}
    covered=set()
    for group in candidate['cost_groups']:
        key=(group['phase'],group['profile_id'])
        if key not in remaining:continue
        n=remaining[key]
        s.expect(type(n) is int and 0<=n<=group['calls'],'Remaining group count invalid')
        costs[s.profile(key[1])['provider']]+=Decimal(group['projected_peak_cost'])*n/Decimal(group['calls'])
        covered.add(key)
    s.expect(covered==set(remaining),'Original cost-model group missing')
    # Thirty-two bounded500 pauses remain possible. Do not assume that500
    # means an unapplied request, nor estimate away unknown-cost reservations.
    seconds=Decimal(str(timing['stress_scenario']['scenario_with_auxiliary_margin_overhead_seconds']))+Decimal(32*60+900+900)
    s.expect(seconds.is_finite() and seconds>0,'Missing/nonfinite prospective timing')
    # The old forecast remains an immutable cost/service source. Its05:59
    # authoring buffer was not the official AoE submission deadline. The user
    # corrected that distinction before this separate prospective registration.
    cutoff=datetime.fromisoformat(COLLECTION_CUTOFF_UTC)
    submission=datetime.fromisoformat(SUBMISSION_DEADLINE_UTC)
    drained=datetime.fromisoformat(TARGET_DRAINED_UTC)
    combined={p:Decimal(spent[p])+costs[p] for p in costs}
    end=now+timedelta(seconds=float(seconds))
    offpeak=dispatch.off_peak(now) and dispatch.off_peak(cutoff-timedelta(microseconds=1)) and cutoff-now<timedelta(days=1)
    wallet_need=costs['ollama']/2+Decimal(s.config()['remaining_credit_floor'])+Decimal('.10')
    return dict(schema_version=1,generated_at=now.isoformat(),collection_cutoff_utc=cutoff.isoformat(),
        original_collection_cutoff_utc=original['collection_cutoff_utc'],
        target_drained_utc=drained.isoformat(),submission_deadline_utc=submission.isoformat(),
        # Dispatch here means scheduler admission, before retained native pacing.
        latest_dispatch_to_target_drain_seconds=int((drained-cutoff).total_seconds()),
        validation_paper_reserve_seconds=int((submission-drained).total_seconds()),
        remaining_calls_by_profile_and_phase={phase+':'+profile:n for (phase,profile),n in sorted(remaining.items())},
        remaining_calls={phase:sum(n for (p,_),n in remaining.items() if p==phase) for phase in PHASES},
        projected_remaining_peak_equivalent_cost={p:str(v) for p,v in costs.items()},
        spent_or_reserved_all_prior_science_and_pilots={p:str(v) for p,v in spent.items()},
        projected_combined_peak_equivalent_cost={p:str(v) for p,v in combined.items()},
        budget_feasible=all(combined[p]<=Decimal(caps[p]) for p in combined),
        off_peak_wallet_gate_passed=bool(offpeak and Decimal(wallet_available)>wallet_need),
        forecast_seconds=str(seconds),conditional_finish_utc=end.isoformat(),deadline_feasible=end<cutoff,
        method='Original per-profile/phase cost projections scaled only by exact unstarted counts; observed shared-capacity/recent-service/p95-barrier stress plus32x60s server-error default pauses, one900s HFavailability episode and one900s Adaption rate episode (not every allowed future wait). Existing auxiliary,25%headroom,3300s outage/blackout/overhead retained. New prospective07:56dispatch cutoff targets08:00drain and preserves3h59 for strict validation/paper before the user-confirmed official11:59UTC deadline; old05:59registration remains intact.',
        uncertainty='Conditional on a newly admitted active collector; not a guarantee, bound or probability. No speedup from the eligibility optimization is assumed in this forecast. No successful-answer selection or outcome accuracy inspected. Unknown terminal usage keeps full reservation; live caps and wallet floor remain binding.',
        billing='Adaption credits; HF/Ollama USD peak equivalents. Off-peak wallet conversion only, private balance never serialized.')


def create():
    from experiments import swarm_ledger_rate as resume
    from analysis import collection_timing as timing
    s.expect(not OUTPUT.exists(),'Never overwrite a registered forecast')
    resume.stopped_prefix_gate()
    remaining={};descriptors={}
    with s.verified_config():
        for phase in PHASES:
            jobs=resume.main_jobs(phase)
            pending=resume.pending_jobs(phase,jobs)
            descriptors[phase]=resume.digest(pending)
            counts=Counter(j['profile_id'] for j in pending)
            remaining.update({(phase,p):n for p,n in counts.items()})
    combined,_,_=resume.cost_baseline()
    transport=resume.ResumeTransport(s.credentials(),s.ROOT/'runs/rate-resume-forecast')
    guard=dispatch.BalanceGuard(transport,'main');guard.check(combined['ollama'],Decimal(0))
    available=guard.available-(combined['ollama']-guard.at_poll)
    bases=[s.ROOT/'runs'/name/'readers' for name in ('swarm-ledger-resume-v1-main','swarm-ledger-resume-v2-main','swarm-ledger-resume-v3-main','swarm-ledger-efficient-v1-main')]
    terminals=[row for base in bases for row in timing.rows(base/'responses.jsonl',True)]
    attempts=[row for base in bases for row in timing.rows(base/'attempts.jsonl')]
    at=datetime.now(timezone.utc)
    projected=timing.summarize(attempts,terminals,at)
    result=build(s.read(s.ROOT/'research/swarm-ledger-complete-forecast.json'),remaining,combined,
        dispatch.execution_config('main','readers')['combined_caps'],projected,at,available)
    s.expect(all(result[k] is True for k in ('deadline_feasible','budget_feasible','off_peak_wallet_gate_passed')),
             'Prospective deadline/budget/wallet gate failed')
    result['unstarted_descriptor_sha256']=descriptors
    result['source_metadata_sha256']={p.relative_to(s.ROOT).as_posix():resume.raw_sha(p)
        for p in [p for base in bases for p in (base/'attempts.jsonl',base/'responses.jsonl')]+[s.ROOT/'research/swarm-ledger-complete-forecast.json']}
    with OUTPUT.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    return {k:result[k] for k in ('forecast_seconds','conditional_finish_utc','deadline_feasible','budget_feasible','off_peak_wallet_gate_passed','remaining_calls')}


if __name__=='__main__':print(json.dumps(create()))
