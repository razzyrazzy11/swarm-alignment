"""Explicit preserved private-admission receipt plus unchanged public replay.

The default private/native gate remains authoritative for issuance. A public
consumer verifies commitments and mathematics, never fresh native authenticity.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

TAG='paper-public-verification-v1'
FREEZE_NAME='research/paper-public-verification-v1-freeze.json'
ADMISSION_NAME='research/paper-public-release-admission.json'
FIGURE_INPUT_NAME='research/paper-public-figure-input.json'
PRIVATE_FIGURE_INPUT='runs/offline-release-recovery-v2-driver/verified-public-input.json'
OWNER_STATE='runs/offline-release-recovery-v2-driver/state.json'
METHOD='Preserved successful private/native admission; unchanged public mathematical replay; no fresh native authenticity claim'
SCOPE='Public source/artifact commitments and frozen mathematics; native authenticity requires the private archive'
SOURCES=('paper/public_replay.py','paper/tests/test_public_replay.py','research/PAPER_PUBLIC_REPLAY_PROTOCOL.md',
         'paper/complete_report_contract.py','paper/verify.py','paper/tests/test_public_verify_mode.py',
         '.github/workflows/report-integrity.yml','.gitattributes')
PARENTS=('research/offline-release-recovery-v2-freeze.json','research/offline-release-recovery-v1-freeze.json',
         'research/paced-resume-analysis-v1-freeze.json')
STAGES=('hf_export','main_export','continuation_provenance','figure_input','figures','figure_provenance','generator_sensitivity')
PUBLIC_DIRECTORIES=('data/swarm-ledger-v1-public','data/swarm-ledger-generator-sensitivity-v1',
                    'paper/figures/swarm-ledger-complete-v1')
HF_REPORT='research/hf-completed-original-results-v3.json'
HF_SUPPLEMENT='data/hf_completed_original_supplement_v3.jsonl'
HF_PROOF='research/hf-offline-release-recovery-v2-proof.json'
MAIN_PROOF='research/swarm-ledger-paced-resume-release-proof.json'
LEDGER_RESEARCH=(
 'offline-release-recovery-v2-freeze.json','hf-offline-release-recovery-v2-proof.json',
 'offline-release-recovery-v1-freeze.json','hf-offline-release-recovery-proof.json',
 'paced-resume-analysis-v1-freeze.json','swarm-ledger-paced-v1-freeze.json','swarm-ledger-paced-resume-release-proof.json',
 'rate-resume-analysis-v1-freeze.json','swarm-ledger-rate-v1-freeze.json','swarm-ledger-rate-resume-release-proof.json',
 'efficient-resume-analysis-v1-freeze.json','swarm-ledger-efficient-v1-freeze.json','swarm-ledger-efficient-resume-release-proof.json',
 'provider-resume-analysis-v1-freeze.json','swarm-ledger-resume-v3-freeze.json','swarm-ledger-provider-resume-release-proof.json',
 'server-resume-analysis-v1-freeze.json','swarm-ledger-resume-v2-freeze.json','swarm-ledger-server-resume-release-proof.json',
 'router-resume-analysis-v1-freeze.json','swarm-ledger-resume-v1-freeze.json','swarm-ledger-resume-release-proof.json',
 'hf-completion-v3-freeze.json','hf-completed-original-results-v3.json',
 'adaption-serving-pilot-v1-freeze.json','adaption-serving-pilot-results.json')
MAIN_DRIVERS={f'runs/{name}/state.json' for name in ('swarm-ledger-v1-main-driver','swarm-ledger-resume-v1-driver',
 'swarm-ledger-resume-v2-driver','swarm-ledger-resume-v3-driver','swarm-ledger-efficient-v1-driver',
 'swarm-ledger-rate-v1-driver','swarm-ledger-paced-v1-driver')}
HF_DRIVERS={f'runs/{name}/state.json' for name in ('factorial-driver-v1','hf-completion-driver-v1',
 'hf-completion-v2-driver','hf-completion-v3-driver')}
FAILED_V1={f'runs/paced-resume-postprocess-driver/{name}' for name in ('state.json','hf_export.stdout.log','hf_export.stderr.log')}
FAILED_V2=FAILED_V1|{f'runs/offline-release-recovery-driver/{name}' for name in ('state.json','hf_export.stdout.log','hf_export.stderr.log')}
MAIN_VERIFICATION=dict(valid=True,scope='offline public source/job/action/evidence/scoring/report replay',
    main_blocks=640,main_reader_terminals=53760,
    native_provenance_limit='Public replay verifies exported jobs/actions/evidence/scoring. HTTP/native authenticity requires the private archive; receipt hashes commit to those archived bytes.')


def require(ok,message):
    if not ok:raise ValueError(message)


def source_hash(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def raw_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return type(value) is str and re.fullmatch(r'[0-9a-f]{64}',value) is not None


def read(path):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'Duplicate public receipt key');result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite public JSON')))


def relative_file(root,name,*,private=False):
    require(type(name) is str and '\\' not in name and ':' not in name,'Unsafe public commitment path')
    p=PurePosixPath(name)
    require(not p.is_absolute() and p.parts and all(x not in ('','.','..') for x in p.parts),'Unsafe public commitment path')
    require(p.parts[0] in (('runs',) if private else ('paper','research','data','experiments','analysis','.github','.gitattributes')),
            'Unknown public commitment root')
    root=Path(root).resolve();target=root/name
    require(all(not q.is_symlink() for q in (target,*target.parents) if q!=root.parent),'Symlink commitment refused')
    require(target.resolve().is_relative_to(root) and target.is_file(),'Missing public commitment: '+name)
    return target


def hash_map(value,*,names=None):
    require(type(value) is dict and value and all(type(k) is str and digest(v) for k,v in value.items()),'Hash commitment schema')
    if names is not None:require(set(value)==set(names),'Hash commitment inventory differs')


def timestamp(value):
    require(type(value) is str,'UTC receipt timestamp required')
    try:stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise ValueError('UTC receipt timestamp required') from None
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds()==0 and stamp<=datetime.now(timezone.utc),
            'UTC receipt timestamp invalid')


def _git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.PIPE)


def _tag_files(root,tag,base,names):
    require(type(tag) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',tag),'Registration tag invalid')
    require(type(base) is str and re.fullmatch(r'[0-9a-f]{40}',base),'Registration base commit invalid')
    for name in names:
        path=relative_file(root,name)
        blob=_git(root,'show',tag+':'+name)
        require(blob.replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n'),'Public registration tag drift')
    require(subprocess.run(['git','merge-base','--is-ancestor',base,tag+'^{}'],cwd=root,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode==0,'Public registration ancestry differs')


def _lineage(root):
    from experiments import offline_release_recovery_v2 as v2_module, offline_release_recovery as v1_module, paced_resume_analysis as paced
    result={}
    tags=('offline-release-recovery-v2','offline-release-recovery-v1','paced-resume-analysis-v1')
    for name,tag,module in zip(PARENTS,tags,(v2_module,v1_module,paced)):
        value=read(relative_file(root,name))
        keys={'schema_version','tag','created','base_commit','source_sha256','parent_registration_sha256'}
        keys|={'method'} if tag=='paced-resume-analysis-v1' else {'failed_waiter_sha256','projection_rule','timing'}
        require(set(value)==keys and type(value['schema_version']) is int and value['schema_version']==1 and value['tag']==tag,
                'Preserved registration schema/identity differs')
        timestamp(value['created']);hash_map(value['source_sha256'],names=module.SOURCES)
        parent_names=(PARENTS[1],PARENTS[2],'research/hf-completion-v3-freeze.json') if tag.endswith('v2') else (
            (PARENTS[2],'research/hf-completion-v3-freeze.json') if tag.endswith('v1') and tag.startswith('offline-') else paced.PARENTS)
        hash_map(value['parent_registration_sha256'],names=parent_names)
        for source,expected in value['source_sha256'].items():
            require(source_hash(relative_file(root,source))==expected,'Preserved source drift')
        for parent,expected in value['parent_registration_sha256'].items():
            require(parent.startswith('research/') and parent.endswith('-freeze.json'),'Unknown registration parent')
            require(source_hash(relative_file(root,parent))==expected,'Preserved registration parent drift')
        if tag!='paced-resume-analysis-v1':
            hash_map(value['failed_waiter_sha256'],names=FAILED_V2 if tag.endswith('v2') else FAILED_V1)
            rule='validated-next-delay-and-private-transport-to-frozen-public-schema-v2' if tag.endswith('v2') else 'validated-private-transport-to-frozen-public-three-field-schema-v1'
            require(value['projection_rule']==rule,'Unknown private projection rule')
        _tag_files(root,tag,value['base_commit'],(*value['source_sha256'],name))
        result[name]=value
    v2,v1=(result[PARENTS[i]] for i in (0,1))
    require(all(v2['failed_waiter_sha256'][k]==v for k,v in v1['failed_waiter_sha256'].items()),'Failed waiter lineage mismatch')
    require(v2['parent_registration_sha256'][PARENTS[1]]==source_hash(root/PARENTS[1]) and
            v2['parent_registration_sha256'][PARENTS[2]]==v1['parent_registration_sha256'][PARENTS[2]]==source_hash(root/PARENTS[2]),
            'Recovery parent lineage mismatch')
    return result


def public_artifact_hashes(root):
    """Hash-only inventory for prospective registration; no issue or replay."""
    root=Path(root).resolve();names={HF_REPORT,HF_SUPPLEMENT,HF_PROOF,MAIN_PROOF}
    names.update('research/'+name for name in LEDGER_RESEARCH if (root/'research'/name).exists())
    for folder in PUBLIC_DIRECTORIES:
        directory=root/folder
        require(directory.is_dir() and not directory.is_symlink(),'Required public artifact directory missing')
        files=list(directory.iterdir())
        require(files and all(p.is_file() and not p.is_symlink() for p in files),'Unexpected public artifact directory entry')
        names.update(p.relative_to(root).as_posix() for p in files)
    # Fixed roots and all ancestry bytes are source-bound, never private logs.
    for name in PARENTS:
        value=read(relative_file(root,name));names.update(value['parent_registration_sha256'])
    return {name:raw_hash(relative_file(root,name)) for name in sorted(names)}


def verify_registration(root,require_pushed=False):
    root=Path(root).resolve();value=read(relative_file(root,FREEZE_NAME))
    require(set(value)=={'schema_version','tag','created','base_commit','source_sha256','parent_registration_sha256',
                        'public_artifact_sha256','verified_figure_input_sha256','owner_state_sha256','owner_supervisor_sha256','method'},'Public verification freeze schema')
    require(type(value['schema_version']) is int and value['schema_version']==1 and value['tag']==TAG and value['method']==METHOD,
            'Public verification freeze identity/scope')
    timestamp(value['created']);hash_map(value['source_sha256'],names=SOURCES);hash_map(value['parent_registration_sha256'],names=PARENTS)
    hash_map(value['public_artifact_sha256'])
    require(all(digest(value[k]) for k in ('verified_figure_input_sha256','owner_state_sha256','owner_supervisor_sha256')),
            'Admission input/owner hash invalid')
    require(value['source_sha256']=={name:source_hash(relative_file(root,name)) for name in SOURCES},'Public verification source drift')
    require(value['parent_registration_sha256']=={name:source_hash(relative_file(root,name)) for name in PARENTS},'Public verification parent drift')
    require(value['public_artifact_sha256']==public_artifact_hashes(root),'Registered public artifact drift')
    _tag_files(root,TAG,value['base_commit'],(*SOURCES,FREEZE_NAME))
    if require_pushed:
        local=_git(root,'rev-parse','refs/tags/'+TAG).decode().strip()
        remote=_git(root,'ls-remote','--tags','origin','refs/tags/'+TAG).decode().splitlines()
        require(len(remote)==1 and remote[0].split()==[local,'refs/tags/'+TAG],'Public verification tag is not pushed')
    return value


def _figure_receipt(root,name):
    value=read(relative_file(root,name,private=name.startswith('runs/')))
    require(set(value)=={'schema_version','kind','inputs','scientific_sources','scientific_runtime'} and
            type(value['schema_version']) is int and value['schema_version']==1 and value['kind']=='swarm-ledger-verified-public-input',
            'Safe public figure input schema differs')
    hash_map(value['inputs']);hash_map(value['scientific_sources'])
    runtime=value['scientific_runtime']
    require(type(runtime) is dict and set(runtime)=={'verification','python_executable','python_version','python_implementation'},
            'Safe figure runtime allowlist differs')
    require(all(type(runtime[k]) is str and runtime[k] and len(runtime[k])<1024 for k in ('python_executable','python_version','python_implementation')),
            'Safe figure runtime invalid')
    require(runtime['verification']==MAIN_VERIFICATION and runtime['verification'].get('valid') is True and
            type(runtime['verification'].get('main_blocks')) is int and type(runtime['verification'].get('main_reader_terminals')) is int,
        'Safe figure verification record differs')
    from analysis import ledger_complete_figures as figures
    require(value['inputs']==figures.input_hashes(root/'data/swarm-ledger-v1-public'),'Safe figure input hashes differ')
    require(value['scientific_sources']==figures.source_hashes(root/'data/swarm-ledger-v1-public'),'Safe figure source hashes differ')
    return value


def ledger_sources(root):
    directory=Path(root)/'data/swarm-ledger-v1-public';manifest=read(directory/'manifest.json')
    value={name:raw_hash(directory/name) for name in ('manifest.json','report.json','registration.json','operational-registration.json')}
    value.update(scientific_registration_sha256=manifest['registration_sha256'],
                 operational_registration_sha256=manifest['operational_registration_sha256'])
    value.update({name:raw_hash(Path(root)/'research'/name) for name in LEDGER_RESEARCH if (Path(root)/'research'/name).exists()})
    value['generator_sensitivity_report_sha256']=raw_hash(Path(root)/'data/swarm-ledger-generator-sensitivity-v1/report.json')
    hash_map(value)
    return value


def _public_proofs(root,lineage):
    from experiments import paced_resume_analysis as paced
    main=read(relative_file(root,MAIN_PROOF));hf=read(relative_file(root,HF_PROOF));report=read(relative_file(root,HF_REPORT))
    require(set(main)=={'schema_version','analysis_tag','analysis_freeze_sha256','continuation_freeze_sha256',
        'prior_continuation_freeze_sha256','server_continuation_freeze_sha256','provider_continuation_freeze_sha256',
        'efficient_continuation_freeze_sha256','rate_continuation_freeze_sha256','driver_state_sha256','public_manifest_sha256',
        'public_report_sha256','unchanged_scientific_serializer','verification','inference_calls'},'MAIN proof schema differs')
    require(type(main['schema_version']) is int and main['schema_version']==1 and main['analysis_tag']=='paced-resume-analysis-v1' and
            main['analysis_freeze_sha256']==source_hash(root/PARENTS[2]),'MAIN proof source identity')
    bindings={'continuation_freeze_sha256':'swarm-ledger-paced-v1','prior_continuation_freeze_sha256':'swarm-ledger-resume-v1',
              'server_continuation_freeze_sha256':'swarm-ledger-resume-v2','provider_continuation_freeze_sha256':'swarm-ledger-resume-v3',
              'efficient_continuation_freeze_sha256':'swarm-ledger-efficient-v1','rate_continuation_freeze_sha256':'swarm-ledger-rate-v1'}
    require(all(main[k]==source_hash(root/'research'/(name+'-freeze.json')) for k,name in bindings.items()),'MAIN proof parent drift')
    require(main['public_manifest_sha256']==raw_hash(root/'data/swarm-ledger-v1-public/manifest.json') and
            main['public_report_sha256']==raw_hash(root/'data/swarm-ledger-v1-public/report.json'),'MAIN proof artifact drift')
    hash_map(main['driver_state_sha256'],names=MAIN_DRIVERS)
    require(main['unchanged_scientific_serializer'] is True and type(main['inference_calls']) is int and main['inference_calls']==0
            and main['verification']==MAIN_VERIFICATION and main['verification'].get('valid') is True and
            type(main['verification'].get('main_blocks')) is int and type(main['verification'].get('main_reader_terminals')) is int,
            'MAIN proof scope differs')
    require(set(hf)=={'schema_version','recovery_tag','recovery_freeze_sha256','paced_analysis_freeze_sha256','projection_rule',
        'public_report_sha256','public_supplement_sha256','raw_batches_sha256','driver_state_sha256','frozen_verification','inference_calls'},
        'HF projection proof schema differs')
    require(type(hf['schema_version']) is int and hf['schema_version']==1 and hf['recovery_tag']=='offline-release-recovery-v2' and
            hf['recovery_freeze_sha256']==source_hash(root/PARENTS[0]) and hf['paced_analysis_freeze_sha256']==source_hash(root/PARENTS[2]) and
            hf['projection_rule']==lineage[PARENTS[0]]['projection_rule'],'HF projection proof identity differs')
    require(hf['public_report_sha256']==raw_hash(root/HF_REPORT) and hf['public_supplement_sha256']==raw_hash(root/HF_SUPPLEMENT),
            'HF projection artifacts differ')
    require(set(report)==paced.HF_KEYS,'HF public report schema differs')
    require(type(hf['raw_batches_sha256']) is dict and set(hf['raw_batches_sha256'])=={'hf-completion-v1','hf-completion-v2','hf-completion-v3'},
            'HF raw-batch inventory differs')
    for hashes in hf['raw_batches_sha256'].values():hash_map(hashes,names={'plan.json','attempts.jsonl','responses.jsonl','summary.json'})
    hash_map(hf['driver_state_sha256'],names=HF_DRIVERS)
    require(hf['raw_batches_sha256']==report['raw_batches_sha256'] and hf['driver_state_sha256']==report['driver_state_sha256'],
            'HF public provenance crossmatch differs')
    require(hf['frozen_verification']==dict(valid=True,original_terminals=11640,supplement_terminals=1898,inference_calls=0) and
            type(hf['inference_calls']) is int and hf['inference_calls']==0,'HF frozen verification scope differs')
    return {'main_driver_state_sha256':main['driver_state_sha256'],'hf_driver_state_sha256':hf['driver_state_sha256'],
            'failed_waiter_sha256':lineage[PARENTS[0]]['failed_waiter_sha256']}


def _owner_attestation(root,freeze):
    state=read(relative_file(root,OWNER_STATE,private=True))
    require(raw_hash(root/OWNER_STATE)==freeze['owner_state_sha256'],'Preserved owner state drift')
    require(state.get('kind')=='offline_release_recovery_v2' and state.get('status')=='complete' and
            state.get('completed_stages')==list(STAGES) and state.get('child_pid') is None and
            type(state.get('exit_code')) is int and state['exit_code']==0 and type(state.get('inference_calls')) is int and state['inference_calls']==0,
            'Completed seven-stage owner required')
    require(state.get('supervisor_sha256')==freeze['owner_supervisor_sha256']==raw_hash(root/'experiments/offline_release_supervisor_v2.py') and
            state.get('recovery_freeze_sha256')==source_hash(root/PARENTS[0]),'Owner source identity drift')
    return dict(kind='offline_release_recovery_v2',status='complete',completed_stages=list(STAGES),child_absent=True,
                exit_code=0,inference_calls=0,state_sha256=freeze['owner_state_sha256'],
                supervisor_sha256=state['supervisor_sha256'],recovery_freeze_sha256=state['recovery_freeze_sha256'],
                terminated_verified_at_issuance=True)


def _validate_admission(value,freeze,freeze_sha,recovery_sha,input_sha,provenance,sources):
    """Pure receipt validator shared by private issuance and fixed-path consumer."""
    require(type(value) is dict and set(value)=={'schema_version','kind','issued_at','scope','registration_tag','registration_freeze_sha256',
                        'public_artifact_sha256','verified_figure_input_sha256','preserved_owner','provenance','ledger_sources'},
            'Public admission receipt schema differs')
    require(type(value['schema_version']) is int and value['schema_version']==1 and value['kind']=='paper-public-release-admission' and
            value['scope']==SCOPE and value['registration_tag']==TAG and value['registration_freeze_sha256']==freeze_sha,
            'Public admission identity/scope differs')
    timestamp(value['issued_at'])
    require(value['public_artifact_sha256']==freeze['public_artifact_sha256'],'Public admission artifact commitments differ')
    require(value['verified_figure_input_sha256']==freeze['verified_figure_input_sha256']==input_sha,
            'Public figure input commitment differs')
    owner=value['preserved_owner']
    require(type(owner) is dict and set(owner)=={'kind','status','completed_stages','child_absent','exit_code','inference_calls','state_sha256',
            'supervisor_sha256','recovery_freeze_sha256','terminated_verified_at_issuance'},'Preserved owner attestation schema differs')
    expected=dict(kind='offline_release_recovery_v2',status='complete',completed_stages=list(STAGES),child_absent=True,
        exit_code=0,inference_calls=0,state_sha256=freeze['owner_state_sha256'],
        supervisor_sha256=freeze['owner_supervisor_sha256'],
        recovery_freeze_sha256=recovery_sha,terminated_verified_at_issuance=True)
    require(owner==expected and type(owner['exit_code']) is int and type(owner['inference_calls']) is int and
            owner['child_absent'] is True and owner['terminated_verified_at_issuance'] is True,'Preserved owner attestation differs')
    require(value['provenance']==provenance,'Public provenance commitments differ')
    require(value['ledger_sources']==sources,'Public ledger source commitments differ')
    return value


def verify_admission_metadata(paper):
    root=Path(paper).resolve().parent;freeze=verify_registration(root);lineage=_lineage(root)
    value=read(relative_file(root,ADMISSION_NAME))
    _figure_receipt(root,FIGURE_INPUT_NAME)
    return _validate_admission(value,freeze,source_hash(root/FREEZE_NAME),source_hash(root/PARENTS[0]),
        raw_hash(relative_file(root,FIGURE_INPUT_NAME)),_public_proofs(root,lineage),ledger_sources(root))


def verify_public_admission(paper):
    """Explicit public path. No private state/log read or native liveness probe."""
    paper=Path(paper).resolve();root=paper.parent
    value=verify_admission_metadata(paper)
    from experiments import paced_resume_analysis as paced
    from analysis import ledger_complete_figures as figures
    from paper import prepare_complete
    paced.verify_hf()  # Frozen source/public reconstruction, no private admission.
    figures.verify_only(root/'data/swarm-ledger-v1-public',root/FIGURE_INPUT_NAME,paper/'figures/swarm-ledger-complete-v1')
    require(prepare_complete.verify_sensitivity(paper)==value['ledger_sources']['generator_sensitivity_report_sha256'],
            'Public sensitivity replay drift')
    require(verify_admission_metadata(paper)==value,'Public admission changed during replay')
    return dict(valid=True,scope=SCOPE,native_authenticity='preserved private admission only; private archive required',inference_calls=0)


def issue(paper):
    """One-shot local issuer. Registration/push and unchanged private gate first."""
    paper=Path(paper).resolve();root=paper.parent
    require(not (root/ADMISSION_NAME).exists() and not (root/FIGURE_INPUT_NAME).exists(),'Never overwrite public admission artifacts')
    freeze=verify_registration(root,require_pushed=True)
    from paper import prepare_complete
    _,bindings=prepare_complete.ready(paper)  # Unchanged full private/native admission and all mathematics.
    require(verify_registration(root)==freeze,'Registration changed during private admission')
    lineage=_lineage(root);owner=_owner_attestation(root,freeze)
    _figure_receipt(root,PRIVATE_FIGURE_INPUT)
    raw=relative_file(root,PRIVATE_FIGURE_INPUT,private=True).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==freeze['verified_figure_input_sha256'],'Private figure receipt drift')
    require(b'\r' not in raw,'Safe figure input must preserve LF bytes across public checkouts')
    require(bindings==ledger_sources(root),'Private/public ledger source commitment differs')
    value=dict(schema_version=1,kind='paper-public-release-admission',issued_at=datetime.now(timezone.utc).isoformat(),scope=SCOPE,
        registration_tag=TAG,registration_freeze_sha256=source_hash(root/FREEZE_NAME),public_artifact_sha256=freeze['public_artifact_sha256'],
        verified_figure_input_sha256=freeze['verified_figure_input_sha256'],preserved_owner=owner,
        provenance=_public_proofs(root,lineage),ledger_sources=bindings)
    # Validate the complete assembled candidate in memory with the SAME pure
    # metadata consumer contract, before either immutable output is opened.
    _validate_admission(value,freeze,source_hash(root/FREEZE_NAME),source_hash(root/PARENTS[0]),
                        hashlib.sha256(raw).hexdigest(),_public_proofs(root,lineage),ledger_sources(root))
    # The safe input is an exact byte copy only after its strict allowlist check.
    with (root/FIGURE_INPUT_NAME).open('xb') as stream:stream.write(raw)
    with (root/ADMISSION_NAME).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    verify_admission_metadata(paper)
    return dict(created=True,scope=SCOPE,inference_calls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('issue','verify'))
    args=parser.parse_args();paper=Path(__file__).resolve().parent
    print(json.dumps(issue(paper) if args.command=='issue' else verify_public_admission(paper),indent=2))


if __name__=='__main__':main()
