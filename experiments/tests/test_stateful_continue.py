import unittest
from experiments.stateful_continue import remaining,verify_union

class ContinuationTests(unittest.TestCase):
    def fixture(self):
        order=[('t'+str(j),'m') for j in range(3840)]
        tasks=[dict(task_id=t,packet={'fake':j}) for j,(t,m) in enumerate(order)]
        starts=[dict(task_id=t,model=m) for t,m in order[:3028]]
        return dict(order=order),starts,tasks

    def test_exact_ordered_unstarted_complement_never_retries_failed_start(self):
        manifest,starts,tasks=self.fixture();pending=remaining(manifest,starts,tasks)
        self.assertEqual(len(pending),812)
        self.assertEqual([(t['task_id'],m) for t,m in pending],manifest['order'][3028:])
        self.assertFalse({(t['task_id'],m) for t,m in pending}&{(s['task_id'],s['model']) for s in starts})

    def test_duplicate_or_unplanned_starts_fail_closed(self):
        manifest,starts,tasks=self.fixture()
        for bad in (starts+[starts[0]],starts+[dict(task_id='outside-plan',model='m')]):
            with self.assertRaises(ValueError):remaining(manifest,bad,tasks)

    def test_changed_planned_grid_fails_closed(self):
        manifest,starts,tasks=self.fixture();manifest['order'][-1]=manifest['order'][0]
        with self.assertRaises(ValueError):remaining(manifest,starts,tasks)

    def test_matching_substitution_in_both_journals_cannot_hide_missing_planned_id(self):
        manifest,_,_=self.fixture()
        starts=[dict(task_id=t,model=m) for t,m in manifest['order']]
        answers=[dict(task=dict(task_id=t),model=m) for t,m in manifest['order']]
        verify_union(manifest['order'],starts,answers)
        starts[-1]['task_id']='unplanned';answers[-1]['task']['task_id']='unplanned'
        with self.assertRaises(ValueError):verify_union(manifest['order'],starts,answers)

if __name__=='__main__':unittest.main()
