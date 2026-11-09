"""Finite three-worker lease audit: actual effects and packet-only evidence."""
import copy
import hashlib
import itertools
import json
import random
from functools import lru_cache


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _valid_public(p):
    return (type(p) is dict and set(p) == {"namespace", "authorized", "scope_ok", "quota_ok", "initial", "notes"}
            and type(p["namespace"]) is int and type(p["initial"]) is int
            and all(type(p[k]) is bool for k in ("authorized", "scope_ok", "quota_ok"))
            and type(p["notes"]) is list and len(p["notes"]) == 2 and all(type(x) is str for x in p["notes"]))


def _valid_world(w):
    return (type(w) is dict and set(w) == {"route", "issued", "delegated", "revoked", "late", "outcome"}
            and type(w["route"]) is list and all(type(x) is str for x in w["route"]) and sorted(w["route"]) == ["A", "B", "C"]
            and all(type(w[k]) is bool for k in ("issued", "delegated", "revoked", "late"))
            and w["outcome"] in ("write", "read", "not_called"))


def worlds(p):
    if not _valid_public(p):
        raise ValueError("invalid public context")
    return [{"route": list(route), **dict(zip(("issued", "delegated", "revoked", "late"), flags)), "outcome": outcome}
            for route in itertools.permutations("ABC") for flags in itertools.product((False, True), repeat=4)
            for outcome in ("write", "read", "not_called")]


def records(p, w):
    if not _valid_public(p) or not _valid_world(w):
        raise ValueError("invalid public context/world")
    rows = [
        ("binding", "h0", {"instance": w["route"][0]}),
        ("grant", "h0", {"issued": w["issued"], "lease": "L", "epoch": 1}),
        ("advisory", "h1", {"text": p["notes"][0]}),
        ("binding", "h1", {"instance": w["route"][1]}),
        ("delegation", "h1", {"delegated": w["delegated"], "parent": "L", "epoch": 1, "child": "D"}),
        ("advisory", "h2", {"text": p["notes"][1]}),
        ("binding", "h2", {"instance": w["route"][2]}),
        ("request", "h2", {"target": "target", "increment": 1}),
        ("result", "h2", {"outcome": w["outcome"], "before": p["initial"], "after": p["initial"] + int(w["outcome"] == "write"), "closed": True}),
        ("clock", "h2", {"settled_at": 2 if w["late"] else 1}),
        ("revocation", "L", {"revoked": w["revoked"], "effective_at": 1 if w["revoked"] else None}),
        ("lease", "L", {"valid_from": 0, "expires_at": 2, "scope": "target", "cap": 1, "epoch": 1}),
        *[("background", f"b{i}", {"value": 12 + i}) for i in range(4)],
    ]
    return [{"id": hashlib.sha256(f'{p["namespace"]}:{i}'.encode()).hexdigest()[:20], "kind": kind, "handle": handle, **payload}
            for i, (kind, handle, payload) in enumerate(rows)]


def simulate(p, w):
    recs = records(p, w)
    permitted = all(p[k] for k in ("authorized", "scope_ok", "quota_ok")) and w["issued"] and w["delegated"] and not w["revoked"] and not w["late"]
    return {"records": recs, "state": {"target": recs[8]["after"]}, "permitted": permitted,
            "label": w["route"][2] if w["outcome"] == "write" and not permitted else "NONE"}


@lru_cache(maxsize=256)
def _universe(public_json):
    p = json.loads(public_json)
    return [(w, {r["id"]: canonical(r) for r in records(p, w)}, simulate(p, w)["label"]) for w in worlds(p)]


def _compatible(packet):
    try:
        if type(packet) is not dict or set(packet) != {"public", "manifest", "records"} or not _valid_public(packet["public"]):
            return []
        p = packet["public"]
        universe = _universe(canonical(p))
        expected = [{k: r[k] for k in ("id", "kind", "handle")} for r in records(p, universe[0][0])]
        if type(packet["manifest"]) is not list or any(type(r) is not dict or set(r) != {"id", "kind", "handle"}
                or any(type(r[k]) is not str for k in ("id", "kind", "handle")) for r in packet["manifest"]):
            return []
        if canonical(packet["manifest"]) != canonical(expected) or type(packet["records"]) is not list:
            return []
        observed = {}
        for r in packet["records"]:
            if type(r) is not dict or type(r.get("id")) is not str or r["id"] in observed:
                return []
            observed[r["id"]] = canonical(r)
        return [(w, rs, label) for w, rs, label in universe if all(rs.get(rid) == value for rid, value in observed.items())]
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return []


def compatible_worlds(packet):
    return copy.deepcopy([w for w, _, _ in _compatible(packet)])


def labels(packet):
    return {label for _, _, label in _compatible(packet)}


def _missing(packet, budget):
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    if not _compatible(packet):
        return []
    present = {r["id"] for r in packet["records"]}
    return [r for r in packet["manifest"] if r["id"] not in present]


def metadata_selector(packet, budget=2):
    missing = _missing(packet, budget)
    priority = [("result", "h2"), ("binding", "h2"), ("clock", "h2"), ("revocation", "L"), ("grant", "h0"), ("delegation", "h1")]
    def rank(r):
        pair = (r["kind"], r["handle"])
        return (priority.index(pair) if pair in priority else len(priority), r["id"])
    return [r["id"] for r in sorted(missing, key=rank)[:budget]]


def contract_selector(packet, budget=2):
    missing = sorted(r["id"] for r in _missing(packet, budget))
    compatible = _compatible(packet)
    if not compatible or not missing or not budget:
        return []
    best = None
    for ids in itertools.combinations(missing, min(budget, len(missing))):
        partitions = {}
        for _, rs, label in compatible:
            key = tuple(rs[rid] for rid in ids)
            count, labs = partitions.setdefault(key, [0, set()])
            partitions[key][0] = count + 1
            labs.add(label)
        score = sum(n * len(labs) for n, labs in partitions.values())
        candidate = (score, ids)
        if best is None or candidate < best:
            best = candidate
    return list(best[1])


def _packet(p, full, slots):
    return {"public": copy.deepcopy(p), "manifest": [{k: r[k] for k in ("id", "kind", "handle")} for r in full],
            "records": [copy.deepcopy(full[i]) for i in sorted(slots)]}


def _rng(p, domain):
    return random.Random(digest({"namespace": p["namespace"], "domain": domain}))


def views(p, w):
    full = records(p, w)
    critical = [1, 4, 6, 8, 9, 10]
    output = []
    def add(name, slots, added=()):
        packet = _packet(p, full, slots)
        restored = [r for r in full if r["id"] in added]
        output.append({"view": name, "packet": packet, "compatible_labels": sorted(labels(packet)), "added_ids": list(added),
                       "restored_bytes": len(canonical(restored).encode()) if added else 0})
    add("sufficient", critical)
    add("identity_loss", set(range(16)) - {0, 3, 6})
    random_missing = set(_rng(p, "random_loss").sample(range(16), 4))
    selective_missing = set(_rng(p, "selective_loss_critical").sample(critical, 2) + _rng(p, "selective_loss_other").sample([i for i in range(16) if i not in critical], 2))
    for loss, missing in (("random", random_missing), ("selective", selective_missing)):
        visible = set(range(16)) - missing
        packet = _packet(p, full, visible)
        add(loss + "_none", visible)
        random_ids = [full[i]["id"] for i in _rng(p, loss + "_restore").sample(sorted(missing), 2)]
        for policy, ids in (("random", random_ids), ("metadata", metadata_selector(packet)), ("contract", contract_selector(packet))):
            restored_slots = {i for i in missing if full[i]["id"] in ids}
            add(loss + "_" + policy, visible | restored_slots, ids)
    return output
