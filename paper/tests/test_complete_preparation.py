"""Pure preparation tests. Synthetic aggregate fixture; never empirical output."""
from pathlib import Path
from copy import deepcopy
from contextlib import ExitStack
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER.parent))
sys.path.insert(0, str(PAPER / 'tests'))
from paper import prepare_complete as prep
from test_complete_report_contract import fixture


class CompletePreparationTests(unittest.TestCase):
    def test_draft_does_not_read_results_or_claim_completion(self):
        with patch.object(prep.contract, 'load_completed', side_effect=AssertionError('No result access')):
            value = prep.draft()
        self.assertIn('NOT FOR SUBMISSION', value['preparation_status'])
        self.assertEqual(value['abstract'], prep.PLACEHOLDER)
        self.assertNotIn('ledger_registration', value)
        self.assertTrue(any('Limitations and Dual-Use / Ethical Considerations' in h for h, _ in value['appendix']))

    def test_waiting_postprocessor_blocks_before_result_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / 'paper'; paper.mkdir()
            state = paper.parent / 'runs/router-resume-postprocess-driver/state.json'
            state.parent.mkdir(parents=True)
            state.write_text('{"status":"waiting_collection"}')
            with patch.object(prep.contract, 'load_completed') as load:
                with self.assertRaisesRegex(ValueError, 'must finish'):
                    prep.ready(paper)
                load.assert_not_called()

    def test_candidate_uses_contract_exactly_and_requires_ready(self):
        report, _ = fixture()
        with patch.object(prep, 'ready', return_value=(report, {'toy': 'synthetic-only'})) as ready:
            value = prep.candidate()
        ready.assert_called_once_with(prep.PAPER)
        self.assertTrue(prep.contract.validate_manuscript(value, report))
        self.assertEqual(value['table1'], prep.contract.expected_fields(report)['table1'])
        self.assertNotIn(prep.PLACEHOLDER, str(value))
        self.assertTrue(150 <= len(value['abstract'].split()) <= 250)
        self.assertIn('VISUAL REVIEW REQUIRED', value['preparation_status'])
        import verify
        verify.validate_source(value)

    def test_writing_never_replaces_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'draft.json'
            prep.write_new(out, {'status': 'draft'})
            with self.assertRaises(FileExistsError): prep.write_new(out, {})
            self.assertIn('draft', out.read_text())


class SensitivityReadinessTests(unittest.TestCase):
    def setUp(self):
        from analysis import ledger_generator_sensitivity as sensitivity
        self.s = sensitivity
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.paper = Path(self.temp.name) / 'paper'; self.paper.mkdir()
        self.source = self.paper.parent / 'data/swarm-ledger-v1-public'; self.source.mkdir(parents=True)
        self.target = self.paper.parent / 'data/swarm-ledger-generator-sensitivity-v1'; self.target.mkdir()
        for name in ('manifest.json', 'report.json'):
            (self.source / name).write_text('{}\n', encoding='utf-8')
        self.registration = {'kind': 'SYNTHETIC TEST REGISTRATION'}
        self.scientific = {'schema_version': 1, 'unique_packets': 2, 'views': {'toy': {'packets': 2}}}
        self.packets, self.verdicts = [{'toy_packet': 1}, {'toy_packet': 2}], [{'toy_verdict': 1}]
        self.original = {'primary': {'toy_effect': 0}}
        self.manifest = {'provenance_limit': 'SYNTHETIC ONLY'}
        (self.target / 'registration.json').write_text(json.dumps(self.registration), encoding='utf-8')
        for name, rows in (('packets.jsonl', self.packets), ('verdicts.jsonl', self.verdicts)):
            (self.target / name).write_text(''.join(sensitivity.study.canonical(x)+'\n' for x in rows), encoding='utf-8')
        inventory = sensitivity.raw_inventory(self.source)
        self.value = dict(deepcopy(self.scientific), created='2026-01-01T00:00:00+00:00',
            registration_sha256='synthetic-sha', input_files_raw_sha256=inventory,
            input_manifest_raw_sha256=inventory['manifest.json'], input_report_raw_sha256=inventory['report.json'],
            input_verification={'valid': True}, original_primary_unchanged=True,
            original_primary_commitment=sensitivity.study.digest(self.original['primary']),
            provenance_limit=self.manifest['provenance_limit'], derived_files_raw_sha256=sensitivity.raw_inventory(self.target))
        self.save()

    def save(self):
        (self.target / 'report.json').write_text(json.dumps(self.value), encoding='utf-8')

    def replay(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.s, 'verify', return_value=self.registration))
            stack.enter_context(patch.object(self.s.study, 'sha', return_value='synthetic-sha'))
            stack.enter_context(patch.object(self.s.analysis, 'load_public_artifacts', return_value=({}, self.original, self.manifest)))
            stack.enter_context(patch.object(self.s, 'summarize', return_value=(self.scientific, self.packets, self.verdicts)))
            return prep.verify_sensitivity(self.paper)

    def test_reconstructed_synthetic_report_and_rows_are_accepted(self):
        self.assertEqual(self.replay(), self.s.raw_inventory(self.target)['report.json'])

    def test_stale_input_or_changed_scientific_primary_and_derived_hashes_rejected(self):
        original = deepcopy(self.value)
        for kind in ('input', 'scientific', 'type', 'primary', 'derived', 'registration', 'extra'):
            with self.subTest(kind=kind):
                self.value = deepcopy(original)
                if kind == 'input': self.value['input_files_raw_sha256']['report.json'] = 'stale'
                elif kind == 'scientific': self.value['unique_packets'] = 999
                elif kind == 'type': self.value['schema_version'] = True
                elif kind == 'primary': self.value['original_primary_commitment'] = 'changed'
                elif kind == 'derived': self.value['derived_files_raw_sha256']['packets.jsonl'] = 'changed'
                elif kind == 'registration': self.value['registration_sha256'] = 'changed'
                else: self.value['unregistered_scientific_claim'] = 1
                self.save()
                with self.assertRaises(ValueError): self.replay()

    def test_changed_rows_rejected_even_if_attacker_updates_their_hash(self):
        (self.target / 'packets.jsonl').write_text('{"toy_packet":999}\n', encoding='utf-8')
        self.value['derived_files_raw_sha256']['packets.jsonl'] = self.s.raw_inventory(self.target)['packets.jsonl']
        self.save()
        with self.assertRaisesRegex(ValueError, 'derived rows differ'): self.replay()


if __name__ == '__main__': unittest.main()
