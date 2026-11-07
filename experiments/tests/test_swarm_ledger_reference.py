"""Independent predicate and constraint support agreement on finite policy grids."""
from copy import deepcopy
from itertools import combinations, product
import unittest

from experiments import swarm_ledger as e
from experiments.swarm_ledger_reference import reference_labels
from experiments.tests.test_swarm_ledger import policy, world


class ReferenceTests(unittest.TestCase):
    def test_exhaustive_projected_complete_and_sufficient_grid(self):
        for b,start,width in product((2,3,4),(0,17),(2,5)):
            p=policy(b,start,width)
            for issued,gy,dx,dy,t,revoked in product((False,True),(False,True),range(3),range(3),e.times(p),(False,True)):
                w=world(issued=issued,gy=gy,dx=dx,dy=dy,time_y=t,revoked=revoked)
                expected={e.simulate(p,w)['label']}
                for slots in (range(16),e.CRITICAL):
                    packet=e.observe(p,w,slots)
                    self.assertEqual(reference_labels(packet),expected)
                    self.assertEqual(set(e.labels(packet)),expected)

    def test_sparse_masks_and_all_bindings(self):
        for x,y in product(e.WORKERS,repeat=2):
            if x==y: continue
            p=policy();w=world(x_worker=x,y_worker=y)
            for slots in ((),(7,),(8,),(7,8),(0,2,3,4),(3,4,5,6),e.CRITICAL):
                q=e.observe(p,w,slots)
                self.assertEqual(reference_labels(q),set(e.labels(q)))

    def test_each_critical_field_can_change_the_target_label(self):
        # Irreducible over the declared domain, not minimal for every individual
        # packet: zero updates or budget4 can need fewer records.
        p=policy()
        pairs={
            0:(world(dx=1),world(dx=1,issued=False)),
            2:(world(dx=1),world(dx=1,gy=False)),
            3:(world(dx=1),world(dx=2)),
            4:(world(dy=0),world(dy=2)),
            5:(world(dx=1,time_y=0),world(dx=1,time_y=5)),
            6:(world(dx=1,time_y=4),world(dx=1,time_y=4,revoked=True)),
            7:(world(y_worker='D'),world(y_worker='E')),
        }
        for removed,(a,b) in pairs.items():
            kept=[i for i in range(16) if i!=removed]
            pa=e.observe(p,a,kept);pb=e.observe(p,b,kept)
            self.assertEqual(pa,pb)
            self.assertNotEqual(e.simulate(p,a)['label'],e.simulate(p,b)['label'])
            self.assertGreater(len(reference_labels(pa)),1)
        p=policy();w=world()
        for k in range(3):
            for missing in combinations(e.CRITICAL,k):
                slots=[i for i in range(16) if i not in missing]
                q=e.observe(p,w,slots)
                self.assertEqual(reference_labels(q),set(e.labels(q)))

    def test_independent_rejects_malformed(self):
        base=e.observe(policy(),world())
        for slot,key,value in ((0,'issued',1),(1,'cap',True),(3,'closed',1),(5,'settled_at',True),(6,'effective_at',4),(7,'instance','F')):
            q=deepcopy(base);q['records'][slot]['payload'][key]=value
            self.assertEqual(reference_labels(q),set())
        q=deepcopy(base);q['records'][7]['payload']['instance']='B'
        self.assertEqual(reference_labels(q),set())
        q=deepcopy(base);q['records'].append(deepcopy(q['records'][0]))
        self.assertEqual(reference_labels(q),set())


if __name__=='__main__':unittest.main()
