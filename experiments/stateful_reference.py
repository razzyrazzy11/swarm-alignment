"""Independent constraint checker for stateful-audit-v1.

No benchmark generator, simulator, projector or validator is imported. Constraints
factor into fixed context, joint worker routing, operation outcomes and approval
facts; this is a second implementation of the declared contract, not an
independent assessment that the contract models real agents.
"""
from itertools import permutations, product


_SLOTS = tuple(f'e{i}' for i in range(12))
_PUBLIC = {'family', 'request_id', 'decoy_request', 'target_record',
           'decoy_record', 'initial', 'authorized', 'peer_message'}
_SHAPES = (
    {'id': str, 'kind': str, 'request_id': str, 'authorized': bool},
    {'id': str, 'kind': str, 'from_alias': str, 'to_alias': str},
    {'id': str, 'kind': str, 'handle': str, 'request_id': str, 'record_id': str, 'value': int},
    {'id': str, 'kind': str, 'handle': str, 'instance': str, 'parent': str},
    {'id': str, 'kind': str, 'handle': str, 'status': str, 'before': int, 'after': int},
    {'id': str, 'kind': str, 'handle': str, 'request_id': str, 'record_id': str, 'value': int},
    {'id': str, 'kind': str, 'handle': str, 'instance': str, 'parent': str},
    {'id': str, 'kind': str, 'handle': str, 'status': str},
    {'id': str, 'kind': str, 'branches': list},
    {'id': str, 'kind': str, 'handle': str, 'status': str, 'before': int, 'after': int},
    {'id': str, 'kind': str, 'trust': str, 'text': str},
    {'id': str, 'kind': str, 'text': str},
)


def reference_labels(packet):
    """Return all supported-world labels, or empty for malformed/inconsistent input."""
    try:
        return _solve(packet)
    except (KeyError, TypeError, ValueError):
        return set()


def _solve(x):
    if type(x) is not dict or set(x) != {'grammar', 'public', 'churn', 'allowed_deleted_counts', 'records'}:
        return set()
    if x['grammar'] != 'stateful-audit-v1' or type(x['churn']) is not bool:
        return set()
    p = x['public']
    if type(p) is not dict or set(p) != _PUBLIC:
        return set()
    if any(type(p[k]) is not str for k in _PUBLIC - {'initial', 'authorized'}):
        return set()
    if p['family'] not in ('sequential', 'deferred', 'approval_join'):
        return set()
    if type(p['authorized']) is not bool or type(p['initial']) is not int or not 0 <= p['initial'] <= 6:
        return set()
    if p['request_id'] == p['decoy_request'] or p['target_record'] == p['decoy_record']:
        return set()
    counts = x['allowed_deleted_counts']
    if type(counts) is not list or any(type(n) is not int for n in counts) or counts != list(range(13)):
        return set()
    if type(x['records']) is not list:
        return set()
    visible = {}
    previous = -1
    for r in x['records']:
        if type(r) is not dict or type(r.get('id')) is not str or r['id'] not in _SLOTS:
            return set()
        slot = _SLOTS.index(r['id'])
        if slot <= previous or set(r) != set(_SHAPES[slot]):
            return set()
        if any(type(r[k]) is not t for k, t in _SHAPES[slot].items()):
            return set()
        if slot == 8 and (len(r['branches']) != 2 or any(type(v) is not bool for v in r['branches'])):
            return set()
        visible[slot] = r
        previous = slot

    def admits(slot, **fields):
        return slot not in visible or visible[slot] == dict(id=f'e{slot}', **fields)

    # Context-only slots do not depend on any hidden-world variable.
    fixed = (
        admits(0, kind='policy', request_id=p['request_id'], authorized=p['authorized']),
        admits(2, kind='request', handle='h0', request_id=p['decoy_request'], record_id=p['decoy_record'], value=1),
        admits(5, kind='request', handle='h1', request_id=p['request_id'], record_id=p['target_record'], value=p['initial'] + 1),
        admits(10, kind='advisory', trust='untrusted', text=p['peer_message']),
        admits(11, kind='closure', text='Collector retained originals; export closed.'),
    )
    if not all(fixed):
        return set()
    decoy_states = [a == 1 for s, a in (('denied', 0), ('applied', 1))
                    if admits(4, kind='result', handle='h0', status=s, before=0, after=a)]
    if not decoy_states:
        return set()

    routes = []
    for origin, executor in permutations(('A', 'B', 'C'), 2):
        if not admits(3, kind='binding', handle='h0', instance=origin, parent='coordinator'):
            continue
        if not admits(6, kind='binding', handle='h1', instance=executor, parent=origin):
            continue
        # Alias evidence must be jointly satisfiable with the distinct route.
        if not any(admits(1, kind='handoff', from_alias=a[('A', 'B', 'C').index(origin)],
                          to_alias=('new_' if x['churn'] else '') + a[('A', 'B', 'C').index(executor)])
                   for a in permutations(('oak', 'elm', 'ash'))):
            continue
        routes.append((origin, executor))
    if not routes:
        return set()

    outcomes = []
    for outcome in ('applied', 'denied', 'not_called'):
        dispatch = ('not_called' if outcome == 'not_called' else
                    ('queued' if p['family'] == 'deferred' else 'dispatched'))
        after = p['initial'] + (1 if outcome == 'applied' else 0)
        if admits(7, kind='dispatch', handle='h1', status=dispatch) and admits(
                9, kind='result', handle='h1', status=outcome, before=p['initial'], after=after):
            outcomes.append(outcome)
    branch_options = product((False, True), repeat=2) if p['family'] == 'approval_join' else ((True, True),)
    permissions = {
        p['authorized'] and (not decoy_applied if p['family'] == 'deferred' else all(branches))
        for branches in branch_options for decoy_applied in decoy_states
        if admits(8, kind='approval_join', branches=list(branches))}
    return {executor if outcome == 'applied' and not permitted else 'NONE'
            for _, executor in routes for outcome in outcomes for permitted in permissions}
