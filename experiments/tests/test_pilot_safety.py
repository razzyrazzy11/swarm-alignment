import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.pilot import run_pilot,scrub

class PilotSafetyTests(unittest.TestCase):
    def test_scrub_before_serializing_escaped_secrets(self):
        secret='fake-"quoted\\secret'
        value={'nested':['prefix '+secret]}
        self.assertNotIn(secret,json.dumps(scrub(value,[secret])))
        self.assertEqual(scrub(value,[secret])['nested'],['prefix [REDACTED]'])

    def test_unknown_charge_halts_and_preserves_results(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run'
            with patch('experiments.pilot.credentials',return_value={'ADAPTION_API_KEY':'TEST_ONLY'}),patch('experiments.pilot.request_json',side_effect=RuntimeError('not logged')):
                summary=run_pilot(out,models=['deepseek-v4-flash'],n=2)
            self.assertEqual(summary['status'],'pilot_halted')
            self.assertGreater(float(summary['estimated_credits']),0)
            rows=[json.loads(s) for s in (out/'responses.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),summary['attempted_calls'])
            self.assertNotIn('TEST_ONLY',(out/'responses.jsonl').read_text())
            self.assertNotIn('not logged',(out/'responses.jsonl').read_text())

    def test_truncation_gate_drains_started_calls(self):
        reply=dict(status='incomplete',model='deepseek-v4-flash',output_text='',usage={'input_tokens':10,'output_tokens':20,'cost':0.00001})
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run'
            with patch('experiments.pilot.credentials',return_value={'ADAPTION_API_KEY':'TEST_ONLY'}),patch('experiments.pilot.request_json',return_value=({'http_status':200,'latency_seconds':0.1},reply)):
                summary=run_pilot(out,models=['deepseek-v4-flash'],n=2,stop_after_incomplete=1)
            self.assertEqual(summary['status'],'pilot_halted')
            self.assertLessEqual(summary['attempted_calls'],4)
            self.assertEqual(len((out/'responses.jsonl').read_text().splitlines()),summary['attempted_calls'])

if __name__=='__main__':unittest.main()
