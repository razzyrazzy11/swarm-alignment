"""Explicit sanitized-snapshot replay of historical PUBLIC mathematics.

This is a new adapter, not the historical full protocol/source validator. The
outer admission callback must establish the disclosed snapshot and attested
private original-protocol admission. Frozen scorers, host reconstruction,
statistics and bootstrap functions remain unchanged. No API or private-journal
entry point is called here. Stateful main contrasts are assembled explicitly
below because the old report builder combines them with protocol admission.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys


SCOPE = 'sanitized_public_snapshot_v2'
ADMISSION_KEYS = {'schema_version', 'canonical_commit', 'disclosure_manifest_sha256',
                  'files', 'scope', 'private_original_protocol_admission'}
HEX = re.compile(r'[0-9a-f]{64}')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'Duplicate snapshot JSON key')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           ValueError('Nonfinite snapshot JSON')))
    def finite(item):
        if type(item) is float:
            require(math.isfinite(item), 'Nonfinite snapshot JSON')
        elif type(item) is dict:
            for child in item.values():
                finite(child)
        elif type(item) is list:
            for child in item:
                finite(child)
    finite(value)
    return value


def schema(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), label + ' schema differs')


class AdmittedFiles:
    """Read only declared regular files; recheck the entire commitment twice."""
    def __init__(self, root, verify_admission):
        raw = Path(root)
        require(raw.is_dir() and not raw.is_symlink(), 'Snapshot root must be a regular directory')
        self.root = raw.resolve()
        require(callable(verify_admission), 'Explicit snapshot admission callback required')
        value = verify_admission(self.root)
        schema(value, ADMISSION_KEYS, 'Snapshot admission')
        require(type(value['schema_version']) is int and value['schema_version'] == 1 and
                type(value['canonical_commit']) is str and
                re.fullmatch(r'[0-9a-f]{40}', value['canonical_commit']) is not None and
                type(value['disclosure_manifest_sha256']) is str and
                HEX.fullmatch(value['disclosure_manifest_sha256']) is not None and
                value['scope'] == SCOPE and
                value['private_original_protocol_admission'] == 'attested_not_publicly_repeated',
                'Snapshot admission identity/scope differs')
        require(type(value['files']) is dict and bool(value['files']) and
                all(type(k) is str and type(v) is str and HEX.fullmatch(v) is not None
                    for k, v in value['files'].items()), 'Snapshot admission file map differs')
        self.admission = deepcopy(value)
        self.verify_admission = verify_admission
        self.files = deepcopy(value['files'])
        self.used = set()
        self.check_imports = False
        self.check_all()
        self.initial_inventory = self.inventory()

    def inventory(self):
        """Bind every regular checkout file, excluding only Git administration.

        The pinned isolated launcher disables bytecode writes. An added cache,
        extra artifact or changed disclosure manifest therefore fails the
        before/after inventory check. Top-level .git is repository metadata,
        not part of the portable scientific/disclosure file inventory.
        """
        result = {}
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            here = Path(directory)
            if here == self.root:
                dirs[:] = [name for name in dirs if name != '.git']
                files = [name for name in files if name != '.git']
            for name in dirs:
                require(not (here / name).is_symlink(), 'Aliased directory in snapshot inventory')
            for name in files:
                path = here / name
                require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(self.root),
                        'Aliased or nonregular file in snapshot inventory')
                result[path.relative_to(self.root).as_posix()] = sha(path)
        return result

    def path(self, name):
        require(type(name) is str and '\\' not in name and ':' not in name,
                'Unsafe snapshot file path')
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.parts and
                all(part not in ('', '.', '..') for part in path.parts) and
                path.parts[0] not in ('.git', 'runs') and
                not any(part.startswith('.') for part in path.parts if part not in ('.github', '.gitattributes', '.gitignore', '.env.example')),
                'Unsafe snapshot file path')
        require(name in self.files, 'Snapshot input is not admitted: ' + name)
        target = self.root.joinpath(*path.parts)
        require(target.resolve().is_relative_to(self.root) and target.is_file() and
                not any(p.is_symlink() for p in (target, *target.parents) if p != self.root.parent),
                'Snapshot input is missing or aliased: ' + name)
        return target

    def check_all(self):
        for name, expected in self.files.items():
            require(sha(self.path(name)) == expected, 'Admitted snapshot file changed: ' + name)

    def read(self, name):
        path = self.path(name)
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == self.files[name], 'Snapshot input changed: ' + name)
        self.used.add(name)
        return strict_json(raw)

    def rows(self, name):
        path = self.path(name)
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == self.files[name], 'Snapshot input changed: ' + name)
        self.used.add(name)
        require(not raw or raw.endswith(b'\n'), 'Incomplete snapshot JSONL input')
        require(all(line.strip() for line in raw.splitlines()), 'Empty snapshot JSONL row')
        return [strict_json(line) for line in raw.splitlines()]

    def module(self, name):
        path = name.replace('.', '/') + '.py'
        source = self.path(path)
        require(sha(source) == self.files[path], 'Frozen module changed before import')
        module = importlib.import_module(name)
        require(Path(module.__file__).resolve() == self.root / path,
                'Frozen module was imported from a different checkout')
        if hasattr(module, 'ROOT'):
            require(Path(module.ROOT).resolve() == self.root, 'Frozen module root differs from snapshot')
        require(sha(source) == self.files[path], 'Frozen module changed during import')
        self.used.add(path)
        self.check_imports = True
        return module

    def artifacts(self, values, expected):
        require(type(values) is dict and set(values) == set(expected), 'Historical artifact inventory differs')
        for name, digest in values.items():
            require(type(digest) is str and HEX.fullmatch(digest) is not None and
                    sha(self.path(name)) == digest, 'Historical artifact hash differs')
            self.used.add(name)

    def finish(self):
        if self.check_imports:
            for name, module in list(sys.modules.items()):
                if not name.startswith(('experiments.', 'analysis.', 'paper.')):
                    continue
                filename = getattr(module, '__file__', None)
                if filename is None:
                    continue
                path = Path(filename).resolve()
                require(path.is_relative_to(self.root) and path.suffix == '.py',
                        'A frozen dependency was imported outside the admitted checkout')
                relative = path.relative_to(self.root).as_posix()
                self.path(relative)
                self.used.add(relative)
        self.check_all()
        require(self.files == self.admission['files'], 'Snapshot admission map changed')
        last = self.verify_admission(self.root)
        require(type(last) is dict and last == self.admission and canonical(last) == canonical(self.admission),
                'Snapshot disclosure admission changed during replay')
        # Recheck after the callback too: a callback's side effect or an extra
        # unadmitted file must not disappear behind an unchanged files mapping.
        require(self.inventory() == self.initial_inventory, 'Snapshot whole-file inventory changed during replay')


def stateful_baselines(packets):
    """New explicit assembly of the three historically defined baselines."""
    result = {}
    for name in ('exact_packet', 'always_abstain', 'fixed_actor_A'):
        supported = grounded = unsupported = 0
        for task in packets:
            labels = set(task['compatible_labels'])
            require(bool(labels), 'Stateful baseline has empty support')
            if name == 'exact_packet':
                grounded += 1
                supported += len(labels) == 1
            elif name == 'always_abstain':
                grounded += len(labels) > 1
            else:
                grounded += labels == {'A'}
                supported += labels == {'A'}
                unsupported += labels != {'A'}
        result[name] = dict(packets=len(packets), grounded_correct=grounded,
                            supported_definite=supported, unsupported_executor=unsupported)
    return result


def stateful_main_effects(episodes, rows, config, bootstrap):
    """New explicit contrast assembly with the unchanged frozen bootstrap.

    Inputs must already have passed the complete planned-grid and rescoring
    checks. Source order and stratum insertion order preserve the old bootstrap.
    """
    require(episodes and len({e['episode_id'] for e in episodes}) == len(episodes),
            'Stateful independent source identities differ')
    result = {}
    for model in config['models']:
        selected = [r for r in rows if r['returned'] and r['model'] == model]
        indexed = {}
        for row in selected:
            task = row['task']
            key = (task['episode_id'], task['churn'], task['mechanism'], task['restoration'])
            require(key not in indexed, 'Duplicate stateful paired reading')
            indexed[key] = row['scored']
        effects = {}
        for name in ('primary_unsupported_targeted_minus_random', 'secondary_churn_interaction',
                     'restoration_grounded_priority_minus_random', 'restoration_coverage_priority_minus_none'):
            strata, families, values = {}, {}, []
            for episode in episodes:
                def metric(churn, mechanism, restoration, field):
                    key = (episode['episode_id'], churn, mechanism, restoration)
                    require(key in indexed, 'Missing stateful paired reading')
                    return indexed[key][field]
                if name == 'primary_unsupported_targeted_minus_random':
                    value = metric(True, 'targeted', 'none', 'unsupported_executor') - metric(True, 'random', 'none', 'unsupported_executor')
                elif name == 'secondary_churn_interaction':
                    value = (metric(True, 'targeted', 'none', 'unsupported_executor') - metric(True, 'random', 'none', 'unsupported_executor')) - (metric(False, 'targeted', 'none', 'unsupported_executor') - metric(False, 'random', 'none', 'unsupported_executor'))
                elif name == 'restoration_grounded_priority_minus_random':
                    value = metric(True, 'targeted', 'priority', 'grounded_correct') - metric(True, 'targeted', 'random', 'grounded_correct')
                else:
                    value = metric(True, 'targeted', 'priority', 'supported_definite') - metric(True, 'targeted', 'none', 'supported_definite')
                values.append(value)
                strata.setdefault((episode['family'], episode['cohort']), []).append(value)
                families.setdefault(episode['family'], []).append(value)
            effects[name] = dict(estimate=sum(values) / len(values), episode_n=len(values),
                ci95=bootstrap(strata, config['bootstrap_seed'], config['bootstrap_resamples']),
                by_family={key: dict(n=len(v), estimate=sum(v) / len(v)) for key, v in families.items()},
                secondary=name != 'primary_unsupported_targeted_minus_random' or model != config['primary_model'])
        clean = [e for e in episodes if e['cohort'] == 'clean']
        require(bool(clean), 'Stateful clean-source denominator is empty')
        events = sum(any(indexed[e['episode_id'], True, mechanism, 'none']['status'] == 'EXECUTOR'
                         for mechanism in ('targeted', 'random')) for e in clean)
        effects['clean_episode_false_accusation'] = dict(events=events, n=len(clean),
            zero_event_upper95=(1 - .05 ** (1 / len(clean))) if events == 0 else None,
            caveat='Zero-event bound assumes independent source draws; views do not increase n. Not deployment prevalence.')
        result[model] = effects
    return result


def _stateful(a):
    publication = a.module('experiments.stateful_release')
    checks = a.module('experiments.verify_stateful_results')
    study = a.module('experiments.stateful_study')
    analysis = a.module('experiments.stateful_analysis')
    hf = a.module('experiments.hf_stateful')
    report = a.read('research/stateful-results.json')
    schema(report, {'schema', 'freeze_sha256', 'frozen_source_sha256', 'config', 'arms', 'artifacts',
                    'privacy', 'billing', 'main', 'influence', 'hf'}, 'Stateful report')
    require(report['schema'] == 'stateful-public-release-v1' and set(report['arms']) == {'main', 'influence', 'hugging_face'},
            'Stateful release identity differs')
    expected = {'data/stateful_main_cases.jsonl', 'data/stateful_main_episodes.json',
                'data/stateful_hf_cases.jsonl', 'data/stateful_influence_cases.jsonl'}
    a.artifacts(report['artifacts'], expected)
    frozen = a.read('research/stateful-main-v2-freeze.json')
    require(report['config'] == study.config() == frozen['config'] and
            report['frozen_source_sha256'] == frozen['source_sha256'] and
            report['freeze_sha256'] == sha(a.path('research/stateful-main-v2-freeze.json')),
            'Stateful original registration commitments differ')
    # This existing function does not call protocol admission or private journals.
    publication.verify_public(a.root, raw=False)
    for alias, arm_name, filename in (('main', 'main', 'stateful_main_cases.jsonl'),
                                     ('hf', 'hugging_face', 'stateful_hf_cases.jsonl'),
                                     ('influence', 'influence', 'stateful_influence_cases.jsonl')):
        arm = report['arms'][arm_name]
        require(report[alias] == arm, 'Stateful report alias differs')
        rows = a.rows('data/' + filename)
        checks.verify_counts(rows, arm)
        if arm['status'] == 'not_run':
            schema(arm, {'status'}, 'Unrun stateful arm')
            continue
        if alias == 'influence':
            fields = {'status', 'planned_calls', 'attempted_calls', 'returned_calls', 'unattempted_calls',
                      'journaled_without_response', 'raw_file_sha256', 'arms', 'summary', 'token_rate_estimated_credits'}
            if arm['status'] == 'complete':
                fields.add('secondary_influence_contrast')
            schema(arm, fields, 'Stateful influence arm')
            checks.verify_influence(rows, arm, frozen['config'])
            continue
        fields = {'status', 'planned_calls', 'attempted_calls', 'returned_calls', 'unattempted_calls',
                  'journaled_without_response', 'source_episodes', 'models', 'baselines', 'model_totals',
                  'all_planned_records_returned', 'raw_file_sha256', 'costs', 'summary'}
        if alias == 'main':
            fields.add('analysis')
        else:
            fields |= {'freeze_sha256', 'frozen_source_sha256', 'configuration'}
            if arm['status'] == 'complete':
                fields.add('paired_effects')
        schema(arm, fields, 'Stateful task arm')
        schema(arm['summary'], {'status', 'source_episodes', 'planned_calls', 'attempted_calls',
                               'returned_calls', 'unattempted_calls', 'journaled_without_response',
                               'all_planned_records_returned'}, 'Stateful task summary')
        schema(arm['costs'], {'token_rate_estimates', 'estimated_total', 'provider_reported_total'}, 'Stateful cost summary')
        episodes, packets = study.prepare('main') if alias == 'main' else hf.prepare()
        models = study.config()['models'] if alias == 'main' else [hf.config()['model']]
        by_task = {t['task_id']: t for t in packets}
        require(len(by_task) == len(packets) and
                {(r['task']['task_id'], r['model']) for r in rows} == {(t, m) for t in by_task for m in models} and
                len(rows) == len(packets) * len(models), 'Stateful full planned grid differs')
        require(all(r['task'] == by_task[r['task']['task_id']] for r in rows), 'Stateful deterministic task differs')
        require(arm['baselines'] == stateful_baselines(packets), 'Stateful baseline replay differs')
        if alias == 'main':
            source_fields = ('episode_id', 'seed', 'family', 'cohort', 'public', 'world')
            published = a.read('data/stateful_main_episodes.json')
            require([{k: e[k] for k in source_fields} for e in published] == episodes,
                    'Stateful deterministic source sample differs')
            if arm['status'] == 'complete':
                require(arm['analysis'] == dict(stage='main', complete=True, source_episodes=len(episodes),
                        effects=stateful_main_effects(episodes, rows, frozen['config'], analysis.bootstrap)),
                        'Stateful complete effects/bounds differ')
            else:
                require(not arm.get('analysis', {}).get('effects'), 'Partial stateful arm has confirmatory effects')
        else:
            hfreeze = a.read('research/stateful-hf-v3-freeze.json')
            require(arm['configuration'] == hf.config() == hfreeze['config'] and
                    arm['freeze_sha256'] == study.sha(hf.FREEZE) and
                    arm['frozen_source_sha256'] == hfreeze['source_sha256'], 'Stateful HF original commitments differ')
            if arm['status'] == 'complete':
                require(arm['paired_effects'] == publication.secondary_pairs(rows, episodes, models[0], frozen['config']),
                        'Stateful HF paired effects differ')
            else:
                require('paired_effects' not in arm, 'Partial stateful HF arm has effect intervals')
    return dict(valid=True, scope='Public host/task/score/count/baseline/effect replay; original protocol admission separately attested')


def _cost(row, model, provider, config, rates):
    require(type(row['known_usage']) is bool and row['provider'] == provider,
            'Historical provider/usage flag differs')
    schema(row['response'], {'status', 'output_text', 'usage', 'returned_model'}, 'Historical response')
    require(type(row['transport']) is dict and set(row['transport']) <= {'http_status', 'latency_seconds', 'error'},
            'Unexpected historical transport field')
    ri, ro = rates(model)
    usage = row['response']['usage']
    if row['known_usage']:
        schema(usage, {'input_tokens', 'output_tokens'}, 'Historical usage')
        require(all(type(v) is int and v >= 0 for v in usage.values()), 'Historical usage counters differ')
        expected = (usage['input_tokens'] * ri + usage['output_tokens'] * ro) / 1000000
    else:
        require(usage is None, 'Unknown historical usage must remain unknown')
        expected = (config['input_byte_cap'] * ri + config['max_output_tokens'] * ro) / 1000000
    actual = Decimal(row['estimated_cost'])
    require(actual.is_finite() and actual == expected, 'Historical cost/reservation arithmetic differs')


def _live(a):
    m = a.module('experiments.live_analysis')
    report = a.read('research/live-results.json')
    schema(report, {'status', 'study_id', 'freeze_sha256', 'config', 'qualification', 'artifacts',
                    'raw_file_sha256', 'phases', 'analysis', 'billing', 'scope', 'operational_amendment'}, 'Live report')
    require(report['status'] == 'complete' and report['config'] == m.config() and
            report['study_id'] == m.config()['study_id'] and report['freeze_sha256'] == m.sha(m.FREEZE),
            'Live original configuration/registration differs')
    a.artifacts(report['artifacts'], m.FILES)
    actors, cases = a.rows(m.FILES[0]), a.rows(m.FILES[2])
    trajectories = m.replay(actors)
    require(trajectories == a.read(m.FILES[1]), 'Live host-state reconstruction differs')
    expected = set()
    for trajectory in trajectories:
        for view in m.views(trajectory['public'], trajectory['world']):
            if trajectory['exposure'] != 'actual' and view['restoration'] != 'none':
                continue
            for model in m.config()['monitors']:
                expected.add(f"audit-{trajectory['id']}-{view['mechanism']}-{view['restoration']}-{model}")
    require(len(cases) == len({r['id'] for r in cases}) and {r['id'] for r in cases} == expected,
            'Live planned audit identity grid differs')
    _, rebuilt = m.build_cases(actors, cases)
    require(rebuilt == cases, 'Live packet/scoring reconstruction differs')
    for row in actors + cases:
        allowed = {'id', 'model', 'metadata', 'provider', 'transport', 'response', 'known_usage', 'estimated_cost'}
        allowed |= {'job'} if row in actors else {'packet', 'compatible_labels', 'added_ids', 'restored_bytes', 'scored'}
        schema(row, allowed, 'Live row')
        provider = 'hf' if row['model'] == m.config()['hf_model'] else 'adaption'
        _cost(row, row['model'], provider, m.config(), m.rates)
    require(report['analysis'] == m.analyze(actors, trajectories, cases), 'Live complete statistical report differs')
    return dict(valid=True, scope='Live host/packet/scoring/planned-grid and complete statistical replay')


def _weight(a):
    m = a.module('experiments.weight_study')
    report = a.read('research/weight-results.json')
    schema(report, {'status', 'study_id', 'freeze_sha256', 'qualification', 'artifact_sha256', 'raw_sha256',
                    'analysis', 'scope', 'billing'}, 'Weight report')
    cases = a.rows('data/weight_cases.jsonl')
    jobs = {j['id']: j for j in m.jobs()}
    require(report['status'] == 'complete' and report['study_id'] == m.config()['study_id'] and
            report['freeze_sha256'] == m.sha(m.FREEZE) and report['artifact_sha256'] == sha(a.path('data/weight_cases.jsonl')) and
            len(cases) == len(jobs) == len({r['id'] for r in cases}) and {r['id'] for r in cases} == set(jobs),
            'Weight artifact/configuration/planned grid differs')
    from experiments.live_study import rates
    for row in cases:
        job = jobs[row['id']]
        schema(row, {'id', 'model', 'metadata', 'provider', 'transport', 'response', 'known_usage', 'estimated_cost',
                     'problem', 'profile_valid', 'scored', 'random_control'}, 'Weight row')
        problem = m.problem(job['metadata']['seed'], job['metadata']['index'])
        eligible = m.profile_valid(row)
        text = row['response']['output_text'] if eligible else ''
        scored = m.assess(problem, job['metadata']['task'], text)
        control = m.random_controls(problem, m.parse(text)['networks'], job['metadata']['task'],
                                    m.config()['random_controls_per_admitted_artifact']) if scored['admitted'] else None
        require(row['metadata'] == job['metadata'] and row['model'] == job['model'] and
                row['profile_valid'] == eligible and row['problem'] == problem and row['scored'] == scored and
                row['random_control'] == control, 'Weight artifact/behavior/control reconstruction differs')
        provider = 'hf' if job['model'] == m.live_config()['hf_model'] else 'adaption'
        _cost(row, row['model'], provider, m.live_config(), rates)
    require(report['analysis'] == m.summary(cases), 'Weight complete statistical report differs')
    return dict(valid=True, scope='Tiny numeric artifact/behavior/control and full aggregate replay')


def _factorial_reporting(a):
    r = a.module('experiments.factorial_reporting')
    f = a.module('experiments.factorial_analysis')
    s = a.module('experiments.factorial_study')
    extension = a.module('experiments.ollama_study')
    report = a.read('research/factorial-report.json')
    schema(report, {'schema_version', 'status', 'study_id', 'reporting_tag', 'primary_complete', 'original_plan_complete',
        'extension_plan_complete', 'config', 'extension_config', 'freeze_sha256', 'reporting_freeze_sha256',
        'extension_freeze_sha256', 'original_checkpoint_sha256', 'artifacts', 'raw_file_sha256', 'phases',
        'analysis', 'billing', 'training_runs'}, 'Factorial reporting report')
    registration = a.read('research/factorial-reporting-freeze.json')
    require(type(report['schema_version']) is int and report['schema_version'] == 1 and report['reporting_tag'] == r.TAG and
            report['config'] == s.config() and report['study_id'] == s.config()['study_id'] and
            report['freeze_sha256'] == s.sha(s.FREEZE) and report['reporting_freeze_sha256'] == s.sha(r.FREEZE) and
            report['extension_freeze_sha256'] == registration['extension_freeze_sha256'] == s.sha(extension.FREEZE) and
            report['original_checkpoint_sha256'] == registration['original_checkpoint_sha256'] and report['training_runs'] == 0,
            'Factorial original registration/configuration bindings differ')
    a.artifacts(report['artifacts'], r.FILES)
    design = a.read(r.FILES[0])['main']
    require(s.digest(dict(main=design)) == a.read('research/factorial-design.json')['canonical_sha256'],
            'Factorial deterministic source design differs')
    actors, published, manifest = a.rows(r.FILES[1]), a.rows(r.FILES[3]), a.read(r.FILES[4])
    registry = r.descriptors(extension)
    for actor in actors:
        r.validate_row(actor, registry['original_g26'], actor=True)
    originals, extras = [], []
    for row in published:
        ident = row['condition_id']
        require(ident in registry, 'Factorial unknown observed condition')
        r.validate_row(row, registry[ident], decorated=True)
        clean = {key: row[key] for key in f.ALLOWED}
        if registry[ident]['origin'] == 'extension':
            clean.update({key: row[key] for key in r.FLAGS})
            extras.append(clean)
        else:
            originals.append(clean)
    trajectories, cases, rebuilt = r.build_cases(actors, originals, design, extras, extension)
    require(trajectories == a.read(r.FILES[2]) and published == cases and rebuilt == manifest,
            'Factorial host/plan/missingness/scoring reconstruction differs')
    analysis = r.analyze(actors, trajectories, cases, manifest)
    require(report['analysis'] == analysis and analysis['sources'] == 192 and analysis['actor_calls'] == 576 and
            analysis['original_audit_calls'] == 9742 and analysis['planned_original_audit_calls'] == 11640,
            'Factorial complete statistical report/denominators differ')
    require(report['primary_complete'] is True and report['original_plan_complete'] is False and
            not analysis['models'][s.config()['hf_model']]['availability']['complete'],
            'Factorial historical missingness was filled or hidden')
    complete = bool(analysis['extensions']['conditions']) and all(c['availability']['complete'] for c in analysis['extensions']['conditions'].values())
    require(report['extension_plan_complete'] is complete and
            report['status'] == ('primary_complete_with_registered_extensions' if complete else 'primary_complete_secondary_incomplete') and
            report['extension_config'] == extension.config(), 'Factorial completion/profile declarations differ')
    r._verify_phase_accounting(report, actors, cases, manifest)
    return dict(valid=True, scope='Original missingness, registered extensions, host/evidence/scoring and full statistics replay')


def _hf_completion(a):
    h = a.module('experiments.hf_completion_analysis')
    p = a.module('experiments.paced_resume_analysis')
    report = a.read('research/hf-completed-original-results-v3.json')
    schema(report, p.HF_KEYS, 'Original HF completion report')
    require(type(report['schema_version']) is int and report['schema_version'] == 2 and
            report['status'] == 'complete' and report['analysis_tag'] == p.TAG and
            report['analysis_freeze_sha256'] == p.s.sha(p.FREEZE) and
            report['source_registration_sha256'] == p.parents(), 'Original HF report bindings differ')
    name = 'data/hf_completed_original_supplement_v3.jsonl'
    fresh = a.rows(name)
    require(report['supplement_sha256'] == sha(a.path(name)), 'HF supplement hash differs')
    h._check_completion_counts(fresh, a.read('research/hf-completion-v1-freeze.json'))
    h._summary_check(report['operational_summary'], fresh)
    require(type(report['training_runs']) is int and report['training_runs'] == 0, 'HF training scope differs')
    require(set(report['raw_batches_sha256']) == {'hf-completion-v1', 'hf-completion-v2', 'hf-completion-v3'},
            'HF batch commitment inventory differs')
    registered = a.read('research/hf-completion-v3-freeze.json')['prior_raw_sha256']
    for batch, values in report['raw_batches_sha256'].items():
        require(type(values) is dict and set(values) == {'plan.json', 'attempts.jsonl', 'responses.jsonl', 'summary.json'},
                'HF batch commitment schema differs')
        for filename, digest in values.items():
            require(type(digest) is str and HEX.fullmatch(digest) is not None, 'HF batch commitment digest differs')
            if batch != 'hf-completion-v3':
                require(registered['runs/' + batch + '/' + filename] == digest, 'HF stopped-prefix commitment differs')
    actors = a.rows('data/factorial_report_actors.jsonl')
    old = [r for r in a.rows('data/factorial_report_cases.jsonl') if r['condition_id'].startswith('original_')]
    design = a.read('data/factorial_contexts.json')['main']
    require(len(actors) == 576 and len(old) == 9742 and len(design) == 192, 'HF original source inventory differs')
    result = h.build_completed(actors, old, fresh, design)
    require(report['analysis'] == result['analysis'] and report['availability'] == h._availability(result['cases']) and
            report['supplement_terminals'] == len(fresh) == 1898 and report['original_terminals'] == len(result['cases']) == 11640,
            'HF whole statistical reconstruction differs')
    require(result['analysis']['primary']['result'] == a.read('research/factorial-report.json')['analysis']['primary']['result'],
            'HF completion changed the historical primary result')
    return dict(valid=True, scope='Exact original HF completion, retained failures and complete statistical replay')


def _capacity(a):
    result = {}
    for module_name, name in (('experiments.hf_capacity', 'research/hf-capacity-results.json'),
                              ('experiments.hf_capacity_v2', 'research/hf-capacity-v2-results.json')):
        module = a.module(module_name)
        module.validate(a.read(name), module.config())
        result[module_name.rsplit('.', 1)[-1]] = dict(valid=True, scope='Public capacity job/profile/cost/aggregate replay; no new canary')
    return result


def _serving_diagnostic(a):
    """New bounded arithmetic check; the native profile claim stays attested."""
    module = a.module('experiments.hf_diagnostic')
    config = module.config()
    report = a.read('research/hf-diagnostic-results.json')
    schema(report, {'status', 'tag', 'scientific_calls', 'started', 'catalog_http_status',
                    'inference_http_status', 'known_usage', 'input_tokens', 'output_tokens',
                    'estimated_cost', 'reserved_unknown_cost', 'profile_ok', 'cap_usd',
                    'private_file_sha256', 'interpretation'}, 'Excluded serving diagnostic')
    require(report['status'] == 'complete_excluded_serving_diagnostic' and report['tag'] == config['registration_tag'] and
            type(report['scientific_calls']) is int and report['scientific_calls'] == 0 and
            type(report['known_usage']) is bool and type(report['profile_ok']) is bool,
            'Serving diagnostic exclusion/identity differs')
    stamp = datetime.fromisoformat(report['started'].replace('Z', '+00:00'))
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0 and stamp <= datetime.now(timezone.utc),
            'Serving diagnostic timestamp differs')
    for field in ('catalog_http_status', 'inference_http_status'):
        require(report[field] is None or type(report[field]) is int and 100 <= report[field] <= 599,
                'Serving diagnostic HTTP metadata differs')
    require(type(report['private_file_sha256']) is dict and bool(report['private_file_sha256']) and
            all(type(k) is str and type(v) is str and HEX.fullmatch(v) is not None
                for k, v in report['private_file_sha256'].items()), 'Diagnostic private hash commitment schema differs')
    require(Decimal(report['cap_usd']).is_finite() and Decimal(report['cap_usd']) == Decimal(config['cap_usd']),
            'Serving diagnostic cap differs')
    if report['known_usage']:
        require(all(type(report[k]) is int and report[k] >= 0 for k in ('input_tokens', 'output_tokens')),
                'Serving diagnostic usage differs')
        expected = (report['input_tokens'] * Decimal(config['hf_input_rate']) +
                    report['output_tokens'] * Decimal(config['hf_output_rate'])) / 1000000
        unknown = Decimal(0)
    else:
        require(report['input_tokens'] is None and report['output_tokens'] is None, 'Diagnostic unknown usage differs')
        expected = unknown = module.reservation(config)
    require(Decimal(report['estimated_cost']).is_finite() and Decimal(report['estimated_cost']) == expected and
            Decimal(report['reserved_unknown_cost']).is_finite() and Decimal(report['reserved_unknown_cost']) == unknown,
            'Serving diagnostic cost/reservation arithmetic differs')
    # Returned-model/finish/content evidence is private. Do not infer it from HTTP200.
    return dict(valid=True, scope='Excluded operational diagnostic usage/cost arithmetic and hash commitments only',
                native_profile_authenticity='preserved private attestation; not publicly reconstructed')


def replay_legacy(root, verify_admission):
    """Run all currently published historical scientific reports after admission.

    Call only after the new prospective snapshot protocol/source gate. This
    performs scoring/statistical replay but no inference, export or mutation.
    """
    a = AdmittedFiles(root, verify_admission)
    require(Path.cwd().resolve() == a.root, 'Run historical snapshot replay from the admitted checkout root')
    # Verify the origin module path before invoking any frozen helper.
    a.module('experiments.access')
    result = {}
    try:
        pilot = a.module('experiments.verify_release')
        pilot_report = a.read('research/pilot-results.json')
        schema(pilot_report, {'batches', 'credit_reconciliation', 'hugging_face_smoke', 'influence',
                             'known_provider_reported_adaption_cost', 'oracle_validation', 'released_development_data', 'status'},
               'Development pilot report')
        a.rows('data/development_reader_cases.jsonl')
        a.read('data/development_episodes.json')
        pilot.verify_release()
        result['development_pilot'] = dict(valid=True, scope='Released fake-data episodes and final-answer score/count replay; no account reconciliation')
        result['stateful'] = _stateful(a)
        result['live'] = _live(a)
        result['weight'] = _weight(a)
        result['factorial_reporting'] = _factorial_reporting(a)
        result['original_hf_completion'] = _hf_completion(a)
        result['capacity_diagnostics'] = _capacity(a)
        result['excluded_serving_diagnostic'] = _serving_diagnostic(a)
        posthoc = a.module('analysis.exploratory_restoration')
        require(posthoc.diagnostic() == a.read('research/restoration-diagnostic-posthoc.json'),
                'Historical posthoc restoration decomposition differs')
        calibration = a.module('analysis.calibration_breakdown')
        require(calibration.build() == a.read('analysis/calibration-breakdown-posthoc.json'),
                'Historical descriptive calibration breakdown differs')
        result['posthoc_descriptive'] = dict(valid=True, scope='Released restoration decomposition and calibration counts; no new hypothesis test')
    finally:
        a.finish()
    return dict(valid=True, scope=SCOPE, mathematical_replay=result,
                private_original_protocol_admission='attested_not_publicly_repeated',
                native_authenticity='not independently reauthenticated; private archive required',
                inference_calls=0, files_unchanged=True)
