"""Synthetic split-append reproduction; never uses a real journal or provider."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from experiments import test_runner as runner


class DispatchSnapshotAmendmentTests(unittest.TestCase):
    def reproduce(self, synchronized):
        partial, release, entered, attempted = (threading.Event() for _ in range(4))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'attempts.jsonl'
            def durable(path,value):
                text=json.dumps(value)+'\n';middle=len(text)//2
                with path.open('w',encoding='utf-8') as output:
                    output.write(text[:middle]);output.flush();partial.set()
                    if not release.wait(3):raise RuntimeError('Synthetic writer was not released')
                    output.write(text[middle:]);output.flush()
            def rows(path):
                entered.set()
                return [json.loads(line) for line in path.read_text().splitlines()]
            module=SimpleNamespace(d=SimpleNamespace(durable=durable),s=SimpleNamespace(rows=rows))
            def read():
                attempted.set()
                return module.s.rows(path)
            def exercise():
                with ThreadPoolExecutor(max_workers=2) as pool:
                    writer=pool.submit(module.d.durable,path,{'id':'synthetic'})
                    self.assertTrue(partial.wait(3))
                    reader=pool.submit(read)
                    self.assertTrue(attempted.wait(3))
                    try:
                        if synchronized:
                            self.assertFalse(entered.wait(.05),'Parser entered during an unfinished append')
                            release.set();writer.result(timeout=3)
                            self.assertEqual(reader.result(timeout=3),[{'id':'synthetic'}])
                        else:
                            self.assertTrue(entered.wait(3))
                            with self.assertRaises(json.JSONDecodeError):reader.result(timeout=3)
                    finally:
                        release.set()
                        writer.result(timeout=3)
            if synchronized:
                with runner.synchronized_fixture_journal(module):exercise()
            else:exercise()

    def test_unadapted_strict_reader_rejects_concurrent_partial_append(self):
        self.reproduce(False)

    def test_adapter_waits_for_complete_append_without_weakening_parser(self):
        self.reproduce(True)

    def test_both_wrappers_restore_and_errors_are_not_swallowed(self):
        def append(*args):raise OSError('synthetic disk failure')
        def rows(*args):raise json.JSONDecodeError('synthetic malformed record','x',0)
        module=SimpleNamespace(d=SimpleNamespace(durable=append),s=SimpleNamespace(rows=rows))
        with self.assertRaisesRegex(RuntimeError,'synthetic test failure'):
            with runner.synchronized_fixture_journal(module):
                with self.assertRaises(OSError):module.d.durable(None,None)
                with self.assertRaises(json.JSONDecodeError):module.s.rows(None)
                raise RuntimeError('synthetic test failure')
        self.assertIs(module.d.durable,append);self.assertIs(module.s.rows,rows)

    def test_fixture_hash_pin_rejects_changed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.py';path.write_bytes(b'original\r\n')
            expected=hashlib.sha256(b'original\n').hexdigest()
            runner.verify_fixture(directory,'fixture.py',expected)
            path.write_bytes(b'changed\n')
            with self.assertRaises(RuntimeError):runner.verify_fixture(directory,'fixture.py',expected)

    def test_original_frozen_dispatch_method_retains_all_assertions(self):
        module=importlib.import_module('experiments.tests.test_swarm_ledger_dispatch')
        case=module.DispatchCollectorTests(runner.DISPATCH_TEST)
        original=getattr(module.DispatchCollectorTests,runner.DISPATCH_TEST)
        try:
            runner.dispatch_fixture_adapter(module,original)(case)
        finally:
            case.doCleanups()


if __name__=='__main__':unittest.main()
