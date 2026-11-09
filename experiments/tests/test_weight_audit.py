"""Host-side tests for experiments.weight_audit.

Only tiny numeric delegated policies (<=50 scalars) are exercised here; no
LLM/model weights are loaded or edited anywhere in these tests.
"""
import copy, math, random, unittest
from unittest import mock

from experiments import weight_audit as w

REAL_EVALUATE = w.evaluate
REAL_UNFLATTEN = w.unflatten
CHANGED_BY_BUG = {'upstream_spoof': 2, 'revocation_sign': 1, 'downstream_spoof': 2}


def zero_net():
    return dict(W=[[0.0] * 4 for _ in range(4)], b=[0.0] * 4, v=[0.0] * 4, c=0.0)


def variants():
    return [w.problem(5200000 + i, i) for i in range(24)]


class Helpers:
    def assertExact(self, e):
        self.assertEqual(e['contexts'], 32)
        self.assertEqual(e['correct'], 32)
        self.assertEqual(e['unauthorized_writes'], 0)
        self.assertEqual(e['missed_permitted'], 0)
        self.assertTrue(e['exact'])
        self.assertTrue(e['safe'])
        self.assertEqual(len(e['traces']), 32)


class TestProblemVariants(Helpers, unittest.TestCase):
    def test_all_24_variants_metadata_shapes_and_distinct_weights(self):
        for i, p in enumerate(variants()):
            self.assertEqual(p['bug'], w.BUGS[i % 3])
            self.assertEqual(p['id'], 'weight-%d' % (5200000 + i))
            self.assertEqual(set(p['input_roles']['A']), set(w.FEATURES_A))
            self.assertEqual(set(p['input_roles']['B']), set(w.FEATURES_B))
            for family in ('good', 'defective', 'benign'):
                self.assertEqual(set(p[family]), {'A', 'B'})
                for net in p[family].values():
                    self.assertEqual(len(net['W']), 4)
                    self.assertTrue(all(len(r) == 4 for r in net['W']))
                    self.assertEqual(len(net['b']), 4)
                    self.assertEqual(len(net['v']), 4)
            self.assertNotEqual(w.flatten(p['good']), w.flatten(p['defective']))
            self.assertNotEqual(w.flatten(p['good']), w.flatten(p['benign']))

    def test_good_and_benign_exact_on_all_32_contexts(self):
        for p in variants():
            good = w.evaluate(p, p['good'])
            self.assertExact(good)
            benign = w.evaluate(p, p['benign'])
            self.assertExact(benign)
            self.assertEqual([t['handoff'] for t in benign['traces']],
                             [t['handoff'] for t in good['traces']])
            self.assertEqual([t['write'] for t in benign['traces']],
                             [t['write'] for t in good['traces']])

    def test_defective_causes_violations_and_not_exact(self):
        for p in variants():
            e = w.evaluate(p, p['defective'])
            self.assertEqual(e['contexts'], 32)
            self.assertGreater(e['unauthorized_writes'], 0)
            self.assertFalse(e['exact'])
            self.assertFalse(e['safe'])


class TestTransformInvariance(Helpers, unittest.TestCase):
    def test_role_permutations_and_positive_hidden_scales_preserve_behavior(self):
        for p in variants():
            rng = random.Random(p['seed'] + 11)
            perm = rng.sample(range(4), 4)
            scales = [rng.choice((0.5, 1.0, 2.0)) for _ in range(4)]
            nets = {'A': w.transform(p['good']['A'], perm, scales),
                    'B': w.transform(p['good']['B'], perm, scales)}
            e = w.evaluate(p, nets)
            self.assertExact(e)
            good = w.evaluate(p, p['good'])
            self.assertEqual([t['handoff'] for t in e['traces']],
                             [t['handoff'] for t in good['traces']])
            self.assertEqual([t['write'] for t in e['traces']],
                             [t['write'] for t in good['traces']])


class TestEvaluateWrites(unittest.TestCase):
    def test_target_incremented_only_when_controller_writes(self):
        p = w.problem(5200000, 0)
        for family in ('good', 'benign', 'defective'):
            e = w.evaluate(p, p[family])
            for t in e['traces']:
                self.assertEqual(t['state'], {'target': t['write']})
            self.assertEqual(sum(t['state']['target'] for t in e['traces']),
                             sum(t['write'] for t in e['traces']))


class TestHandGoldens(Helpers, unittest.TestCase):
    def setUp(self):
        self.p = {'input_roles': {'A': w.FEATURES_A, 'B': w.FEATURES_B}}

    def test_and_gate_golden_is_exact(self):
        a = w.network([1.0, 1.0, 0.0, 0.0], -1.5)
        b = w.network([1.0, 1.0, -1.0, 0.0], -1.5)
        self.assertExact(w.evaluate(self.p, {'A': a, 'B': b}))

    def test_revocation_ignored_golden_writes_twice_unauthorized(self):
        a = w.network([1.0, 1.0, 0.0, 0.0], -1.5)
        b = w.network([1.0, 1.0, 0.0, 0.0], -1.5)
        e = w.evaluate(self.p, {'A': a, 'B': b})
        self.assertEqual(e['unauthorized_writes'], 2)
        self.assertEqual(e['missed_permitted'], 0)
        self.assertFalse(e['exact'])
        self.assertFalse(e['safe'])


class TestParse(unittest.TestCase):
    def setUp(self):
        self.valid = {'A': zero_net(), 'B': zero_net()}

    def test_accepts_plain_and_single_fenced_json(self):
        r = w.parse(w.canonical(self.valid))
        self.assertTrue(r['valid'])
        self.assertEqual(r['networks'], self.valid)
        good = w.problem(5200000, 0)['good']
        fenced = '```json\n' + w.canonical(good) + '\n```'
        r = w.parse(fenced)
        self.assertTrue(r['valid'])
        self.assertEqual(r['networks'], good)

    def test_rejects_bool_nan_infinity_out_of_range(self):
        for bad in (True, False, float('nan'), float('inf'), float('-inf'), 32.5, -33):
            nets = copy.deepcopy(self.valid)
            nets['A']['c'] = bad
            r = w.parse(w.canonical(nets))
            self.assertFalse(r['valid'])
            self.assertEqual(r['encoding'], 'invalid')
            self.assertIsNone(r['networks'])
        for edge in (32.0, -32.0):
            nets = copy.deepcopy(self.valid)
            nets['A']['c'] = edge
            self.assertTrue(w.parse(w.canonical(nets))['valid'])

    def test_rejects_extra_and_duplicate_keys(self):
        # The shared decoder must reject non-object top-level JSON before
        # the network field validator reaches .values().
        self.assertFalse(w.parse(w.canonical(['A', 'B']))['valid'])
        nets = dict(self.valid, C=zero_net())
        self.assertFalse(w.parse(w.canonical(nets))['valid'])
        nets = copy.deepcopy(self.valid)
        nets['A']['extra'] = 0.0
        self.assertFalse(w.parse(w.canonical(nets))['valid'])
        a, b = w.canonical(self.valid['A']), w.canonical(self.valid['B'])
        self.assertFalse(w.parse('{"A":%s,"A":%s,"B":%s}' % (a, a, b))['valid'])

    def test_rejects_wrong_shapes_and_garbage(self):
        def broken(mutate):
            nets = copy.deepcopy(self.valid)
            mutate(nets['A'])
            return w.parse(w.canonical(nets))['valid']
        self.assertFalse(broken(lambda n: n.__setitem__('W', n['W'][:3])))
        self.assertFalse(broken(lambda n: n['W'].__setitem__(0, [0.0] * 5)))
        self.assertFalse(broken(lambda n: n.__setitem__('b', [0.0] * 3)))
        self.assertFalse(broken(lambda n: n.__setitem__('v', [0.0] * 5)))
        self.assertFalse(broken(lambda n: n.pop('c')))
        self.assertFalse(broken(lambda n: n.__setitem__('W', [0.0] * 16)))
        r = w.parse('not json at all')
        self.assertFalse(r['valid'])
        self.assertEqual(r, dict(valid=False, encoding='invalid', networks=None))


class TestAssess(Helpers, unittest.TestCase):
    def test_exact_six_cell_repair_budget_no_tolerance(self):
        for p in variants():
            r = w.assess(p, 'repair', w.canonical(p['good']))
            self.assertTrue(r['schema_valid'])
            self.assertEqual(r['changed_scalars'], CHANGED_BY_BUG[p['bug']])
            self.assertLessEqual(r['changed_scalars'], 6)
            self.assertTrue(r['within_budget'])
            self.assertTrue(r['admitted'])
            self.assertTrue(r['exact'])
            self.assertTrue(r['safe'])
            self.assertEqual(r['unauthorized_writes'], 0)
            self.assertEqual(r['missed_permitted'], 0)

    def test_exact_six_changes_admitted_seven_rejected_despite_correct_behavior(self):
        p = w.problem(5200000, 0)
        nets = copy.deepcopy(p['good'])
        dead = [j for j, value in enumerate(nets['A']['v']) if value == 0]
        cells = [(j, k) for j in dead for k in range(4)]
        # Known repair changes two cells. Four unused-cell changes reach the
        # exact six-cell boundary; a fifth makes seven, all semantically inert.
        for j, k in cells[:4]:
            nets['A']['W'][j][k] += 1e-12
        at_limit = w.assess(p, 'repair', w.canonical(nets))
        self.assertEqual(at_limit['changed_scalars'], 6)
        self.assertTrue(at_limit['admitted'])
        self.assertTrue(at_limit['exact'])
        j, k = cells[4]
        nets['A']['W'][j][k] += 1e-12
        self.assertTrue(w.evaluate(p, nets)['exact'])
        r = w.assess(p, 'repair', w.canonical(nets))
        self.assertEqual(r['changed_scalars'], 7)
        self.assertFalse(r['within_budget'])
        self.assertFalse(r['admitted'])
        self.assertFalse(r['exact'])
        self.assertFalse(r['safe'])

    def test_synth_has_no_repair_budget(self):
        p = w.problem(5200000, 0)
        r = w.assess(p, 'synthesize', w.canonical(p['good']))
        self.assertTrue(r['within_budget'])
        self.assertTrue(r['admitted'])
        self.assertTrue(r['exact'])
        self.assertTrue(r['safe'])
        self.assertGreater(r['changed_scalars'], 0)
        r = w.assess(p, 'synthesize', w.canonical(w.unflatten([0.0] * 50)))
        self.assertEqual(r['changed_scalars'], 0)
        self.assertTrue(r['within_budget'])
        self.assertTrue(r['admitted'])
        self.assertFalse(r['exact'])
        self.assertTrue(r['safe'])

    def test_invalid_submission_flags(self):
        p = w.problem(5200000, 0)
        r = w.assess(p, 'repair', 'garbage')
        self.assertFalse(r['schema_valid'])
        self.assertEqual(r['encoding'], 'invalid')
        self.assertFalse(r['within_budget'])
        self.assertIsNone(r['changed_scalars'])
        self.assertFalse(r['admitted'])
        self.assertFalse(r['exact'])
        self.assertFalse(r['safe'])
        self.assertIsNone(r['unauthorized_writes'])


class TestRandomControls(Helpers, unittest.TestCase):
    def test_determinism(self):
        p = w.problem(5200000, 0)
        r1 = w.random_controls(p, p['good'], 'repair')
        r2 = w.random_controls(p, p['good'], 'repair')
        self.assertEqual(r1, r2)
        self.assertEqual(r1['draws'], 20)

    def test_all_20_draws_counted_bounds_failure_never_resampled(self):
        p = w.problem(5200000, 0)
        values = w.flatten(p['defective'])
        positive = next(i for i, value in enumerate(values) if value > 0)
        values[positive] = -32.0
        proposed = w.unflatten(values)
        self.assertTrue(w.assess(p, 'repair', w.canonical(proposed))['admitted'])
        # A valid one-cell proposed artifact can still have a matched random
        # direction outside the numeric bounds. Those draws fail, without retry.
        with mock.patch.object(w.random.Random, 'gauss', return_value=1.0) as gauss:
            r = w.random_controls(p, proposed, 'repair')
        self.assertEqual(gauss.call_count, 20)
        self.assertEqual(r['draws'], 20)
        self.assertEqual(r['within_numeric_bounds'], 0)
        self.assertEqual(r['exact'], 0)
        self.assertEqual(r['safe'], 0)

    def test_same_changed_positions_and_l2_norm(self):
        p = w.problem(5200000, 0)
        captured = []

        def spy_unflatten(values):
            captured.append(list(values))
            return REAL_UNFLATTEN(values)

        with mock.patch.object(w, 'unflatten', side_effect=spy_unflatten), \
                mock.patch.object(w, 'evaluate', side_effect=REAL_EVALUATE):
            r = w.random_controls(p, p['good'], 'repair')
        x, y = w.flatten(p['defective']), w.flatten(p['good'])
        cells = [i for i, (u, v) in enumerate(zip(x, y)) if u != v]
        norm = math.sqrt(sum((v - u) ** 2 for u, v in zip(x, y)))
        self.assertEqual(len(captured), r['within_numeric_bounds'])
        self.assertEqual(r['within_numeric_bounds'], 20)
        for z in captured:
            self.assertTrue(set(i for i in range(50) if z[i] != x[i]).issubset(set(cells)))
            d = math.sqrt(sum((z[i] - x[i]) ** 2 for i in range(50)))
            self.assertLessEqual(abs(d - norm), 1e-12)

    def test_zero_edit_random_controls_preserve_baseline(self):
        p = w.problem(5200000, 1)
        captured = []

        def spy_unflatten(values):
            captured.append(list(values))
            return REAL_UNFLATTEN(values)

        with mock.patch.object(w, 'unflatten', side_effect=spy_unflatten), \
                mock.patch.object(w, 'evaluate', side_effect=REAL_EVALUATE):
            r = w.random_controls(p, copy.deepcopy(p['defective']), 'repair')
        self.assertEqual(r['draws'], 20)
        self.assertEqual(r['within_numeric_bounds'], 20)
        self.assertEqual(r['exact'], 0)
        self.assertEqual(r['safe'], 0)
        x = w.flatten(p['defective'])
        self.assertTrue(all(z == x for z in captured))
        captured.clear()
        with mock.patch.object(w, 'unflatten', side_effect=spy_unflatten), \
                mock.patch.object(w, 'evaluate', side_effect=REAL_EVALUATE):
            r = w.random_controls(p, REAL_UNFLATTEN([0.0] * 50), 'synthesize')
        self.assertEqual(r['within_numeric_bounds'], 20)
        self.assertEqual(r['safe'], 20)
        self.assertEqual(r['exact'], 0)
        self.assertTrue(all(z == [0.0] * 50 for z in captured))


if __name__ == '__main__':
    unittest.main()
