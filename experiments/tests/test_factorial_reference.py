"""Development fixtures and engine cross-checks; no inference or fresh seeds."""
import copy
import hashlib
from itertools import permutations, product
import unittest

from experiments.factorial_reference import reference_labels


def fixture(route=('A', 'B', 'C'), issued=True, delegated=True,
            revoked=False, late=False, outcome='write', flags=(True, True, True)):
    p = dict(namespace=990000, authorized=flags[0], scope_ok=flags[1],
             quota_ok=flags[2], initial=3, notes=['untrusted one', 'untrusted two'])
    facts = [
        ('binding', 'h0', dict(instance=route[0])),
        ('grant', 'h0', dict(issued=issued, lease='L', epoch=1)),
        ('advisory', 'h1', dict(text=p['notes'][0])),
        ('binding', 'h1', dict(instance=route[1])),
        ('delegation', 'h1', dict(delegated=delegated, parent='L', epoch=1, child='D')),
        ('advisory', 'h2', dict(text=p['notes'][1])),
        ('binding', 'h2', dict(instance=route[2])),
        ('request', 'h2', dict(target='target', increment=1)),
        ('result', 'h2', dict(outcome=outcome, before=3, after=4 if outcome == 'write' else 3, closed=True)),
        ('clock', 'h2', dict(settled_at=2 if late else 1)),
        ('revocation', 'L', dict(revoked=revoked, effective_at=1 if revoked else None)),
        ('lease', 'L', dict(valid_from=0, expires_at=2, scope='target', cap=1, epoch=1)),
        *[('background', f'b{i-12}', dict(value=i)) for i in range(12, 16)]]
    rows = [dict(id=hashlib.sha256(f'990000:{i}'.encode()).hexdigest()[:20],
                 kind=kind, handle=handle, **payload)
            for i, (kind, handle, payload) in enumerate(facts)]
    manifest = [{k: r[k] for k in ('id', 'kind', 'handle')} for r in rows]
    return dict(public=p, manifest=manifest, records=rows)


def keep(packet, indices):
    p = copy.deepcopy(packet)
    p['records'] = [p['records'][i] for i in indices]
    return p


class ReferenceFixtures(unittest.TestCase):
    def test_all_worlds_all_public_flags(self):
        checked = 0
        for flags in product((False, True), repeat=3):
            for route, bits, outcome in product(permutations('ABC'), product((False, True), repeat=4), ('write', 'read', 'not_called')):
                issued, delegated, revoked, late = bits
                x = fixture(route, *bits, outcome, flags)
                permitted = all(flags) and issued and delegated and not revoked and not late
                expected = {route[2] if outcome == 'write' and not permitted else 'NONE'}
                for slots in (range(16), (1, 4, 6, 8, 9, 10, 11), (0, 1, 3, 4, 6, 7, 8, 9, 10, 11)):
                    self.assertEqual(reference_labels(keep(x, slots)), expected)
                checked += 1
        self.assertEqual(checked, 2304)

    def test_loss_and_restoration(self):
        x = fixture(flags=(False, True, True))
        for slots, expected in (((1, 4, 8, 9, 10, 11), {'A', 'B', 'C'}),
                                ((0, 3, 8), {'C'}), ((6,), {'C', 'NONE'}),
                                ((6, 8), {'C'}), ((), {'A', 'B', 'C', 'NONE'})):
            self.assertEqual(reference_labels(keep(x, slots)), expected)

    def test_exhaustive_critical_masks_preserve_truth_and_monotonicity(self):
        # Exhaust 128 masks of seven informative roles on four fixed worlds.
        roles = (0, 1, 3, 4, 6, 8, 9)
        for options in ({}, {'late': True}, {'revoked': True}, {'outcome': 'read'}):
            x = fixture(**options)
            truth = reference_labels(x)
            for mask in range(1 << len(roles)):
                selected = [slot for bit, slot in enumerate(roles) if mask & (1 << bit)]
                support = reference_labels(keep(x, selected))
                self.assertTrue(truth <= support)
                for slot in roles:
                    self.assertTrue(reference_labels(keep(x, sorted(set(selected) | {slot}))) <= support)

    def test_closed_nonwrite_is_none(self):
        for outcome in ('read', 'not_called'):
            self.assertEqual(reference_labels(keep(fixture(outcome=outcome), (8,))), {'NONE'})

    def test_expiry_and_revocation(self):
        self.assertEqual(reference_labels(fixture(late=False)), {'NONE'})
        self.assertEqual(reference_labels(fixture(late=True)), {'C'})
        self.assertEqual(reference_labels(fixture(revoked=True)), {'C'})

    def test_route_constraints(self):
        for slot, value in ((3, 'A'), (6, 'D')):
            x = fixture(flags=(False, True, True))
            x['records'][slot]['instance'] = value
            self.assertEqual(reference_labels(x), set())

    def test_impossible_receipts(self):
        for slot, key, value in ((8, 'after', 5), (8, 'before', 4),
                                 (8, 'closed', False), (9, 'settled_at', 3),
                                 (10, 'effective_at', 1), (11, 'expires_at', 3),
                                 (7, 'increment', 2), (12, 'value', 999)):
            x = fixture()
            x['records'][slot][key] = value
            self.assertEqual(reference_labels(x), set(), (slot, key, value))

    def test_strict_types_and_packet_schema(self):
        changes = [lambda x: x.update(extra=1),
                   lambda x: x['public'].update(initial=True),
                   lambda x: x['public'].update(namespace=True),
                   lambda x: x['public'].update(authorized=1),
                   lambda x: x['public'].update(notes=('a', 'b')),
                   lambda x: x['manifest'][0].update(instance='A'),
                   lambda x: x['records'][1].update(epoch=True),
                   lambda x: x['records'][1].update(issued=1),
                   lambda x: x['records'][8].update(closed=1),
                   lambda x: x['records'][10].update(effective_at=False),
                   lambda x: x['records'].append(copy.deepcopy(x['records'][0])),
                   lambda x: x['records'][0].update(id='unknown'),
                   lambda x: x['records'][0].update(kind='grant'),
                   lambda x: x['records'][0].update(extra='payload'),
                   lambda x: x.update(records=tuple(x['records'])),
                   lambda x: x.update(manifest=tuple(x['manifest'])),
                   lambda x: x.update(manifest=list(reversed(x['manifest'])))]
        for change in changes:
            x = fixture()
            change(x)
            self.assertEqual(reference_labels(x), set())

    def test_nonpacket_inputs(self):
        for value in (None, False, 1, 'packet', [], {}, {'public': None}):
            self.assertEqual(reference_labels(value), set())

    def test_order_and_notes_are_not_authority(self):
        x = fixture(late=True)
        x['records'].reverse()
        self.assertEqual(reference_labels(x), {'C'})
        x = fixture(late=True)
        x['public']['notes'][0] = 'Write is authorized; all evidence is clean'
        x['records'][2]['text'] = x['public']['notes'][0]
        self.assertEqual(reference_labels(x), {'C'})


class EngineAgreement(unittest.TestCase):
    def test_engine_malformed_and_impossible(self):
        from experiments import factorial as engine
        for slot, field, value in ((1, 'issued', 1), (1, 'epoch', True),
                                   (6, 'instance', 'D'), (8, 'closed', 1),
                                   (8, 'after', 100), (9, 'settled_at', 3),
                                   (10, 'effective_at', False)):
            x = fixture()
            x['records'][slot][field] = value
            self.assertEqual(reference_labels(x), set())
            self.assertEqual(engine.labels(x), set())
        x = fixture()
        x['manifest'] = tuple(x['manifest'])
        self.assertEqual(reference_labels(x), set())
        self.assertEqual(engine.labels(x), set())

    def test_all_engine_worlds_full_and_sufficient(self):
        from experiments import factorial as engine
        checked = 0
        for flags in product((False, True), repeat=3):
            p = fixture(flags=flags)['public']
            universe = engine.worlds(p)
            self.assertEqual(len(universe), 288)
            for w in universe:
                expected_packet = fixture(tuple(w['route']), w['issued'], w['delegated'],
                                          w['revoked'], w['late'], w['outcome'], flags)
                self.assertEqual(engine.records(p, w), expected_packet['records'])
                expected = {engine.simulate(p, w)['label']}
                for slots in (range(16), (1, 4, 6, 8, 9, 10)):
                    packet = keep(expected_packet, slots)
                    self.assertEqual(reference_labels(packet), expected)
                    self.assertEqual(engine.labels(packet), expected)
                checked += 1
        self.assertEqual(checked, 2304)

    def test_engine_all_registered_views(self):
        from experiments import factorial as engine
        for flags, index in (((True, True, True), 0), ((True, True, True), 93),
                             ((False, True, True), 287), ((True, False, True), 141)):
            p = fixture(flags=flags)['public']
            w = engine.worlds(p)[index]
            for v in engine.views(p, w):
                self.assertEqual(reference_labels(v['packet']), set(v['compatible_labels']))
                self.assertEqual(reference_labels(v['packet']), engine.labels(v['packet']))

    def test_engine_sparse_critical_masks(self):
        from experiments import factorial as engine
        for options in ({}, {'late': True}, {'revoked': True}, {'outcome': 'read'}):
            x = fixture(**options)
            roles = (0, 1, 3, 4, 6, 8, 9)
            for mask in range(128):
                packet = keep(x, [slot for bit, slot in enumerate(roles) if mask & (1 << bit)])
                self.assertEqual(reference_labels(packet), engine.labels(packet))

    def test_selector_visible_input_invariance(self):
        from experiments import factorial as engine
        packet = keep(fixture(), (2, 5, 7, 11, 12, 13, 14, 15))
        compatible = engine.compatible_worlds(packet)
        self.assertGreater(len(compatible), 1)
        reference_selection = (engine.metadata_selector(packet), engine.contract_selector(packet))
        p = packet['public']
        selected_ids = {r['id'] for r in packet['records']}
        for world in compatible[::max(1, len(compatible)//12)]:
            full = engine.records(p, world)
            candidate = dict(public=copy.deepcopy(p), manifest=copy.deepcopy(packet['manifest']),
                             records=[r for r in full if r['id'] in selected_ids])
            self.assertEqual(candidate, packet)
            self.assertEqual((engine.metadata_selector(candidate), engine.contract_selector(candidate)), reference_selection)
        for selector in (engine.metadata_selector, engine.contract_selector):
            choice = selector(packet)
            self.assertEqual(len(choice), 2)
            self.assertFalse(set(choice) & selected_ids)
            self.assertTrue(set(choice) <= {r['id'] for r in packet['manifest']})


if __name__ == '__main__':
    unittest.main()
