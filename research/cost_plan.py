"""Reproduce prospective token costing. No network access or credentials used."""
from decimal import Decimal
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def estimate(d,output_tokens=None):
    core=d['episodes']*d['packets_per_episode']*d['prompts']*d['primary_repetitions']
    repeat=d['reliability_episodes']*d['packets_per_episode']*d['prompts']*d['extra_reliability_repetitions']
    pilot=d['pilot_episodes']*d['packets_per_episode']*d['prompts']*d['primary_repetitions']
    input_tokens=d['input_tokens_per_call_assumption']
    output_tokens=d['output_tokens_per_call_assumption'] if output_tokens is None else output_tokens
    rows=[]
    total=Decimal(0)
    for m in d['models']:
        unit=(Decimal(str(input_tokens))*Decimal(m['input'])+Decimal(str(output_tokens))*Decimal(m['output']))/Decimal(1_000_000)
        cost=unit*(core+repeat+pilot)
        total+=cost
        rows.append(dict(model=m['id'],core_calls=core,reliability_extra_calls=repeat,pilot_calls=pilot,
                         estimated_credits=str(cost)))
    return dict(status=d['status'],input_tokens_assumed=input_tokens,output_tokens_assumed=output_tokens,
                total_calls=(core+repeat+pilot)*len(rows),models=rows,
                estimated_total_credits=str(total),
                research_ceiling_credits=d['research_spend_ceiling_credits'],
                remaining_nominal_ceiling=str(Decimal(d['research_spend_ceiling_credits'])-total),
                caveat='Not an invoice or guaranteed upper bound; ignores cached discounts, retries, tools, episode generation and possible billing overhead. Verify account eligibility and actual usage first.')

if __name__=='__main__':
    d=json.loads((ROOT/'adaption-design.json').read_text(encoding='utf-8'))
    print(json.dumps(estimate(d),indent=2))
