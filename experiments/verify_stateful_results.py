"""Replay published aggregate statistics offline without changing frozen code.

This checks publication consistency, not provider invoices or the realism of the
finite grammar. No credentials, network or ignored native runs are needed.
"""
from decimal import Decimal
import json
from pathlib import Path
import random
import tempfile

from experiments.access import ROOT
from experiments import stateful_release as publication
from experiments import stateful_analysis as analysis
from experiments.stateful_study import FREEZE, prepare, sha, verify_freeze
from experiments.stateful_influence import MESSAGES
from experiments.pilot import RATES


FIELDS = ('calls', 'grounded_correct', 'supported_definite', 'unsupported_executor',
          'unsupported_none', 'invalid', 'strict_schema_invalid', 'singleton')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_counts(rows, arm):
    """Recount every planned/attempted/returned distinction and view metric."""
    require(all(type(r['attempted']) is bool and type(r['returned']) is bool and
                (not r['returned'] or r['attempted']) for r in rows), 'Invalid call-state flags')
    if arm['status'] == 'not_run':
        require(not rows, 'not_run arm has published cases')
        return
    returned = [r for r in rows if r['returned']]
    attempted = sum(r['attempted'] for r in rows)
    expected = dict(planned_calls=len(rows), attempted_calls=attempted, returned_calls=len(returned),
                    unattempted_calls=len(rows)-attempted, journaled_without_response=attempted-len(returned))
    require(arm['status'] in ('complete', 'partial'), 'Unknown arm status')
    for key, value in expected.items():
        require(arm[key] == value and arm['summary'][key] == value, 'Count mismatch: '+key)
    require(arm['summary']['status'] == arm['status'], 'Summary status mismatch')
    require(arm['status'] != 'complete' or len(returned) == len(rows) == attempted, 'Incomplete arm called complete')
    if not rows or 'task' not in rows[0]:
        return
    identities = [(r['task']['task_id'], r['model']) for r in rows]
    require(len(set(identities)) == len(rows), 'Duplicate published task/model')
    groups = {model: {} for model in {r['model'] for r in rows}}
    for row in returned:
        t, score = row['task'], row['scored']
        key = f"{t['family']}/{t['cohort']}/churn={t['churn']}/{t['mechanism']}/{t['restoration']}"
        count = groups[row['model']].setdefault(key, dict.fromkeys(FIELDS, 0))
        count['calls'] += 1
        for field in ('grounded_correct', 'supported_definite', 'unsupported_executor', 'unsupported_none'):
            count[field] += score[field]
        count['invalid'] += score['status'] == 'INVALID'
        count['strict_schema_invalid'] += not score['strict_schema_valid']
        count['singleton'] += len(t['compatible_labels']) == 1
    totals = {model: {field: sum(g[field] for g in groups[model].values()) for field in FIELDS} for model in groups}
    require(groups == arm['models'], 'Per-view aggregates mismatch')
    require(totals == arm['model_totals'], 'Model totals mismatch')
    sources = len({r['task']['episode_id'] for r in rows})
    require(sources == arm['source_episodes'] == arm['summary']['source_episodes'], 'Source n mismatch')
    all_returned = len(returned) == len(rows) == attempted
    require(arm['all_planned_records_returned'] == all_returned == arm['summary']['all_planned_records_returned'], 'Collection status mismatch')
    estimated = sum((Decimal(publication.money(r['cost_estimate'])) for r in returned if r.get('cost_estimate') is not None), Decimal(0))
    reported = sum((Decimal(publication.money((r['response'].get('usage') or {})['provider_reported_cost']))
                    for r in returned if 'provider_reported_cost' in (r['response'].get('usage') or {})), Decimal(0))
    require(estimated == Decimal(publication.money(arm['costs']['estimated_total'])), 'Estimated cost total mismatch')
    require(reported == Decimal(publication.money(arm['costs']['provider_reported_total'])), 'Reported cost total mismatch')


def replay_main(root, rows, arm, frozen):
    episodes = publication.read_json(root/'data/stateful_main_episodes.json')
    episodes = [{k: e[k] for k in ('episode_id', 'seed', 'family', 'cohort', 'public', 'world')} for e in episodes]
    expected_episodes, packets = prepare('main')
    require(episodes == expected_episodes, 'Published episodes differ from frozen sample')
    expected_ids = {(t['task_id'], model) for t in packets for model in frozen['config']['models']}
    require({(r['task']['task_id'], r['model']) for r in rows} == expected_ids and len(rows) == len(expected_ids), 'Main planned grid mismatch')
    with tempfile.TemporaryDirectory(prefix='stateful-public-replay-') as name:
        out = Path(name)
        publication.write_json(out/'episodes.json', episodes)
        publication.write_json(out/'packets.json', packets)
        publication.write_json(out/'manifest.json', dict(stage='main', freeze=frozen))
        publication.write_json(out/'summary.json', dict(stage='main', complete=arm['status'] == 'complete', freeze_sha256=sha(FREEZE)))
        publication.write_rows(out/'attempts.jsonl', [dict(task_id=r['task']['task_id'], model=r['model'],
            reserved_credits=r.get('reserved_liability') or '0') for r in rows if r['attempted']])
        publication.write_rows(out/'responses.jsonl', [dict(task=r['task'], model=r['model'], response=r['response'], scored=r['scored'])
                                                     for r in rows if r['returned']])
        recalculated = analysis.analyze(out)
    require(arm['models'] == {m: v['counts'] for m, v in recalculated['models'].items()}, 'Main replay counts mismatch')
    require(arm['baselines'] == recalculated['baselines'], 'Main baselines mismatch')
    if arm['status'] == 'complete':
        require(arm['analysis']['effects'] == {m: v['effects'] for m, v in recalculated['models'].items()}, 'Main effects/intervals mismatch')
    else:
        require(not arm.get('analysis', {}).get('effects'), 'Partial main has confirmatory effects')
    if 'analysis' in arm:
        for key in ('stage', 'complete', 'source_episodes'):
            require(arm['analysis'][key] == recalculated[key], 'Main analysis metadata mismatch')


def verify_influence(rows, arm, c):
    settings = c['influence']
    expected = []
    for source in range(settings['source_episodes']):
        order = [(a, w) for a in MESSAGES for w in (False, True)]
        random.Random(settings['seed_start']+source).shuffle(order)
        expected.append((source, 'origin', None, None))
        expected.extend((source, 'receiver', a, w) for a, w in order)
    require([(r['source'], r['phase'], r['arm'], r['warning']) for r in rows] == expected, 'Influence planned grid mismatch')
    counts = {}
    for a in MESSAGES:
        for warning in (False, True):
            selected = [r for r in rows if r['returned'] and r['phase'] == 'receiver' and r['arm'] == a and r['warning'] == warning]
            counts[a+('/warning' if warning else '/plain')] = dict(calls=len(selected), **{
                k: sum(r['scored'][k] for r in selected) for k in ('attempted_unauthorized', 'executed_unauthorized', 'allowed_task_success', 'invalid')})
    require(arm['arms'] == counts == arm['summary']['arms'], 'Influence arm counts mismatch')
    ri, ro = map(Decimal, RATES[settings['model']])
    reserve = (18000*ri+settings['max_output_tokens']*ro)/1000000
    for row in (r for r in rows if r['returned']):
        require(row['model'] == settings['model'], 'Influence model mismatch')
        usage = row['response'].get('usage') or {}
        known = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens'))
        cost = (usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve
        require(Decimal(publication.money(row['cost_estimate'])) == cost, 'Influence per-call cost mismatch')
    total = sum((Decimal(publication.money(r['cost_estimate'])) for r in rows if r['returned'] and r.get('cost_estimate') is not None), Decimal(0))
    require(total == Decimal(publication.money(arm['token_rate_estimated_credits'])) == Decimal(publication.money(arm['summary']['token_rate_estimated_credits'])), 'Influence cost mismatch')
    if arm['status'] == 'complete':
        indexed = {(r['source'], r['arm'], r['warning']): r['scored']['executed_unauthorized'] for r in rows if r['phase'] == 'receiver'}
        differences = [indexed[j, 'malicious', False]-indexed[j, 'benign', False] for j in range(settings['source_episodes'])]
        effect = dict(estimate=sum(differences)/len(differences), n=len(differences),
                      ci95=analysis.bootstrap({'source': differences}, c['bootstrap_seed'], c['bootstrap_resamples']))
        require(arm['secondary_influence_contrast'] == effect, 'Influence paired effect mismatch')
    else:
        require('secondary_influence_contrast' not in arm, 'Partial influence has an effect interval')


def verify(root=ROOT):
    root = Path(root)
    publication.verify_public(root)
    report = publication.read_json(root/'research/stateful-results.json')
    frozen = verify_freeze()
    require(report['config'] == frozen['config'] and report['frozen_source_sha256'] == frozen['source_sha256'] and
            report['freeze_sha256'] == publication.file_hash(FREEZE), 'Aggregate freeze mismatch')
    for alias, arm_name, filename in [('main', 'main', 'stateful_main_cases.jsonl'),
                                     ('hf', 'hugging_face', 'stateful_hf_cases.jsonl'),
                                     ('influence', 'influence', 'stateful_influence_cases.jsonl')]:
        arm = report['arms'][arm_name]
        require(report[alias] == arm, 'Aggregate alias mismatch: '+alias)
        rows = publication.read_rows(root/'data'/filename)
        verify_counts(rows, arm)
        if arm['status'] == 'not_run':
            continue
        if alias == 'main':
            replay_main(root, rows, arm, frozen)
        elif alias == 'hf':
            from experiments import hf_stateful
            hf = hf_stateful.verify_freeze()
            episodes, tasks = hf_stateful.prepare()
            require(arm['configuration'] == hf['config'] and arm['freeze_sha256'] == hf_stateful.sha(hf_stateful.FREEZE) and
                    arm['frozen_source_sha256'] == hf['source_sha256'], 'HF freeze/configuration mismatch')
            require({(r['task']['task_id'], r['model']) for r in rows} == {(t['task_id'], hf['config']['model']) for t in tasks}, 'HF planned grid mismatch')
            if arm['status'] == 'complete':
                require(arm['paired_effects'] == publication.secondary_pairs(rows, episodes, hf['config']['model'], frozen['config']), 'HF paired effects mismatch')
            else:
                require('paired_effects' not in arm, 'Partial HF has effect intervals')
        else:
            verify_influence(rows, arm, frozen['config'])
    return dict(valid=True, scope='Public counts, aliases, frozen analysis, paired effects and cost arithmetic; not invoices')


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
