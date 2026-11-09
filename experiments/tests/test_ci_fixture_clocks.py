"""Explicit scenario clocks for frozen synthetic tests; no provider calls."""
from contextlib import ExitStack
from datetime import datetime, timezone, timedelta
import importlib
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
from concurrent.futures import wait as real_wait
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

    def test_all_named_original_methods_pass_with_all_assertions(self):
        suite=selected_suite();self.assertEqual(suite.countTestCases(),34)
        # Keep each distinct method, not merely the final method of each class.
        methods=[(type(case),case._testMethodName,getattr(type(case),case._testMethodName))
                 for case in runner.cases(suite)]
        with ExitStack() as stack:
            runner.install_clock_fixtures(suite,stack,Path(__file__).resolve().parents[2])
            result=unittest.TestResult();suite.run(result)
        self.assertEqual(result.testsRun,34)
        self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])
        self.assertEqual(result.skipped,[])
        for cls,name,original in methods:self.assertIs(getattr(cls,name),original)

    def test_execution_datetime_is_local_nested_patch_overrides_and_restores(self):
        module=SimpleNamespace(r=SimpleNamespace(datetime=datetime))
        actual=datetime
        class ExplicitDatetime(datetime):
            @classmethod
            def now(cls,tz=None):return datetime.fromtimestamp(runner.FIXTURE_EPOCH+100,tz)
        def original(case):
            case.assertIs(datetime,actual)
            case.assertIsNot(module.r.datetime,actual)
            case.assertEqual(module.r.datetime.now(timezone.utc).timestamp(),runner.FIXTURE_EPOCH)
            case.assertEqual(module.r.datetime.fromisoformat(runner.FIXTURE_UTC),datetime.fromisoformat(runner.FIXTURE_UTC))
            with patch.object(module.r,'datetime',ExplicitDatetime):
                case.assertEqual(module.r.datetime.now(timezone.utc).timestamp(),runner.FIXTURE_EPOCH+100)
            case.assertEqual(module.r.datetime.now(timezone.utc).timestamp(),runner.FIXTURE_EPOCH)
            raise RuntimeError('synthetic failure')
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            runner.clock_fixture_adapter(module,original,'execution')(self)
        self.assertIs(module.r.datetime,actual)

    def test_rate_and_paced_real_cutoffs_remain_active_inside_scenario_adapter(self):
        for name in ('swarm_ledger_rate','swarm_ledger_paced'):
            module=importlib.import_module('experiments.'+name)
            fixture=SimpleNamespace(r=module)
            cutoff=datetime.fromisoformat(module.policy['cutoff_utc'])
            actual=module.datetime
            def original(case):
                # A fixed ambient scenario does not relax an explicitly late
                # admission, and a nested future clock overrides the fixture.
                with case.assertRaisesRegex(ValueError,'last dispatch'):
                    module.dispatch_time_gate(at=cutoff)
                class LateDatetime(datetime):
                    @classmethod
                    def now(cls,tz=None):return cutoff+timedelta(seconds=1)
                with patch.object(module,'datetime',LateDatetime):
                    with case.assertRaisesRegex(ValueError,'last dispatch'):module.dispatch_time_gate()
            with self.subTest(module=name):
                runner.clock_fixture_adapter(fixture,original,'execution')(self)
                self.assertIs(module.datetime,actual)

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

    def test_scripted_success_first_reproduces_original_recovery_assumption(self):
        module=importlib.import_module('experiments.tests.test_swarm_ledger_paced')
        cls=module.UnionTests;name=runner.CONNECTION_ORDER_FIXTURE[2]
        original=getattr(cls,name);case=cls(name)
        observed=[]
        def success_first(futures,*args,**kwargs):
            if isinstance(futures,dict):
                preferred=next((future for ident in ('new-good','new-later','new-connection')
                    for future,job in futures.items() if job['id']==ident),None)
                if preferred is not None:
                    completed,_=real_wait((preferred,),*args,**kwargs)
                    observed.extend(futures[f]['id'] for f in completed)
                    return completed,set(futures)-set(completed)
            return real_wait(futures,*args,**kwargs)
        case.setUp()
        try:
            with patch.object(module.r,'wait',success_first),self.assertRaisesRegex(AssertionError,'1 not greater than or equal to 2'):
                runner.clock_fixture_adapter(module,original,'execution')(case)
        finally:
            case.tearDown();case.doCleanups()
        self.assertEqual(observed,['new-good','new-later','new-connection'])

        # The adapter changes only observation order and retains ALL original
        # assertions even when the underlying fake wait prefers successes.
        for nested in (False,True):
            case=cls(name);observed.clear();case.setUp();actual=module.r.wait
            method=runner.connection_fixture_adapter(module,original)
            if nested:method=runner.connection_fixture_adapter(module,method)
            try:
                with patch.object(module.r,'wait',success_first):
                    runner.clock_fixture_adapter(module,method,'execution')(case)
            finally:
                case.tearDown();case.doCleanups()
            self.assertIs(module.r.wait,actual)

    def test_connection_observation_alias_restores_after_failure(self):
        def actual(*args,**kwargs):raise RuntimeError('synthetic wait failure')
        module=SimpleNamespace(r=SimpleNamespace(wait=actual))
        future=object()
        def original(case):module.r.wait({future:{'id':'new-connection'}})
        with self.assertRaisesRegex(RuntimeError,'synthetic wait failure'):
            runner.connection_fixture_adapter(module,original)(self)
        self.assertIs(module.r.wait,actual)

    def test_connection_observation_preserves_wait_arguments_and_remaining_futures(self):
        failed,other=object(),object();mode=object();calls=[]
        def actual(futures,*args,**kwargs):
            calls.append((tuple(futures),args,kwargs));return {failed},set()
        module=SimpleNamespace(r=SimpleNamespace(wait=actual))
        def original(case):
            completed,remaining=module.r.wait({failed:{'id':'new-connection'},other:{'id':'new-good'}},
                                            timeout=.25,return_when=mode)
            case.assertEqual(completed,{failed});case.assertEqual(remaining,{other})
        runner.connection_fixture_adapter(module,original)(self)
        self.assertEqual(calls,[((failed,),(),{'timeout':.25,'return_when':mode})])
        self.assertIs(module.r.wait,actual)

    def test_connection_order_adapter_is_selected_only_for_exact_pinned_method(self):
        suite=selected_suite();actual=runner.connection_fixture_adapter
        with ExitStack() as stack,patch.object(runner,'connection_fixture_adapter',wraps=actual) as selected:
            runner.install_clock_fixtures(suite,stack,Path(__file__).resolve().parents[2])
            selected.assert_called_once()
            module,original=selected.call_args.args
            self.assertEqual(module.__name__.rsplit('.',1)[-1],runner.CONNECTION_ORDER_FIXTURE[0])
            self.assertEqual(original.__name__,runner.CONNECTION_ORDER_FIXTURE[2])

    def test_pilot_datetime_is_local_and_nested_late_calendar_still_stops_dispatch(self):
        module=importlib.import_module('experiments.tests.test_adaption_serving_pilot')
        actual=module.p.datetime;global_datetime=datetime
        cutoff=datetime.fromisoformat(module.p.POLICY['cutoff_utc'])
        class LateDatetime(datetime):
            @classmethod
            def now(cls,tz=None):return cutoff+timedelta(seconds=1)
        def original(case):
            case.assertIs(datetime,global_datetime)
            case.assertIsNot(module.p.datetime,actual)
            case.assertEqual(module.p.datetime.now(timezone.utc).timestamp(),runner.FIXTURE_EPOCH)
            case.assertFalse(module.p.fits_window(cutoff))
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'runs'/module.p.TAG).mkdir(parents=True)
                freeze=root/'freeze.json';freeze.write_text('{}')
                clock=module.Clock();gate=module.Gate();calls=[]
                def forbidden(*args,**kwargs):calls.append(1);raise AssertionError('Late scenario cannot dispatch')
                with patch.object(module.p,'ROOT',root),patch.object(module.p,'FREEZE',freeze),\
                     patch.object(module.p,'datetime',LateDatetime):
                    result=module.p._run(module.p.plan(),'synthetic',forbidden,gate,clock,clock.sleep)
                case.assertEqual(calls,[]);case.assertEqual(result['started'],0)
                case.assertEqual(result['stop_reason'],'pilot_cutoff')
            case.assertEqual(module.p.datetime.now(timezone.utc).timestamp(),runner.FIXTURE_EPOCH)
            raise RuntimeError('synthetic failure')
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            runner.clock_fixture_adapter(module,original,'pilot')(self)
        self.assertIs(module.p.datetime,actual);self.assertIs(datetime,global_datetime)

    def test_pilot_clock_inventory_excludes_real_run_watchdog_and_explicit_cutoff_tests(self):
        entry=next(entry for entry in runner.CLOCK_FIXTURES if entry[0]=='test_adaption_serving_pilot')
        self.assertEqual(len(entry[2]),6);self.assertEqual(entry[3],'pilot');self.assertEqual(entry[4],runner.FIXTURE_SHA256)
        for name in ('test_run_refuses_before_primary_without_loading_credentials',
                     'test_watchdog_state_requires_actual_parent_child','test_secondary_cutoff_has_full45minute_reserve',
                     'test_primary_and_postprocess_must_be_complete_real_states'):
            self.assertNotIn(name,entry[2])


if __name__=='__main__':unittest.main()
