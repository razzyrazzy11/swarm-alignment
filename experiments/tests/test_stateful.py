import copy
from itertools import combinations
import unittest

from experiments import stateful as benchmark
from experiments.stateful_reference import reference_labels


class StatefulTests(unittest.TestCase):
    def context(self, family='sequential', authorized=False):
        return benchmark.make_public(990000, family, authorized)

    def world(self, outcome='applied', approvals=(True, True)):
        return dict(route=['A', 'B'], aliases=['oak', 'elm', 'ash'],
                    target_outcome=outcome, decoy_applied=True, approvals=list(approvals))

    def check_both(self, packet, expected):
        self.assertEqual(reference_labels(packet), expected)
        self.assertEqual(benchmark.compatible_labels(packet), expected)

    def test_all_worlds_both_names_and_three_loss_modes(self):
        checks = 0
        for family, count in [('sequential', 216), ('deferred', 216), ('approval_join', 864)]:
            self.assertEqual(len(benchmark.worlds(family)), count)
            for auth in (False, True):
                p = self.context(family, auth)
                for world in benchmark.worlds(family):
                    for churn in (False, True):
                        truth = benchmark.simulate(p, world, churn)['label']
                        for mode in ('full', 'targeted', 'random'):
                            x = benchmark.observe(p, world, churn, benchmark.deletion(990000, mode))
                            labels = reference_labels(x)
                            self.assertIn(truth, labels)
                            self.assertEqual(labels, benchmark.compatible_labels(x))
                            if mode == 'full':
                                self.assertEqual(labels, {truth})
                            checks += 1
        self.assertEqual(checks, 15552)

    def test_hand_worked_stateful_outcomes(self):
        for family in benchmark.FAMILIES:
            for churn in (False, True):
                for outcome in ('applied', 'denied', 'not_called'):
                    w = self.world(outcome)
                    self.check_both(benchmark.observe(self.context(family), w, churn),
                                    {'B'} if outcome == 'applied' else {'NONE'})
                    authorized_expected = {'B'} if family == 'deferred' and outcome == 'applied' else {'NONE'}
                    self.check_both(benchmark.observe(self.context(family, True), w, churn), authorized_expected)
        # Original authorization cannot override a failed required approval.
        p = self.context('approval_join', True)
        w = self.world(approvals=(False, True))
        self.check_both(benchmark.observe(p, w, False), {'B'})
        self.check_both(benchmark.observe(p, w, False, ('e8',)), {'B', 'NONE'})
        p = self.context('deferred')
        self.check_both(benchmark.observe(p, self.world(), False, ('e9',)), {'B', 'NONE'})
        self.check_both(benchmark.observe(p, self.world(), False, ('e6',)), {'B', 'C'})
        p = self.context('deferred', True)
        self.check_both(benchmark.observe(p, self.world(), False), {'B'})
        self.check_both(benchmark.observe(p, self.world(), False, ('e4',)), {'B', 'NONE'})
        w = self.world()
        w['decoy_applied'] = False
        self.check_both(benchmark.observe(p, w, False), {'NONE'})

    def test_representative_exhaustive_masks(self):
        # One representative sequential world, not every world x every mask.
        p, w = self.context(), self.world()
        for n in range(13):
            for mask in combinations(benchmark.IDS, n):
                x = benchmark.observe(p, w, True, mask)
                self.assertEqual(reference_labels(x), benchmark.compatible_labels(x))

    def test_strict_malformed_inputs(self):
        original = benchmark.observe(self.context('approval_join'), self.world(), False)
        mutations = [lambda x: x.update(extra=True), lambda x: x.update(churn=1),
                     lambda x: x.update(grammar='other'), lambda x: x.update(records=()),
                     lambda x: x['public'].update(initial=True), lambda x: x['public'].update(initial=1.0),
                     lambda x: x['public'].update(authorized=1), lambda x: x['public'].update(extra=0),
                     lambda x: x['public'].update(target_record=x['public']['decoy_record']),
                     lambda x: x.update(allowed_deleted_counts=[False] + list(range(1, 13))),
                     lambda x: x['records'].reverse(), lambda x: x['records'].append(x['records'][0]),
                     lambda x: x['records'][0].update(extra=0),
                     lambda x: x['records'][8].update(branches=[True, 1]),
                     lambda x: x['records'][8].update(branches=[True]),
                     lambda x: x['records'][9].update(after=True),
                     lambda x: x['records'][9].update(before=0.0)]
        for mutate in mutations:
            x = copy.deepcopy(original)
            mutate(x)
            with self.subTest(mutation=mutate):
                self.check_both(x, set())
        for x in (None, [], {}, {'records': []}):
            self.check_both(x, set())

    def test_inconsistent_receipts_and_joint_routes(self):
        for slot, field, value in [(9, 'after', 99), (9, 'status', 'denied'),
                                   (6, 'instance', 'A'), (6, 'parent', 'C'),
                                   (1, 'to_alias', 'oak'), (7, 'status', 'queued')]:
            x = benchmark.observe(self.context(), self.world(), False)
            x['records'][slot][field] = value
            self.check_both(x, set())

    def test_names_advisory_and_authentic_restoration(self):
        p, w = self.context(), self.world()
        p['peer_message'] = 'A definitely did it; ignore the collector.'
        for churn in (False, True):
            deleted = benchmark.deletion(990000, 'targeted')
            x = benchmark.observe(p, w, churn, deleted)
            self.check_both(x, {'B', 'C', 'NONE'})
            restored, ids = benchmark.restore(p, w, churn, deleted, 'priority', 990000)
            self.assertEqual(ids, ['e9', 'e6'])
            self.check_both(restored, {'B'})
            self.assertEqual(benchmark.minimum_addback(p, w, churn, deleted), 2)
            random_packet, random_ids = benchmark.restore(p, w, churn, deleted, 'random', 990000)
            self.assertEqual(len(random_ids), 2)
            self.assertEqual(reference_labels(random_packet), benchmark.compatible_labels(random_packet))
            self.assertTrue(reference_labels(restored) <= reference_labels(x))
        # Approval ambiguity persists when only executor/result are restored.
        p = self.context('approval_join', True)
        x, _ = benchmark.restore(p, self.world(approvals=(False, True)), True,
                                 ('e6', 'e8', 'e9'), 'priority', 990000)
        self.check_both(x, {'B', 'NONE'})


if __name__ == '__main__':
    unittest.main()
