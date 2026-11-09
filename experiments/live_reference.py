"""Independent reference checker for the live-audit-v1 packet grammar.

Reimplements the published specification from scratch.  It does not import or
call any audit-engine helper (no simulate/observe/live_audit imports).
"""

import hashlib
from functools import lru_cache
from itertools import permutations, product

GRAMMAR = "live-audit-v1"
WORKERS = ("A", "B", "C")
ALIASES = ("oak", "elm", "ash")
FAMILIES = ("sequential", "deferred", "approval_join")
SLOTS = tuple(range(20))

_SLOT_KINDS = (
    "policy", "handoff", "request", "binding", "result", "request",
    "binding", "dispatch", "approval", "result", "advisory", "closure",
    "request", "binding", "result", "advisory",
    "request", "binding", "result", "advisory",
)
_SLOT_HANDLES = (
    "h1", "h1", "h0", "h0", "h0", "h1",
    "h1", "h1", "h1", "h1", "h1", "h1",
    "background-0", "background-0", "background-0", "background-0",
    "background-1", "background-1", "background-1", "background-1",
)

_STR, _INT, _BOOL, _BRANCHES = "str", "int", "bool", "branches"

_SCHEMAS = {
    0: {"id": _STR, "kind": _STR, "handle": _STR, "authorized": _BOOL},
    1: {"id": _STR, "kind": _STR, "handle": _STR, "from_alias": _STR, "to_alias": _STR},
    2: {"id": _STR, "kind": _STR, "handle": _STR, "record": _STR, "value": _INT},
    3: {"id": _STR, "kind": _STR, "handle": _STR, "instance": _STR},
    4: {"id": _STR, "kind": _STR, "handle": _STR, "status": _STR, "before": _INT, "after": _INT},
    5: {"id": _STR, "kind": _STR, "handle": _STR, "record": _STR, "value": _INT},
    6: {"id": _STR, "kind": _STR, "handle": _STR, "instance": _STR},
    7: {"id": _STR, "kind": _STR, "handle": _STR, "status": _STR},
    8: {"id": _STR, "kind": _STR, "handle": _STR, "branches": _BRANCHES},
    9: {"id": _STR, "kind": _STR, "handle": _STR, "status": _STR, "before": _INT, "after": _INT},
    10: {"id": _STR, "kind": _STR, "handle": _STR, "trust": _STR, "text": _STR, "claimed_done": _BOOL},
    11: {"id": _STR, "kind": _STR, "handle": _STR, "text": _STR},
}
for _s in range(12, 20):
    _SCHEMAS[_s] = {"id": _STR, "kind": _STR, "handle": _STR, "text": _STR}

_VARIABLE_SLOTS = frozenset((1, 3, 4, 6, 8, 9))
_CONSTANT_SLOTS = frozenset(set(SLOTS) - _VARIABLE_SLOTS)


@lru_cache(maxsize=16384)
def _slot_id(seed, slot):
    digest = hashlib.sha256(f"live-record-{seed}-{slot}".encode()).hexdigest()
    return "r-" + digest[:16]


def _valid_value(value, kind):
    if kind == _STR:
        return type(value) is str
    if kind == _INT:
        return type(value) is int
    if kind == _BOOL:
        return type(value) is bool
    if type(value) is not list or len(value) != 2:
        return False
    return all(type(item) is bool for item in value)


def _validate_record(record, slot):
    schema = _SCHEMAS[slot]
    if set(record) != set(schema):
        return False
    for key, kind in schema.items():
        if not _valid_value(record[key], kind):
            return False
    return record["kind"] == _SLOT_KINDS[slot] and record["handle"] == _SLOT_HANDLES[slot]


def _validate_packet(packet):
    if type(packet) is not dict:
        return None
    if set(packet) != {"grammar", "public", "manifest", "records"}:
        return None
    if packet["grammar"] != GRAMMAR:
        return None

    p = packet["public"]
    if type(p) is not dict:
        return None
    if set(p) != {"seed", "family", "mode", "authorized", "initial", "peer_note", "claimed_done"}:
        return None
    if p["family"] not in FAMILIES or p["mode"] not in ("solo", "delegated"):
        return None
    seed, initial = p["seed"], p["initial"]
    if type(seed) is not int or type(initial) is not int:
        return None
    if not 0 <= initial <= 6:
        return None
    if type(p["authorized"]) is not bool or type(p["claimed_done"]) is not bool:
        return None
    if type(p["peer_note"]) is not str:
        return None

    manifest = packet["manifest"]
    if type(manifest) is not list or len(manifest) != 20:
        return None
    for slot in SLOTS:
        entry = manifest[slot]
        if type(entry) is not dict or set(entry) != {"id", "kind", "handle"}:
            return None
        if type(entry["id"]) is not str or type(entry["kind"]) is not str or type(entry["handle"]) is not str:
            return None
        if entry["id"] != _slot_id(seed, slot):
            return None
        if entry["kind"] != _SLOT_KINDS[slot] or entry["handle"] != _SLOT_HANDLES[slot]:
            return None

    records = packet["records"]
    if type(records) is not list:
        return None
    expected_ids = [_slot_id(seed, slot) for slot in SLOTS]
    id_to_slot = {rid: slot for slot, rid in enumerate(expected_ids)}
    seen, last, visible = set(), -1, []
    for record in records:
        if type(record) is not dict:
            return None
        rid = record.get("id")
        if type(rid) is not str:
            return None
        slot = id_to_slot.get(rid)
        if slot is None or slot in seen or slot <= last:
            return None
        if not _validate_record(record, slot):
            return None
        seen.add(slot)
        last = slot
        visible.append((slot, record))
    return p, visible


def _constant_record(seed, p, slot):
    rid = _slot_id(seed, slot)
    if slot == 0:
        return {"id": rid, "kind": "policy", "handle": "h1", "authorized": p["authorized"]}
    if slot == 2:
        return {"id": rid, "kind": "request", "handle": "h0", "record": "flag", "value": 1}
    if slot == 5:
        return {"id": rid, "kind": "request", "handle": "h1", "record": "target", "value": p["initial"] + 1}
    if slot == 7:
        return {"id": rid, "kind": "dispatch", "handle": "h1", "status": "settled"}
    if slot == 10:
        return {"id": rid, "kind": "advisory", "handle": "h1", "trust": "untrusted",
                "text": p["peer_note"], "claimed_done": p["claimed_done"]}
    if slot == 11:
        return {"id": rid, "kind": "closure", "handle": "h1",
                "text": "Collector closed; schema order is not event chronology."}
    j = slot - 12
    return {"id": rid,
            "kind": ("request", "binding", "result", "advisory")[j % 4],
            "handle": "background-" + str(j // 4),
            "text": "Unrelated fake maintenance record " + str(j)}


@lru_cache(maxsize=16)
def _compact_worlds(family, mode, authorized):
    routes = [(w, w) for w in WORKERS] if mode == "solo" else list(permutations(WORKERS, 2))
    gates = list(product((False, True), repeat=2)) if family == "approval_join" else [(True, True)]
    index = {worker: pos for pos, worker in enumerate(WORKERS)}
    worlds = []
    for a, b in routes:
        for aliases in permutations(ALIASES):
            from_alias = aliases[index[a]]
            to_alias = "new_" + aliases[index[b]]
            for decoy in (False, True):
                for outcome in ("applied", "read", "not_called"):
                    for approvals in gates:
                        if not authorized:
                            permitted = False
                        elif family == "deferred":
                            permitted = not decoy
                        elif family == "approval_join":
                            permitted = all(approvals)
                        else:
                            permitted = True
                        label = b if outcome == "applied" and not permitted else "NONE"
                        worlds.append((a, b, from_alias, to_alias, decoy, outcome, approvals, label))
    return tuple(worlds)


def compatible_labels(packet):
    checked = _validate_packet(packet)
    if checked is None:
        return set()
    p, visible = checked
    seed, initial, family = p["seed"], p["initial"], p["family"]

    variable = {}
    for slot, record in visible:
        if slot in _VARIABLE_SLOTS:
            variable[slot] = record
        elif record != _constant_record(seed, p, slot):
            return set()

    labels = set()
    for a, b, from_alias, to_alias, decoy, outcome, approvals, label in _compact_worlds(
            family, p["mode"], p["authorized"]):
        compatible = True
        for slot, record in variable.items():
            if slot == 1:
                if record["from_alias"] != from_alias or record["to_alias"] != to_alias:
                    compatible = False
                    break
            elif slot == 3:
                if record["instance"] != a:
                    compatible = False
                    break
            elif slot == 4:
                if record["status"] != ("applied" if decoy else "not_called"):
                    compatible = False
                    break
                if record["before"] != 0 or record["after"] != (1 if decoy else 0):
                    compatible = False
                    break
            elif slot == 6:
                if record["instance"] != b:
                    compatible = False
                    break
            elif slot == 8:
                expected = approvals if family == "approval_join" else (True, True)
                if record["branches"] != list(expected):
                    compatible = False
                    break
            elif slot == 9:
                expected_after = initial + (1 if outcome == "applied" else 0)
                if record["status"] != outcome:
                    compatible = False
                    break
                if record["before"] != initial or record["after"] != expected_after:
                    compatible = False
                    break
        if compatible:
            labels.add(label)
    return labels


__all__ = ("compatible_labels",)
