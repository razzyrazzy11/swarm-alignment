"""Conservative remaining-work forecast using frozen operational metadata only."""
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import hashlib,json
from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_complete_dispatch as old

PHASES=('reporter','readers','calibration','influence')
def build(original,spent,now,wallet_available):
    candidate=original['candidates'][0]
    expect=s.expect
    expect(candidate['native_per_model']==candidate['ollama_per_model']==2,'Original capacity differs')
    remaining={p:Decimal(0) for p in ('adaption','hf','ollama')}
    for row in candidate['cost_groups']:
        if row['phase'] in PHASES:
            remaining[s.profile(row['profile_id'])['provider']]+=Decimal(row['projected_peak_cost'])
    # Deliberately retain the ENTIRE original reporter bound, despite 1752/2560
    # already terminal. This is conservative and needs no outcome-dependent fit.
    base=sum((Decimal(x['bottleneck_seconds']) for x in candidate['phase_bounds'] if x['phase'] in PHASES),Decimal(0))
    seconds=base*Decimal('1.25')+Decimal(1800+900+600)
    cutoff=datetime.fromisoformat(original['collection_cutoff_utc'])
    totals={k:Decimal(spent[k])+remaining[k] for k in remaining}
    caps=s.config()['combined_caps']
    budget=all(v<=Decimal(caps[k]) for k,v in totals.items())
    wallet_need=remaining['ollama']/2+Decimal(s.config()['remaining_credit_floor'])+Decimal('.10')
    return dict(schema_version=1,generated_at=now.isoformat(),collection_cutoff_utc=cutoff.isoformat(),
        original_forecast_sha256=hashlib.sha256((s.ROOT/'research/swarm-ledger-complete-forecast.json').read_bytes()).hexdigest(),
        remaining_calls=dict(reporter=808,readers=53760,calibration=240,influence=240,total=55048),
        method='Entire original remaining-phase bounds, including full2560 reporter bound;1.25margin+1800s overhead+900s outage+600s blackout',
        forecast_seconds=str(seconds),deadline_feasible=now.timestamp()+float(seconds)<cutoff.timestamp(),
        projected_remaining_peak_equivalent_cost={k:str(v) for k,v in remaining.items()},
        spent_or_reserved_all_prior_science_and_pilots={k:str(v) for k,v in spent.items()},
        projected_combined_peak_equivalent_cost={k:str(v) for k,v in totals.items()},budget_feasible=budget,
        off_peak_wallet_gate_passed=Decimal(wallet_available)>wallet_need,
        billing='Token-rate forecasts/reservations, not invoices. Adaption units are credits; HF and Ollama units are USD. Ollama off-peak conversion only.',
        uncertainty='Operational forecast, not a completion guarantee; original request bodies/endpoints unchanged; client caps remain binding.')

def create():
    from experiments import swarm_ledger_resume as resume
    output=s.ROOT/'research/router-resume-forecast.json'
    s.expect(not output.exists(),'Never overwrite a forecast')
    combined,_,_=resume.cost_baseline()
    transport=resume.ResumeTransport(s.credentials(),s.ROOT/'runs/router-resume-forecast')
    guard=old.BalanceGuard(transport,'main');guard.check(combined['ollama'],Decimal(0))
    available=guard.available-(combined['ollama']-guard.at_poll)
    original=s.read(s.ROOT/'research/swarm-ledger-complete-forecast.json')
    result=build(original,combined,datetime.now(timezone.utc),available)
    s.expect(all(result[k] is True for k in ('deadline_feasible','budget_feasible','off_peak_wallet_gate_passed')),'Remaining workload fails deadline/budget/wallet gate')
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(created=True,forecast_seconds=result['forecast_seconds'],deadline_feasible=True,budget_feasible=True,off_peak_wallet_gate_passed=True)
if __name__=='__main__':print(json.dumps(create()))
