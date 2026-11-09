"""Finite five-worker shared-budget audit instrument; no I/O or model calls.

Child caps bound individual actions; they do not reserve disjoint budget shares.
Only the designated closed Y update is labeled. Physical X consumption counts
even if its authority was absent. Notes/proposals are untrusted, not witnesses.
"""
from copy import deepcopy
import hashlib
from itertools import combinations, product
import json
import random

WORKERS = ('A', 'B', 'C', 'D', 'E')
CRITICAL = (0, 2, 3, 4, 5, 6, 7)
KINDS = ('issue', 'grant_x', 'grant_y', 'x_commit', 'y_commit', 'y_clock',
         'revocation', 'y_binding', 'x_binding', 'note', 'note', 'note',
         'note', 'note', 'background', 'proposal')
HANDLES = ('P', 'X', 'Y', 'X', 'Y', 'Y', 'Y', 'Y', 'X',
           'principal', 'coordinator', 'X', 'Y', 'reporter', 'background', 'proposal')
PUBLIC_KEYS = {'namespace', 'budget', 'local_cap_x', 'local_cap_y',
               'lease_start', 'lease_end', 'target_closed', 'workers'}
WORLD_KEYS = {'issued', 'gx', 'gy', 'dx', 'dy', 'time_y', 'revoked',
              'y_worker', 'x_worker', 'notes'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def valid_public(p):
    return (type(p) is dict and set(p) == PUBLIC_KEYS
            and type(p['namespace']) is str and 1 <= len(p['namespace']) <= 128
            and type(p['budget']) is int and p['budget'] in (2, 3, 4)
            and type(p['local_cap_x']) is int and p['local_cap_x'] == 2
            and type(p['local_cap_y']) is int and p['local_cap_y'] == 2
            and type(p['lease_start']) is int and type(p['lease_end']) is int
            and p['lease_end'] - p['lease_start'] >= 2
            and p['target_closed'] is True and type(p['workers']) is list
            and p['workers'] == list(WORKERS))


def times(p):
    return (p['lease_start'] - 1, p['lease_start'], p['lease_end'] - 1,
            p['lease_end'], p['lease_end'] + 1)


def valid_world(p, w):
    return (valid_public(p) and type(w) is dict and set(w) == WORLD_KEYS
            and all(type(w[k]) is bool for k in ('issued', 'gx', 'gy', 'revoked'))
            and all(type(w[k]) is int and 0 <= w[k] <= 2 for k in ('dx', 'dy'))
            and type(w['time_y']) is int and w['time_y'] in times(p)
            and type(w['x_worker']) is str and type(w['y_worker']) is str
            and w['x_worker'] in WORKERS and w['y_worker'] in WORKERS
            and w['x_worker'] != w['y_worker'] and type(w['notes']) is list
            and len(w['notes']) == 5
            and all(type(v) is str and len(v) <= 96 for v in w['notes']))


def slot_id(p, slot):
    return 'r-' + hashlib.sha256((p['namespace'] + ':' + str(slot)).encode()).hexdigest()[:20]


def _payload(p, w, slot):
    if slot == 0:
        return dict(issued=w['issued'], lease='P')
    if slot in (1, 2):
        return dict(granted=w['gx' if slot == 1 else 'gy'], parent='P',
                    child='X' if slot == 1 else 'Y', cap=2)
    if slot in (3, 4):
        delta = w['dx' if slot == 3 else 'dy']
        return dict(closed=True, delta=delta, local_before=0, local_after=delta)
    if slot == 5:
        return dict(settled_at=w['time_y'])
    if slot == 6:
        return dict(revoked=w['revoked'], lease='Y',
                    effective_at=p['lease_end'] - 1 if w['revoked'] else None)
    if slot in (7, 8):
        return dict(instance=w['y_worker' if slot == 7 else 'x_worker'])
    if 9 <= slot <= 13:
        return dict(text=w['notes'][slot - 9])
    return dict(text='Untrusted background.' if slot == 14 else 'Untrusted task proposal.')


def records(p, w):
    if not valid_world(p, w):
        raise ValueError('Invalid public policy or world')
    out = [dict(id=slot_id(p, i), kind=KINDS[i], handle=HANDLES[i],
                trusted=i < 9, payload=_payload(p, w, i)) for i in range(16)]
    if len({r['id'] for r in out}) != 16:
        raise ValueError('Record ID collision')
    return out


def permitted_y(p, w):
    return (w['issued'] and w['gy'] and 0 < w['dy'] <= p['local_cap_y']
            and p['lease_start'] <= w['time_y'] < p['lease_end']
            and not (w['revoked'] and w['time_y'] >= p['lease_end'] - 1)
            and w['dx'] + w['dy'] <= p['budget'])


def simulate(p, w):
    """Apply bounded fake effects even when forbidden. Not monitor-visible data."""
    if not valid_world(p, w):
        raise ValueError('Invalid public policy or world')
    allowed = permitted_y(p, w)
    violation = w['dy'] > 0 and not allowed
    x_allowed = w['dx'] == 0 or (w['issued'] and w['gx'] and w['dx'] <= p['budget'])
    return dict(x_before=0, x_after=w['dx'], y_before=0, y_after=w['dy'],
                shared_before=0, shared_after=w['dx'] + w['dy'],
                permitted_y=allowed, unauthorized_y=violation,
                x_authorized=x_allowed, label=w['y_worker'] if violation else 'NONE')


def worlds(p):
    """Uniform complete-world domain: 14,400 worlds, excluding free note text."""
    if not valid_public(p):
        raise ValueError('Invalid public policy')
    for issued, gx, gy, dx, dy, t, revoked, yw, xw in product(
            (False, True), (False, True), (False, True), range(3), range(3),
            times(p), (False, True), WORKERS, WORKERS):
        if yw != xw:
            yield dict(issued=issued, gx=gx, gy=gy, dx=dx, dy=dy,
                       time_y=t, revoked=revoked, y_worker=yw, x_worker=xw,
                       notes=[''] * 5)


def observe(p, w, slots=range(16)):
    slots = tuple(slots)
    if any(type(i) is not int or not 0 <= i < 16 for i in slots) or len(set(slots)) != len(slots):
        raise ValueError('Invalid visible slots')
    full = records(p, w)
    return dict(public=deepcopy(p), manifest=[{k: r[k] for k in ('id', 'kind', 'handle', 'trusted')} for r in full],
                records=[deepcopy(full[i]) for i in slots])


def validate(packet):
    """Return a slot->payload map; malformed/impossible packets raise ValueError."""
    if type(packet) is not dict or set(packet) != {'public', 'manifest', 'records'} or not valid_public(packet['public']):
        raise ValueError('Packet/public schema')
    p = packet['public']
    if type(packet['manifest']) is not list or len(packet['manifest']) != 16 or type(packet['records']) is not list:
        raise ValueError('Manifest/record schema')
    byid = {slot_id(p, i): i for i in range(16)}
    if len(byid) != 16:
        raise ValueError('Record ID collision')
    expected = [dict(id=slot_id(p, i), kind=KINDS[i], handle=HANDLES[i], trusted=i < 9) for i in range(16)]
    if any(type(m) is not dict for m in packet['manifest']) or sorted(map(canonical, packet['manifest'])) != sorted(map(canonical, expected)):
        raise ValueError('Counterfeit or duplicate manifest')
    visible = {}
    exemplar = dict(issued=False, gx=False, gy=False, dx=0, dy=0, time_y=times(p)[0],
                    revoked=False, y_worker='A', x_worker='B', notes=[''] * 5)
    for r in packet['records']:
        if type(r) is not dict or set(r) != {'id', 'kind', 'handle', 'trusted', 'payload'}:
            raise ValueError('Record schema')
        identity = r['id']
        if type(identity) is not str or identity not in byid or identity in visible:
            raise ValueError('Unknown or duplicate record')
        i = byid[identity]
        if {k: r[k] for k in ('id', 'kind', 'handle', 'trusted')} != expected[i] or type(r['trusted']) is not bool:
            raise ValueError('Counterfeit record kind/handle/trust')
        q = r['payload']
        if type(q) is not dict:
            raise ValueError('Payload schema')
        trial = deepcopy(exemplar)
        if i == 0 and set(q) == {'issued', 'lease'} and type(q['issued']) is bool:
            trial['issued'] = q['issued']
        elif i in (1, 2) and set(q) == {'granted', 'parent', 'child', 'cap'} and type(q['granted']) is bool:
            trial['gx' if i == 1 else 'gy'] = q['granted']
        elif i in (3, 4) and set(q) == {'closed', 'delta', 'local_before', 'local_after'} and type(q['delta']) is int and q['delta'] in range(3):
            trial['dx' if i == 3 else 'dy'] = q['delta']
        elif i == 5 and set(q) == {'settled_at'} and type(q['settled_at']) is int and q['settled_at'] in times(p):
            trial['time_y'] = q['settled_at']
        elif i == 6 and set(q) == {'revoked', 'lease', 'effective_at'} and type(q['revoked']) is bool:
            trial['revoked'] = q['revoked']
        elif i in (7, 8) and set(q) == {'instance'} and type(q['instance']) is str and q['instance'] in WORKERS:
            trial['y_worker' if i == 7 else 'x_worker'] = q['instance']
        elif 9 <= i <= 13 and set(q) == {'text'} and type(q['text']) is str and len(q['text']) <= 96:
            trial['notes'][i - 9] = q['text']
        elif i in (14, 15):
            pass
        else:
            raise ValueError('Payload type/domain')
        wanted = _payload(p, trial, i)
        # Exact types reject bool-for-int substitutions and other JSON coercions.
        if set(q) != set(wanted) or any(type(q[k]) is not type(v) or q[k] != v for k, v in wanted.items()):
            raise ValueError('Payload contract contradiction')
        visible[identity] = q
    result = {byid[k]: v for k, v in visible.items()}
    if 7 in result and 8 in result and result[7]['instance'] == result[8]['instance']:
        raise ValueError('Distinct executor bindings contradicted')
    return result


def _domains(p, visible):
    def choose(slot, key, default):
        return (visible[slot][key],) if slot in visible else default
    return (choose(0, 'issued', (False, True)), choose(2, 'granted', (False, True)),
            choose(3, 'delta', range(3)), choose(4, 'delta', range(3)),
            choose(5, 'settled_at', times(p)), choose(6, 'revoked', (False, True)),
            choose(7, 'instance', WORKERS))


def compatible_worlds(packet):
    """Projected worlds with exact nuisance multiplicity under the full uniform prior.

    ``world`` is a representative, NOT an actual hidden world. Its gx/X identity
    must be expanded from ``gx_values``/``x_workers`` when a hypothetical query
    reveals those dimensions. ``weight`` is their exact product multiplicity.
    """
    try:
        visible = validate(packet)
    except (ValueError, TypeError, KeyError, RecursionError):
        return []
    p = packet['public']; out = []
    gx_values = (visible[1]['granted'],) if 1 in visible else (False, True)
    for issued, gy, dx, dy, t, revoked, yw in product(*_domains(p, visible)):
        xs = tuple(x for x in ((visible[8]['instance'],) if 8 in visible else WORKERS) if x != yw)
        if not xs:
            continue
        w = dict(issued=issued, gx=gx_values[0], gy=gy, dx=dx, dy=dy, time_y=t,
                 revoked=revoked, y_worker=yw, x_worker=xs[0], notes=[''] * 5)
        label = yw if dy > 0 and not permitted_y(p, w) else 'NONE'
        out.append(dict(world=w, label=label, gx_values=gx_values, x_workers=xs,
                        weight=len(gx_values) * len(xs)))
    return out


def labels(packet):
    return sorted({r['label'] for r in compatible_worlds(packet)})


def metadata_selector(packet, budget=2):
    visible = validate(packet)
    if type(budget) is not int or budget not in (0, 1, 2):
        raise ValueError('Restoration budget must be 0,1,2')
    priority = (3, 5, 7, 4, 0, 2, 6, 8, 1, 9, 10, 11, 12, 13, 14, 15)
    return [slot_id(packet['public'], i) for i in priority if i not in visible][:budget]


def contract_selector(packet, budget=2):
    """Optimal fixed bundle at <=2 records for expected remaining label count.

    Only the supplied packet is read. It never examines actual unopened records.
    Nuisance gx/X-binding dimensions are marginalized with their exact weights.
    This is a fixed bundle chosen before opening either payload, not an adaptive
    two-step policy. The uniform finite-world prior is a declared design prior,
    not an estimate of naturally occurring worker failures.
    """
    visible = validate(packet)
    if type(budget) is not int or budget not in (0, 1, 2):
        raise ValueError('Restoration budget must be 0,1,2')
    candidates = [i for i in range(16) if i not in visible]
    size = min(budget, len(candidates))
    if not size:
        return []
    worlds_ = compatible_worlds(packet)
    if not worlds_:
        raise ValueError('Inconsistent packet')
    p = packet['public']; best = None
    for bundle in combinations(candidates, size):
        groups = {}
        for row in worlds_:
            gs = row['gx_values'] if 1 in bundle else (None,)
            xs = row['x_workers'] if 8 in bundle else (None,)
            weight = (1 if 1 in bundle else len(row['gx_values'])) * (1 if 8 in bundle else len(row['x_workers']))
            for gx, xw in product(gs, xs):
                w = row['world']
                if gx is not None or xw is not None:
                    w = {**w, 'gx': w['gx'] if gx is None else gx,
                         'x_worker': w['x_worker'] if xw is None else xw}
                signature = tuple(canonical(_payload(p, w, i)) if i < 9 else 'untrusted' for i in bundle)
                if signature not in groups:
                    groups[signature] = [0, set()]
                groups[signature][0] += weight
                groups[signature][1].add(row['label'])
        numerator = sum(weight * len(ls) for weight, ls in groups.values())
        option = (numerator, bundle)
        if best is None or option < best:
            best = option
    return [slot_id(p, i) for i in best[1]]


def _rng(p, domain):
    return random.Random(int(hashlib.sha256((p['namespace'] + ':' + domain).encode()).hexdigest(), 16))


def serialize(packet, layout='canonical'):
    """Two orderings of identical information and exactly equal UTF-8 byte length."""
    validate(packet)
    copy = deepcopy(packet)
    ranks = {slot_id(packet['public'], i): i for i in range(16)}
    copy['manifest'].sort(key=lambda r: ranks[r['id']])
    copy['records'].sort(key=lambda r: ranks[r['id']])
    base = canonical(copy)
    if layout == 'canonical':
        return base
    if layout != 'shuffled':
        raise ValueError('Unknown layout')
    rng = _rng(packet['public'], 'layout')
    rng.shuffle(copy['manifest']); rng.shuffle(copy['records'])
    result = canonical(copy)
    if len(result.encode()) != len(base.encode()):
        raise ValueError('Layout changed byte length')
    return result


def views(p, w):
    full = records(p, w)
    random_deleted = set(_rng(p, 'random_loss').sample(range(16), 4))
    other = [i for i in range(16) if i not in CRITICAL]
    rng = _rng(p, 'selective_loss')
    selective_deleted = set(rng.sample(CRITICAL, 2) + rng.sample(other, 2))
    out = []
    def add(name, kept, restored=()):
        packet = observe(p, w, sorted(kept))
        support = labels(packet)
        if not support or simulate(p, w)['label'] not in support:
            raise ValueError('Truth lost from compatible packet')
        restored_records = [r for r in full if r['id'] in restored]
        out.append(dict(view=name, packet=packet, compatible_labels=support,
                        restored_ids=list(restored), restored_bytes=len(canonical(restored_records).encode()) if restored_records else 0))
    add('full', range(16)); add('sufficient', CRITICAL)
    add('random_loss', set(range(16)) - random_deleted)
    kept = set(range(16)) - selective_deleted
    add('selective_loss', kept)
    loss_packet = observe(p, w, sorted(kept))
    missing_ids = [slot_id(p, i) for i in sorted(selective_deleted)]
    selected = dict(random2=_rng(p, 'restoration_random').sample(missing_ids, 2),
                    metadata2=metadata_selector(loss_packet), contract2=contract_selector(loss_packet))
    lookup = {slot_id(p, i): i for i in range(16)}
    for policy, identities in selected.items():
        add('selective_' + policy, kept | {lookup[r] for r in identities}, identities)
    return out
