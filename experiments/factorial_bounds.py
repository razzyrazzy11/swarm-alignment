"""Logical bounds for paired binary scores with unobserved outcomes.

An observed terminal INVALID must arrive as integer 0. None represents only an
unobserved outcome; this module cannot establish that provenance. These are
finite-benchmark logical bounds, not a confidence interval or an imputation.
No missing-at-random, monotonicity, or deterministic-decoding assumption is used.
"""

from collections.abc import Mapping
import math


def compute_binary_pair_bounds(pairs):
    """Bound mean(procedure - direct) over every supplied source.

    Accept a nonempty list/tuple of mappings containing unique strict-integer
    source_seed and direct/procedure values that are strict integers 0/1 or None.
    Additional per-pair metadata is ignored. The caller must enforce its planned
    sample size (192 for the original study). Exact integer numerators describe
    the attainable lattice; the reported interval is its convex hull.
    """
    if not isinstance(pairs, (list, tuple)):
        raise TypeError("pairs must be a list or tuple")
    if not pairs:
        raise ValueError("pairs must not be empty")
    seen = set()
    lower = upper = unknown = complete = p_only = d_only = neither = total = 0
    for pair in pairs:
        if not isinstance(pair, Mapping):
            raise TypeError("each pair must be a mapping")
        if not {"source_seed", "direct", "procedure"}.issubset(pair):
            raise ValueError("pair lacks required fields")
        seed = pair["source_seed"]
        if type(seed) is not int:
            raise TypeError("source_seed must be a strict integer")
        if seed in seen:
            raise ValueError("duplicate source_seed")
        seen.add(seed)
        d, p = pair["direct"], pair["procedure"]
        for value in (d, p):
            if value is not None and type(value) is not int:
                raise TypeError("outcome must be a strict integer or None")
            if value is not None and value not in (0, 1):
                raise ValueError("observed outcome must be 0 or 1")
        unknown += int(d is None) + int(p is None)
        if d is not None and p is not None:
            complete += 1
            total += p - d
            lower += p - d
            upper += p - d
        elif p is not None:
            p_only += 1
            lower += p - 1
            upper += p
        elif d is not None:
            d_only += 1
            lower -= d
            upper += 1 - d
        else:
            neither += 1
            lower -= 1
            upper += 1
    n = len(pairs)
    return dict(n=n, estimate_lower=lower / n, estimate_upper=upper / n,
                width=(upper - lower) / n, lower_numerator=lower,
                upper_numerator=upper, denominator=n, unknown_cells=unknown,
                complete_pairs=complete, procedure_only=p_only,
                direct_only=d_only, neither=neither,
                complete_pair_sum_difference=total, complete_pair_count=complete,
                lattice_step=1 / n)


def validate_binary_pair_bounds(pairs, result):
    """Recompute the contract and reject missing, extra, or tampered fields.

    Returns None on success. Numeric types are part of the JSON-facing contract:
    bool and float replacements of integer metadata are rejected.
    """
    expected = compute_binary_pair_bounds(pairs)
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping")
    if set(result) != set(expected):
        raise ValueError("result fields differ from bounds contract")
    for key, value in expected.items():
        actual = result[key]
        if type(actual) is not type(value):
            raise TypeError("incorrect bounds field type: " + key)
        if type(actual) is float and not math.isfinite(actual):
            raise ValueError("nonfinite bounds field: " + key)
        if actual != value:
            raise ValueError("bounds field does not match input pairs: " + key)
