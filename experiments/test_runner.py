"""Run all experiment tests with the disclosed, frozen-fixture race correction.

Only synthetic PilotTests.run_fixture is adapted; collector code is untouched.
See research/CI_FIXTURE_AMENDMENT.md. No credentials or inference are used.
"""
import hashlib
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

FIXTURE_SHA256 = '58340e8ed2b58e34af88ae611377a61960f19e9769ff605b6ce1d3fdb909ac8d'


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


def main():
    import sys
    root = Path(__file__).resolve().parents[1]
    path = root / 'experiments/tests/test_adaption_serving_pilot.py'
    actual = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    if actual != FIXTURE_SHA256:
        raise RuntimeError('Frozen fixture changed; compatibility amendment needs review')
    suite = unittest.defaultTestLoader.discover(str(root / 'experiments/tests'))
    matches = {type(case) for case in cases(suite)
               if type(case).__module__ == 'test_adaption_serving_pilot'
               and type(case).__name__ == 'PilotTests'}
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one original pilot test class')
    cls = matches.pop()
    module = sys.modules[cls.__module__]
    print('CI fixture amendment: deterministic synthetic call ordinal; all discovered tests retained.', flush=True)
    with patch.object(cls, 'run_fixture', fixture_adapter(module)):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
