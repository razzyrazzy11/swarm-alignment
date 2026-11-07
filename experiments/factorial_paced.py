"""Conditional final exact-unstarted continuation; no inference on import/verify."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import importlib
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import build_opener

from experiments import factorial_continue as c
from experiments import factorial_study as s
from experiments.access import SameOriginRedirect

SOURCES = ('experiments/factorial_paced.py',
           'experiments/tests/test_factorial_paced.py',
           'research/FACTORIAL_PACED_CONTINUATION.md',
           'experiments/factorial_continue.py')
LIMITS = dict(initial_start_interval_seconds=30, max_start_interval_seconds=60,
              initial_cooldown_seconds=600, rate_cooldown_seconds=600,
              max_total_429=8, hf_phase_cap='2')
CAPACITY_TAG = 'hf-capacity-v1'
CAPACITY_REPORT = 'research/hf-capacity-results.json'


def verify_capacity(registration,private=False):
    """Public replay only. A valid but failed canary does not admit collection."""
    if registration['capacity_tag'] != CAPACITY_TAG:
        raise ValueError('Unexpected capacity registration')
    path = s.ROOT/CAPACITY_REPORT
    if not path.is_file():raise ValueError('Capacity report unavailable')
    if c.raw_sha(path) != registration['capacity_results_sha256']:
        raise ValueError('Capacity report changed')
    cap = importlib.import_module('experiments.hf_capacity')
    report = cap.verify_results(private=True) if private else cap.verify_results()
    if (report.get('complete') is not True or report.get('passed') is not True
            or type(report.get('planned')) is not int or report['planned'] != 24
            or type(report.get('returned')) is not int or report['returned'] != 24
            or report.get('unstarted') != 0):
        raise ValueError('Complete successful capacity canary required')
    return report


def verify_sources(registration, tagged=True):
    c.verify_original_sources()
    path = Path(registration).resolve()
    if not path.is_relative_to(s.ROOT.resolve()):
        raise ValueError('Registration must be inside repository')
    record = s.read(path)
    expected = {'schema_version','registration_tag','original_freeze_sha256',
                'source_sha256','output_directory','starting','historical_429_ids',
                'limits','jobs_ids_sha256','capacity_results_sha256','capacity_tag'}
    # Optional creation/summary metadata is descriptive and still tag-bound.
    if set(record)-{'created','starting_summary_sha256'} != expected:
        raise ValueError('Paced registration fields changed')
    if type(record['schema_version']) is not int or record['schema_version'] != 1 or record['limits'] != LIMITS:
        raise ValueError('Paced registration schema/limits changed')
    if record['original_freeze_sha256'] != s.sha(s.FREEZE):
        raise ValueError('Original scientific freeze mismatch')
    if record['source_sha256'] != {name:s.sha(s.ROOT/name) for name in SOURCES}:
        raise ValueError('Paced continuation sources changed')
    if Decimal(s.config()['hf_phase_cap']) != Decimal('2'):
        raise ValueError('Original HF cap changed')
    if tagged:
        relative = path.relative_to(s.ROOT.resolve()).as_posix()
        for name in (*SOURCES,relative):
            blob = subprocess.check_output(['git','show',record['registration_tag']+':'+name],cwd=s.ROOT)
            if blob.replace(b'\r\n',b'\n') != (s.ROOT/name).read_bytes().replace(b'\r\n',b'\n'):
                raise ValueError('Paced continuation tag mismatch')
    out = (s.ROOT/record['output_directory']).resolve()
    if out != s.folder('audits').resolve() or not out.is_relative_to((s.ROOT/'runs').resolve()):
        raise ValueError('Original ignored audit directory required')
    if len(record['historical_429_ids']) != 5 or len(set(record['historical_429_ids'])) != 5:
        raise ValueError('Exactly five retained historical 429 identities required')
    verify_capacity(record)
    return record,out


def verify(registration, tagged=True):
    s.verify()
    record,out = verify_sources(registration,tagged=tagged)
    verify_capacity(record,private=True)
    jobs,plan = c.shuffled_plan(s.audit_jobs())
    if s.read(out/'plan.json') != plan or s.digest(sorted(plan['ids'])) != record['jobs_ids_sha256']:
        raise ValueError('Original request plan changed')
    starts,results,started = c.ledger(out,jobs,plan)
    actual = dict(attempts_sha256=c.raw_sha(out/'attempts.jsonl'),
                  responses_sha256=c.raw_sha(out/'responses.jsonl'),
                  attempt_count=len(starts),response_count=len(results),
                  started_ids_sha256=s.digest(sorted(started)),
                  terminal_ids_sha256=s.digest(sorted(row['id'] for row in results)),
                  plan_sha256=c.raw_sha(out/'plan.json'))
    if actual != record['starting'] or len(results) != 9742 or len(jobs)-len(results) != 1898:
        raise ValueError('Exact starting checkpoint changed')
    historical = {row['id'] for row in results if row['provider']=='hf'
                  and row['transport'].get('http_status')==429}
    if historical != set(record['historical_429_ids']):
        raise ValueError('Historical 429 identities changed')
    if any(s.body_for(job)[0]!='hf' for job in jobs if job['id'] not in started):
        raise ValueError('Only never-started HF requests may continue')
    return record,jobs,plan,out,results,started


class CapturingOpener:
    """Save bounded private error evidence, then preserve original transport semantics.

    Request elapsed time includes this local error capture; it is not a measure
    of provider-internal compute. No error text or headers enter public rows.
    """
    def __init__(self,folder,secrets=(),opener=None,clock=None):
        self.folder=Path(folder);self.secrets=list(secrets)
        self.opener=opener or build_opener(SameOriginRedirect())
        self.index=0;self.capture_failed=False
        self.clock=clock or time.monotonic;self.last_open_started=None
        self.retry_after_delay=0.0

    def open(self,request,timeout=120):
        try:
            self.retry_after_delay=0.0
            self.last_open_started=self.clock()
            return self.opener.open(request,timeout=timeout)
        except HTTPError as error:
            self.retry_after_delay=c.retry_after(error.headers.get('Retry-After')) if error.headers else 0.0
            try:
                raw=error.read(16384).decode('utf-8',errors='replace')
                self.folder.mkdir(parents=True,exist_ok=True)
                receipt=s.scrub(dict(http_status=error.code,response_headers=dict(error.headers or {}),
                                     error_body=raw,error_body_byte_cap=16384),self.secrets)
                with (self.folder/f'error-{self.index:03d}.json').open('x',encoding='utf-8') as file:
                    file.write(json.dumps(receipt,ensure_ascii=True,indent=2)+'\n')
                self.index+=1
            except Exception:
                # Preserve the actual HTTP failure for the durable terminal row.
                # The executor halts after recording it if private capture fails.
                self.capture_failed=True
            raise


@contextmanager
def exclusive_run(out):
    if (out/'continuation.lock').exists():
        raise ValueError('Earlier continuation lock active or stale')
    lock=out/'continuation-pacing.lock'
    try:handle=lock.open('x',encoding='ascii')
    except FileExistsError:raise ValueError('Paced continuation active or stale lock') from None
    try:
        with handle:
            handle.write('1\n');handle.flush()
            yield
    finally:lock.unlink()


def execute(registration,transport=None,clock=None,sleep=None):
    _,out=verify_sources(registration,tagged=True)
    with exclusive_run(out):
        return _execute_locked(registration,transport,clock,sleep)


def _execute_locked(registration,transport=None,clock=None,sleep=None):
    record,jobs,plan,out,results,started=verify(registration,tagged=True)
    clock=clock or time.monotonic;sleep=sleep or time.sleep
    historical=set(record['historical_429_ids']);cfg=s.config()
    gateways=sum(row['transport'].get('http_status') in (502,503,504) for row in results)
    for row in results:
        exemption=(row['id'] in historical and row['provider']=='hf'
                   and row['transport'].get('http_status')==429 and not row['known_usage']
                   and row['transport'].get('error')=='HTTPError'
                   and row.get('native_response') is None)
        if not exemption and s.unsafe(row,gateways,0):
            raise ValueError('Prior non-rate fatal gate remains active')
    costs={provider:sum((Decimal(row['estimated_cost']) for row in results
                        if row['provider']==provider),Decimal(0)) for provider in ('adaption','hf')}
    total429=len(historical);pending=[job for job in jobs if job['id'] not in started]
    halted=False;gap=LIMITS['initial_start_interval_seconds'];keys=None
    next_start=clock()+LIMITS['initial_cooldown_seconds'];stop=out/'STOP'
    with (out/'attempts.jsonl').open('a',encoding='utf-8') as attempts, \
            (out/'responses.jsonl').open('a',encoding='utf-8') as responses:
        while pending and not halted:
            try:c.wait_until(next_start,stop,clock,sleep)
            except c.Stopped:halted=True;break
            job=pending[0];provider,payload=s.body_for(job)
            if provider!='hf':raise ValueError('HF-only dispatch')
            ri,ro=s.rates(job['model'])
            reserve=(cfg['input_byte_cap']*ri+cfg['max_output_tokens']*ro)/1000000
            if costs[provider]+reserve>Decimal(cfg[provider+'_phase_cap']) or stop.exists():
                halted=True;break
            if keys is None:
                keys=s.credentials()
                if not keys.get('HF_TOKEN'):raise ValueError('HF credential unavailable')
                if transport is None:
                    opener=CapturingOpener(out/'paced-private-errors',keys.values(),clock=clock)
                    transport=c.Transport(out/'paced-rate.jsonl',opener=opener)
            s.durable(attempts,dict(id=job['id'],request_sha256=s.digest(payload),provider=provider,
                                    reserved_cost=str(reserve),started=datetime.now(timezone.utc).isoformat()))
            try:public,native=transport(s.HF+'/chat/completions',keys['HF_TOKEN'],payload,timeout=120)
            except Exception:public,native={'http_status':None,'error':'unexpected_request_error'},None
            normal,known=s.safe_response(native,job['model']);usage=normal['usage']
            cost=(usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve
            costs[provider]+=cost;gateways+=int(public.get('http_status') in (502,503,504))
            row=s.scrub(dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,
                             transport=public,response=normal,known_usage=known,
                             estimated_cost=str(cost),native_response=native),keys.values())
            s.durable(responses,row);results.append(row);pending.pop(0)
            # Anchor to the actual client opener call, not the time before a
            # potentially slow durable start or request construction. Injected
            # transports without that trace use a conservative post-response gap.
            opened=c.numeric(getattr(getattr(transport,'opener',None),'last_open_started',None))
            base=clock() if opened is None else opened
            next_start=max(base+gap,clock())
            if public.get('http_status')==429:
                total429+=1
                if (known or native is not None or public.get('error')!='HTTPError'
                        or total429>=LIMITS['max_total_429']):
                    halted=True
                else:
                    gap=LIMITS['max_start_interval_seconds']
                    cooldown=LIMITS['rate_cooldown_seconds']*(2**(total429-6))
                    delay=c.numeric(getattr(transport,'delay',0)) or 0
                    next_start=max(base+gap,clock()+max(cooldown,delay))
            elif s.unsafe(row,gateways,0):halted=True
            elif public.get('http_status') in (502,503,504):
                delay=c.numeric(getattr(getattr(transport,'opener',None),'retry_after_delay',0)) or 0
                next_start=max(next_start,clock()+delay)
            if getattr(getattr(transport,'opener',None),'capture_failed',False):halted=True
    summary=dict(planned=len(jobs),returned=len(results),complete=len(results)==len(jobs),halted=halted,
                 unstarted=len(pending),gateway_errors=gateways,
                 incomplete=sum(row['response']['status']=='incomplete' for row in results),
                 costs={provider:str(costs[provider]) for provider in ('adaption','hf')},freeze_sha256=s.sha(s.FREEZE))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('verify','run'));parser.add_argument('--registration',required=True)
    args=parser.parse_args()
    if args.command=='verify':
        verify_sources(args.registration,tagged=True)
        result=dict(valid=True,mode='public sources/tags/capacity replay only; no private main ledgers')
    else:result=execute(args.registration)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
