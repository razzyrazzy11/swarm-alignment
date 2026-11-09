"""Synthetic tests only: no study files or model outputs are read."""

import itertools
import json
import unittest

from experiments.factorial_bounds import (
    compute_binary_pair_bounds as bounds,
    validate_binary_pair_bounds as validate,
)


def pair(seed, d, p):
    return dict(source_seed=seed, direct=d, procedure=p)


class BinaryPairBoundsTests(unittest.TestCase):
    def test_each_observation_pattern(self):
        for d, p, lo, hi, field in (
            (0, 1, 1, 1, "complete_pairs"),
            (None, 1, 0, 1, "procedure_only"),
            (1, None, -1, 0, "direct_only"),
            (None, None, -1, 1, "neither"),
        ):
            with self.subTest(d=d, p=p):
                r = bounds([pair(1, d, p)])
                self.assertEqual((r["estimate_lower"], r["estimate_upper"]), (lo, hi))
                self.assertEqual(r[field], 1)
                validate([pair(1, d, p)], r)

    def test_complete_case_counterexample(self):
        records = [pair(1, 0, 1), pair(2, None, 0)]
        r = bounds(records)
        self.assertEqual((r["estimate_lower"], r["estimate_upper"]), (0, 0.5))
        self.assertEqual(r["complete_pair_sum_difference"], 1)
        self.assertEqual(r["complete_pair_count"], 1)
        self.assertEqual(r["unknown_cells"], 1)

    def test_all_missing_all_observed_and_known_zero(self):
        r = bounds([pair(i, None, None) for i in range(3)])
        self.assertEqual((r["estimate_lower"], r["estimate_upper"], r["width"]), (-1, 1, 2))
        observed = [pair(1, 0, 1), pair(2, 1, 0), pair(3, 0, 0)]
        r = bounds(observed)
        self.assertEqual((r["lower_numerator"], r["upper_numerator"], r["unknown_cells"]), (0, 0, 0))
        self.assertEqual(bounds([pair(1, 0, 0)])["width"], 0)
        self.assertEqual(bounds([pair(1, None, 0)])["width"], 1)

    def test_exhaustive_binary_completions_extrema_and_lattice(self):
        patterns = list(itertools.product((0, 1, None), repeat=2))
        for n in (1, 2, 3):
            for cells in itertools.product(patterns, repeat=n):
                records = [pair(i, d, p) for i, (d, p) in enumerate(cells)]
                r = bounds(records)
                possibilities = [{p - d for d in ((0, 1) if d0 is None else (d0,))
                                  for p in ((0, 1) if p0 is None else (p0,))}
                                 for d0, p0 in cells]
                sums = {sum(values) for values in itertools.product(*possibilities)}
                self.assertEqual(min(sums), r["lower_numerator"])
                self.assertEqual(max(sums), r["upper_numerator"])
                self.assertEqual(sums, set(range(min(sums), max(sums) + 1)))
                self.assertEqual(r["width"], r["unknown_cells"] / n)
                self.assertEqual(r["lattice_step"], 1 / n)
                validate(records, r)

    def test_invalid_inputs_and_duplicate_identity_rejected(self):
        invalid = [[], {}, iter([]), [None], [{}], [pair(True, 0, 1)],
                   [pair(1.0, 0, 1)], [pair(1, 0, 1), pair(1, 1, 0)]]
        for value in (True, False, 0.0, 1.0, float("nan"), float("inf"), "0", [], {}, -1, 2):
            invalid.extend(([pair(1, value, 0)], [pair(1, 0, value)]))
        for records in invalid:
            with self.subTest(records=records), self.assertRaises((TypeError, ValueError)):
                bounds(records)

    def test_order_metadata_json_and_tampering(self):
        records = [pair(1, 0, 1), pair(2, None, 0), pair(3, 1, None), pair(4, None, None)]
        records[0]["stratum"] = "ignored metadata"
        r = bounds(records)
        self.assertEqual({key: r[key] for key in (
            "n", "lower_numerator", "upper_numerator", "denominator",
            "unknown_cells", "complete_pairs", "procedure_only", "direct_only", "neither",
            "complete_pair_sum_difference", "complete_pair_count")},
            dict(n=4, lower_numerator=-2, upper_numerator=2, denominator=4,
                 unknown_cells=4, complete_pairs=1, procedure_only=1,
                 direct_only=1, neither=1, complete_pair_sum_difference=1,
                 complete_pair_count=1))
        self.assertEqual(r["width"], 1.0)  # Half of the eight cells are unknown.
        self.assertEqual(r, bounds(list(reversed(records))))
        validate(records, json.loads(json.dumps(r, allow_nan=False)))
        for key, value in r.items():
            changed = dict(r)
            changed[key] = value + 1
            with self.subTest(key=key), self.assertRaises((TypeError, ValueError)):
                validate(records, changed)
        for key, replacement in (("n", True), ("n", 4.0), ("width", float("nan")),
                                 ("width", float("inf")), ("width", 1)):
            with self.subTest(key=key, replacement=replacement), self.assertRaises((TypeError, ValueError)):
                validate(records, dict(r, **{key: replacement}))
        missing = dict(r)
        del missing["n"]
        for changed in (missing, dict(r, extra=1), None):
            with self.assertRaises((TypeError, ValueError)):
                validate(records, changed)


if __name__ == "__main__":
    unittest.main()
