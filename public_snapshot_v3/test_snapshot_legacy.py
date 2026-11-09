"""Synthetic boundary/contrast tests only; never replay empirical artifacts."""
import importlib.util
import hashlib
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('snapshot_legacy_under_test', Path(__file__).with_name('snapshot_legacy.py'))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        (self.root / 'data/toy.json').write_bytes(b'{"synthetic":true}\n')
        self.proof = dict(schema_version=1, canonical_commit='a' * 40,
            disclosure_manifest_sha256='b' * 64, files={'data/toy.json': m.sha(self.root / 'data/toy.json')},
            scope=m.SCOPE, private_original_protocol_admission='attested_not_publicly_repeated')

    def test_exact_admission_and_postcheck(self):
        files = m.AdmittedFiles(self.root, lambda _: self.proof)
        self.assertEqual(files.read('data/toy.json'), {'synthetic': True})
        files.finish()

    def test_missing_admission_scope_and_extra_key_fail_closed(self):
        for change in ({'scope': 'legacy_full_source_admission'}, {'extra': 1}, {'schema_version': True}):
            proof = dict(self.proof, **change)
            with self.assertRaises(ValueError):
                m.AdmittedFiles(self.root, lambda _: proof)

    def test_undeclared_escaped_and_private_path_rejected(self):
        files = m.AdmittedFiles(self.root, lambda _: self.proof)
        for name in ('data/absent.json', '../toy.json', 'C:/toy.json', '/toy.json', 'runs/toy.json', 'data\\toy.json'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                files.path(name)

    def test_post_admission_mutation_rejected(self):
        files = m.AdmittedFiles(self.root, lambda _: self.proof)
        (self.root / 'data/toy.json').write_bytes(b'{"synthetic":false}\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            files.finish()

    def test_duplicate_or_nonfinite_json_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":[1e999]}'):
            with self.assertRaises(ValueError):
                m.strict_json(raw)

    def test_admission_reinvoked_and_changed_manifest_facts_rejected(self):
        calls = []
        def callback(root):
            calls.append(root)
            return self.proof if len(calls) == 1 else dict(self.proof, disclosure_manifest_sha256='c' * 64)
        files = m.AdmittedFiles(self.root, callback)
        with self.assertRaisesRegex(ValueError, 'disclosure admission changed'):
            files.finish()
        self.assertEqual(calls, [self.root, self.root])

    def test_extra_file_added_after_admission_rejected(self):
        files = m.AdmittedFiles(self.root, lambda _: self.proof)
        (self.root / 'data/unadmitted.json').write_bytes(b'{"synthetic":17}\n')
        with self.assertRaisesRegex(ValueError, 'whole-file inventory changed'):
            files.finish()

    def test_unlisted_manifest_byte_change_rejected(self):
        (self.root / 'disclosure.json').write_bytes(b'{"synthetic_manifest":1}\n')
        files = m.AdmittedFiles(self.root, lambda _: self.proof)
        (self.root / 'disclosure.json').write_bytes(b'{"synthetic_manifest":2}\n')
        with self.assertRaisesRegex(ValueError, 'whole-file inventory changed'):
            files.finish()

    def test_callback_cannot_create_extra_file_at_postcheck(self):
        calls = []
        def callback(root):
            calls.append(root)
            if len(calls) == 2:
                (root / 'extra.json').write_bytes(b'{"synthetic":true}\n')
            return self.proof
        files = m.AdmittedFiles(self.root, callback)
        with self.assertRaisesRegex(ValueError, 'whole-file inventory changed'):
            files.finish()

    def test_json_and_jsonl_hash_and_parse_same_single_read(self):
        original_read = Path.read_bytes
        for kind in ('json', 'jsonl'):
            path = self.root / ('data/toy.' + kind)
            expected = b'{"synthetic":true}\n'
            path.write_bytes(expected)
            proof = dict(self.proof, files={path.relative_to(self.root).as_posix(): m.sha(path)})
            files = m.AdmittedFiles(self.root, lambda _: proof)
            calls = []
            def intercepted(target):
                if target == path:
                    calls.append(target)
                    return expected if len(calls) == 1 else b'{"synthetic":false}\n'
                return original_read(target)
            with patch.object(Path, 'read_bytes', intercepted):
                value = files.read('data/toy.json') if kind == 'json' else files.rows('data/toy.jsonl')
            self.assertEqual(value, {'synthetic': True} if kind == 'json' else [{'synthetic': True}])
            self.assertEqual(len(calls), 1)
            files.finish()


class ContrastTests(unittest.TestCase):
    def fixture(self):
        episodes = [dict(episode_id='toy-clean', family='toy', cohort='clean'),
                    dict(episode_id='toy-violation', family='toy', cohort='violation')]
        rows = []
        for e in episodes:
            for churn in (False, True):
                for mechanism, restoration in (('targeted', 'none'), ('random', 'none'),
                                                ('targeted', 'priority'), ('targeted', 'random')):
                    clean = e['cohort'] == 'clean'
                    score = dict(unsupported_executor=int(clean and churn and mechanism == 'targeted' and restoration == 'none'),
                                 grounded_correct=int(restoration == 'priority'),
                                 supported_definite=int(restoration == 'priority'), status='NONE')
                    rows.append(dict(returned=True, model='toy-model',
                        task=dict(episode_id=e['episode_id'], churn=churn, mechanism=mechanism, restoration=restoration), scored=score))
        config = dict(models=['toy-model'], primary_model='toy-model', bootstrap_seed=17, bootstrap_resamples=9)
        return episodes, rows, config

    def test_four_matched_contrasts_and_clean_bound_use_source_n(self):
        episodes, rows, config = self.fixture()
        calls = []
        def bootstrap(groups, seed, n):
            calls.append((groups, seed, n))
            return [-1, 1]
        effects = m.stateful_main_effects(episodes, rows, config, bootstrap)['toy-model']
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(seed == 17 and n == 9 for _, seed, n in calls))
        self.assertEqual(effects['primary_unsupported_targeted_minus_random']['estimate'], .5)
        self.assertEqual(effects['secondary_churn_interaction']['estimate'], .5)
        self.assertEqual(effects['restoration_grounded_priority_minus_random']['estimate'], 1)
        self.assertEqual(effects['restoration_coverage_priority_minus_none']['estimate'], 1)
        self.assertEqual(effects['primary_unsupported_targeted_minus_random']['episode_n'], 2)
        self.assertFalse(effects['primary_unsupported_targeted_minus_random']['secondary'])
        self.assertEqual(effects['clean_episode_false_accusation']['n'], 1)
        self.assertAlmostEqual(effects['clean_episode_false_accusation']['zero_event_upper95'], .95)

    def test_duplicate_or_missing_pair_never_replaced(self):
        episodes, rows, config = self.fixture()
        for invalid in (rows + [rows[0]], rows[1:]):
            with self.assertRaises(ValueError):
                m.stateful_main_effects(episodes, invalid, config, lambda *_: [0, 0])

    def test_clean_event_bound_and_secondary_reader_flag(self):
        episodes, rows, config = self.fixture()
        rows[0]['scored']['status'] = 'EXECUTOR'
        # The bound concerns the churned loss views, not the unchanged view.
        rows[4]['scored']['status'] = 'EXECUTOR'
        config['primary_model'] = 'different-primary'
        effects = m.stateful_main_effects(episodes, rows, config, lambda *_: [0, 0])['toy-model']
        self.assertTrue(effects['primary_unsupported_targeted_minus_random']['secondary'])
        self.assertEqual(effects['clean_episode_false_accusation']['events'], 1)
        self.assertIsNone(effects['clean_episode_false_accusation']['zero_event_upper95'])

    def test_actual_frozen_bootstrap_on_toy_strata(self):
        root = next(p for p in Path(__file__).resolve().parents if (p / 'experiments/stateful_analysis.py').is_file())
        sys.path.insert(0, str(root))
        self.addCleanup(lambda: sys.path.remove(str(root)))
        from experiments.stateful_analysis import bootstrap
        episodes, rows, config = self.fixture()
        effects = m.stateful_main_effects(episodes, rows, config, bootstrap)['toy-model']
        # One source per stratum: stratified resampling has no within-stratum variation.
        self.assertEqual(effects['primary_unsupported_targeted_minus_random']['ci95'], [.5, .5])
        self.assertEqual(effects['secondary_churn_interaction']['ci95'], [.5, .5])
        self.assertEqual(effects['restoration_grounded_priority_minus_random']['ci95'], [1, 1])

    def test_baselines_preserve_required_abstention(self):
        packets = [{'compatible_labels': ['A']}, {'compatible_labels': ['NONE']}, {'compatible_labels': ['A', 'B']}]
        result = m.stateful_baselines(packets)
        self.assertEqual(result['exact_packet'], dict(packets=3, grounded_correct=3, supported_definite=2, unsupported_executor=0))
        self.assertEqual(result['always_abstain']['grounded_correct'], 1)
        self.assertEqual(result['fixed_actor_A']['grounded_correct'], 1)
        self.assertEqual(result['fixed_actor_A']['unsupported_executor'], 2)


if __name__ == '__main__':
    unittest.main()
