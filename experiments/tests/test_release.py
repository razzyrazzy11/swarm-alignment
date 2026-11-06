import unittest
from experiments.verify_release import verify_release

class ReleaseTests(unittest.TestCase):
    def test_source_replay_packets_outputs_and_counts(self):
        self.assertEqual(verify_release()['reader_calls'],120)
