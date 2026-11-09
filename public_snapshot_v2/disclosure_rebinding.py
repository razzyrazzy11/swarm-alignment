"""Explicit byte-preserving metadata rebinding for a NEW public admission route.

Original files and their private location plan stay private. Only reviewed
64-hex metadata value tokens are replaced, never scientific rows or experiment
logic. V2 also permits one checksum literal in one historical fixture test.
No historical source validator is patched, and no Git ref is changed here.
The helper performs no filesystem/network I/O and has no real-source defaults.
"""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import PurePosixPath
import re


HASH = re.compile(r'[0-9a-f]{64}')
HASH_BYTES = re.compile(rb'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])')
ANY_HASH_BYTES = re.compile(rb'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', re.IGNORECASE)
KINDS = {'raw', 'lf', 'canonical_json'}
PLAN_KEYS = {'schema_version', 'canonical_commit', 'original_sha256', 'seed_sha256', 'locations'}
FIXTURE_CHECKSUM_TARGET = 'paper/tests/test_integrity.py'
FIXTURE_CHECKSUM_SOURCE = 'paper/tests/fixtures/results-v3/manifest.json'
FIXTURE_CHECKSUM_LINE = 20


class RebindingError(ValueError):
    """Category-only errors never include a private hash, line or value."""


def need(ok, category):
    if not ok:
        raise RebindingError(category)


def sha(raw):
    need(type(raw) is bytes, 'file bytes required')
    return hashlib.sha256(raw).hexdigest()


def path_name(name):
    need(type(name) is str and bool(name) and ':' not in name and '\\' not in name and
         not any(ord(c) < 32 for c in name), 'unsafe metadata path')
    path = PurePosixPath(name)
    need(not path.is_absolute() and str(path) == name and
         all(p not in ('', '.', '..', '.git') for p in path.parts), 'unsafe metadata path')
    need(not any(p == 'runs' or p.startswith('runs-') for p in path.parts), 'private run path refused')
    return path


def metadata_path(name):
    path = path_name(name)
    need(name == FIXTURE_CHECKSUM_TARGET or
         (path.parts[0] in {'research', 'paper', 'analysis'} and path.suffix in {'.json', '.md'}),
         'scientific data/code target refused')
    return path


def _fixture_checksum_controls(target, controls):
    """V2's only Python target is one guarded fixture checksum token."""
    if target != FIXTURE_CHECKSUM_TARGET:
        return
    need(type(controls) is list and len(controls) == 1, 'fixture checksum requires one control')
    control = controls[0]
    need(control.get('kind') == 'text_line'
         and control.get('source_path') == FIXTURE_CHECKSUM_SOURCE
         and type(control.get('line')) is int and control['line'] == FIXTURE_CHECKSUM_LINE
         and type(control.get('token_index')) is int and control['token_index'] == 0
         and type(control.get('expected_token_count')) is int and control['expected_token_count'] == 1
         and type(control.get('hash_variants')) is list and bool(control['hash_variants'])
         and all(type(kind) is str for kind in control['hash_variants'])
         and set(control['hash_variants']) <= {'raw', 'lf'},
         'fixture checksum scope differs')


def _finite(value):
    if type(value) is float:
        need(math.isfinite(value), 'nonfinite metadata JSON')
    elif type(value) is dict:
        for child in value.values():
            _finite(child)
    elif type(value) is list:
        for child in value:
            _finite(child)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate metadata JSON key')
        result[key] = value
    return result


DECODER = json.JSONDecoder(object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(RebindingError('nonfinite metadata JSON')))


def canonical(raw):
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(RebindingError('nonfinite metadata JSON')))
    except (UnicodeError, json.JSONDecodeError):
        raise RebindingError('invalid metadata JSON') from None
    _finite(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def variants(name, raw):
    result = {'raw': sha(raw), 'lf': sha(raw.replace(b'\r\n', b'\n'))}
    if PurePosixPath(name).suffix == '.json':
        result['canonical_json'] = sha(canonical(raw))
    return result


def _pointer(parts):
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def json_string_tokens(raw):
    """Return RFC6901 pointer -> exact UTF-8 byte span for each string VALUE.

    Keys and other primitive values are never replacement targets. Offsets are
    UTF-8 bytes, so non-ASCII prefixes and original indentation/newlines survive.
    """
    need(type(raw) is bytes, 'file bytes required')
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        raise RebindingError('invalid metadata JSON encoding') from None
    # Preserve the BOM if present; it is not part of the JSON grammar.
    start = 1 if text.startswith('\ufeff') else 0
    tokens = {}

    def ws(index):
        while index < len(text) and text[index] in ' \t\r\n':
            index += 1
        return index

    def parse(index, parts):
        index = ws(index)
        need(index < len(text), 'truncated metadata JSON')
        if text[index] == '{':
            index = ws(index + 1)
            seen = set()
            if index < len(text) and text[index] == '}':
                return index + 1
            while True:
                try:
                    key, end = DECODER.raw_decode(text, index)
                except (json.JSONDecodeError, ValueError):
                    raise RebindingError('invalid metadata JSON object') from None
                need(type(key) is str and key not in seen, 'duplicate or invalid metadata JSON key')
                seen.add(key)
                index = ws(end)
                need(index < len(text) and text[index] == ':', 'invalid metadata JSON object')
                index = ws(parse(index + 1, parts + (key,)))
                need(index < len(text), 'truncated metadata JSON object')
                if text[index] == '}':
                    return index + 1
                need(text[index] == ',', 'invalid metadata JSON object separator')
                index = ws(index + 1)
        if text[index] == '[':
            index = ws(index + 1)
            if index < len(text) and text[index] == ']':
                return index + 1
            count = 0
            while True:
                index = ws(parse(index, parts + (str(count),)))
                count += 1
                need(index < len(text), 'truncated metadata JSON array')
                if text[index] == ']':
                    return index + 1
                need(text[index] == ',', 'invalid metadata JSON array separator')
                index = ws(index + 1)
        try:
            value, end = DECODER.raw_decode(text, index)
        except (json.JSONDecodeError, ValueError):
            raise RebindingError('invalid metadata JSON primitive') from None
        _finite(value)
        if type(value) is str:
            pointer = _pointer(parts)
            need(pointer not in tokens, 'ambiguous metadata JSON pointer')
            byte_start = len(text[:index].encode('utf-8'))
            byte_end = len(text[:end].encode('utf-8'))
            tokens[pointer] = dict(value=value, start=byte_start, end=byte_end,
                                   parts=parts, line=text.count('\n', 0, index) + 1)
        return end

    try:
        end = ws(parse(start, ()))
    except RecursionError:
        raise RebindingError('metadata JSON nesting limit') from None
    need(end == len(text), 'extra metadata JSON content')
    return tokens


def _original_variants(original_files, source):
    need(source in original_files, 'reviewed metadata source missing')
    return variants(source, original_files[source])


def _matching_variants(original_files, source, digest):
    matches = sorted(k for k, value in _original_variants(original_files, source).items() if value == digest)
    need(bool(matches), 'unknown original source-hash variant')
    return matches


def build_private_location_plan(original_files, seed_changes, reviewed_findings, canonical_commit):
    """Build PRIVATE guarded controls from reviewed category/path findings.

    The findings may contain scanner-style json_field displays whose dictionary
    keys contain slashes. Resolve those to a unique real scalar pointer rather
    than guessing how to split the display. This function does not transform
    any file; its output contains private guards and must never be published.
    """
    need(type(canonical_commit) is str and re.fullmatch(r'[0-9a-f]{40}', canonical_commit) is not None,
         'canonical source identity invalid')
    need(type(original_files) is dict and original_files and type(seed_changes) is dict,
         'explicit original/seed file maps required')
    for name, raw in original_files.items():
        path_name(name)
        need(type(raw) is bytes, 'original file bytes required')
    base = dict(original_files)
    for name, raw in seed_changes.items():
        metadata_path(name)
        need(name != FIXTURE_CHECKSUM_TARGET, 'fixture checksum cannot be a privacy seed')
        need(name in original_files and type(raw) is bytes and raw != original_files[name], 'invalid privacy seed change')
        base[name] = raw
    need(type(reviewed_findings) is list and bool(reviewed_findings), 'reviewed location findings required')
    controls = {}
    for finding in reviewed_findings:
        need(type(finding) is dict and finding.get('category') in
             {'direct_private_source_commitment', 'indirect_private_source_commitment', 'private_source_commitment'},
             'unreviewed location category')
        target = finding.get('path')
        source = finding.get('private_metadata_source_path', finding.get('source_path'))
        target_path = metadata_path(target)
        path_name(source)
        need(target in original_files and source in original_files, 'reviewed source/target missing')
        original_variants = _original_variants(original_files, source)
        if target_path.suffix == '.json':
            original_tokens = json_string_tokens(original_files[target])
            if 'json_pointer' in finding:
                pointers = [finding['json_pointer']] if finding['json_pointer'] in original_tokens else []
            elif 'json_field' in finding:
                display = finding['json_field']
                pointers = [pointer for pointer, value in original_tokens.items()
                            if '/' + '/'.join(value['parts']) == display]
                need(len(pointers) == 1, 'ambiguous or unknown scanner JSON field')
            else:
                line = finding.get('line')
                need(type(line) is int and line > 0, 'reviewed JSON location missing')
                pointers = [pointer for pointer, value in original_tokens.items()
                            if value['line'] == line and value['value'] in original_variants.values()]
            need(bool(pointers), 'unknown reviewed JSON location')
            for pointer in pointers:
                token = original_tokens[pointer]
                need(type(token['value']) is str and HASH.fullmatch(token['value']) is not None,
                     'reviewed JSON value is not a hash')
                choices = _matching_variants(original_files, source, token['value'])
                base_token = json_string_tokens(base[target]).get(pointer)
                need(base_token is not None and base_token['value'] == token['value'], 'privacy seed changed a reviewed metadata hash')
                control = dict(kind='json_pointer', pointer=pointer, source_path=source, hash_variants=choices)
                key = (target, 'json_pointer', pointer)
                need(key not in controls or controls[key] == control, 'ambiguous metadata source at location')
                controls[key] = control
        else:
            line = finding.get('line')
            need(type(line) is int and line > 0, 'reviewed text line missing')
            if target == FIXTURE_CHECKSUM_TARGET:
                need(line == FIXTURE_CHECKSUM_LINE and source == FIXTURE_CHECKSUM_SOURCE,
                     'fixture checksum source or line differs')
            original_lines = original_files[target].splitlines(keepends=True)
            base_lines = base[target].splitlines(keepends=True)
            need(len(original_lines) == len(base_lines) and line <= len(original_lines), 'privacy seed changed reviewed line structure')
            found = list(HASH_BYTES.finditer(original_lines[line - 1]))
            candidates = [(i, match.group().decode('ascii')) for i, match in enumerate(found)
                          if match.group().decode('ascii') in original_variants.values()]
            need(bool(candidates), 'unknown reviewed text hash location')
            base_found = list(HASH_BYTES.finditer(base_lines[line - 1]))
            need(len(base_found) == len(found), 'privacy seed changed reviewed hash-token count')
            for index, digest in candidates:
                need(base_found[index].group().decode('ascii') == digest, 'privacy seed changed a reviewed metadata hash')
                choices = _matching_variants(original_files, source, digest)
                if target == FIXTURE_CHECKSUM_TARGET:
                    choices = [kind for kind in choices if kind in {'raw', 'lf'}]
                    need(bool(choices), 'fixture checksum requires raw or LF source hash')
                control = dict(kind='text_line', line=line, token_index=index, expected_token_count=len(found),
                               line_sha256=sha(base_lines[line - 1]), source_path=source,
                               hash_variants=choices)
                key = (target, 'text_line', line, index)
                need(key not in controls or controls[key] == control, 'ambiguous metadata source at location')
                controls[key] = control
    locations = defaultdict(list)
    for key in sorted(controls):
        locations[key[0]].append(controls[key])
    for target, target_controls in locations.items():
        _fixture_checksum_controls(target, target_controls)
    return dict(schema_version=1, canonical_commit=canonical_commit,
                original_sha256={name: sha(raw) for name, raw in sorted(original_files.items())},
                seed_sha256={name: sha(raw) for name, raw in sorted(seed_changes.items())},
                locations=dict(locations))


def _topological(locations):
    order, state = [], {}
    def visit(name):
        need(state.get(name) != 'visiting', 'metadata commitment cycle')
        if state.get(name) == 'done':
            return
        state[name] = 'visiting'
        for control in locations.get(name, []):
            visit(control['source_path'])
        state[name] = 'done'
        order.append(name)
    for target in sorted(locations):
        visit(target)
    return order


def _new_digest(original_files, current, control):
    source = control['source_path']
    choices = control['hash_variants']
    need(type(choices) is list and bool(choices) and len(set(choices)) == len(choices) and set(choices) <= KINDS,
         'invalid reviewed hash-variant controls')
    before = _original_variants(original_files, source)
    need(all(kind in before for kind in choices) and len({before[k] for k in choices}) == 1,
         'ambiguous original source-hash variants')
    after = variants(source, current[source])
    need(len({after[k] for k in choices}) == 1, 'ambiguous updated source-hash variants')
    return before[choices[0]], after[choices[0]]


def _apply(target, base, original_files, current, controls):
    _fixture_checksum_controls(target, controls)
    raw = base[target]
    spans = []
    tokens = json_string_tokens(raw) if target.endswith('.json') else None
    lines = raw.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    for control in controls:
        old, new = _new_digest(original_files, current, control)
        if control['kind'] == 'json_pointer':
            need(set(control) == {'kind', 'pointer', 'source_path', 'hash_variants'}, 'invalid JSON location control')
            need(tokens is not None and type(control['pointer']) is str and control['pointer'] in tokens,
                 'unknown reviewed JSON pointer')
            token = tokens[control['pointer']]
            need(token['value'] == old and raw[token['start']:token['end']] == ('"' + old + '"').encode('ascii'),
                 'reviewed JSON token changed or escaped')
            start, end = token['start'] + 1, token['end'] - 1
        elif control['kind'] == 'text_line':
            need(set(control) == {'kind', 'line', 'token_index', 'expected_token_count', 'line_sha256', 'source_path', 'hash_variants'},
                 'invalid text location control')
            line, index, count = control['line'], control['token_index'], control['expected_token_count']
            need(type(line) is int and 1 <= line <= len(lines) and type(index) is int and index >= 0 and
                 type(count) is int and count > index and type(control['line_sha256']) is str and
                 sha(lines[line - 1]) == control['line_sha256'], 'reviewed text line guard changed')
            found = list(HASH_BYTES.finditer(lines[line - 1]))
            need(len(found) == count and found[index].group().decode('ascii') == old, 'reviewed text hash token changed')
            start, end = starts[line - 1] + found[index].start(), starts[line - 1] + found[index].end()
        else:
            raise RebindingError('unknown reviewed location kind')
        spans.append((start, end, new.encode('ascii')))
    spans.sort()
    need(all(left[1] <= right[0] for left, right in zip(spans, spans[1:])), 'overlapping reviewed locations')
    chunks, cursor = [], 0
    for start, end, value in spans:
        chunks.extend((raw[cursor:start], value))
        cursor = end
    chunks.append(raw[cursor:])
    return b''.join(chunks)


def rebind_metadata(original_files, seed_changes, private_plan):
    """Return new file bytes and public new-hash/path/category metadata only.

    Derive every pass from the original/seed base, never replace already changed
    strings opportunistically. No old hash is emitted in the public metadata.
    """
    need(type(original_files) is dict and original_files and type(seed_changes) is dict and type(private_plan) is dict and
         set(private_plan) == PLAN_KEYS, 'explicit rebinding input schema required')
    need(type(private_plan['schema_version']) is int and private_plan['schema_version'] == 1 and
         type(private_plan['canonical_commit']) is str and re.fullmatch(r'[0-9a-f]{40}', private_plan['canonical_commit']) is not None,
         'private location-plan identity differs')
    for name, raw in original_files.items():
        path_name(name)
        need(type(raw) is bytes, 'original file bytes required')
    need(private_plan['original_sha256'] == {name: sha(raw) for name, raw in sorted(original_files.items())},
         'original private file guards differ')
    need(private_plan['seed_sha256'] == {name: sha(raw) for name, raw in sorted(seed_changes.items())},
         'privacy seed guards differ')
    base = dict(original_files)
    for name, raw in seed_changes.items():
        metadata_path(name)
        need(name != FIXTURE_CHECKSUM_TARGET, 'fixture checksum cannot be a privacy seed')
        need(name in original_files and type(raw) is bytes and raw != original_files[name], 'invalid privacy seed change')
        base[name] = raw
    locations = private_plan['locations']
    need(type(locations) is dict and bool(locations), 'reviewed metadata locations required')
    for target, controls in locations.items():
        metadata_path(target)
        need(target in base and type(controls) is list and bool(controls), 'invalid reviewed target inventory')
        for control in controls:
            need(type(control) is dict and 'source_path' in control and 'kind' in control, 'invalid reviewed location')
            common = {'kind', 'source_path', 'hash_variants'}
            expected = common | ({'pointer'} if control['kind'] == 'json_pointer' else
                                 {'line', 'token_index', 'expected_token_count', 'line_sha256'} if control['kind'] == 'text_line' else set())
            need(control['kind'] in {'json_pointer', 'text_line'} and set(control) == expected,
                 'invalid reviewed location schema')
            need((target.endswith('.json') and control['kind'] == 'json_pointer') or
                 ((target.endswith('.md') or target == FIXTURE_CHECKSUM_TARGET)
                  and control['kind'] == 'text_line'), 'location kind differs from metadata format')
            path_name(control['source_path'])
            need(control['source_path'] in base, 'reviewed metadata source missing')
        _fixture_checksum_controls(target, controls)
    order = _topological(locations)
    current, fingerprints = dict(base), set()
    for _ in range(len(order) + 2):
        updated = dict(base)
        for target in order:
            if target in locations:
                updated[target] = _apply(target, base, original_files, updated, locations[target])
        if updated == current:
            current = updated
            break
        stamp = tuple((name, sha(updated[name])) for name in sorted(set(locations) | set(seed_changes)))
        need(stamp not in fingerprints, 'metadata rebinding did not converge')
        fingerprints.add(stamp)
        current = updated
    else:
        raise RebindingError('metadata rebinding fixed point not reached')
    # Old sensitive source digests elsewhere would remain a guessing oracle.
    retired = set()
    for name in current:
        if current[name] == original_files[name]:
            continue
        before, after = variants(name, original_files[name]), variants(name, current[name])
        retired.update(value.encode('ascii') for kind, value in before.items() if after[kind] != value)
    for name, raw in current.items():
        candidates = [raw]
        # JSON escaping must not hide an old digest from the closure check.
        if name.endswith('.json'):
            candidates.append(canonical(raw))
        elif name.endswith('.jsonl'):
            candidates.extend(canonical(line) for line in raw.splitlines() if line.strip())
        need(not any(match.group().lower() in retired for value in candidates for match in ANY_HASH_BYTES.finditer(value)),
             'unreviewed stale metadata commitment location')
    changes = []
    for name in sorted(current):
        if current[name] != original_files[name]:
            changes.append(dict(path=name, sha256=sha(current[name]), category='metadata_rebound' if name in locations else 'privacy_redacted_source'))
    return current, dict(schema_version=1, scope='sanitized_metadata_rebinding_v2', changes=changes)
