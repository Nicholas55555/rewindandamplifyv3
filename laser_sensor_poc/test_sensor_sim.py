import itertools
import math
import unittest
import numpy as np
from sensor_sim import click_prob, hmm_log_likelihood, sample_record


class SensorTests(unittest.TestCase):
    def test_ry_born_rule(self):
        np.testing.assert_allclose(click_prob(np.array([0, np.pi/2, np.pi])), [0, .5, 1], atol=1e-14)
        self.assertAlmostEqual(float(np.mean(click_prob(np.pi/2 + np.array([-.8, .8])))), .5)

    def test_iid_is_matched_binary_bernoulli(self):
        for seq in itertools.product([0, 1], repeat=4):
            self.assertAlmostEqual(hmm_log_likelihood(seq, .5), 4*math.log(.5), places=12)

    def test_forward_against_direct_sum(self):
        seq = [1, 1, 0, 1]
        switch = .13
        p = click_prob(np.pi/2 + np.array([-.8, .8]))
        likelihood = 0.0
        for hidden in itertools.product([0, 1], repeat=len(seq)):
            term = .5
            for i, (h, bit) in enumerate(zip(hidden, seq)):
                if i:
                    term *= switch if h != hidden[i-1] else 1-switch
                term *= p[h] if bit else 1-p[h]
            likelihood += term
        self.assertAlmostEqual(hmm_log_likelihood(seq, switch, delta=.8), math.log(likelihood), places=12)

    def test_qiskit_statevector_when_installed(self):
        try:
            from qiskit import QuantumCircuit
            from qiskit.quantum_info import Statevector
        except ImportError:
            self.skipTest("Qiskit not installed in this interpreter")
        for theta in [0, .37, np.pi/2, 2.4, np.pi]:
            circuit = QuantumCircuit(1)
            circuit.ry(theta, 0)
            p_one = Statevector.from_instruction(circuit).probabilities()[1]
            self.assertAlmostEqual(float(click_prob(theta)), float(p_one), places=12)

    def test_reproducible(self):
        a = sample_record(np.random.default_rng(123), 100, .02)
        b = sample_record(np.random.default_rng(123), 100, .02)
        for first, second in zip(a, b):
            np.testing.assert_array_equal(first, second)


if __name__ == "__main__":
    unittest.main()
