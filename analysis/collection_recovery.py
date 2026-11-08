"""Metadata-only recovery supervision; the frozen live collector owns resumption."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from analysis.collection_progress import stamp,CUTOFF,DEADLINE,require,registered_deadline_policy


def decide(driver, availability, now, owned_process_alive, *, cutoff=CUTOFF):
    require(type(owned_process_alive) is bool,'Actual process observation required')
    require(now.tzinfo is not None,'Aware current time required')
    require(isinstance(cutoff,datetime) and cutoff.tzinfo is not None and cutoff<=DEADLINE,'Invalid reporting cutoff')
    value=dict(schema_version=1,checked_at=now.isoformat(),inference_retry_permitted=False,
        collector_restart_permitted=False,automatic_recovery_owner='registered live collector',
        scientific_validation_complete=False,collection_cutoff_utc=cutoff.isoformat(),submission_deadline_utc=DEADLINE.isoformat())
    status=driver.get('status')
    if status=='complete':
        return dict(value,action='wait_for_actual_termination_and_strict_replay',attention=False)
    if status!='running' or not owned_process_alive:
        return dict(value,action='preserve_and_investigate_no_blind_restart',attention=True)
    if now>=cutoff:
        return dict(value,action='check_cutoff_and_drain_no_new_dispatch',attention=True)
    if availability and availability.get('status')=='waiting':
        updated=stamp(availability['updated'])
        require(updated<=now,'Future recovery status')
        remaining=availability.get('episode_remaining_seconds')
        if remaining is not None:
            require(type(remaining) in (int,float) and 0<=remaining<=900,'Invalid episode remainder')
        # This only supervises the published admission budget; it never signals
        # a process or authorizes another POST. Blocking GETs/draining can finish
        # later and must be investigated instead of blindly relaunching.
        expiry=updated+timedelta(seconds=900 if remaining is None else remaining)
        attention=now>=expiry
        return dict(value,action='inspect_expired_recovery_budget' if attention else 'wait_for_registered_automatic_resume',
            attention=attention,admission_budget_expires_utc=expiry.isoformat(),
            failure_class=availability.get('failure_class'),provider=availability.get('provider'),next_dispatch_at=availability.get('next_dispatch_at'),
            scope='Provider-scoped hold when provider is set; other providers may continue under registered guards')
    return dict(value,action='continue_metadata_monitoring',attention=False)


def startup_decision(manifest,observed,now,*,cutoff=CUTOFF):
    """A bounded, exact native creation match can explain pre-state startup.

    This is observation only: it never launches/restarts a process or permits
    inference. Missing, invalid, reused or expired identities require attention.
    """
    require(now.tzinfo is not None and cutoff.tzinfo is not None,'Aware startup clock required')
    value=dict(schema_version=1,checked_at=now.isoformat(),attention=True,
        action='inspect_missing_or_invalid_startup_identity',inference_retry_permitted=False,
        collector_restart_permitted=False,collector_launch_permitted=False,
        scientific_validation_complete=False,collection_cutoff_utc=cutoff.isoformat(),
        submission_deadline_utc=DEADLINE.isoformat(),startup_budget_seconds=1800)
    try:
        require(type(manifest) is dict and type(observed) is dict,'Native startup evidence missing')
        require(manifest.get('kind')=='collect' and manifest.get('source_tag')=='swarm-ledger-paced-v1','Startup lineage differs')
        require(type(manifest.get('pid')) is int and manifest['pid']>0 and type(observed.get('pid')) is int
                and observed['pid']==manifest['pid'],'Startup PID differs')
        # Compare the native timestamp literally, retaining its 100ns precision;
        # datetime parsing alone would truncate the seventh fractional digit.
        require(manifest.get('created_utc')==observed.get('created_utc'),'Native creation identity differs')
        created=stamp(manifest.get('created_utc'));launched=stamp(manifest.get('launched_utc'))
        require(created<=now and launched<=now,'Future startup evidence')
        expires=launched+timedelta(seconds=1800)
    except (ValueError,TypeError,KeyError):
        return value
    if now>=cutoff:return dict(value,action='check_cutoff_and_startup_no_new_dispatch')
    if now>=expires:return dict(value,action='inspect_unexplained_30_minute_startup',startup_budget_expires_utc=expires.isoformat())
    return dict(value,attention=False,action='wait_for_registered_startup',
        startup_budget_expires_utc=expires.isoformat(),
        scope='Live matching paced launch identity; source/prefix verification may precede durable driver state')


def main():
    root=Path(__file__).resolve().parents[1]
    paced=(root/'research/swarm-ledger-paced-v1-freeze.json').exists()
    efficient=(root/'research/swarm-ledger-efficient-v1-freeze.json').exists()
    rate=(root/'research/swarm-ledger-rate-v1-freeze.json').exists()
    state=root/('runs/swarm-ledger-paced-v1-driver/state.json' if paced else 'runs/swarm-ledger-rate-v1-driver/state.json' if rate else 'runs/swarm-ledger-efficient-v1-driver/state.json' if efficient else 'runs/swarm-ledger-resume-v3-driver/state.json')
    if not state.is_file():
        require(paced,'Actual registered driver required')
        from experiments.server_resume_preflight import process_snapshot
        manifest_path=root/'runs/paced-resume-launch/launch.json'
        manifest=None;observed=None
        if manifest_path.is_file() and not manifest_path.is_symlink():
            try:
                manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
                if type(manifest) is dict and type(manifest.get('pid')) is int and manifest['pid']>0:
                    observed=process_snapshot(manifest['pid'])
            except (ValueError,TypeError,OSError):pass
        policy=registered_deadline_policy(root)
        result=startup_decision(manifest,observed,datetime.now(timezone.utc),cutoff=stamp(policy['collection_cutoff_utc']))
        result.update(policy)
        print(json.dumps(result,allow_nan=False));raise SystemExit(bool(result['attention']))
    driver=json.loads(state.read_text(encoding='utf-8'))
    from experiments.server_resume_preflight import process_snapshot
    observed=process_snapshot(driver['pid'])
    alive=bool(observed and stamp(observed['created_utc'])<=stamp(driver['updated']))
    if driver.get('child_pid') is not None:
        child=process_snapshot(driver['child_pid'])
        alive=alive and bool(child and stamp(child['created_utc'])<=stamp(driver['updated']))
    path=root/('runs/swarm-ledger-paced-v1-main/availability-state.json' if paced else 'runs/swarm-ledger-rate-v1-main/availability-state.json' if rate else 'runs/swarm-ledger-efficient-v1-main/availability-state.json' if efficient else 'runs/swarm-ledger-resume-v3-main/availability-state.json')
    available=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    policy=registered_deadline_policy(root)
    result=decide(driver,available,datetime.now(timezone.utc),alive,cutoff=stamp(policy['collection_cutoff_utc']))
    result.update(policy)
    print(json.dumps(result,allow_nan=False));raise SystemExit(bool(result['attention']))


if __name__=='__main__':main()
