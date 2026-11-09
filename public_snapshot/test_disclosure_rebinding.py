"""Toy-only metadata rebinding: no project source plan or empirical export."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('rebinding_under_test', Path(__file__).with_name('disclosure_rebinding.py'))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class RebindingTests(unittest.TestCase):
    def fixture(self):
        document = b'Private synthetic field: OMIT_ME.\r\nBudget cap remains unchanged.\r\n'
        freeze = ('{\r\n  "source_sha256": {"research/toy.md": "' + m.sha(document.replace(b'\r\n', b'\n')) + '"},\r\n  "science": [17, true]\r\n}\r\n').encode()
        report = json.dumps({'freeze_sha256': m.sha(freeze), 'scientific_estimate': .125}, indent=2).encode() + b'\n'
        note = ('Résumé metadata ' + m.sha(report) + '; keep text.\n').encode()
        files = {'research/toy.md': document, 'research/toy-freeze.json': freeze,
                 'research/toy-report.json': report, 'research/toy-note.md': note,
                 'experiments/toy.py': b'CONSTANT = 17\n', 'data/toy.jsonl': b'{"scientific":17}\n'}
        seeds = {'research/toy.md': document.replace(b'OMIT_ME', b'[withheld]')}
        findings = [
            dict(path='research/toy-freeze.json', json_field='/source_sha256/research/toy.md',
                 private_metadata_source_path='research/toy.md', category='direct_private_source_commitment'),
            dict(path='research/toy-report.json', json_pointer='/freeze_sha256',
                 private_metadata_source_path='research/toy-freeze.json', category='indirect_private_source_commitment'),
            dict(path='research/toy-note.md', line=1, private_metadata_source_path='research/toy-report.json',
                 category='indirect_private_source_commitment'),
        ]
        return files, seeds, findings

    def test_transitive_byte_preserving_rebinding_and_public_metadata(self):
        files, seeds, findings = self.fixture()
        plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
        updated, public = m.rebind_metadata(files, seeds, plan)
        self.assertEqual(updated['research/toy.md'], seeds['research/toy.md'])
        freeze = files['research/toy-freeze.json'].replace(m.variants('research/toy.md', files['research/toy.md'])['lf'].encode(),
                                                         m.variants('research/toy.md', updated['research/toy.md'])['lf'].encode())
        self.assertEqual(updated['research/toy-freeze.json'], freeze)
        self.assertEqual(updated['research/toy-report.json'], files['research/toy-report.json'].replace(m.sha(files['research/toy-freeze.json']).encode(), m.sha(freeze).encode()))
        self.assertEqual(updated['research/toy-note.md'], files['research/toy-note.md'].replace(m.sha(files['research/toy-report.json']).encode(), m.sha(updated['research/toy-report.json']).encode()))
        self.assertEqual(updated['experiments/toy.py'], files['experiments/toy.py'])
        self.assertEqual(updated['data/toy.jsonl'], files['data/toy.jsonl'])
        encoded = json.dumps(public)
        self.assertNotIn('OMIT_ME', encoded)
        self.assertNotIn('original_sha256', encoded)
        self.assertNotIn('line_sha256', encoded)
        for name in files:
            if name in seeds or name in plan['locations']:
                self.assertNotIn(m.sha(files[name]), encoded)
        self.assertTrue(all(set(c) == {'path', 'sha256', 'category'} for c in public['changes']))
        self.assertEqual(json.loads(updated['research/toy-freeze.json'])['science'], [17, True])

    def test_original_and_seed_guard_drift_rejected(self):
        files, seeds, findings = self.fixture()
        plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
        for changed_files, changed_seeds in ((dict(files, **{'experiments/toy.py': b'changed'}), seeds),
                                              (files, dict(seeds, **{'research/toy.md': b'changed'}))):
            with self.assertRaises(m.RebindingError):
                m.rebind_metadata(changed_files, changed_seeds, plan)

    def test_missing_closure_location_fails_instead_of_leaving_old_hash(self):
        files, seeds, findings = self.fixture()
        plan = m.build_private_location_plan(files, seeds, findings[:-1], 'a' * 40)
        with self.assertRaisesRegex(m.RebindingError, 'unreviewed stale'):
            m.rebind_metadata(files, seeds, plan)

    def test_source_variant_is_matched_not_guessed(self):
        files, seeds, findings = self.fixture()
        broken = dict(files)
        broken['research/toy-report.json'] = broken['research/toy-report.json'].replace(m.sha(files['research/toy-freeze.json']).encode(), b'0' * 64)
        with self.assertRaisesRegex(m.RebindingError, 'variant'):
            m.build_private_location_plan(broken, seeds, findings, 'a' * 40)

    def test_json_pointer_escaping_arrays_unicode_and_exact_token_offsets(self):
        raw = ('{"é": "keep", "a/b~c": ["' + 'd' * 64 + '"]}\r\n').encode()
        tokens = m.json_string_tokens(raw)
        token = tokens['/a~1b~0c/0']
        self.assertEqual(raw[token['start']:token['end']], ('"' + 'd' * 64 + '"').encode())
        self.assertEqual(token['value'], 'd' * 64)

    def test_scanner_display_ambiguity_is_rejected(self):
        files = {'research/source.md': b'toy', 'research/target.json': json.dumps({'a/b': m.sha(b'toy'), 'a': {'b': m.sha(b'toy')}}).encode()}
        findings = [dict(path='research/target.json', json_field='/a/b', source_path='research/source.md', category='private_source_commitment')]
        with self.assertRaisesRegex(m.RebindingError, 'ambiguous'):
            m.build_private_location_plan(files, {}, findings, 'a' * 40)

    def test_cycles_rejected_without_rehash_loop(self):
        files, seeds, findings = self.fixture()
        plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
        plan['locations']['research/toy-freeze.json'][0]['source_path'] = 'research/toy-report.json'
        with self.assertRaisesRegex(m.RebindingError, 'cycle'):
            m.rebind_metadata(files, seeds, plan)

    def test_updated_variant_ambiguity_is_rejected(self):
        files = {'research/source.json': b'{"x":1}', 'research/target.json': ('{"source":"' + m.sha(b'{"x":1}') + '"}').encode()}
        seeds = {'research/source.json': b'{ "x": 1 }'}
        findings = [dict(path='research/target.json', json_pointer='/source', source_path='research/source.json', category='private_source_commitment')]
        plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
        with self.assertRaisesRegex(m.RebindingError, 'ambiguous updated'):
            m.rebind_metadata(files, seeds, plan)

    def test_code_data_targets_and_escaped_paths_refused(self):
        files, seeds, findings = self.fixture()
        for path in ('experiments/toy.py', 'data/toy.jsonl', '../research/toy.md', '/research/toy.md', 'research/../toy.md'):
            bad = deepcopy(findings)
            bad[0]['path'] = path
            with self.assertRaises(m.RebindingError):
                m.build_private_location_plan(files, seeds, bad, 'a' * 40)

    def test_duplicate_keys_nonfinite_and_trailing_json_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{}{}'):
            with self.assertRaises(m.RebindingError):
                m.json_string_tokens(raw)

    def test_unreviewed_code_hash_reference_fails_closed(self):
        files, seeds, findings = self.fixture()
        files['experiments/toy.py'] += ('REFERENCE = "' + m.sha(files['research/toy.md']) + '"\n').encode()
        plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
        with self.assertRaisesRegex(m.RebindingError, 'unreviewed stale'):
            m.rebind_metadata(files, seeds, plan)

    def test_unknown_escaped_or_uppercase_hash_oracle_rejected(self):
        for form in ('escaped', 'uppercase'):
            files, seeds, findings = self.fixture()
            digest = m.sha(files['research/toy.md'])
            value = ('\\u00' + format(ord(digest[0]), '02x') + digest[1:]) if form == 'escaped' else digest.upper()
            files['research/unreviewed.json'] = ('{"unexpected":"' + value + '"}\n').encode()
            plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
            with self.subTest(form=form), self.assertRaisesRegex(m.RebindingError, 'unreviewed stale'):
                m.rebind_metadata(files, seeds, plan)

    def test_malformed_location_schema_fails_closed(self):
        files, seeds, findings = self.fixture()
        plan = m.build_private_location_plan(files, seeds, findings, 'a' * 40)
        for change in ('missing', 'extra', 'kind'):
            invalid = deepcopy(plan)
            control = invalid['locations']['research/toy-freeze.json'][0]
            if change == 'missing':
                del control['hash_variants']
            elif change == 'extra':
                control['unreviewed'] = True
            else:
                control['kind'] = 'text_line'
            with self.subTest(change=change), self.assertRaises(m.RebindingError):
                m.rebind_metadata(files, seeds, invalid)


if __name__ == '__main__':
    unittest.main()
