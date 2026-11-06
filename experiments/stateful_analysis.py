"""Rescore frozen main study; cluster inference by source episode, never views."""
import argparse,json,random,math
from decimal import Decimal
from pathlib import Path
from experiments.access import ROOT
from experiments.pilot import classify,digest
from experiments.stateful import compatible_labels,simulate
from experiments.stateful_study import verify_freeze,config,sha,FREEZE,prepare

def quantile(xs,p):
    ys=sorted(xs);position=(len(ys)-1)*p;lo=int(position);hi=min(lo+1,len(ys)-1)
    return ys[lo]+(ys[hi]-ys[lo])*(position-lo)

def bootstrap(groups,seed,n):
    rng=random.Random(seed)
    if not groups or any(not values for values in groups.values()):raise ValueError('Empty stratum')
    estimates=[]
    for _ in range(n):
        selected=[rng.choice(values) for values in groups.values() for _ in range(len(values))]
        estimates.append(sum(selected)/len(selected))
    return [quantile(estimates,.025),quantile(estimates,.975)]

def analyze(out):
    verify_freeze();c=config();out=Path(out)
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    summary=json.loads((out/'summary.json').read_text(encoding='utf-8')) if (out/'summary.json').exists() else dict(stage=manifest['stage'],complete=False,freeze_sha256=sha(FREEZE))
    if manifest['freeze']['source_sha256']!=json.loads(FREEZE.read_text())['source_sha256'] or summary['freeze_sha256']!=sha(FREEZE):raise ValueError('Run freeze mismatch')
    packets=json.loads((out/'packets.json').read_text(encoding='utf-8'));episodes=json.loads((out/'episodes.json').read_text(encoding='utf-8'))
    expected_episodes,expected_packets=prepare(summary['stage'])
    if episodes!=expected_episodes or packets!=expected_packets:raise ValueError('Frozen source/task replay mismatch')
    planned={t['task_id']:t for t in packets};sources={e['episode_id']:e for e in episodes}
    rows=[json.loads(s) for s in (out/'responses.jsonl').read_text(encoding='utf-8').splitlines()]
    attempts=[json.loads(s) for s in (out/'attempts.jsonl').read_text(encoding='utf-8').splitlines()]
    started={(r['task_id'],r['model']):r for r in attempts}
    if len(started)!=len(attempts):raise ValueError('Duplicate journaled start')
    seen=set()
    for row in rows:
        t=row['task'];ident=(t['task_id'],row['model'])
        if ident in seen or t['task_id'] not in planned or t!=planned[t['task_id']] or row['model'] not in c['models'] or ident not in started:raise ValueError('Duplicate/unplanned response')
        seen.add(ident);labels=compatible_labels(t['packet'])
        if sorted(labels)!=t['compatible_labels'] or digest(t['packet'])!=t['packet_sha256'] or classify(row['response'],labels)!=row['scored']:raise ValueError('Rescoring mismatch')
        source=sources[t['episode_id']]
        if simulate(source['public'],source['world'],t['churn'])['label'] not in labels:raise ValueError('Truth missing')
    if summary['complete'] and len(seen)!=len(packets)*len(c['models']):raise ValueError('Incomplete run labeled complete')
    report=dict(stage=summary['stage'],complete=summary['complete'],source_episodes=len(sources),planned_calls=len(packets)*len(c['models']),
                attempted_calls=len(attempts),retained_responses=len(rows),missing_calls=len(packets)*len(c['models'])-len(rows),
                journaled_without_response=len(set(started)-seen),unknown_reserved_liability=str(sum((Decimal(started[k]['reserved_credits']) for k in set(started)-seen),Decimal(0))),
                models={},baselines={},inference_scope='Finite scripted-world design; journaled starts can include dispatch-uncertain calls; no population or collusion claim')
    for model in c['models']:
        rs=[r for r in rows if r['model']==model]
        groups={}
        for r in rs:
            t=r['task'];key=f"{t['family']}/{t['cohort']}/churn={t['churn']}/{t['mechanism']}/{t['restoration']}"
            counts=groups.setdefault(key,dict(calls=0,grounded_correct=0,supported_definite=0,unsupported_executor=0,unsupported_none=0,invalid=0,singleton=0))
            counts['calls']+=1
            for k in ('grounded_correct','supported_definite','unsupported_executor','unsupported_none'):counts[k]+=r['scored'][k]
            counts['invalid']+=r['scored']['status']=='INVALID';counts['singleton']+=len(t['compatible_labels'])==1
        effects={};paired={}
        for r in rs:
            t=r['task'];paired[(t['episode_id'],t['churn'],t['mechanism'],t['restoration'])]=r
        # Estimate only after the entire frozen grid completed. Partial batches
        # retain descriptive counts without presenting favorable-prefix effects.
        if summary['complete'] and summary['stage']=='main':
            for name in ('primary_unsupported_targeted_minus_random','secondary_churn_interaction','restoration_grounded_priority_minus_random','restoration_coverage_priority_minus_none'):
                strata={};vals=[];perfamily={}
                for eid,e in sources.items():
                    def score(churn,mechanism,restoration,metric):return paired[eid,churn,mechanism,restoration]['scored'][metric]
                    if name.startswith('primary'):
                        value=score(True,'targeted','none','unsupported_executor')-score(True,'random','none','unsupported_executor')
                    elif name=='secondary_churn_interaction':
                        value=(score(True,'targeted','none','unsupported_executor')-score(True,'random','none','unsupported_executor'))-(score(False,'targeted','none','unsupported_executor')-score(False,'random','none','unsupported_executor'))
                    elif name=='restoration_grounded_priority_minus_random':
                        value=score(True,'targeted','priority','grounded_correct')-score(True,'targeted','random','grounded_correct')
                    else:value=score(True,'targeted','priority','supported_definite')-score(True,'targeted','none','supported_definite')
                    vals.append(value);strata.setdefault((e['family'],e['cohort']),[]).append(value);perfamily.setdefault(e['family'],[]).append(value)
                effects[name]=dict(estimate=sum(vals)/len(vals),episode_n=len(vals),ci95=bootstrap(strata,c['bootstrap_seed'],c['bootstrap_resamples']),
                                   by_family={k:dict(n=len(v),estimate=sum(v)/len(v)) for k,v in perfamily.items()},secondary=not name.startswith('primary') or model!=c['primary_model'])
            clean=[e for e in sources.values() if e['cohort']=='clean']
            false=sum(any(paired[e['episode_id'],True,m,'none']['scored']['status']=='EXECUTOR' for m in ('targeted','random')) for e in clean)
            effects['clean_episode_false_accusation']=dict(events=false,n=len(clean),zero_event_upper95=(1-.05**(1/len(clean))) if false==0 else None,
                caveat='Zero-event bound assumes independent source draws; views do not increase n. Not deployment prevalence.')
        report['models'][model]=dict(counts=groups,effects=effects)
    for name in ('exact_packet','always_abstain','fixed_actor_A'):
        supported=grounded=unsupported=0
        for t in packets:
            labels=set(t['compatible_labels'])
            if name=='exact_packet':grounded+=1;supported+=len(labels)==1
            elif name=='always_abstain':grounded+=len(labels)>1
            else:grounded+=labels=={'A'};supported+=labels=={'A'};unsupported+=labels!={'A'}
        report['baselines'][name]=dict(packets=len(packets),grounded_correct=grounded,supported_definite=supported,unsupported_executor=unsupported)
    (out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='runs/stateful-main');a=p.parse_args()
    r=analyze(ROOT/a.out);print(json.dumps({k:v for k,v in r.items() if k not in ('models','baselines')},indent=2))
