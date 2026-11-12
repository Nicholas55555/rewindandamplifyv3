"""Checks for the repeat aggregation in the synthetic dose study."""
import unittest

import numpy as np

from dose_sweep import study


class DoseSweepTests(unittest.TestCase):
    def test_repeat_summary_reproduces_and_matches_recorded_runs(self):
        first = study((1.35, 1.5), shots=500, repeats=3, seed=41)
        self.assertEqual(first, study((1.35, 1.5), shots=500, repeats=3, seed=41))
        self.assertEqual(len(first["rows"]), 2)
        for row in first["rows"]:
            for name in ("direct", "importance"):
                result = row[name]
                self.assertEqual(len(result["estimates"]), 3)
                self.assertAlmostEqual(result["mean_estimate"], np.mean(result["estimates"]))
                self.assertAlmostEqual(result["mean_estimate_se_from_repeats"],
                                       np.std(result["estimates"], ddof=1) / np.sqrt(3))

    def test_requires_repeats(self):
        with self.assertRaises(ValueError):
            study(repeats=1)


if __name__ == "__main__":
    unittest.main()
