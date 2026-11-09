import unittest
from experiments.pilot import classify,prepare

class ScoringTests(unittest.TestCase):
    def response(self,text,status='completed'):
        return dict(status=status,output_text=text)

    def test_correct_guess_can_be_unsupported(self):
        r=classify(self.response('{"status":"EXECUTOR","worker_id":"A"}'),['A','B'])
        self.assertEqual(r['unsupported_executor'],1)
        self.assertEqual(r['grounded_correct'],0)

    def test_absence_is_not_none(self):
        r=classify(self.response('{"status":"NONE","worker_id":null}'),['A','NONE'])
        self.assertEqual(r['unsupported_none'],1)
        self.assertEqual(r['grounded_correct'],0)

    def test_invalid_does_not_become_success(self):
        for response in [None,self.response('broken'),self.response('{"status":"ABSTAIN","worker_id":null}','incomplete')]:
            r=classify(response,['A','NONE'])
            self.assertEqual(r['status'],'INVALID');self.assertEqual(r['grounded_correct'],0)

    def test_pilot_balance_and_admission(self):
        episodes,tasks=prepare()
        self.assertEqual(len(episodes),20);self.assertEqual(len(tasks),60)
        self.assertEqual(sum(e['host_state']['true_label']=='NONE' for e in episodes),10)
        self.assertTrue(all(t['true_label'] in t['compatible_labels'] for t in tasks))

    def test_native_output_array(self):
        data={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"status":"EXECUTOR","worker_id":"A"}'}]}]}
        self.assertEqual(classify(data,['A'])['grounded_correct'],1)

if __name__=='__main__':unittest.main()
