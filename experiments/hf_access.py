"""Read HF routing/prices and make one explicitly selected bounded smoke call."""
import json
from decimal import Decimal
from experiments.access import ROOT,credentials,request_json
from experiments.pilot import prepare,GRAMMAR,classify,scrub

def catalog():
    key=credentials().get('HF_TOKEN')
    if not key:raise ValueError('HF token unavailable')
    status,data=request_json('https://router.huggingface.co/v1/models',key)
    out=ROOT/'runs/access-check';out.mkdir(parents=True,exist_ok=True)
    selected=[]
    for row in (data or {}).get('data',[]):
        if row.get('id')=='Qwen/Qwen3.8-27B':selected.append(row)
    result=dict(transport=status,selected=selected)
    (out/'hf-router-catalog.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

def smoke():
    key=credentials().get('HF_TOKEN')
    if not key:raise ValueError('HF token unavailable')
    out=ROOT/'runs/hf-smoke-v1'
    out.mkdir(exist_ok=False)
    _,tasks=prepare(2)
    tasks=[t for t in tasks if t['mechanism'] in ('full','targeted')]
    model='Qwen/Qwen3.8-27B:cerebras'
    # Exact provider/rates checked from /v1/models before this smoke test.
    r_in=Decimal('0.99');r_out=Decimal('1.49');spent=Decimal(0)
    rows=[]
    manifest=dict(status='access/serving smoke test only',provider='cerebras',model=model,
        planned_calls=len(tasks),max_output_tokens=4096,usd_ceiling='0.10',input_usd_per_million=str(r_in),
        output_usd_per_million=str(r_out),packets=[t['packet_sha256'] for t in tasks])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    with (out/'attempts.jsonl').open('x',encoding='utf-8') as attempts,(out/'responses.jsonl').open('x',encoding='utf-8') as responses:
        for t in tasks:
            reserve=(6000*r_in+4096*r_out)/1_000_000
            if spent+reserve>Decimal('0.10'):break
            attempts.write(json.dumps(dict(episode_id=t['episode_id'],mechanism=t['mechanism'],reserved_usd=str(reserve)))+'\n');attempts.flush()
            body=dict(model=model,messages=[{'role':'system','content':GRAMMAR},{'role':'user','content':json.dumps(t['packet'],sort_keys=True,separators=(',',':'))}],temperature=0,max_tokens=4096,stream=False)
            transport,data=request_json('https://router.huggingface.co/v1/chat/completions',key,body,timeout=60)
            u=(data or {}).get('usage') or {}
            known=all(type(u.get(k)) is int and u[k]>=0 for k in ('prompt_tokens','completion_tokens'))
            cost=(u['prompt_tokens']*r_in+u['completion_tokens']*r_out)/1_000_000 if known else reserve
            spent+=cost
            choice=((data or {}).get('choices') or [{}])[0]
            normalized=dict(status='completed' if choice.get('finish_reason')=='stop' else 'incomplete',output_text=(choice.get('message') or {}).get('content') or '')
            row=scrub(dict(episode_id=t['episode_id'],mechanism=t['mechanism'],packet_sha256=t['packet_sha256'],
                transport=transport,response=data,estimated_usd=str(cost),scored=classify(normalized,t['compatible_labels'])),[key])
            rows.append(row);responses.write(json.dumps(row)+'\n');responses.flush()
            if not known or u['prompt_tokens']>6000 or u['completion_tokens']>4096:break
    summary=dict(calls=len(rows),http_200=sum(r['transport']['http_status']==200 for r in rows),estimated_usd=str(spent),
        grounded_correct=sum(r['scored']['grounded_correct'] for r in rows),invalid=sum(r['scored']['status']=='INVALID' for r in rows),
        caveat='Four smoke calls are not a replication or evidence of checkpoint equivalence; HF billing may post later.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');args=p.parse_args()
    smoke() if args.smoke else catalog()
