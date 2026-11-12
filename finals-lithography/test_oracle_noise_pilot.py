"""Unit checks for scoring the noisy threshold-oracle pilot."""
import importlib.util
import unittest

if importlib.util.find_spec('qiskit_aer'):
    from oracle_noise_pilot import conditional_score, wilson


@unittest.skipUnless(importlib.util.find_spec('qiskit_aer'), 'optional qiskit-aer not installed')
class NoisyPilotScoreTests(unittest.TestCase):
    def test_wilson_interval_includes_boundary_and_is_not_degenerate(self):
        a, b = wilson(0, 100)
        self.assertEqual(a, 0)
        self.assertGreater(b, 0)
        a, b = wilson(100, 100)
        self.assertLess(a, 1)
        self.assertEqual(b, 1)

    def test_conditioning_uses_qiskit_little_endian_counts(self):
        counts = {'000': 1, '001': 4, '010': 4, '100': 4, '111': 7}
        result = conditional_score(counts, 3, .8)
        self.assertEqual(result['accepted'], 13)
        self.assertEqual(result['accepted_counts']['100'], 4)  # site 0 is rightmost
        self.assertAlmostEqual(result['conditional_tv'], 0.0)
        self.assertLessEqual(result['conditional_tv_95_percent_finite_shot_bound'][0], result['conditional_tv'])
        self.assertGreaterEqual(result['conditional_tv_95_percent_finite_shot_bound'][1], result['conditional_tv'])


if __name__ == '__main__':
    unittest.main()
