import math
import unittest
import numpy as np
from robustness_check import apply_bit_flips, pulse_area_probability


class RobustnessTests(unittest.TestCase):
    def test_binary_channel_endpoints(self):
        y = np.array([0, 1, 1, 0, 1])
        np.testing.assert_array_equal(apply_bit_flips(np.random.default_rng(1), y, 0), y)
        np.testing.assert_array_equal(apply_bit_flips(np.random.default_rng(1), y, 1), 1-y)

    def test_pulse_area_degeneracy(self):
        original = pulse_area_probability(math.pi/2, 1)
        for factor in [.25, .5, 1, 2, 4]:
            self.assertAlmostEqual(pulse_area_probability((math.pi/2)*factor, 1/factor),
                                   original, places=14)

    def test_invalid_channel(self):
        with self.assertRaises(ValueError):
            apply_bit_flips(np.random.default_rng(1), [1], 1.1)

    def test_seeded_channel_flip_rates_by_input(self):
        y = np.tile([0, 1], 100000)
        actual = apply_bit_flips(np.random.default_rng(829), y, .25)
        self.assertAlmostEqual(float(actual[y == 0].mean()), .25, delta=.005)
        self.assertAlmostEqual(float(actual[y == 1].mean()), .75, delta=.005)


if __name__ == "__main__":
    unittest.main()
