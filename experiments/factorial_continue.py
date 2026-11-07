"""Separately registered, sequential HF scheduling; no calls on import or verify.

Never retries an ID. Historical 429s remain terminal INVALID observations with
their original reserved cost. The frozen scientific request and scoring code is
reused without modifying its source, configuration, or serving profile.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from experiments import factorial_study as s
from experiments.access import SameOriginRedirect

SOURCES = ('experiments/factorial_continue.py',
           'experiments/tests/test_factorial_continue.py',
           'research/FACTORIAL_RATE_CONTINUATION.md')
LIMITS = dict(min_start_interval_seconds=12, cooldown_seconds=300,
              max_total_429=5, hf_phase_cap='2')


def raw_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def retry_after(value, now=None):
    """Nonnegative finite seconds, or an RFC HTTP date; never arbitrary text."""
    number = numeric(value)
    if number is not None:
        return number
    if not isinstance(value, str):
        return None
    try:
        stamp = parsedate_to_datetime(value)
        if stamp.tzinfo is None:
            return None
        return numeric(stamp.timestamp() - (time.time() if now is None else now))
    except (TypeError, ValueError, OverflowError):
        return None


class Stopped(Exception):
    pass


class Transport:
    """One in-flight request, unchanged native transport shape and serialization.

    Scheduling/pacing happens BEFORE journaling in execute(). This lock is a
    second safeguard against accidental concurrent transport use, not a retry.
    Only numeric allowlisted rate metadata is written into the ignored sidecar.
    """
    def __init__(self, sidecar, opener=None, monotonic=None, wall=None):
        self.sidecar = Path(sidecar)
        self.opener = opener or build_opener(SameOriginRedirect())
        self.monotonic = monotonic or time.monotonic
        self.wall = wall or time.time
        self.lock = threading.Lock()
        self.delay = 0.0

    def metadata(self, headers, status):
        record = {'http_status': status}
        if headers is not None:
            delay = retry_after(headers.get('Retry-After'), self.wall())
            if delay is not None:
                record['retry_after_seconds'] = delay
            for header, field in (('RateLimit-Reset', 'ratelimit_reset'),
                                  ('X-RateLimit-Reset', 'x_ratelimit_reset')):
                value = numeric(headers.get(header))
                if value is not None:
                    record[field] = value
        # Reset fields are retained numerically, but their unspecified units are
        # NOT interpreted as a delay. Retry-After supplies the waiting contract.
        if status == 429:
            self.delay = record.get('retry_after_seconds', 0.0)
        with self.sidecar.open('a', encoding='utf-8') as file:
            s.durable(file, record)

    def __call__(self, url, key, body, timeout=120):
        if url != s.HF + '/chat/completions':
            raise ValueError('Continuation transport is HF only')
        with self.lock:
            request = Request(url, data=json.dumps(body).encode(),
                              headers={'Authorization': 'Bearer ' + key,
                                       'Content-Type': 'application/json',
                                       'User-Agent': 'swarm-alignment-pilot/0.1'},
                              method='POST')
            start = self.monotonic()
            try:
                with self.opener.open(request, timeout=timeout) as reply:
                    data = json.load(reply)
                    elapsed = round(self.monotonic() - start, 3)
                    self.metadata(reply.headers, reply.status)
                    return {'http_status': reply.status,
                            'latency_seconds': elapsed}, data
            except HTTPError as error:
                elapsed = round(self.monotonic() - start, 3)
                self.metadata(error.headers, error.code)
                return {'http_status': error.code,
                        'latency_seconds': elapsed,
                        'error': 'HTTPError'}, None
            except (URLError, TimeoutError, OSError, ValueError):
                return {'http_status': None,
                        'latency_seconds': round(self.monotonic() - start, 3),
                        'error': 'transport_or_json_error'}, None


def wait_until(deadline, stop, clock, sleep):
    while True:
        if stop.exists():
            raise Stopped()
        remaining = deadline - clock()
        if remaining <= 0:
            return
        sleep(min(remaining, 1.0))


def shuffled_plan(jobs):
    jobs = list(jobs)
    random.Random(s.config()['order_seed']).shuffle(jobs)
    ids = [job['id'] for job in jobs]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate jobs')
    return jobs, dict(freeze_sha256=s.sha(s.FREEZE), jobs_sha256=s.digest(jobs),
                      ids=ids, planned=len(jobs))


def ledger(out, jobs, plan):
    """Validate IDs/costs/body commitments; no model output is printed."""
    starts = s.rows(out / 'attempts.jsonl')
    results = s.rows(out / 'responses.jsonl')
    started = {row['id'] for row in starts}
    terminal = {row['id'] for row in results}
    if (len(started) != len(starts) or len(terminal) != len(results)
            or started != terminal or not started <= set(plan['ids'])):
        raise ValueError('Unresolved/duplicate start; never retry')
    by_id = {job['id']: job for job in jobs}
    reserves = {}
    config = s.config()
    price = {model:s.rates(model) for model in {job['model'] for job in jobs}}
    for row in starts:
        provider, body = s.body_for(by_id[row['id']])
        if row['provider'] != provider or row['request_sha256'] != s.digest(body):
            raise ValueError('Historical request body drift')
        ri, ro = price[by_id[row['id']]['model']]
        reserve = (config['input_byte_cap']*ri+config['max_output_tokens']*ro)/1000000
        if Decimal(row['reserved_cost']) != reserve:
            raise ValueError('Historical cost reservation mismatch')
        reserves[row['id']] = reserve
    for row in results:
        if row['provider'] != s.body_for(by_id[row['id']])[0]:
            raise ValueError('Historical provider mismatch')
        cost = Decimal(row['estimated_cost'])
        if not cost.is_finite() or cost < 0:
            raise ValueError('Invalid historical cost')
        if not row['known_usage'] and cost != reserves[row['id']]:
            raise ValueError('Unknown historical usage must retain full reservation')
        if row['known_usage']:
            usage = row['response']['usage']
            ri, ro = price[by_id[row['id']]['model']]
            expected = (usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000
            if cost != expected:
                raise ValueError('Historical known usage cost mismatch')
    return starts, results, started


def verify_original_sources():
    """Original source/tag checks, without the private design-context join.

    Full run verification separately calls the untouched original s.verify().
    """
    s.verify_core()
    frozen = s.read(s.FREEZE)
    config = s.config()
    if frozen['config'] != config or frozen['source_sha256'] != {
            name:s.sha(s.ROOT/name) for name in s.SOURCES}:
        raise ValueError('Frozen sources/config changed')
    for name, expected in {**frozen['source_sha256'],
                           'research/'+s.FREEZE.name:s.sha(s.FREEZE)}.items():
        blob = subprocess.check_output(['git','show',config['study_id']+':'+name], cwd=s.ROOT)
        if hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest() != expected:
            raise ValueError('Original registration tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',frozen['base_commit'],
                       config['study_id']+'^{}'], cwd=s.ROOT, capture_output=True).returncode:
        raise ValueError('Original registration ancestry')


def verify_sources(registration, tagged=True):
    """Public verification: sources/tag only; ignored live ledgers are not read."""
    verify_original_sources()
    path = Path(registration).resolve()
    if not path.is_relative_to(s.ROOT.resolve()):
        raise ValueError('Registration must be inside repository')
    registration = s.read(path)
    if registration['schema_version'] != 1 or registration['limits'] != LIMITS:
        raise ValueError('Registration schema/limits changed')
    if registration['original_freeze_sha256'] != s.sha(s.FREEZE):
        raise ValueError('Original freeze mismatch')
    if registration['source_sha256'] != {name: s.sha(s.ROOT/name) for name in SOURCES}:
        raise ValueError('Continuation sources changed')
    if Decimal(s.config()['hf_phase_cap']) != Decimal('2'):
        raise ValueError('Original HF phase cap changed')
    if tagged:
        tag = registration['registration_tag']
        relative = path.relative_to(s.ROOT.resolve()).as_posix()
        for name in (*SOURCES, relative):
            blob = subprocess.check_output(['git', 'show', tag+':'+name], cwd=s.ROOT)
            expected = (s.ROOT/name).read_bytes()
            if blob.replace(b'\r\n', b'\n') != expected.replace(b'\r\n', b'\n'):
                raise ValueError('Continuation tag mismatch')
    out = (s.ROOT/registration['output_directory']).resolve()
    if out != s.folder('audits').resolve() or not out.is_relative_to((s.ROOT/'runs').resolve()):
        raise ValueError('Must continue original ignored audit directory')
    return registration, out


def verify(registration, tagged=False, initial=True):
    """Full private starting checkpoint verification, required before dispatch."""
    s.verify()
    registration, out = verify_sources(registration, tagged=tagged)
    jobs, plan = shuffled_plan(s.audit_jobs())
    if s.read(out/'plan.json') != plan:
        raise ValueError('Changed original request plan')
    if s.digest(sorted(plan['ids'])) != registration['jobs_ids_sha256']:
        raise ValueError('Job ID grid mismatch')
    starts, results, started = ledger(out, jobs, plan)
    if initial:
        expected = registration['starting']
        actual = dict(attempts_sha256=raw_sha(out/'attempts.jsonl'),
                      responses_sha256=raw_sha(out/'responses.jsonl'),
                      attempt_count=len(starts), response_count=len(results),
                      started_ids_sha256=s.digest(sorted(started)),
                      terminal_ids_sha256=s.digest(sorted(row['id'] for row in results)),
                      plan_sha256=raw_sha(out/'plan.json'))
        if actual != expected:
            raise ValueError('Starting checkpoint mismatch')
        historical = {row['id'] for row in results if row['provider']=='hf'
                      and row['transport'].get('http_status') == 429}
        if (len(registration['historical_429_ids']) != len(set(registration['historical_429_ids']))
                or historical != set(registration['historical_429_ids'])):
            raise ValueError('Historical 429 snapshot mismatch')
    if any(s.body_for(job)[0] != 'hf' for job in jobs if job['id'] not in started):
        raise ValueError('Only HF remainder may continue')
    return registration, jobs, plan, out, results, started


@contextmanager
def exclusive_run(out):
    """No automatic stale-lock recovery: a crashed operator must investigate."""
    lock = Path(out)/'continuation.lock'
    try:
        handle = lock.open('x', encoding='ascii')
    except FileExistsError:
        raise ValueError('Continuation already active or stale lock requires review') from None
    try:
        with handle:
            handle.write('1\n')
            handle.flush()
            yield
    finally:
        lock.unlink()


def execute(registration, transport=None, clock=None, sleep=None):
    _, out = verify_sources(registration, tagged=True)
    with exclusive_run(out):
        return _execute_locked(registration, transport, clock, sleep)


def _execute_locked(registration, transport=None, clock=None, sleep=None):
    registration, jobs, plan, out, results, started = verify(registration, tagged=True)
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    stop = out/'STOP'
    transport = transport or Transport(out/'continuation-rate.jsonl')
    c = s.config()
    keys = None  # Credentials are read only after all registration/gate checks.
    historical = set(registration['historical_429_ids'])
    gateways = sum(row['transport'].get('http_status') in (502,503,504) for row in results)
    for row in results:
        exemption = (row['id'] in historical and row['provider']=='hf'
                     and row['transport'].get('http_status')==429
                     and not row['known_usage']
                     and row['transport'].get('error')=='HTTPError')
        if not exemption and s.unsafe(row, gateways, 0):
            raise ValueError('Prior non-429 fatal gate remains active')
    total429 = len(historical)
    costs = {provider: sum((Decimal(row['estimated_cost']) for row in results
                           if row['provider']==provider), Decimal(0))
             for provider in ('hf','adaption')}
    pending = [job for job in jobs if job['id'] not in started]
    halted = total429 >= LIMITS['max_total_429']
    next_start = clock() + (LIMITS['cooldown_seconds'] if historical
                            else LIMITS['min_start_interval_seconds'])
    with (out/'attempts.jsonl').open('a', encoding='utf-8') as attempts, \
            (out/'responses.jsonl').open('a', encoding='utf-8') as responses:
        while pending and not halted:
            try:
                wait_until(next_start, stop, clock, sleep)
            except Stopped:
                halted = True
                break
            job = pending[0]
            provider, body = s.body_for(job)
            if provider != 'hf':
                raise ValueError('HF-only dispatch required')
            ri, ro = s.rates(job['model'])
            reserve = (c['input_byte_cap']*ri+c['max_output_tokens']*ro)/1000000
            if costs[provider]+reserve > Decimal(c[provider+'_phase_cap']):
                halted = True
                break
            if stop.exists():
                halted = True
                break
            if keys is None:
                keys = s.credentials()
                if not keys.get('HF_TOKEN'):
                    raise ValueError('HF credential unavailable')
            start_time = clock()
            s.durable(attempts, dict(id=job['id'], request_sha256=s.digest(body),
                                    provider=provider, reserved_cost=str(reserve),
                                    started=datetime.now(timezone.utc).isoformat()))
            try:
                public, native = transport(s.HF+'/chat/completions', keys['HF_TOKEN'], body, timeout=120)
            except Exception:
                public, native = {'http_status': None, 'error': 'unexpected_request_error'}, None
            normal, known = s.safe_response(native, job['model'])
            usage = normal['usage']
            cost = (usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve
            costs[provider] += cost
            gateways += int(public.get('http_status') in (502,503,504))
            row = s.scrub(dict(id=job['id'], model=job['model'], metadata=job['metadata'],
                               provider=provider, transport=public, response=normal,
                               known_usage=known, estimated_cost=str(cost), native_response=native), keys.values())
            s.durable(responses, row)
            results.append(row)
            pending.pop(0)
            next_start = max(start_time+LIMITS['min_start_interval_seconds'], clock())
            is429 = public.get('http_status') == 429
            if is429:
                # Fresh failure is terminal. Continuing means NEXT ID, never retry.
                total429 += 1
                if (known or public.get('error') != 'HTTPError'
                        or total429 >= LIMITS['max_total_429']):
                    halted = True
                else:
                    delay = numeric(getattr(transport, 'delay', 0)) or 0
                    next_start = max(next_start, clock()+max(LIMITS['cooldown_seconds'], delay))
            elif s.unsafe(row, gateways, 0):
                halted = True
    summary = dict(planned=len(jobs), returned=len(results), complete=len(results)==len(jobs),
                   halted=halted, unstarted=len(pending), gateway_errors=gateways,
                   incomplete=sum(row['response']['status']=='incomplete' for row in results),
                   costs={provider:str(costs[provider]) for provider in ('adaption','hf')},
                   freeze_sha256=s.sha(s.FREEZE))
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify','run'))
    parser.add_argument('--registration', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        verify_sources(args.registration, tagged=True)
        result = dict(valid=True, mode='public source/tag verification; no live ledgers or calls')
    else:
        result = execute(args.registration)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
