"""Synthetic checks of the standard-library-only launcher preflight."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('_snapshot_launcher_tests', HERE / 'verify.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


def fixture(root):
    path = root / 'public_snapshot_v2'
    path.mkdir()
    raw = b'# synthetic launcher\n'
    (path / 'verify.py').write_bytes(raw)
    manifest = dict(kind=v.SCOPE, files={
        'public_snapshot_v2/verify.py': dict(sha256=v.sha(raw), bytes=len(raw), role='generated')})
    encoded = json.dumps(manifest).encode()
    (root / v.MANIFEST).write_bytes(encoded)
    (root / v.RECEIPT).write_bytes(b'{}')
    return v.sha(encoded)


class LauncherTests(unittest.TestCase):
    def test_preflight_accepts_only_externally_pinned_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            digest = fixture(root)
            self.assertEqual(v.preflight(root, digest)['kind'], v.SCOPE)
            with self.assertRaisesRegex(ValueError, 'External manifest pin'):
                v.preflight(root, '0' * 64)
            (root / 'extra.txt').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError, 'extra'):
                v.preflight(root, digest)

    def test_byte_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            digest = fixture(root)
            (root / 'public_snapshot_v2/verify.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Disclosed file differs'):
                v.preflight(root, digest)

    def test_case_alias_inventory_fails_before_filesystem_lookup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            manifest = json.loads((root / v.MANIFEST).read_bytes())
            name = 'public_snapshot_v2/verify.py'
            manifest['files'][name.upper()] = dict(manifest['files'][name])
            raw = json.dumps(manifest).encode()
            (root / v.MANIFEST).write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'Case-aliased'):
                v.preflight(root, v.sha(raw))

    def test_caches_and_nested_git_are_never_hidden(self):
        for name in ('nested/.git/secret', '__pycache__/secret', 'nested/cache.pyc', '.git'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                digest = fixture(root)
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'synthetic')
                with self.assertRaises(ValueError):
                    v.preflight(root, digest)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            digest = fixture(root)
            (root / '.git').mkdir()
            (root / '.git/HEAD').write_text('ref: refs/heads/master', encoding='ascii')
            v.preflight(root, digest)

    def test_path_and_json_ambiguities_fail_closed(self):
        for name in ('../outside', '/absolute', 'a//b', 'a\\b', 'C:secret', 'a/./b',
                     'CON', 'dir/NUL.txt', 'dir/trailing.', 'dir/trailing '):
            with self.subTest(name=name), self.assertRaises(ValueError):
                v.safe_relative(name)
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'\xff'):
            with self.assertRaises(ValueError):
                v.strict_json(raw)

    def test_failure_report_omits_message_and_input(self):
        marker = 'private synthetic input'
        try:
            raise ValueError(marker)
        except ValueError as exc:
            report = v.safe_failure(exc, 'synthetic')
        self.assertNotIn(marker, json.dumps(report))
        self.assertFalse(report['valid'])

    def test_result_cannot_overwrite_snapshot_or_existing_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'snapshot'
            root.mkdir()
            with self.assertRaises(ValueError):
                v.write_result(root / 'result.json', {}, root)
            target = Path(temp) / 'result.json'
            v.write_result(target, {'valid': True}, root)
            with self.assertRaises(ValueError):
                v.write_result(target, {}, root)

    def test_preflight_cli_never_imports_project_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'public_snapshot_v2'
            path.mkdir()
            launcher = (HERE / 'verify.py').read_bytes()
            (path / 'verify.py').write_bytes(launcher)
            poison = b'raise RuntimeError("project import occurred before preflight")\n'
            (path / '__init__.py').write_bytes(poison)
            files = {('public_snapshot_v2/' + name): dict(sha256=v.sha(raw), bytes=len(raw), role='generated')
                     for name, raw in [('verify.py', launcher), ('__init__.py', poison)]}
            manifest = json.dumps(dict(kind=v.SCOPE, files=files)).encode()
            (root / v.MANIFEST).write_bytes(manifest)
            (root / v.RECEIPT).write_bytes(b'{}')
            command = [sys.executable, '-I', '-B']
            if sys.flags.optimize:
                command.append('-O')
            command += [str(path / 'verify.py'), '--preflight-only',
                        '--expected-manifest-sha256', v.sha(manifest)]
            result = subprocess.run(command, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout.decode('utf-8'))
            self.assertTrue(json.loads(result.stdout)['preflight_valid'])
            self.assertFalse((path / '__pycache__').exists())

    def test_read_only_audit_hook_blocks_mutation_and_network(self):
        with tempfile.TemporaryDirectory() as temp:
            script = '''import importlib.util, pathlib, socket, sys
spec=importlib.util.spec_from_file_location('trusted', sys.argv[1])
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
root=pathlib.Path(sys.argv[2]).resolve(); m.offline_read_only(root)
attempts=[lambda: (root/'forbidden').write_bytes(b'x'),lambda: socket.getaddrinfo('example.com',443)]
for attempt in attempts:
    try: attempt()
    except m.LaunchError: continue
    raise RuntimeError('audit hook failed')
'''
            command = [sys.executable, '-I', '-B', '-c', script, str(HERE / 'verify.py'), temp]
            result = subprocess.run(command, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
