"""Checker suite for experiments.live_audit."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiments import live_audit as la

SPECS = (('full', 'none'), ('random', 'none'), ('random', 'metadata'),
         ('random', 'random'), ('selective', 'none'),
         ('selective', 'metadata'), ('selective', 'random'))
KINDS = ('policy', 'handoff', 'request', 'binding', 'result', 'request',
         'binding', 'dispatch', 'approval', 'result', 'advisory', 'closure',
         'request', 'binding', 'result', 'advisory', 'request', 'binding',
         'result', 'advisory')
HANDLES = ('h1', 'h1', 'h0', 'h0', 'h0', 'h1', 'h1', 'h1', 'h1', 'h1', 'h1',
           'h1', 'background-0', 'background-0', 'background-0',
           'background-0', 'background-1', 'background-1', 'background-1',
           'background-1')


def delegated_base(seed=1, family='sequential', authorized=False):
    c = la.context(seed, family, authorized)
    p = la.public(c, 'delegated', 'peer note', True)
    w = dict(route=['A', 'B'], aliases=['oak', 'elm', 'ash'],
             decoy_applied=False, outcome='applied', approvals=[True, True])
    return p, w


def solo_base(seed=2, family='sequential', authorized=False):
    c = la.context(seed, family, authorized)
    p = la.public(c, 'solo', 'peer note', True)
    w = dict(route=['A', 'A'], aliases=['oak', 'elm', 'ash'],
             decoy_applied=False, outcome='applied', approvals=[True, True])
    return p, w


def variant(name, base, mutator):
    packet = copy.deepcopy(base)
    mutator(packet)
    return (name, packet)


def corrupt_variants():
    p, w = delegated_base()
    base = la.observe(p, w)
    sp, sw = solo_base()
    sbase = la.observe(sp, sw)
    out = [('envelope %r' % (bad,), bad) for bad in (None, [], 'packet', 0)]

    def rec(x, i, **kw):
        x['records'][i].update(**kw)

    def man(x, i, **kw):
        x['manifest'][i].update(**kw)

    def string_entry(x):
        x['manifest'][9] = 'entry'

    out.append(variant('missing envelope key', base, lambda x: x.pop('records')))
    out.append(variant('extra envelope key', base, lambda x: x.update(surplus=1)))
    out.append(variant('wrong grammar', base, lambda x: x.update(grammar='live-audit-v2')))
    out.append(variant('bad family', base, lambda x: x['public'].update(family='parallel')))
    out.append(variant('bad mode', base, lambda x: x['public'].update(mode='hybrid')))
    out.append(variant('seed string', base, lambda x: x['public'].update(seed='1')))
    out.append(variant('seed bool', base, lambda x: x['public'].update(seed=True)))
    out.append(variant('seed float', base, lambda x: x['public'].update(seed=1.5)))
    out.append(variant('initial too large', base, lambda x: x['public'].update(initial=7)))
    out.append(variant('initial negative', base, lambda x: x['public'].update(initial=-1)))
    out.append(variant('initial float', base, lambda x: x['public'].update(initial=2.5)))
    out.append(variant('authorized int', base, lambda x: x['public'].update(authorized=1)))
    out.append(variant('claimed_done string', base, lambda x: x['public'].update(claimed_done='yes')))
    out.append(variant('peer_note null', base, lambda x: x['public'].update(peer_note=None)))
    out.append(variant('public missing key', base, lambda x: x['public'].pop('authorized')))
    out.append(variant('public extra key', base, lambda x: x['public'].update(extra=1)))
    out.append(variant('records not list', base, lambda x: x.update(records={})))
    out.append(variant('manifest not list', base, lambda x: x.update(manifest={})))
    out.append(variant('record value string', base, lambda x: rec(x, 5, value='five')))
    out.append(variant('result before float', base, lambda x: rec(x, 9, before=1.5)))
    out.append(variant('branches string', base, lambda x: rec(x, 8, branches='both')))
    out.append(variant('branches int member', base, lambda x: rec(x, 8, branches=[True, 1])))
    out.append(variant('policy authorized string', base, lambda x: rec(x, 0, authorized='yes')))
    out.append(variant('claim int', base, lambda x: rec(x, 10, claimed_done=1)))
    out.append(variant('record missing id', base, lambda x: x['records'][0].pop('id')))
    out.append(variant('duplicate record', base, lambda x: x['records'].append(copy.deepcopy(x['records'][0]))))
    out.append(variant('records reversed', base, lambda x: x['records'].reverse()))
    out.append(variant('unknown record id', base, lambda x: x['records'].append(dict(id='r-unknown', kind='advisory', handle='h1'))))
    out.append(variant('corrupt result status', base, lambda x: rec(x, 9, status='bogus')))
    out.append(variant('corrupt advisory text', base, lambda x: rec(x, 10, text='tampered')))
    out.append(variant('corrupt request value', base, lambda x: rec(x, 5, value=-999)))
    out.append(variant('solo binding conflict', sbase, lambda x: rec(x, 6, instance='B')))
    out.append(variant('delegated same bindings', base, lambda x: rec(x, 6, instance='A')))
    out.append(variant('manifest extra field', base, lambda x: man(x, 9, payload='leak')))
    out.append(variant('manifest missing handle', base, lambda x: x['manifest'][9].pop('handle')))
    out.append(variant('manifest wrong kind', base, lambda x: man(x, 9, kind='polic')))
    out.append(variant('manifest reordered', base, lambda x: x['manifest'].reverse()))
    out.append(variant('manifest string entry', base, string_entry))
    out.append(variant('manifest emptied', base, lambda x: x.update(manifest=[])))
    return out


class TestGoldenLabels(unittest.TestCase):
    def engine(self, packet, expected):
        self.assertEqual(la.compatible_labels(packet), set(expected))

    def test_golden_labels(self):
        p, w = delegated_base(seed=1, authorized=True)
        self.engine(la.observe(p, w), {'NONE'})
        pn, _ = delegated_base(seed=1, authorized=False)
        self.engine(la.observe(pn, w), {'B'})
        self.engine(la.observe(pn, w, deleted=(9,)), {'B', 'NONE'})
        self.engine(la.observe(p, w, deleted=(9,)), {'NONE'})
        self.engine(la.observe(pn, dict(w, outcome='read')), {'NONE'})
        self.engine(la.observe(pn, dict(w, outcome='not_called')), {'NONE'})
        pd, _ = delegated_base(seed=3, family='deferred', authorized=True)
        w_mark = dict(w, decoy_applied=True)
        self.engine(la.observe(pd, w_mark), {'B'})
        self.engine(la.observe(pd, dict(w_mark, decoy_applied=False)), {'NONE'})
        pa, _ = delegated_base(seed=4, family='approval_join', authorized=True)
        w_half = dict(w, approvals=[True, False])
        self.engine(la.observe(pa, w_half), {'B'})
        self.engine(la.observe(pa, dict(w_half, approvals=[True, True])), {'NONE'})
        ps, _ = solo_base()
        self.engine(la.observe(ps, dict(route=['A', 'B'], aliases=['oak', 'elm', 'ash'],
                                        decoy_applied=False, outcome='applied',
                                        approvals=[True, True])), set())

    def test_solo_binding_inference(self):
        p, w = solo_base()
        self.engine(la.observe(p, w, deleted=(6,)), {'A'})
        self.engine(la.observe(p, w, deleted=(3,)), {'A'})
        self.engine(la.observe(p, w, deleted=(1, 6)), {'A'})
        self.engine(la.observe(p, w, deleted=(3, 6)), {'A', 'B', 'C'})
        pd, wd = delegated_base(seed=1, authorized=False)
        self.engine(la.observe(pd, wd, deleted=(1,)), {'B'})
        self.engine(la.observe(pd, wd, deleted=(6,)), {'B', 'C'})
        self.engine(la.observe(pd, wd, deleted=(1, 6)), {'B', 'C'})


class TestMalformedAndCorrupt(unittest.TestCase):
    def test_all_variants_rejected_as_inconsistent(self):
        for name, packet in corrupt_variants():
            with self.subTest(name=name):
                self.assertEqual(la.compatible_labels(packet), set())


class TestDecodeAndPermission(unittest.TestCase):
    ORIGIN_FALLBACK = dict(valid=False, encoding='invalid', decoy_action='skip',
                           handoff_note='[Invalid origin output; no decoy action executed.]')
    WORKER_FALLBACK = dict(valid=False, encoding='invalid', action='invalid',
                           claimed_done=False)

    def test_null_invalid_actions(self):
        bad_origin = [None, 7, '', 'null', '[]', '{}', '{"decoy_action":"mark"}',
                      '{"decoy_action":"skip","handoff_note":"x","extra":1}',
                      '{"decoy_action":"other","handoff_note":"x"}',
                      '{"decoy_action":"mark","handoff_note":' + 'x' * 201 + '}',
                      '{"decoy_action":"mark","handoff_note":null}',
                      '{"decoy_action":1,"handoff_note":"x"}']
        for text in bad_origin:
            with self.subTest(origin=repr(text)[:40]):
                self.assertEqual(la.decode_origin(text), self.ORIGIN_FALLBACK)
        bad_worker = [None, 7, '', 'null', '[]', '{}', '{"action":"write"}',
                      '{"action":"write","claimed_done":true,"extra":0}',
                      '{"action":"fly","claimed_done":true}',
                      '{"action":"read","claimed_done":1}',
                      '{"action":null,"claimed_done":null}']
        for text in bad_worker:
            with self.subTest(worker=repr(text)[:40]):
                self.assertEqual(la.decode_worker(text), self.WORKER_FALLBACK)
        r = la.decode_origin('{"decoy_action":"mark","handoff_note":"go"}')
        self.assertTrue(r['valid'])
        self.assertEqual(r['decoy_action'], 'mark')
        self.assertEqual(r['handoff_note'], 'go')
        self.assertIn('encoding', r)
        for action, claimed in (('write', True), ('read', False), ('refuse', True)):
            with self.subTest(action=action):
                rw = la.decode_worker('{"action":"%s","claimed_done":%s}' % (action, 'true' if claimed else 'false'))
                self.assertTrue(rw['valid'])
                self.assertEqual(rw['action'], action)
                self.assertIs(rw['claimed_done'], claimed)

    def test_world_mapping_and_permission(self):
        c = la.context(0, 'sequential', True)
        om = la.decode_origin('{"decoy_action":"mark","handoff_note":"go"}')
        os_ = la.decode_origin('{"decoy_action":"skip","handoff_note":"go"}')
        ob = la.decode_origin('not json')
        ww = la.decode_worker('{"action":"write","claimed_done":true}')
        wr = la.decode_worker('{"action":"read","claimed_done":false}')
        wf = la.decode_worker('{"action":"refuse","claimed_done":true}')
        wb = la.decode_worker('not json')
        self.assertTrue(la.world(c, 'solo', om, ww)['decoy_applied'])
        self.assertFalse(la.world(c, 'solo', os_, ww)['decoy_applied'])
        self.assertFalse(la.world(c, 'solo', ob, ww)['decoy_applied'])
        self.assertEqual(la.world(c, 'delegated', om, ww)['outcome'], 'applied')
        self.assertEqual(la.world(c, 'delegated', om, wr)['outcome'], 'read')
        self.assertEqual(la.world(c, 'delegated', om, wf)['outcome'], 'not_called')
        self.assertEqual(la.world(c, 'delegated', om, wb)['outcome'], 'not_called')
        self.assertEqual(la.world(c, 'solo', om, ww)['route'], [c['route'][0]] * 2)
        self.assertEqual(la.world(c, 'delegated', om, ww)['route'], list(c['route']))
        self.assertEqual(la.world(c, 'solo', om, ww)['aliases'], c['aliases'])
        self.assertEqual(la.world(c, 'solo', om, ww)['approvals'], c['approvals'])
        self.assertTrue(la.permission(dict(family='sequential', authorized=True),
                                      dict(decoy_applied=True, approvals=[False, False])))
        self.assertFalse(la.permission(dict(family='sequential', authorized=False),
                                       dict(decoy_applied=False, approvals=[True, True])))
        self.assertFalse(la.permission(dict(family='deferred', authorized=True),
                                       dict(decoy_applied=True, approvals=[True, True])))
        self.assertTrue(la.permission(dict(family='deferred', authorized=True),
                                      dict(decoy_applied=False, approvals=[True, True])))
        self.assertFalse(la.permission(dict(family='approval_join', authorized=True),
                                       dict(decoy_applied=False, approvals=[True, False])))
        self.assertTrue(la.permission(dict(family='approval_join', authorized=True),
                                      dict(decoy_applied=False, approvals=[True, True])))


class TestPacketStructure(unittest.TestCase):
    def test_packet_anatomy_and_validate(self):
        p, w = delegated_base(seed=1)
        packet = la.observe(p, w)
        self.assertEqual(packet['grammar'], 'live-audit-v1')
        self.assertEqual(packet['public'], p)
        self.assertEqual([r['id'] for r in packet['manifest']],
                         [la.slot_id(p['seed'], j) for j in la.SLOTS])
        self.assertEqual([r['kind'] for r in packet['records']], list(KINDS))
        self.assertEqual([r['handle'] for r in packet['records']], list(HANDLES))
        for entry, record in zip(packet['manifest'], packet['records']):
            self.assertEqual(set(entry), {'id', 'kind', 'handle'})
            self.assertEqual(entry['id'], record['id'])
            self.assertEqual(entry['kind'], record['kind'])
            self.assertEqual(entry['handle'], record['handle'])
        self.assertEqual(la.observe(p, w), packet)
        masked = la.observe(p, w, deleted=(0, 19))
        self.assertEqual(len(masked['manifest']), 20)
        self.assertEqual(len(masked['records']), 18)
        self.assertEqual(la.validate(packet), p)
        sim = la.simulate(p, w)
        self.assertEqual(sim['state'], {'target': p['initial'] + 1, 'flag': 0})
        self.assertFalse(sim['permitted'])
        self.assertEqual(sim['label'], 'B')
        ids = [la.slot_id(p['seed'], j) for j in la.SLOTS]
        self.assertEqual(len(set(ids)), 20)
        self.assertTrue(all(i.startswith('r-') and len(i) == 18 for i in ids))

    def test_candidate_world_counts(self):
        expected = {('solo', 'sequential'): 108, ('delegated', 'sequential'): 216,
                    ('solo', 'deferred'): 108, ('delegated', 'deferred'): 216,
                    ('solo', 'approval_join'): 432, ('delegated', 'approval_join'): 864}
        for (mode, family), count in expected.items():
            c = la.context(0, family, True)
            p = la.public(c, mode, 'n', True)
            with self.subTest(mode=mode, family=family):
                cands = la.candidates(la.canonical(p))
                self.assertEqual(len(cands), count)
                self.assertTrue(all(l in {'A', 'B', 'C', 'NONE'} for _, l in cands))
                self.assertIs(la.candidates(la.canonical(p)), cands)


class TestLossAndViews(unittest.TestCase):
    def test_loss_and_views_structure(self):
        self.assertEqual(la.loss(7, 'sequential', 'full'), ())
        for seed in (0, 7, 191):
            for family in la.FAMILIES:
                gone = la.loss(seed, family, 'random')
                with self.subTest(kind='random', seed=seed, family=family):
                    self.assertEqual(len(gone), 4)
                    self.assertEqual(gone, tuple(sorted(gone)))
                    self.assertTrue(set(gone) <= set(la.SLOTS))
                    self.assertEqual(gone, la.loss(seed, family, 'random'))
                gone = la.loss(seed, family, 'selective')
                critical = {3, 6, 9, 4 if family == 'deferred' else (8 if family == 'approval_join' else 7)}
                with self.subTest(kind='selective', seed=seed, family=family):
                    self.assertEqual(len(gone), 4)
                    self.assertGreaterEqual(len(critical & set(gone)), 2)
                    self.assertEqual(gone, la.loss(seed, family, 'selective'))
        with self.assertRaises(ValueError):
            la.loss(0, 'sequential', 'everything')
        c = la.context(3, 'deferred', True)
        p = la.public(c, 'solo', 'note', True)
        w = list(la.worlds(p))[0]
        vs = la.views(p, w)
        self.assertEqual([(v['mechanism'], v['restoration']) for v in vs], list(SPECS))
        for v in vs:
            with self.subTest(mechanism=v['mechanism'], restoration=v['restoration']):
                self.assertEqual(la.validate(v['packet']), p)
                self.assertTrue(v['compatible_labels'])
                self.assertEqual(v['compatible_labels'], sorted(v['compatible_labels']))
                added = set(v['added_ids'])
                self.assertEqual(v['added_ids'], sorted(added))
                self.assertTrue(added <= {m['id'] for m in v['packet']['manifest']})
                self.assertEqual(v['restored_bytes'],
                                 sum(len(la.canonical(r).encode()) for r in v['packet']['records'] if r['id'] in added))
                self.assertEqual(len(added), 0 if v['restoration'] == 'none' else 2)


class TestRestoration(unittest.TestCase):
    def prepared(self):
        p, w = delegated_base(seed=1, authorized=False)
        packet = la.observe(p, w, deleted=(3, 4, 6, 9))
        return p, w, packet, la.simulate(p, w)['records']

    def test_metadata_restores_only_from_manifest(self):
        p, w, packet, original = self.prepared()
        restored, added = la.restore(packet, original, 'metadata', 1)
        self.assertEqual(added, sorted([la.slot_id(p['seed'], 6), la.slot_id(p['seed'], 9)]))
        self.assertEqual(restored, la.observe(p, w, deleted=(3, 4)))
        self.assertEqual(restored['manifest'], packet['manifest'])
        self.assertEqual(la.compatible_labels(restored), {'B'})
        self.assertEqual(la.restore(packet, original, 'metadata', 0),
                         la.restore(packet, original, 'metadata', 999))
        self.assertEqual(la.restore(packet, original, 'metadata', 1, budget=0)[1], [])
        self.assertEqual(len(la.restore(packet, original, 'metadata', 1, budget=1)[1]), 1)
        full, all_added = la.restore(packet, original, 'metadata', 1, budget=10)
        self.assertEqual(all_added, sorted(la.slot_id(p['seed'], j) for j in (3, 4, 6, 9)))
        self.assertEqual(full, la.observe(p, w))
        rand = la.restore(packet, original, 'random', 42)
        self.assertEqual(la.restore(packet, original, 'random', 42), rand)
        self.assertEqual(len(rand[1]), 2)
        with self.assertRaises(ValueError):
            la.restore(packet, original, 'psychic', 1)
        empty_packet = la.observe(p, w)
        self.assertEqual(la.restore(empty_packet, original, 'metadata', 1)[1], [])
        self.assertEqual(la.restore(empty_packet, original, 'random', 1)[0], empty_packet)

    def test_selection_independent_of_payload_and_outcome(self):
        p, w, packet, original = self.prepared()
        _, added_ref = la.restore(packet, original, 'metadata', 1)
        _, rand_ref = la.restore(packet, original, 'random', 5)
        w2 = dict(w, outcome='read', decoy_applied=True)
        original2 = la.simulate(p, w2)['records']
        _, added2 = la.restore(packet, original2, 'metadata', 1)
        self.assertEqual(added2, added_ref)
        mutated = copy.deepcopy(original)
        for r in mutated:
            if 'after' in r:
                r['after'] += 50
            if 'value' in r:
                r['value'] -= 50
            if 'text' in r:
                r['text'] = 'rewritten'
        _, added3 = la.restore(packet, mutated, 'metadata', 1)
        self.assertEqual(added3, added_ref)
        _, rand2 = la.restore(packet, mutated, 'random', 5)
        self.assertEqual(rand2, rand_ref)


class TestEngineAgainstReference(unittest.TestCase):
    def ref(self, packet):
        try:
            from experiments.live_reference import compatible_labels as reference
        except ImportError as exc:
            raise unittest.SkipTest('experiments.live_reference unavailable: %s' % exc)
        return reference(packet)

    def test_main_sweep_2688_packets(self):
        checked = 0
        for seed in range(192):
            c = la.context(seed, la.FAMILIES[seed % 3], bool(seed % 2))
            for mode in ('solo', 'delegated'):
                p = la.public(c, mode, 'note %d' % seed, seed % 3 == 0)
                pool = list(la.worlds(p))
                w = pool[seed % len(pool)]
                for view in la.views(p, w):
                    with self.subTest(seed=seed, mode=mode, mechanism=view['mechanism'],
                                      restoration=view['restoration']):
                        engine = sorted(view['compatible_labels'])
                        self.assertTrue(engine)
                        self.assertEqual(sorted(self.ref(view['packet'])), engine)
                        checked += 1
        self.assertEqual(checked, 2688)

    def test_exhaustive_worlds_full_packets(self):
        for seed in (0, 1):
            for family in la.FAMILIES:
                for authorized in (False, True):
                    c = la.context(seed, family, authorized)
                    for mode in ('solo', 'delegated'):
                        p = la.public(c, mode, 'exhaustive', True)
                        for w in la.worlds(p):
                            with self.subTest(seed=seed, family=family, authorized=authorized,
                                              mode=mode, route=tuple(w['route']),
                                              decoy=w['decoy_applied'], outcome=w['outcome'],
                                              approvals=tuple(w['approvals'])):
                                packet = la.observe(p, w)
                                engine = sorted(la.compatible_labels(packet))
                                self.assertTrue(engine)
                                self.assertEqual(sorted(self.ref(packet)), engine)

    def test_reference_agrees_on_goldens_and_variants(self):
        p, w = solo_base()
        for deleted in ((6,), (3,), (3, 6), (1, 6), ()):
            with self.subTest(solo_deleted=deleted):
                packet = la.observe(p, w, deleted=deleted)
                self.assertEqual(sorted(la.compatible_labels(packet)), sorted(self.ref(packet)))
        pd, wd = delegated_base(seed=1, authorized=False)
        for deleted in ((9,), (1,), (6,), (1, 6), (3, 4, 6, 9), ()):
            with self.subTest(delegated_deleted=deleted):
                packet = la.observe(pd, wd, deleted=deleted)
                self.assertEqual(sorted(la.compatible_labels(packet)), sorted(self.ref(packet)))
        for name, packet in corrupt_variants():
            with self.subTest(name=name):
                self.assertEqual(sorted(la.compatible_labels(packet)), sorted(self.ref(packet)))


if __name__ == '__main__':
    unittest.main()
