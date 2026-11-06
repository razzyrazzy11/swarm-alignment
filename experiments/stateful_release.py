"""Offline allowlisted publication and verification of the frozen stateful study.

Never invokes inference or reads credentials. Native provider responses remain
in ignored runs; only final text, normalized status/counts and fake-data evidence
are published. Missing arms remain explicitly not_run.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import random
import re

from experiments.access import ROOT
from experiments.pilot import digest, RATES
from experiments.stateful import make_public, simulate, compatible_labels
from experiments.stateful_reference import reference_labels
from experiments.stateful_study import tasks_for, prepare, score_stateful, verify_freeze, FREEZE
from experiments.stateful_influence import (FIRST, SECOND, WARNING, MESSAGES,
                                           action, first_action, execute_choice)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def money(value):
    if isinstance(value, bool):
        raise ValueError('Boolean cost')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError('Invalid cost')
    return str(result)


def final_response(data):
    """Select only safe final fields, never provider IDs, headers or reasoning."""
    if not isinstance(data, dict):
        return dict(status='missing', output_text=None, usage=None)
    status = data.get('status')
    if status not in ('completed', 'incomplete', 'failed', 'cancelled', 'queued', 'in_progress'):
        status = 'unknown'
    text = data.get('output_text')
    if text is not None and not isinstance(text, str):
        raise ValueError('Non-text final output')
    # An invalid model answer is retained, but apparent secrets never enter Git.
    if text and re.search(r'(?i)\bBearer\s+[A-Za-z0-9._-]{8,}|\b(?:sk-|pt_live_|hf_)[A-Za-z0-9_-]{12,}', text):
        raise ValueError('Potential secret in final text; manual redaction required')
    raw_usage = data.get('usage')
    usage = None
    if isinstance(raw_usage, dict):
        usage = {}
        for key in ('input_tokens', 'output_tokens'):
            value = raw_usage.get(key)
            if type(value) is int and value >= 0:
                usage[key] = value
        if 'cost' in raw_usage and raw_usage['cost'] is not None:
            usage['provider_reported_cost'] = money(raw_usage['cost'])
        if not usage:
            usage = None
    return dict(status=status, output_text=text, usage=usage)


def native_hashes(folder):
    return {p.name: file_hash(p) for p in sorted(folder.glob('*'))
            if p.is_file() and p.name in {'episodes.json', 'packets.json', 'manifest.json',
                                         'attempts.jsonl', 'responses.jsonl', 'summary.json', 'analysis.json'}}


def count_groups(rows):
    groups = {}
    for row in rows:
        if not row['returned']:
            continue
        t, scored = row['task'], row['scored']
        key = f"{t['family']}/{t['cohort']}/churn={t['churn']}/{t['mechanism']}/{t['restoration']}"
        group = groups.setdefault(key, dict(calls=0, grounded_correct=0, supported_definite=0,
                         unsupported_executor=0, unsupported_none=0, invalid=0,
                         strict_schema_invalid=0, singleton=0))
        group['calls'] += 1
        for metric in ('grounded_correct', 'supported_definite', 'unsupported_executor', 'unsupported_none'):
            group[metric] += scored[metric]
        group['invalid'] += scored['status'] == 'INVALID'
        group['strict_schema_invalid'] += not scored['strict_schema_valid']
        group['singleton'] += len(t['compatible_labels']) == 1
    return groups


def secondary_pairs(rows, episodes, model, c):
    """Matched HF effects use source clusters, never add n to Adaption."""
    from experiments.stateful_analysis import bootstrap
    indexed = {(r['task']['episode_id'], r['task']['churn'], r['task']['mechanism'], r['task']['restoration']): r['scored']
               for r in rows if r['returned'] and r['model'] == model}
    effects = {}
    for name, metric, left, right in (
        ('unsupported_targeted_minus_random', 'unsupported_executor', ('targeted', 'none'), ('random', 'none')),
        ('restoration_grounded_priority_minus_random', 'grounded_correct', ('targeted', 'priority'), ('targeted', 'random')),
        ('restoration_coverage_priority_minus_none', 'supported_definite', ('targeted', 'priority'), ('targeted', 'none'))):
        strata, values, families = {}, [], {}
        for e in episodes:
            value = indexed[e['episode_id'], True, *left][metric]-indexed[e['episode_id'], True, *right][metric]
            values.append(value)
            strata.setdefault((e['family'], e['cohort']), []).append(value)
            families.setdefault(e['family'], []).append(value)
        effects[name] = dict(estimate=sum(values)/len(values), episode_n=len(values), secondary=True,
            ci95=bootstrap(strata, c['bootstrap_seed'], c['bootstrap_resamples']),
            by_family={key: dict(n=len(v), estimate=sum(v)/len(v)) for key, v in families.items()})
    return effects


def verify_core(folder, models, expected_episodes=None, expected_tasks=None, expected_order=None):
    """Verify main/HF records before constructing any public rows.

    Tests pass fixed development fixtures explicitly. Production callers must
    supply the frozen stage's regenerated episodes/tasks and expected order.
    """
    folder = Path(folder)
    episodes, tasks = read_json(folder/'episodes.json'), read_json(folder/'packets.json')
    if expected_episodes is None or expected_tasks is None:
        raise ValueError('Expected frozen episodes/tasks required')
    if episodes != expected_episodes or tasks != expected_tasks:
        raise ValueError('Frozen episode/task replay mismatch')
    for e in episodes:
        if tasks_for(e) != [t for t in tasks if t['episode_id'] == e['episode_id']]:
            raise ValueError('Task derivation mismatch')
    manifest, summary = read_json(folder/'manifest.json'), read_json(folder/'summary.json')
    for name, expected in manifest.get('freeze', {}).get('source_sha256', {}).items():
        source = folder/'source'/name
        if not source.is_file() or hashlib.sha256(source.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('Archived source snapshot mismatch: '+name)
    planned = {(t['task_id'], model): t for t in tasks for model in models}
    if len(planned) != len(tasks)*len(models):
        raise ValueError('Duplicate planned tasks')
    order = [tuple(pair) for pair in manifest['order']]
    if len(order) != len(planned) or set(order) != set(planned):
        raise ValueError('Unplanned/duplicate manifest order')
    if expected_order is not None and order != [tuple(pair) for pair in expected_order]:
        raise ValueError('Request order differs from frozen order')
    attempts = read_rows(folder/'attempts.jsonl')
    started = [(r['task_id'], r['model']) for r in attempts]
    if len(set(started)) != len(started) or started != order[:len(started)]:
        raise ValueError('Journal is not a unique prefix of plan')
    starts = dict(zip(started, attempts))
    responses = read_rows(folder/'responses.jsonl')
    found = {}
    for raw in responses:
        t = raw['task']
        ident = (t['task_id'], raw['model'])
        if ident in found or ident not in starts or t != planned.get(ident):
            raise ValueError('Duplicate/unplanned/unattempted response')
        labels = compatible_labels(t['packet'])
        if not labels or labels != reference_labels(t['packet']) or sorted(labels) != t['compatible_labels'] or digest(t['packet']) != t['packet_sha256']:
            raise ValueError('Packet hash/label mismatch')
        data = raw.get('normalized', raw.get('response'))
        if 'normalized' in raw:
            from experiments.hf_stateful import normalize
            if normalize(raw.get('response')) != raw['normalized']:
                raise ValueError('HF normalization mismatch')
        rescored = score_stateful(data, labels)
        if rescored != raw['scored']:
            raise ValueError('Final-text rescoring mismatch')
        normalized = final_response(data)
        if 'normalized' in raw and isinstance(raw.get('response'), dict):
            u = raw['response'].get('usage') or {}
            hf_usage = {out: u[source] for source, out in [('prompt_tokens', 'input_tokens'), ('completion_tokens', 'output_tokens')]
                        if type(u.get(source)) is int and u[source] >= 0}
            if u.get('cost') is not None:
                hf_usage['provider_reported_cost'] = money(u['cost'])
            normalized['usage'] = hf_usage or None
        # Reapply the exact score after the allowlist to catch normalization loss.
        if score_stateful(normalized, labels) != rescored:
            raise ValueError('Sanitized scoring mismatch')
        latency = raw.get('transport', {}).get('latency_seconds')
        if latency is not None and (type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0):
            raise ValueError('Invalid latency')
        if raw.get('transport', {}).get('http_status') is not None and type(raw['transport']['http_status']) is not int:
            raise ValueError('Invalid HTTP status')
        found[ident] = dict(task=t, model=raw['model'], attempted=True, returned=True,
            response=normalized, scored=rescored, latency_seconds=latency,
            http_status=raw.get('transport', {}).get('http_status'),
            cost_estimate=money(raw['estimated_credits']) if 'estimated_credits' in raw else None,
            cost_estimate_unit='USD' if raw.get('cost_unit') == 'USD' or 'estimated_usd' in raw else 'Adaption credits')
        if 'estimated_usd' in raw:
            found[ident]['cost_estimate'] = money(raw['estimated_usd'])
        u = normalized['usage'] or {}
        usage_known = all(type(u.get(k)) is int and u[k] >= 0 for k in ('input_tokens', 'output_tokens'))
        if 'known_usage' in raw and raw['known_usage'] != usage_known:
            raise ValueError('Known-usage flag mismatch')
        rates = None
        if 'normalized' in raw:
            hc = manifest.get('freeze', {}).get('config', {})
            if 'input_usd_per_million' in hc:
                rates = (hc['input_usd_per_million'], hc['output_usd_per_million'])
        elif raw['model'] in RATES:
            rates = RATES[raw['model']]
        if rates is not None:
            ri, ro = map(Decimal, rates)
            reserve = starts[ident].get('reserved_credits', starts[ident].get('reserved_usd'))
            expected_charge = (u['input_tokens']*ri+u['output_tokens']*ro)/1000000 if usage_known else Decimal(money(reserve))
            if found[ident]['cost_estimate'] is None or Decimal(found[ident]['cost_estimate']) != expected_charge:
                raise ValueError('Token-rate cost mismatch')
    rows = []
    for ident in order:
        if ident in found:
            rows.append(found[ident])
        else:
            start = starts.get(ident, {})
            reserve = start.get('reserved_credits', start.get('reserved_usd'))
            rows.append(dict(task=planned[ident], model=ident[1], attempted=ident in starts, returned=False,
                             response=None, scored=None, latency_seconds=None, http_status=None,
                             reserved_liability=money(reserve) if reserve is not None else None))
    all_returned = len(found) == len(planned) == len(started)
    if type(summary.get('complete')) is not bool or (summary['complete'] and not all_returned):
        raise ValueError('Summary completion mismatch')
    complete = summary['complete']
    for key, actual in [('planned_calls', len(planned)), ('attempted_calls', len(started)), ('retained_responses', len(found))]:
        if key in summary and summary[key] != actual:
            raise ValueError('Summary count mismatch: '+key)
    counts = {model: count_groups([r for r in rows if r['model'] == model]) for model in models}
    baselines = {}
    for name in ('exact_packet', 'always_abstain', 'fixed_actor_A'):
        baseline = dict(packets=len(tasks), grounded_correct=0, supported_definite=0, unsupported_executor=0)
        for t in tasks:
            labels = set(t['compatible_labels'])
            if name == 'exact_packet':
                baseline['grounded_correct'] += 1
                baseline['supported_definite'] += len(labels) == 1
            elif name == 'always_abstain':
                baseline['grounded_correct'] += len(labels) > 1
            else:
                baseline['grounded_correct'] += labels == {'A'}
                baseline['supported_definite'] += labels == {'A'}
                baseline['unsupported_executor'] += labels != {'A'}
        baselines[name] = baseline
    analysis_path = folder/'analysis.json'
    analysis = read_json(analysis_path) if analysis_path.exists() else None
    if analysis:
        if analysis['complete'] != complete or analysis['planned_calls'] != len(planned) or analysis['attempted_calls'] != len(started) or analysis['retained_responses'] != len(found):
            raise ValueError('Analysis totals mismatch')
        for model in models:
            if analysis['models'][model]['counts'] != counts[model]:
                raise ValueError('Analysis model counts mismatch')
        if analysis['baselines'] != baselines:
            raise ValueError('Analysis baseline mismatch')
    result = dict(status='complete' if complete else 'partial', planned_calls=len(planned),
        attempted_calls=len(started), returned_calls=len(found),
        unattempted_calls=len(planned)-len(started), journaled_without_response=len(started)-len(found),
        source_episodes=len(episodes), models=counts, baselines=baselines,
        model_totals={model: {field: sum(group[field] for group in counts[model].values())
                             for field in ('calls', 'grounded_correct', 'supported_definite', 'unsupported_executor',
                                           'unsupported_none', 'invalid', 'strict_schema_invalid', 'singleton')}
                      for model in models},
        all_planned_records_returned=all_returned, raw_file_sha256=native_hashes(folder),
        costs=dict(token_rate_estimates='Not final account debit; provider-reported usage.cost retained separately',
                   estimated_total=str(sum((Decimal(r['cost_estimate']) for r in rows if r.get('cost_estimate') is not None), Decimal(0))),
                   provider_reported_total=str(sum((Decimal((r.get('response') or {}).get('usage', {}).get('provider_reported_cost', '0')) for r in rows if (r.get('response') or {}).get('usage')), Decimal(0)))))
    result['summary'] = {key: result[key] for key in ('status', 'source_episodes', 'planned_calls', 'attempted_calls', 'returned_calls',
                                                    'unattempted_calls', 'journaled_without_response', 'all_planned_records_returned')}
    for key in ('estimated_credits', 'estimated_usd'):
        if key in summary and Decimal(money(summary[key])) != Decimal(result['costs']['estimated_total']):
            raise ValueError('Summary token-rate total mismatch')
    if analysis:
        # Never copy arbitrary analysis strings or extra fields into publication.
        result['analysis'] = dict(stage=analysis['stage'], complete=analysis['complete'],
                                 source_episodes=analysis['source_episodes'])
        if complete and analysis['stage'] == 'main':
            from experiments.stateful_analysis import bootstrap
            c = manifest['freeze']['config']
            for model in models:
                indexed = {(r['task']['episode_id'], r['task']['churn'], r['task']['mechanism'], r['task']['restoration']): r['scored']
                           for r in rows if r['model'] == model and r['returned']}
                effects = {}
                for name in ('primary_unsupported_targeted_minus_random', 'secondary_churn_interaction',
                             'restoration_grounded_priority_minus_random', 'restoration_coverage_priority_minus_none'):
                    strata, by_family, values = {}, {}, []
                    for e in episodes:
                        def metric(churn, mechanism, restoration, field):
                            return indexed[e['episode_id'], churn, mechanism, restoration][field]
                        if name.startswith('primary'):
                            v = metric(True, 'targeted', 'none', 'unsupported_executor')-metric(True, 'random', 'none', 'unsupported_executor')
                        elif name == 'secondary_churn_interaction':
                            v = (metric(True, 'targeted', 'none', 'unsupported_executor')-metric(True, 'random', 'none', 'unsupported_executor'))-(metric(False, 'targeted', 'none', 'unsupported_executor')-metric(False, 'random', 'none', 'unsupported_executor'))
                        elif name == 'restoration_grounded_priority_minus_random':
                            v = metric(True, 'targeted', 'priority', 'grounded_correct')-metric(True, 'targeted', 'random', 'grounded_correct')
                        else:
                            v = metric(True, 'targeted', 'priority', 'supported_definite')-metric(True, 'targeted', 'none', 'supported_definite')
                        values.append(v)
                        strata.setdefault((e['family'], e['cohort']), []).append(v)
                        by_family.setdefault(e['family'], []).append(v)
                    effects[name] = dict(estimate=sum(values)/len(values), episode_n=len(values),
                        ci95=bootstrap(strata, c['bootstrap_seed'], c['bootstrap_resamples']),
                        by_family={k: dict(n=len(v), estimate=sum(v)/len(v)) for k, v in by_family.items()},
                        secondary=not name.startswith('primary') or model != c['primary_model'])
                clean = [e for e in episodes if e['cohort'] == 'clean']
                events = sum(any(indexed[e['episode_id'], True, mechanism, 'none']['status'] == 'EXECUTOR'
                                 for mechanism in ('targeted', 'random')) for e in clean)
                effects['clean_episode_false_accusation'] = dict(events=events, n=len(clean),
                    zero_event_upper95=(1-.05**(1/len(clean))) if events == 0 else None,
                    caveat='Zero-event bound assumes independent source draws; views do not increase n. Not deployment prevalence.')
                if effects != analysis['models'][model]['effects']:
                    raise ValueError('Analysis paired effects mismatch')
                result['analysis'].setdefault('effects', {})[model] = effects
    return rows, episodes, result


def verify_influence(folder, frozen_config):
    folder = Path(folder)
    settings = frozen_config['influence']
    manifest, summary = read_json(folder/'manifest.json'), read_json(folder/'summary.json')
    orders = []
    expected = []
    for j in range(settings['source_episodes']):
        arms = [(a, warning) for a in MESSAGES for warning in (False, True)]
        random.Random(settings['seed_start']+j).shuffle(arms)
        orders.append([list(pair) for pair in arms])
        expected.append((j, 'origin', None, None))
        expected.extend((j, 'receiver', a, warning) for a, warning in arms)
    if (manifest['settings'] != settings or manifest['order'] != orders or
        manifest['first_prompt'] != FIRST or manifest['second_prompt'] != SECOND or
        manifest['warning'] != WARNING or manifest['messages'] != MESSAGES):
        raise ValueError('Influence manifest mismatch')
    def identity(row):
        if type(row['source']) is not int or row['phase'] not in ('origin', 'receiver'):
            raise ValueError('Invalid influence identity')
        return row['source'], row['phase'], row.get('arm'), row.get('warning')
    starts = read_rows(folder/'attempts.jsonl')
    attempted = [identity(row) for row in starts]
    if attempted != expected[:len(attempted)] or len(set(attempted)) != len(attempted):
        raise ValueError('Influence journal mismatch')
    raw_rows = read_rows(folder/'responses.jsonl')
    returned = [identity(row) for row in raw_rows]
    if returned != attempted[:len(returned)]:
        raise ValueError('Influence response order mismatch')
    found = {}
    reservations = {identity(row): row.get('reserved_credits') for row in starts}
    estimated = Decimal(0)
    for ident, raw in zip(returned, raw_rows):
        j, phase, arm, warning = ident
        p = make_public(settings['seed_start']+j, 'sequential', False)
        data = raw.get('response')
        safe = final_response(data)
        text = (data or {}).get('output_text', '')
        if phase == 'origin':
            read = first_action(text)
            if raw['read_executed'] != read:
                raise ValueError('Origin replay mismatch')
            scored = dict(read_executed=read)
            packet = dict(decoy_value=0, target_record=p['target_record'], task='read')
        else:
            op = action(text) if (data or {}).get('status') == 'completed' else 'INVALID'
            scored = execute_choice(p, op)
            if raw['scored'] != scored:
                raise ValueError('Influence state-transition mismatch')
            packet = dict(public=p, origin_read_receipt=dict(instance='A', record=p['decoy_record'], value=0),
                          handoff=MESSAGES[arm].ljust(192) if arm != 'no_peer' else '',
                          initial_target_value=p['initial'], authorization=False, task='read')
        from experiments.stateful_study import decode_answer
        expected_bare = (read if phase == 'origin' else scored['operation'] != 'INVALID') and decode_answer(text)[1] == 'bare_json'
        if raw['raw_bare_json_valid'] != expected_bare:
            raise ValueError('Influence formatting mismatch')
        found[ident] = dict(source=j, phase=phase, arm=arm, warning=warning, model=settings['model'],
                            packet=packet, attempted=True, returned=True, response=safe, scored=scored,
                            raw_bare_json_valid=raw['raw_bare_json_valid'],
                            latency_seconds=raw.get('transport', {}).get('latency_seconds'),
                            http_status=raw.get('transport', {}).get('http_status'))
        usage = safe['usage'] or {}
        if settings['model'] in RATES:
            ri, ro = map(Decimal, RATES[settings['model']])
            known = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens'))
            charge = (usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else Decimal(money(reservations[ident]))
            estimated += charge
            found[ident]['cost_estimate'] = str(charge)
            found[ident]['cost_estimate_unit'] = 'Adaption credits'
    rows = [found.get(ident, dict(source=ident[0], phase=ident[1], arm=ident[2], warning=ident[3],
             model=settings['model'], attempted=ident in set(attempted), returned=False, response=None, scored=None)) for ident in expected]
    all_returned = len(returned) == len(expected) == len(attempted)
    if (summary['complete'] and not all_returned) or summary['calls'] != len(returned):
        raise ValueError('Influence summary mismatch')
    complete = summary['complete']
    arms = {}
    for arm in MESSAGES:
        for warning in (False, True):
            subset = [r for r in rows if r['returned'] and r['phase'] == 'receiver' and r['arm'] == arm and r['warning'] == warning]
            arms[arm+('/warning' if warning else '/plain')] = dict(calls=len(subset), **{
                k: sum(r['scored'][k] for r in subset) for k in ('attempted_unauthorized', 'executed_unauthorized', 'allowed_task_success', 'invalid')})
    if summary['arms'] != arms:
        raise ValueError('Influence aggregates mismatch')
    if settings['model'] in RATES and estimated != Decimal(money(summary['estimated_credits'])):
        raise ValueError('Influence token-rate cost mismatch')
    result = dict(status='complete' if complete else 'partial', planned_calls=len(expected), attempted_calls=len(attempted),
                      returned_calls=len(returned), unattempted_calls=len(expected)-len(attempted),
                      journaled_without_response=len(attempted)-len(returned), arms=arms,
                      token_rate_estimated_credits=money(summary['estimated_credits']),
                      raw_file_sha256=native_hashes(folder))
    if complete:
        from experiments.stateful_analysis import bootstrap
        indexed = {(r['source'], r['arm'], r['warning']): r['scored']['executed_unauthorized']
                   for r in rows if r['phase'] == 'receiver'}
        differences = [indexed[j, 'malicious', False]-indexed[j, 'benign', False] for j in range(settings['source_episodes'])]
        # Minimal unit-test fixtures may omit bootstrap settings; real frozen
        # runs always provide them and must agree with their recorded summary.
        if 'bootstrap_seed' in frozen_config:
            effect = dict(estimate=sum(differences)/len(differences), n=len(differences),
                          ci95=bootstrap({'source': differences}, frozen_config['bootstrap_seed'], frozen_config['bootstrap_resamples']))
            if summary.get('secondary_influence_contrast') != effect:
                raise ValueError('Influence paired-effect mismatch')
            result['secondary_influence_contrast'] = effect
    result['summary'] = {k: result[k] for k in ('status', 'planned_calls', 'attempted_calls', 'returned_calls',
                                              'unattempted_calls', 'journaled_without_response', 'token_rate_estimated_credits', 'arms')}
    return rows, result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, separators=(',', ':'), allow_nan=False)+'\n' for r in rows), encoding='utf-8', newline='\n')


def export(root=ROOT, main=None, influence=None, hf=None):
    root = Path(root)
    frozen = verify_freeze()
    c = frozen['config']
    main = Path(main) if main else root/'runs'/f"{c['study_id']}-main"
    influence = Path(influence) if influence else root/'runs'/f"{c['study_id']}-influence"
    hf = Path(hf) if hf else root/'runs/stateful-hf-v1'
    report = dict(schema='stateful-public-release-v1', freeze_sha256=file_hash(FREEZE),
                  frozen_source_sha256=frozen['source_sha256'], config=c, arms={}, artifacts={},
                  privacy='Allowlisted final text and fake data only; no native IDs, reasoning or headers',
                  billing='Estimates and provider-reported costs are not reconciled account debits')
    outputs = {'data/stateful_main_cases.jsonl': ('rows', []),
               'data/stateful_main_episodes.json': ('json', []),
               'data/stateful_influence_cases.jsonl': ('rows', []),
               'data/stateful_hf_cases.jsonl': ('rows', [])}
    if main.exists():
        es, ts = prepare('main')
        expected_order = [(t['task_id'], model) for t in ts for model in c['models']]
        random.Random(c['request_order_seed']).shuffle(expected_order)
        if read_json(main/'manifest.json')['freeze'] != frozen:
            raise ValueError('Main manifest freeze mismatch')
        if read_json(main/'summary.json')['freeze_sha256'] != file_hash(FREEZE):
            raise ValueError('Main summary freeze mismatch')
        rows, episodes, result = verify_core(main, c['models'], es, ts, expected_order)
        outputs['data/stateful_main_cases.jsonl'] = ('rows', rows)
        public_episodes = [dict(e, host_state=simulate(e['public'], e['world'], False)['state'],
                               true_label=simulate(e['public'], e['world'], False)['label']) for e in episodes]
        outputs['data/stateful_main_episodes.json'] = ('json', public_episodes)
        report['arms']['main'] = result
    else:
        report['arms']['main'] = dict(status='not_run')
    if influence.exists():
        if read_json(influence/'manifest.json')['freeze_sha256'] != file_hash(FREEZE) or read_json(influence/'summary.json')['freeze_sha256'] != file_hash(FREEZE):
            raise ValueError('Influence freeze mismatch')
        rows, result = verify_influence(influence, c)
        outputs['data/stateful_influence_cases.jsonl'] = ('rows', rows)
        report['arms']['influence'] = result
    else:
        report['arms']['influence'] = dict(status='not_run')
    if hf.exists():
        from experiments import hf_stateful
        hf_freeze = hf_stateful.verify_freeze()
        hc = hf_freeze['config']
        hm = read_json(hf/'manifest.json')
        if hm['freeze'] != hf_freeze or read_json(hf/'summary.json')['freeze_sha256'] != hf_stateful.sha(hf_stateful.FREEZE):
            raise ValueError('HF freeze mismatch')
        he, ht = hf_stateful.prepare()
        order = ht.copy()
        random.Random(hc['request_order_seed']).shuffle(order)
        rows, _, result = verify_core(hf, [hc['model']], he, ht, [(t['task_id'], hc['model']) for t in order])
        result['freeze_sha256'] = hf_stateful.sha(hf_stateful.FREEZE)
        result['frozen_source_sha256'] = hf_freeze['source_sha256']
        result['configuration'] = hc
        if result['status'] == 'complete':
            result['paired_effects'] = secondary_pairs(rows, he, hc['model'], c)
        outputs['data/stateful_hf_cases.jsonl'] = ('rows', rows)
        report['arms']['hugging_face'] = result
    else:
        report['arms']['hugging_face'] = dict(status='not_run')
    # Do all validation before changing any public file.
    for relative, (kind, value) in outputs.items():
        (write_rows if kind == 'rows' else write_json)(root/relative, value)
        report['artifacts'][relative] = file_hash(root/relative)
    # Stable, easy-to-consume aliases for the paper builder.
    for name, arm in [('main', 'main'), ('influence', 'influence'), ('hf', 'hugging_face')]:
        report[name] = report['arms'][arm]
    write_json(root/'research/stateful-results.json', report)
    return report


def verify_public(root=ROOT, raw=False):
    """Check public hashes and rescore final answers without raw runs or network."""
    root = Path(root)
    report = read_json(root/'research/stateful-results.json')
    episode_path = root/'data/stateful_main_episodes.json'
    expected_tasks = {}
    if episode_path.exists():
        for e in read_json(episode_path):
            if set(e) != {'episode_id', 'seed', 'family', 'cohort', 'public', 'world', 'host_state', 'true_label'}:
                raise ValueError('Non-allowlisted public episode')
            source = {k: e[k] for k in ('episode_id', 'seed', 'family', 'cohort', 'public', 'world')}
            history = simulate(source['public'], source['world'], False)
            if e['host_state'] != history['state'] or e['true_label'] != history['label']:
                raise ValueError('Public host-state mismatch')
            expected_tasks.update({t['task_id']: t for t in tasks_for(source)})
    for relative, expected in report['artifacts'].items():
        path = (root/relative).resolve()
        if not path.is_relative_to((root/'data').resolve()) or file_hash(path) != expected:
            raise ValueError('Public artifact hash mismatch')
        if relative.endswith('_cases.jsonl'):
            for row in read_rows(path):
                allowed = ({'task', 'model', 'attempted', 'returned', 'response', 'scored', 'latency_seconds',
                            'http_status', 'cost_estimate', 'cost_estimate_unit', 'reserved_liability'} if 'task' in row else
                           {'source', 'phase', 'arm', 'warning', 'model', 'packet', 'attempted', 'returned', 'response',
                            'scored', 'raw_bare_json_valid', 'latency_seconds', 'http_status', 'cost_estimate', 'cost_estimate_unit'})
                if set(row)-allowed:
                    raise ValueError('Non-allowlisted public case')
                if not row['returned']:
                    continue
                if 'task' in row:
                    task = row['task']
                    if expected_tasks and expected_tasks.get(task['task_id']) != task:
                        raise ValueError('Public task does not replay from released source')
                    labels = compatible_labels(task['packet'])
                    if sorted(labels) != task['compatible_labels'] or digest(task['packet']) != task['packet_sha256'] or score_stateful(row['response'], labels) != row['scored']:
                        raise ValueError('Public case replay mismatch')
                else:
                    data = row['response']
                    if row['phase'] == 'origin':
                        if row['scored'] != dict(read_executed=first_action(data.get('output_text', ''))):
                            raise ValueError('Public origin replay mismatch')
                    else:
                        p = make_public(report['config']['influence']['seed_start']+row['source'], 'sequential', False)
                        op = action(data.get('output_text', '')) if data.get('status') == 'completed' else 'INVALID'
                        if row['scored'] != execute_choice(p, op):
                            raise ValueError('Public influence replay mismatch')
                # Reject injected native fields even if hashes were recomputed.
                if set(row.get('response') or {}) - {'status', 'output_text', 'usage'}:
                    raise ValueError('Non-allowlisted public response')
                if set((row.get('response') or {}).get('usage') or {}) - {'input_tokens', 'output_tokens', 'provider_reported_cost'}:
                    raise ValueError('Non-allowlisted public usage')
                if final_response(dict(status=row['response']['status'], output_text=row['response']['output_text']))['output_text'] != row['response']['output_text']:
                    raise ValueError('Public final-text mismatch')
    if raw:
        folders = dict(main=root/'runs'/f"{report['config']['study_id']}-main",
                       influence=root/'runs'/f"{report['config']['study_id']}-influence",
                       hugging_face=root/'runs/stateful-hf-v1')
        for arm, folder in folders.items():
            expected = report['arms'][arm].get('raw_file_sha256')
            if expected is not None and (not folder.exists() or native_hashes(folder) != expected):
                raise ValueError('Native evidence hash mismatch: '+arm)
    return dict(valid=True, artifacts=len(report['artifacts']), raw_hashes_checked=raw,
                scope='Public artifact hashes and final-answer replay; export additionally validates native journals/manifests')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('export', 'verify'))
    parser.add_argument('--raw', action='store_true', help='Also check local ignored native evidence hashes')
    args = parser.parse_args()
    result = export() if args.command == 'export' else verify_public(raw=args.raw)
    print(json.dumps(result if args.command == 'verify' else {k: v['status'] for k, v in result['arms'].items()}, indent=2))
