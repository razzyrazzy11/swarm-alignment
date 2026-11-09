"""Prospective admission of efficient scheduling; strict five-batch MAIN union, no inference."""
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib, json, subprocess
from pathlib import Path
from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_complete_analysis as a

ROOT=s.ROOT
TAG='efficient-resume-analysis-v1'
FREEZE=ROOT/'research/efficient-resume-analysis-v1-freeze.json'
SOURCES=('experiments/efficient_resume_analysis.py','experiments/tests/test_efficient_resume_analysis.py',
 'research/EFFICIENT_RESUME_ANALYSIS_PROTOCOL.md','experiments/efficient_resume_supervisor.py',
 'experiments/tests/test_efficient_resume_supervisor.py','research/EFFICIENT_RESUME_OPERATIONS.md')
PARENTS=('research/swarm-ledger-efficient-v1-freeze.json','research/provider-resume-analysis-v1-freeze.json',
 'research/swarm-ledger-resume-v3-freeze.json','research/server-resume-analysis-v1-freeze.json',
 'research/swarm-ledger-resume-v2-freeze.json','research/swarm-ledger-resume-v1-freeze.json',
 'research/router-resume-analysis-v1-freeze.json','research/hf-completion-v3-freeze.json')
HF_REPORT=ROOT/'research/hf-completed-original-results-v3.json'
HF_SUPPLEMENT=ROOT/'data/hf_completed_original_supplement_v3.jsonl'
MAIN_PROOF=ROOT/'research/swarm-ledger-efficient-resume-release-proof.json'
HF_KEYS={'schema_version','status','analysis_tag','analysis_freeze_sha256','supplement_sha256','source_registration_sha256',
    'raw_batches_sha256','supplement_terminals','original_terminals','analysis','availability','operational_summary',
    'driver_state_sha256','training_runs','provenance_limit'}
expect=s.expect

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def parents():return {p:s.sha(ROOT/p) for p in PARENTS}

def freeze():
    expect(not FREEZE.exists(),'Analysis registration already exists')
    for p in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/p).read_bytes().replace(b'\r\n',b'\n'),'Commit analysis sources first')
    # Collection must not start before this admission method is committed.
    terminated('runs/swarm-ledger-resume-v1-driver/state.json',stopped=True)
    terminated('runs/swarm-ledger-resume-v2-driver/state.json',stopped=True)
    terminated('runs/swarm-ledger-resume-v3-driver/state.json',stopped=True)
    for folder in ('runs/swarm-ledger-efficient-v1-main',):
        expect(not any(p.stat().st_size for p in (ROOT/folder).glob('**/attempts.jsonl')),'Continuation already started')
    value=dict(schema_version=1,tag=TAG,created=s.now(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={p:s.sha(ROOT/p) for p in SOURCES},parent_registration_sha256=parents(),
        method='Same frozen scientific functions; original/router-v1/server-v2/provider-v3/efficient-v1 disjoint union; unchanged scientific calculations and retained failures; no inference retry')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
    return dict(created=True,tag=TAG)

def verify():
    from experiments import provider_resume_analysis as prior
    prior.verify()
    v=s.read(FREEZE)
    expect(set(v)=={'schema_version','tag','created','base_commit','source_sha256','parent_registration_sha256','method'},'Analysis registration schema')
    expect(v['schema_version']==1 and v['tag']==TAG,'Analysis registration identity')
    expect(v['source_sha256']=={p:s.sha(ROOT/p) for p in SOURCES} and v['parent_registration_sha256']==parents(),'Analysis source/parent drift')
    for p in (*SOURCES,str(FREEZE.relative_to(ROOT)).replace('\\','/')):
        blob=subprocess.check_output(['git','show',TAG+':'+p],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/p).read_bytes().replace(b'\r\n',b'\n'),'Analysis tag drift')
    expect(subprocess.run(['git','merge-base','--is-ancestor',v['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Analysis ancestry')
    return v

def disjoint_union(groups,wanted):
    """Independent invariant used by private and public continuation admission."""
    result={}
    for group in groups:
        for row in group:
            expect(row['id'] not in result,'Repeated identity across collection batches')
            result[row['id']]=row
    expect(set(result)==set(wanted),'Incomplete or extraneous union')
    return list(result.values())

def terminated(relative,complete=False,*,stopped=False):
    from experiments.swarm_ledger_complete_dispatch import process_dead
    path=ROOT/relative
    expect(path.is_file() and not path.is_symlink(),'Actual driver metadata required')
    raw=path.read_bytes();v=json.loads(raw)
    expect(not (complete and stopped),'Conflicting driver requirement')
    expect(v['status']=='complete' if complete else v['status']=='stopped' if stopped else v['status'] in ('stopped','complete'),'Actual driver is not ready')
    stamp=datetime.fromisoformat(v['updated'].replace('Z','+00:00'))
    expect(stamp.tzinfo is not None and stamp.utcoffset()==timedelta(0) and stamp<=datetime.now(timezone.utc),'Final driver timestamp invalid')
    process_dead(v['pid'],v['updated'])
    if v.get('child_pid') is not None:process_dead(v['child_pid'],v['updated'])
    expect(path.read_bytes()==raw,'Driver state changed during proof')
    return sha(path)

def drivers(kind):
    if kind=='main':
        paths=[('runs/swarm-ledger-v1-main-driver/state.json',False),
               ('runs/swarm-ledger-resume-v1-driver/state.json',False),
               ('runs/swarm-ledger-resume-v2-driver/state.json',False),
               ('runs/swarm-ledger-resume-v3-driver/state.json',False),
               ('runs/swarm-ledger-efficient-v1-driver/state.json',True)]
    elif kind=='hf':
        paths=[('runs/factorial-driver-v1/state.json',False),('runs/hf-completion-driver-v1/state.json',False),
               ('runs/hf-completion-v2-driver/state.json',False),('runs/hf-completion-v3-driver/state.json',True)]
    else:raise ValueError('Unknown collection kind')
    return {p:terminated(p,complete,stopped=kind=='main' and not complete) for p,complete in paths}

def no_collectors():
    expect(not list(ROOT.glob('runs/**/collector.lock')),'Active/stale collector lock; never remove it')

def admission_main():
    from experiments import swarm_ledger_efficient as resume
    resume.verify();proof=drivers('main');no_collectors()
    contexts=s.contexts('main');a.validate_contexts(contexts)
    expect(s.digest(contexts)==s.read(s.freeze_path('main'))['contexts_sha256'],'MAIN contexts changed')
    previous={};coverage,engineering=a.validate_pre_main()
    for role in a.ROLES:
        jobs=s.actor_jobs(role,contexts,previous)
        rows,coverage[role]=resume.union_phase(role,jobs,require_complete=True)
        previous.update({r['id']:r for r in rows})
    sources=s.source_worlds(contexts,previous);jobs=s.reader_jobs(sources)
    readers,coverage['readers']=resume.union_phase('readers',jobs,require_complete=True)
    calibration=s.calibration_sources();cal_jobs=s.reader_jobs(calibration)
    cal_rows,coverage['calibration']=resume.union_phase('calibration',cal_jobs,require_complete=True)
    influence_jobs=s.influence_jobs(contexts,previous)
    influence,coverage['influence']=resume.union_phase('influence',influence_jobs,require_complete=True)
    def cases(worlds,planned,rows):
        byworld={w['source_id']:w for w in worlds};byrow={r['id']:r for r in rows};cache={};result=[]
        for j in planned:
            sid=j['metadata']['source_id'];w=byworld[sid]
            if sid not in cache:cache[sid]={('receipt_only7' if v['view']=='sufficient' else v['view']):v['packet'] for v in a.engine.views(w['public'],w['world'])}
            result.append(a.score_case(j,byrow[j['id']],w,cache[sid][j['metadata']['view']]))
        return result
    data=dict(contexts=contexts,sources=sources,actor_rows=list(previous.values()),cases=cases(sources,jobs,readers),
        calibration=cases(calibration,cal_jobs,cal_rows),influence_sources=s.influence_worlds(contexts,previous,influence),
        influence_rows=influence,coverage=coverage,engineering=engineering)
    expect(len(data['cases'])==53760 and len(data['calibration'])==240 and len(data['influence_rows'])==240,'Complete grid required')
    return data,proof

def export_main(output):
    verify();no_collectors();output=Path(output).resolve()
    expect(output.is_relative_to(ROOT.resolve()) and not output.exists(),'Use new in-project public directory')
    companion=MAIN_PROOF
    expect(not companion.exists(),'Release companion exists')
    with s.verified_config():
        data,proof=admission_main();commitment=a.data_commitment(data)
        manifest=a._write_public(data,output)
        checked=a.verify_public(output)
        expect(drivers('main')==proof and a.data_commitment(data)==commitment,'Admission changed during release')
        verify();no_collectors()
        from experiments import swarm_ledger_efficient as resume
        resume.verify()
        value=dict(schema_version=1,analysis_tag=TAG,analysis_freeze_sha256=s.sha(FREEZE),
            continuation_freeze_sha256=s.sha(resume.FREEZE),
            prior_continuation_freeze_sha256=s.sha(ROOT/'research/swarm-ledger-resume-v1-freeze.json'),
            server_continuation_freeze_sha256=s.sha(ROOT/'research/swarm-ledger-resume-v2-freeze.json'),
            provider_continuation_freeze_sha256=s.sha(ROOT/'research/swarm-ledger-resume-v3-freeze.json'),driver_state_sha256=proof,
            public_manifest_sha256=sha(output/'manifest.json'),public_report_sha256=sha(output/'report.json'),
            unchanged_scientific_serializer=True,verification=checked,inference_calls=0)
        with companion.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
        return checked

def verify_main(output,replay=True):
    verify();output=Path(output);proof=s.read(MAIN_PROOF)
    from experiments import swarm_ledger_efficient as resume
    expect(set(proof)=={'schema_version','analysis_tag','analysis_freeze_sha256','continuation_freeze_sha256',
        'prior_continuation_freeze_sha256','server_continuation_freeze_sha256','provider_continuation_freeze_sha256','driver_state_sha256','public_manifest_sha256','public_report_sha256','unchanged_scientific_serializer','verification','inference_calls'},'MAIN companion schema')
    expect(type(proof['schema_version']) is int and proof['schema_version']==1 and proof['analysis_tag']==TAG,'MAIN companion identity')
    expect(proof['analysis_freeze_sha256']==s.sha(FREEZE) and proof['continuation_freeze_sha256']==s.sha(resume.FREEZE)
        and proof['prior_continuation_freeze_sha256']==s.sha(ROOT/'research/swarm-ledger-resume-v1-freeze.json')
        and proof['server_continuation_freeze_sha256']==s.sha(ROOT/'research/swarm-ledger-resume-v2-freeze.json')
        and proof['provider_continuation_freeze_sha256']==s.sha(ROOT/'research/swarm-ledger-resume-v3-freeze.json'),'MAIN companion registration drift')
    expect(proof['public_manifest_sha256']==sha(output/'manifest.json') and proof['public_report_sha256']==sha(output/'report.json'),'MAIN companion artifact drift')
    expect(proof['unchanged_scientific_serializer'] is True and type(proof['inference_calls']) is int and proof['inference_calls']==0,'MAIN companion scope')
    expect(set(proof['driver_state_sha256'])=={'runs/swarm-ledger-v1-main-driver/state.json','runs/swarm-ledger-resume-v1-driver/state.json',
        'runs/swarm-ledger-resume-v2-driver/state.json','runs/swarm-ledger-resume-v3-driver/state.json','runs/swarm-ledger-efficient-v1-driver/state.json'},'MAIN driver provenance inventory')
    expect(all(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v) for v in proof['driver_state_sha256'].values()),'MAIN driver hash provenance')
    expect(proof['verification'].get('valid') is True,'MAIN prior replay missing')
    if replay:expect(a.verify_public(output)==proof['verification'],'MAIN scientific replay drift')
    return dict(valid=True,continuation_provenance_verified=True,scientific_replay_performed=replay)

def hf_completed():
    from experiments import hf_completion_v3 as resume
    from experiments import hf_completion_analysis as original
    from experiments import hf_completion as h
    from experiments import factorial_analysis as f
    # Even the completed separate HF cohort is released only after the actual
    # MAIN continuation has completed and all owned collectors have terminated.
    resume.verify();drivers('main');proof=drivers('hf');no_collectors()
    private,body_by,summary,commitments=resume.private_completed()
    fresh=[{k:r[k] for k in f.ALLOWED}|dict(request_sha256=body_by[r['id']]) for r in private]
    original._check_completion_counts(fresh,h.verify())
    original._summary_check(summary,fresh)
    actors,old,design=original._old_inputs();result=original.build_completed(actors,old,fresh,design)
    expect(result['analysis']['primary']['result']==s.read(ROOT/'research/factorial-report.json')['analysis']['primary']['result'],'Original primary changed')
    return fresh,result,summary,commitments,proof

def export_hf():
    verify();expect(not HF_REPORT.exists() and not HF_SUPPLEMENT.exists(),'Never overwrite an HF release')
    fresh,result,summary,commitments,proof=hf_completed()
    text=''.join(s.canonical(r)+'\n' for r in sorted(fresh,key=lambda r:r['id']))
    HF_SUPPLEMENT.write_text(text,encoding='utf-8',newline='\n')
    value=dict(schema_version=2,status='complete',analysis_tag=TAG,analysis_freeze_sha256=s.sha(FREEZE),
        supplement_sha256=sha(HF_SUPPLEMENT),source_registration_sha256=parents(),raw_batches_sha256=commitments,
        supplement_terminals=1898,original_terminals=11640,analysis=result['analysis'],
        availability=__import__('experiments.hf_completion_analysis',fromlist=['_availability'])._availability(result['cases']),
        operational_summary=summary,driver_state_sha256=proof,training_runs=0,
        provenance_limit='Sanitized scientific replay; native normalization requires private archived receipts; failed deliveries retained.')
    expect(drivers('hf')==proof,'HF drivers changed during release');verify();no_collectors()
    with HF_REPORT.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
    return verify_hf()

def verify_hf():
    from experiments import hf_completion_analysis as original
    from experiments import hf_completion as h
    verify();v=s.read(HF_REPORT)
    expect(set(v)==HF_KEYS,'HF public schema')
    expect(type(v['schema_version']) is int and v['schema_version']==2 and v['status']=='complete' and v['analysis_tag']==TAG,'HF public identity')
    expect(v['analysis_freeze_sha256']==s.sha(FREEZE) and v['source_registration_sha256']==parents(),'HF source drift')
    expect(v['supplement_sha256']==sha(HF_SUPPLEMENT),'HF public supplement changed')
    fresh=original.rows(HF_SUPPLEMENT);original._check_completion_counts(fresh,h.verify())
    original._summary_check(v['operational_summary'],fresh)
    expect(type(v['training_runs']) is int and v['training_runs']==0,'HF training scope drift')
    expected_batches={'hf-completion-v1','hf-completion-v2','hf-completion-v3'}
    expect(set(v['raw_batches_sha256'])==expected_batches,'HF three-batch provenance required')
    from experiments import hf_completion_v3 as resume
    registered=s.read(resume.FREEZE)['prior_raw_sha256']
    for batch,values in v['raw_batches_sha256'].items():
        expect(set(values)=={'plan.json','attempts.jsonl','responses.jsonl','summary.json'},'HF batch provenance schema')
        for filename,digest in values.items():
            expect(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'HF batch hash')
            if batch!='hf-completion-v3':expect(registered['runs/'+batch+'/'+filename]==digest,'HF stopped-prefix provenance changed')
    actors,old,design=original._old_inputs();result=original.build_completed(actors,old,fresh,design)
    expect(v['analysis']==result['analysis'] and v['availability']==original._availability(result['cases']),'HF scientific reconstruction differs')
    expect(v['supplement_terminals']==len(fresh)==1898 and v['original_terminals']==len(result['cases'])==11640,'HF completion denominator')
    expect(result['analysis']['primary']['result']==s.read(ROOT/'research/factorial-report.json')['analysis']['primary']['result'],'Original primary drift')
    return dict(valid=True,original_terminals=11640,supplement_terminals=1898,inference_calls=0)

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','verify','export-main','verify-main','export-hf','verify-hf'));p.add_argument('--output',type=Path);args=p.parse_args()
    if args.command=='export-main':expect(args.output is not None,'Explicit output required');result=export_main(args.output)
    elif args.command=='verify-main':expect(args.output is not None,'Explicit output required');result=verify_main(args.output)
    else:result={'freeze':freeze,'verify':verify,'export-hf':export_hf,'verify-hf':verify_hf}[args.command]()
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
