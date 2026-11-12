import itertools
import math
import unittest
import numpy as np
from fusion_check import P_QUBIT, log_likelihood, sample_pair


class FusionTests(unittest.TestCase):
    def test_joint_forward_against_enumeration(self):
        observations = np.array([[1, 0], [1, 1], [0, 0], [0, 1]])
        probs = np.array([[.3, .7], [.35, .65]])
        switch = .1
        total = 0.
        for hidden in itertools.product([0, 1], repeat=len(observations)):
            term = .5
            for i, (state, row) in enumerate(zip(hidden, observations)):
                if i:
                    term *= switch if state != hidden[i-1] else 1-switch
                for bit, p in zip(row, probs[:, state]):
                    term *= p if bit else 1-p
            total += term
        self.assertAlmostEqual(log_likelihood(observations, probs, switch), math.log(total), places=12)

    def test_no_information_sensor_cancels_from_likelihood_ratio(self):
        y = np.array([[0, 1], [1, 1], [1, 0], [1, 1], [0, 0]])
        neutral = np.array([[.5, .5]])
        joint = np.concatenate((P_QUBIT[None, :], neutral), axis=0)
        lr = lambda data, p: log_likelihood(data, p, .02) - log_likelihood(data, p, .5)
        self.assertAlmostEqual(lr(y, joint), lr(y[:, :1], P_QUBIT[None, :]), places=12)

    def test_iid_joint_keeps_shared_state_correlation(self):
        probabilities = np.array([[.3, .7], [.35, .65]])
        both_one = np.array([[1, 1]])
        expected = .5*(.3*.35 + .7*.65)
        self.assertAlmostEqual(math.exp(log_likelihood(both_one, probabilities, .5)), expected)
        self.assertNotAlmostEqual(expected, .25)

    def test_reproducible_pair(self):
        x = sample_pair(np.random.default_rng(5), .02, 30)
        y = sample_pair(np.random.default_rng(5), .02, 30)
        for first, second in zip(x, y):
            np.testing.assert_array_equal(first, second)


if __name__ == "__main__":
    unittest.main()
