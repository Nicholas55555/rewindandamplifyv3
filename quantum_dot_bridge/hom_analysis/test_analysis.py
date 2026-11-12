import unittest
from pathlib import Path

import numpy as np

from analysis import (CYCLE_NS, REFERENCE_INDICES, area, area_ratio, correct_visibility,
                      extract, load_histograms, monte_carlo, peak_masks, point_metrics,
                      register_offset)


def fixture(center, reference, background=0):
    peaks = {}
    for k in (0,) + REFERENCE_INDICES:
        peaks[str(k)] = {"count": center if k == 0 else reference,
                         "window_bins": 80, "background_bins": 80,
                         "background_count": background}
    return {"peaks": peaks}


class AnalysisTests(unittest.TestCase):
    def test_known_visibility_different_exposures(self):
        co, cross = fixture(200, 4000), fixture(1500, 3000)
        self.assertAlmostEqual(point_metrics(co, cross)["raw_visibility"], .9)

    def test_arbitrary_acquisition_scale_cancels(self):
        a = point_metrics(fixture(200, 4000), fixture(1500, 3000))
        b = point_metrics(fixture(1400, 28000), fixture(4500, 9000))
        self.assertEqual(a, b)

    def test_zero_and_complete_raw_interference(self):
        self.assertEqual(point_metrics(fixture(500, 1000), fixture(500, 1000))["raw_visibility"], 0)
        self.assertEqual(point_metrics(fixture(0, 1000), fixture(500, 1000))["raw_visibility"], 1)

    def test_balanced_no_multiphoton_correction_identity(self):
        np.testing.assert_allclose(correct_visibility(np.array([0., .2, 1.]), .5, 0.), [0., .2, 1.])

    def test_correction_invariant_R_exchange(self):
        self.assertAlmostEqual(float(correct_visibility(.8, .514, .016)), float(correct_visibility(.8, .486, .016)))

    def test_no_clipping_corrected_values(self):
        self.assertGreater(float(correct_visibility(1.0)), 1.)

    def test_calibration_rejects_unphysical(self):
        for r, g in [(0, .01), (1, .01), (.5, -1), (.5, 1)]:
            with self.assertRaises(ValueError):
                correct_visibility(.8, r, g)

    def test_equal_disjoint_peak_and_background_windows(self):
        t = np.arange(-2500, 2500) * .05
        for k in (0,) + REFERENCE_INDICES:
            p, b, center = peak_masks(t, k * CYCLE_NS - .25, 2.)
            self.assertEqual(p.sum(), 80)
            self.assertEqual(b.sum(), 80)
            self.assertFalse(np.any(p & b))
            self.assertLessEqual(abs(center - (k * CYCLE_NS - .25)), .02500001)

    def test_side_registration_ignores_arbitrary_center(self):
        t = np.arange(-2500, 2500) * .05
        c = np.zeros_like(t)
        for k in REFERENCE_INDICES:
            c += 1000 * np.exp(-((t - k*CYCLE_NS + .25) / .2) ** 2)
        offset = register_offset(t, c)
        c[np.abs(t) < 1] = 1000000
        self.assertAlmostEqual(offset, -.25)
        self.assertEqual(register_offset(t, c), offset)

    def test_constant_background_recovers_known_area_ratio(self):
        ex = fixture(120, 1020, background=20)
        self.assertAlmostEqual(area_ratio(ex, subtract_background=True), .1)
        self.assertEqual(area(ex["peaks"]["0"], True), 100)

    def test_independent_known_peak_extraction(self):
        t = np.arange(-2500, 2500) * .05
        c = np.full(t.shape, 2, dtype=int)
        for k in (0,) + REFERENCE_INDICES:
            idx = np.argmin(abs(t - (k*CYCLE_NS - .25)))
            c[idx] += 100 if k == 0 else 1000
        out = extract({"time_ns": t, "counts": c})
        self.assertAlmostEqual(area_ratio(out, subtract_background=True), .1)

    def test_shared_calibration_induces_covariance(self):
        pair = (fixture(10000, 100000), fixture(50000, 100000))
        out = monte_carlo([pair, pair], samples=10000, seed=12)
        cov = np.array(out["calibration_only_covariance"])
        self.assertGreater(cov[0, 1], 0)
        self.assertAlmostEqual(cov[0, 0], cov[0, 1])
        self.assertAlmostEqual(cov[1, 1], cov[0, 1])

    def test_count_uncertainty_matches_delta_method(self):
        c, r, x, s = 10000, 100000, 50000, 100000
        pair = (fixture(c, r), fixture(x, s))
        out = monte_carlo([pair, pair], samples=80000, seed=13)
        ratio = c/r/(x/s)
        derivative = float(correct_visibility(1.) - correct_visibility(0.))
        expected = derivative*ratio*np.sqrt(1/c + 1/(4*r) + 1/x + 1/(4*s))
        self.assertLess(abs(out["cases"][0]["count_only_sd"]/expected-1), .02)

    def test_raw_sources_pinned_and_expected(self):
        _, records = load_histograms(Path(__file__).resolve().parent.parent / "reference_hom")
        self.assertEqual(len(records), 6)
        for record in records:
            self.assertEqual(record["counts"].shape, (5000,))


if __name__ == "__main__":
    unittest.main()
