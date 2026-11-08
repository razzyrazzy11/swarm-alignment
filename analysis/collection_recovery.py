"""Metadata-only recovery supervision; the frozen live collector owns resumption."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from analysis.collection_progress import stamp,CUTOFF,require


def decide(driver, availability, now, owned_process_alive):
    require(type(owned_process_alive) is bool,'Actual process observation required')
    require(now.tzinfo is not None,'Aware current time required')
    value=dict(schema_version=1,checked_at=now.isoformat(),inference_retry_permitted=False,
        collector_restart_permitted=False,automatic_recovery_owner='registered live collector',
        scientific_validation_complete=False)
    status=driver.get('status')
    if status=='complete':
        return dict(value,action='wait_for_actual_termination_and_strict_replay',attention=False)
    if status!='running' or not owned_process_alive:
        return dict(value,action='preserve_and_investigate_no_blind_restart',attention=True)
    if now>=CUTOFF:
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
            failure_class=availability.get('failure_class'),next_dispatch_at=availability.get('next_dispatch_at'))
    return dict(value,action='continue_metadata_monitoring',attention=False)


def main():
    root=Path(__file__).resolve().parents[1]
    efficient=(root/'research/swarm-ledger-efficient-v1-freeze.json').exists()
    state=root/('runs/swarm-ledger-efficient-v1-driver/state.json' if efficient else 'runs/swarm-ledger-resume-v3-driver/state.json')
    require(state.is_file(),'Actual registered v3 driver required')
    driver=json.loads(state.read_text(encoding='utf-8'))
    from experiments.server_resume_preflight import process_snapshot
    observed=process_snapshot(driver['pid'])
    alive=bool(observed and stamp(observed['created_utc'])<=stamp(driver['updated']))
    if driver.get('child_pid') is not None:
        child=process_snapshot(driver['child_pid'])
        alive=alive and bool(child and stamp(child['created_utc'])<=stamp(driver['updated']))
    path=root/('runs/swarm-ledger-efficient-v1-main/availability-state.json' if efficient else 'runs/swarm-ledger-resume-v3-main/availability-state.json')
    available=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    result=decide(driver,available,datetime.now(timezone.utc),alive)
    print(json.dumps(result,allow_nan=False));raise SystemExit(bool(result['attention']))


if __name__=='__main__':main()
