"""Trusted-launcher entry point for a separately pinned sanitized snapshot.

Obtain this launcher's checksum and the manifest checksum from the author's
separate release announcement. Check the launcher before executing it. A digest
read only from the downloaded archive is not an independent trust anchor.

Run with Python -I -B. Preflight uses only the standard library and runs before
project imports or dependency installation. Full verification is offline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import traceback

MANIFEST = 'public_snapshot_v2/disclosure-manifest.json'
RECEIPT = 'public_snapshot_v2/admission.json'
SCOPE = 'sanitized_public_snapshot_v2'


class LaunchError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise LaunchError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_relative(value):
    require(type(value) is str and value and len(value) <= 512,
            'Invalid declared path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and '\\' not in value
            and ':' not in value and not any(ord(c) < 32 for c in value)
            and all(p.casefold() not in {'', '.', '..', '.git', '__pycache__'}
                    and not p.endswith(('.', ' '))
                    and not re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p, re.I)
                    for p in path.parts),
            'Unsafe declared path')
    return path


def strict_json(raw):
    require(len(raw) <= 2_000_000, 'Manifest exceeds the preflight size bound')
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'Duplicate manifest key')
            out[key] = value
        return out
    def finite(token):
        value = float(token)
        require(math.isfinite(value), 'Nonfinite manifest number')
        return value
    def constant(_):
        raise LaunchError('Nonfinite manifest number')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_float=finite, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise LaunchError('Malformed manifest') from None


def actual_files(root):
    found = set()
    for directory, dirs, names in os.walk(root, topdown=True, followlinks=False):
        parent = Path(directory)
        for name in list(dirs):
            path = parent / name
            require(not path.is_symlink() and path.resolve() == path.absolute()
                    and path.resolve().is_relative_to(root), 'Linked snapshot directory')
            if name == '.git' and parent == root:
                dirs.remove(name)
                continue
            require(name not in {'.git', '__pycache__'}, 'Nested Git history or bytecode cache')
        for name in names:
            path = parent / name
            require(not path.is_symlink() and path.resolve().is_relative_to(root)
                    and name not in {'.git', '__pycache__'}
                    and path.suffix.lower() not in {'.pyc', '.pyo'},
                    'Linked file, Git indirection or bytecode cache')
            found.add(path.relative_to(root).as_posix())
    return found


def preflight(root, expected_digest):
    root = Path(root).resolve()
    require(type(expected_digest) is str and re.fullmatch(r'[0-9a-f]{64}', expected_digest),
            'An independently obtained expected manifest SHA-256 is required')
    manifest_path = root / MANIFEST
    require(manifest_path.is_file() and not manifest_path.is_symlink()
            and manifest_path.resolve().is_relative_to(root), 'Manifest missing or linked')
    raw = manifest_path.read_bytes()
    require(sha(raw) == expected_digest, 'External manifest pin differs')
    manifest = strict_json(raw)
    require(type(manifest) is dict and manifest.get('kind') == SCOPE
            and type(manifest.get('files')) is dict and 1 <= len(manifest['files']) <= 2000,
            'Unrecognized disclosure inventory')
    files = manifest['files']
    require(all(type(name) is str for name in files)
            and len({name.casefold() for name in files}) == len(files),
            'Case-aliased disclosure paths')
    require('public_snapshot_v2/verify.py' in files, 'Trusted launcher absent from inventory')
    for name, item in files.items():
        safe_relative(name)
        require(name not in {MANIFEST, RECEIPT} and type(item) is dict
                and set(item) == {'sha256', 'bytes', 'role'}
                and type(item['sha256']) is str
                and re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
                and type(item['bytes']) is int and 0 <= item['bytes'] <= 100_000_000,
                'Invalid preflight commitment')
    require(actual_files(root) == set(files) | {MANIFEST, RECEIPT},
            'Missing or extra snapshot files')
    for name, item in files.items():
        path = root / name
        require(path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(root), 'Unsafe preflight file')
        raw = path.read_bytes()
        require(len(raw) == item['bytes'] and sha(raw) == item['sha256'],
                'Disclosed file differs from the external pin')
    return manifest


def offline_read_only(root, *, allow_local_subprocess=False):
    root = root.resolve()
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    def inside(value):
        if not isinstance(value, (str, bytes, os.PathLike)):
            return False
        try:
            return Path(os.fsdecode(value)).resolve().is_relative_to(root)
        except (ValueError, OSError):
            return False
    def hook(event, args):
        if event in {'socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo'}:
            raise LaunchError('Network access is disabled during snapshot verification')
        if event == 'subprocess.Popen' and not allow_local_subprocess:
            raise LaunchError('Subprocess execution is disabled during mathematical replay')
        if event == 'open' and args:
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & write_flags
            )
            if writing and inside(args[0]):
                raise LaunchError('Verification cannot write inside the admitted snapshot')
        if event in {'os.remove', 'os.rmdir', 'os.mkdir', 'os.rename', 'os.replace'}:
            if any(inside(value) for value in args[:2]):
                raise LaunchError('Verification cannot mutate the admitted snapshot')
    sys.addaudithook(hook)


def safe_failure(exc, stage):
    return dict(valid=False, stage=stage, error_type=type(exc).__name__,
                frames=[dict(file=Path(f.filename).name, function=f.name, line=f.lineno)
                        for f in traceback.extract_tb(exc.__traceback__)],
                detail='No input values or raw exception message are disclosed.')


def write_result(path, result, root):
    if path is None:
        return
    path = Path(path).absolute()
    require(path.suffix == '.json' and not path.resolve().is_relative_to(root)
            and path.parent.is_dir() and not path.exists(),
            'Result path must be a new JSON file outside the snapshot')
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--tests-only', action='store_true')
    parser.add_argument('--report-json', type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    stage = 'preflight'
    try:
        require(sys.flags.isolated == 1 and sys.dont_write_bytecode is True,
                'Use the trusted launcher with Python -I -B')
        require(not (args.preflight_only and args.tests_only), 'Choose one verification mode')
        preflight(root, args.expected_manifest_sha256)
        if args.preflight_only:
            result = dict(preflight_valid=True, scientific_verification_performed=False,
                          manifest_sha256=args.expected_manifest_sha256)
        else:
            offline_read_only(root, allow_local_subprocess=args.tests_only)
            sys.path.insert(0, str(root))
            from public_snapshot_v2.admission import verify_admission
            admit = lambda candidate: verify_admission(
                candidate, expected_manifest_sha256=args.expected_manifest_sha256)
            stage = 'disclosure_admission'
            before = admit(root)
            if args.tests_only:
                import unittest
                suite = unittest.defaultTestLoader.discover(
                    str(root / 'public_snapshot_v2'), pattern='test_*.py')
                outcome = unittest.TextTestRunner(verbosity=2).run(suite)
                require(outcome.wasSuccessful(), 'Snapshot code tests failed')
                require(admit(root) == before, 'Snapshot changed during code tests')
                result = dict(code_tests_passed=True, tests=outcome.testsRun,
                              skipped=len(outcome.skipped), scientific_verification_performed=False,
                              manifest_sha256=args.expected_manifest_sha256)
            else:
                from public_snapshot_v2.snapshot_math import verify_main_and_sensitivity
                from public_snapshot_v2.snapshot_legacy import replay_legacy
                from public_snapshot_v2.artifacts import verify_artifacts
                stage = 'main_and_sensitivity'
                print(json.dumps(dict(stage=stage, status='running')), flush=True)
                current = verify_main_and_sensitivity(root, admit)
                stage = 'historical_mathematics'
                print(json.dumps(dict(stage=stage, status='running')), flush=True)
                legacy = replay_legacy(root, admit)
                stage = 'paper_and_figures'
                print(json.dumps(dict(stage=stage, status='running')), flush=True)
                artifacts = verify_artifacts(root, admit, current)
                stage = 'final_admission'
                require(admit(root) == before, 'Snapshot changed during verification')
                result = dict(valid=True, scope=SCOPE,
                              manifest_sha256=args.expected_manifest_sha256,
                              private_original_protocol_admission='attested_not_publicly_repeated',
                              original_native_provider_authentication='not_publicly_repeated',
                              main_and_sensitivity=current, historical_mathematics=legacy,
                              paper_and_figures=artifacts, experimental_provider_calls=0,
                              optimized=bool(sys.flags.optimize), isolated=True)
        write_result(args.report_json, result, root)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        result = safe_failure(exc, stage)
        try:
            write_result(args.report_json, result, root)
        except Exception:
            pass
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
