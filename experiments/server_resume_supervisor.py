"""One-shot v2 collection and independent offline waiter; never restart a request."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('hf_export','main_export','continuation_provenance','figure_input',
          'figures','figure_provenance','generator_sensitivity')


def save(path, value):
    value['updated'] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix('.tmp')
    for attempt in range(40):
        try:
            with temporary.open('w', encoding='utf-8') as stream:
                json.dump(value, stream, indent=2); stream.write('\n')
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path); return
        except PermissionError:
            if attempt == 39: raise
            time.sleep(.25)


def child_run(folder, state, path, stage, command):
    with (folder/(stage+'.stdout.log')).open('xb') as output, (folder/(stage+'.stderr.log')).open('xb') as error:
        child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=error,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        # Keep the owned child and its reservations intact even if interrupted.
        try:
            state.update(stage=stage, child_pid=child.pid); save(path,state)
            code = child.wait()
        except BaseException:
            child.wait(); raise
    state['child_pid'] = None
    if code:
        state.update(status='stopped', reason='phase_failed_no_retry', exit_code=code)
        save(path,state); raise ValueError('Owned phase failed; no automatic restart')


def collect(folder, state, path):
    for phase in ('readers','calibration','influence'):
        child_run(folder,state,path,phase,[sys.executable,'-m','experiments.swarm_ledger_resume_v2','run','--phase',phase])
        summary = json.loads((folder/(phase+'.stdout.log')).read_text(encoding='utf-8'))
        if summary.get('complete') is not True: raise ValueError('Registered union phase incomplete')
        state.update(summary=summary,last_completed_stage=phase); save(path,state)


def processing_jobs():
    public='data/swarm-ledger-v1-public'
    receipt='runs/server-resume-postprocess-driver/verified-public-input.json'
    figures='paper/figures/swarm-ledger-complete-v1'
    return [
        ('hf_export',[sys.executable,'-m','experiments.server_resume_analysis','export-hf']),
        ('main_export',[sys.executable,'-m','experiments.server_resume_analysis','export-main','--output',public]),
        ('continuation_provenance',[sys.executable,'-m','experiments.server_resume_analysis','verify-main','--output',public]),
        ('figure_input',[sys.executable,'-m','analysis.ledger_complete_figures','verify-input','--public',public,'--receipt',receipt]),
        ('figures',['C:/Python314/python.exe','-m','analysis.ledger_complete_figures','generate','--public',public,'--receipt',receipt,'--output',figures]),
        ('figure_provenance',[sys.executable,'-m','analysis.ledger_complete_figures','verify-only','--public',public,'--receipt',receipt,'--output',figures]),
        ('generator_sensitivity',[sys.executable,'-m','analysis.ledger_generator_sensitivity','export','--input',public,'--output','data/swarm-ledger-generator-sensitivity-v1'])]


def postprocess(folder, state, path):
    from experiments import server_resume_analysis as release
    complete_seen=None
    while True:
        actual=ROOT/'runs/swarm-ledger-resume-v2-driver/state.json'
        if actual.exists():
            current=json.loads(actual.read_text(encoding='utf-8'))
            if current['status']=='stopped':raise ValueError('Actual v2 collector stopped incomplete')
            if current['status']=='complete':
                # A durable complete state precedes actual supervisor exit.
                # Wait briefly for real termination, without fabricating proof.
                complete_seen=time.monotonic() if complete_seen is None else complete_seen
                try:
                    release.drivers('main');release.drivers('hf');release.no_collectors();break
                except ValueError:
                    if time.monotonic()-complete_seen>120:raise
        save(path,state);time.sleep(30)
    for stage,command in processing_jobs():
        state['status']='processing'
        child_run(folder,state,path,stage,command)
        state['completed_stages'].append(stage);save(path,state)
    state.update(paper_authored=False,visual_qa_complete=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=('collect','postprocess'))
    args=parser.parse_args()
    from experiments import server_resume_analysis as release
    from experiments import swarm_ledger_resume_v2 as resume
    release.verify();resume.verify()
    name='swarm-ledger-resume-v2-driver' if args.kind=='collect' else 'server-resume-postprocess-driver'
    folder=ROOT/'runs'/name;folder.mkdir(parents=True,exist_ok=True);path=folder/'state.json'
    if path.exists():raise ValueError('Actual supervisor state already exists; never restart blindly')
    state=dict(status='running' if args.kind=='collect' else 'waiting_collection',
        pid=os.getpid(),child_pid=None,completed_stages=[],kind=args.kind,
        supervisor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save(path,state)
    try:
        (collect if args.kind=='collect' else postprocess)(folder,state,path)
        state.update(status='complete',exit_code=0,child_pid=None);save(path,state)
    except BaseException as error:
        state.update(status='stopped',error_class=type(error).__name__)
        state.setdefault('reason','supervisor_or_admission_failure');save(path,state);raise


if __name__=='__main__':
    lease=None
    if os.name=='nt':
        from ctypes import wintypes
        lease=ctypes.WinDLL('kernel32',use_last_error=True)
        lease.SetThreadExecutionState.argtypes=[wintypes.DWORD]
        lease.SetThreadExecutionState.restype=wintypes.DWORD
        if not lease.SetThreadExecutionState(0x80000001):raise RuntimeError('Idle sleep lease unavailable')
    try:main()
    finally:
        if lease:lease.SetThreadExecutionState(0x80000000)
