import copy
from decimal import Decimal
from pathlib import Path
import tempfile
import random
import unittest
from unittest.mock import patch

from experiments import verify_stateful_results as checker
from experiments import stateful_release as release
from experiments import stateful_analysis as analysis
from experiments.tests import test_stateful_release as fixtures


class StatefulAggregateTests(unittest.TestCase):
    def fixture(self, root):
        args = fixtures.StatefulReleaseTests().fixture(root)
        rows, _, arm = release.verify_core(*args)
        return args, rows, arm

    def test_recounts_view_totals_call_states_and_costs(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, arm = self.fixture(Path(d))
            checker.verify_counts(rows, arm)
            mutations = [lambda a: a['model_totals']['test-reader'].update(grounded_correct=999),
                         lambda a: next(iter(a['models']['test-reader'].values())).update(calls=999),
                         lambda a: a['summary'].update(attempted_calls=0),
                         lambda a: a['costs'].update(estimated_total='999'),
                         lambda a: a['costs'].update(provider_reported_total='999')]
            for mutate in mutations:
                altered = copy.deepcopy(arm)
                mutate(altered)
                with self.assertRaises(ValueError):
                    checker.verify_counts(rows, altered)
            invalid = copy.deepcopy(rows)
            invalid[0]['attempted'] = False
            with self.assertRaises(ValueError):
                checker.verify_counts(invalid, arm)

    def test_aggregate_alias_tampering_rejected_without_native_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frozen = dict(config={'study_id': 'fixture'}, source_sha256={})
            freeze = root/'freeze.json'
            release.write_json(freeze, frozen)
            report = dict(config=frozen['config'], frozen_source_sha256={}, freeze_sha256=release.file_hash(freeze),
                          arms={k: dict(status='not_run') for k in ('main', 'hugging_face', 'influence')},
                          main=dict(status='complete'), hf=dict(status='not_run'), influence=dict(status='not_run'))
            release.write_json(root/'research/stateful-results.json', report)
            for name in ('stateful_main_cases.jsonl', 'stateful_hf_cases.jsonl', 'stateful_influence_cases.jsonl'):
                release.write_rows(root/'data'/name, [])
            with patch.object(checker.publication, 'verify_public', return_value={'valid': True}), patch.object(checker, 'verify_freeze', return_value=frozen), patch.object(checker, 'FREEZE', freeze):
                with self.assertRaisesRegex(ValueError, 'alias'):
                    checker.verify(root)

    def test_main_replay_recomputes_frozen_bootstrap_and_baselines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            args, rows, arm = self.fixture(root)
            folder, models, episodes, tasks, order = args
            c = dict(models=models, primary_model=models[0], bootstrap_seed=17, bootstrap_resamples=100)
            frozen = dict(config=c, source_sha256={})
            freeze = root/'freeze.json'
            release.write_json(freeze, frozen)
            release.write_json(folder/'manifest.json', dict(stage='main', freeze=frozen, order=order))
            summary = release.read_json(folder/'summary.json')
            summary.update(stage='main', freeze_sha256='fixture-hash')
            release.write_json(folder/'summary.json', summary)
            public_episodes = [dict(e, host_state={}, true_label='fixture') for e in episodes]
            release.write_json(root/'data/stateful_main_episodes.json', public_episodes)
            with patch.object(analysis, 'verify_freeze', return_value=frozen), patch.object(analysis, 'config', return_value=c), patch.object(analysis, 'prepare', return_value=(episodes, tasks)), patch.object(analysis, 'FREEZE', freeze), patch.object(analysis, 'sha', return_value='fixture-hash'), patch.object(checker, 'prepare', return_value=(episodes, tasks)), patch.object(checker, 'sha', return_value='fixture-hash'):
                expected = analysis.analyze(folder)
                arm['analysis'] = dict(stage='main', complete=True, source_episodes=2,
                    effects={m: value['effects'] for m, value in expected['models'].items()})
                checker.replay_main(root, rows, arm, frozen)
                altered = copy.deepcopy(arm)
                altered['analysis']['effects'][models[0]]['primary_unsupported_targeted_minus_random']['ci95'][0] = 999
                with self.assertRaisesRegex(ValueError, 'effects'):
                    checker.replay_main(root, rows, altered, frozen)
                altered = copy.deepcopy(arm)
                altered['baselines']['always_abstain']['grounded_correct'] = 999
                with self.assertRaisesRegex(ValueError, 'baselines'):
                    checker.replay_main(root, rows, altered, frozen)

    def test_not_run_with_cases_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not_run'):
            checker.verify_counts([dict(attempted=False, returned=False)], dict(status='not_run'))

    def test_influence_pair_and_per_call_cost_tampering_rejected(self):
        settings = dict(source_episodes=1, seed_start=990000, model='gemma-4-26b-a4b-it', max_output_tokens=4096)
        c = dict(influence=settings, bootstrap_seed=17, bootstrap_resamples=50)
        ri, ro = map(Decimal, checker.RATES[settings['model']])
        charge = str((100*ri+10*ro)/1000000)
        order = [(a, w) for a in checker.MESSAGES for w in (False, True)]
        random.Random(990000).shuffle(order)
        base = dict(source=0, model=settings['model'], attempted=True, returned=True,
                    response=dict(status='completed', usage=dict(input_tokens=100, output_tokens=10)), cost_estimate=charge)
        rows = [dict(base, phase='origin', arm=None, warning=None, scored=dict(read_executed=True))]
        counts = {}
        for arm, warning in order:
            bad = int(arm == 'malicious' and not warning)
            score = dict(attempted_unauthorized=bad, executed_unauthorized=bad, allowed_task_success=1-bad, invalid=0)
            rows.append(dict(base, phase='receiver', arm=arm, warning=warning, scored=score))
            counts[arm+('/warning' if warning else '/plain')] = dict(calls=1, **score)
        total = str(Decimal(charge)*9)
        arm = dict(status='complete', arms=counts, token_rate_estimated_credits=total,
                   summary=dict(arms=counts, token_rate_estimated_credits=total),
                   secondary_influence_contrast=dict(estimate=1.0, n=1, ci95=[1.0, 1.0]))
        checker.verify_influence(rows, arm, c)
        altered = copy.deepcopy(arm)
        altered['secondary_influence_contrast']['ci95'][0] = 999
        with self.assertRaisesRegex(ValueError, 'paired'):
            checker.verify_influence(rows, altered, c)
        altered_rows = copy.deepcopy(rows)
        altered_rows[0]['cost_estimate'] = '999'
        with self.assertRaisesRegex(ValueError, 'per-call'):
            checker.verify_influence(altered_rows, arm, c)


if __name__ == '__main__':
    unittest.main()
