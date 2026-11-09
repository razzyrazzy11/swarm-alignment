"""Synthetic integrity tests only; no actual study data or mathematical replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import snapshot_math as replay


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


class SyntheticDisclosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {}

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = value if type(value) is bytes else (canonical(value) + '\n').encode('utf-8')
        path.write_bytes(raw)
        self.files[name] = hashlib.sha256(raw).hexdigest()
        return raw

    def facts(self):
        return dict(schema_version=1, canonical_commit='a' * 40,
                    disclosure_manifest_sha256='b' * 64, files=dict(self.files),
                    scope=replay.SCOPE, private_original_protocol_admission=replay.PRIVATE_ADMISSION)

    def binding(self):
        return replay.AdmissionBinding.check(self.root, self.facts())

    def shards(self):
        self.put('data/toy/manifest.json', {'synthetic': True})
        rows = [{'id': 'synthetic-1', 'value': 2}, {'id': 'synthetic-2', 'value': 3}]
        raw = ''.join(canonical(row) + '\n' for row in rows).encode()
        self.put('data/toy/cases-toy-0000.jsonl', raw)
        manifest = {'artifacts': {'cases:toy': [dict(file='cases-toy-0000.jsonl', bytes=len(raw),
                                                  rows=len(rows), sha256=hashlib.sha256(raw).hexdigest())]}}
        return rows, manifest

    def load_shards(self, manifest):
        return replay.read_shard_groups(self.binding(), 'data/toy', manifest, {'cases:toy'},
                                        {'manifest.json'}, 10_000, canonical)

    def test_explicit_admission_binding_is_immutable_and_exact(self):
        self.put('data/toy.json', {'synthetic': True})
        facts = self.facts()
        binding = replay.AdmissionBinding.check(self.root, facts)
        facts['files']['data/toy.json'] = 'c' * 64
        self.assertEqual(binding.json('data/toy.json'), {'synthetic': True})
        with self.assertRaises(TypeError):
            binding.files['data/toy.json'] = 'd' * 64

    def test_no_default_or_boolean_admission(self):
        self.put('data/toy.json', {})
        for facts in (None, True, False, {}, {'valid': True}):
            with self.subTest(facts_type=type(facts).__name__):
                with self.assertRaises(ValueError):
                    replay.AdmissionBinding.check(self.root, facts)
        with self.assertRaisesRegex(ValueError, 'Explicit source-disclosure'):
            replay.verify_main_and_sensitivity(self.root, None)

    def test_disclosure_gate_runs_before_and_after_the_replay(self):
        self.put('data/toy.json', {})
        calls = []
        def gate(root):
            calls.append(root)
            return self.facts()
        with replay.admitted_snapshot(self.root, gate) as binding:
            self.assertEqual(binding.json('data/toy.json'), {})
            self.assertEqual(len(calls), 1)
        self.assertEqual(calls, [self.root, self.root])

    def test_disclosure_fact_drift_is_rejected_after_replay(self):
        self.put('data/toy.json', {})
        calls = []
        def gate(root):
            calls.append(root)
            value = self.facts()
            if len(calls) == 2:
                value['disclosure_manifest_sha256'] = 'c' * 64
            return value
        with self.assertRaisesRegex(ValueError, 'disclosure changed'):
            with replay.admitted_snapshot(self.root, gate):
                pass

    def test_input_byte_drift_is_rejected_after_replay(self):
        self.put('data/toy.json', {})
        with self.assertRaisesRegex(ValueError, 'checksum'):
            with replay.admitted_snapshot(self.root, lambda root: self.facts()):
                (self.root / 'data/toy.json').write_bytes(b'{"changed":true}\n')

    def test_unknown_fields_modes_and_invalid_commitments_fail_closed(self):
        self.put('data/toy.json', {})
        variants = []
        value = self.facts(); value['extra'] = True; variants.append(value)
        value = self.facts(); value['schema_version'] = True; variants.append(value)
        value = self.facts(); value['scope'] = 'historical-source-authenticated'; variants.append(value)
        value = self.facts(); value['private_original_protocol_admission'] = 'publicly_repeated'; variants.append(value)
        value = self.facts(); value['canonical_commit'] = 'a' * 39; variants.append(value)
        value = self.facts(); value['disclosure_manifest_sha256'] = 'B' * 64; variants.append(value)
        value = self.facts(); value['files'] = {}; variants.append(value)
        for value in variants:
            with self.subTest(keys=sorted(value)):
                with self.assertRaises(ValueError):
                    replay.AdmissionBinding.check(self.root, value)

    def test_unsafe_or_private_paths_rejected_before_read(self):
        for name in ('../a', '/a', 'a\\b', 'C:a', 'a//b', 'a/./b', '.git/config',
                     'runs/raw.json', 'nested/runs-private/raw.json', '.env', '.env.production'):
            with self.subTest(path_category='unsafe/private'):
                value = self.facts(); value['files'] = {name: 'c' * 64}
                with self.assertRaises(ValueError):
                    replay.AdmissionBinding.check(self.root, value)

    def test_environment_example_stays_permitted(self):
        self.put('.env.example', b'SYNTHETIC_KEY=\n')
        self.assertEqual(self.binding().read('.env.example'), b'SYNTHETIC_KEY=\n')

    def test_missing_unadmitted_and_changed_inputs_rejected(self):
        self.put('data/toy.json', {'synthetic': True})
        binding = self.binding()
        with self.assertRaisesRegex(ValueError, 'not admitted'):
            binding.read('data/other.json')
        (self.root / 'data/toy.json').write_bytes(b'{}\n')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            binding.verify_files()
        (self.root / 'data/toy.json').unlink()
        with self.assertRaises(ValueError):
            binding.verify_files()

    def test_symlink_input_rejected(self):
        self.put('data/toy.json', b'{}\n')
        link = self.root / 'data/alias.json'
        try:
            link.symlink_to(self.root / 'data/toy.json')
        except (OSError, NotImplementedError):
            self.skipTest('Host does not permit creating synthetic symlinks')
        self.files['data/alias.json'] = self.files['data/toy.json']
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.binding()

    def test_nonfinite_and_duplicate_json_are_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"x":-Infinity}', b'{"x":1e999}', b'[1, {"x": 1e999}]', b'\xff'):
            with self.subTest(category='ambiguous/nonfinite/invalid'):
                with self.assertRaises(ValueError):
                    replay.strict_json(raw)

    def test_valid_json_preserves_numeric_and_boolean_types(self):
        value = replay.strict_json(b'{"a":1,"b":true,"c":1.5,"d":[null,false]}')
        self.assertIs(type(value['a']), int)
        self.assertIs(type(value['b']), bool)
        self.assertEqual(value['d'], [None, False])

    def test_valid_shards_preserve_exact_rows(self):
        expected, manifest = self.shards()
        self.assertEqual(self.load_shards(manifest), {'cases:toy': expected})

    def test_shard_group_path_order_and_unknown_fields_rejected(self):
        _, manifest = self.shards()
        variants = []
        value = deepcopy(manifest); value['artifacts']['extra'] = []; variants.append(value)
        value = deepcopy(manifest); value['artifacts']['cases:toy'] = []; variants.append(value)
        value = deepcopy(manifest); value['artifacts']['cases:toy'][0]['file'] = '../elsewhere'; variants.append(value)
        value = deepcopy(manifest); value['artifacts']['cases:toy'][0]['file'] = 'cases-toy-0001.jsonl'; variants.append(value)
        value = deepcopy(manifest); value['artifacts']['cases:toy'][0]['extra'] = True; variants.append(value)
        for value in variants:
            with self.subTest(category='schema/path/order'):
                with self.assertRaises(ValueError):
                    self.load_shards(value)

    def test_shard_checksum_size_and_row_loss_rejected(self):
        _, manifest = self.shards()
        for field, value in (('bytes', True), ('bytes', 1), ('rows', True), ('rows', 1),
                             ('sha256', '0' * 64)):
            changed = deepcopy(manifest); changed['artifacts']['cases:toy'][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.load_shards(changed)

    def test_noncanonical_jsonl_and_incomplete_tail_rejected(self):
        for raw in (b'{"id":"synthetic-1", "value":2}\n',
                    b'{"id":"synthetic-1","value":2}',
                    b'{"id":"synthetic-1","value":2}\r\n',
                    b'[]\n'):
            with self.subTest(category='noncanonical/truncated/nonobject'):
                self.files = {}
                self.put('data/toy/manifest.json', {})
                self.put('data/toy/cases-toy-0000.jsonl', raw)
                manifest = {'artifacts': {'cases:toy': [dict(file='cases-toy-0000.jsonl',
                    bytes=len(raw), rows=1, sha256=hashlib.sha256(raw).hexdigest())]}}
                with self.assertRaises(ValueError):
                    self.load_shards(manifest)

    def test_unlisted_or_nonregular_artifact_rejected(self):
        _, manifest = self.shards()
        self.put('data/toy/unlisted.json', {})
        with self.assertRaisesRegex(ValueError, 'Unlisted/nonregular'):
            self.load_shards(manifest)
        (self.root / 'data/toy/unlisted.json').unlink()
        self.files.pop('data/toy/unlisted.json')
        (self.root / 'data/toy/subdirectory').mkdir()
        with self.assertRaisesRegex(ValueError, 'Unlisted/nonregular'):
            self.load_shards(manifest)


if __name__ == '__main__':
    unittest.main()
