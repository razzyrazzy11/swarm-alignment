"""Post-primary pilot queue and owned-child watchdog; no primary restarts."""
from datetime import datetime,timezone
from pathlib import Path
import ctypes,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
JOB=ROOT/'runs/adaption-serving-pilot-driver'
CUTOFF=datetime.fromisoformat('2026-11-09T09:30:00+00:00').timestamp()
def drain_with_deadline(child,hard_stop,monotonic_stop=None):
    """Metadata failures must not disable the owned pilot's hard watchdog."""
    remaining=max(0,hard_stop-time.time())
    if monotonic_stop is not None:remaining=min(remaining,max(0,monotonic_stop-time.monotonic()))
    try:return False,child.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        child.kill();return True,child.wait()
def save(state):
    state['updated']=datetime.now(timezone.utc).isoformat();path=JOB/'state.json';temp=path.with_suffix('.tmp')
    for n in range(40):
        try:
            with temp.open('w',encoding='utf-8') as f:json.dump(state,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
            os.replace(temp,path);return
        except PermissionError:
            if n==39:raise
            time.sleep(.25)
def main():
    JOB.mkdir(parents=True,exist_ok=True)
    if (JOB/'state.json').exists():raise ValueError('Existing pilot supervisor; never restart blindly')
    sys.path.insert(0,str(ROOT));from experiments import adaption_serving_pilot as pilot
    pilot.verify()
    state=dict(status='waiting_primary',pid=os.getpid(),child_pid=None,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inference_attempted=False)
    save(state);child=None
    try:
        while True:
            if time.time()+2700>=CUTOFF:
                state.update(status='deferred',reason='Primary-first policy leaves insufficient pilot time',inference_attempted=False);save(state);return
            ready=True
            for name in pilot.DRIVERS:
                path=ROOT/name
                if not path.exists():ready=False;continue
                actual=json.loads(path.read_text())
                if actual['status']=='stopped':
                    state.update(status='blocked',reason='Primary collection or verification stopped; pilot remains unrun');save(state);return
                if actual['status']!='complete':ready=False
            if ready:
                # Creation-aware actual process checks; no invented state or PIDs.
                try:pilot.primary_complete();break
                except ValueError:pass
            save(state);time.sleep(30)
        state.update(status='running',stage='pilot',inference_attempted=True);save(state)
        hard_stop=min(time.time()+2700,CUTOFF)
        monotonic_stop=time.monotonic()+max(0,hard_stop-time.time())
        state['watchdog_deadline_utc']=datetime.fromtimestamp(hard_stop,timezone.utc).isoformat();save(state)
        command=[sys.executable,'-m','experiments.adaption_serving_pilot','run']
        with (JOB/'pilot.stdout.log').open('xb') as out,(JOB/'pilot.stderr.log').open('xb') as err:
            child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            state['child_pid']=child.pid;state['pilot_child_pid']=child.pid;save(state);deadline=monotonic_stop
            while child.poll() is None and time.monotonic()<deadline and time.time()<CUTOFF:
                time.sleep(min(5,max(.01,deadline-time.monotonic())));save(state)
            if child.poll() is None:
                # Kill ONLY the owned child handle. Durable attempt reservations
                # remain unknown; no terminal is fabricated and nothing is resent.
                child.kill();child.wait();state.update(status='stopped',reason='watchdog_timeout',exit_code=child.returncode);save(state)
            else:
                state.update(status='collected' if child.returncode==0 else 'stopped',exit_code=child.returncode)
                if child.returncode:state['reason']='child_failed'
                else:
                    summary_path=ROOT/'runs/adaption-serving-pilot-v1/summary.json'
                    summary=json.loads(summary_path.read_text())
                    state['pilot_complete']=summary.get('complete') is True
                    if not state['pilot_complete']:state.update(status='partial',reason='pilot_incomplete')
                save(state)
            child=None
        # Export explicit partial/complete operational outcomes, never primary data.
        if state.get('exit_code')==0:state['status']='processing'
        state.update(stage='analysis');save(state)
        with (JOB/'analysis.stdout.log').open('xb') as out,(JOB/'analysis.stderr.log').open('xb') as err:
            child=subprocess.Popen([sys.executable,'-m','experiments.adaption_serving_pilot','analyze'],cwd=ROOT,stdout=out,stderr=err)
            state['analysis_child_pid']=child.pid;save(state);code=child.wait();child=None
        if code:raise ValueError('Pilot operational analysis failed; preserve records')
        state.update(status='complete' if state.get('pilot_complete') is True else 'partial' if state.get('exit_code')==0 else 'stopped',stage='finished',analysis_complete=True);save(state)
    except BaseException as error:
        if child is not None:
            if state.get('stage')=='pilot':
                killed,code=drain_with_deadline(child,hard_stop,monotonic_stop)
                state['exit_code']=code
                if killed:state['reason']='watchdog_timeout'
            else:child.wait()
        state.update(status='stopped',error_class=type(error).__name__);state.setdefault('reason','supervisor_failure');save(state);raise
if __name__=='__main__':
    lease=None
    if os.name=='nt':
        from ctypes import wintypes
        lease=ctypes.WinDLL('kernel32',use_last_error=True);lease.SetThreadExecutionState.argtypes=[wintypes.DWORD];lease.SetThreadExecutionState.restype=wintypes.DWORD
        if not lease.SetThreadExecutionState(0x80000001):raise RuntimeError('Idle sleep lease unavailable')
    try:main()
    finally:
        if lease:lease.SetThreadExecutionState(0x80000000)
