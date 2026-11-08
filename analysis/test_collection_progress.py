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

    def test_explicit_cutoff_changes_only_margins_not_duration(self):
        old=p.project(self.attempts,self.terminals,self.now)
        cutoff=datetime(2026,11,9,7,56,tzinfo=timezone.utc)
        new=p.project(self.attempts,self.terminals,self.now,cutoff=cutoff)
        for name in ('conservative_collection_seconds','cumulative_reader_seconds','optimistic_conditional_reader_seconds','conservative_collection_finish_utc'):
            self.assertEqual(new[name],old[name])
        self.assertAlmostEqual(new['conservative_margin_to_cutoff_hours']-old['conservative_margin_to_cutoff_hours'],117/60)
        self.assertEqual(old['collection_cutoff_utc'],p.CUTOFF.isoformat())

    def test_actual_rate_registration_selects_new_admission_without_changing_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);research=root/'research';research.mkdir()
            baseline=root/'progress-projection.json';baseline.write_text('{"historical_cutoff":"05:59"}')
            raw=baseline.read_bytes()
            self.assertEqual(p.registered_deadline_policy(root)['collection_cutoff_utc'],p.CUTOFF.isoformat())
            policy=dict(cutoff_utc='2026-11-09T07:56:00+00:00',target_drained_utc='2026-11-09T08:00:00+00:00',submission_deadline_utc=p.DEADLINE.isoformat())
            (research/'swarm-ledger-rate-v1-freeze.json').write_text(json.dumps(dict(schema_version=1,tag='swarm-ledger-rate-v1',policy=policy)))
            value=p.registered_deadline_policy(root)
            self.assertEqual(value['collection_cutoff_utc'],policy['cutoff_utc'])
            self.assertEqual(value['submission_deadline_utc'],p.DEADLINE.isoformat())
            self.assertEqual(baseline.read_bytes(),raw)
            self.assertEqual(p.CUTOFF.hour,5)

    def test_malformed_rate_deadline_never_falls_back_to_old_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);research=root/'research';research.mkdir();path=research/'swarm-ledger-rate-v1-freeze.json'
            for value in ({'schema_version':1,'tag':'wrong','policy':{}},
                          {'schema_version':1,'tag':'swarm-ledger-rate-v1','policy':dict(cutoff_utc=p.DEADLINE.isoformat(),target_drained_utc=p.DEADLINE.isoformat(),submission_deadline_utc=p.DEADLINE.isoformat())}):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):p.registered_deadline_policy(root)

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
