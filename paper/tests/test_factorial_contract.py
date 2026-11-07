"""Synthetic contract tests for the factorial branch of verify.validate_results.

Every fixture value is a bookkeeping example, not an empirical outcome:
no live project, results, API, credentials, network, shell, or subprocess.
"""
import json
from copy import deepcopy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verify import validate_results

SOURCES = 192
MODEL_IDS = ['fixture-a', 'fixture-b', 'fixture-c']
MODEL_NAMES = {'fixture-a': 'Gemma 26B A4B', 'fixture-b': 'Gemma 31B', 'fixture-c': 'Llama 70B HF'}
VIEWS = ['sufficient', 'identity_loss',
         'random_none', 'random_random', 'random_metadata', 'random_contract',
         'selective_none', 'selective_random', 'selective_metadata', 'selective_contract']
PRIMARY = {'n': SOURCES, 'estimate': 30 / SOURCES, 'ci95': [0.10, 0.22]}
SECONDARY = {
    'metadata_minus_random': {'n': SOURCES, 'estimate': 0.0625, 'ci95': [0.0, 0.125]},
    'contract_minus_metadata': {'n': SOURCES, 'estimate': 0.03125, 'ci95': [-0.03125, 0.09375]},
}


def build_results():
    models = {}
    for model in MODEL_IDS:
        by_view = {}
        for view in VIEWS:
            by_view[view] = {
                'direct': {'raw': {'calls': SOURCES,
                                   'grounded_correct': 120 if view == 'sufficient' else 140,
                                   'supported_definite': 120,
                                   'unsupported_executor': 20,
                                   'unsupported_none': 10,
                                   'invalid': 12}},
                'procedure': {'raw': {'calls': SOURCES,
                                      'grounded_correct': 150 if view == 'sufficient' else 160,
                                      'supported_definite': 150,
                                      'unsupported_executor': 10,
                                      'unsupported_none': 5,
                                      'invalid': 5}}}
            for procedure in ('direct', 'procedure'):
                gated = deepcopy(by_view[view][procedure]['raw'])
                gated['unsupported_executor'] = gated['unsupported_none'] = 0
                if view != 'sufficient':
                    gated['grounded_correct'] = 170 if procedure == 'direct' else 175
                by_view[view][procedure]['gated'] = gated
        models[model] = {'by_view': by_view,
                         'totals': {'calls': 20 * SOURCES},
                         'primary_same_packet_procedure_minus_direct': dict(PRIMARY),
                         'secondary_acquisition_grounded': {k: dict(v) for k, v in SECONDARY.items()}}
    return {'status': 'complete',
            'config': {'study_id': 'factorial-audit-v1', 'sources': SOURCES, 'monitors': list(MODEL_IDS)},
            'analysis': {'sources': SOURCES,
                         'actor_calls': 3 * SOURCES,
                         'main_audit_calls': 20 * SOURCES * len(MODEL_IDS),
                         'calibration_calls': 120,
                         'models': models}}


def build_content():
    table1 = [['Model (sources)', 'Supported definite direct / procedure', 'Primary same-packet effect']]
    table2 = [['Model (calls)', 'Grounded correct direct / procedure', 'Unsupported executor/none D; P', 'Invalid direct / procedure']]
    table3 = [['Model (sources)', 'Metadata minus random', 'Contract minus metadata']]
    for model in MODEL_IDS:
        name = MODEL_NAMES[model]
        table1.append([f'{name} ({SOURCES})', '120/192 / 150/192', '+15.62 [+10.00, +22.00]'])
        table2.append([f'{name} (3840)', '1380 / 1590', 'D:200/100; P:100/50', '120 / 50'])
        table3.append([f'{name} ({SOURCES})', '+6.25 [+0.00, +12.50]', '+3.12 [-3.12, +9.38]'])
    return {'table2_source': 'factorial',
            'evidence_status': {'status': 'completed factorial study',
                                'source_groups': SOURCES,
                                'actor_calls': 576,
                                'main_audit_calls': 11520,
                                'calibration_calls': 120,
                                'training_runs': 0,
                                'freeze': 'factorial-audit-v1'},
            'table2_model_ids': list(MODEL_IDS),
            'table1': table1,
            'table2': table2,
            'table3': table3}


class FactorialContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.paper = root / 'paper'
        research = root / 'research'
        research.mkdir()
        self.paper.mkdir()
        self.results_path = research / 'factorial-results.json'
        self.write_results(build_results())

    def write_results(self, results):
        self.results_path.write_text(json.dumps(results), encoding='utf-8')

    def test_raw_counts_anchor_reader_table(self):
        content = build_content()
        validate_results(self.paper, content)
        # The public source contains both raw and gated results. Mutate the
        # manuscript, not the raw source, to detect accidental gate credit.
        gated_grounded = deepcopy(content)
        for row in gated_grounded['table2'][1:]:
            row[1] = '1650 / 1725'
        with self.subTest('gated grounded aggregates 1650/1725 cannot replace raw 1380/1590'):
            with self.assertRaisesRegex(ValueError, 'Reader table differs from public cases'):
                validate_results(self.paper, gated_grounded)
        gated_unsupported = deepcopy(content)
        for row in gated_unsupported['table2'][1:]:
            row[2] = 'D:0/0; P:0/0'
        with self.subTest('gated zero unsupported counts cannot replace raw D:200/100; P:100/50'):
            with self.assertRaisesRegex(ValueError, 'Reader table differs from public cases'):
                validate_results(self.paper, gated_unsupported)

    def test_calibration_and_per_reader_calls_stay_separate(self):
        content = build_content()
        validate_results(self.paper, content)
        folded = build_results()
        folded['analysis']['main_audit_calls'] += 120
        folded_content = build_content()
        folded_content['evidence_status']['main_audit_calls'] += 120
        with self.subTest('adding 120 calibration to main_audit_calls breaks the call grid; calibration stays 120'):
            self.write_results(folded)
            with self.assertRaisesRegex(ValueError, 'Factorial source/call grid differs'):
                validate_results(self.paper, folded_content)
        inflated = build_results()
        inflated_content = build_content()
        for model in inflated['analysis']['models'].values():
            model['totals']['calls'] += 40
        for row in inflated_content['table2'][1:]:
            row[0] = row[0].replace('(3840)', '(3880)')
        with self.subTest('adding 40 per reader to totals and table2 label breaks the call grid'):
            self.write_results(inflated)
            with self.assertRaisesRegex(ValueError, 'Reader table differs from public call grid'):
                validate_results(self.paper, inflated_content)

    def test_primary_effect_denominator_pinned_to_sources(self):
        content = build_content()
        validate_results(self.paper, content)
        tampered = build_results()
        for model in tampered['analysis']['models'].values():
            model['primary_same_packet_procedure_minus_direct']['n'] = 20 * SOURCES
        self.write_results(tampered)
        with self.assertRaisesRegex(ValueError, 'Effect source denominator differs'):
            validate_results(self.paper, content)


if __name__ == '__main__':
    unittest.main()
