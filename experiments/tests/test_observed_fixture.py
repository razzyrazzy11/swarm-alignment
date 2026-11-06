import json
from pathlib import Path
import unittest
from experiments.oracle import compatible_labels
from experiments.pilot import classify

class ObservedFixtureTests(unittest.TestCase):
    def test_observed_correct_guess_is_unsupported(self):
        root=Path(__file__).resolve().parents[2]
        x=json.loads((root/'research/fixtures/unsupported-development-example.json').read_text())
        labels=compatible_labels(x['packet'])
        self.assertEqual(labels,set(x['compatible_labels']))
        answer=json.loads(x['actual_output'])
        self.assertEqual(answer['worker_id'],x['complete_history_label'])
        score=classify({'status':'completed','output_text':x['actual_output']},labels)
        self.assertEqual(score['unsupported_executor'],1)
        self.assertEqual(score['grounded_correct'],0)
