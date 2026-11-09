"""Admit an author-reviewed editorial successor without rewriting its parent."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .verify import (FREEZE, MANIFEST, PARENT_MANIFEST, PARENT_RECEIPT, PROTOCOL, QA,
                     RevisionError, preflight, relative, require, sha, strict_json)

AUTHORING = 'paper/prepare_complete.py'
CHECKSUM_TEST = 'paper/tests/test_integrity.py'
FIXTURE_MANIFEST = 'paper/tests/fixtures/results-v3/manifest.json'
AUTHORING_AST = 'e0f1de3f2d9cb017271abe527c9331dd6799120c6f7f81d2e773068d36a6d2ec'
AUTHORING_RAW_SHA256 = 'cdb8119637b52d420302876d33f66f7ef5fd96af5c7aca5f50bbe3869577be84'
FIXTURE_METADATA = '59988c8091a8384298b153d178b2d0b1819eb77ecddb1bd6a2e435aaf764a5b7'
METADATA = {
    FIXTURE_MANIFEST: FIXTURE_METADATA,
    'research/paper-public-figure-input.json': 'e9618c1a6da19cb296ce50e0d1a66756b8effbcf10eedc8bebf39afbb077da98',
    'paper/figures/swarm-ledger-complete-v1/ledger_figures_provenance.json': 'c2dd2abcfb39deddadb5383fe5a14cd729a782848476c7f17eb22489aafe5c4c',
}
PRESENTATION = {
    'paper/content.json': 'f5c91116e35b6efe672d87a8911f797ae629ae459c95217c43b8cc8369ab1ec8',
    'paper/complete-draft.json': '2e70ed79b86222bfbda07113e1a60ad83be3ebb8bd91131c1d12b0560db431dc',
    'paper/complete-reference-basis.json': 'e0ab7f9771215ce3484e4a2d2945034c0e0da87f068f1354e1b2ebde065c2d12',
    'paper/tests/fixtures/results-v3/content.json': '459496735b48e6e4e965459489268d974116e7ea95920aa0498b57aa5e217436',
}
DISPLAY_FIELDS = {
    'paper/complete-draft.json': {'subtitle': 'Multi-Agent Oversight and Control'},
    'paper/complete-reference-basis.json': {'scope': 'Editorially derived historical reference basis with an unrelated reference removed and remaining citations renumbered; no empirical results or private collection data'},
    'paper/tests/fixtures/results-v3/content.json': {
        'affiliation': 'Independent Researcher', 'subtitle': 'Multi-Agent Oversight and Control'},
}
EDITABLE_CONFIG = {'.gitignore', '.gitattributes', '.github/workflows/snapshot-integrity.yml'}


def masked_json(value):
    if type(value) is dict:
        return {key: masked_json(item) for key, item in value.items()}
    if type(value) is list:
        return [masked_json(item) for item in value]
    if type(value) is str and re.fullmatch('[0-9a-f]{64}', value):
        return '__HASH__'
    return value


def json_invariant(value):
    raw = json.dumps(masked_json(value), sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False).encode('utf-8')
    return sha(raw)


def authoring_ast(raw, expected_cardinality):
    """Normalize display strings inside the one draft function, and one guard."""
    tree = ast.parse(raw.decode('utf-8'))
    drafts = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'draft']
    require(len(drafts) == 1, 'Authoring function identity differs')
    guards = []
    for node in ast.walk(drafts[0]):
        if not (isinstance(node, ast.Compare) and isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name) and node.left.func.id == 'len'
                and len(node.left.args) == 1 and isinstance(node.left.args[0], ast.Subscript)):
            continue
        item = node.left.args[0]
        if (isinstance(item.value, ast.Name) and item.value.id == 'basis'
                and isinstance(item.slice, ast.Constant) and item.slice.value == 'references'
                and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq)
                and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant)
                and type(node.comparators[0].value) is int
                and node.comparators[0].value == expected_cardinality):
            guards.append(node.comparators[0])
    require(len(guards) == 1, 'Exact authoring bibliography guard differs')
    guards[0].value = 0
    for node in ast.walk(drafts[0]):
        if isinstance(node, ast.Constant) and type(node.value) is str:
            node.value = '__PRESENTATION_TEXT__'
    return sha(ast.dump(tree, annotate_fields=True, include_attributes=False).encode('utf-8'))


def artifact_path(name):
    return (name.startswith(('paper/out/', 'paper/tests/fixtures/results-v3/out/'))
            and Path(name).suffix.lower() in {'.pdf', '.docx', '.json'})


def validate_changes(parent_files, files, changes, read, checksum_checker):
    require(type(changes) is dict and all(name in parent_files for name in changes),
            'Only existing, explicitly reviewed paths may change')
    require(set(parent_files) <= set(files), 'Parent file deletion is not admitted')
    actual = {name for name, row in parent_files.items() if files[name]['sha256'] != row['sha256']}
    require(set(changes) == actual, 'Author-reviewed change set differs')
    for name in sorted(actual):
        category = changes[name]
        require(category in {'editorial', 'metadata', 'artifact'}, 'Unknown revision change category')
        require(not name.startswith(('data/', 'public_snapshot_v3/')),
                'Scientific data or preserved parent implementation changed')
        raw = read(name)
        if name.endswith('.py'):
            if name == AUTHORING:
                require(category == 'editorial' and sha(raw) == AUTHORING_RAW_SHA256
                        and authoring_ast(raw, 30) == AUTHORING_AST,
                        'Authoring logic changed outside presentation and exact bibliography guard')
            elif name == CHECKSUM_TEST:
                require(category == 'metadata', 'Fixture checksum category differs')
                checksum_checker(raw, read(FIXTURE_MANIFEST))
            else:
                raise RevisionError('Production or test code changed')
        elif name in PRESENTATION:
            value = strict_json(raw)
            require(type(value) is dict and category == 'editorial', 'Presentation document category differs')
            invariant = {key: item for key, item in value.items()
                         if key not in {'references', 'sections', 'appendix'}}
            for key, expected in DISPLAY_FIELDS.get(name, {}).items():
                require(value.get(key) == expected, 'Approved display field differs')
                invariant[key] = '__REVIEWED_DISPLAY_FIELD__'
            require(json_invariant(invariant) == PRESENTATION[name], 'Scientific presentation fields changed')
        elif artifact_path(name):
            require(category == 'artifact', 'Paper artifact category differs')
            if name.endswith('.json'):
                strict_json(raw)
        elif name in METADATA:
            require(category == 'metadata' and json_invariant(strict_json(raw)) == METADATA[name],
                    'Fixed provenance record changed beyond checksum metadata')
        elif name.endswith('.md') or name in EDITABLE_CONFIG:
            require(category == 'editorial', 'Editable document category differs')
            raw.decode('utf-8')
        else:
            raise RevisionError('Unreviewed kind of parent file changed')


def verify_admission(root, *, expected_manifest_sha256):
    root = Path(root).resolve()
    manifest, parent, receipt = preflight(root, expected_manifest_sha256)
    # Import only after the new externally pinned inventory authenticates the
    # unchanged parent module. Its old whole-root admission is never called.
    from public_snapshot_v3 import admission as old
    old.validate_objects(parent, receipt)
    require(receipt['manifest_sha256'] == manifest['parent_manifest_sha256'],
            'Parent receipt refers to a different immutable publication')
    parent_files = dict(parent['files'])
    parent_files[PARENT_MANIFEST] = dict(sha256=sha((root / PARENT_MANIFEST).read_bytes()))
    parent_files[PARENT_RECEIPT] = dict(sha256=sha((root / PARENT_RECEIPT).read_bytes()))
    files = manifest['files']
    extras = set(files) - set(parent_files)
    require({PROTOCOL, FREEZE, QA, 'publication_revision/verify.py',
             'publication_revision/admission.py', 'publication_revision/artifacts.py'} <= extras,
            'Editorial source, authority or QA record missing')
    require(all(name in {PROTOCOL, FREEZE, QA} or
                (name.startswith('publication_revision/') and Path(name).suffix in {'.py', '.md', '.txt'})
                for name in extras), 'Unexpected new revision file')
    read = lambda name: (root / relative(name)).read_bytes()
    validate_changes(parent_files, files, manifest['changes'], read, old.verify_fixture_checksum_bytes)
    freeze = strict_json(read(FREEZE))
    require(type(freeze) is dict and set(freeze) == {
        'kind', 'tag', 'parent_manifest_sha256', 'source_commit', 'source_sha256', 'created_utc'},
        'Editorial source freeze schema differs')
    require(freeze['kind'] == 'publication_editorial_revision_v1_source_freeze'
            and freeze['tag'] == 'publication-editorial-revision-v1'
            and freeze['parent_manifest_sha256'] == manifest['parent_manifest_sha256']
            and type(freeze['source_commit']) is str and re.fullmatch('[0-9a-f]{40}', freeze['source_commit']),
            'Editorial source freeze identity differs')
    source_names = {name for name in extras if name.startswith('publication_revision/')} | {PROTOCOL}
    source_hashes = freeze['source_sha256']
    require(type(source_hashes) is dict and source_names <= set(source_hashes)
            and set(source_hashes) <= source_names | EDITABLE_CONFIG
            and all(name in files and files[name]['sha256'] == digest
                    for name, digest in source_hashes.items()), 'Editorial registered source bytes differ')
    stamp = datetime.fromisoformat(freeze['created_utc'])
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0
            and stamp <= datetime.now(timezone.utc), 'Editorial source chronology differs')
    return dict(schema_version=1, canonical_commit=parent['canonical_commit'],
                disclosure_manifest_sha256=expected_manifest_sha256,
                files={name: row['sha256'] for name, row in files.items()},
                scope='sanitized_public_snapshot_v3',
                private_original_protocol_admission='attested_not_publicly_repeated')
