"""Toy repositories and synthetic byte maps only; never a project export."""
from copy import deepcopy
import ast
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
PACKAGE = '_snapshot_export_test_package'
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(HERE)]
    sys.modules[PACKAGE] = package
m = importlib.import_module(PACKAGE + '.export_snapshot')


class ToyGitTests(unittest.TestCase):
    def git(self, repo, *args):
        result = subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Synthetic',
                                 '-c', 'user.email=synthetic@example.invalid',
                                 '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false',
                                 *args], capture_output=True)
        self.assertEqual(result.returncode, 0, 'Synthetic Git fixture command failed')
        return result.stdout.decode('utf-8').strip()

    def fixture(self, *, pushed=True, annotated=False, extra=False, changed_tag_code=False,
                mutate_freeze=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        repo = root / 'source'; repo.mkdir()
        self.git(repo, 'init')
        self.git(repo, 'config', 'core.autocrlf', 'false')
        self.git(repo, 'symbolic-ref', 'HEAD', 'refs/heads/master')
        (repo / 'README.md').write_bytes(b'Synthetic canonical input.\n')
        self.git(repo, 'add', 'README.md'); self.git(repo, 'commit', '-m', 'Synthetic canonical input')
        canonical = self.git(repo, 'rev-parse', 'HEAD')
        tree = self.git(repo, 'rev-parse', 'HEAD^{tree}')
        sources = {
            m.PACKAGE + 'export_snapshot.py': b'# synthetic issuer\n',
            m.LAUNCHER: b'# synthetic launcher\n',
            m.PROTOCOL_PATH: b'Synthetic disclosure protocol.\n',
        }
        for name, raw in sources.items():
            path = repo / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        if extra:
            (repo / m.PACKAGE / 'unreviewed.py').write_bytes(b'# synthetic unexpected code\n')
        self.git(repo, 'add', '.'); self.git(repo, 'commit', '-m', 'Synthetic prospective code')
        code = self.git(repo, 'rev-parse', 'HEAD')
        hashes = {name: m.sha(raw) for name, raw in sources.items()}
        freeze = dict(schema_version=1, tag=m.TAG, canonical_commit=canonical,
                      canonical_tree=tree, tooling_source_commit=code, source_sha256=hashes,
                      created=datetime.now(timezone.utc).isoformat())
        if mutate_freeze:
            mutate_freeze(freeze)
        raw = m.encode(freeze)
        path = repo / m.FREEZE_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        if changed_tag_code:
            (repo / m.LAUNCHER).write_bytes(b'# synthetic changed code after declaration\n')
        self.git(repo, 'add', '.'); self.git(repo, 'commit', '-m', 'Synthetic prospective freeze')
        if annotated:
            self.git(repo, 'tag', '-a', m.TAG, '-m', 'Synthetic annotated tag')
        else:
            self.git(repo, 'tag', m.TAG)
        remote = root / 'remote.git'; remote.mkdir(); self.git(remote, 'init', '--bare')
        self.git(repo, 'remote', 'add', 'origin', str(remote))
        if pushed:
            self.git(repo, 'push', 'origin', 'refs/tags/' + m.TAG)
        return repo, dict(canonical_commit=canonical, canonical_tree=tree,
                          expected_tooling_hashes=hashes, expected_freeze_sha256=m.sha(raw),
                          expected_origin=str(remote))

    def test_exact_prospective_source_freeze_and_push_gate(self):
        repo, kwargs = self.fixture()
        result = m._verify_tooling_tag(repo, **kwargs)
        self.assertEqual(dict(result.source_hashes), kwargs['expected_tooling_hashes'])
        self.assertEqual(m.sha(result.package_files[m.LAUNCHER]), kwargs['expected_tooling_hashes'][m.LAUNCHER])
        self.assertEqual(self.git(repo, 'status', '--porcelain'), '')

    def test_unpushed_or_wrong_origin_cannot_admit_export(self):
        repo, kwargs = self.fixture(pushed=False)
        with self.assertRaisesRegex(ValueError, 'not exactly pushed'):
            m._verify_tooling_tag(repo, **kwargs)
        repo, kwargs = self.fixture()
        kwargs['expected_origin'] = 'synthetic-other-origin'
        with self.assertRaisesRegex(ValueError, 'origin differs'):
            m._verify_tooling_tag(repo, **kwargs)

    def test_freeze_hash_source_hash_or_canonical_tree_drift_rejected(self):
        for mutate in ('freeze', 'source', 'tree'):
            repo, kwargs = self.fixture()
            if mutate == 'freeze': kwargs['expected_freeze_sha256'] = '0' * 64
            elif mutate == 'source': kwargs['expected_tooling_hashes'] = dict(kwargs['expected_tooling_hashes'], **{m.LAUNCHER: '0' * 64})
            else: kwargs['canonical_tree'] = '0' * 40
            with self.subTest(kind=mutate):
                with self.assertRaises(ValueError): m._verify_tooling_tag(repo, **kwargs)

    def test_unreviewed_package_and_post_code_commit_changes_rejected(self):
        for settings in ({'extra': True}, {'changed_tag_code': True}):
            repo, kwargs = self.fixture(**settings)
            with self.subTest(category='unreviewed source'):
                with self.assertRaises(ValueError): m._verify_tooling_tag(repo, **kwargs)

    def test_annotated_tag_and_unknown_or_future_freeze_rejected(self):
        for settings in ({'annotated': True},
                         {'mutate_freeze': lambda f: f.update(extra=True)},
                         {'mutate_freeze': lambda f: f.update(created='2999-01-01T00:00:00+00:00')},
                         {'mutate_freeze': lambda f: f.update(schema_version=True)}):
            repo, kwargs = self.fixture(**settings)
            with self.subTest(category='tag/schema/time'):
                with self.assertRaises(ValueError): m._verify_tooling_tag(repo, **kwargs)

    def test_git_blob_reader_ignores_untracked_private_files(self):
        repo, kwargs = self.fixture()
        (repo / 'untracked-private.txt').write_bytes(b'Synthetic untracked content.\n')
        entries = m._tree_entries(repo, kwargs['canonical_commit'])
        files = m._blobs(repo, entries)
        self.assertEqual(files, {'README.md': b'Synthetic canonical input.\n'})


class ByteAssemblyTests(unittest.TestCase):
    def scripts(self):
        lines = m._workflow().decode().splitlines()
        result = []
        for index, line in enumerate(lines):
            if line == '        run: |':
                body = []
                for following in lines[index + 1:]:
                    if not following.startswith('          '):
                        break
                    body.append(following[10:])
                self.assertTrue(body[0].endswith(" <<'PY'"))
                self.assertEqual(body[-1], 'PY')
                prefix = body[0][:-len(" <<'PY'")].split()
                python = '\n'.join(body[1:-1]) + '\n'
                result.append((prefix, python))
        return result

    def claims(self):
        return dict(schema_version=1, kind='private_canonical_admission_attestation_v1',
                    canonical_commit=m.a.CANONICAL_COMMIT,
                    authority='author_attested_private_canonical_verification',
                    original_verification=dict(normal_private='PASS', optimized_private='PASS',
                                               master_ci=42620835573, master_ci_commit=m.a.CANONICAL_COMMIT),
                    artifact_hashes={'paper/out/swarm_audit_scoping.pdf': m.a.CANONICAL_PDF,
                                     'paper/out/swarm_audit_scoping.docx': m.a.CANONICAL_DOCX},
                    private_original_protocol_admission=m.a.PRIVATE_ADMISSION,
                    privacy_checks=dict(policy_version=1, reviewed_files=9, reviewed_spans=10,
                                        known_credential_values_checked=3, known_credential_matches=0,
                                        structured_fields_checked=True, unknown_secret_absence_claimed=False))

    def assemble(self, original=None, **kwargs):
        original = original or {'README.md': b'Canonical synthetic README.\n',
                                '.github/workflows/original.yml': b'name: Synthetic original\n',
                                'experiments/toy.py': b'VALUE = 17\n',
                                'data/toy.jsonl': b'{"scientific":17}\n'}
        return m._assemble_files(original, {m.LAUNCHER: b'# synthetic launcher\n'},
                                 redactions=kwargs.get('redactions', []), rebindings=kwargs.get('rebindings', []),
                                 private_attestation=kwargs.get('claims', self.claims()),
                                 tooling_source_commit='d' * 40)

    def test_original_workflow_readme_and_science_preserved_separately(self):
        files, manifest, receipt = self.assemble()
        self.assertEqual(files['provenance/CANONICAL_README.md'], b'Canonical synthetic README.\n')
        self.assertEqual(files['provenance/original-workflows/original.yml'], b'name: Synthetic original\n')
        self.assertNotIn('.github/workflows/original.yml', files)
        self.assertEqual([p for p in files if p.startswith('.github/workflows/')], ['.github/workflows/snapshot-integrity.yml'])
        self.assertEqual(files['data/toy.jsonl'], b'{"scientific":17}\n')
        self.assertEqual(files['experiments/toy.py'], b'VALUE = 17\n')
        self.assertEqual(manifest['files']['data/toy.jsonl']['role'], 'canonical')
        self.assertEqual(m.sha(files[m.a.MANIFEST]), receipt['manifest_sha256'])
        self.assertEqual(m.a.attestation_digest(receipt), manifest['attestation_sha256'])

    def test_attestation_mutation_does_not_mutate_encoded_snapshot(self):
        claims = self.claims()
        files, manifest, receipt = self.assemble(claims=claims)
        claims['privacy_checks']['known_credential_matches'] = 99
        self.assertEqual(receipt['privacy_checks']['known_credential_matches'], 0)
        self.assertEqual(m.a.decode_json(files[m.a.RECEIPT])['privacy_checks']['known_credential_matches'], 0)

    def test_private_guard_metadata_never_enters_public_assembly(self):
        row = dict(path='research/toy.md', line=1, category='provider_account_credit', semantic_role='initial_credit_observed')
        for private_key in ('original_sha256', 'line_sha256', 'source_sha256'):
            changed = dict(row, **{private_key: 'a' * 64})
            with self.subTest(field=private_key):
                with self.assertRaisesRegex(ValueError, 'private redaction guard'):
                    self.assemble(redactions=[changed])

    def test_external_pins_before_dependencies_and_replay_in_workflow(self):
        workflow = m._workflow().decode()
        self.assertIn('vars.SNAPSHOT_MANIFEST_SHA256', workflow)
        self.assertIn('vars.SNAPSHOT_LAUNCHER_SHA256', workflow)
        self.assertLess(workflow.index('--preflight-only'), workflow.index('pip install'))
        self.assertLess(workflow.index('pip install'), workflow.index('Verify disclosed mathematics'))
        self.assertNotIn('admission.json', workflow)
        self.assertIn('persist-credentials: false', workflow)

    def test_generated_heredoc_python_is_real_multiline_syntax(self):
        scripts = self.scripts()
        self.assertEqual(len(scripts), 5)
        for prefix, source in scripts:
            with self.subTest(mode=' '.join(prefix[1:])):
                ast.parse(source)
                self.assertIn('\nimport', '\n' + source)
                self.assertNotIn('\\nimport', source)
        self.assertEqual(sum('-O' in prefix for prefix, _ in scripts), 2)
        self.assertEqual(sum('--tests-only' in prefix for prefix, _ in scripts), 2)
        self.assertIn('--preflight-only', scripts[0][0])

    def test_decoded_workflow_bootstrap_executes_toy_launcher_and_propagates_optimization(self):
        launcher = (b'import json,os,pathlib,sys\n'
                    b'pathlib.Path(os.environ["SYNTHETIC_PROBE"]).write_text(json.dumps({"opt":sys.flags.optimize,"args":sys.argv[1:]}))\n')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / m.LAUNCHER
            target.parent.mkdir(); target.write_bytes(launcher)
            probe = root / 'probe.json'
            env = dict(os.environ, SNAPSHOT_LAUNCHER_SHA256=m.sha(launcher),
                       SNAPSHOT_MANIFEST_SHA256='a' * 64, SYNTHETIC_PROBE=str(probe))
            for prefix, source in self.scripts():
                with self.subTest(mode=' '.join(prefix[1:])):
                    result = subprocess.run([sys.executable, *prefix[1:]], input=source.encode(),
                                            cwd=root, env=env, capture_output=True)
                    self.assertEqual(result.returncode, 0, 'Decoded toy bootstrap failed')
                    value = json.loads(probe.read_text())
                    self.assertEqual(value['opt'], int('-O' in prefix))
                    self.assertEqual(value['args'][:2], ['--expected-manifest-sha256', 'a' * 64])
                    self.assertEqual('--tests-only' in value['args'], '--tests-only' in prefix)

    def test_bootstrap_rejects_bad_or_missing_external_pin_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / m.LAUNCHER
            target.parent.mkdir(); target.write_bytes(b'raise SystemExit("Toy launcher should not execute")\n')
            prefix, source = self.scripts()[0]
            for expected in ('', '0' * 64):
                env = dict(os.environ, SNAPSHOT_LAUNCHER_SHA256=expected,
                           SNAPSHOT_MANIFEST_SHA256='a' * 64)
                result = subprocess.run([sys.executable, *prefix[1:]], input=source.encode(),
                                        cwd=root, env=env, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'Toy launcher should not execute', result.stderr)

    def test_readme_checks_launcher_and_preflight_before_dependency_install(self):
        text = m._new_readme().decode()
        self.assertLess(text.index('python -I -B -c'), text.index('--preflight-only'))
        self.assertLess(text.index('--preflight-only'), text.index('pip install'))
        self.assertIn('-B -O public_snapshot/verify.py', text)
        self.assertIn('--tests-only', text)
        self.assertIn('research/PUBLIC_SNAPSHOT_DISCLOSURE_PROTOCOL.md', text)
        for folder in ('paper/out/', 'data/', 'experiments/', 'analysis/', 'research/', 'public_snapshot/'):
            self.assertIn('`' + folder + '`', text)

    def test_private_literal_generators_are_materialized_once_and_reusable(self):
        values = (value for value in (b'synthetic-one', b'synthetic-two', b'synthetic-three'))
        checked = m._private_literals({'credential': values})
        self.assertEqual(checked['credential'], (b'synthetic-one', b'synthetic-two', b'synthetic-three'))
        self.assertEqual(tuple(checked['credential']), tuple(checked['credential']))
        for bad in ({'credential': [b'same'] * 3}, {'credential': ['not bytes']},
                    {'credential': [b'']}, {'unknown': [b'synthetic']}):
            with self.assertRaises(ValueError): m._private_literals(bad)

    def test_retired_commitment_scope_includes_original_variants_and_line_guards(self):
        original = {'research/toy.json': b'{"value": 1}\r\n'}
        transformed = {'research/toy.json': b'{"value":2}\n'}
        guard = m.sha(b'Synthetic guarded line.\n')
        rules = [types.SimpleNamespace(spans=[types.SimpleNamespace(line_sha256=guard)])]
        result = m._no_retired_commitments(original, transformed, rules, {'safe.txt': b'Synthetic safe text.\n'})
        expected = {guard.encode(), *(value.encode() for value in m.rebinding.variants('research/toy.json', original['research/toy.json']).values())}
        self.assertEqual(result, frozenset(expected))
        with self.assertRaisesRegex(ValueError, 'private original commitment retained'):
            m._no_retired_commitments(original, transformed, rules, {'safe.txt': guard.upper().encode()})

    def test_retired_commitments_rejected_inside_compressed_containers(self):
        token = m.sha(b'Synthetic retired source commitment.')
        escaped = ''.join('\\u%04x' % ord(character) for character in token.upper())
        payloads = {}
        for suffix, member, body in (
                ('zip', 'metadata.json', json.dumps({'digest': token.upper()}).encode()),
                ('zip', 'escaped.json', ('{"digest":"' + escaped + '"}').encode()),
                ('docx', 'word/document.xml', ('<document><p>' + token.upper() + '</p></document>').encode())):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(member, body)
            payloads['artifact-' + member.replace('/', '-') + '.' + suffix] = stream.getvalue()
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(('BT /F1 12 Tf 72 720 Td (' + token.upper() + ') Tj ET').encode())
        page[NameObject('/Contents')] = writer._add_object(stream.flate_encode())
        output = io.BytesIO(); writer.write(output)
        payloads['artifact.pdf'] = output.getvalue()
        private = {'credential': (b'synthetic-one', b'synthetic-two', b'synthetic-three')}
        for name, raw in payloads.items():
            with self.subTest(container=name.rsplit('.', 1)[-1]):
                retired = m._no_retired_commitments({}, {}, [], {name: raw})
                self.assertEqual(retired, frozenset())
                with self.assertRaisesRegex(ValueError, 'private_source_commitment'):
                    m._audit_private_files({name: raw}, private, frozenset({token.encode()}), {}, {})
        self.assertNotIn('private_source_commitment', private)

    def test_final_response_approvals_are_path_field_metadata_only(self):
        files = {'data/toy.jsonl': b'{"final_output":"synthetic final","actual_output":"synthetic legacy final"}\n',
                 'research/toy.json': b'{"rows":[{"response":{"output_text":"synthetic final"}}]}\n',
                 'experiments/toy.py': b'TEXT = "not structured data"\n'}
        final, reports = m.collect_approval_candidates(files)
        self.assertEqual(final, {'data/toy.jsonl': {('final_output',), ('actual_output',)},
                                 'research/toy.json': {('rows', '[]', 'response', 'output_text')}})
        self.assertEqual(reports, {})
        self.assertNotIn('synthetic final', repr(final))

    def test_destination_and_issuer_receipt_are_new_and_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); source = root / 'source'; source.mkdir()
            target, receipt = m._destinations(source, root / 'new', root / 'receipt.json')
            self.assertEqual(target, root / 'new')
            with self.assertRaises(ValueError): m._destinations(source, source, root / 'receipt.json')
            with self.assertRaises(ValueError): m._destinations(source, root / 'new', root / 'new/receipt.json')
            gitdir = source / '.git'; gitdir.mkdir()
            with self.assertRaises(ValueError): m._destinations(source, gitdir / 'new', root / 'receipt.json')

    def test_exclusive_writer_never_overwrites_an_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'snapshot'
            m._write_new_snapshot(target, {'safe.txt': b'synthetic'})
            self.assertEqual((target / 'safe.txt').read_bytes(), b'synthetic')
            with self.assertRaises(ValueError): m._write_new_snapshot(target, {'safe.txt': b'changed'})
            self.assertEqual((target / 'safe.txt').read_bytes(), b'synthetic')


if __name__ == '__main__':
    unittest.main()
