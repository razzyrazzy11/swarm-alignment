"""PRIVATE issuance of the separately admitted sanitized publication snapshot.

There is no default issuance and no public self-admission command. The operator
must supply reviewed private plans, in-memory private literals, original-check
attestations and externally reviewed prospective source commitments. The fixed
scientific input is read only from canonical Git blobs. This module neither
changes refs/history nor performs inference or mathematical replay.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from types import MappingProxyType

from . import admission as a
from . import disclosure_rebinding as rebinding
from . import privacy_policy as privacy
from . import snapshot_math


TAG = 'public-snapshot-disclosure-v1'
FREEZE_PATH = 'research/public-snapshot-disclosure-v1-freeze.json'
PROTOCOL_PATH = 'research/PUBLIC_SNAPSHOT_DISCLOSURE_PROTOCOL.md'
PACKAGE = 'public_snapshot/'
LAUNCHER = PACKAGE + 'verify.py'
CANONICAL_FILES = 521
OFFICIAL_ORIGINS = frozenset({
    'https://github.com/razzyrazzy11/swarm-alignment.git',
    'https://github.com/razzyrazzy11/swarm-alignment',
    'git@github.com:razzyrazzy11/swarm-alignment.git',
    'ssh://git@github.com/razzyrazzy11/swarm-alignment.git',
})
FREEZE_KEYS = frozenset({
    'schema_version', 'tag', 'canonical_commit', 'canonical_tree',
    'tooling_source_commit', 'source_sha256', 'created',
})
FINAL_KEYS = frozenset({'finaloutput', 'actualoutput', 'finalresponse', 'finalmodelresponse', 'outputtext'})
GITATTRIBUTES = b'''* text eol=lf
*.pdf -text
*.docx -text
*.png -text
*.jpg -text
*.jpeg -text
*.gif -text
*.zip -text
*.woff -text
*.woff2 -text
'''


class SnapshotIssueError(ValueError):
    """Category-only failures; never include private source values or guards."""


def need(condition, category):
    if not condition:
        raise SnapshotIssueError(category)


def sha(raw):
    need(type(raw) is bytes, 'issuance bytes required')
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    try:
        return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                           allow_nan=False) + '\n').encode('utf-8')
    except (TypeError, ValueError):
        raise SnapshotIssueError('issuance metadata cannot be encoded') from None


def _name(value):
    path = a.relative_name(value)
    need(not a.forbidden_name(value)
         and not any(part.casefold() in {'.git', '__pycache__', '.swarm', '.playwright-mcp'} for part in path.parts)
         and path.suffix.lower() not in {'.pyc', '.pyo'}, 'excluded issuance path')
    need(not any(part.endswith(('.', ' ')) for part in path.parts)
         and not any(re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part, re.I)
                     for part in path.parts), 'nonportable issuance path')
    return path


def _git(repo, *arguments, data=None, remote=False):
    # Read-only Git, no replacement/lazy objects or interactive credential prompt.
    # Global credential helpers remain available for the authorized private origin.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
               GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    try:
        result = subprocess.run(['git', '-C', str(repo), *arguments], input=data,
                                capture_output=True, env=env, timeout=60 if remote else 30)
    except (OSError, subprocess.TimeoutExpired):
        raise SnapshotIssueError('Git read unavailable') from None
    need(result.returncode == 0, 'Git read failed')
    return result.stdout


def _git_text(repo, *arguments, remote=False):
    try:
        return _git(repo, *arguments, remote=remote).decode('utf-8').strip()
    except UnicodeError:
        raise SnapshotIssueError('Git metadata encoding invalid') from None


def _tree_entries(repo, commit):
    need(type(commit) is str and re.fullmatch(r'[0-9a-f]{40}', commit), 'Git commit identity invalid')
    raw = _git(repo, 'ls-tree', '-r', '-z', '--full-tree', commit)
    result = {}
    aliases = set()
    for record in raw.split(b'\0'):
        if not record:
            continue
        try:
            header, encoded_name = record.split(b'\t', 1)
            mode, kind, oid = header.decode('ascii').split(' ')
            name = encoded_name.decode('utf-8')
        except (ValueError, UnicodeError):
            raise SnapshotIssueError('Git tree record invalid') from None
        _name(name)
        need(mode in {'100644', '100755'} and kind == 'blob'
             and re.fullmatch(r'[0-9a-f]{40}', oid), 'nonregular Git input refused')
        need(name not in result and name.casefold() not in aliases, 'duplicate or aliased Git path')
        aliases.add(name.casefold())
        result[name] = oid
    need(bool(result), 'empty Git input tree')
    return result


def _blobs(repo, entries):
    names = sorted(entries)
    query = ''.join(entries[name] + '\n' for name in names).encode('ascii')
    output = _git(repo, 'cat-file', '--batch', data=query)
    result = {}
    offset = 0
    for name in names:
        end = output.find(b'\n', offset)
        need(end >= offset, 'truncated Git batch record')
        try:
            oid, kind, size_text = output[offset:end].decode('ascii').split(' ')
            size = int(size_text)
        except (ValueError, UnicodeError):
            raise SnapshotIssueError('invalid Git batch record') from None
        need(oid == entries[name] and kind == 'blob' and 0 <= size <= 100_000_000,
             'Git blob identity or bound differs')
        start = end + 1
        raw = output[start:start + size]
        need(len(raw) == size and output[start + size:start + size + 1] == b'\n', 'truncated Git blob')
        actual = hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0' + raw).hexdigest()
        need(actual == oid, 'Git blob hash differs')
        result[name] = raw
        offset = start + size + 1
    need(offset == len(output), 'extra Git batch content')
    return result


@dataclass(frozen=True)
class ToolingGate:
    source_commit: str
    tag_commit: str
    freeze_sha256: str
    source_hashes: object
    package_files: object


def _verify_tooling_tag(repo, *, canonical_commit, canonical_tree,
                        expected_tooling_hashes, expected_freeze_sha256,
                        expected_origin, tooling_tag=TAG):
    """Generic private helper, exercised with toy repositories only in tests."""
    need(tooling_tag == TAG and a.is_hash(expected_freeze_sha256), 'prospective tag commitment invalid')
    need(type(canonical_commit) is str and re.fullmatch(r'[0-9a-f]{40}', canonical_commit)
         and type(canonical_tree) is str and re.fullmatch(r'[0-9a-f]{40}', canonical_tree)
         and _git_text(repo, 'rev-parse', canonical_commit + '^{tree}') == canonical_tree,
         'canonical source-tree commitment differs')
    need(type(expected_tooling_hashes) is dict and bool(expected_tooling_hashes), 'reviewed tooling inventory required')
    for name, digest in expected_tooling_hashes.items():
        _name(name)
        need((name.startswith(PACKAGE) or name == PROTOCOL_PATH) and a.is_hash(digest),
             'tooling source commitment invalid')
        need(not name.startswith(PACKAGE) or Path(name).suffix.lower() in {'.py', '.md', '.txt', '.yml', '.yaml'}
             or Path(name).name == '.gitattributes', 'private issuance product in tooling sources')
    need(PROTOCOL_PATH in expected_tooling_hashes and LAUNCHER in expected_tooling_hashes
         and PACKAGE + 'export_snapshot.py' in expected_tooling_hashes, 'required tooling source missing')
    need(_git_text(repo, 'remote', 'get-url', 'origin') == expected_origin, 'private canonical origin differs')
    tag_commit = _git_text(repo, 'rev-parse', 'refs/tags/' + tooling_tag)
    need(re.fullmatch(r'[0-9a-f]{40}', tag_commit) and _git_text(repo, 'cat-file', '-t', tag_commit) == 'commit',
         'prospective tag must be an exact lightweight commit tag')
    freeze_entries = _tree_entries(repo, tag_commit)
    need(FREEZE_PATH in freeze_entries, 'prospective freeze missing')
    freeze_raw = _blobs(repo, {FREEZE_PATH: freeze_entries[FREEZE_PATH]})[FREEZE_PATH]
    need(sha(freeze_raw) == expected_freeze_sha256, 'prospective freeze hash differs')
    freeze = a.decode_json(freeze_raw)
    need(type(freeze) is dict and set(freeze) == FREEZE_KEYS and type(freeze['schema_version']) is int
         and freeze['schema_version'] == 1, 'prospective freeze schema differs')
    need(freeze['tag'] == tooling_tag and freeze['canonical_commit'] == canonical_commit
         and freeze['canonical_tree'] == canonical_tree, 'prospective scientific identity differs')
    source_commit = freeze['tooling_source_commit']
    need(type(source_commit) is str and re.fullmatch(r'[0-9a-f]{40}', source_commit), 'prospective code identity invalid')
    need(freeze['source_sha256'] == expected_tooling_hashes, 'prospective source inventory differs')
    try:
        created = datetime.fromisoformat(freeze['created'])
    except (TypeError, ValueError):
        raise SnapshotIssueError('prospective timestamp invalid') from None
    need(created.tzinfo is not None and created.utcoffset().total_seconds() == 0
         and created <= datetime.now(timezone.utc), 'prospective timestamp invalid')
    _git(repo, 'merge-base', '--is-ancestor', canonical_commit, source_commit)
    _git(repo, 'merge-base', '--is-ancestor', source_commit, tag_commit)
    entries = _tree_entries(repo, source_commit)
    package_names = {name for name in entries if name.startswith(PACKAGE)}
    need(package_names | {PROTOCOL_PATH} == set(expected_tooling_hashes), 'unreviewed prospective package file')
    need(all(name in freeze_entries for name in expected_tooling_hashes), 'prospective tag source missing')
    source_files = _blobs(repo, {name: entries[name] for name in expected_tooling_hashes})
    tag_files = _blobs(repo, {name: freeze_entries[name] for name in expected_tooling_hashes})
    need(all(source_files[name] == tag_files[name] and sha(source_files[name]) == expected
             for name, expected in expected_tooling_hashes.items()), 'prospective code bytes drifted')
    source_time = _git_text(repo, 'show', '-s', '--format=%ct', source_commit)
    need(source_time.isdigit() and created.timestamp() >= int(source_time), 'prospective chronology differs')
    remote = _git_text(repo, 'ls-remote', '--tags', 'origin', 'refs/tags/' + tooling_tag, remote=True)
    need(remote == tag_commit + '\trefs/tags/' + tooling_tag, 'prospective tag is not exactly pushed')
    return ToolingGate(source_commit, tag_commit, expected_freeze_sha256,
                       MappingProxyType(dict(expected_tooling_hashes)), MappingProxyType(source_files))


def _assert_running_sources(repo, gate):
    for module in (a, privacy, rebinding, snapshot_math):
        path = Path(module.__file__).resolve()
        need(path.is_relative_to(repo), 'issuer dependency loaded outside private source')
        name = path.relative_to(repo).as_posix()
        need(name in gate.source_hashes and sha(path.read_bytes()) == gate.source_hashes[name],
             'running issuer dependency differs from prospective source')
    own = Path(__file__).resolve()
    need(own.is_relative_to(repo) and own.relative_to(repo).as_posix() == PACKAGE + 'export_snapshot.py'
         and sha(own.read_bytes()) == gate.source_hashes[PACKAGE + 'export_snapshot.py'],
         'running issuer differs from prospective source')


def _structured_candidates(files):
    """Structure-only preflight. It returns paths/field names, never values."""
    final, reports = {}, {}
    for name, raw in files.items():
        if not name.startswith(('data/', 'research/', 'analysis/')) or not name.endswith(('.json', '.jsonl')):
            continue
        try:
            records = ([snapshot_math.strict_json(line) for line in raw.splitlines() if line.strip()]
                       if name.endswith('.jsonl') else [snapshot_math.strict_json(raw)])
        except ValueError:
            raise SnapshotIssueError('registered structured source could not be inspected') from None
        def walk(value, trail=()):
            if type(value) is dict:
                for key, item in value.items():
                    field = trail + (key,)
                    normalized = re.sub('[^a-z0-9]', '', key.lower())
                    if normalized in FINAL_KEYS and type(item) is str and item:
                        final.setdefault(name, set()).add(field)
                    if normalized == 'thinkingcontrol' and trail == () and type(item) is dict:
                        reports.setdefault(name, set()).add(field)
                    walk(item, field)
            elif type(value) is list:
                for item in value:
                    walk(item, trail + ('[]',))
        for record in records:
            walk(record)
    return final, reports


def collect_approval_candidates(files):
    """Private preflight only; no approval is inferred from these field names."""
    need(type(files) is dict and all(type(raw) is bytes for raw in files.values()), 'source byte map required')
    return _structured_candidates(files)


def _approved_map(value):
    need(type(value) is dict, 'explicit reviewed field permission map required')
    result = {}
    for name, fields in value.items():
        _name(name)
        need(name.startswith(('data/', 'research/', 'analysis/')) and name.endswith(('.json', '.jsonl')),
             'field permission outside registered scientific data')
        try:
            normalized = frozenset(tuple(field) for field in fields)
        except TypeError:
            raise SnapshotIssueError('field permission shape invalid') from None
        need(normalized and all(field and all(type(part) is str and part for part in field)
                                for field in normalized), 'field permission shape invalid')
        result[name] = normalized
    return result


def _private_literals(value):
    """Materialize once so a one-shot iterable cannot bypass later file audits."""
    need(type(value) is dict and 'credential' in value
         and set(value) <= {'credential', 'private_header_value', 'native_response_id', 'private_answer'},
         'in-memory private-value checks required')
    result = {}
    total = 0
    for category, values in value.items():
        try:
            collected = []
            for index, item in enumerate(values):
                need(index < 10000 and type(item) is bytes and bool(item) and len(item) <= 1_000_000,
                     'private-literal input invalid or excessive')
                total += len(item)
                need(total <= 16_000_000, 'private-literal input excessive')
                collected.append(item)
        except TypeError:
            raise SnapshotIssueError('private-literal input invalid') from None
        result[category] = tuple(dict.fromkeys(collected))
    need(len(result['credential']) >= 3, 'private credential review scope differs')
    return result


def _no_retired_commitments(original, transformed, rules, public_files):
    """Reject visible retired digests and return the immutable decoded-audit set."""
    retired = {rule_span.line_sha256.encode('ascii') for rule in rules for rule_span in rule.spans}
    for name in original:
        if original[name] == transformed[name]:
            continue
        before = rebinding.variants(name, original[name])
        after = rebinding.variants(name, transformed[name])
        retired.update(value.encode('ascii') for kind, value in before.items() if after[kind] != value)
    for name, raw in public_files.items():
        candidates = [raw]
        if name.endswith('.json'):
            candidates.append(rebinding.canonical(raw))
        elif name.endswith('.jsonl'):
            candidates.extend(rebinding.canonical(line) for line in raw.splitlines() if line.strip())
        need(not any(match.group().lower() in retired for body in candidates
                     for match in rebinding.ANY_HASH_BYTES.finditer(body)),
             'private original commitment retained in disclosure')
    return frozenset(retired)


def _audit_private_files(files, forbidden_values, retired, approved, reports):
    """Apply the typed retired-digest guard to raw and decoded containers too."""
    need(type(retired) is frozenset and all(type(value) is bytes
         and re.fullmatch(rb'[0-9a-f]{64}', value) for value in retired),
         'private retired-commitment audit input differs')
    private = dict(forbidden_values)
    need('private_source_commitment' not in private,
         'private retired-commitment audit scope differs')
    private['private_source_commitment'] = tuple(sorted(retired))
    aliases = set()
    for name, raw in files.items():
        _name(name)
        need(name.casefold() not in aliases, 'aliased disclosure output path')
        aliases.add(name.casefold())
        privacy.audit_forbidden_values(name, raw, private,
                                       approved_final_output_fields=approved,
                                       approved_scientific_report_fields=reports)


def _new_readme():
    return b'''# When Can a Swarm Be Audited?

**Multi-Agent Oversight and Control.** This controlled, matched experiment asks
which part of oversight needs repair: acquiring authentic evidence, delivering a
usable verdict, or using sufficient evidence correctly. Read the
[submitted PDF](paper/out/swarm_audit_scoping.pdf) and the
[complete MAIN report](data/swarm-ledger-v1-public/report.json).

This is a sanitized publication snapshot, with a new explicit disclosure and
verification path. The original registered Git history and original protocol
text remain privately retained. Account-credit values are withheld; scientific
data, final study responses, scoring, bootstrap definitions, code and the
submitted PDF/DOCX are unchanged. Source-commitment metadata is explicitly rebound
to the disclosed documents. No new experimental calls were made.

The [disclosure protocol](research/PUBLIC_SNAPSHOT_DISCLOSURE_PROTOCOL.md) states
which checks can be repeated publicly and which original checks are privately
attested. The snapshot is organized as follows:

- `paper/out/`: the final PDF and editable DOCX.
- `data/`: MAIN, generator-sensitivity and earlier study artifacts.
- `experiments/`: unchanged scientific generation, parsing and scoring modules.
- `analysis/`: figure code and historical checks.
- `research/`: disclosed protocol copies and study context.
- `public_snapshot/`: the new admission, mathematical replay and fixture tests.

## Reproduce the disclosed study

Use Python 3.12. Obtain the
expected manifest and launcher SHA-256 values separately from the author's
release announcement; do not treat values inside this snapshot as external trust
anchors. The launcher authenticates the externally pinned manifest and complete
file inventory before importing project modules.

First check the launcher using only the standard library. Replace both placeholder
digests below with the independently obtained author release values. If a check
fails, stop; do not execute the launcher or install the snapshot's dependencies.

```text
python -I -B -c 'import hashlib,pathlib,re,sys;h=sys.argv[1];sys.exit(0 if re.fullmatch("[0-9a-f]{64}",h) and hashlib.sha256(pathlib.Path("public_snapshot/verify.py").read_bytes()).hexdigest()==h else "Launcher pin mismatch")' EXTERNAL_LAUNCHER_SHA256
python -I -B public_snapshot/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256 --preflight-only
python -m pip install -r paper/preparation-requirements.txt
python -I -B public_snapshot/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256 --tests-only
python -I -B -O public_snapshot/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256 --tests-only
python -I -B public_snapshot/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256
python -I -B -O public_snapshot/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256
```

GitHub Actions requires the author-controlled repository variables
`SNAPSHOT_MANIFEST_SHA256` and `SNAPSHOT_LAUNCHER_SHA256`. The workflow checks the
launcher against the latter before executing it, then runs the externally pinned
admission check before installing the admitted dependencies and replaying results.

The new mathematical route recomputes the disclosed results with the unchanged
scientific functions. It does not pretend to repeat authentication of omitted
original protocol bytes or private native-provider records. The admission receipt
explicitly records the author's privately completed original verification.

The [canonical README](provenance/CANONICAL_README.md) and original workflows are
preserved byte-for-byte as historical provenance. Their original Git-based
commands and relative links describe the privately retained archive, rather than
this new snapshot. Official upload and publication remain author actions.
'''


def _workflow():
    # Both pins are external repository variables, never read from admission.json.
    bootstrap = '''import hashlib,os,pathlib,re,subprocess,sys
p=pathlib.Path("public_snapshot/verify.py")
h=os.environ.get("SNAPSHOT_LAUNCHER_SHA256", "")
m=os.environ.get("SNAPSHOT_MANIFEST_SHA256", "")
if not re.fullmatch("[0-9a-f]{64}",h) or not re.fullmatch("[0-9a-f]{64}",m): raise SystemExit("External release pins required")
if hashlib.sha256(p.read_bytes()).hexdigest()!=h: raise SystemExit("Launcher pin mismatch")
flags=["-I","-B"]+(["-O"] if sys.flags.optimize else [])
subprocess.run([sys.executable,*flags,str(p),"--expected-manifest-sha256",m,*sys.argv[1:]],check=True)
'''
    text = '''name: Snapshot integrity
on: [push, pull_request, workflow_dispatch]
permissions:
  contents: read
jobs:
  snapshot-integrity:
    runs-on: ubuntu-latest
    env:
      SNAPSHOT_MANIFEST_SHA256: ${{ vars.SNAPSHOT_MANIFEST_SHA256 }}
      SNAPSHOT_LAUNCHER_SHA256: ${{ vars.SNAPSHOT_LAUNCHER_SHA256 }}
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
'''
    def step(name, arguments='', optimized=False):
        flags = '-I -B -O' if optimized else '-I -B'
        command = f"python {flags} -{(' ' + arguments) if arguments else ''} <<'PY'"
        script = command + '\n' + bootstrap + 'PY\n'
        return '      - name: ' + name + '\n        run: |\n' + ''.join('          ' + line + '\n' for line in script.splitlines())
    text += step('Authenticate external pins and disclosed files before dependencies', '--preflight-only')
    text += '''      - name: Install admitted verification dependencies
        run: python -m pip install -r paper/preparation-requirements.txt
'''
    text += step('Run admitted code tests', '--tests-only')
    text += step('Run admitted optimized code tests', '--tests-only', True)
    text += step('Verify disclosed mathematics and artifacts')
    text += step('Verify disclosed optimized mathematics and artifacts', optimized=True)
    return text.encode('utf-8')


def _protect_originals(original, transformed):
    need(set(original) == set(transformed), 'source inventory changed during disclosure')
    for name in original:
        if name.startswith(('data/', 'experiments/')) or name.endswith(('.py', '.pdf', '.docx')):
            need(transformed[name] == original[name], 'scientific data/code/artifact bytes changed')
    changed = {name for name in original if original[name] != transformed[name]}
    need(changed == set(a.REDACTION_PATHS) | set(a.REBINDING_PATHS), 'undeclared disclosure change')


def _assemble_files(transformed, tooling_files, *, redactions, rebindings,
                    private_attestation, tooling_source_commit):
    """Pure metadata assembly; production validates its result before writing."""
    need(type(redactions) is list and all(type(row) is dict and set(row) == {
        'path', 'line', 'category', 'semantic_role'} for row in redactions), 'private redaction guard in public metadata')
    need(type(rebindings) is list and all(type(row) is dict and set(row) == {
        'path', 'sha256', 'category'} for row in rebindings), 'private source guard in public metadata')
    files = {}
    roles = {}
    for name, raw in transformed.items():
        _name(name)
        target = ('provenance/CANONICAL_README.md' if name == 'README.md' else
                  'provenance/original-workflows/' + name[len('.github/workflows/'):]
                  if name.startswith('.github/workflows/') else name)
        _name(target)
        need(target not in files, 'relocated source path collision')
        files[target] = raw
        roles[target] = ('relocated' if target != name else 'redacted' if name in a.REDACTION_PATHS
                         else 'metadata_rebound' if name in a.REBINDING_PATHS else 'canonical')
    if '.gitattributes' in files:
        need('provenance/CANONICAL_GITATTRIBUTES' not in files, 'attribute provenance collision')
        files['provenance/CANONICAL_GITATTRIBUTES'] = files.pop('.gitattributes')
        roles['provenance/CANONICAL_GITATTRIBUTES'] = 'relocated'
        roles.pop('.gitattributes')
    generated = {'README.md': _new_readme(), '.gitattributes': GITATTRIBUTES,
                 '.github/workflows/snapshot-integrity.yml': _workflow()}
    for name, raw in dict(tooling_files, **generated).items():
        _name(name)
        need(name not in files and type(raw) is bytes, 'generated source path collision')
        files[name] = raw
        roles[name] = 'generated'
    need(LAUNCHER in files, 'trusted launcher missing')
    need(type(private_attestation) is dict and set(private_attestation) == a.RECEIPT_KEYS - {'manifest_sha256'},
         'explicit original-verification attestation required')
    receipt = a.decode_json(encode(private_attestation))
    manifest = dict(schema_version=1, kind=a.SCOPE, canonical_commit=a.CANONICAL_COMMIT,
                    canonical_tree=a.CANONICAL_TREE, tooling_source_commit=tooling_source_commit,
                    tooling_tag=TAG, policy=dict(a.POLICY),
                    files={name: dict(sha256=sha(raw), bytes=len(raw), role=roles[name])
                           for name, raw in sorted(files.items())},
                    redactions=redactions, rebindings=rebindings,
                    attestation_sha256=a.attestation_digest(receipt))
    manifest_raw = encode(manifest)
    receipt['manifest_sha256'] = sha(manifest_raw)
    files[a.MANIFEST] = manifest_raw
    files[a.RECEIPT] = encode(receipt)
    need(sha(files[a.MANIFEST]) == receipt['manifest_sha256']
         and a.attestation_digest(receipt) == manifest['attestation_sha256'], 'admission hash cycle differs')
    return files, manifest, receipt


def _destinations(source_repo, destination, issuer_receipt_path):
    destination, receipt = Path(destination), Path(issuer_receipt_path)
    need(destination.is_absolute() and receipt.is_absolute(), 'explicit absolute issuance destinations required')
    need(not destination.exists() and not destination.is_symlink()
         and destination.parent.is_dir() and not destination.parent.is_symlink(), 'new disclosure destination required')
    destination = destination.parent.resolve() / destination.name
    need(not any(part.casefold() == '.git' for part in destination.parts)
         and not destination.is_relative_to((source_repo / '.git').resolve()), 'Git archive destination refused')
    need(not receipt.exists() and not receipt.is_symlink() and receipt.parent.is_dir()
         and not receipt.parent.is_symlink(), 'new private issuer receipt required')
    receipt = receipt.parent.resolve() / receipt.name
    need(not receipt.is_relative_to(destination) and not destination.is_relative_to(receipt),
         'issuer receipt must remain outside disclosure')
    return destination, receipt


def _write_new_snapshot(destination, files):
    """No overwrite, move or recursive deletion; failed writes remain unadmitted."""
    need(not destination.exists() and not destination.is_symlink(), 'disclosure destination appeared')
    try:
        destination.mkdir(exist_ok=False)
        for name, raw in sorted(files.items()):
            path = destination / str(_name(name))
            path.parent.mkdir(parents=True, exist_ok=True)
            need(not any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(destination)),
                 'linked disclosure output refused')
            need(path.parent.resolve().is_relative_to(destination), 'escaped disclosure output refused')
            with path.open('xb') as target:
                target.write(raw)
        found = a.inventory(destination)
        need(found == set(files), 'written disclosure inventory differs')
        need(all((destination / name).read_bytes() == raw for name, raw in files.items()),
             'written disclosure bytes differ')
    except OSError:
        raise SnapshotIssueError('exclusive disclosure write failed') from None


def issue_snapshot(source_repo, destination, *, private_guard_plan, private_rebinding_plan,
                   forbidden_values, approved_final_output_fields, approved_scientific_report_fields,
                   private_attestation, issuer_receipt_path, expected_tooling_hashes,
                   expected_freeze_sha256, tooling_tag=TAG):
    """Issue ONLY after reviewed prospective source/tag/PUSH and private admission.

    No alternative canonical commit or boolean bypass is accepted. This function
    does not run the full scientific verifier; the returned candidate still needs
    the separately pinned full normal/optimized public replay.
    """
    try:
        source_repo = Path(source_repo).resolve()
        need(source_repo.is_dir(), 'private source repository unavailable')
        need(Path(_git_text(source_repo, 'rev-parse', '--show-toplevel')).resolve() == source_repo,
             'private source root differs')
        destination, issuer_receipt_path = _destinations(source_repo, destination, issuer_receipt_path)
        need(_git_text(source_repo, 'rev-parse', a.CANONICAL_COMMIT + '^{tree}') == a.CANONICAL_TREE,
             'canonical scientific tree differs')
        origin = _git_text(source_repo, 'remote', 'get-url', 'origin')
        need(origin in OFFICIAL_ORIGINS, 'authorized private origin required')
        gate = _verify_tooling_tag(source_repo, canonical_commit=a.CANONICAL_COMMIT,
                                  canonical_tree=a.CANONICAL_TREE,
                                  expected_tooling_hashes=expected_tooling_hashes,
                                  expected_freeze_sha256=expected_freeze_sha256,
                                  expected_origin=origin, tooling_tag=tooling_tag)
        _assert_running_sources(source_repo, gate)
        entries = _tree_entries(source_repo, a.CANONICAL_COMMIT)
        need(len(entries) == CANONICAL_FILES, 'canonical scientific file inventory differs')
        originals = _blobs(source_repo, entries)
        need(type(private_guard_plan) is dict and private_guard_plan.get('source_commit') == a.CANONICAL_COMMIT,
             'private privacy-plan source differs')
        rules = privacy.load_private_rule_metadata(private_guard_plan)
        need(len(rules) == 9 and sum(len(rule.spans) for rule in rules) == 10
             and {rule.path for rule in rules} == set(a.REDACTION_PATHS), 'reviewed privacy-plan scope differs')
        seeds = {}
        redactions = []
        for rule in rules:
            need(rule.path in originals, 'reviewed privacy source missing')
            seeds[rule.path], public = privacy.redact_document(originals[rule.path], rule)
            redactions.extend(dict(path=rule.path, **row) for row in public['redactions'])
        need(type(private_rebinding_plan) is dict and private_rebinding_plan.get('canonical_commit') == a.CANONICAL_COMMIT,
             'private source-commitment plan differs')
        transformed, metadata = rebinding.rebind_metadata(originals, seeds, private_rebinding_plan)
        _protect_originals(originals, transformed)
        rebound_rows = [dict(path=row['path'], sha256=row['sha256'], category='private_source_commitment')
                        for row in metadata['changes'] if row['path'] in a.REBINDING_PATHS]
        need({row['path'] for row in rebound_rows} == set(a.REBINDING_PATHS), 'rebinding disclosure inventory differs')
        approved = _approved_map(approved_final_output_fields)
        reports = _approved_map(approved_scientific_report_fields)
        candidates, report_candidates = _structured_candidates(originals)
        need(approved == {name: frozenset(fields) for name, fields in candidates.items()}
             and reports == {name: frozenset(fields) for name, fields in report_candidates.items()},
             'reviewed scientific field permissions differ')
        forbidden_values = _private_literals(forbidden_values)
        credential_count = len(forbidden_values['credential'])
        need(credential_count >= 3 and private_attestation['privacy_checks']['known_credential_values_checked'] == credential_count,
             'private credential review scope differs')
        files, manifest, receipt = _assemble_files(
            transformed, dict(gate.package_files), redactions=redactions, rebindings=rebound_rows,
            private_attestation=private_attestation, tooling_source_commit=gate.source_commit)
        a.validate_objects(manifest, receipt)
        retired = _no_retired_commitments(originals, transformed, rules, files)
        _audit_private_files(files, forbidden_values, retired, approved, reports)
        launcher_sha = sha(files[LAUNCHER])
        need(launcher_sha == gate.source_hashes[LAUNCHER], 'trusted launcher source differs')
        _write_new_snapshot(destination, files)
        # Load only the prospective, byte-checked stdlib admission module, from
        # the candidate itself, so its origin and exact-inventory checks apply.
        spec = importlib.util.spec_from_file_location('_issued_snapshot_admission', destination / PACKAGE / 'admission.py')
        need(spec is not None and spec.loader is not None, 'issued admission module unavailable')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        facts = module.verify_admission(destination, expected_manifest_sha256=receipt['manifest_sha256'])
        need(facts['disclosure_manifest_sha256'] == receipt['manifest_sha256'], 'issued admission differs')
        private_receipt = dict(
            schema_version=1, kind='private_sanitized_snapshot_issuance_v1',
            issued_at=datetime.now(timezone.utc).isoformat(), canonical_commit=a.CANONICAL_COMMIT,
            canonical_tree=a.CANONICAL_TREE, tooling_source_commit=gate.source_commit,
            tooling_tag=TAG, tooling_tag_commit=gate.tag_commit, tooling_freeze_sha256=gate.freeze_sha256,
            expected_manifest_sha256=receipt['manifest_sha256'], expected_launcher_sha256=launcher_sha,
            public_files=len(files), reviewed_redacted_files=9, reviewed_redacted_spans=10,
            private_original_protocol_admission=a.PRIVATE_ADMISSION,
            issuance_preflight='PASS', full_scientific_snapshot_replay='NOT_RUN',
            publication='NOT_PERFORMED', original_git_history='UNCHANGED_PRIVATE',
        )
        try:
            with issuer_receipt_path.open('xb') as target:
                target.write(encode(private_receipt))
        except OSError:
            raise SnapshotIssueError('exclusive private issuance receipt write failed') from None
        return private_receipt
    except (SnapshotIssueError, a.SnapshotAdmissionError, privacy.PrivacyPolicyError, rebinding.RebindingError):
        raise
    except Exception:
        raise SnapshotIssueError('snapshot issuance failed') from None
