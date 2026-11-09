"""Recompute redacted development aggregates from retained, ignored runs."""
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from experiments.access import ROOT
from experiments.oracle import compatible_labels,decision
from experiments.pilot import classify,digest

RUNS=('pilot-development-v1','pilot-qualification-v2','pilot-development-v3','pilot-development-v4')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def readrows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]

def aggregate():
    report=dict(status='development only; no confirmatory estimates',oracle_validation=dict(worlds_per_authorization=108,
        valid_world_mask_checks=55296,independent_constraint_checker=True,scope='one toy grammar; not arbitrary trace histories'),
        batches={},known_provider_reported_adaption_cost=Decimal(0),credit_reconciliation='Final balance not re-read after browser connection failure; interrupted v1 has unresolved unreturned calls.')
    example=None
    released=[]
    for name in RUNS:
        folder=ROOT/'runs'/name
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        tasks=json.loads((folder/'packets.json').read_text(encoding='utf-8'))
        lookup={(t['episode_id'],t['mechanism']):t for t in tasks}
        rows=readrows(folder/'responses.jsonl')
        costs=[]
        for r in rows:
            t=lookup[(r['episode_id'],r['mechanism'])]
            labels=compatible_labels(t['packet'])
            if labels!=set(t['compatible_labels']) or digest(t['packet'])!=r['packet_sha256']:
                raise ValueError('Packet/reference integrity failure')
            recomputed=classify(r.get('response'),labels)
            if recomputed!=r['scored']:raise ValueError('Retained/recomputed score disagreement')
            raw_cost=((r.get('response') or {}).get('usage') or {}).get('cost')
            if type(raw_cost) in (int,float):
                amount=Decimal(str(raw_cost))
                if amount.is_finite() and amount>=0:costs.append(amount)
            if name=='pilot-development-v4' and example is None and recomputed['unsupported_executor']:
                example=dict(model=r['model'],mechanism=r['mechanism'],packet=t['packet'],
                    complete_history_label=t['true_label'],compatible_labels=sorted(labels),
                    actual_output=(r['response'] or {}).get('output_text'),
                    explanation='A definite worker name is unsupported because the visible packet permits several executor labels. This is an observed development error, not collusive intent.')
        batch=dict(planned_calls=manifest['calls'],retained_responses=len(rows),
            episodes_with_any_response=len({r['episode_id'] for r in rows}),
            status='interrupted; unreturned calls unknown or unstarted' if name.endswith('v1') else json.loads((folder/'summary.json').read_text())['status'],
            raw_responses_sha256=sha(folder/'responses.jsonl'),manifest_sha256=sha(folder/'manifest.json'),
            provider_reported_cost_known_responses=str(sum(costs,Decimal(0))),models={})
        if (folder/'attempts.jsonl').exists():
            attempts=readrows(folder/'attempts.jsonl')
            batch['journaled_attempts']=len(attempts)
            batch['attempted_without_retained_response']=len(attempts)-len(rows)
        else:batch['journaled_attempts']=None
        for model in manifest['models']:
            rs=[r for r in rows if r['model']==model]
            batch['models'][model]=dict(calls=len(rs),http_200=sum(r['transport']['http_status']==200 for r in rs),
                **{k:sum(r['scored'][k] for r in rs) for k in ('grounded_correct','unsupported_executor','unsupported_none','supported_definite')},
                invalid=sum(r['scored']['status']=='INVALID' for r in rs),
                incomplete=sum((r.get('response') or {}).get('status')=='incomplete' for r in rs),
                mean_latency_seconds=round(sum(r['transport'].get('latency_seconds',0) for r in rs)/len(rs),3) if rs else None)
        if name=='pilot-development-v4':
            for r in rows:
                t=lookup[(r['episode_id'],r['mechanism'])]
                released.append(dict(episode_id=r['episode_id'],mechanism=r['mechanism'],model=r['model'],
                    packet=t['packet'],packet_sha256=r['packet_sha256'],complete_history_label=t['true_label'],
                    compatible_labels=t['compatible_labels'],response_status=(r['response'] or {}).get('status'),
                    actual_output=(r['response'] or {}).get('output_text'),scored=r['scored'],
                    latency_seconds=r['transport']['latency_seconds']))
            batch['structural_by_view']={}
            for mechanism in ('full','random','targeted'):
                ts=[t for t in tasks if t['mechanism']==mechanism]
                batch['structural_by_view'][mechanism]=dict(packets=len(ts),singleton=sum(len(t['compatible_labels'])==1 for t in ts),
                    ambiguous=sum(len(t['compatible_labels'])>1 for t in ts))
            batch['deterministic_same_packet']=dict(calls=len(tasks),grounded_correct=len(tasks),supported_definite=sum(len(t['compatible_labels'])==1 for t in tasks))
            batch['always_abstain']=dict(calls=len(tasks),grounded_correct=sum(len(t['compatible_labels'])>1 for t in tasks),supported_definite=0)
            for model,stats in batch['models'].items():
                rs=[r for r in rows if r['model']==model]
                stats['clean_worker_accusation_calls']=sum(r['true_label']=='NONE' and r['scored']['status']=='EXECUTOR' for r in rs)
                stats['by_view']={m:dict(calls=sum(r['mechanism']==m for r in rs),grounded_correct=sum(r['scored']['grounded_correct'] for r in rs if r['mechanism']==m),unsupported_executor=sum(r['scored']['unsupported_executor'] for r in rs if r['mechanism']==m),unsupported_none=sum(r['scored']['unsupported_none'] for r in rs if r['mechanism']==m),invalid=sum(r['scored']['status']=='INVALID' for r in rs if r['mechanism']==m)) for m in ('full','random','targeted')}
        report['batches'][name]=batch
        report['known_provider_reported_adaption_cost']+=sum(costs,Decimal(0))
    influence=ROOT/'runs/influence-development-v1'
    ir=readrows(influence/'responses.jsonl')
    report['influence']=json.loads((influence/'summary.json').read_text())
    report['influence']['source_states']=4
    report['influence']['raw_responses_sha256']=sha(influence/'responses.jsonl')
    icost=sum((Decimal(str(((r.get('response') or {}).get('usage') or {}).get('cost',0))) for r in ir),Decimal(0))
    report['influence']['provider_reported_cost']=str(icost)
    report['known_provider_reported_adaption_cost']+=icost
    report['known_provider_reported_adaption_cost']=str(report['known_provider_reported_adaption_cost'])
    hf=ROOT/'runs/hf-smoke-v1'
    report['hugging_face_smoke']=json.loads((hf/'summary.json').read_text())
    report['hugging_face_smoke']['raw_responses_sha256']=sha(hf/'responses.jsonl')
    target=ROOT/'data';target.mkdir(exist_ok=True)
    cases=target/'development_reader_cases.jsonl'
    cases.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in sorted(released,key=lambda r:(r['episode_id'],r['mechanism'],r['model']))),encoding='utf-8',newline='\n')
    episodes=target/'development_episodes.json'
    episodes.write_text((ROOT/'runs/pilot-development-v4/episodes.json').read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    report['released_development_data']=dict(cases_sha256=sha(cases),episodes_sha256=sha(episodes),
        scope='Sanitized fake episodes and actual final-answer text; no keys, provider IDs, request headers or native reasoning outputs. Development only.')
    (ROOT/'research/pilot-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if example:
        target=ROOT/'research/fixtures';target.mkdir(exist_ok=True)
        (target/'unsupported-development-example.json').write_text(json.dumps(example,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    r=aggregate()
    print(json.dumps(dict(batches={k:dict(status=v['status'],retained=v['retained_responses']) for k,v in r['batches'].items()},
        known_provider_reported_adaption_cost=r['known_provider_reported_adaption_cost'],
        fixed_batch=r['batches']['pilot-development-v4'],influence_calls=r['influence']['calls']),indent=2))
