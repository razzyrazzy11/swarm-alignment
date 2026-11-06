"""Verify public development data and reported counts without keys or network."""
import hashlib
import json
from pathlib import Path
from experiments.oracle import Scenario,World,execute,compatible_labels,packet
from experiments.pilot import classify,digest

ROOT=Path(__file__).resolve().parents[1]

def verify_release():
    report=json.loads((ROOT/'research/pilot-results.json').read_text())
    casefile=ROOT/'data/development_reader_cases.jsonl';episodefile=ROOT/'data/development_episodes.json'
    for path,field in ((casefile,'cases_sha256'),(episodefile,'episodes_sha256')):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=report['released_development_data'][field]:raise ValueError('Release hash mismatch')
    episodes=json.loads(episodefile.read_text())
    byid={e['episode_id']:e for e in episodes}
    if len(byid)!=20 or len(episodes)!=20:raise ValueError('Source episode count mismatch')
    for e in episodes:
        s=Scenario(**e['scenario']);wd=e['world'];w=World(wd['actor'],wd['outcome'],tuple(wd['aliases']),wd['churn'])
        if execute(s,w)!=e['host_state']:raise ValueError('Fake-state replay mismatch')
    rows=[json.loads(s) for s in casefile.read_text().splitlines()]
    ids={(r['episode_id'],r['mechanism'],r['model']) for r in rows}
    if len(rows)!=120 or len(ids)!=120:raise ValueError('Reader count/uniqueness mismatch')
    for r in rows:
        e=byid[r['episode_id']];wd=e['world']
        s=Scenario(**e['scenario']);w=World(wd['actor'],wd['outcome'],tuple(wd['aliases']),wd['churn'])
        visible={v['id'] for v in r['packet']['records']}
        deleted=[f'e{i}' for i in range(8) if f'e{i}' not in visible]
        reconstructed=packet(s,w,deleted,**r['packet']['instrumentation'],allowed_counts=tuple(r['packet']['public']['allowed_deleted_counts']))
        if reconstructed!=r['packet']:raise ValueError('Visible packet does not match source episode')
        labels=compatible_labels(r['packet'])
        if labels!=set(r['compatible_labels']) or digest(r['packet'])!=r['packet_sha256']:raise ValueError('Packet/reference mismatch')
        if r['complete_history_label']!=byid[r['episode_id']]['host_state']['true_label']:raise ValueError('Hidden-state label mismatch')
        score=classify(dict(status=r['response_status'],output_text=r['actual_output']),labels)
        if score!=r['scored']:raise ValueError('Score mismatch')
    for model,counts in report['batches']['pilot-development-v4']['models'].items():
        rs=[r for r in rows if r['model']==model]
        for metric in ('grounded_correct','supported_definite','unsupported_executor','unsupported_none'):
            if sum(r['scored'][metric] for r in rs)!=counts[metric]:raise ValueError('Aggregate mismatch: '+metric)
        if len(rs)!=counts['calls'] or sum(r['scored']['status']=='INVALID' for r in rs)!=counts['invalid']:raise ValueError('Call/invalid count mismatch')
    return dict(source_episodes=len(episodes),reader_calls=len(rows),result='PASS')

if __name__=='__main__':print(json.dumps(verify_release()))
