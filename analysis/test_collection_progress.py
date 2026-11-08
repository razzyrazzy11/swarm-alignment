"""Pure synthetic checks for the metadata-only reporting helper."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from analysis import collection_progress as p


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.attempts = [dict(id=profile, profile_id=profile,
            started=(self.now-timedelta(seconds=100)).isoformat()) for profile in p.PLANNED]
        self.terminals = [dict(id=profile, profile_id=profile, latency_seconds=10,
            http_status=200, known_usage=True, anomaly=False) for profile in p.PLANNED]

    def test_shared_provider_loads_are_summed_and_global_slots_bound(self):
        result = p.project(self.attempts, self.terminals, self.now)
        resources = result['shared_capacity_resource_seconds']
        self.assertEqual(resources['ollama_shared_provider'], ((12800-1)+(5120-1))*10/2)
        self.assertEqual(resources['hf_shared_provider'], (5120-1)*10)
        self.assertEqual(resources['native_g26_model'], (12800-1)*10/2)
        self.assertEqual(resources['global_eight_slots'], (sum(p.PLANNED.values())-6)*10/8)
        self.assertEqual(result['optimistic_conditional_reader_seconds'], max(resources.values()))
        self.assertIn('not a hard wall-clock bound', result['limits'])

    def test_prior_conservative_formula_and_deadline_margins_retained(self):
        result = p.project(self.attempts, self.terminals, self.now)
        old = (12800-1)*100
        expected = (old+80+1286.812875)*1.25+3300
        self.assertEqual(result['cumulative_reader_seconds'], old)
        self.assertEqual(result['conservative_collection_seconds'], expected)
        self.assertAlmostEqual(result['conservative_hours_remaining_to_submission']-
                               result['conservative_margin_to_cutoff_hours'], 6)

    def test_failure_is_included_and_missing_latency_disclosed(self):
        self.terminals[0].update(http_status=None, known_usage=False, anomaly=True,
                                 latency_seconds=None)
        result = p.project(self.attempts, self.terminals, self.now)
        self.assertEqual(result['profiles']['g26']['terminal'], 1)
        self.assertEqual(result['profiles']['g26']['unknown_usage'], 1)
        self.assertEqual(result['profiles']['g26']['anomalies'], 1)
        self.assertEqual(result['profiles']['g26']['missing_latency'], 1)
        self.assertIsNone(result['optimistic_conditional_reader_seconds'])

    def test_inflight_is_valid_not_a_terminal_or_corruption(self):
        result = p.project(self.attempts, self.terminals[1:], self.now)
        self.assertEqual(result['total_in_flight'], 1)
        self.assertIsNone(result['cumulative_reader_seconds'])

    def test_duplicate_foreign_and_unstarted_records_fail_closed(self):
        cases = [(self.attempts*2, self.terminals), (self.attempts, self.terminals*2),
                 (self.attempts, [dict(self.terminals[0], id='not-started')]),
                 ([dict(self.attempts[0], profile_id='foreign')], []),
                 (self.attempts, [dict(self.terminals[0], profile_id='g31')])]
        for attempts, terminals in cases:
            with self.subTest(attempts=len(attempts), terminals=len(terminals)):
                with self.assertRaises(ValueError):
                    p.project(attempts, terminals, self.now)

    def test_invalid_latency_and_flags_are_rejected(self):
        for change in ({'latency_seconds': float('nan')}, {'latency_seconds': -1},
                       {'latency_seconds': True}, {'http_status': True},
                       {'known_usage': 1}, {'anomaly': 'false'}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    p.project(self.attempts, [dict(self.terminals[0], **change)], self.now)

    def test_partial_final_line_ignored_and_answer_fields_not_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'responses.jsonl'
            row = dict(id='synthetic', profile_id='g26', transport=dict(latency_seconds=1,
                http_status=200), known_usage=True, anomaly=False,
                response='ANSWER MUST NOT APPEAR', private_native_id='PRIVATE')
            path.write_bytes((json.dumps(row)+'\n{"partial":').encode())
            result = p.read_metadata(path, terminal=True)
            self.assertEqual(len(result), 1)
            self.assertNotIn('ANSWER', json.dumps(result))
            self.assertNotIn('PRIVATE', json.dumps(result))
            path.write_text('{bad json}\n')
            with self.assertRaises(json.JSONDecodeError):
                p.read_metadata(path, terminal=True)
            path.write_text('{"id":"a","id":"b"}\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON object key'):
                p.read_metadata(path, terminal=True)


if __name__ == '__main__':
    unittest.main()
