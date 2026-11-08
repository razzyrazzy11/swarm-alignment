"""Force the overlap that made the historical synthetic fixture flaky."""
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from experiments.test_runner import ScriptedTransport


class FixtureAmendmentTests(unittest.TestCase):
    def test_exactly_one_failure_even_when_both_calls_start_before_return(self):
        barrier = threading.Barrier(2)
        transport = ScriptedTransport(lambda body: {'status': 'completed'}, True,
                                      lambda: barrier.wait(timeout=5))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(transport, {}, 'synthetic', False, 180) for _ in range(2)]
            results = [future.result() for future in futures]
        self.assertCountEqual([r[0]['http_status'] for r in results], [504, 200])
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(transport.active, [0, 2])
        failed = next(r for r in results if r[0]['http_status'] == 504)
        self.assertIsNone(failed[1])
        self.assertEqual(failed[2]['headers']['Retry-After'], '2')
