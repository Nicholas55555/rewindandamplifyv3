"""Independent checks of register order, conditioning, recursion and noise."""
import unittest
import numpy as np
from qiskit import QuantumCircuit
from model import (one_bin, prepare, amplify, statevector, vector_branches,
                   channel_branches, event_recursion, selection, trace_distance,
                   density_branches, readout_mix, noisy_density)
from dilation_feasibility import kraus_superoperator


class MultibinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Independent toy: known Bernoulli outcome; click applies a complex
        # unitary to memory. Exact history probabilities are analytic.
        unitary = np.eye(8, dtype=complex)
        unitary[:2, :2] = np.array([[1, 1j], [1j, 1]])/np.sqrt(2)
        cls.ops = [np.sqrt(.7)*np.eye(8), np.sqrt(.3)*unitary]
        cls.maps = [kraus_superoperator(k[None], 8) for k in cls.ops]
        v = np.vstack(cls.ops)
        cls.prep, cls.flags = prepare(one_bin(v), 3, 0)
        cls.branches = vector_branches(statevector(cls.prep), 3, 0)

    def test_all_eight_branches_and_conditional_states(self):
        reference = channel_branches(self.maps, 3)
        for bits, rho in self.branches.items():
            expected_p = .3**sum(bits)*.7**(3-sum(bits))
            self.assertAlmostEqual(np.trace(rho).real, expected_p, places=10)
            np.testing.assert_allclose(rho, reference[bits], atol=1e-10)
        self.assertAlmostEqual(sum(np.trace(x).real for x in self.branches.values()), 1, places=10)

    def test_full_amplification_preserves_every_conditional_history(self):
        for event in ["last", "all"]:
            result = vector_branches(statevector(amplify(self.prep, self.flags, event)), 3, 0)
            p, target = selection(self.branches, event)
            pa, after = selection(result, event)
            self.assertAlmostEqual(pa, np.sin(3*np.arcsin(np.sqrt(p)))**2, places=10)
            self.assertLess(trace_distance(target, after), 1e-10)
            for bits, rho in result.items():
                before = self.branches[bits]
                self.assertLess(trace_distance(rho/np.trace(rho), before/np.trace(before)), 1e-9)

    def test_event_recursion_equals_history_sum(self):
        for event in ["last", "all"]:
            p, rho = selection(self.branches, event)
            np.testing.assert_allclose(event_recursion(self.maps, 3, event), p*rho, atol=1e-10)

    def test_density_partial_trace_preserves_complex_coherence(self):
        vector = np.zeros(32, complex)
        vector[8] = 1/np.sqrt(3); vector[9] = 1j/np.sqrt(3); vector[16] = 1/np.sqrt(3)
        full = np.outer(vector, vector.conj())
        a = density_branches(full, 1)
        b = vector_branches(vector, 1, 1)
        for bit in [0, 1]: np.testing.assert_allclose(a[bit], b[(bit,)], atol=1e-15)
        self.assertAlmostEqual(a[1][0, 1].imag, -1/3)

    def test_readout_conditions_mixed_true_flags(self):
        no = np.diag([.9, 0.]); yes = np.diag([0., .1])
        mixed = readout_mix([no, yes], .1, .2)
        np.testing.assert_allclose(mixed[1], np.diag([.09, .08]))
        np.testing.assert_allclose(sum(mixed), no+yes)
        self.assertAlmostEqual(np.trace(mixed[1]), .17)

    def test_exact_density_depolarization_definition(self):
        qc = QuantumCircuit(2); qc.cx(0, 1)
        np.testing.assert_allclose(noisy_density(qc, 1.), np.eye(4)/4, atol=1e-12)

    def test_memory_guards(self):
        with self.assertRaisesRegex(ValueError, "capped"): noisy_density(QuantumCircuit(9), 0)
        with self.assertRaisesRegex(ValueError, "capped"): prepare(QuantumCircuit(8), 4, 4)
        with self.assertRaises(ValueError): readout_mix([np.eye(2), np.eye(2)], -.1, .2)


if __name__ == "__main__": unittest.main()
