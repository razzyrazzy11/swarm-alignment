"""Independent visible-fact constraint solver for the finite lease workflow.

No generator, simulator, projector or engine validator is imported. Empty support
means malformed or inconsistent evidence; it is never a definite accusation.
"""
import hashlib
from itertools import permutations, product


_KINDS = ('binding', 'grant', 'advisory', 'binding', 'delegation',
          'advisory', 'binding', 'request', 'result', 'clock',
          'revocation', 'lease', 'background', 'background', 'background', 'background')
_HANDLES = ('h0', 'h0', 'h1', 'h1', 'h1', 'h2', 'h2', 'h2', 'h2',
            'h2', 'L', 'L', 'b0', 'b1', 'b2', 'b3')
_FIELDS = (
    {'instance': str}, {'issued': bool, 'lease': str, 'epoch': int},
    {'text': str}, {'instance': str},
    {'delegated': bool, 'parent': str, 'epoch': int, 'child': str},
    {'text': str}, {'instance': str}, {'target': str, 'increment': int},
    {'outcome': str, 'before': int, 'after': int, 'closed': bool},
    {'settled_at': int}, {'revoked': bool, 'effective_at': (int, type(None))},
    {'valid_from': int, 'expires_at': int, 'scope': str, 'cap': int, 'epoch': int},
    {'value': int}, {'value': int}, {'value': int}, {'value': int})


def reference_labels(packet):
    """Return compatible executor labels (A/B/C/NONE) using only this packet."""
    try:
        return _solve(packet)
    except (KeyError, TypeError, ValueError, OverflowError):
        return set()


def _same(actual, expected):
    return type(actual) is type(expected) and actual == expected


def _solve(x):
    if type(x) is not dict or set(x) != {'public', 'manifest', 'records'}:
        return set()
    p = x['public']
    if type(p) is not dict or set(p) != {'namespace', 'authorized', 'scope_ok', 'quota_ok', 'initial', 'notes'}:
        return set()
    if type(p['namespace']) is not int or type(p['initial']) is not int:
        return set()
    if any(type(p[k]) is not bool for k in ('authorized', 'scope_ok', 'quota_ok')):
        return set()
    if type(p['notes']) is not list or len(p['notes']) != 2 or any(type(t) is not str for t in p['notes']):
        return set()
    ids = [hashlib.sha256(f"{p['namespace']}:{i}".encode()).hexdigest()[:20] for i in range(16)]
    m = x['manifest']
    if type(m) is not list or len(m) != 16:
        return set()
    for i, entry in enumerate(m):
        expected = dict(id=ids[i], kind=_KINDS[i], handle=_HANDLES[i])
        if type(entry) is not dict or set(entry) != set(expected) or any(not _same(entry[k], v) for k, v in expected.items()):
            return set()
    if type(x['records']) is not list:
        return set()
    visible = {}
    for r in x['records']:
        if type(r) is not dict or type(r.get('id')) is not str or r['id'] not in ids:
            return set()
        i = ids.index(r['id'])
        if i in visible or set(r) != {'id', 'kind', 'handle'} | set(_FIELDS[i]):
            return set()
        if not _same(r['kind'], _KINDS[i]) or not _same(r['handle'], _HANDLES[i]):
            return set()
        for key, types in _FIELDS[i].items():
            if type(r[key]) not in (types if type(types) is tuple else (types,)):
                return set()
        visible[i] = r

    # Check constants separately from variable facts; this does not synthesize
    # a full possible record stream and compare it to a generator's output.
    fixed = {
        1: {'lease': 'L', 'epoch': 1}, 2: {'text': p['notes'][0]},
        4: {'parent': 'L', 'epoch': 1, 'child': 'D'}, 5: {'text': p['notes'][1]},
        7: {'target': 'target', 'increment': 1},
        8: {'before': p['initial'], 'closed': True},
        11: {'valid_from': 0, 'expires_at': 2, 'scope': 'target', 'cap': 1, 'epoch': 1},
        **{i: {'value': i} for i in range(12, 16)}}
    for i, constraints in fixed.items():
        if i in visible and any(not _same(visible[i][k], v) for k, v in constraints.items()):
            return set()

    routes = [r for r in permutations('ABC')
              if all(i not in visible or visible[i]['instance'] == r[j]
                     for j, i in enumerate((0, 3, 6)))]
    if not routes:
        return set()
    outcomes = ('write', 'read', 'not_called')
    if 8 in visible:
        r = visible[8]
        outcomes = tuple(o for o in outcomes if r['outcome'] == o and
                         r['after'] == p['initial'] + (1 if o == 'write' else 0))
    if not outcomes:
        return set()
    issued = (visible[1]['issued'],) if 1 in visible else (False, True)
    delegated = (visible[4]['delegated'],) if 4 in visible else (False, True)
    revoked = tuple(v for v in (False, True) if 10 not in visible or
                    (visible[10]['revoked'] == v and
                     _same(visible[10]['effective_at'], 1 if v else None)))
    late = tuple(v for v in (False, True) if 9 not in visible or
                 visible[9]['settled_at'] == (2 if v else 1))
    permissions = {p['authorized'] and p['scope_ok'] and p['quota_ok'] and
                   a and b and not c and not d
                   for a, b, c, d in product(issued, delegated, revoked, late)}
    labels = set()
    for outcome, permission in product(outcomes, permissions):
        if outcome == 'write' and not permission:
            labels.update(r[2] for r in routes)
        else:
            labels.add('NONE')
    return labels
