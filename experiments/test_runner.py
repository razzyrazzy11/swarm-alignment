"""Run all experiment tests with the disclosed, frozen-fixture race correction.

Only named synthetic fixtures are adapted; collector code is untouched.
See research/CI_FIXTURE_AMENDMENT.md. No credentials or inference are used.
"""
import hashlib
from contextlib import contextmanager, ExitStack
from datetime import datetime
from functools import wraps
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

FIXTURE_SHA256 = '58340e8ed2b58e34af88ae611377a61960f19e9769ff605b6ce1d3fdb909ac8d'
DISPATCH_FIXTURE_SHA256 = '32ac534ceecf2ffe2cfc0abff882b64f6419a6f326ec28072400fb3b8fd3683e'
DISPATCH_TEST = 'test_pilot_preserves_reservation_and_does_not_gate_json_accuracy'
FIXTURE_UTC = '2026-11-08T00:00:00+00:00'
FIXTURE_EPOCH = datetime.fromisoformat(FIXTURE_UTC).timestamp()
METADATA_CLOCK_METHODS = (
    'test_metadata_transient_read_only_backoff_then_success',
    'test_metadata_funding_fails_without_sleep_or_retry',
    'test_late_metadata_success_is_not_admission')
EXECUTION_CLOCK_METHODS = (
    'test_connection_failure_is_retained_once_and_only_unstarted_continue',
    'test_unclassified_parse_failure_stops_without_resending',
    'test_http503_capture_failure_is_fatal_even_when_capacity_class_matches',
    'test_500_recovery_never_reissues_and_rechecks_health',
    'test_500_known_usage_is_fatal_even_without_anomaly_flag',
    'test_500_pauses_unstarted_until_new_health_cycle',
    'test_provider_cap_stops_before_any_send')
CONNECTION_ORDER_FIXTURE=('test_swarm_ledger_paced','UnionTests',
    'test_connection_failure_is_retained_once_and_only_unstarted_continue')
CLOCK_FIXTURES = (
    ('test_swarm_ledger_efficient', 'AvailabilityTests', METADATA_CLOCK_METHODS, 'metadata',
     '2386d634f34b250e8c16a948b3982a8eecbea5cb85a2c680d4f099275eed1201'),
    ('test_swarm_ledger_resume_v3', 'AvailabilityTests', METADATA_CLOCK_METHODS, 'metadata',
     '7df6af71199cad5c5b6dec06791b3a32a383e18056dcf2de82ed50265fa8bce2'),
    ('test_swarm_ledger_forecast', 'WalletIntegrationTests',
     ('test_one_shared_cache_check_not_one_get_per_candidate',), 'forecast',
     '20e9fd0443df2718c8a0e8c47ee38fb21f31ef502457aca65dab5b12ef8ae3e1'),
    ('test_swarm_ledger_forecast_v2', 'WalletIntegrationTests',
     ('test_one_shared_cache_check_not_one_get_per_candidate',), 'forecast',
     '4efbdffc5e383f4612ba6f9ab1e8c1ae0b784de8ae14d492af9e3e825e6668a5'),
    ('test_swarm_ledger_rate', 'AvailabilityTests', METADATA_CLOCK_METHODS, 'metadata',
     '7594d160b120e5a60994b414190bad1b45ad34b16021dc277994bf4c7415f692'),
    ('test_swarm_ledger_paced', 'AvailabilityTests', METADATA_CLOCK_METHODS, 'metadata',
     '6e7b820fd140814ef45135b01e39e23c32d2db967f5a8d16cf600cf11871c4c5'),
    ('test_swarm_ledger_rate', 'UnionTests', EXECUTION_CLOCK_METHODS, 'execution',
     '7594d160b120e5a60994b414190bad1b45ad34b16021dc277994bf4c7415f692'),
    ('test_swarm_ledger_paced', 'UnionTests', EXECUTION_CLOCK_METHODS, 'execution',
     '6e7b820fd140814ef45135b01e39e23c32d2db967f5a8d16cf600cf11871c4c5'))


class ScriptedTransport:
    """Capture an immutable call ordinal before allowing concurrent overlap."""
    def __init__(self, native, error=False, pause=None):
        self.native = native
        self.error = error
        self.pause = pause or (lambda: time.sleep(.001))
        self.calls = []
        self.active = [0, 0]
        self.lock = threading.Lock()

    def __call__(self, body, key, stream, timeout):
        with self.lock:
            self.active[0] += 1
            self.active[1] = max(self.active[1], self.active[0])
            self.calls.append((body, stream, timeout))
            ordinal = len(self.calls)
        try:
            self.pause()
            if self.error and ordinal == 1:
                return (dict(http_status=504, error='HTTPError', latency_seconds=60),
                        None, dict(error_body='Gateway time-out', headers={'Retry-After': '2'}))
            native = self.native(body)
            return (dict(http_status=200, latency_seconds=2), native,
                    dict(native_response=native, headers={}))
        finally:
            with self.lock:
                self.active[0] -= 1


def fixture_adapter(module):
    def run_fixture(case, error=False):
        temp = tempfile.TemporaryDirectory()
        case.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / 'runs' / module.p.TAG).mkdir(parents=True)
        freeze = root / 'freeze.json'
        freeze.write_text('{}')
        clock, gate = module.Clock(), module.Gate()
        request = ScriptedTransport(module.native, error)
        with patch.object(module.p, 'ROOT', root), patch.object(module.p, 'FREEZE', freeze):
            summary = module.p._run(module.p.plan(), 'privatekey', request, gate, clock, clock.sleep)
        return root, summary, request.calls, request.active, gate
    return run_fixture


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


@contextmanager
def synchronized_fixture_journal(module):
    """Serialize only a fake worker's snapshot with that fixture's appends.

    The original test method and strict journal parser remain unchanged. This
    context is never installed in a real collector or outside that one test.
    """
    lock = threading.RLock()
    durable, rows = module.d.durable, module.s.rows
    @wraps(durable)
    def append(*args, **kwargs):
        with lock:
            return durable(*args, **kwargs)
    @wraps(rows)
    def snapshot(*args, **kwargs):
        with lock:
            return rows(*args, **kwargs)
    with patch.object(module.d, 'durable', append), patch.object(module.s, 'rows', snapshot):
        yield


def dispatch_fixture_adapter(module, original):
    @wraps(original)
    def run(case):
        with synchronized_fixture_journal(module):
            return original(case)
    return run


def verify_fixture(root, relative, expected):
    path = Path(root) / relative
    actual = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    if actual != expected:
        raise RuntimeError('Frozen fixture changed; compatibility amendment needs review: '+relative)


def clock_fixture_adapter(module, original, kind):
    """Pin only a synthetic scenario's ambient clock, never its cutoff policy.

    Explicit patches inside the original tests remain innermost and override
    this baseline. Metadata uses a module-local proxy, not the global time
    module. Forecasts receive only a fixed generated-at string; wallet cache
    freshness continues using the original real-clock comparisons. Execution
    scenarios replace only the owning module's datetime class with a subclass
    overriding now(); explicit at arguments and nested patches still win.
    """
    if kind not in ('metadata', 'forecast', 'execution'):
        raise ValueError('Unknown synthetic clock fixture kind')
    @wraps(original)
    def run(case):
        if kind == 'metadata':
            actual = module.r.time
            clock = SimpleNamespace(time=lambda: FIXTURE_EPOCH,
                monotonic=actual.monotonic, sleep=actual.sleep)
            with patch.object(module.r, 'time', clock):
                return original(case)
        if kind == 'execution':
            actual = module.r.datetime
            class ScenarioDatetime(actual):
                @classmethod
                def now(cls, tz=None):
                    return actual.fromtimestamp(FIXTURE_EPOCH, tz)
            with patch.object(module.r, 'datetime', ScenarioDatetime):
                return original(case)
        with patch.object(module.f.s, 'now', return_value=FIXTURE_UTC):
            return original(case)
    return run


def connection_fixture_adapter(module,original):
    """Observe the scripted connection failure before other fake completions.

    The unchanged fixture's recovery assertion assumes never-started work is
    still pending when that failure is observed. Futures still execute under
    the original caps; this controls only the test's observation order. Every
    returned completion comes from the original wait, with no fabricated rows,
    health calls or future state, and the module-local alias is restored.
    """
    @wraps(original)
    def run(case):
        actual=module.r.wait
        def observe_failure_first(futures,*args,**kwargs):
            if isinstance(futures,dict):
                failed=[future for future,job in futures.items() if job['id']=='new-connection']
                if failed:
                    if len(failed)!=1:raise RuntimeError('Expected one scripted connection failure')
                    completed,_=actual((failed[0],),*args,**kwargs)
                    return completed,set(futures)-set(completed)
            return actual(futures,*args,**kwargs)
        with patch.object(module.r,'wait',observe_failure_first):return original(case)
    return run


def install_clock_fixtures(suite, stack, root):
    """Fail closed on fixture identity, class inventory and named test methods."""
    import sys
    for name, class_name, methods, kind, expected in CLOCK_FIXTURES:
        verify_fixture(root, 'experiments/tests/'+name+'.py', expected)
        matches = {type(case) for case in cases(suite)
                   if type(case).__module__.rsplit('.',1)[-1] == name
                   and type(case).__name__ == class_name}
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one clock fixture class: '+name)
        cls = matches.pop()
        module = sys.modules[cls.__module__]
        selected = {case._testMethodName for case in cases(suite) if type(case) is cls}
        if not set(methods) <= selected:
            raise RuntimeError('Expected all named clock fixture methods: '+name+'.'+class_name)
        for method in methods:
            original = getattr(cls, method)
            if (name,class_name,method)==CONNECTION_ORDER_FIXTURE:
                original=connection_fixture_adapter(module,original)
            stack.enter_context(patch.object(cls, method,
                clock_fixture_adapter(module, original, kind)))


def main():
    import sys
    root = Path(__file__).resolve().parents[1]
    verify_fixture(root, 'experiments/tests/test_adaption_serving_pilot.py', FIXTURE_SHA256)
    verify_fixture(root, 'experiments/tests/test_swarm_ledger_dispatch.py', DISPATCH_FIXTURE_SHA256)
    suite = unittest.defaultTestLoader.discover(str(root / 'experiments/tests'))
    matches = {type(case) for case in cases(suite)
               if type(case).__module__ == 'test_adaption_serving_pilot'
               and type(case).__name__ == 'PilotTests'}
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one original pilot test class')
    cls = matches.pop()
    module = sys.modules[cls.__module__]
    dispatch_matches = {type(case) for case in cases(suite)
                        if type(case).__module__ == 'test_swarm_ledger_dispatch'
                        and type(case).__name__ == 'DispatchCollectorTests'}
    if len(dispatch_matches) != 1:
        raise RuntimeError('Expected exactly one original dispatch test class')
    dispatch_cls = dispatch_matches.pop()
    dispatch_module = sys.modules[dispatch_cls.__module__]
    original = getattr(dispatch_cls, DISPATCH_TEST)
    clock_count=sum(len(methods) for _,_,methods,_,_ in CLOCK_FIXTURES)
    print('CI fixture amendments: deterministic synthetic call ordinal, test-only atomic journal snapshot, and '+str(clock_count)+' explicit scenario clocks; all discovered tests retained.', flush=True)
    with ExitStack() as stack:
        stack.enter_context(patch.object(cls, 'run_fixture', fixture_adapter(module)))
        stack.enter_context(patch.object(dispatch_cls, DISPATCH_TEST,
            dispatch_fixture_adapter(dispatch_module, original)))
        install_clock_fixtures(suite, stack, root)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
