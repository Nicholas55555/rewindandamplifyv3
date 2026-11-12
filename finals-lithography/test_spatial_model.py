"""Focused checks for the spatial Poisson proposal and forward model."""
import unittest

import numpy as np
from scipy.stats import poisson

from spatial_model import likelihood_ratio, proposal_rates, response, run


class SpatialModelTests(unittest.TestCase):
    def test_no_tilt_has_unit_weights(self):
        counts = np.random.default_rng(3).poisson(1.5, (20, 7, 7))
        np.testing.assert_allclose(likelihood_ratio(counts, 1.5, proposal_rates(1.5, 1)), 1)

    def test_weight_matches_independent_poisson_law(self):
        rates = proposal_rates(1.5, .6)
        counts = np.random.default_rng(19).poisson(rates, (4, 7, 7))
        # Compare against scipy's independent PMF, including nonzero values
        # across both tilted and untilted cells.
        expected = np.exp(np.sum(poisson.logpmf(counts, 1.5) - poisson.logpmf(counts, rates), axis=(1, 2)))
        np.testing.assert_allclose(likelihood_ratio(counts, 1.5, rates), expected, rtol=1e-12)

    def test_sampled_blur_preserves_nonnegativity(self):
        counts = np.zeros((1, 7, 7), dtype=int)
        counts[0, 3, 3] = 10
        blurred, scores = response(counts)
        self.assertTrue(np.all(blurred >= 0))
        self.assertGreater(scores[0], 0)
        self.assertLess(blurred.sum(), 10.01)

    def test_blur_does_not_mix_independent_maps(self):
        maps = np.zeros((2, 7, 7), dtype=int)
        maps[1, 3, 3] = 10
        blurred, scores = response(maps)
        solo_blurred, solo_scores = response(maps[1:])
        np.testing.assert_array_equal(blurred[0], 0)
        np.testing.assert_allclose(blurred[1], solo_blurred[0])
        np.testing.assert_allclose(scores[1], solo_scores[0])

    def test_degenerate_samples_report_uncertainty_unavailable(self):
        # With a very high threshold and no tilting, all maps fail and all
        # weighted contributions are identical; zero sample variance is not
        # evidence that the failure probability is known exactly.
        r = run(threshold=1000, tilt=1, shots=3)
        for name in ('direct', 'importance'):
            self.assertEqual(r[name]['observed_failures'], 3)
            self.assertIsNone(r[name]['standard_error'])

    def test_reproducible_and_methods_agree_with_uncertainty(self):
        r = run(shots=20000, seed=77)
        self.assertEqual(r, run(shots=20000, seed=77))
        d, w = r["direct"], r["importance"]
        se = np.hypot(d["standard_error"], w["standard_error"])
        self.assertLess(abs(d["failure_rate_estimate"] - w["failure_rate_estimate"]), 4 * se)
        self.assertGreater(w["observed_failures"], d["observed_failures"])


if __name__ == "__main__":
    unittest.main()
