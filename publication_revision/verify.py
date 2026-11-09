"""Externally pinned, isolated, offline publication-revision entry point.

Check this file's digest against the author's external release value before
running it. The manifest pin must also come from outside this checkout.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import traceback

SCOPE = 'publication_editorial_revision_v1'
MANIFEST = 'publication_revision/manifest.json'
PARENT_MANIFEST = 'public_snapshot_v3/disclosure-manifest.json'
PARENT_RECEIPT = 'public_snapshot_v3/admission.json'
PARENT_MANIFEST_SHA256 = '93a801f3f07b1178b8e631de66ab4738ebedb4acfdf33a007aefdd5692dc21b4'
PARENT_LAUNCHER_SHA256 = 'ab46c5a9f30e826a4bbe227d6674309dca782c69279d9a6b2395bcccbdeb3c04'
PARENT_RECEIPT_SHA256 = '884318a1ed79f41934647c5b396aad06fb9e9a3c6de8a030a7c3678558ebf574'
PROTOCOL = 'research/PUBLICATION_EDITORIAL_REVISION_V1_PROTOCOL.md'
FREEZE = 'research/publication-editorial-revision-v1-freeze.json'
QA = 'research/editorial-paper-qa-v1.json'
KEYS = {'schema_version', 'kind', 'parent_manifest_sha256', 'files', 'changes', 'qa_path'}


class RevisionError(ValueError):
    """Category-only errors, without response text or private source values."""


class RevisionParser(argparse.ArgumentParser):
    def error(self, _message):
        raise RevisionError('Invalid arguments')


def require(ok, message):
    if not ok:
        raise RevisionError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hash_value(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def relative(value):
    require(type(value) is str and value and len(value) <= 512, 'Invalid revision path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and '\\' not in value and ':' not in value
            and not any(ord(c) < 32 for c in value)
            and all(part.casefold() not in {'', '.', '..', '.git', '__pycache__'}
                    and not part.endswith(('.', ' '))
                    and not re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part, re.I)
                    for part in path.parts), 'Unsafe revision path')
    require(not any(part == 'runs' or part.startswith('runs-') for part in path.parts)
            and not any((part == '.env' or part.startswith('.env.')) and part != '.env.example'
                        for part in path.parts)
            and path.suffix.lower() not in {'.pyc', '.pyo'}, 'Private or cached revision path')
    return path


def strict_json(raw):
    require(type(raw) is bytes and len(raw) <= 4_000_000, 'Revision JSON exceeds its bound')
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'Duplicate revision JSON key')
            out[key] = value
        return out
    def finite(token):
        value = float(token)
        require(math.isfinite(value), 'Nonfinite revision JSON')
        return value
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_float=finite,
                          parse_constant=lambda _: (_ for _ in ()).throw(RevisionError('Nonfinite revision JSON')))
    except (UnicodeError, json.JSONDecodeError):
        raise RevisionError('Malformed revision JSON') from None


def actual_files(root):
    require(root.is_dir() and not root.is_symlink(), 'Revision root must be a directory')
    found = set()
    for directory, dirs, names in os.walk(root, topdown=True, followlinks=False):
        here = Path(directory)
        for name in list(dirs):
            path = here / name
            info = path.lstat()
            require(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'Linked revision directory')
            if here == root and name == '.git':
                dirs.remove(name)
                continue
            relative(path.relative_to(root).as_posix())
        for name in names:
            path = here / name
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
                    and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'Linked or nonregular revision file')
            relative(path.relative_to(root).as_posix())
            found.add(path.relative_to(root).as_posix())
    require(len(found) == len({name.casefold() for name in found}), 'Aliased revision inventory')
    return found


def preflight(root, expected_manifest_sha256):
    require(hash_value(expected_manifest_sha256), 'External revision manifest pin required')
    root = Path(root).resolve()
    raw = (root / MANIFEST).read_bytes()
    require(sha(raw) == expected_manifest_sha256, 'Revision manifest pin differs')
    value = strict_json(raw)
    require(type(value) is dict and set(value) == KEYS and type(value['schema_version']) is int
            and value['schema_version'] == 1 and value['kind'] == SCOPE
            and value['parent_manifest_sha256'] == PARENT_MANIFEST_SHA256
            and value['qa_path'] == QA, 'Revision manifest schema or authority differs')
    files = value['files']
    require(type(files) is dict and 1 <= len(files) <= 2500 and MANIFEST not in files,
            'Revision inventory schema differs')
    for name, row in files.items():
        relative(name)
        require(type(row) is dict and set(row) == {'sha256', 'bytes'}
                and hash_value(row['sha256']) and type(row['bytes']) is int and row['bytes'] >= 0,
                'Revision file commitment differs')
    require(actual_files(root) == set(files) | {MANIFEST}, 'Revision inventory has missing or extra files')
    for name, row in files.items():
        current = (root / name).read_bytes()
        require(len(current) == row['bytes'] and sha(current) == row['sha256'], 'Revision file bytes differ')
    parent_raw = (root / PARENT_MANIFEST).read_bytes()
    receipt_raw = (root / PARENT_RECEIPT).read_bytes()
    require(sha(parent_raw) == PARENT_MANIFEST_SHA256 and sha(receipt_raw) == PARENT_RECEIPT_SHA256
            and sha((root / 'public_snapshot_v3/verify.py').read_bytes()) == PARENT_LAUNCHER_SHA256,
            'Preserved parent authority differs')
    parent = strict_json(parent_raw)
    require(type(parent) is dict and type(parent.get('files')) is dict,
            'Parent inventory schema differs')
    for name, row in parent['files'].items():
        if name.startswith('public_snapshot_v3/'):
            require(name in files and files[name]['sha256'] == row['sha256'],
                    'Immutable parent implementation differs before import')
    require((root / MANIFEST).read_bytes() == raw, 'Revision changed during preflight')
    return value, parent, strict_json(receipt_raw)


def safe_failure(exc, stage):
    return dict(valid=False, scope=SCOPE, stage=stage, error_type=type(exc).__name__,
                frames=[dict(file=Path(frame.filename).name, function=frame.name, line=frame.lineno)
                        for frame in traceback.extract_tb(exc.__traceback__)],
                detail='No input values or raw exception message are disclosed.')


def write_result(path, result, root):
    if path is None:
        return
    path = Path(path).absolute()
    require(path.suffix == '.json' and not path.resolve().is_relative_to(root)
            and path.parent.is_dir() and not path.parent.is_symlink()
            and not path.exists() and not path.is_symlink(),
            'Report must be a new JSON file outside the revision')
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


@contextmanager
def outside_working_directory(root):
    """Own a temporary view without changing or weakening the root audit hook."""
    previous = Path.cwd()
    owned = tempfile.TemporaryDirectory(prefix='publication-verification-')
    location = Path(owned.name).resolve()
    try:
        require(not location.is_relative_to(root), 'Temporary view must be outside the admitted revision')
        os.chdir(location)
        yield location
    finally:
        # Relative dir_fd cleanup audit events must resolve outside the root.
        os.chdir(location.parent)
        try:
            owned.cleanup()
        finally:
            os.chdir(previous)


def main(argv=None):
    parser = RevisionParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--tests-only', action='store_true')
    parser.add_argument('--report-json', type=Path)
    root = Path(__file__).resolve().parents[1]
    args = None
    stage = 'arguments'
    try:
        args = parser.parse_args(argv)
        stage = 'preflight'
        require(sys.flags.isolated and sys.dont_write_bytecode, 'Run the revision with Python -I -B')
        require(not (args.preflight_only and args.tests_only), 'Choose one revision verification mode')
        preflight(root, args.expected_manifest_sha256)
        sys.path.insert(0, str(root))
        from public_snapshot_v3.verify import offline_read_only
        offline_read_only(root, allow_local_subprocess=args.tests_only)
        from publication_revision.admission import verify_admission
        callback = lambda location: verify_admission(location, expected_manifest_sha256=args.expected_manifest_sha256)
        stage = 'editorial_admission'
        facts = callback(root)
        if args.preflight_only:
            result = dict(valid=True, scope=SCOPE, stage=stage, scientific_verification_performed=False)
        elif args.tests_only:
            import unittest
            sys.path.insert(0, str(root / 'public_snapshot_v3'))
            with outside_working_directory(root):
                loader = unittest.TestLoader()
                suite = unittest.TestSuite(loader.discover(str(root / name), pattern='test_*.py',
                                                          top_level_dir=str(root))
                                           for name in ('public_snapshot_v3', 'publication_revision'))
                outcome = unittest.TextTestRunner(verbosity=1).run(suite)
            require(outcome.wasSuccessful() and outcome.testsRun >= 150 and not outcome.skipped,
                    'Required parent and editorial code tests failed or skipped')
            require(callback(root) == facts, 'Revision changed during code tests')
            result = dict(valid=True, scope=SCOPE, tests=outcome.testsRun, skipped=len(outcome.skipped),
                          scientific_verification_performed=False)
        else:
            from public_snapshot_v3.snapshot_math import verify_main_and_sensitivity
            from public_snapshot_v3.snapshot_legacy import replay_legacy
            from publication_revision.artifacts import verify_artifacts
            current = Path.cwd()
            try:
                os.chdir(root)
                stage = 'main_and_sensitivity'
                print(json.dumps(dict(stage=stage, status='running')), flush=True)
                main_result = verify_main_and_sensitivity(root, callback)
                stage = 'historical_mathematics'
                print(json.dumps(dict(stage=stage, status='running')), flush=True)
                legacy_result = replay_legacy(root, callback)
                stage = 'revised_papers'
                print(json.dumps(dict(stage=stage, status='running')), flush=True)
                artifact_result = verify_artifacts(root, callback, main_result)
            finally:
                os.chdir(current)
            stage = 'final_admission'
            require(callback(root) == facts, 'Revision changed during verification')
            result = dict(valid=True, scope=SCOPE, mathematical_route='sanitized_public_snapshot_v3',
                          original_protocol_admission='preserved_parent_attestation_not_repeated',
                          mathematics=main_result, legacy=legacy_result, artifacts=artifact_result,
                          scientific_verification_performed=True)
        result.update(optimized=bool(sys.flags.optimize), isolated=True, experimental_provider_calls=0,
                      manifest_sha256=args.expected_manifest_sha256)
        write_result(args.report_json, result, root)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        result = safe_failure(exc, stage)
        try:
            write_result(args.report_json if args is not None else None, result, root)
        except Exception:
            pass
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
