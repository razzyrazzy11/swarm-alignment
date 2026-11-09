"""Controlled original V2 fixture race, using synthetic journals only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from experiments import test_runner as runner

V2_FIXTURE_SHA256='9a4c9979d497cf879015266109a320caae1a603ea5ee971ce7f3ea4bfaeceeca'


class V2DispatchSnapshotTests(unittest.TestCase):
    def original_reproduction(self,synchronized):
        module=importlib.import_module('experiments.tests.test_swarm_ledger_dispatch_v2')
        runner.verify_fixture(Path(__file__).resolve().parents[2],
            'experiments/tests/test_swarm_ledger_dispatch_v2.py',V2_FIXTURE_SHA256)
        case=module.DispatchCollectorTests(runner.DISPATCH_TEST)
        original=getattr(type(case),runner.DISPATCH_TEST)
        partial,requested,entered,parse_failed,release=(threading.Event() for _ in range(5))
        main_thread=threading.get_ident();actual_append=module.d.durable;actual_rows=module.s.rows
        attempts=0;parser_errors=[];captured=[]
        def append(path,value):
            nonlocal attempts
            if path.name=='capture-failures.jsonl':captured.append(value['error_class'])
            if path.name!='attempts.jsonl':return actual_append(path,value)
            attempts+=1
            if attempts!=2:return actual_append(path,value)
            text=module.s.canonical(value)+'\n';middle=len(text)//2
            with path.open('a',encoding='utf-8',newline='\n') as stream:
                stream.write(text[:middle]);stream.flush();partial.set()
                if not release.wait(5):raise RuntimeError('Controlled append release timed out')
                stream.write(text[middle:]);stream.flush();os.fsync(stream.fileno())
        def strict_rows(path):
            worker=threading.get_ident()!=main_thread and path.name=='attempts.jsonl'
            if worker:entered.set()
            try:return actual_rows(path)
            except json.JSONDecodeError:
                parser_errors.append('JSONDecodeError');parse_failed.set();raise
        def coordinator():
            try:
                self.assertTrue(partial.wait(5));self.assertTrue(requested.wait(5))
                if synchronized:self.assertFalse(entered.wait(.05),'Strict parser entered during partial append')
                else:self.assertTrue(parse_failed.wait(5),'Original worker did not reject partial JSON')
            finally:release.set()
        case.setUp()
        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(module.d,'durable',append))
                stack.enter_context(patch.object(module.s,'rows',strict_rows))
                if synchronized:stack.enter_context(runner.synchronized_fixture_journal(module))
                protected_rows=module.s.rows
                def request_snapshot(path):
                    if threading.get_ident()!=main_thread and path.name=='attempts.jsonl':
                        requested.set()
                        if not partial.wait(5):raise RuntimeError('Controlled partial append was not reached')
                    return protected_rows(path)
                stack.enter_context(patch.object(module.s,'rows',request_snapshot))
                with ThreadPoolExecutor(max_workers=1) as controller:
                    coordination=controller.submit(coordinator)
                    try:
                        if synchronized:original(case)  # Every original assertion, including 64 exactly-once calls.
                        else:
                            with self.assertRaisesRegex(ValueError,'Collector stopped on provider integrity/budget condition'):
                                original(case)
                    finally:
                        release.set();coordination.result(timeout=6)
            self.assertIs(module.d.durable,actual_append);self.assertIs(module.s.rows,actual_rows)
            if synchronized:
                self.assertEqual(parser_errors,[]);self.assertEqual(captured,[])
            else:
                self.assertIn('JSONDecodeError',parser_errors);self.assertIn('JSONDecodeError',captured)
        finally:
            release.set();case.doCleanups()

    def test_original_v2_split_append_reproduces_outer_stop_and_adapter_retains_assertions(self):
        if not __debug__:
            # Python removes the ORIGINAL snapshot expression because it is a
            # bare assert. Run this causal control in an explicitly unoptimized
            # child, while the separate original-method adapter test still runs
            # in this optimized interpreter. No test is skipped.
            program=('import sys,unittest;'
                'from experiments.tests.test_ci_dispatch_v2_snapshot import V2DispatchSnapshotTests;'
                'sys.flags.optimize==0 or sys.exit("Expected unoptimized causal-control child");'
                'r=unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite([V2DispatchSnapshotTests('
                '"test_original_v2_split_append_reproduces_outer_stop_and_adapter_retains_assertions")]));'
                'sys.exit(not r.wasSuccessful())')
            result=subprocess.run([sys.executable,'-E','-c',program],cwd=Path(__file__).resolve().parents[2],
                capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            return
        self.original_reproduction(False)
        self.original_reproduction(True)

    def test_original_v2_method_with_adapter_keeps_all_original_assertions(self):
        module=importlib.import_module('experiments.tests.test_swarm_ledger_dispatch_v2')
        case=module.DispatchCollectorTests(runner.DISPATCH_TEST)
        original=getattr(type(case),runner.DISPATCH_TEST)
        case.setUp()
        try:runner.dispatch_fixture_adapter(module,original)(case)
        finally:case.doCleanups()

    def test_dispatch_install_is_exact_pinned_v1_v2_and_restores_methods(self):
        suite=unittest.TestSuite();originals=[]
        for name,cls_name,method,_ in runner.DISPATCH_FIXTURES:
            module=importlib.import_module('experiments.tests.'+name);cls=getattr(module,cls_name)
            originals.append((cls,method,getattr(cls,method)));suite.addTest(cls(method))
        self.assertEqual(suite.countTestCases(),2)
        with ExitStack() as stack:
            runner.install_dispatch_fixtures(suite,stack,Path(__file__).resolve().parents[2])
            for cls,method,original in originals:self.assertIsNot(getattr(cls,method),original)
            result=unittest.TestResult();suite.run(result)
        self.assertEqual(result.testsRun,2);self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])
        self.assertEqual(result.skipped,[])
        for cls,method,original in originals:self.assertIs(getattr(cls,method),original)

    def test_missing_original_v2_fixture_fails_closed(self):
        name,cls_name,method,_=runner.DISPATCH_FIXTURES[0]
        module=importlib.import_module('experiments.tests.'+name)
        suite=unittest.TestSuite([getattr(module,cls_name)(method)])
        with ExitStack() as stack,self.assertRaisesRegex(RuntimeError,'dispatch snapshot fixture class'):
            runner.install_dispatch_fixtures(suite,stack,Path(__file__).resolve().parents[2])


if __name__=='__main__':unittest.main()
