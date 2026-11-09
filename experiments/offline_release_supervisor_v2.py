"""One-shot, prospectively registered offline recovery; never performs inference."""
import hashlib
import json
import os
from pathlib import Path
import sys

from experiments import paced_resume_supervisor as prior

ROOT = Path(__file__).resolve().parents[1]
DRIVER = 'runs/offline-release-recovery-v2-driver'
STAGES = prior.STAGES


def processing_jobs():
    jobs = prior.processing_jobs()
    jobs[0] = ('hf_export', [sys.executable, '-m',
                           'experiments.offline_release_recovery_v2', 'export-hf'])
    old = 'runs/paced-resume-postprocess-driver/verified-public-input.json'
    new = DRIVER + '/verified-public-input.json'
    return [(stage, [new if arg == old else arg for arg in command])
            for stage, command in jobs]


def admission():
    from experiments import offline_release_recovery_v2 as recovery
    from experiments import paced_resume_analysis as release
    recovery.verify()
    recovery.require_unused_targets()
    release.drivers('main')
    release.drivers('hf')
    release.no_collectors()
    release.terminated('runs/paced-resume-postprocess-driver/state.json',
                       stopped=True)
    release.terminated('runs/offline-release-recovery-driver/state.json', stopped=True)
    return recovery


def main():
    folder = ROOT / DRIVER
    # Refuse even an empty existing directory: an interrupted launch is evidence.
    if folder.exists():
        raise ValueError('Offline recovery directory exists; never restart blindly')
    recovery = admission()
    jobs = processing_jobs()
    if tuple(stage for stage, _ in jobs) != STAGES:
        raise ValueError('Exact seven offline stages required')
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / 'state.json'
    state = dict(status='processing', pid=os.getpid(), child_pid=None,
                 completed_stages=[], kind='offline_release_recovery_v2',
                 supervisor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 recovery_freeze_sha256=hashlib.sha256(recovery.FREEZE.read_bytes()).hexdigest(),
                 inference_calls=0, paper_authored=False, visual_qa_complete=False)
    prior.save(path, state)
    try:
        for stage, command in jobs:
            prior.child_run(folder, state, path, stage, command)
            state['completed_stages'].append(stage)
            prior.save(path, state)
        state.update(status='complete', exit_code=0, child_pid=None)
        prior.save(path, state)
    except BaseException as error:
        state.update(status='stopped', error_class=type(error).__name__)
        state.setdefault('reason', 'offline_release_failure')
        prior.save(path, state)
        raise


if __name__ == '__main__':
    main()
