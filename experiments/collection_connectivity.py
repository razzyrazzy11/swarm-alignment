"""Prospective connectivity gates and credential-safe, single-attempt transport.

This module never loads credentials, creates inference requests, or calls a
provider at import. Callers own registered endpoints, serialization, journals,
reservations, Retry-After policy, and model/output validation.
"""
from datetime import datetime, timezone, timedelta
import hashlib
from http.client import HTTPException, IncompleteRead
import json
import math
import re
import ssl
import threading
import time
from urllib.error import HTTPError, URLError

DEADLINE = '2026-11-09T05:59:00+00:00'
STAGES = ('open', 'read', 'size_check', 'json_decode', 'complete')


class ConnectivityUnavailable(ValueError):
    """Bounded connectivity wait or registered collection cutoff reached."""


def _epoch(value):
    if isinstance(value, str):
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Aware collection deadline required')
        value = stamp.timestamp()
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Finite collection deadline required')
    return value


def blackout_end(epoch):
    """Return reset-window end for 04:55 <= UTC time < 05:05, else None."""
    stamp = datetime.fromtimestamp(epoch, timezone.utc)
    start = stamp.replace(hour=4, minute=55, second=0, microsecond=0)
    end = stamp.replace(hour=5, minute=5, second=0, microsecond=0)
    return end.timestamp() if start <= stamp < end else None


class ConnectivityGate:
    """Gate new dispatch only; never retry an already attempted inference.

    probe must perform only a bounded authenticated, allowlisted catalog GET and
    return a literal bool. False means connectivity unavailable. Exceptions
    propagate, so authentication/model/catalog validation errors are not silently
    converted into outage waits. Callers must drain existing futures before a
    recovery wait and retain all failed terminals and unknown-cost reservations.
    """
    def __init__(self, probe, *, clock=time.time, sleep=time.sleep,
                 deadline=DEADLINE, pause_seconds=900):
        if not callable(probe) or not 15 <= pause_seconds <= 900:
            raise ValueError('Bounded catalog probe and pause required')
        self.probe, self.clock, self.sleep = probe, clock, sleep
        self.deadline, self.pause_seconds = _epoch(deadline), float(pause_seconds)
        self.needs_health = True
        self.verified_at = None
        self.lock = threading.RLock()

    def _refresh_reset(self, now):
        stamp = datetime.fromtimestamp(now, timezone.utc)
        reset = stamp.replace(hour=5, minute=0, second=0, microsecond=0)
        if stamp < reset:
            reset -= timedelta(days=1)
        if self.verified_at is not None and (now < self.verified_at or self.verified_at < reset.timestamp() <= now):
            self.needs_health = True

    def connection_failed(self):
        with self.lock:
            self.needs_health = True

    def dispatch_allowed(self):
        """Fast metadata-only check; it never probes or sleeps."""
        with self.lock:
            now = self.clock()
            self._refresh_reset(now)
            reset = blackout_end(now)
            if reset is not None:
                self.needs_health = True
            return now < self.deadline and reset is None and not self.needs_health

    def before_dispatch(self, force_health=False):
        with self.lock:
            if force_health:
                self.needs_health = True
            started, slept, probes, consecutive = self.clock(), 0., 0, 0
            last_good = None
            while True:
                now = self.clock()
                self._refresh_reset(now)
                elapsed = max(0., now-started, slept)
                if now >= self.deadline:
                    raise ConnectivityUnavailable('Registered collection cutoff reached')
                if elapsed >= self.pause_seconds:
                    raise ConnectivityUnavailable('Bounded connectivity pause exhausted')
                reset = blackout_end(now)
                if reset is not None:
                    self.needs_health = True
                    consecutive, last_good = 0, None
                    delay = min(15., reset-now)
                elif not self.needs_health:
                    return dict(ready=True, probes=probes, waited_seconds=round(elapsed, 3))
                else:
                    healthy = self.probe()
                    probes += 1
                    if type(healthy) is not bool:
                        raise ValueError('Catalog probe must return a literal bool')
                    now = self.clock()
                    if now >= self.deadline or max(now-started, slept) >= self.pause_seconds:
                        raise ConnectivityUnavailable('Connectivity probe exceeded wait or cutoff')
                    if blackout_end(now) is not None:
                        consecutive, last_good = 0, None
                        continue
                    if healthy:
                        if last_good is not None and now-last_good >= 15:
                            consecutive += 1
                        else:
                            consecutive = 1
                        last_good = now
                        if consecutive >= 2:
                            self.needs_health = False
                            self.verified_at = now
                            return dict(ready=True, probes=probes,
                                        waited_seconds=round(max(0., now-started, slept), 3))
                    else:
                        consecutive, last_good = 0, None
                    delay = 15.
                budget = min(self.pause_seconds-max(0., self.clock()-started, slept),
                             self.deadline-self.clock())
                delay = min(delay, budget)
                if delay <= 0:
                    raise ConnectivityUnavailable('No remaining connectivity wait budget')
                self.sleep(delay)
                slept += delay


def _safe_headers(headers):
    """Only nonsecret numeric/date/MIME fields; never full provider headers."""
    result = {}
    if headers is None:
        return result
    for name in ('Content-Length', 'RateLimit-Reset', 'X-RateLimit-Reset'):
        value = str(headers.get(name, ''))
        if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value) and len(value) <= 32:
            result[name] = value
    mime = str(headers.get('Content-Type', '')).split(';', 1)[0].strip().lower()
    if re.fullmatch(r'[a-z0-9.+-]+/[a-z0-9.+-]+', mime) and len(mime) <= 100:
        result['Content-Type'] = mime
    value = str(headers.get('Retry-After', '')).strip()
    if len(value) <= 128:
        if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
            result['Retry-After'] = value
        else:
            from email.utils import parsedate_to_datetime, format_datetime
            try:
                stamp = parsedate_to_datetime(value)
                if stamp.tzinfo is not None:
                    result['Retry-After'] = format_datetime(stamp.astimezone(timezone.utc), usegmt=True)
            except (ValueError, TypeError, OverflowError):
                pass
    return result


def _exception_fields(error):
    """Do not stringify exceptions: messages can contain URLs or credentials."""
    result = {'exception_class': type(error).__name__}
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, BaseException):
        result['reason_class'] = type(reason).__name__
    for name in ('errno', 'winerror'):
        value = getattr(reason, name, None)
        if type(value) is int:
            result[name] = value
    return result


def _connection_error(error, stage):
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, ssl.SSLError):
        return False
    return stage in ('open', 'read') and isinstance(error, (URLError, OSError, TimeoutError, IncompleteRead))


def safe_request(opener, request, *, timeout, max_bytes=2097152,
                 monotonic=time.monotonic, wall=time.time):
    """Execute exactly one HTTP request, never retry it.

    Returns (public_status, native_json_or_None, private_receipt). Successful
    JSON and bounded HTTP error text are private values for existing normalizers
    and overload classifiers. Callers scrub and durably capture those receipts;
    they must not publish them. Public diagnostics contain no response fragments,
    URLs, request IDs, exception messages, or credential-bearing headers.
    """
    if not 1 <= max_bytes <= 2097152 or not 0 < timeout <= 180:
        raise ValueError('Registered bounded response size and timeout required')
    started, started_wall = monotonic(), wall()
    stage, native, raw = 'open', None, None
    status = {'http_status': None, 'connection_fault': False}
    private, headers, diagnostic = {}, {}, {}
    try:
        with opener.open(request, timeout=timeout) as reply:
            status['http_status'] = reply.status  # Preserve status BEFORE read/decode.
            headers = _safe_headers(reply.headers)
            stage = 'read'
            raw = reply.read(max_bytes+1)
            stage = 'size_check'
            if len(raw) > max_bytes:
                raise ValueError('Native body cap')
            stage = 'json_decode'
            native = json.loads(raw)
            private = {'native_response': native, 'headers': headers}
            stage = 'complete'
    except HTTPError as error:
        status.update(http_status=error.code, error='HTTPError')
        headers = _safe_headers(error.headers)
        try:
            stage = 'read'
            raw = error.read(16384)
            private = {'headers': headers, 'error_body': raw.decode('utf-8', errors='replace')}
            stage = 'complete'
        except (URLError, OSError, TimeoutError, ValueError, HTTPException) as capture:
            status['capture_failed'] = True
            diagnostic.update(_exception_fields(capture))
    except (URLError, OSError, TimeoutError, ValueError, HTTPException) as error:
        status['error'] = ('connection_error' if _connection_error(error, stage)
                           else 'response_validation_error')
        status['connection_fault'] = _connection_error(error, stage)
        diagnostic.update(_exception_fields(error))
        if isinstance(error, IncompleteRead) and isinstance(error.partial, bytes):
            raw = error.partial[:max_bytes+1]
    diagnostic.update(stage=stage, started_utc=datetime.fromtimestamp(started_wall, timezone.utc).isoformat(),
                      finished_utc=datetime.fromtimestamp(wall(), timezone.utc).isoformat())
    if raw is not None:
        diagnostic.update(body_bytes=len(raw), body_sha256=hashlib.sha256(raw).hexdigest())
    if 'Content-Type' in headers:
        diagnostic['content_type'] = headers['Content-Type']
    if 'Content-Length' in headers:
        diagnostic['content_length'] = int(headers['Content-Length']) if headers['Content-Length'].isdigit() else headers['Content-Length']
    status.update(latency_seconds=round(monotonic()-started, 3), diagnostics=diagnostic)
    return status, native, private
