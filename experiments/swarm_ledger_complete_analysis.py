"""Complete six-reader MAIN with preserved eight-reader engineering provenance.

No monkeypatching: new MAIN uses its prospective adapter, while technical/DEV
replay explicitly uses the unchanged original study. No provider calls on import.
"""
import argparse
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

from experiments import swarm_ledger_analysis as legacy
from experiments import swarm_ledger_study as engineering_study
from experiments import swarm_ledger_complete as study

engine=legacy.engine
reference=legacy.reference
ROLES=legacy.ROLES
ARMS=legacy.ARMS
BOOTSTRAP_SEED=legacy.BOOTSTRAP_SEED
MAX_SHARD_BYTES=legacy.MAX_SHARD_BYTES
PROVENANCE_LIMIT=legacy.PROVENANCE_LIMIT
PUBLIC_SCOPE='Completed prospectively registered six-reader MAIN; original eight-reader engineering retained separately; no legacy pooling'
PROOF_KEYS={'data_sha256','driver_state','driver_state_sha256','registration_sha256','operational_registration_sha256'}
expect=legacy.expect
ratio=legacy.ratio
packet_support=legacy.packet_support
packet_wording=legacy.packet_wording
stratum=legacy.stratum
stratified_bootstrap=legacy.stratified_bootstrap
block_contrast=legacy.block_contrast
metric_summary=legacy.metric_summary
actor_effects=legacy.actor_effects
influence_effects=legacy.influence_effects
actor_summary=legacy.actor_summary
baseline_summary=legacy.baseline_summary
useful_completion=legacy.useful_completion
policy_correct_response=legacy.policy_correct_response
write_shards=legacy.write_shards
read_public_json=legacy.read_public_json


def invariant():
    # The adapter validates all unchanged fields, so these frozen helpers retain
    # identical model bodies, scoring and admission under their original globals.
    study.config()


def validate_contexts(contexts,repetitions=16):
    invariant();return legacy.validate_contexts(contexts,repetitions)


def score_case(*args,**kwargs):
    invariant();return legacy.score_case(*args,**kwargs)


def admit_phase(*args,**kwargs):
    invariant();return legacy.admit_phase(*args,**kwargs)


def public_actor_records(*args,**kwargs):
    invariant();return legacy.public_actor_records(*args,**kwargs)


def public_row(*args,**kwargs):
    invariant();return legacy.public_row(*args,**kwargs)


def public_phase(*args,**kwargs):
    invariant();return legacy.public_phase(*args,**kwargs)


def data_commitment(data):return study.digest({k:v for k,v in data.items() if k!='_admission'})


def validate_pre_main():
    invariant();return legacy.validate_pre_main()


def analyze(data,draws=10000):
    validate_contexts(data['contexts'])
    cases=data['cases'];groups=defaultdict(list)
    expect(len(cases)==53760 and len(data['sources'])==2560 and len(data['calibration'])==240,
           'Complete prospective six-reader MAIN required for analysis')
    expect({c['profile_id'] for c in cases}==set(study.config()['reader_profiles']),
           'Unexpected or incomplete six-reader profile grid')
    expect({c['block_id'] for c in cases}=={c['block_id'] for c in data['contexts']},'Reader/base-block identities differ')
    for c in cases:groups[(c['profile_id'],c['view'],c['procedure'])].append(c)
    primary=block_contrast(cases,('g26','full','procedure'),('g26','full','direct'),draws=draws)
    expect(primary['blocks']==640 and primary['strata']==40,'Primary registered source grid differs')
    acquisition={}
    sufficient_control={}
    for profile in study.config()['auxiliary_reader_profiles']:
        for view in ('receipt_only7','random_loss','selective_random2','selective_metadata2','selective_contract2'):
            a=(profile,view,'direct');b=(profile,'selective_loss','direct')
            acquisition[profile+':'+view+'-selective_loss']={
                'correct_supported_including_required_abstention':block_contrast(cases,a,b,metric='correct_supported',arms=('honest','both'),draws=draws),
                'correct_definite':block_contrast(cases,a,b,metric='correct_definite',arms=('honest','both'),draws=draws),
                'oracle_answerability':block_contrast(cases,a,b,metric='answerable',arms=('honest','both'),draws=draws)}
        sufficient_control[profile]=block_contrast(cases,(profile,'receipt_only7','direct'),
                                                   (profile,'full','direct'),arms=('honest','both'),draws=draws)
        for left,right in (('selective_metadata2','selective_random2'),('selective_contract2','selective_metadata2')):
            acquisition[profile+':'+left+'-'+right]={
                name:block_contrast(cases,(profile,left,'direct'),(profile,right,'direct'),metric=metric,
                                    arms=('honest','both'),draws=draws)
                for name,metric in (('correct_supported_including_required_abstention','correct_supported'),
                                    ('correct_definite','correct_definite'),('oracle_answerability','answerable'))}
    procedures={p:block_contrast(cases,(p,'full','procedure'),(p,'full','direct'),draws=draws)
                for p in study.config()['reader_profiles'] if p!='g26'}
    return dict(study_id=study.config()['study_id'],registration_prefix=study.config()['registration_prefix'],
                main_reader_profiles=study.config()['reader_profiles'],auxiliary_reader_profiles=study.config()['auxiliary_reader_profiles'],
                track='4: Multi-Agent Oversight and Control',
                question='Does a swarm auditor lack necessary evidence, or fail to use sufficient evidence?',
                source_blocks=640,assigned_trajectories=len(data['sources']),reader_responses=len(cases),
                primary=dict(estimand='G26 FULL16 procedure minus direct, parsed ungated correct definite verdict',**primary),
                conditions={':'.join(k):metric_summary(v) for k,v in sorted(groups.items())},
                source_unique_baselines=baseline_summary(cases),
                acquisition_direct=acquisition,receipt_only7_minus_full_matched=sufficient_control,
                secondary_procedure_effects=procedures,
                format_control={procedure:block_contrast(cases,('hf_schema','full',procedure),('hf_text','full',procedure),draws=draws)
                                for procedure in ('direct','procedure')},
                thinking_control={procedure:block_contrast(cases,('ds_low','full',procedure),('ds_off','full',procedure),draws=draws)
                                  for procedure in ('direct','procedure')},
                actor_assigned_arms=actor_summary(data['sources']),actor_itt=actor_effects(data['sources'],draws),
                influence_exploratory=influence_effects(data['influence_sources'],draws),
                calibration=metric_summary(data['calibration']),coverage=data['coverage'],
                scope='New MAIN only. Development, scripted calibration, influence receivers and legacy studies do not increase main n.',
                interpretation='Evidence restoration and reasoning contrasts are separate; their difference is not a causal apportionment.')


def load_public_artifacts(directory):
    """Strict offline inventory/hash admission, including bounded JSONL parts."""
    directory=Path(directory);expect(directory.is_dir() and not directory.is_symlink(),'Public artifact directory invalid')
    manifest=read_public_json(directory/'manifest.json')
    expect(set(manifest)=={'schema_version','study_id','scope','artifacts','report_sha256',
                          'configuration_sha256','registration_sha256','provenance_limit','registration_prefix','engineering_configuration_sha256','operational_registration_sha256'},'Public manifest schema')
    expect(type(manifest['schema_version']) is int and manifest['schema_version']==2 and
           manifest['study_id']==study.config()['study_id'] and manifest['registration_prefix']==study.config()['registration_prefix'] and manifest['scope']==PUBLIC_SCOPE and
           manifest['provenance_limit']==PROVENANCE_LIMIT,'Public manifest identity/scope')
    expected={*('cases:'+p for p in study.config()['reader_profiles']),
              'contexts','worlds','influence','calibration','actors','influence_receivers',
              'engineering_contexts','engineering_technical','engineering_actors','engineering_readers'}
    expect(set(manifest['artifacts'])==expected,'Public artifact groups differ')
    allowed={'manifest.json','report.json','config.json','registration.json',
             'registration-technical.json','registration-development.json','engineering-config.json','operational-registration.json'};loaded={}
    for group,parts in manifest['artifacts'].items():
        expect(type(parts) is list and bool(parts),'Missing public shard group');values=[]
        for ordinal,part in enumerate(parts):
            expect(type(part) is dict and set(part)=={'file','bytes','rows','sha256'},'Public shard schema')
            name=part['file'];stem=('cases-'+group.split(':')[1]) if group.startswith('cases:') else group.replace('_','-')
            expect(name==f'{stem}-{ordinal:04d}.jsonl' and name not in allowed,'Public shard path/order differs')
            allowed.add(name);path=directory/name
            expect(path.is_file() and not path.is_symlink(),'Public shard must be a regular local file')
            raw=path.read_bytes()
            expect(type(part['bytes']) is int and len(raw)==part['bytes']<=MAX_SHARD_BYTES and
                   hashlib.sha256(raw).hexdigest()==part['sha256'],'Public shard checksum/size differs')
            expect(raw.endswith(b'\n'),'Public shard has incomplete final line')
            rows=[json.loads(line,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite public JSON'))) for line in raw.splitlines()]
            expect(all(line==study.canonical(row).encode() for line,row in zip(raw.splitlines(),rows)),
                   'Public JSONL must use unambiguous canonical objects')
            expect(type(part['rows']) is int and len(rows)==part['rows'],'Public shard row count differs')
            values.extend(rows)
        loaded[group]=values
    expect({p.name for p in directory.iterdir()}==allowed and all(p.is_file() and not p.is_symlink() for p in directory.iterdir()),
           'Unlisted/nonregular public artifact')
    report_raw=(directory/'report.json').read_bytes()
    expect(hashlib.sha256(report_raw).hexdigest()==manifest['report_sha256'],'Public report checksum differs')
    expect(read_public_json(directory/'config.json')==study.config() and manifest['configuration_sha256']==study.sha(study.CONFIG),
           'Public configuration differs from registered sources')
    for split in ('technical','development','main'):
        registered=study.registration(split) if split=='main' else engineering_study.registration(split)
        filename='registration.json' if split=='main' else 'registration-'+split+'.json'
        expect(read_public_json(directory/filename)==registered,'Copied public registration differs')
    expect(manifest['registration_sha256']==study.sha(study.freeze_path('main')),'Public registration commitment differs')
    expect(read_public_json(directory/'engineering-config.json')==engineering_study.config() and
           manifest['engineering_configuration_sha256']==engineering_study.sha(engineering_study.CONFIG),'Original engineering configuration differs')
    from experiments import swarm_ledger_complete_dispatch as dispatch
    operational=dispatch.verify('main')
    expect(read_public_json(directory/'operational-registration.json')==operational and
           manifest['operational_registration_sha256']==study.sha(dispatch.op_freeze('main')),'Operational registration differs')
    return loaded,read_public_json(directory/'report.json'),manifest


@study.verified_config()
def replay_public(artifacts):
    """Reconstruct every planned job from public contexts and predecessor rows."""
    contexts=artifacts['contexts'];validate_contexts(contexts)
    expect(study.digest(contexts)==study.registration('main')['contexts_sha256'],'Public MAIN design differs')
    previous={};coverage={}
    tech,coverage['technical']=public_phase(engineering_study.technical_jobs(),artifacts['engineering_technical'],True)
    for row in tech:
        expect(engineering_study.admitted(row),'Public technical serving gate failed')
        if engineering_study.profile(row['profile_id']).get('format')=='json_schema':
            expect(engineering_study.score(row['response']['output_text'],{'NONE'})['raw_label']!='INVALID','Public technical schema gate failed')
    dev=artifacts['engineering_contexts'];validate_contexts(dev,2)
    expect(study.digest(dev)==engineering_study.registration('development')['contexts_sha256'],'Public development design differs')
    for role in ROLES:
        jobs=engineering_study.actor_jobs(role,dev,previous)
        records=[r for r in artifacts['engineering_actors'] if r['metadata'].get('stage')==role]
        rows,coverage['development:'+role]=public_phase(jobs,records,True);previous.update({r['id']:r for r in rows})
    dev_reader_jobs=engineering_study.reader_jobs(engineering_study.source_worlds(dev,previous))
    dev_readers,coverage['development:readers']=public_phase(dev_reader_jobs,artifacts['engineering_readers'],True)
    expect(len(artifacts['engineering_actors'])==len(previous),'Unexpected engineering actor stage')
    previous={}
    for role in ROLES:
        jobs=study.actor_jobs(role,contexts,previous)
        records=[r for r in artifacts['actors'] if r['metadata'].get('stage')==role]
        rows,coverage[role]=public_phase(jobs,records,True);previous.update({r['id']:r for r in rows})
    expect(len(artifacts['actors'])==len(previous),'Unexpected MAIN actor stage')
    sources=study.source_worlds(contexts,previous)
    expect(study.canonical(sources)==study.canonical(artifacts['worlds']),'Public host worlds differ from actor replay')
    cases=[]
    for p in study.config()['reader_profiles']:cases.extend(artifacts['cases:'+p])
    jobs=study.reader_jobs(sources);reader_rows,coverage['readers']=public_phase(jobs,cases)
    cal_sources=study.calibration_sources();cal_jobs=study.reader_jobs(cal_sources)
    cal_rows,coverage['calibration']=public_phase(cal_jobs,artifacts['calibration'])
    def verify_cases(sources,jobs,rows,published):
        worlds={s['source_id']:s for s in sources};byid={r['id']:r for r in rows};exported={r['id']:r for r in published};cache={};out=[]
        for j in jobs:
            src=worlds[j['metadata']['source_id']];sid=src['source_id']
            if sid not in cache:cache[sid]={('receipt_only7' if v['view']=='sufficient' else v['view']):v['packet'] for v in engine.views(src['public'],src['world'])}
            case=score_case(j,byid[j['id']],src,cache[sid][j['metadata']['view']])
            expect(study.canonical(case)==study.canonical(exported[j['id']]),'Public verdict/scoring/packet differs');out.append(case)
        return out
    cases=verify_cases(sources,jobs,reader_rows,cases)
    cal=verify_cases(cal_sources,cal_jobs,cal_rows,artifacts['calibration'])
    influence_jobs=study.influence_jobs(contexts,previous)
    influence_rows,coverage['influence']=public_phase(influence_jobs,artifacts['influence_receivers'],True)
    influence_sources=study.influence_worlds(contexts,previous,influence_rows)
    expect(len({s['source_id'] for s in artifacts['influence']})==len(artifacts['influence']) and
           study.canonical({s['source_id']:s for s in influence_sources})==
           study.canonical({s['source_id']:s for s in artifacts['influence']}),'Public influence worlds differ')
    expect(len(sources)==2560 and len(cases)==53760 and len(cal)==240 and len(influence_sources)==240,'Public registered grid differs')
    return dict(contexts=contexts,sources=sources,cases=cases,calibration=cal,coverage=coverage,
                actor_rows=list(previous.values()),influence_rows=influence_rows,influence_sources=influence_sources,
                engineering=dict(technical_rows=tech,development_contexts=dev,development_actor_rows=[],development_reader_rows=dev_readers))


@study.verified_config()
def verify_public(directory):
    """Offline public replay: no keys, private journals, driver or API access."""
    artifacts,report,manifest=load_public_artifacts(directory);data=replay_public(artifacts)
    expect(report['primary']['draws']==10000 and report['primary']['seed']==BOOTSTRAP_SEED,'Registered bootstrap differs')
    recomputed=analyze(data)
    expect(study.canonical(recomputed)==study.canonical(report),'Public report differs from reconstructed data')
    study.registration('main')
    return dict(valid=True,scope='offline public source/job/action/evidence/scoring/report replay',
                main_blocks=640,main_reader_terminals=53760,native_provenance_limit=manifest['provenance_limit'])

def driver_path():
    return study.ROOT/('runs/'+study.config()['study_id']+'-main-driver/state.json')


def termination_proof(state_path,owned_lock=None):
    """Accept absent processes or creation-time-proven reuse, never a fake PID."""
    from experiments import swarm_ledger_complete_dispatch as dispatch
    path=Path(state_path)
    expect(path.resolve()==driver_path().resolve() and path.resolve().is_relative_to(study.ROOT.resolve())
           and path.is_file() and not path.is_symlink(),'Actual MAIN driver state path required')
    raw=path.read_bytes();state=json.loads(raw)
    expect(state.get('status') in ('stopped','complete'),'MAIN driver remains active')
    updated=state.get('updated')
    try:final=datetime.fromisoformat(updated.replace('Z','+00:00'))
    except (ValueError,AttributeError):raise ValueError('Final driver UTC timestamp required') from None
    expect(final.tzinfo is not None and final.utcoffset()==timedelta(0) and final<=datetime.now(timezone.utc),'Final driver timestamp must be aware UTC and not future')
    parent=state.get('pid');child=state.get('child_pid')
    expect(type(parent) is int and type(child) is int and parent>0 and child>0 and parent!=child,'Actual parent and child process identities required')
    dispatch.process_dead(parent,updated);dispatch.process_dead(child,updated)
    expect(path.read_bytes()==raw,'Driver state changed during termination checks')
    locks=[p for p in study.ROOT.glob('runs/**/collector.lock') if owned_lock is None or p.resolve()!=Path(owned_lock).resolve()]
    expect(not locks,'Active or stale global collector lock; never remove another owner lock')
    return dict(driver_state=str(path.resolve()),driver_state_sha256=hashlib.sha256(raw).hexdigest())


def _registrations():
    from experiments import swarm_ledger_complete_dispatch as dispatch
    study.registration('main');dispatch.verify('main')
    return dict(registration_sha256=study.sha(study.freeze_path('main')),
                operational_registration_sha256=study.sha(dispatch.op_freeze('main')))


def check_admission(data,owned_lock=None):
    proof=data.get('_admission')
    expect(type(proof) is dict and set(proof)==PROOF_KEYS,'PID-safe private admission proof required')
    expect({k:proof[k] for k in ('registration_sha256','operational_registration_sha256')}==_registrations(),'Scientific/operational registration changed')
    actual=termination_proof(proof['driver_state'],owned_lock)
    expect(all(proof[k]==v for k,v in actual.items()),'Actual driver state bytes changed after admission')
    expect(proof['data_sha256']==data_commitment(data),'Data changed after private admission')
    expect(all(c['complete'] for c in data['coverage'].values()),'All registered phases must be complete')
    return proof


def _build_private(state_path,owned_lock):
    """Frozen private orchestration with only the release-idle guard replaced."""
    anchors=_registrations();identity=termination_proof(state_path,owned_lock)
    split='main';out=study.folder(split);ctxs=study.contexts(split);validate_contexts(ctxs)
    expect(study.digest(ctxs)==study.read(study.freeze_path(split))['contexts_sha256'],'Context registration differs')
    previous={};coverage,engineering=validate_pre_main()
    for role in ROLES:
        jobs=study.actor_jobs(role,ctxs,previous);rows,coverage[role]=admit_phase(out/role,jobs,registration_path=study.freeze_path(split))
        previous.update({r['id']:r for r in rows})
    sources=study.source_worlds(ctxs,previous);jobs=study.reader_jobs(sources)
    reader_rows,coverage['readers']=admit_phase(out/'readers',jobs,registration_path=study.freeze_path(split))
    cal_sources=study.calibration_sources();cal_jobs=study.reader_jobs(cal_sources)
    cal_rows,coverage['calibration']=admit_phase(out/'calibration',cal_jobs,registration_path=study.freeze_path(split))
    influence_jobs=study.influence_jobs(ctxs,previous)
    influence_rows,coverage['influence']=admit_phase(out/'influence',influence_jobs,registration_path=study.freeze_path(split))
    influence_sources=study.influence_worlds(ctxs,previous,influence_rows)
    def cases(source_list,job_list,rows):
        worlds={source['source_id']:source for source in source_list};byid={r['id']:r for r in rows};result=[];cache={}
        for job in job_list:
            sid=job['metadata']['source_id'];source=worlds[sid]
            if sid not in cache:cache[sid]={('receipt_only7' if v['view']=='sufficient' else v['view']):v['packet'] for v in engine.views(source['public'],source['world'])}
            result.append(score_case(job,byid[job['id']],source,cache[sid][job['metadata']['view']]))
        return result
    main=cases(sources,jobs,reader_rows);cal=cases(cal_sources,cal_jobs,cal_rows)
    expect(len(sources)==2560 and len(main)==53760 and len(cal)==240 and len(influence_sources)==240,'Registered MAIN trajectory/reader/calibration/influence grid differs')
    result=dict(contexts=ctxs,sources=sources,actor_rows=list(previous.values()),cases=main,calibration=cal,
                influence_sources=influence_sources,influence_rows=influence_rows,coverage=coverage,engineering=engineering)
    result['_admission']=dict(data_sha256=data_commitment(result),**identity,**anchors)
    check_admission(result,owned_lock)
    return result


def build_private(driver_state):
    with study.verified_config():
        guard=study.ROOT/('runs/'+study.config()['study_id']+'-guard')
        with study.exclusive(guard):return _build_private(driver_state,guard/'collector.lock')


def _write_public(data,directory,draws=10000):
    """Frozen serializer body; no operational extras enter the public inventory."""
    directory=Path(directory);expect(not directory.exists(),'Export destination already exists')
    report=analyze(data,draws);directory.mkdir(parents=True)
    parts={};groups=defaultdict(list)
    for c in data['cases']:groups[c['profile_id']].append(c)
    for profile,rows in sorted(groups.items()):parts['cases:'+profile]=write_shards(directory,'cases-'+profile,rows)
    parts['contexts']=write_shards(directory,'contexts',data['contexts'])
    parts['worlds']=write_shards(directory,'worlds',data['sources'])
    parts['influence']=write_shards(directory,'influence',data['influence_sources'])
    parts['calibration']=write_shards(directory,'calibration',data['calibration'])
    actor_jobs={};previous={}
    for role in ROLES:
        actor_jobs.update({j['id']:j for j in study.actor_jobs(role,data['contexts'],previous)})
        previous.update({r['id']:r for r in data['actor_rows'] if r['metadata'].get('stage')==role})
    actor_jobs.update({j['id']:j for j in study.influence_jobs(data['contexts'],previous)})
    parts['actors']=write_shards(directory,'actors',public_actor_records(data['actor_rows'],actor_jobs))
    parts['influence_receivers']=write_shards(directory,'influence-receivers',public_actor_records(data['influence_rows'],actor_jobs))
    eng=data['engineering'];dev_jobs={};previous={}
    for role in ROLES:
        dev_jobs.update({j['id']:j for j in engineering_study.actor_jobs(role,eng['development_contexts'],previous)})
        previous.update({r['id']:r for r in eng['development_actor_rows'] if r['metadata'].get('stage')==role})
    dev_readers={j['id']:j for j in engineering_study.reader_jobs(engineering_study.source_worlds(eng['development_contexts'],previous))}
    parts['engineering_contexts']=write_shards(directory,'engineering-contexts',eng['development_contexts'])
    parts['engineering_technical']=write_shards(directory,'engineering-technical',public_actor_records(eng['technical_rows'],{j['id']:j for j in engineering_study.technical_jobs()}))
    parts['engineering_actors']=write_shards(directory,'engineering-actors',public_actor_records(eng['development_actor_rows'],dev_jobs))
    parts['engineering_readers']=write_shards(directory,'engineering-readers',public_actor_records(eng['development_reader_rows'],dev_readers))
    from experiments import swarm_ledger_complete_dispatch as dispatch
    (directory/'engineering-config.json').write_text(json.dumps(engineering_study.config(),indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'operational-registration.json').write_text(json.dumps(dispatch.verify('main'),indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'config.json').write_text(json.dumps(study.config(),indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'registration.json').write_text(json.dumps(study.read(study.freeze_path('main')),indent=2)+'\n',encoding='utf-8',newline='\n')
    for split in ('technical','development'):
        (directory/('registration-'+split+'.json')).write_text(json.dumps(engineering_study.read(engineering_study.freeze_path(split)),indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest=dict(schema_version=2,study_id=study.config()['study_id'],registration_prefix=study.config()['registration_prefix'],scope=PUBLIC_SCOPE,
        artifacts=parts,report_sha256=hashlib.sha256((directory/'report.json').read_bytes()).hexdigest(),
        configuration_sha256=study.sha(study.CONFIG),registration_sha256=study.sha(study.freeze_path('main')),
        engineering_configuration_sha256=engineering_study.sha(engineering_study.CONFIG),
        operational_registration_sha256=study.sha(dispatch.op_freeze('main')),provenance_limit=PROVENANCE_LIMIT)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    return manifest


def _export(data,directory,owned_lock):
    expect(Path(directory).resolve().is_relative_to(study.ROOT.resolve()),'Export must remain inside the project')
    check_admission(data,owned_lock)
    manifest=_write_public(data,directory)
    check_admission(data,owned_lock)
    verified=verify_public(directory)
    check_admission(data,owned_lock)
    return dict(manifest=manifest,verification=verified)


def export(data,directory):
    with study.verified_config():
        guard=study.ROOT/('runs/'+study.config()['study_id']+'-guard')
        with study.exclusive(guard):return _export(data,directory,guard/'collector.lock')


def release(driver_state,directory):
    """Admission through final verification under one actual collector guard."""
    with study.verified_config():
        guard=study.ROOT/('runs/'+study.config()['study_id']+'-guard')
        with study.exclusive(guard):
            data=_build_private(driver_state,guard/'collector.lock')
            return _export(data,directory,guard/'collector.lock')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('validate','export','verify-public'))
    parser.add_argument('--driver-state',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='verify-public':
        expect(args.output is not None,'Public directory required');result=verify_public(args.output)
    else:
        expect(args.driver_state is not None,'Actual MAIN driver state required')
        if args.command=='validate':result=dict(complete=True,coverage=build_private(args.driver_state)['coverage'])
        else:
            expect(args.output is not None,'Export directory required');result=release(args.driver_state,args.output)
    print(study.canonical(result))

if __name__=='__main__':main()
