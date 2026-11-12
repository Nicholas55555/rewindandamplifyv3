import unittest
from dataclasses import replace

import numpy as np
from scipy.integrate import quad

from physical_model import (Parameters, photon_modes, gram_embedding, true_instrument,
    observed_instrument, effect, apply, choi, source_isometries, branch_states,
    probabilities, classical_matrices, gap_superoperator, bosonic_instrument)
from circuits import frozen_pair_circuit, sequential_circuit, circuit_branches, validate_circuit


class PhysicalTests(unittest.TestCase):
    def test_complex_gram_against_temporal_integral(self):
        modes, info = gram_embedding([-1., 1., 0., 2.])
        for i, a in enumerate(info['frequencies_over_gamma']):
            for j, b in enumerate(info['frequencies_over_gamma']):
                direct = quad(lambda t: np.exp(-t)*np.cos((b-a)*t), 0, np.inf)[0]
                direct -= 1j*quad(lambda t: np.exp(-t)*np.sin((b-a)*t), 0, np.inf)[0]
                self.assertAlmostEqual(abs(np.vdot(modes[:, i], modes[:, j])-direct), 0., places=9)

    def test_source_completeness(self):
        for dephase in [0., .25, 1.]:
            for control in [0., 1., -1.]:
                source, _ = source_isometries(Parameters(gap_dephasing=dephase), control)
                check = sum(v.reshape(-1, 2).conj().T @ v.reshape(-1, 2) for v in source)
                np.testing.assert_allclose(check, np.eye(2), atol=1e-12)

    def test_instrument_CP_and_trace(self):
        for dephase in [0., .25, 1.]:
            p = Parameters(gap_dephasing=dephase, mode_overlap=.85)
            for control in [0., 1., -1.]:
                maps, _ = observed_instrument(p, control)
                np.testing.assert_allclose(effect(sum(maps)), np.eye(2), atol=1e-12)
                for m in maps:
                    c = choi(m)
                    np.testing.assert_allclose(c, c.conj().T, atol=1e-12)
                    self.assertGreater(np.linalg.eigvalsh(c).min(), -1e-12)

    def test_bosonic_full_instrument_not_only_probability(self):
        for d in [0., .25, 1.]:
            for control in [0., 1., -1.]:
                p = Parameters(gap_dephasing=d)
                np.testing.assert_allclose(true_instrument(p, control)[0], bosonic_instrument(p, control), atol=1e-12)

    def test_passive_effect_is_scalar_and_known_overlap(self):
        for switch in [0., .02, .1, .5]:
            theta = 2*np.arcsin(np.sqrt(switch))
            for dephase in [0., 1.]:
                maps, _ = true_instrument(Parameters(theta=theta, gap_dephasing=dephase))
                np.testing.assert_allclose(effect(maps[1]), .4*switch*np.eye(2), atol=1e-12)

    def test_no_false_information_from_passive_record(self):
        q = probabilities(branch_states(Parameters(), [0.]*4))
        c = probabilities(branch_states(Parameters(gap_dephasing=1.), [0.]*4))
        np.testing.assert_allclose(list(q.values()), list(c.values()), atol=1e-12)

    def test_observed_loss_and_confusion_mixtures(self):
        p = Parameters(eta=.5, e01=.1, e10=.2, mode_overlap=1.)
        bare, _ = true_instrument(p, 1.)
        observed, _ = observed_instrument(p, 1.)
        np.testing.assert_allclose(observed[0], .75*sum(bare), atol=1e-13)
        np.testing.assert_allclose(observed[2], .25*(.1*bare[0]+.8*bare[1]), atol=1e-13)

    def test_classical_diagonal_recursion(self):
        p = Parameters(gap_dephasing=1.)
        q = np.array([.3, .7]); rho = np.diag(q)
        for control, outcome in [(0., 1), (1., 2), (-1., 0), (1., 1)]:
            matrices = classical_matrices(p, control)
            maps, _ = observed_instrument(p, control)
            q = matrices[outcome] @ q
            rho = apply(maps[outcome], rho)
            np.testing.assert_allclose(rho, np.diag(q), atol=1e-12)
            rho = apply(gap_superoperator(p), rho)
            q = abs(np.array([[np.cos(p.theta/2), -np.sin(p.theta/2)], [np.sin(p.theta/2), np.cos(p.theta/2)]]))**2 @ q
            np.testing.assert_allclose(rho, np.diag(q), atol=1e-12)

    def test_all_observed_branches_positive_normalized(self):
        states = branch_states(Parameters(), [0., 1., -1.], observed=True)
        self.assertAlmostEqual(sum(probabilities(states).values()), 1., places=12)
        for rho in states.values():
            self.assertGreater(np.linalg.eigvalsh(rho).min(), -1e-12)

    def test_frozen_pair_real_state_preparation(self):
        for p in [0., .02, .1, .5]:
            circuit = frozen_pair_circuit(p)
            _, vector, _ = circuit_branches(circuit)
            observed = np.abs(vector[np.arange(len(vector)) >> 4 == 1])**2
            self.assertAlmostEqual(float(observed.sum()), .4*p, places=12)

    def test_one_pair_circuit_against_instrument(self):
        for dephase in [0., 1.]:
            for controls in [[0.], [1.], [-1.]]:
                report = validate_circuit(Parameters(gap_dephasing=dephase), controls)
                self.assertLess(report['branch_frobenius_error_max'], 1e-10)
                self.assertLess(report['conditional_memory_trace_distance_max'], 1e-10)
                self.assertLessEqual(report['resources']['qubits'], 8)

    def test_two_pair_retained_memory_circuit(self):
        for dephase in [0., 1.]:
            report = validate_circuit(Parameters(gap_dephasing=dephase), [1., -1.])
            self.assertLess(report['branch_frobenius_error_max'], 1e-10)
            self.assertLess(report['conditional_memory_trace_distance_max'], 1e-10)
            self.assertLessEqual(report['resources']['qubits'], 15)


if __name__ == '__main__':
    unittest.main()
