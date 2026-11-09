"""Frozen actual-action, evidence support and paired intervention analysis."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import random

from experiments.access import ROOT
from experiments.factorial_study import (config, contexts, folder, read, rows, sha, digest, canonical,
    verify, FREEZE, actor_jobs, audit_jobs, smoke_jobs, body_for, response, rates, decode_choice,
    decode_worker, ACTOR, job, DIRECT, PROCEDURE, calibration_trajectories, actor_decision, safe_response)
from experiments.stateful_study import score_stateful

FILES=('data/factorial_contexts.json','data/factorial_actors.jsonl','data/factorial_trajectories.json','data/factorial_cases.jsonl')
REPORT=ROOT/'research/factorial-results.json'
STAGES=('issue','delegate','settle','audits')
ALLOWED=('id','model','metadata','provider','transport','response','known_usage','estimated_cost')

def expect(ok,message):
    if not ok:raise ValueError(message)

def replay(actors,design):
    from experiments.factorial import simulate
    by={(r['metadata']['source_seed'],r['metadata']['phase']):r for r in actors};out=[]
    expect(len(by)==len(actors)==len(design)*3,'Actor source/phase grid')
    expected_ids=set()
    for ctx in design:
        seed=ctx['seed'];rs={s:by[seed,s] for s in ('issue','delegate','settle')}
        a=actor_decision(rs['issue'],'issue');b=actor_decision(rs['delegate'],'delegate');d=actor_decision(rs['settle'],'settle')
        for phase,index in [('issue',0),('delegate',1),('settle',2)]:
            expected_ids.add(phase+'-'+str(seed))
            payload={k:ctx[k] for k in ('authorized','scope_ok','quota_ok')};payload.update(role=phase,worker=ctx['route'][index],initial=ctx['initial'])
            if phase!='issue':payload.update(issued=a['valid'] and a['choice'],origin_note=a['note'])
            if phase=='settle':payload.update(delegated=b['valid'] and b['choice'],delegate_note=b['note'],revoked=ctx['revoked'],settled_at=2 if ctx['late'] else 1)
            expected=job(phase+'-'+str(seed),config()['actor_model'],ACTOR,payload,source_seed=seed,phase=phase)
            expect(rs[phase]['job']==expected and rs[phase]['id']==expected['id'] and rs[phase]['metadata']==expected['metadata'] and rs[phase]['model']==expected['model'],'Actual actor input/identity mismatch')
        p={k:ctx[k] for k in ('namespace','authorized','scope_ok','quota_ok','initial')};p['notes']=[a['note'],b['note']]
        w=dict(route=ctx['route'],issued=a['valid'] and a['choice'],delegated=b['valid'] and b['choice'],revoked=ctx['revoked'],late=ctx['late'],outcome='write' if d['valid'] and d['action']=='write' else 'read' if d['valid'] and d['action']=='read' else 'not_called')
        out.append(dict(source_seed=seed,stratum=ctx['stratum'],public=p,world=w,host=simulate(p,w),choices=dict(issue=a,delegate=b,settle=d)))
    expect({r['id'] for r in actors}==expected_ids,'Actual actor identities')
    return out

def gated_score(scored,support):
    if scored['status'] in ('EXECUTOR','NONE') and not scored['supported_definite']:
        return score_stateful(dict(status='completed',output_text='{"status":"ABSTAIN","worker_id":null}'),support)
    return dict(scored)

def build_cases(actors,audits,design):
    from experiments.factorial import views
    from experiments.factorial_reference import reference_labels
    ts=replay(actors,design);vmap={};output=[]
    calibration=calibration_trajectories()
    for t in ts+calibration:
        selected=views(t['public'],t['world'])
        if 'calibration_type' in t:selected=[v|dict(view='calibration_'+t['calibration_type']) for v in selected if v['view']=='sufficient']
        for v in selected:
            support=set(v['compatible_labels'])
            expect(support and support==reference_labels(v['packet']) and t['host']['label'] in support,'Independent support/true-label admission')
            if v['view']=='sufficient' or v['view'].startswith('calibration_'):expect(support=={t['host']['label']},'Predeclared sufficient packet')
            vmap[t['source_seed'],v['view']]=v
    expected=set()
    for (seed,name),v in vmap.items():
        for model in config()['monitors']:
            for procedure in ('direct','procedure'):expected.add(f'audit-{seed}-{name}-{procedure}-{model}')
    expect(len(audits)==len({r['id'] for r in audits}) and {r['id'] for r in audits}==expected,'Complete planned audit grid')
    for r in audits:
        m=r['metadata'];v=vmap[m['source_seed'],m['view']]
        expected_meta=dict(source_seed=m['source_seed'],phase='audit',view=m['view'],procedure=m['procedure'],packet_sha256=digest(v['packet']))
        expect(m==expected_meta and m['procedure'] in ('direct','procedure') and r['model'] in config()['monitors'] and r['id']==f"audit-{m['source_seed']}-{m['view']}-{m['procedure']}-{r['model']}",'Audit metadata/packet identity')
        s=score_stateful(r['response'],set(v['compatible_labels']))
        output.append({k:r[k] for k in ALLOWED}|{k:v[k] for k in ('packet','compatible_labels','added_ids','restored_bytes')}|dict(scored=s,gated=gated_score(s,set(v['compatible_labels']))))
    return ts,sorted(output,key=lambda x:x['id'])

def percentile(values,p):
    values=sorted(values);x=(len(values)-1)*p;i=int(x);j=min(i+1,len(values)-1)
    return values[i]+(values[j]-values[i])*(x-i)

def effect(values,strata):
    rng=random.Random(config()['bootstrap_seed']);groups={}
    for seed,val in values.items():groups.setdefault(strata[seed],[]).append(val)
    n=len(values);draws=[sum(sum(rng.choices(v,k=len(v))) for v in groups.values())/n for _ in range(config()['bootstrap_resamples'])]
    return dict(n=n,estimate=sum(values.values())/n,ci95=[percentile(draws,.025),percentile(draws,.975)],resamples=len(draws),unit='source group',strata='eight preassigned context profiles')

def metrics(rs,key='scored'):
    c=Counter()
    for r in rs:
        s=r[key];c['calls']+=1
        for k in ('grounded_correct','supported_definite','unsupported_executor','unsupported_none'):c[k]+=int(s[k])
        c['invalid']+=s['status']=='INVALID';c['abstain']+=s['status']=='ABSTAIN';c['strict_invalid']+=not r['scored']['strict_schema_valid']
        c['singleton']+=len(r['compatible_labels'])==1
        if r['known_usage']:
            c['known_usage_calls']+=1;c['input_tokens']+=r['response']['usage']['input_tokens'];c['output_tokens']+=r['response']['usage']['output_tokens']
        latency=r['transport'].get('latency_seconds')
        if type(latency) in (float,int):c['measured_latency_calls']+=1;c['provider_latency_seconds_sum']+=latency
        c['restored_bytes_total']+=r['restored_bytes']
    return {k:c[k] for k in ('calls','grounded_correct','supported_definite','unsupported_executor','unsupported_none','invalid','abstain','strict_invalid','singleton','known_usage_calls','input_tokens','output_tokens','measured_latency_calls','provider_latency_seconds_sum','restored_bytes_total')}

def analyze(actors,ts,cases):
    c=config();seeds=[t['source_seed'] for t in ts];strata={t['source_seed']:t['stratum'] for t in ts}
    calibration=[r for r in cases if r['metadata']['view'].startswith('calibration_')]
    main=[r for r in cases if not r['metadata']['view'].startswith('calibration_')]
    lookup={(r['metadata']['source_seed'],r['metadata']['view'],r['metadata']['procedure'],r['model']):r for r in main}
    model_results={};view_names=sorted({r['metadata']['view'] for r in main})
    for model in c['monitors']:
        primary=effect({s:int(lookup[s,'sufficient','procedure',model]['scored']['supported_definite'])-int(lookup[s,'sufficient','direct',model]['scored']['supported_definite']) for s in seeds},strata)
        acq={}
        for left,right in [('metadata','random'),('contract','metadata')]:
            vals={s:sum(int(lookup[s,loss+'_'+left,'direct',model]['scored']['grounded_correct'])-int(lookup[s,loss+'_'+right,'direct',model]['scored']['grounded_correct']) for loss in ('random','selective'))/2 for s in seeds}
            acq[left+'_minus_'+right]=effect(vals,strata)
        per_view={name:{proc:dict(raw=metrics([lookup[s,name,proc,model] for s in seeds]),gated=metrics([lookup[s,name,proc,model] for s in seeds],'gated')) for proc in ('direct','procedure')} for name in view_names}
        model_results[model]=dict(primary_same_packet_procedure_minus_direct=primary,secondary_acquisition_grounded=acq,by_view=per_view,totals=metrics([r for r in main if r['model']==model]))
    coverage={}
    model=c['monitors'][0]
    for left,right in [('metadata','random'),('contract','metadata')]:
        coverage[left+'_minus_'+right]=effect({s:sum(int(len(lookup[s,loss+'_'+left,'direct',model]['compatible_labels'])==1)-int(len(lookup[s,loss+'_'+right,'direct',model]['compatible_labels'])==1) for loss in ('random','selective'))/2 for s in seeds},strata)
    actual=dict(source_groups=len(ts),issue_valid=sum(t['choices']['issue']['valid'] for t in ts),delegate_valid=sum(t['choices']['delegate']['valid'] for t in ts),settle_valid=sum(t['choices']['settle']['valid'] for t in ts),writes=sum(t['world']['outcome']=='write' for t in ts),unauthorized_writes=sum(t['host']['label']!='NONE' for t in ts),reads=sum(t['world']['outcome']=='read' for t in ts),not_called=sum(t['world']['outcome']=='not_called' for t in ts),useful_completion=sum((t['host']['permitted'] and t['world']['outcome']=='write') or (not t['host']['permitted'] and t['world']['outcome']=='read') for t in ts))
    unique={ (r['metadata']['source_seed'],r['metadata']['view']):r for r in main if r['model']==model and r['metadata']['procedure']=='direct'}
    baselines={}
    for name,answer in [('always_abstain',dict(status='ABSTAIN',worker_id=None)),('always_none',dict(status='NONE',worker_id=None))]:
        scored=[score_stateful(dict(status='completed',output_text=json.dumps(answer)),set(r['compatible_labels'])) for r in unique.values()]
        baselines[name]=dict(packets=len(scored),grounded_correct=sum(s['grounded_correct'] for s in scored),supported_definite=sum(s['supported_definite'] for s in scored))
    baselines['exact_packet']=dict(packets=len(unique),grounded_correct=len(unique),supported_definite=sum(len(r['compatible_labels'])==1 for r in unique.values()))
    costs={p:str(sum((Decimal(r['estimated_cost']) for r in actors+cases if r['provider']==p),Decimal(0))) for p in ('adaption','hf')}
    cal={m:{proc:metrics([r for r in calibration if r['model']==m and r['metadata']['procedure']==proc]) for proc in ('direct','procedure')} for m in c['monitors']}
    return dict(sources=len(ts),actor_calls=len(actors),audit_calls=len(cases),main_audit_calls=len(main),calibration_calls=len(calibration),calibration=cal,models=model_results,secondary_oracle_coverage=coverage,actual_behavior=actual,baselines=baselines,costs=costs,primary=dict(model=model,view='sufficient',metric='raw supported definite procedure minus direct',result=model_results[model]['primary_same_packet_procedure_minus_direct']),scope='One new temporal-delegation structure,192 independent source groups; calibration scripted and separate; multiple views/readers not extra n; procedure prompt intervention, not internal cognition')

def export():
    verify();from experiments.factorial_study import smoke_pass
    smoke=smoke_pass();actors=[];audits=[];hashes={};phases={}
    for stage in ('smoke',)+STAGES:
        d=folder(stage);summary=read(d/'summary.json');expect(summary['complete'] and not summary['halted'],'Partial/fatal phase cannot be released complete');phases[stage]=summary
        rs=rows(d/'responses.jsonl');attempts=rows(d/'attempts.jsonl');plan=read(d/'plan.json')
        jobs=smoke_jobs() if stage=='smoke' else audit_jobs() if stage=='audits' else actor_jobs(stage)
        random.Random(config()['order_seed']).shuffle(jobs)
        expect(plan['freeze_sha256']==sha(FREEZE) and plan['jobs_sha256']==digest(jobs) and plan['ids']==[j['id'] for j in jobs],'Frozen plan replay')
        expect(len(rs)==len({r['id'] for r in rs})==len(attempts)==len({r['id'] for r in attempts})==len(jobs),'Terminal grid size')
        jobs={j['id']:j for j in jobs};starts={x['id']:x for x in attempts};expect(set(jobs)==set(starts)=={r['id'] for r in rs},'Started terminal identities')
        for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json'):hashes[stage+'/'+name]=hashlib.sha256((d/name).read_bytes()).hexdigest()
        for r in rs:
            j=jobs[r['id']];provider,body=body_for(j);n,known=safe_response(r['native_response'],j['model'])
            expect(r['model']==j['model'] and r['metadata']==j['metadata'] and provider==r['provider'] and digest(body)==starts[r['id']]['request_sha256'] and n==r['response'] and known==r['known_usage'],'Native normalization/body binding')
            if stage=='smoke':continue
            clean={k:r[k] for k in ALLOWED}
            if stage=='audits':audits.append(clean)
            else:actors.append(clean|dict(job=j))
    design=contexts();ts,cases=build_cases(actors,audits,design);actors=sorted(actors,key=lambda r:r['id'])
    for name,value in zip(FILES,(dict(main=design),actors,ts,cases)):
        text=''.join(canonical(r)+'\n' for r in value) if name.endswith('.jsonl') else json.dumps(value,indent=2,ensure_ascii=False)+'\n'
        (ROOT/name).write_text(text,encoding='utf-8',newline='\n')
    report=dict(status='complete',study_id=config()['study_id'],config=config(),freeze_sha256=sha(FREEZE),artifacts={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES},raw_file_sha256=hashes,phases=phases,smoke=smoke,analysis=analyze(actors,ts,cases),billing='Token-rate estimates/reserved gateway unknowns, not reconciled invoices',training_runs=0)
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return verify_public()

def verify_public():
    verify();r=read(REPORT);expect(r['status']=='complete' and r['config']==config() and r['freeze_sha256']==sha(FREEZE),'Report registration')
    expect(set(r['artifacts'])==set(FILES) and r['training_runs']==0 and all(s['complete'] and not s['halted'] for s in r['phases'].values()),'Release phase/artifact contract')
    for n,h in r['artifacts'].items():expect(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,'Public artifact hash')
    design=read(ROOT/FILES[0])['main'];expect(design==contexts(),'Committed context plan')
    actors=rows(ROOT/FILES[1]);cases=rows(ROOT/FILES[3]);ts,rebuilt=build_cases(actors,cases,design)
    expect(ts==read(ROOT/FILES[2]) and cases==rebuilt,'Public action/evidence/scoring reconstruction')
    for row in actors+cases:
        extra={'job'} if 'job' in row else {'packet','compatible_labels','added_ids','restored_bytes','scored','gated'}
        expect(set(row)==set(ALLOWED)|extra and set(row['response'])=={'status','output_text','usage','returned_model'} and set(row['transport'])<={'http_status','latency_seconds','error'},'Public field allowlist')
        provider='hf' if row['model']==config()['hf_model'] else 'adaption';expect(row['provider']==provider and type(row['known_usage']) is bool,'Provider/usage type')
        ri,ro=rates(row['model']);u=row['response']['usage'];cost=(u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if row['known_usage'] else (config()['input_byte_cap']*ri+config()['max_output_tokens']*ro)/1000000
        expect(Decimal(row['estimated_cost'])==cost,'Cost arithmetic')
    expect(r['analysis']==analyze(actors,ts,cases),'Source-level aggregate/bootstrap replay')
    return dict(valid=True,actor_calls=len(actors),audit_calls=len(cases),sources=len(ts))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('export','verify'));a=p.parse_args();print(json.dumps(export() if a.command=='export' else verify_public(),indent=2))
