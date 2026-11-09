"""Public mathematical replay under an explicit sanitized-source disclosure.

This is a NEW admission route. It does not call, replace or claim to satisfy the
historical private-protocol registration validators. The trusted outer disclosure
verifier supplies an exact file inventory and identifies the privately admitted
canonical commit; this module rechecks those files and uses the unchanged frozen
job builders, host simulator, scoring, bootstrap and sensitivity functions.

Importing this module reads no data, credentials or provider state. No export or
provider request is implemented here. Real replay is a separate prospective gate.
"""
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from types import MappingProxyType


ADMISSION_KEYS = {
    'schema_version', 'canonical_commit', 'disclosure_manifest_sha256', 'files',
    'scope', 'private_original_protocol_admission',
}
SCOPE = 'sanitized_public_snapshot_v3'
PRIVATE_ADMISSION = 'attested_not_publicly_repeated'
MAIN_MANIFEST_KEYS = {
    'schema_version', 'study_id', 'scope', 'artifacts', 'report_sha256',
    'configuration_sha256', 'registration_sha256', 'provenance_limit',
    'registration_prefix', 'engineering_configuration_sha256',
    'operational_registration_sha256',
}
MAIN_DIRECTORY = 'data/swarm-ledger-v1-public'
SENSITIVITY_DIRECTORY = 'data/swarm-ledger-generator-sensitivity-v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash(value, digits=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(digits) + '}', value) is not None


def _relative(value):
    require(type(value) is str and value and '\\' not in value and ':' not in value
            and '\x00' not in value, 'Invalid disclosed relative path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value
            and all(part not in ('', '.', '..', '.git') for part in path.parts),
            'Unsafe disclosed relative path')
    require(not any(part == 'runs' or part.startswith('runs-') for part in path.parts),
            'Private run path cannot be a disclosed input')
    require(not any((part == '.env' or part.startswith('.env.')) and part != '.env.example'
                    for part in path.parts), 'Private environment path cannot be a disclosed input')
    return path


def _no_duplicates(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate public JSON key')
        result[key] = value
    return result


def _finite(value):
    if type(value) is float:
        require(math.isfinite(value), 'Nonfinite public JSON number')
    elif type(value) is list:
        for item in value:
            _finite(item)
    elif type(value) is dict:
        for item in value.values():
            _finite(item)


def strict_json(raw):
    require(type(raw) is bytes, 'Public JSON input must be bytes')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_no_duplicates,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite public JSON')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid public JSON encoding or syntax') from exc
    _finite(value)
    return value


@dataclass(frozen=True)
class AdmissionBinding:
    """Checked binding facts returned by the separately reviewed source verifier.

    A binding is not a signature or fresh authentication of omitted protocols.
    The external verifier is an explicit trusted dependency, never a default True.
    """
    root: Path
    canonical_commit: str
    disclosure_manifest_sha256: str
    files: Mapping

    @classmethod
    def check(cls, root, facts):
        root = Path(root)
        require(root.is_dir() and not root.is_symlink(), 'Snapshot root must be a regular local directory')
        root = root.resolve()
        require(type(facts) is dict and set(facts) == ADMISSION_KEYS, 'Disclosure admission schema differs')
        require(type(facts['schema_version']) is int and facts['schema_version'] == 1,
                'Disclosure admission version differs')
        require(facts['scope'] == SCOPE and facts['private_original_protocol_admission'] == PRIVATE_ADMISSION,
                'Disclosure admission scope differs')
        require(_hash(facts['canonical_commit'], 40) and _hash(facts['disclosure_manifest_sha256']),
                'Disclosure admission commitments invalid')
        files = facts['files']
        require(type(files) is dict and files, 'Exact disclosed file inventory required')
        for name, digest in files.items():
            _relative(name)
            require(_hash(digest), 'Disclosed file digest invalid')
        binding = cls(root, facts['canonical_commit'], facts['disclosure_manifest_sha256'],
                      MappingProxyType(dict(files)))
        binding.verify_files()
        return binding

    def facts(self):
        return dict(schema_version=1, canonical_commit=self.canonical_commit,
                    disclosure_manifest_sha256=self.disclosure_manifest_sha256,
                    files=dict(self.files), scope=SCOPE,
                    private_original_protocol_admission=PRIVATE_ADMISSION)

    def path(self, name):
        path = _relative(name)
        require(name in self.files, 'Public replay input is not admitted')
        current = self.root
        for part in path.parts:
            current = current / part
            require(not current.is_symlink(), 'Symlink in public replay input')
        require(current.is_file() and current.resolve().is_relative_to(self.root),
                'Public replay input missing or escaped root')
        return current

    def read(self, name):
        raw = self.path(name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == self.files[name], 'Disclosed input checksum differs')
        return raw

    def json(self, name):
        return strict_json(self.read(name))

    def relative(self, path):
        path = Path(path).resolve()
        require(path.is_relative_to(self.root), 'Scientific module/config escaped snapshot root')
        return path.relative_to(self.root).as_posix()

    def verify_files(self):
        for name in self.files:
            self.read(name)


def _directory(binding, name):
    _relative(name)
    path = binding.root / name
    require(path.is_dir() and not path.is_symlink() and path.resolve().is_relative_to(binding.root),
            'Public artifact directory invalid')
    return path


@contextmanager
def admitted_snapshot(root, verify_admission):
    """Keep the disclosed source facts and bytes stable through a replay."""
    require(callable(verify_admission), 'Explicit source-disclosure verifier required')
    binding = AdmissionBinding.check(root, verify_admission(Path(root)))
    try:
        yield binding
    finally:
        binding.verify_files()
        last = verify_admission(Path(root))
        require(type(last) is dict and last == binding.facts(),
                'Source disclosure changed during mathematical replay')


def _science(binding):
    # The caller runs from the new snapshot root. A cached module from the private
    # repository must never stand in for the disclosed copy.
    binding.read(binding.relative(__file__))
    from experiments import swarm_ledger_complete_analysis as analysis
    from experiments import swarm_ledger_complete as study
    from experiments import swarm_ledger_complete_dispatch as dispatch
    from analysis import ledger_generator_sensitivity as sensitivity
    require(Path(study.ROOT).resolve() == binding.root, 'Scientific ROOT differs from admitted snapshot')
    for name, module in list(sys.modules.items()):
        if name.startswith(('experiments.', 'analysis.')):
            source = getattr(module, '__file__', None)
            if source and str(source).endswith('.py'):
                binding.read(binding.relative(source))
    for module in (study, study.old, dispatch):
        for attribute in ('CONFIG', 'CATALOG'):
            value = getattr(module, attribute, None)
            if value is not None:
                binding.read(binding.relative(value))
    return analysis, study, dispatch, sensitivity


def read_shard_groups(binding, directory, manifest, groups, fixed_names, max_shard_bytes, canonical):
    """Exact declared public shards; no identity replacement or permissive JSON."""
    path = _directory(binding, directory)
    require(type(manifest) is dict and type(manifest.get('artifacts')) is dict
            and set(manifest['artifacts']) == set(groups), 'Public artifact groups differ')
    allowed = set(fixed_names)
    loaded = {}
    for group, parts in manifest['artifacts'].items():
        require(type(parts) is list and bool(parts), 'Missing public shard group')
        values = []
        for ordinal, part in enumerate(parts):
            require(type(part) is dict and set(part) == {'file', 'bytes', 'rows', 'sha256'},
                    'Public shard schema differs')
            stem = 'cases-' + group.split(':')[1] if group.startswith('cases:') else group.replace('_', '-')
            expected_name = f'{stem}-{ordinal:04d}.jsonl'
            require(part['file'] == expected_name and expected_name not in allowed, 'Public shard path/order differs')
            allowed.add(expected_name)
            raw = binding.read(directory + '/' + expected_name)
            require(type(part['bytes']) is int and len(raw) == part['bytes'] <= max_shard_bytes
                    and _hash(part['sha256']) and hashlib.sha256(raw).hexdigest() == part['sha256'],
                    'Public shard checksum/size differs')
            require(raw.endswith(b'\n'), 'Public shard has incomplete final line')
            lines = raw.splitlines()
            rows = [strict_json(line) for line in lines]
            require(all(type(row) is dict for row in rows), 'Public shard rows must be objects')
            require(raw == b''.join(canonical(row).encode('utf-8') + b'\n' for row in rows),
                    'Public JSONL must use exact canonical objects and LF')
            require(type(part['rows']) is int and len(rows) == part['rows'], 'Public shard row count differs')
            values.extend(rows)
        loaded[group] = values
    entries = list(path.iterdir())
    require({entry.name for entry in entries} == allowed
            and all(entry.is_file() and not entry.is_symlink() for entry in entries),
            'Unlisted/nonregular public artifact')
    return loaded


def load_main(binding, directory=MAIN_DIRECTORY):
    """New disclosure admission plus the unchanged public data-format checks.

    Registration copies are compared against admitted JSON, NOT re-presented as
    calls to the historical Git/private-protocol registration validators.
    """
    analysis, study, dispatch, _ = _science(binding)
    manifest = binding.json(directory + '/manifest.json')
    require(type(manifest) is dict and set(manifest) == MAIN_MANIFEST_KEYS, 'Public manifest schema differs')
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 2
            and manifest['study_id'] == study.config()['study_id']
            and manifest['registration_prefix'] == study.config()['registration_prefix']
            and manifest['scope'] == analysis.PUBLIC_SCOPE
            and manifest['provenance_limit'] == analysis.PROVENANCE_LIMIT, 'Public manifest identity/scope differs')
    groups = {'cases:' + profile for profile in study.config()['reader_profiles']} | {
        'contexts', 'worlds', 'influence', 'calibration', 'actors', 'influence_receivers',
        'engineering_contexts', 'engineering_technical', 'engineering_actors', 'engineering_readers',
    }
    fixed = {'manifest.json', 'report.json', 'config.json', 'registration.json',
             'registration-technical.json', 'registration-development.json',
             'engineering-config.json', 'operational-registration.json'}
    artifacts = read_shard_groups(binding, directory, manifest, groups, fixed,
                                 analysis.MAX_SHARD_BYTES, study.canonical)
    raw = binding.read(directory + '/report.json')
    require(_hash(manifest['report_sha256']) and hashlib.sha256(raw).hexdigest() == manifest['report_sha256'],
            'Public report checksum differs')
    require(binding.json(directory + '/config.json') == study.config()
            and manifest['configuration_sha256'] == study.sha(study.CONFIG),
            'Public configuration differs from admitted sources')
    for split in ('technical', 'development', 'main'):
        registration_path = study.freeze_path(split) if split == 'main' else analysis.engineering_study.freeze_path(split)
        registered = binding.json(binding.relative(registration_path))
        filename = 'registration.json' if split == 'main' else 'registration-' + split + '.json'
        require(binding.json(directory + '/' + filename) == registered,
                'Copied public registration differs from admitted original JSON')
    require(manifest['registration_sha256'] == study.sha(study.freeze_path('main')),
            'Public registration commitment differs')
    engineering = analysis.engineering_study
    require(binding.json(directory + '/engineering-config.json') == engineering.config()
            and manifest['engineering_configuration_sha256'] == engineering.sha(engineering.CONFIG),
            'Original engineering configuration differs')
    operational_path = dispatch.op_freeze('main')
    operational = binding.json(binding.relative(operational_path))
    require(binding.json(directory + '/operational-registration.json') == operational
            and manifest['operational_registration_sha256'] == study.sha(operational_path),
            'Copied operational registration differs from admitted original JSON')
    report = strict_json(raw)
    require(type(report) is dict, 'Public mathematical report must be an object')
    return artifacts, report, manifest


def reconstruct_main(binding, artifacts):
    """Explicit orchestration of the frozen pure job/host/evidence/scoring APIs."""
    analysis, study, _, _ = _science(binding)
    engineering = analysis.engineering_study
    contexts = artifacts['contexts']
    analysis.validate_contexts(contexts)
    registration = binding.json(binding.relative(study.freeze_path('main')))
    require(study.digest(contexts) == registration['contexts_sha256'], 'Public MAIN design differs')
    previous = {}
    coverage = {}
    technical, coverage['technical'] = analysis.public_phase(engineering.technical_jobs(), artifacts['engineering_technical'], True)
    for row in technical:
        require(engineering.admitted(row), 'Public technical serving gate failed')
        if engineering.profile(row['profile_id']).get('format') == 'json_schema':
            require(engineering.score(row['response']['output_text'], {'NONE'})['raw_label'] != 'INVALID',
                    'Public technical schema gate failed')
    development = artifacts['engineering_contexts']
    analysis.validate_contexts(development, 2)
    dev_registration = binding.json(binding.relative(engineering.freeze_path('development')))
    require(study.digest(development) == dev_registration['contexts_sha256'], 'Public development design differs')
    for role in analysis.ROLES:
        jobs = engineering.actor_jobs(role, development, previous)
        records = [row for row in artifacts['engineering_actors'] if row['metadata'].get('stage') == role]
        rows, coverage['development:' + role] = analysis.public_phase(jobs, records, True)
        previous.update({row['id']: row for row in rows})
    dev_jobs = engineering.reader_jobs(engineering.source_worlds(development, previous))
    dev_readers, coverage['development:readers'] = analysis.public_phase(dev_jobs, artifacts['engineering_readers'], True)
    require(len(artifacts['engineering_actors']) == len(previous), 'Unexpected engineering actor stage')
    previous = {}
    for role in analysis.ROLES:
        jobs = study.actor_jobs(role, contexts, previous)
        records = [row for row in artifacts['actors'] if row['metadata'].get('stage') == role]
        rows, coverage[role] = analysis.public_phase(jobs, records, True)
        previous.update({row['id']: row for row in rows})
    require(len(artifacts['actors']) == len(previous), 'Unexpected MAIN actor stage')
    sources = study.source_worlds(contexts, previous)
    require(study.canonical(sources) == study.canonical(artifacts['worlds']), 'Public host worlds differ from actor replay')
    cases = []
    for profile in study.config()['reader_profiles']:
        cases.extend(artifacts['cases:' + profile])
    jobs = study.reader_jobs(sources)
    reader_rows, coverage['readers'] = analysis.public_phase(jobs, cases)
    calibration_sources = study.calibration_sources()
    calibration_jobs = study.reader_jobs(calibration_sources)
    calibration_rows, coverage['calibration'] = analysis.public_phase(calibration_jobs, artifacts['calibration'])

    def verify_cases(worlds, planned, normalized, published):
        by_source = {source['source_id']: source for source in worlds}
        by_id = {row['id']: row for row in normalized}
        exported = {row['id']: row for row in published}
        require(len(by_source) == len(worlds) and len(by_id) == len(normalized)
                and len(exported) == len(published), 'Duplicate public source/case identity')
        cache = {}
        output = []
        for job in planned:
            source = by_source[job['metadata']['source_id']]
            source_id = source['source_id']
            if source_id not in cache:
                cache[source_id] = {
                    'receipt_only7' if view['view'] == 'sufficient' else view['view']: view['packet']
                    for view in analysis.engine.views(source['public'], source['world'])
                }
            case = analysis.score_case(job, by_id[job['id']], source, cache[source_id][job['metadata']['view']])
            require(study.canonical(case) == study.canonical(exported[job['id']]),
                    'Public verdict/scoring/packet differs')
            output.append(case)
        return output

    cases = verify_cases(sources, jobs, reader_rows, cases)
    calibration = verify_cases(calibration_sources, calibration_jobs, calibration_rows, artifacts['calibration'])
    influence_jobs = study.influence_jobs(contexts, previous)
    influence_rows, coverage['influence'] = analysis.public_phase(influence_jobs, artifacts['influence_receivers'], True)
    influence_sources = study.influence_worlds(contexts, previous, influence_rows)
    require(len({source['source_id'] for source in artifacts['influence']}) == len(artifacts['influence'])
            and study.canonical({source['source_id']: source for source in influence_sources})
            == study.canonical({source['source_id']: source for source in artifacts['influence']}),
            'Public influence worlds differ')
    require(len(sources) == 2560 and len(cases) == 53760 and len(calibration) == 240
            and len(influence_sources) == 240, 'Public registered grid differs')
    return dict(contexts=contexts, sources=sources, cases=cases, calibration=calibration, coverage=coverage,
                actor_rows=list(previous.values()), influence_rows=influence_rows,
                influence_sources=influence_sources,
                engineering=dict(technical_rows=technical, development_contexts=development,
                                 development_actor_rows=[], development_reader_rows=dev_readers))


def verify_sensitivity(binding, artifacts, original_report, manifest, directory=SENSITIVITY_DIRECTORY):
    analysis, study, _, sensitivity = _science(binding)
    path = _directory(binding, directory)
    require({entry.name for entry in path.iterdir()} == {'report.json', 'packets.jsonl', 'verdicts.jsonl', 'registration.json'}
            and all(entry.is_file() and not entry.is_symlink() for entry in path.iterdir()),
            'Sensitivity artifact inventory differs')
    report = binding.json(directory + '/report.json')
    scientific, packets, verdicts = sensitivity.summarize(artifacts)
    extra = {'created', 'registration_sha256', 'input_files_raw_sha256', 'input_manifest_raw_sha256',
             'input_report_raw_sha256', 'input_verification', 'original_primary_unchanged',
             'original_primary_commitment', 'provenance_limit', 'derived_files_raw_sha256'}
    require(type(report) is dict and set(report) == set(scientific) | extra, 'Sensitivity report fields differ')
    require(all(study.canonical(report[key]) == study.canonical(value) for key, value in scientific.items()),
            'Sensitivity scientific report differs')
    try:
        created = datetime.fromisoformat(report['created'])
    except (TypeError, ValueError) as exc:
        raise ValueError('Sensitivity timestamp invalid') from exc
    require(created.tzinfo is not None and created <= datetime.now(timezone.utc), 'Sensitivity timestamp invalid/future')
    registered = binding.json(binding.relative(sensitivity.REGISTRATION))
    require(binding.json(directory + '/registration.json') == registered
            and report['registration_sha256'] == study.sha(sensitivity.REGISTRATION),
            'Copied sensitivity registration differs')
    input_path = _directory(binding, MAIN_DIRECTORY)
    inputs = {entry.name: hashlib.sha256(binding.read(MAIN_DIRECTORY + '/' + entry.name)).hexdigest()
              for entry in sorted(input_path.iterdir())}
    require(report['input_files_raw_sha256'] == inputs
            and report['input_manifest_raw_sha256'] == inputs['manifest.json']
            and report['input_report_raw_sha256'] == inputs['report.json'], 'Sensitivity input commitments differ')
    require(report['original_primary_unchanged'] is True
            and report['original_primary_commitment'] == study.digest(original_report['primary'])
            and report['provenance_limit'] == manifest['provenance_limit'], 'Sensitivity primary/provenance commitment differs')
    historical = dict(valid=True, scope='offline public source/job/action/evidence/scoring/report replay',
                      main_blocks=640, main_reader_terminals=53760,
                      native_provenance_limit=manifest['provenance_limit'])
    require(study.canonical(report['input_verification']) == study.canonical(historical),
            'Preserved sensitivity input-verification receipt differs')
    for filename, values in (('packets.jsonl', packets), ('verdicts.jsonl', verdicts)):
        expected = ''.join(study.canonical(row) + '\n' for row in values).encode('utf-8')
        require(binding.read(directory + '/' + filename) == expected, 'Sensitivity derived rows differ')
    derived = {filename: hashlib.sha256(binding.read(directory + '/' + filename)).hexdigest()
               for filename in ('packets.jsonl', 'verdicts.jsonl', 'registration.json')}
    require(report['derived_files_raw_sha256'] == derived, 'Sensitivity derived commitments differ')
    return dict(valid=True, matched_sources=1280, unique_packets=8960, recorded_verdict_rows=38400)


def verify_main_and_sensitivity(root, verify_admission):
    """Full MAIN/sensitivity mathematical replay, with no provider or Git calls.

    ``verify_admission`` is the separately reviewed outer source/disclosure gate.
    Its exact facts and admitted bytes must remain stable through the whole run.
    Existing private-protocol validators are neither patched nor called here.
    """
    with admitted_snapshot(root, verify_admission) as binding:
        analysis, study, _, _ = _science(binding)
        with study.verified_config():
            artifacts, published, manifest = load_main(binding)
            data = reconstruct_main(binding, artifacts)
            primary = published.get('primary')
            require(type(primary) is dict and type(primary.get('draws')) is int and primary['draws'] == 10000
                    and type(primary.get('seed')) is int and primary['seed'] == analysis.BOOTSTRAP_SEED,
                    'Registered bootstrap differs')
            recomputed = analysis.analyze(data, draws=10000)
            require(study.canonical(recomputed) == study.canonical(published),
                    'Public report differs from reconstructed data')
            sensitivity_result = verify_sensitivity(binding, artifacts, published, manifest)
            report_commitment = study.digest(recomputed)
    return dict(valid=True, scope='public mathematical replay under sanitized_public_snapshot_v3',
                private_original_protocol_admission=PRIVATE_ADMISSION,
                canonical_commit=binding.canonical_commit,
                disclosure_manifest_sha256=binding.disclosure_manifest_sha256,
                main_blocks=640, main_reader_terminals=53760, calibration_terminals=240,
                influence_terminals=240, mathematical_report_sha256=report_commitment,
                generator_sensitivity=sensitivity_result)
