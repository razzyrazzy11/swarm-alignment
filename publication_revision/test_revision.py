"""Synthetic boundary checks; no experimental replay or provider requests."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from publication_revision import admission as a, artifacts as p, verify as v


def row(raw):
    return dict(sha256=v.sha(raw), bytes=len(raw))


class ChangePolicyTests(unittest.TestCase):
    def check(self, path, before, after, category):
        a.validate_changes({path: row(before)}, {path: row(after)}, {path: category},
                           lambda name: after, lambda *args: True)

    def test_data_and_production_code_changes_rejected_even_if_declared(self):
        for path in ('data/toy.jsonl', 'experiments/scorer.py', 'paper/verify.py',
                     'public_snapshot_v3/snapshot_math.py'):
            with self.subTest(path=path), self.assertRaises(v.RevisionError):
                self.check(path, b'old', b'new', 'metadata')

    def test_only_explicit_document_changes_are_admitted(self):
        self.check('README.md', b'Old synthetic prose.', b'New synthetic prose.', 'editorial')
        with self.assertRaises(v.RevisionError):
            self.check('README.md', b'old', b'new', 'artifact')
        with self.assertRaises(v.RevisionError):
            a.validate_changes({'README.md': row(b'same')}, {'README.md': row(b'same')},
                               {'README.md': 'editorial'}, lambda name: b'same', lambda *args: True)

    def test_missing_parent_file_and_unknown_change_category_rejected(self):
        with self.assertRaises(v.RevisionError):
            a.validate_changes({'README.md': row(b'x')}, {}, {}, lambda name: b'', lambda *args: True)
        with self.assertRaises(v.RevisionError):
            self.check('README.md', b'old', b'new', 'unchecked')

    def test_fixture_checksum_checker_is_mandatory(self):
        def reject(*args):
            raise v.RevisionError('Synthetic assertion edit')
        before = {a.CHECKSUM_TEST: row(b'old'), a.FIXTURE_MANIFEST: row(b'manifest')}
        after = dict(before, **{a.CHECKSUM_TEST: row(b'new')})
        with self.assertRaises(v.RevisionError):
            a.validate_changes(before, after, {a.CHECKSUM_TEST: 'metadata'},
                               lambda name: b'new' if name == a.CHECKSUM_TEST else b'manifest', reject)

    def test_preserved_fixture_guard_rejects_added_assertion(self):
        from public_snapshot_v3.admission import verify_fixture_checksum_bytes
        root = Path(__file__).resolve().parents[1]
        raw = (root / a.CHECKSUM_TEST).read_bytes()
        lines = raw.splitlines(keepends=True)
        manifest = b'{"synthetic_manifest":true}\n'
        lines[19] = re.sub(rb'[0-9a-f]{64}', v.sha(manifest).encode(), lines[19])
        source = b''.join(lines)
        self.assertTrue(verify_fixture_checksum_bytes(source, manifest))
        with self.assertRaises(ValueError):
            verify_fixture_checksum_bytes(source + b'\nassert False\n', manifest)

    def test_json_invariant_preserves_numbers_and_masks_only_digest_values(self):
        self.assertEqual(a.json_invariant({'x': 'a' * 64, 'n': 17}),
                         a.json_invariant({'x': 'b' * 64, 'n': 17}))
        self.assertNotEqual(a.json_invariant({'n': 17}), a.json_invariant({'n': 18}))
        self.assertNotEqual(a.json_invariant({'n': False}), a.json_invariant({'n': 0}))
        self.assertNotEqual(a.json_invariant({'text': 'old'}), a.json_invariant({'text': 'new'}))

    def test_fixed_provenance_records_reject_numeric_and_source_path_changes(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('research/paper-public-figure-input.json',
                     'paper/figures/swarm-ledger-complete-v1/ledger_figures_provenance.json'):
            value = json.loads((root / name).read_bytes())
            self.assertEqual(a.json_invariant(value), a.METADATA[name])
            numeric = deepcopy(value)
            numeric['schema_version'] = 2
            paths = deepcopy(value)
            sources = paths['scientific_sources']
            key = next(iter(sources))
            sources['research/unreviewed-source.md'] = sources.pop(key)
            for changed in (numeric, paths):
                with self.subTest(path=name), self.assertRaises(v.RevisionError):
                    self.check(name, b'previous metadata', json.dumps(changed).encode(), 'metadata')

    def test_authoring_ast_allows_only_draft_text_and_one_cardinality_slot(self):
        def source(word, cardinality, other=17, outside='fixed'):
            return (f'OTHER = {other}\nLABEL = {outside!r}\n'
                    f'def draft(basis):\n    """{word}"""\n'
                    f'    if len(basis["references"]) != {cardinality}:\n'
                    '        raise ValueError("display label")\n    return basis\n').encode()
        baseline = a.authoring_ast(source('old', 31), 31)
        self.assertEqual(baseline, a.authoring_ast(source('new', 30), 30))
        self.assertNotEqual(baseline, a.authoring_ast(source('new', 30, other=18), 30))
        self.assertNotEqual(baseline, a.authoring_ast(source('new', 30, outside='changed'), 30))
        with self.assertRaises(v.RevisionError):
            a.authoring_ast(source('new', 29), 30)

    def test_reviewed_raw_authoring_pin_blocks_operational_string_change(self):
        root = Path(__file__).resolve().parents[1]
        reviewed = (root / a.AUTHORING).read_bytes()
        self.assertEqual(v.sha(reviewed), a.AUTHORING_RAW_SHA256)
        self.assertIn(b"'schema_version'", reviewed)
        changed = reviewed.replace(b"'schema_version'", b"'other_key'", 1)
        self.assertEqual(a.authoring_ast(reviewed, 30), a.authoring_ast(changed, 30))
        with self.assertRaises(v.RevisionError):
            self.check(a.AUTHORING, b'previous source', changed, 'editorial')


class BootstrapTests(unittest.TestCase):
    def manifest(self, root, *, extra=False):
        raw = b'Synthetic source.'
        (root / 'safe.txt').write_bytes(raw)
        (root / 'publication_revision').mkdir()
        value = dict(schema_version=1, kind=v.SCOPE, parent_manifest_sha256=v.PARENT_MANIFEST_SHA256,
                     files={'safe.txt': row(raw)}, changes={}, qa_path=v.QA)
        data = json.dumps(value).encode()
        (root / v.MANIFEST).write_bytes(data)
        if extra:
            (root / 'unexpected.txt').write_bytes(b'Synthetic extra.')
        return v.sha(data)

    def test_external_pin_missing_or_wrong_fails_before_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.manifest(root)
            for pin in ('', None, '0' * 64):
                with self.subTest(pin_type=type(pin).__name__), self.assertRaises(v.RevisionError):
                    v.preflight(root, pin)

    def test_extra_file_and_false_parent_cannot_pass_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pin = self.manifest(root, extra=True)
            with self.assertRaisesRegex(v.RevisionError, 'inventory'):
                v.preflight(root, pin)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.manifest(root)
            parent = root / 'public_snapshot_v3'
            parent.mkdir()
            for name in ('disclosure-manifest.json', 'admission.json', 'verify.py'):
                (parent / name).write_bytes(b'{}')
            manifest = json.loads((root / v.MANIFEST).read_bytes())
            for path in parent.iterdir():
                manifest['files'][path.relative_to(root).as_posix()] = row(path.read_bytes())
            raw = json.dumps(manifest).encode()
            (root / v.MANIFEST).write_bytes(raw)
            with self.assertRaisesRegex(v.RevisionError, 'parent authority'):
                v.preflight(root, v.sha(raw))

    def test_malformed_and_aliased_inputs_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{}{}'):
            with self.assertRaises(v.RevisionError):
                v.strict_json(raw)
        for path in ('../outside', '.git/x', 'x/__pycache__/x', 'x/NUL.txt', 'x./y', 'x\\y'):
            with self.assertRaises(v.RevisionError):
                v.relative(path)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'nested/.git').mkdir(parents=True)
            with self.assertRaises(v.RevisionError):
                v.actual_files(root)

    def test_safe_failure_never_includes_raw_exception_text(self):
        secret = 'fabricated-sensitive-error-canary'
        try:
            raise RuntimeError(secret)
        except RuntimeError as exc:
            result = v.safe_failure(exc, 'synthetic')
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(result['error_type'], 'RuntimeError')

    def test_report_is_exclusive_and_outside_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp); root = parent / 'snapshot'; root.mkdir()
            target = parent / 'result.json'
            v.write_result(target, {'valid': True}, root)
            with self.assertRaises(v.RevisionError):
                v.write_result(target, {'valid': False}, root)
            with self.assertRaises(v.RevisionError):
                v.write_result(root / 'result.json', {}, root)

    def test_cli_mode_conflict_is_safe_metadata_only(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(Path(v.__file__)),
                                 '--expected-manifest-sha256', '0' * 64,
                                 '--tests-only', '--preflight-only'], capture_output=True)
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout)
        self.assertFalse(value['valid'])
        self.assertEqual(value['stage'], 'preflight')
        self.assertNotIn('Traceback', result.stderr.decode())

    def test_cli_unknown_argument_never_echoes_its_value(self):
        canary = 'fabricated-argument-canary'
        result = subprocess.run([sys.executable, '-I', '-B', str(Path(v.__file__)),
                                 '--expected-manifest-sha256', '0' * 64,
                                 '--unrecognized', canary], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(canary.encode(), result.stdout + result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['stage'], 'arguments')
        self.assertFalse(value['valid'])

    def test_preserved_offline_hook_blocks_network_writes_and_replay_subprocess(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            script = ('import pathlib,sys,socket,subprocess\n'
                      f'sys.path.insert(0,{str(root)!r})\n'
                      'from public_snapshot_v3.verify import offline_read_only\n'
                      f'r=pathlib.Path({temp!r});offline_read_only(r)\n'
                      'blocked=0\n'
                      'for action in (lambda:(r/"new.txt").write_text("toy"),'
                      'lambda:socket.socket().connect(("127.0.0.1",9)),'
                      'lambda:subprocess.run([sys.executable,"-c","pass"])):\n'
                      ' try: action()\n'
                      ' except ValueError: blocked+=1\n'
                      'assert blocked==3\n')
            outcome = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual(outcome.returncode, 0, 'Synthetic offline guard failed')
            self.assertFalse((Path(temp) / 'new.txt').exists())

    def test_owned_outside_view_cleans_up_with_preserved_root_hook(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            script = ('import pathlib,sys,os\n'
                      f'sys.path.insert(0,{str(root)!r})\n'
                      'from public_snapshot_v3.verify import offline_read_only\n'
                      'from publication_revision.verify import outside_working_directory\n'
                      f'r=pathlib.Path({temp!r});os.chdir(r);offline_read_only(r)\n'
                      'with outside_working_directory(r) as owned:\n'
                      ' (owned/"synthetic.txt").write_text("toy")\n'
                      ' saved=owned\n'
                      'assert not saved.exists() and pathlib.Path.cwd()==r\n')
            outcome = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual(outcome.returncode, 0, 'Owned outside view failed')


class FreshQaTests(unittest.TestCase):
    def fixture(self):
        paths = p.EDITIONS['current']
        return dict(content=paths[0], content_sha256='a' * 64, docx=paths[1], docx_sha256='b' * 64,
                    pdf=paths[2], pdf_sha256='c' * 64, builder_sha256='d' * 64,
                    export_engine='Microsoft Word', export_source_unchanged=True,
                    export_owned_instance_verified=True, pages=2, main_pages=1, abstract_words=196,
                    rendered_page_sha256=['e' * 64, 'f' * 64], visual_review=dict(
                        complete=True, reviewer='synthetic reviewer', reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                        inspected_pages=[1, 2]))

    def test_fresh_complete_qa_shape_is_required(self):
        p.validate_qa_record(self.fixture(), p.EDITIONS['current'])
        for change in ('incomplete', 'missing_page', 'duplicate_page', 'unowned', 'wrong_path', 'old_shape'):
            record = self.fixture()
            if change == 'incomplete': record['visual_review']['complete'] = False
            elif change == 'missing_page': record['visual_review']['inspected_pages'] = [1]
            elif change == 'duplicate_page': record['visual_review']['inspected_pages'] = [1, 1]
            elif change == 'unowned': record['export_owned_instance_verified'] = False
            elif change == 'wrong_path': record['pdf'] = 'paper/out/other.pdf'
            else: record['carried_forward'] = True
            with self.subTest(change=change), self.assertRaises(v.RevisionError):
                p.validate_qa_record(record, p.EDITIONS['current'])


if __name__ == '__main__':
    unittest.main()
