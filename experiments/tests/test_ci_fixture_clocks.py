"""Explicit scenario clocks for frozen synthetic tests; no provider calls."""
from contextlib import ExitStack
from datetime import datetime
import importlib
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from experiments import test_runner as runner


def selected_suite():
    suite=unittest.TestSuite()
    for name,class_name,methods,_,_ in runner.CLOCK_FIXTURES:
        module=importlib.import_module('experiments.tests.'+name)
        cls=getattr(module,class_name)
        suite.addTests(cls(method) for method in methods)
    return suite


class FixtureClockTests(unittest.TestCase):
    def test_metadata_proxy_is_local_nested_patches_override_and_restore(self):
        module=SimpleNamespace(r=SimpleNamespace(time=time))
        actual=time.time
        def original(case):
            case.assertIs(time.time,actual)
            case.assertIsNot(module.r.time,time)
            case.assertEqual(module.r.time.time(),runner.FIXTURE_EPOCH)
            with patch.object(module.r.time,'time',return_value=runner.FIXTURE_EPOCH+100):
                case.assertEqual(module.r.time.time(),runner.FIXTURE_EPOCH+100)
            case.assertEqual(module.r.time.time(),runner.FIXTURE_EPOCH)
            raise RuntimeError('synthetic failure')
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            runner.clock_fixture_adapter(module,original,'metadata')(self)
        self.assertIs(module.r.time,time);self.assertIs(time.time,actual)

    def test_forecast_only_generated_at_is_pinned_and_restored(self):
        actual=lambda:'actual scenario marker'
        module=SimpleNamespace(f=SimpleNamespace(s=SimpleNamespace(now=actual)))
        def original(case):
            case.assertEqual(module.f.s.now(),runner.FIXTURE_UTC)
            raise RuntimeError('synthetic failure')
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            runner.clock_fixture_adapter(module,original,'forecast')(self)
        self.assertIs(module.f.s.now,actual)

    def test_all_eight_original_methods_pass_with_all_assertions(self):
        suite=selected_suite();self.assertEqual(suite.countTestCases(),8)
        # Keep each distinct method, not merely the final method of each class.
        methods=[(type(case),case._testMethodName,getattr(type(case),case._testMethodName))
                 for case in runner.cases(suite)]
        with ExitStack() as stack:
            runner.install_clock_fixtures(suite,stack,Path(__file__).resolve().parents[2])
            result=unittest.TestResult();suite.run(result)
        self.assertEqual(result.testsRun,8)
        self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])
        self.assertEqual(result.skipped,[])
        for cls,name,original in methods:self.assertIs(getattr(cls,name),original)

    def test_real_cutoff_guard_still_blocks_before_any_request(self):
        module=importlib.import_module('experiments.swarm_ledger_resume_v3')
        cutoff=datetime.fromisoformat(module.policy['cutoff_utc']).timestamp()
        clock=SimpleNamespace(time=lambda:cutoff+1,monotonic=time.monotonic,sleep=time.sleep)
        with tempfile.TemporaryDirectory() as directory:
            transport=module.ResumeTransport({},Path(directory),object())
            with patch.object(module,'time',clock),patch.object(module.connectivity,'safe_request') as request:
                with self.assertRaisesRegex(ValueError,'cutoff'):
                    transport.metadata('https://router.huggingface.co/v1/models')
                request.assert_not_called()

    def test_missing_named_fixture_fails_closed(self):
        suite=selected_suite()
        incomplete=unittest.TestSuite(list(runner.cases(suite))[:-1])
        with ExitStack() as stack,self.assertRaises(RuntimeError):
            runner.install_clock_fixtures(incomplete,stack,Path(__file__).resolve().parents[2])


if __name__=='__main__':unittest.main()
