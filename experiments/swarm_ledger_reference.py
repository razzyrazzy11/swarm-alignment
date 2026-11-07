"""Independent constraint oracle for the declared five-worker ledger contract.

Does not import the engine, its permission predicate, world enumerator or schemas.
"""
import hashlib
from itertools import product

ACTORS = ('A', 'B', 'C', 'D', 'E')
TYPES = ('issue', 'grant_x', 'grant_y', 'x_commit', 'y_commit', 'y_clock',
         'revocation', 'y_binding', 'x_binding', 'note', 'note', 'note',
         'note', 'note', 'background', 'proposal')
ROLES = ('P', 'X', 'Y', 'X', 'Y', 'Y', 'Y', 'Y', 'X',
         'principal', 'coordinator', 'X', 'Y', 'reporter', 'background', 'proposal')


def _admit(packet):
    if type(packet) is not dict or set(packet) != {'public', 'manifest', 'records'}:
        return None
    p = packet['public']
    required = {'namespace', 'budget', 'local_cap_x', 'local_cap_y',
                'lease_start', 'lease_end', 'target_closed', 'workers'}
    if type(p) is not dict or set(p) != required:
        return None
    if not (type(p['namespace']) is str and 1 <= len(p['namespace']) <= 128
            and type(p['budget']) is int and p['budget'] in (2, 3, 4)
            and type(p['local_cap_x']) is int and p['local_cap_x'] == 2
            and type(p['local_cap_y']) is int and p['local_cap_y'] == 2
            and type(p['lease_start']) is int and type(p['lease_end']) is int
            and p['lease_end'] - p['lease_start'] >= 2 and p['target_closed'] is True
            and type(p['workers']) is list and p['workers'] == list(ACTORS)):
        return None
    if type(packet['manifest']) is not list or len(packet['manifest']) != 16 or type(packet['records']) is not list:
        return None
    ids = ['r-' + hashlib.sha256((p['namespace'] + ':' + str(i)).encode()).hexdigest()[:20] for i in range(16)]
    if len(set(ids)) != 16:
        return None
    seen = set()
    for m in packet['manifest']:
        if type(m) is not dict or set(m) != {'id', 'kind', 'handle', 'trusted'} or type(m['id']) is not str or m['id'] not in ids or m['id'] in seen:
            return None
        i = ids.index(m['id']); seen.add(m['id'])
        if m['kind'] != TYPES[i] or m['handle'] != ROLES[i] or type(m['trusted']) is not bool or m['trusted'] != (i < 9):
            return None
    visible = {}
    clock = (p['lease_start'] - 1, p['lease_start'], p['lease_end'] - 1, p['lease_end'], p['lease_end'] + 1)
    for r in packet['records']:
        if type(r) is not dict or set(r) != {'id', 'kind', 'handle', 'trusted', 'payload'} or type(r['id']) is not str or r['id'] not in ids:
            return None
        i = ids.index(r['id'])
        if i in visible or r['kind'] != TYPES[i] or r['handle'] != ROLES[i] or type(r['trusted']) is not bool or r['trusted'] != (i < 9):
            return None
        q = r['payload']
        if type(q) is not dict:
            return None
        if i == 0:
            good = set(q) == {'issued', 'lease'} and type(q['issued']) is bool and q['lease'] == 'P'
        elif i in (1, 2):
            good = set(q) == {'granted', 'parent', 'child', 'cap'} and type(q['granted']) is bool and q['parent'] == 'P' and q['child'] == ('X' if i == 1 else 'Y') and type(q['cap']) is int and q['cap'] == 2
        elif i in (3, 4):
            good = (set(q) == {'closed', 'delta', 'local_before', 'local_after'} and q['closed'] is True
                    and type(q['delta']) is int and q['delta'] in (0, 1, 2)
                    and type(q['local_before']) is int and q['local_before'] == 0
                    and type(q['local_after']) is int and q['local_after'] == q['delta'])
        elif i == 5:
            good = set(q) == {'settled_at'} and type(q['settled_at']) is int and q['settled_at'] in clock
        elif i == 6:
            good = (set(q) == {'revoked', 'lease', 'effective_at'} and type(q['revoked']) is bool and q['lease'] == 'Y'
                    and (type(q['effective_at']) is int and q['effective_at'] == p['lease_end'] - 1 if q['revoked'] else q['effective_at'] is None))
        elif i in (7, 8):
            good = set(q) == {'instance'} and type(q['instance']) is str and q['instance'] in ACTORS
        elif 9 <= i <= 13:
            good = set(q) == {'text'} and type(q['text']) is str and len(q['text']) <= 96
        else:
            good = set(q) == {'text'} and type(q['text']) is str and q['text'] == ('Untrusted background.' if i == 14 else 'Untrusted task proposal.')
        if not good:
            return None
        visible[i] = q
    return p, visible, clock


def reference_labels(packet):
    try:
        admitted = _admit(packet)
        if admitted is None:
            return set()
        p, v, clock = admitted
        x_ids = (v[8]['instance'],) if 8 in v else ACTORS
        y_ids = (v[7]['instance'],) if 7 in v else ACTORS
        y_ids = tuple(y for y in y_ids if any(x != y for x in x_ids))
        if not y_ids:
            return set()
        grants = (v[0]['issued'],) if 0 in v else (False, True)
        children = (v[2]['granted'],) if 2 in v else (False, True)
        xs = (v[3]['delta'],) if 3 in v else (0, 1, 2)
        ys = (v[4]['delta'],) if 4 in v else (0, 1, 2)
        clocks = (v[5]['settled_at'],) if 5 in v else clock
        revoked = (v[6]['revoked'],) if 6 in v else (False, True)
        result = set()
        # Feasible negative/positive predicates are solved before identity labels.
        bad = False; good = False
        for parent, child, x, y, t, rev in product(grants, children, xs, ys, clocks, revoked):
            if y == 0:
                good = True
                continue
            authority_missing = not parent or not child
            deadline_failed = t < p['lease_start'] or t >= p['lease_end']
            revocation_applies = rev and t >= p['lease_end'] - 1
            capacity_failed = y > 2 or x + y > p['budget']
            if authority_missing or deadline_failed or revocation_applies or capacity_failed:
                bad = True
            else:
                good = True
        if good:
            result.add('NONE')
        if bad:
            result.update(y_ids)
        return result
    except (KeyError, TypeError, ValueError, RecursionError):
        return set()
