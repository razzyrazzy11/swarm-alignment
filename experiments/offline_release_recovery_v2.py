"""V2 scheduler-metadata boundary over frozen V1 projection; no inference.

Frozen raw/native admission happens before projection. Scientific fields,
failed terminals, costs, request identities, scoring and bootstrap are unchanged.
"""
import argparse
from copy import deepcopy
from datetime import datetime,timedelta
import math
import hashlib
import json
from pathlib import Path
import re
import subprocess

from experiments import offline_release_recovery as v1
from experiments import paced_resume_analysis as paced
from experiments import hf_completion_v3 as collection
from experiments import hf_completion_analysis as original
from experiments import factorial_analysis as factorial

ROOT=paced.ROOT
TAG='offline-release-recovery-v2'
FREEZE=ROOT/'research/offline-release-recovery-v2-freeze.json'
PROOF=ROOT/'research/hf-offline-release-recovery-v2-proof.json'
SOURCES=('experiments/offline_release_recovery_v2.py','experiments/tests/test_offline_release_recovery_v2.py',
         'research/OFFLINE_RELEASE_RECOVERY_V2_PROTOCOL.md','experiments/offline_release_supervisor_v2.py',
         'experiments/tests/test_offline_release_supervisor_v2.py')
RULE='validated-next-delay-and-private-transport-to-frozen-public-schema-v2'
expect=paced.expect


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parents():
    v1.verify();paced.verify();collection.verify()
    return {p.relative_to(ROOT).as_posix():paced.s.sha(p) for p in (v1.FREEZE,paced.FREEZE,collection.FREEZE)}


def failed_waiter():
    relative='runs/offline-release-recovery-driver/state.json'
    commitment=paced.terminated(relative,stopped=True)
    path=ROOT/relative;state=paced.s.read(path)
    expect(state.get('status')=='stopped' and state.get('stage')=='hf_export' and
           state.get('completed_stages')==[] and state.get('reason')=='phase_failed_no_retry' and
           state.get('exit_code')==1 and state.get('error_class')=='ValueError',
           'Exact failed first HF export attestation required')
    paths=[path,path.parent/'hf_export.stdout.log',path.parent/'hf_export.stderr.log']
    expect(all(p.is_file() and not p.is_symlink() for p in paths),'Actual failed waiter evidence required')
    result={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    expect(result[relative]==commitment,'Failed waiter state changed during proof')
    return dict(v1.failed_waiter(),**result)


def require_unused_targets():
    targets=(paced.HF_REPORT,paced.HF_SUPPLEMENT,PROOF,ROOT/'data/swarm-ledger-v1-public',paced.MAIN_PROOF,
             ROOT/'runs/offline-release-recovery-v2-driver',ROOT/'paper/figures/swarm-ledger-complete-v1',
             ROOT/'data/swarm-ledger-generator-sensitivity-v1')
    expect(not any(p.exists() for p in targets),'Offline recovery requires unused output targets')
    return True


def freeze():
    expect(not FREEZE.exists(),'Offline recovery registration exists')
    require_unused_targets();failed=failed_waiter()
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit offline recovery sources first')
    record=dict(schema_version=1,tag=TAG,created=paced.s.now(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256={name:paced.s.sha(ROOT/name) for name in SOURCES},parent_registration_sha256=parents(),failed_waiter_sha256=failed,
                projection_rule=RULE,timing='After frozen V1 offline release failed on known scheduler metadata; before V2 recovered scoring or output; no new inference')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,tag=TAG,inference_calls=0)


def verify():
    value=paced.s.read(FREEZE)
    expect(set(value)=={'schema_version','tag','created','base_commit','source_sha256','parent_registration_sha256','failed_waiter_sha256','projection_rule','timing'},'Recovery registration schema')
    expect(type(value['schema_version']) is int and value['schema_version']==1 and value['tag']==TAG and value['projection_rule']==RULE,'Recovery registration identity')
    expect(value['source_sha256']=={name:paced.s.sha(ROOT/name) for name in SOURCES} and value['parent_registration_sha256']==parents(),'Recovery source or parent drift')
    expect(value['failed_waiter_sha256']==failed_waiter(),'Failed first waiter evidence changed')
    for name in (*SOURCES,FREEZE.relative_to(ROOT).as_posix()):
        blob=subprocess.check_output(['git','show',TAG+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Recovery tag drift')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Recovery ancestry')
    return value


def project_admitted(private,body_by):
    """Validate/omit only scheduler metadata, then use frozen V1 projection."""
    scientific=[]
    for row in private:
        expect('next_delay_seconds' in row,'Recorded scheduler metadata missing')
        delay=row['next_delay_seconds']
        # No invented upper bound: even a stopped Retry-After path can record
        # a delay above the live wait envelope. It does not affect the verdict.
        expect(type(delay) in (int,float) and (type(delay) is int or math.isfinite(delay)) and delay>=0,
               'Recorded scheduler delay must be finite nonnegative numeric')
        value=deepcopy(row);del value['next_delay_seconds'];scientific.append(value)
    return v1.project_admitted(scientific,body_by)


def hf_completed():
    verify();collection.verify();paced.drivers('main');proof=paced.drivers('hf');paced.no_collectors()
    # This frozen call verifies raw prefixes, native normalization, identities,
    # request-body commitments, error receipts, unknown reserves and final costs.
    private,body_by,summary,commitments=collection.private_completed()
    fresh=project_admitted(private,body_by)
    original._check_completion_counts(fresh,original.h.verify());original._summary_check(summary,fresh)
    actors,old,design=original._old_inputs();result=original.build_completed(actors,old,fresh,design)
    expect(result['analysis']['primary']['result']==paced.s.read(ROOT/'research/factorial-report.json')['analysis']['primary']['result'],'Original primary changed')
    return fresh,result,summary,commitments,proof


def export_hf():
    verify();expect(not paced.HF_REPORT.exists() and not paced.HF_SUPPLEMENT.exists() and not PROOF.exists(),'Never overwrite an offline release')
    fresh,result,summary,commitments,proof=hf_completed()
    text=''.join(paced.s.canonical(row)+'\n' for row in sorted(fresh,key=lambda row:row['id']))
    with paced.HF_SUPPLEMENT.open('x',encoding='utf-8',newline='\n') as file:file.write(text)
    value=dict(schema_version=2,status='complete',analysis_tag=paced.TAG,analysis_freeze_sha256=paced.s.sha(paced.FREEZE),
        supplement_sha256=sha(paced.HF_SUPPLEMENT),source_registration_sha256=paced.parents(),raw_batches_sha256=commitments,
        supplement_terminals=1898,original_terminals=11640,analysis=result['analysis'],availability=original._availability(result['cases']),
        operational_summary=summary,driver_state_sha256=proof,training_runs=0,
        provenance_limit='Sanitized scientific replay; native normalization requires private archived receipts; failed deliveries retained.')
    expect(paced.drivers('hf')==proof,'HF drivers changed during release');verify();paced.no_collectors()
    with paced.HF_REPORT.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(value,indent=2)+'\n')
    checked=paced.verify_hf()  # Frozen scientific/public verifier remains authoritative.
    record=dict(schema_version=1,recovery_tag=TAG,recovery_freeze_sha256=paced.s.sha(FREEZE),
                paced_analysis_freeze_sha256=paced.s.sha(paced.FREEZE),projection_rule=RULE,
                public_report_sha256=sha(paced.HF_REPORT),public_supplement_sha256=sha(paced.HF_SUPPLEMENT),
                raw_batches_sha256=commitments,driver_state_sha256=proof,frozen_verification=checked,inference_calls=0)
    with PROOF.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return verify_projection(replay=False)


def verify_projection(replay=False):
    verify();value=paced.s.read(PROOF)
    expect(set(value)=={'schema_version','recovery_tag','recovery_freeze_sha256','paced_analysis_freeze_sha256','projection_rule',
                       'public_report_sha256','public_supplement_sha256','raw_batches_sha256','driver_state_sha256','frozen_verification','inference_calls'},'Projection proof schema')
    expect(type(value['schema_version']) is int and value['schema_version']==1 and value['recovery_tag']==TAG and value['projection_rule']==RULE,'Projection proof identity')
    expect(value['recovery_freeze_sha256']==paced.s.sha(FREEZE) and value['paced_analysis_freeze_sha256']==paced.s.sha(paced.FREEZE),'Projection registration drift')
    expect(value['public_report_sha256']==sha(paced.HF_REPORT) and value['public_supplement_sha256']==sha(paced.HF_SUPPLEMENT),'Projection public artifact drift')
    expected={'hf-completion-v1','hf-completion-v2','hf-completion-v3'}
    expect(set(value['raw_batches_sha256'])==expected,'Projection three-batch inventory')
    for hashes in value['raw_batches_sha256'].values():
        expect(set(hashes)=={'plan.json','attempts.jsonl','responses.jsonl','summary.json'} and all(type(d) is str and re.fullmatch(r'[0-9a-f]{64}',d) for d in hashes.values()),'Projection raw hash schema')
    expect(set(value['driver_state_sha256'])=={'runs/factorial-driver-v1/state.json','runs/hf-completion-driver-v1/state.json','runs/hf-completion-v2-driver/state.json','runs/hf-completion-v3-driver/state.json'} and all(type(d) is str and re.fullmatch(r'[0-9a-f]{64}',d) for d in value['driver_state_sha256'].values()),'Projection driver hash inventory')
    expect(value['frozen_verification']==dict(valid=True,original_terminals=11640,supplement_terminals=1898,inference_calls=0) and type(value['inference_calls']) is int and value['inference_calls']==0,'Projection frozen verification missing')
    report=paced.s.read(paced.HF_REPORT)
    expect(value['raw_batches_sha256']==report['raw_batches_sha256'] and
           value['driver_state_sha256']==report['driver_state_sha256'],'Projection provenance differs from committed report')
    if replay:expect(paced.verify_hf()==value['frozen_verification'],'Projection scientific replay drift')
    return dict(valid=True,projection_verified=True,scientific_replay_performed=replay,inference_calls=0)


def verify_hf():return verify_projection(replay=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('freeze','verify','export-hf','verify-hf'));args=parser.parse_args()
    result={'freeze':freeze,'verify':verify,'export-hf':export_hf,'verify-hf':verify_hf}[args.command]()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
