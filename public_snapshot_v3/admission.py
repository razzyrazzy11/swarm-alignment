"""Explicit admission of a sanitized disclosure, not the private Git archive.

The receipt records the author's privately completed original checks. Public
checks authenticate disclosed bytes against that receipt and replay mathematics;
they do not repeat omitted original-protocol or native-provider authentication.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import tokenize

CANONICAL_COMMIT = '7c3f570fb89ffa685e495dce46349cc9caee4876'
CANONICAL_TREE = '4f4a08d4c60361dfc68c945ab93be544a48a4bbb'
CANONICAL_PDF = '418c27f6e9d5b7ecfc4e76f1c7bbb76ca412370d15c3ff5ff7741be1ea6fd193'
CANONICAL_DOCX = '2f91e32f28c3941af64e913a5868a805cc27e8d1383b45f08f9e01852c2221a7'
SCOPE = 'sanitized_public_snapshot_v3'
PRIVATE_ADMISSION = 'attested_not_publicly_repeated'
MANIFEST = 'public_snapshot_v3/disclosure-manifest.json'
RECEIPT = 'public_snapshot_v3/admission.json'
CHECKSUM_TEST_PATH = 'paper/tests/test_integrity.py'
FIXTURE_MANIFEST_PATH = 'paper/tests/fixtures/results-v3/manifest.json'
_CHECKSUM_LINE = 20
_CHECKSUM_SENTINEL = '__DISCLOSED_FIXTURE_MANIFEST_CHECKSUM__'
SAFE_FIXTURE_AST_SHA256 = '7075efa24c08d8c44b43cfa75c5ac051378d130c3b243517ea656ff09372937d'
REDACTION_PATHS = frozenset({
    'research/DEVIATIONS.md', 'research/PILOT_RESULTS.md',
    'research/PROTOCOL.md', 'research/REVIEW.md', 'research/SOURCE_AUDIT.md',
    'research/SUITE_STRATEGY.md', 'research/OLLAMA_PROTOCOL.md',
    'research/STATEFUL_RUNBOOK.md',
    'research/SWARM_MONITOR_TRAINING_FEASIBILITY.md',
})
MANIFEST_KEYS = frozenset({
    'schema_version', 'kind', 'canonical_commit', 'canonical_tree',
    'tooling_source_commit', 'tooling_tag', 'policy', 'files', 'redactions', 'rebindings',
    'attestation_sha256',
})
RECEIPT_KEYS = frozenset({
    'schema_version', 'kind', 'manifest_sha256', 'canonical_commit',
    'authority', 'original_verification', 'artifact_hashes',
    'private_original_protocol_admission', 'privacy_checks',
})
POLICY = {
    'public_mode': SCOPE,
    'private_original_protocol_admission': PRIVATE_ADMISSION,
    'original_git_history': 'privately_retained_not_in_snapshot',
    'scientific_values_and_final_responses': 'unchanged',
    'scientific_code': 'scientific_functions_unchanged_one_fixture_checksum_literal_rebound_assertions_unchanged',
    'source_commitment_metadata': 'explicitly_rebound_for_disclosure',
    'score_or_bootstrap_changes': False,
}
_HEX64 = re.compile(r'[0-9a-f]{64}')
_HEX40 = re.compile(r'[0-9a-f]{40}')
REBINDING_PATHS = frozenset({
    'analysis/calibration-breakdown-posthoc.json', 'paper/content.json',
    'paper/out/build-check.json', 'paper/out/pdf-check.json',
    'research/FINAL_REVIEW_3_CODE_PROVENANCE.md',
    'research/ollama-reader-v1-freeze.json',
    'research/adaption-serving-pilot-v1-freeze.json',
    'research/efficient-resume-analysis-v1-freeze.json',
    'research/factorial-report.json', 'research/factorial-reporting-freeze.json',
    'research/hf-completed-original-analysis-freeze.json',
    'research/hf-completed-original-analysis-v1-incomplete-freeze.json',
    'research/hf-completed-original-results-v3.json',
    'research/hf-completion-release-v1-freeze.json',
    'research/hf-completion-v2-freeze.json', 'research/hf-completion-v3-freeze.json',
    'research/hf-offline-release-recovery-v2-proof.json',
    'research/offline-release-recovery-v1-freeze.json',
    'research/offline-release-recovery-v2-freeze.json',
    'research/paced-resume-analysis-v1-freeze.json',
    'research/paper-public-release-admission.json',
    'research/paper-public-verification-v1-freeze.json',
    'research/provider-resume-analysis-v1-freeze.json',
    'research/rate-resume-analysis-v1-freeze.json',
    'research/router-resume-analysis-v1-freeze.json',
    'research/server-resume-analysis-v1-freeze.json',
    'research/swarm-ledger-paced-resume-release-proof.json',
    'paper/tests/fixtures/results-v3/out/build-check.json',
    FIXTURE_MANIFEST_PATH,
    CHECKSUM_TEST_PATH,
})


class SnapshotAdmissionError(ValueError):
    """An admission failure, with no private input in its message."""


def require(condition, message):
    if not condition:
        raise SnapshotAdmissionError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _checksum_ast(raw, checksum_line):
    require(type(raw) is bytes and type(checksum_line) is int and checksum_line > 0,
            'Explicit fixture checksum source and line required')
    try:
        text = raw.decode('utf-8-sig')
        tree = ast.parse(text)
        nodes = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Constant) and type(node.value) is str
                 and _HEX64.fullmatch(node.value) and node.lineno == checksum_line
                 and node.end_lineno == checksum_line]
        literal_tokens = []
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if (token.type == tokenize.STRING and token.start[0] == checksum_line
                    and token.end[0] == checksum_line):
                try:
                    value = ast.literal_eval(token.string)
                except (ValueError, SyntaxError):
                    continue
                if type(value) is str and _HEX64.fullmatch(value):
                    literal_tokens.append(value)
    except (UnicodeError, SyntaxError, tokenize.TokenError):
        raise SnapshotAdmissionError('Fixture checksum source is not admitted Python') from None
    require(len(nodes) == 1 and len(literal_tokens) == 1
            and nodes[0].value == literal_tokens[0],
            'Exactly one fixture checksum literal is required at the reviewed line')
    checksum = nodes[0].value
    nodes[0].value = _CHECKSUM_SENTINEL
    return ast.dump(tree, annotate_fields=True, include_attributes=False), checksum


def normalized_ast(raw, *, checksum_line):
    """Return a location-free AST with exactly one reviewed hash sentinel.

    No original private checksum is returned in this normalized representation.
    Comments and formatting do not authorize an assertion or expression change.
    """
    return _checksum_ast(raw, checksum_line)[0]


def verify_fixture_checksum_bytes(test_raw, manifest_raw):
    """Verify the sole disclosed test-checksum change without running the test.

    The safe baseline commits to the canonical test AST after removing its one
    private fixture-manifest checksum. All assertions and other AST values stay
    fixed, and the disclosed literal must match the exact manifest bytes. The
    original fixture is deliberately -text and its CRLF bytes are significant.
    """
    require(type(manifest_raw) is bytes, 'Fixture manifest bytes are required')
    normalized, checksum = _checksum_ast(test_raw, _CHECKSUM_LINE)
    require(digest(normalized.encode('utf-8')) == SAFE_FIXTURE_AST_SHA256,
            'Fixture integrity test assertions or AST changed')
    require(checksum == digest(manifest_raw),
            'Fixture integrity test does not bind the disclosed manifest')
    return True


def is_hash(value):
    return type(value) is str and _HEX64.fullmatch(value) is not None


def relative_name(value):
    require(type(value) is str and value and len(value) <= 512,
            'Invalid disclosure-relative path')
    require(not any(ord(c) < 32 for c in value) and '\\' not in value and ':' not in value,
            'Unsafe disclosure-relative path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value
            and all(part not in ('.', '..', '')
                    and not part.endswith(('.', ' '))
                    and not re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part, re.I)
                    for part in path.parts),
            'Unsafe disclosure-relative path')
    return path


def forbidden_name(value):
    path = relative_name(value)
    return any(part.startswith('runs') or part in {'.git', '.swarm', '.playwright-mcp'}
               for part in path.parts) or (
        path.name.startswith('.env') and path.name != '.env.example'
    ) or path.name in {'id_rsa', 'id_ed25519', '.modal.toml', 'private-rule-plan.json'} or (
        path.suffix.lower() in {'.pem', '.key'}
    )


def file_path(root, name):
    relative_name(name)
    path = root / name
    require(path.is_file() and not path.is_symlink()
            and path.resolve().is_relative_to(root),
            'Disclosure file is absent, linked or outside the snapshot')
    return path


def decode_json(raw):
    require(type(raw) is bytes and len(raw) <= 2_000_000, 'Disclosure JSON exceeds its size bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate disclosure JSON key')
            result[key] = value
        return result
    def bad_constant(_):
        raise SnapshotAdmissionError('Nonfinite disclosure JSON value')
    def finite_float(token):
        value = float(token)
        require(math.isfinite(value), 'Nonfinite disclosure JSON value')
        return value
    try:
        return json.loads(raw.decode('utf-8'),
                          object_pairs_hook=pairs, parse_constant=bad_constant,
                          parse_float=finite_float)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SnapshotAdmissionError('Malformed disclosure JSON') from None


def read_json(path):
    return decode_json(path.read_bytes())


def attestation_digest(receipt):
    """Bind author claims without the manifest back-reference; avoid a cycle."""
    claims = {key: value for key, value in receipt.items() if key != 'manifest_sha256'}
    raw = json.dumps(claims, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return digest(raw)


def validate_objects(manifest, receipt):
    require(type(manifest) is dict and set(manifest) == MANIFEST_KEYS,
            'Disclosure manifest schema differs')
    require(type(receipt) is dict and set(receipt) == RECEIPT_KEYS,
            'Private-admission receipt schema differs')
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1
            and type(receipt['schema_version']) is int and receipt['schema_version'] == 1,
            'Disclosure schema version differs')
    require(manifest['kind'] == SCOPE and receipt['kind'] == 'private_canonical_admission_attestation_v1',
            'Disclosure admission kind differs')
    require(manifest['canonical_commit'] == receipt['canonical_commit'] == CANONICAL_COMMIT,
            'Canonical scientific commit differs')
    require(manifest['canonical_tree'] == CANONICAL_TREE
            and type(manifest['tooling_source_commit']) is str
            and _HEX40.fullmatch(manifest['tooling_source_commit']) is not None
            and manifest['tooling_tag'] == 'public-snapshot-disclosure-v3',
            'Disclosure source identity differs')
    require(type(manifest['policy']) is dict and manifest['policy'] == POLICY
            and type(manifest['policy']['score_or_bootstrap_changes']) is bool,
            'Disclosure scientific/privacy boundary differs')
    require(receipt['authority'] == 'author_attested_private_canonical_verification'
            and receipt['private_original_protocol_admission'] == PRIVATE_ADMISSION,
            'Private-source attestation must remain explicit')
    require(is_hash(receipt['manifest_sha256']), 'Invalid disclosure manifest hash')
    require(is_hash(manifest['attestation_sha256'])
            and attestation_digest(receipt) == manifest['attestation_sha256'],
            'Author claims differ from the pinned disclosure')
    verification = receipt['original_verification']
    require(type(verification) is dict
            and set(verification) == {'normal_private', 'optimized_private', 'master_ci', 'master_ci_commit'}
            and type(verification['master_ci']) is int
            and verification == dict(normal_private='PASS', optimized_private='PASS',
                                     master_ci=42620835573, master_ci_commit=CANONICAL_COMMIT),
            'Original verification attestation differs')
    require(receipt['artifact_hashes'] == {
        'paper/out/swarm_audit_scoping.pdf': CANONICAL_PDF,
        'paper/out/swarm_audit_scoping.docx': CANONICAL_DOCX,
    }, 'Submitted artifact identity differs')
    privacy = receipt['privacy_checks']
    require(type(privacy) is dict and set(privacy) == {
        'policy_version', 'reviewed_files', 'reviewed_spans',
        'known_credential_values_checked', 'known_credential_matches',
        'structured_fields_checked', 'unknown_secret_absence_claimed',
    }, 'Privacy attestation schema differs')
    require(type(privacy['policy_version']) is int and privacy['policy_version'] == 1
            and type(privacy['reviewed_files']) is int
            and privacy['reviewed_files'] == 9 and type(privacy['reviewed_spans']) is int
            and privacy['reviewed_spans'] == 10
            and type(privacy['known_credential_values_checked']) is int
            and privacy['known_credential_values_checked'] >= 3
            and type(privacy['known_credential_matches']) is int
            and privacy['known_credential_matches'] == 0
            and privacy['structured_fields_checked'] is True
            and privacy['unknown_secret_absence_claimed'] is False,
            'Privacy review scope differs')
    files = manifest['files']
    require(type(files) is dict and 1 <= len(files) <= 2000, 'Invalid disclosure inventory')
    require(all(type(name) is str for name in files)
            and len({name.casefold() for name in files}) == len(files),
            'Case-aliased disclosure paths')
    for name, item in files.items():
        require(not forbidden_name(name) and name not in {MANIFEST, RECEIPT},
                'Excluded or circular disclosure inventory entry')
        require(type(item) is dict and set(item) == {'sha256', 'bytes', 'role'}
                and is_hash(item['sha256']) and type(item['bytes']) is int
                and 0 <= item['bytes'] <= 100_000_000,
                'Disclosure file commitment differs')
        role = item['role']
        require(type(role) is str and role in {'canonical', 'redacted', 'metadata_rebound', 'generated', 'relocated'},
                'Unknown disclosure file role')
        if role == 'redacted':
            require(name in REDACTION_PATHS, 'Undeclared scientific/source redaction')
        if role == 'metadata_rebound':
            require(name in REBINDING_PATHS, 'Unreviewed source-commitment rebinding')
        if name == CHECKSUM_TEST_PATH:
            require(role == 'metadata_rebound', 'Fixture checksum test must be explicitly disclosed')
        elif name.startswith(('data/', 'experiments/')) or name.endswith('.py') and name.startswith(('analysis/', 'paper/')):
            require(role == 'canonical', 'Scientific data/code/paper bytes must be unchanged')
    redactions = manifest['redactions']
    require(type(redactions) is list and len(redactions) == 10,
            'Reviewed redaction span count differs')
    paths = set()
    for row in redactions:
        require(type(row) is dict and set(row) == {'path', 'line', 'category', 'semantic_role'},
                'Redaction disclosure must omit private source/value details')
        require(type(row['path']) is str and row['path'] in REDACTION_PATHS and row['path'] in files
                and files[row['path']]['role'] == 'redacted'
                and type(row['line']) is int and row['line'] > 0
                and type(row['category']) is str
                and row['category'] in {'provider_account_credit', 'provider_account_balance'}
                and type(row['semantic_role']) is str and row['semantic_role'] in {
                    'initial_credit_observed', 'starting_credit_observed',
                    'remaining_credit_observed', 'provider_available_credit_observed',
                    'stated_starting_credit_allocation',
                }, 'Reviewed redaction role differs')
        paths.add(row['path'])
    require(paths == REDACTION_PATHS, 'Reviewed redaction file set differs')
    require({n for n, item in files.items() if item['role'] == 'redacted'} == REDACTION_PATHS,
            'Undisclosed redacted file')
    expected = [
        ('research/DEVIATIONS.md', 68, 'initial_credit_observed'),
        ('research/PILOT_RESULTS.md', 49, 'starting_credit_observed'),
        ('research/PROTOCOL.md', 51, 'initial_credit_observed'),
        ('research/REVIEW.md', 133, 'initial_credit_observed'),
        ('research/SOURCE_AUDIT.md', 66, 'initial_credit_observed'),
        ('research/SUITE_STRATEGY.md', 49, 'initial_credit_observed'),
        ('research/OLLAMA_PROTOCOL.md', 33, 'remaining_credit_observed'),
        ('research/STATEFUL_RUNBOOK.md', 73, 'provider_available_credit_observed'),
        ('research/STATEFUL_RUNBOOK.md', 73, 'provider_available_credit_observed'),
        ('research/SWARM_MONITOR_TRAINING_FEASIBILITY.md', 64, 'stated_starting_credit_allocation'),
    ]
    require(sorted((r['path'], r['line'], r['semantic_role']) for r in redactions) == sorted(expected)
            and all(r['category'] == 'provider_account_credit' for r in redactions),
            'Reviewed redaction coordinates differ')
    rebindings = manifest['rebindings']
    require(type(rebindings) is list and 1 <= len(rebindings) <= 512,
            'Source-commitment rebinding inventory differs')
    seen = set()
    for row in rebindings:
        require(type(row) is dict and set(row) == {'path', 'sha256', 'category'},
                'Source-commitment disclosure schema differs')
        require(type(row['path']) is str and row['path'] in REBINDING_PATHS and row['path'] in files
                and files[row['path']]['role'] == 'metadata_rebound'
                and is_hash(row['sha256']) and row['sha256'] == files[row['path']]['sha256']
                and row['category'] == 'private_source_commitment',
                'Source-commitment disclosure role differs')
        ident = row['path']
        require(ident not in seen, 'Duplicate source metadata disclosure')
        seen.add(ident)
    require({r['path'] for r in rebindings}
            == {n for n, item in files.items() if item['role'] == 'metadata_rebound'}
            == REBINDING_PATHS,
            'Undisclosed source metadata file')
    return {name: value['sha256'] for name, value in files.items()}


def inventory(root):
    found = set()
    for path in root.rglob('*'):
        parts = path.relative_to(root).parts
        if parts[0] == '.git':
            git_dir = root / '.git'
            require(git_dir.is_dir() and not git_dir.is_symlink()
                    and git_dir.resolve() == git_dir.absolute(), 'Unsafe root Git directory')
            continue
        require('.git' not in parts and '__pycache__' not in parts
                and path.suffix.lower() not in {'.pyc', '.pyo'},
                'Nested Git history or bytecode cache in disclosure')
        require(not path.is_symlink() and path.resolve().is_relative_to(root),
                'Linked or escaped snapshot path')
        if path.is_file():
            found.add(path.relative_to(root).as_posix())
    return found


def verify_admission(root, *, expected_manifest_sha256):
    root = Path(root).resolve()
    require(is_hash(expected_manifest_sha256),
            'A separately obtained expected manifest digest is required')
    require(Path(__file__).resolve().is_relative_to(root),
            'Admission module was loaded outside the snapshot')
    manifest_path, receipt_path = file_path(root, MANIFEST), file_path(root, RECEIPT)
    manifest_raw, receipt_raw = manifest_path.read_bytes(), receipt_path.read_bytes()
    require(digest(manifest_raw) == expected_manifest_sha256,
            'Disclosure differs from the externally pinned manifest')
    manifest, receipt = decode_json(manifest_raw), decode_json(receipt_raw)
    require(digest(manifest_raw) == receipt['manifest_sha256'],
            'Disclosure manifest hash mismatch')
    files = validate_objects(manifest, receipt)
    require(inventory(root) == set(files) | {MANIFEST, RECEIPT},
            'Missing or extra snapshot files')
    for name, expected in files.items():
        path = file_path(root, name)
        require(path.stat().st_size == manifest['files'][name]['bytes']
                and digest(path.read_bytes()) == expected,
                'Disclosed file bytes differ')
    for name, expected in receipt['artifact_hashes'].items():
        require(name in files and files[name] == expected, 'Submitted artifact is missing or changed')
    require(CHECKSUM_TEST_PATH in files and FIXTURE_MANIFEST_PATH in files,
            'Disclosed fixture checksum inputs are missing')
    verify_fixture_checksum_bytes(file_path(root, CHECKSUM_TEST_PATH).read_bytes(),
                                  file_path(root, FIXTURE_MANIFEST_PATH).read_bytes())
    return dict(schema_version=1, canonical_commit=CANONICAL_COMMIT,
                disclosure_manifest_sha256=receipt['manifest_sha256'], files=files,
                scope=SCOPE, private_original_protocol_admission=PRIVATE_ADMISSION)
