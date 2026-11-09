"""Host policy, packet boundaries, and exact restoration-prior regression checks."""
from copy import deepcopy
from itertools import combinations, product
import json
import unittest

from experiments import swarm_ledger as e


def policy(budget=3, start=0, width=5):
    return dict(namespace='nonce-test-7b9a', budget=budget, local_cap_x=2,
                local_cap_y=2, lease_start=start, lease_end=start+width,
                target_closed=True, workers=list(e.WORKERS))


def world(**kw):
    return dict(dict(issued=True, gx=True, gy=True, dx=2, dy=2, time_y=0,
                     revoked=False, y_worker='D', x_worker='B', notes=['']*5), **kw)


class LedgerTests(unittest.TestCase):
    def test_host_actual_consumption_and_target_scope(self):
        p=policy()
        for issued,gx in product((False,True), repeat=2):
            s=e.simulate(p,world(issued=issued,gx=gx))
            self.assertEqual(s['shared_after'],4)
            self.assertTrue(s['unauthorized_y'])
            self.assertEqual(s['label'],'D')
        self.assertEqual(e.simulate(p,world(issued=False,dy=0))['label'],'NONE')
        self.assertEqual(e.simulate(policy(4),world())['label'],'NONE')

    def test_boundary_grid(self):
        for b,start,width in product((2,3,4),(0,17),(2,5)):
            p=policy(b,start,width)
            for issued,gy,dx,dy,t,revoked in product((False,True),(False,True),range(3),range(3),e.times(p),(False,True)):
                w=world(issued=issued,gy=gy,dx=dx,dy=dy,time_y=t,revoked=revoked)
                positive=(dy>0 and (not issued or not gy or t<start or t>=start+width or
                          (revoked and t>=start+width-1) or dx+dy>b))
                self.assertEqual(e.simulate(p,w)['label'], 'D' if positive else 'NONE')

    def test_uniform_complete_world_domain_and_projection_weights(self):
        p=policy(); w=world()
        self.assertEqual(sum(1 for _ in e.worlds(p)),14400)
        rows=e.compatible_worlds(e.observe(p,w,()))
        self.assertEqual(len(rows),1800)
        self.assertEqual(sum(r['weight'] for r in rows),14400)
        packet=e.observe(p,w,(8,))
        self.assertNotIn('B',e.labels(packet))
        self.assertEqual(sum(r['weight'] for r in e.compatible_worlds(packet)),2880)

    def test_packet_boundary_and_layout(self):
        p=policy(); packet=e.observe(p,world(notes=['false accusation A']*5))
        self.assertEqual(set(packet['public']),e.PUBLIC_KEYS)
        for i in (3,4):
            self.assertEqual(set(packet['records'][i]['payload']),{'closed','delta','local_before','local_after'})
        a=e.serialize(packet); b=e.serialize(packet,'shuffled')
        self.assertEqual(len(a.encode()),len(b.encode()))
        aa=json.loads(a); bb=json.loads(b)
        self.assertEqual(aa['public'],bb['public'])
        self.assertEqual(sorted(aa['records'],key=lambda r:r['id']), sorted(bb['records'],key=lambda r:r['id']))
        self.assertEqual(e.labels(packet),e.labels(e.observe(p,world(notes=['']*5))))

    def test_identifiers_ignore_payload_and_views_never_drop_truth(self):
        p=policy(); one=world(); two=world(issued=False,gx=False,gy=False,dx=0,dy=0,time_y=5,revoked=True,y_worker='E',x_worker='A')
        self.assertEqual([r['id'] for r in e.records(p,one)],[r['id'] for r in e.records(p,two)])
        views=e.views(p,one)
        self.assertEqual(len(views),7)
        self.assertEqual([len(v['packet']['records']) for v in views],[16,7,12,12,14,14,14])
        for v in views:
            self.assertIn('D',v['compatible_labels'])
        # Same visible packet implies the exact same unopened selection even when truth differs.
        for selector in (e.metadata_selector,e.contract_selector):
            a=e.observe(p,one,(0,2,4,5,6,7)); b=e.observe(p,world(dx=0),(0,2,4,5,6,7))
            self.assertEqual(a,b)
            self.assertEqual(selector(a),selector(b))

    def test_contract_selector_matches_full_world_prior(self):
        p=policy(); w=world()
        # Both nuisance dimensions are queryable, including X identity correlated with target identity.
        for kept in ((0,2,3,4,5,6,9,10,11,12,13,14,15), (0,2,4,5,6,7,9,10,11,12,13,14,15)):
            packet=e.observe(p,w,kept); visible=e.validate(packet)
            full=[]
            for candidate in e.worlds(p):
                rr=e.records(p,candidate)
                if all(rr[i]['payload']==q for i,q in visible.items()):
                    full.append((rr,e.simulate(p,candidate)['label']))
            candidates=[i for i in range(16) if i not in kept]
            costs=[]
            for bundle in combinations(candidates,2):
                groups={}
                for rr,label in full:
                    sig=tuple(e.canonical(rr[i]['payload']) for i in bundle)
                    if sig not in groups: groups[sig]=[0,set()]
                    groups[sig][0]+=1; groups[sig][1].add(label)
                costs.append((sum(n*len(s) for n,s in groups.values()),bundle))
            best=min(costs)[1]
            self.assertEqual(e.contract_selector(packet),[e.slot_id(p,i) for i in best])

    def test_rejects_counterfeits_duplicates_corruption_and_types(self):
        p=policy(); base=e.observe(p,world())
        variants=[]
        q=deepcopy(base); q['records'].append(deepcopy(q['records'][0])); variants.append(q)
        q=deepcopy(base); q['manifest'][0]=deepcopy(q['manifest'][1]); variants.append(q)
        q=deepcopy(base); q['records'][0]['trusted']=1; variants.append(q)
        q=deepcopy(base); q['manifest'][0]['trusted']=1; variants.append(q)
        q=deepcopy(base); q['records'][3]['payload']['local_after']=1; variants.append(q)
        q=deepcopy(base); q['records'][4]['payload']['delta']=True; variants.append(q)
        q=deepcopy(base); q['records'][7]['payload']['instance']='B'; variants.append(q)
        q=deepcopy(base); q['records'][0]['id']='counterfeit'; variants.append(q)
        q=deepcopy(base); q['public']['budget']=True; variants.append(q)
        for packet in variants:
            with self.subTest(packet=packet):
                self.assertEqual(e.labels(packet),[])
                with self.assertRaises(ValueError): e.validate(packet)


if __name__=='__main__': unittest.main()
