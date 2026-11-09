"""Prospective PID-safe release of the unchanged original HF completion analysis.

Import/freeze/verify do not read supplement answers or contact providers.
Only explicit export after completed collection admits private journal contents.
"""
import argparse
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

from experiments import hf_completion as h
from experiments import hf_completion_v2 as recovery
from experiments import hf_completion_analysis as a
from experiments import factorial_continue as c
from experiments import factorial_study as s
from experiments import factorial_analysis as f
from experiments.swarm_ledger_dispatch_v2 import process_dead

ROOT=s.ROOT
TAG='hf-completion-release-v1'
FREEZE=ROOT/'research/hf-completion-release-v1-freeze.json'
COMPANION=ROOT/'research/hf-completed-original-release-proof.json'
SOURCES=('experiments/hf_completion_release.py','experiments/tests/test_hf_completion_release.py',
         'research/HF_COMPLETION_RELEASE_PROTOCOL.md','experiments/swarm_ledger_dispatch_v2.py')
DRIVERS=('runs/factorial-driver-v1/state.json',a.DRIVER,'runs/hf-completion-v2-driver/state.json')
expect=a.expect


def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parent_anchors():
    a.verify_registration();h.verify();recovery.verify()
    return {str(p.relative_to(ROOT)).replace('\\','/'):s.sha(p) for p in (a.FREEZE,h.FREEZE,recovery.FREEZE)}


def freeze():
    expect(not FREEZE.exists(),'Release registration already exists')
    anchors=parent_anchors()
    for name in SOURCES:
        expect(h.blob(name,'HEAD').replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),
               'Commit release sources before registration')
    value=dict(schema_version=1,tag=TAG,created=datetime.now(timezone.utc).isoformat(),
               base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               source_sha256={name:s.sha(ROOT/name) for name in SOURCES},parent_registration_sha256=anchors,
               timing='Operational release guard registered during collection, before supplement answer unblinding; all scientific methods unchanged')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(value,indent=2)+'\n')
    return dict(created=True,tag=TAG,inference_calls=0,supplement_answers_read=False)


def verify():
    value=s.read(FREEZE)
    expect(set(value)=={'schema_version','tag','created','base_commit','source_sha256','parent_registration_sha256','timing'},'Release registration schema')
    expect(type(value['schema_version']) is int and value['schema_version']==1 and value['tag']==TAG,'Release registration identity')
    expect(value['source_sha256']=={name:s.sha(ROOT/name) for name in SOURCES},'Release source changed')
    expect(value['parent_registration_sha256']==parent_anchors(),'Frozen scientific registrations changed')
    for name in (*SOURCES,str(FREEZE.relative_to(ROOT)).replace('\\','/')):
        expect(h.blob(name,TAG).replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Release tag differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Release registration ancestry')
    return value


def driver_proof(owned_lock=False):
    """Do not confuse a later process reusing a terminated driver's PID with it."""
    hashes={}
    for ordinal,name in enumerate(DRIVERS):
        path=ROOT/name
        expect(path.is_file() and not path.is_symlink(),'Actual driver termination metadata required')
        raw=path.read_bytes();state=json.loads(raw)
        expected_status=('stopped','complete') if ordinal<2 else ('complete',)
        expect(state.get('status') in expected_status,'Actual HF driver collection is not terminal-complete')
        try:ended=datetime.fromisoformat(state['updated'].replace('Z','+00:00'))
        except (ValueError,KeyError,AttributeError):raise ValueError('Final driver UTC timestamp required') from None
        expect(ended.tzinfo is not None and ended.utcoffset()==timedelta(0) and ended<=datetime.now(timezone.utc),'Final driver timestamp invalid')
        pid=state.get('pid');expect(type(pid) is int and pid>0,'Actual driver PID required')
        process_dead(pid,state['updated'])
        if ordinal>0:
            child=state.get('child_pid');expect(type(child) is int and child>0 and child!=pid,'Actual driver child identity required')
            process_dead(child,state['updated'])
        if state.get('collector_pid') is not None:process_dead(state['collector_pid'],state['updated'])
        expect(path.read_bytes()==raw,'Driver state changed during termination checks')
        hashes[name]=hashlib.sha256(raw).hexdigest()
    locks=[s.folder('audits')/name for name in ('collector.lock','continuation-pacing.lock','continuation.lock')]
    locks.extend((h.folder()/'collector.lock',recovery.folder()/'collector.lock'))
    owned={s.folder('audits')/'continuation.lock',recovery.folder()/'collector.lock'} if owned_lock else set()
    expect(not [p for p in locks if p not in owned and p.exists()],'Relevant HF collector active or stale lock; never remove it')
    return hashes


def private_snapshot():
    """Only metadata commitments escape: native/error contents remain private."""
    paths=[]
    for folder in (h.folder(),recovery.folder()):
        paths.extend(folder/name for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json'))
        paths.extend(sorted((folder/'private-errors').glob('*.json')))
    expect(all(p.is_file() and not p.is_symlink() for p in paths),'Private commitment requires regular files')
    return {str(p.relative_to(ROOT)).replace('\\','/'):raw_sha(p) for p in paths}


def guard(owned_lock=False):
    verify();return driver_proof(owned_lock)


def original_prefix(owned_lock=False):
    """Read-only replay of source/body/cost commitments, without printing answers."""
    c.verify_original_sources();s.verify();guard(owned_lock);cfg=h.config();checkpoint=s.read(ROOT/h.CHECKPOINT)
    for relative,value in checkpoint['raw_prefixes'].items():
        stage,name=relative.split('/',1);path=s.folder(stage)/name
        expect(path.stat().st_size==value['bytes'] and h.raw_sha(path)==value['sha256'],
               'Original raw checkpoint changed: '+relative)
    jobs,plan=c.shuffled_plan(s.audit_jobs());out=s.folder('audits')
    expect(s.read(out/'plan.json')==plan,'Original plan changed')
    starts,rows,started=c.ledger(out,jobs,plan)
    expect(len(starts)==len(rows)==cfg['historical_audit_terminals'],'Original checkpoint count changed')
    expect(sum(r['provider']=='hf' for r in rows)==cfg['historical_hf_terminals'],'Historical HF count changed')
    rate_ids=[r['id'] for r in rows if r['transport'].get('http_status')==429]
    expect(len(rate_ids)==cfg['historical_429_count'],'Historical error count changed')
    pending=[j for j in jobs if j['id'] not in started]
    expect(len(pending)==cfg['original_unstarted'],'Original unstarted complement changed')
    _,published,_=h.snapshot()
    for j in pending:
        d=h.descriptor(j);p=published[j['id']]
        expect(all(d[k]==p[k] for k in d),'Original request differs from published commitment')
    return pending,rate_ids

def prior_prefix(owned_lock=False):
    """Private call; requires analysis source registration before any answer read."""
    from experiments import hf_completion_analysis as a
    a.verify_registration();guard(owned_lock)
    jobs,historical=original_prefix(owned_lock)
    registration=h.verify()
    plan=dict(freeze_sha256=s.sha(h.FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),
              pending_sha256=s.digest(registration['pending']))
    starts,rows,started=h.supplement_ledger(h.folder(),jobs,plan)
    expect(len(starts)==len(rows)==9,'Prior completion prefix must remain exactly nine terminals')
    hashes={name:h.raw_sha(h.folder()/name) for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}
    remaining=[j for j in jobs if j['id'] not in started]
    expect(len(remaining)==1889,'Remaining original complement differs')
    # Count the newly diagnosed prior overload, without changing its old flag.
    prior_transients=0
    for row in rows:
        receipt=row.get('error_receipt')
        if receipt is not None:
            error=s.read(h.folder()/receipt['file'])
            prior_transients+=int(recovery.explicit_overload(error['http_status'],error['error_body']))
    expect(prior_transients==1,'Diagnosed prior overload count differs')
    return remaining,rows,hashes,prior_transients

def private_completed(owned_lock=False):
    """Validated two-journal union, for explicit completed-analysis export only."""
    registration=recovery.verify();jobs,prior,hashes,transients=prior_prefix(owned_lock)
    expect(hashes==registration['prior_raw_sha256'] and [x['id'] for x in prior]==registration['prior_ids'],'Prior nine journal bytes changed')
    expect([h.descriptor(j) for j in jobs]==registration['pending'],'Recovery remaining plan changed')
    plan=dict(freeze_sha256=s.sha(recovery.FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),pending_sha256=s.digest(registration['pending']))
    starts,new,started=recovery.supplement_ledger(recovery.folder(),jobs,plan)
    expect(len(starts)==len(new)==1889,'Recovery is not terminal-complete')
    summary=s.read(recovery.folder()/'summary.json')
    expect(set(summary)=={'planned','returned','unstarted','complete','halted','stop_reason','new_transient_errors',
        'prior_terminals','prior_estimated_cost','new_estimated_cost','combined_estimated_cost','freeze_sha256'},'Recovery summary schema')
    expect(summary['complete'] is True and summary['planned']==1889 and summary['returned']==1889 and summary['unstarted']==0 and summary['freeze_sha256']==s.sha(recovery.FREEZE),'Recovery summary incomplete')
    new_cost=sum((Decimal(x['estimated_cost']) for x in new),Decimal(0))
    prior_cost=sum((Decimal(x['estimated_cost']) for x in prior),Decimal(0))
    expect(Decimal(summary['new_estimated_cost'])==new_cost and Decimal(summary['prior_estimated_cost'])==prior_cost==Decimal(registration['prior_estimated_cost']) and Decimal(summary['combined_estimated_cost'])==new_cost+prior_cost,'Recovery summary cost differs')
    expect(summary['prior_terminals']==9 and type(summary['new_transient_errors']) is int and summary['new_transient_errors']==transients+sum(h.transient(x) for x in new),'Recovery summary transient accounting differs')
    combined=prior+new
    combined_summary=dict(planned=1898,returned=1898,unstarted=0,complete=True,halted=summary['halted'],
        stop_reason=summary['stop_reason'],new_transient_errors=transients+sum(h.transient(x) for x in new),
        historical_429_preserved=5,new_estimated_cost=str(sum((Decimal(x['estimated_cost']) for x in combined),Decimal(0))),
        historical_hf_cost='0.880229785',freeze_sha256=s.sha(h.FREEZE),cost_basis='token-rate estimate or full unknown reservation, not reconciled invoice',
        original_audit_returned=11640,original_hf_returned=3880)
    commitments={'hf-completion-v1':hashes,'hf-completion-v2':{name:h.raw_sha(recovery.folder()/name) for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}}
    body_by={d['id']:d['request_sha256'] for d in h.verify()['pending']}
    return combined,body_by,combined_summary,commitments

def export(publish_after_collection=False):
    expect(publish_after_collection,'Explicit publication flag required')
    verify();registration=a.verify_registration();completion=h.verify();initial_states=driver_proof();initial_private=private_snapshot()
    from experiments import hf_completion_v2 as recovery
    recovery.verify()
    with h.exclusive(recovery.folder()):
        private,body_by,summary,raw=private_completed(owned_lock=True)
        expect(len(private)==1898,'Incomplete supplement cannot be published COMPLETE')
        fresh=[{k:x[k] for k in f.ALLOWED}|dict(request_sha256=body_by[x['id']]) for x in private]
        a._check_completion_counts(fresh,completion)
        a._summary_check(summary,fresh)
        actors,old,design=a._old_inputs();result=a.build_completed(actors,old,fresh,design)
        expect(len(result['cases'])==11640,'Original terminal grid size')
        original_primary=a.read(ROOT/'research/factorial-report.json')['analysis']['primary']['result']
        expect(result['analysis']['primary']['result']==original_primary,'Original primary estimate/interval changed')
        text=''.join(s.canonical(x)+'\n' for x in sorted(fresh,key=lambda x:x['id']))
        expect(not a.REPORT.exists() and not COMPANION.exists() and not (ROOT/a.SUPPLEMENT).exists(),'New release exists; do not overwrite')
        expect(driver_proof(True)==initial_states and private_snapshot()==initial_private,'Driver/private journal changed before publication')
        verify()
        (ROOT/a.SUPPLEMENT).write_text(text,encoding='utf-8',newline='\n')
        report=dict(schema_version=1,status='complete',study_id=s.config()['study_id'],analysis_tag=a.TAG,
            analysis_freeze_sha256=s.sha(a.FREEZE),completion_freeze_sha256=s.sha(h.FREEZE),
            recovery_freeze_sha256=s.sha(recovery.FREEZE),
            source_artifacts=registration['anchors'],supplement_artifacts={a.SUPPLEMENT:a.sha(ROOT/a.SUPPLEMENT)},
            raw_supplement_sha256=raw,analysis=result['analysis'],availability=a._availability(result['cases']),
            historical_hf_429_preserved=len(completion['historical_429_ids']),supplement_terminals=len(fresh),
            operational_summary=summary,training_runs=0,
            billing='Original token-rate estimates or unknown reservations, not reconciled invoices',
            provenance_limit='Public reconstruction checks sanitized records and commitments; native normalization requires private journals')
        a.REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        return finish_release(initial_states,initial_private,owned_lock=True)

def finish_release(states,private,owned_lock=False):
    result=a.verify_public()
    expect(driver_proof(owned_lock)==states and private_snapshot()==private,'Driver/private journal changed during publication')
    verify()
    proof=dict(schema_version=1,release_tag=TAG,release_freeze_sha256=s.sha(FREEZE),
               driver_state_sha256=states,private_archive_sha256=private,
               output_sha256={str(p.relative_to(ROOT)).replace('\\','/'):raw_sha(p) for p in (a.REPORT,ROOT/a.SUPPLEMENT)},
               frozen_verifier=result,scientific_schema_unchanged=True,inference_calls=0)
    with COMPANION.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(proof,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('freeze','verify','export'))
    parser.add_argument('--publish-after-collection',action='store_true');args=parser.parse_args()
    result=freeze() if args.command=='freeze' else verify() if args.command=='verify' else export(args.publish_after_collection)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
