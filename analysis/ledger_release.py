"""Prospective PID-safe release orchestration over unchanged frozen science.

No credentials, native journals, process inspection or API calls on import.
Only explicit validate/export commands admit private completed MAIN data.
"""
import argparse
from collections import defaultdict
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path

from experiments import swarm_ledger_analysis as a
from experiments import swarm_ledger_dispatch_v2 as dispatch
from experiments import swarm_ledger_study as s

PROOF_KEYS={'data_sha256','driver_state','driver_state_sha256','registration_sha256','operational_registration_sha256'}
expect=a.expect


def driver_path():
    return s.ROOT/('runs/'+s.config()['study_id']+'-main-driver/state.json')


def termination_proof(state_path,owned_lock=None):
    """Accept absent processes or creation-time-proven reuse, never a fake PID."""
    path=Path(state_path)
    expect(path.resolve()==driver_path().resolve() and path.resolve().is_relative_to(s.ROOT.resolve())
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
    locks=[p for p in s.ROOT.glob('runs/**/collector.lock') if owned_lock is None or p.resolve()!=Path(owned_lock).resolve()]
    expect(not locks,'Active or stale global collector lock; never remove another owner lock')
    return dict(driver_state=str(path.resolve()),driver_state_sha256=hashlib.sha256(raw).hexdigest())


def _registrations():
    s.registration('main');dispatch.verify('main')
    return dict(registration_sha256=s.sha(s.freeze_path('main')),
                operational_registration_sha256=s.sha(dispatch.op_freeze('main')))


def check_admission(data,owned_lock=None):
    proof=data.get('_admission')
    expect(type(proof) is dict and set(proof)==PROOF_KEYS,'PID-safe private admission proof required')
    expect({k:proof[k] for k in ('registration_sha256','operational_registration_sha256')}==_registrations(),'Scientific/operational registration changed')
    actual=termination_proof(proof['driver_state'],owned_lock)
    expect(all(proof[k]==v for k,v in actual.items()),'Actual driver state bytes changed after admission')
    expect(proof['data_sha256']==a.data_commitment(data),'Data changed after private admission')
    expect(all(c['complete'] for c in data['coverage'].values()),'All registered phases must be complete')
    return proof


def _build_private(state_path,owned_lock):
    """Frozen private orchestration with only the release-idle guard replaced."""
    anchors=_registrations();identity=termination_proof(state_path,owned_lock)
    split='main';out=s.folder(split);ctxs=s.contexts(split);a.validate_contexts(ctxs)
    expect(s.digest(ctxs)==s.read(s.freeze_path(split))['contexts_sha256'],'Context registration differs')
    previous={};coverage,engineering=a.validate_pre_main()
    for role in a.ROLES:
        jobs=s.actor_jobs(role,ctxs,previous);rows,coverage[role]=a.admit_phase(out/role,jobs,registration_path=s.freeze_path(split))
        previous.update({r['id']:r for r in rows})
    sources=s.source_worlds(ctxs,previous);jobs=s.reader_jobs(sources)
    reader_rows,coverage['readers']=a.admit_phase(out/'readers',jobs,registration_path=s.freeze_path(split))
    cal_sources=s.calibration_sources();cal_jobs=s.reader_jobs(cal_sources)
    cal_rows,coverage['calibration']=a.admit_phase(out/'calibration',cal_jobs,registration_path=s.freeze_path(split))
    influence_jobs=s.influence_jobs(ctxs,previous)
    influence_rows,coverage['influence']=a.admit_phase(out/'influence',influence_jobs,registration_path=s.freeze_path(split))
    influence_sources=s.influence_worlds(ctxs,previous,influence_rows)
    def cases(source_list,job_list,rows):
        worlds={source['source_id']:source for source in source_list};byid={r['id']:r for r in rows};result=[];cache={}
        for job in job_list:
            sid=job['metadata']['source_id'];source=worlds[sid]
            if sid not in cache:cache[sid]={('receipt_only7' if v['view']=='sufficient' else v['view']):v['packet'] for v in a.engine.views(source['public'],source['world'])}
            result.append(a.score_case(job,byid[job['id']],source,cache[sid][job['metadata']['view']]))
        return result
    main=cases(sources,jobs,reader_rows);cal=cases(cal_sources,cal_jobs,cal_rows)
    expect(len(sources)==2560 and len(main)==64000 and len(cal)==320 and len(influence_sources)==240,'Registered MAIN trajectory/reader/calibration/influence grid differs')
    result=dict(contexts=ctxs,sources=sources,actor_rows=list(previous.values()),cases=main,calibration=cal,
                influence_sources=influence_sources,influence_rows=influence_rows,coverage=coverage,engineering=engineering)
    result['_admission']=dict(data_sha256=a.data_commitment(result),**identity,**anchors)
    check_admission(result,owned_lock)
    return result


def build_private(driver_state):
    with s.verified_config():
        guard=s.ROOT/('runs/'+s.config()['study_id']+'-guard')
        with s.exclusive(guard):return _build_private(driver_state,guard/'collector.lock')


def _write_public(data,directory,draws=10000):
    """Frozen serializer body; no operational extras enter the public inventory."""
    directory=Path(directory);expect(not directory.exists(),'Export destination already exists')
    report=a.analyze(data,draws);directory.mkdir(parents=True)
    parts={};groups=defaultdict(list)
    for c in data['cases']:groups[c['profile_id']].append(c)
    for profile,rows in sorted(groups.items()):parts['cases:'+profile]=a.write_shards(directory,'cases-'+profile,rows)
    parts['contexts']=a.write_shards(directory,'contexts',data['contexts'])
    parts['worlds']=a.write_shards(directory,'worlds',data['sources'])
    parts['influence']=a.write_shards(directory,'influence',data['influence_sources'])
    parts['calibration']=a.write_shards(directory,'calibration',data['calibration'])
    actor_jobs={};previous={}
    for role in a.ROLES:
        actor_jobs.update({j['id']:j for j in s.actor_jobs(role,data['contexts'],previous)})
        previous.update({r['id']:r for r in data['actor_rows'] if r['metadata'].get('stage')==role})
    actor_jobs.update({j['id']:j for j in s.influence_jobs(data['contexts'],previous)})
    parts['actors']=a.write_shards(directory,'actors',a.public_actor_records(data['actor_rows'],actor_jobs))
    parts['influence_receivers']=a.write_shards(directory,'influence-receivers',a.public_actor_records(data['influence_rows'],actor_jobs))
    eng=data['engineering'];dev_jobs={};previous={}
    for role in a.ROLES:
        dev_jobs.update({j['id']:j for j in s.actor_jobs(role,eng['development_contexts'],previous)})
        previous.update({r['id']:r for r in eng['development_actor_rows'] if r['metadata'].get('stage')==role})
    dev_readers={j['id']:j for j in s.reader_jobs(s.source_worlds(eng['development_contexts'],previous))}
    parts['engineering_contexts']=a.write_shards(directory,'engineering-contexts',eng['development_contexts'])
    parts['engineering_technical']=a.write_shards(directory,'engineering-technical',a.public_actor_records(eng['technical_rows'],{j['id']:j for j in s.technical_jobs()}))
    parts['engineering_actors']=a.write_shards(directory,'engineering-actors',a.public_actor_records(eng['development_actor_rows'],dev_jobs))
    parts['engineering_readers']=a.write_shards(directory,'engineering-readers',a.public_actor_records(eng['development_reader_rows'],dev_readers))
    (directory/'config.json').write_text(json.dumps(s.config(),indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'registration.json').write_text(json.dumps(s.read(s.freeze_path('main')),indent=2)+'\n',encoding='utf-8',newline='\n')
    for split in ('technical','development'):
        (directory/('registration-'+split+'.json')).write_text(json.dumps(s.read(s.freeze_path(split)),indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest=dict(schema_version=1,study_id=s.config()['study_id'],scope=a.PUBLIC_SCOPE,
        artifacts=parts,report_sha256=hashlib.sha256((directory/'report.json').read_bytes()).hexdigest(),
        configuration_sha256=s.sha(s.CONFIG),registration_sha256=s.sha(s.freeze_path('main')),
        provenance_limit=a.PROVENANCE_LIMIT)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    return manifest


def _export(data,directory,owned_lock):
    expect(Path(directory).resolve().is_relative_to(s.ROOT.resolve()),'Export must remain inside the project')
    check_admission(data,owned_lock)
    manifest=_write_public(data,directory)
    check_admission(data,owned_lock)
    verified=a.verify_public(directory)
    check_admission(data,owned_lock)
    return dict(manifest=manifest,verification=verified)


def export(data,directory):
    with s.verified_config():
        guard=s.ROOT/('runs/'+s.config()['study_id']+'-guard')
        with s.exclusive(guard):return _export(data,directory,guard/'collector.lock')


def release(driver_state,directory):
    """Admission through final verification under one actual collector guard."""
    with s.verified_config():
        guard=s.ROOT/('runs/'+s.config()['study_id']+'-guard')
        with s.exclusive(guard):
            data=_build_private(driver_state,guard/'collector.lock')
            return _export(data,directory,guard/'collector.lock')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('validate','export'));parser.add_argument('--driver-state',type=Path,required=True)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.command=='validate':
        data=build_private(args.driver_state);result=dict(complete=True,coverage=data['coverage'])
    else:
        expect(args.output is not None,'Explicit export directory required');result=release(args.driver_state,args.output)
    print(s.canonical(result))


if __name__=='__main__':main()
