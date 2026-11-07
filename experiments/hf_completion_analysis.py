"""New complete-original release; immutable old report and unchanged analysis."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess

from experiments import factorial_analysis as f
from experiments import factorial_reporting as r
from experiments import factorial_study as s
from experiments import hf_completion as h

ROOT=s.ROOT
TAG='hf-completed-original-analysis-v2'
FREEZE=ROOT/'research/hf-completed-original-analysis-freeze.json'
REPORT=ROOT/'research/hf-completed-original-results.json'
SUPPLEMENT='data/hf_completed_original_supplement.jsonl'
SOURCES=('experiments/hf_completion_analysis.py','experiments/tests/test_hf_completion_analysis.py',
         'research/HF_COMPLETION_ANALYSIS.md',
         'research/HF_COMPLETION_ANALYSIS_REGISTRATION_CORRECTION.md',
         'research/hf-completed-original-analysis-v1-incomplete-freeze.json',
         'experiments/hf_completion_v2.py','experiments/tests/test_hf_completion_v2.py',
         'research/HF_COMPLETION_V2_PROTOCOL.md')
ANCHORS=('research/factorial-report.json',)+r.FILES
DRIVER='runs/hf-completion-driver-v1/state.json'
SUMMARY_KEYS={'planned','returned','unstarted','complete','halted','stop_reason',
              'new_transient_errors','historical_429_preserved','new_estimated_cost',
              'historical_hf_cost','freeze_sha256','cost_basis',
              'original_audit_returned','original_hf_returned'}


def expect(ok,message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(v) for v in Path(path).read_text(encoding='utf-8').splitlines()]
def blob(path,tag=h.SNAPSHOT): return subprocess.check_output(['git','show',tag+':'+path],cwd=ROOT)


def build_completed(actors,old_original_cases,supplement_public,design):
    """Pure reconstruction: complete original grid, never an extension or imputation.

    Supplement rows have exactly the original public terminal fields plus the
    reconstructed request_sha256. Old rows retain the historical report schema.
    Production counts are checked by the release wrapper, allowing tiny tests.
    """
    ts,packets,jobs,_,registry=r.build_plan(actors,design)
    expected={j['id']:j for j in jobs}
    old=list(old_original_cases); fresh=list(supplement_public)
    expect(len(old)==len({x['id'] for x in old}),'Duplicate historical terminal')
    expect(len(fresh)==len({x['id'] for x in fresh}),'Duplicate supplement terminal')
    expect(not ({x['id'] for x in old}&{x['id'] for x in fresh}),'Historical terminal repeated')
    expect({x['id'] for x in old+fresh}==set(expected),'Incomplete/unplanned original terminal grid')
    actor_descriptor=registry['original_g26']
    for row in actors: r.validate_row(row,actor_descriptor,actor=True)
    audits=[]
    for row in old:
        expect(row['id'] in expected,'Historical identity outside original plan')
        j=expected[row['id']];ident=r._condition(j,registry)
        expect(row.get('condition_id')==ident,'Historical condition identity')
        r.validate_row(row,registry[ident],decorated=True)
        audits.append({k:row[k] for k in f.ALLOWED})
    for row in fresh:
        expect(set(row)==set(f.ALLOWED)|{'request_sha256'},'Supplement public allowlist')
        expect(row['id'] in expected,'Supplement identity outside original plan')
        j=expected[row['id']];ident=r._condition(j,registry)
        expect(ident=='original_hf','Only original unstarted HF may be supplemented')
        provider,body=s.body_for(j)
        expect(row['request_sha256']==s.digest(body) and provider=='hf','Supplement request body differs')
        clean={k:row[k] for k in f.ALLOWED};r.validate_row(clean,registry[ident])
        audits.append(clean)
    trajectories,cases=f.build_cases(actors,audits,design)
    rebuilt={x['id']:x for x in cases}
    for row in old:
        new=rebuilt[row['id']]
        expect(all(row[k]==new[k] for k in ('compatible_labels','restored_bytes','scored','gated')),
               'Historical support/scoring changed')
    return dict(trajectories=trajectories,cases=cases,analysis=f.analyze(actors,trajectories,cases))


def freeze():
    """Root invokes only after committing sources; does not inspect supplement."""
    expect(not FREEZE.exists(),'Analysis registration already exists')
    h.verify()
    expect(blob('experiments/factorial_analysis.py').replace(b'\r\n',b'\n')==(ROOT/'experiments/factorial_analysis.py').read_bytes().replace(b'\r\n',b'\n'),'Original analysis source changed since V3')
    for name in SOURCES:
        expect(blob(name,'HEAD').replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),
               'Commit analysis sources before registration')
    anchors={name:hashlib.sha256(blob(name)).hexdigest() for name in ANCHORS}
    expect(all(sha(ROOT/name)==value for name,value in anchors.items()),'Historical V3 anchor changed')
    record=dict(schema_version=1,tag=TAG,created=datetime.now(timezone.utc).isoformat(),
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256={name:s.sha(ROOT/name) for name in SOURCES},snapshot_tag=h.SNAPSHOT,
                anchors=anchors,completion_freeze_sha256=s.sha(h.FREEZE),
                analysis_sha256=s.sha(ROOT/'experiments/factorial_analysis.py'),
                timing='Original outcomes known; completion collection already ongoing; wrapper frozen before supplement unblinding')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,tag=TAG,scope='source registration only; no supplement answers read')


def verify_registration():
    h.verify();value=read(FREEZE)
    expect(set(value)=={'schema_version','tag','created','base_commit','source_sha256','snapshot_tag','anchors',
                       'completion_freeze_sha256','analysis_sha256','timing'},'Analysis registration schema')
    expect(value['schema_version']==1 and type(value['schema_version']) is int and value['tag']==TAG and value['snapshot_tag']==h.SNAPSHOT,'Analysis registration identity')
    expect(value['source_sha256']=={name:s.sha(ROOT/name) for name in SOURCES},'Analysis sources changed')
    expect(value['completion_freeze_sha256']==s.sha(h.FREEZE) and value['analysis_sha256']==s.sha(ROOT/'experiments/factorial_analysis.py'),'Frozen methods changed')
    expect(blob('experiments/factorial_analysis.py').replace(b'\r\n',b'\n')==(ROOT/'experiments/factorial_analysis.py').read_bytes().replace(b'\r\n',b'\n'),'Original analysis source differs from V3')
    expect(set(value['anchors'])==set(ANCHORS),'V3 anchor set changed')
    for name,expected in value['anchors'].items():
        expect(sha(ROOT/name)==expected==hashlib.sha256(blob(name)).hexdigest(),'Historical V3 anchor changed: '+name)
    for name in (*SOURCES,'research/'+FREEZE.name):
        expect(blob(name,TAG).replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Analysis tag differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Analysis registration ancestry')
    return value


def _process_absent(pid):
    expect(type(pid) is int and pid>0,'Driver process identity required')
    if os.name=='nt':
        command=(f'try {{ Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 }} '
                 'catch { if ($_.CategoryInfo.Category -eq "ObjectNotFound") { exit 3 }; exit 4 }')
        expect(subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True).returncode==3,
               'Driver/child active or process lookup failed')
    else:
        try: os.kill(pid,0)
        except ProcessLookupError: return
        except OSError: raise ValueError('Driver process termination cannot be verified') from None
        raise ValueError('Driver/child still active')


def driver_stopped():
    state=read(ROOT/DRIVER)
    expect(state.get('status') in ('stopped','complete'),'Completion driver still active')
    _process_absent(state.get('pid'))
    _process_absent(state.get('child_pid'))
    if state.get('collector_pid') is not None: _process_absent(state['collector_pid'])
    expect(not (h.folder()/'collector.lock').exists(),'Completion lock active/stale; do not remove it')


def recovery_stopped():
    from experiments import hf_completion_v2 as recovery
    state=read(ROOT/'runs/hf-completion-v2-driver/state.json')
    expect(state.get('status') in ('stopped','complete'),'Recovery driver still active')
    _process_absent(state.get('pid'));_process_absent(state.get('child_pid'))
    expect(not (recovery.folder()/'collector.lock').exists(),'Recovery collector lock active/stale')


def _old_inputs():
    actors=rows(ROOT/r.FILES[1]);design=read(ROOT/r.FILES[0])['main']
    original=[x for x in rows(ROOT/r.FILES[3]) if x['condition_id'].startswith('original_')]
    expect(len(actors)==576 and len(design)==192 and len(original)==9742,'Historical source counts changed')
    return actors,original,design


def _availability(cases):
    result={}
    for model in s.config()['monitors']:
        selected=[x for x in cases if x['model']==model]
        statuses=Counter(x['scored']['status'] for x in selected)
        result[model]=dict(planned=3880,terminal=len(selected),terminal_complete=len(selected)==3880,
            successful_serving=sum(x['transport'].get('http_status')==200 and x['response']['status']=='completed' for x in selected),
            strict_schema_valid=sum(x['scored']['strict_schema_valid'] for x in selected),
            invalid=statuses['INVALID'],http_429=sum(x['transport'].get('http_status')==429 for x in selected))
    return result


def _check_completion_counts(fresh,registration):
    expected={x['id']:x for x in registration['pending']}
    expect(len(fresh)==1898 and len({x['id'] for x in fresh})==1898 and {x['id'] for x in fresh}==set(expected),'All1898 original unstarted identities must be terminal')
    for row in fresh:
        d=expected[row['id']]
        expect(all(row[k]==d[k] for k in ('model','provider','metadata','request_sha256')),'Registered supplement descriptor differs')


def _summary_check(summary,fresh):
    expect(set(summary)==SUMMARY_KEYS,'Supplement summary public allowlist')
    expect(summary['complete'] is True and summary['planned']==1898 and summary['returned']==1898 and summary['unstarted']==0,'Operational terminal accounting differs')
    expect(summary['freeze_sha256']==s.sha(h.FREEZE) and summary['historical_429_preserved']==5 and summary['original_audit_returned']==11640 and summary['original_hf_returned']==3880,'Operational plan accounting differs')
    expect(type(summary['new_transient_errors']) is int and 0<=summary['new_transient_errors']<=h.FIXED['new_transient_allowance'],'Operational transient count invalid')
    expect(Decimal(summary['new_estimated_cost'])==sum((Decimal(x['estimated_cost']) for x in fresh),Decimal(0)),'Supplement summary cost differs from terminal costs')


def export(publish_after_collection=False):
    expect(publish_after_collection,'Explicit publication flag required')
    registration=verify_registration();completion=h.verify();driver_stopped();recovery_stopped()
    from experiments import hf_completion_v2 as recovery
    recovery.verify()
    with h.exclusive(recovery.folder()):
        private,body_by,summary,raw=recovery.private_completed(owned_lock=True)
        expect(len(private)==1898,'Incomplete supplement cannot be published COMPLETE')
        fresh=[{k:x[k] for k in f.ALLOWED}|dict(request_sha256=body_by[x['id']]) for x in private]
        _check_completion_counts(fresh,completion)
        _summary_check(summary,fresh)
        actors,old,design=_old_inputs();result=build_completed(actors,old,fresh,design)
        expect(len(result['cases'])==11640,'Original terminal grid size')
        original_primary=read(ROOT/'research/factorial-report.json')['analysis']['primary']['result']
        expect(result['analysis']['primary']['result']==original_primary,'Original primary estimate/interval changed')
        text=''.join(s.canonical(x)+'\n' for x in sorted(fresh,key=lambda x:x['id']))
        expect(not REPORT.exists() and not (ROOT/SUPPLEMENT).exists(),'New release exists; do not overwrite')
        (ROOT/SUPPLEMENT).write_text(text,encoding='utf-8',newline='\n')
        report=dict(schema_version=1,status='complete',study_id=s.config()['study_id'],analysis_tag=TAG,
            analysis_freeze_sha256=s.sha(FREEZE),completion_freeze_sha256=s.sha(h.FREEZE),
            recovery_freeze_sha256=s.sha(recovery.FREEZE),
            source_artifacts=registration['anchors'],supplement_artifacts={SUPPLEMENT:sha(ROOT/SUPPLEMENT)},
            raw_supplement_sha256=raw,analysis=result['analysis'],availability=_availability(result['cases']),
            historical_hf_429_preserved=len(completion['historical_429_ids']),supplement_terminals=len(fresh),
            operational_summary=summary,training_runs=0,
            billing='Original token-rate estimates or unknown reservations, not reconciled invoices',
            provenance_limit='Public reconstruction checks sanitized records and commitments; native normalization requires private journals')
        REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    return verify_public()


def verify_public():
    registration=verify_registration();completion=h.verify();report=read(REPORT)
    from experiments import hf_completion_v2 as recovery
    recovery.verify()
    expect(set(report)=={'schema_version','status','study_id','analysis_tag','analysis_freeze_sha256',
        'completion_freeze_sha256','recovery_freeze_sha256','source_artifacts','supplement_artifacts','raw_supplement_sha256',
        'analysis','availability','historical_hf_429_preserved','supplement_terminals','operational_summary',
        'training_runs','billing','provenance_limit'},'Completed report public allowlist')
    expect(report['schema_version']==1 and report['status']=='complete' and report['study_id']==s.config()['study_id'] and report['analysis_tag']==TAG,'Completed report identity')
    expect(report['analysis_freeze_sha256']==s.sha(FREEZE) and report['completion_freeze_sha256']==s.sha(h.FREEZE),'Report registration changed')
    expect(report['recovery_freeze_sha256']==s.sha(recovery.FREEZE),'Recovery registration changed')
    expect(report['source_artifacts']==registration['anchors'] and report['supplement_artifacts']=={SUPPLEMENT:sha(ROOT/SUPPLEMENT)},'Public input commitments changed')
    fresh=rows(ROOT/SUPPLEMENT);_check_completion_counts(fresh,completion)
    actors,old,design=_old_inputs();result=build_completed(actors,old,fresh,design)
    expect(report['analysis']==result['analysis'] and report['availability']==_availability(result['cases']),'Original point estimate/bootstrap reconstruction differs')
    expect(report['analysis']['primary']['result']==read(ROOT/'research/factorial-report.json')['analysis']['primary']['result'],'Original primary changed')
    expect(report['historical_hf_429_preserved']==5 and report['supplement_terminals']==1898 and report['training_runs']==0,'Completion denominators changed')
    summary=report['operational_summary']
    _summary_check(summary,fresh)
    commitments=report['raw_supplement_sha256']
    expect(set(commitments)=={'hf-completion-v1','hf-completion-v2'},'Two-journal provenance required')
    for hashes in commitments.values():
        expect(set(hashes)=={'plan.json','attempts.jsonl','responses.jsonl','summary.json'} and all(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v) for v in hashes.values()),'Private provenance commitment schema')
    expect(commitments['hf-completion-v1']==read(recovery.FREEZE)['prior_raw_sha256'],'Immutable first nine provenance changed')
    return dict(valid=True,original_terminals=len(result['cases']),supplement_terminals=len(fresh),sources=len(design),private_runs_required=False,inference_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('freeze','verify-registration','export','verify'))
    parser.add_argument('--publish-after-collection',action='store_true');args=parser.parse_args()
    command={'freeze':freeze,'verify-registration':verify_registration,'export':lambda:export(args.publish_after_collection),'verify':verify_public}[args.command]
    print(json.dumps(command(),indent=2))
