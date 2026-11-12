"""Bounded checks of temporal quantum states, interference and pair accounting."""
import unittest

import numpy as np
from numpy.polynomial.legendre import leggauss

from model import (Emitter, hom_observables, hom_overlap, quadrature_overlap,
                   simulate_trap_pairs, stationary_trap_joint, temporal_density,
                   trap_pair_overlap, wilson_interval)


class QuantumDotBridgeTests(unittest.TestCase):
    def test_parameter_guards(self):
        for kwargs in [{'lifetime_s': 0}, {'lifetime_s': -1}, {'pure_dephasing_per_s': -1},
                       {'frequency_offset_hz': np.nan}]:
            with self.assertRaises(ValueError):
                Emitter(**kwargs)
        for eta in [-.1, 1.1, np.inf]:
            with self.assertRaises(ValueError):
                hom_observables(.5, eta)
        with self.assertRaises(ValueError):
            temporal_density(-1, 0, Emitter())
        with self.assertRaises(ValueError):
            stationary_trap_joint(1.01)

    def test_transform_limit_and_t2_relation(self):
        for rate in [0, 1e8, 5e8, 2e9]:
            emitter = Emitter(1e-9, rate)
            self.assertAlmostEqual(hom_overlap(emitter, emitter), emitter.coherence_time_s / (2 * emitter.lifetime_s))
        self.assertEqual(hom_overlap(Emitter(), Emitter()), 1)

    def test_hertz_angular_conversion_and_common_shift(self):
        gamma = 1e9
        half_overlap_hz = gamma / (2 * np.pi)
        self.assertAlmostEqual(hom_overlap(Emitter(), Emitter(frequency_offset_hz=half_overlap_hz)), .5)
        a, b = Emitter(1e-9, 1e8, .2e9), Emitter(1e-9, 1e8, .35e9)
        shifted_a, shifted_b = Emitter(1e-9, 1e8, 1.2e9), Emitter(1e-9, 1e8, 1.35e9)
        self.assertAlmostEqual(hom_overlap(a, b), hom_overlap(shifted_a, shifted_b))

    def test_unequal_lifetime_pure_state_overlap(self):
        first, second = Emitter(1e-9), Emitter(2e-9)
        self.assertAlmostEqual(hom_overlap(first, second), 8 / 9)
        self.assertAlmostEqual(hom_overlap(first, second), hom_overlap(second, first))

    def test_fully_distinguishable_limit(self):
        self.assertLess(hom_overlap(Emitter(), Emitter(frequency_offset_hz=1e15)), 1e-12)
        result = hom_observables(0, .2)
        self.assertEqual(result['conditional_coincidence_probability'], .5)
        self.assertAlmostEqual(result['coincidence_probability_per_excitation_pair'], .02)

    def test_monotonic_dephasing_and_detuning(self):
        base = Emitter()
        dephased = [hom_overlap(Emitter(1e-9, g), Emitter(1e-9, g)) for g in [0, 1e8, 1e9, 1e10]]
        detuned = [hom_overlap(base, Emitter(frequency_offset_hz=d)) for d in [0, 1e8, 1e9, 1e10]]
        self.assertTrue(np.all(np.diff(dephased) < 0))
        self.assertTrue(np.all(np.diff(detuned) < 0))

    def test_density_normalization_hermiticity_and_positive_semidefinite(self):
        nodes, weights = leggauss(96)
        end = 24e-9
        time = (nodes + 1) * end / 2
        weights = weights * end / 2
        for dephasing in [0, 1e8, 1e9]:
            emitter = Emitter(1e-9, dephasing, .4e9)
            kernel = temporal_density(time[:, None], time[None, :], emitter)
            matrix = np.sqrt(weights[:, None] * weights[None, :]) * kernel
            np.testing.assert_allclose(matrix, matrix.conj().T, atol=1e-14)
            self.assertAlmostEqual(np.trace(matrix).real, 1 - np.exp(-24), places=12)
            self.assertGreater(np.linalg.eigvalsh(matrix).min(), -1e-13)
            if dephasing == 0:
                self.assertAlmostEqual(np.trace(matrix @ matrix).real, (1 - np.exp(-24)) ** 2, places=12)

    def test_independent_kernel_quadrature_and_refinement(self):
        examples = [(Emitter(), Emitter()),
                    (Emitter(1e-9, 3e8), Emitter(1e-9, 3e8)),
                    (Emitter(1e-9, 1e8, -.25e9), Emitter(1e-9, 1e8, .25e9)),
                    (Emitter(1e-9, 1e8), Emitter(1.4e-9, 3e8, .25e9))]
        for a, b in examples:
            coarse, fine = quadrature_overlap(a, b, 96), quadrature_overlap(a, b, 192)
            self.assertLess(abs(fine['overlap'] - hom_overlap(a, b)), fine['absolute_truncation_bound'] + 1e-10)
            self.assertLess(abs(fine['overlap'] - coarse['overlap']), 1e-10)

    def test_unnormalized_quadrature_retains_finite_window_loss(self):
        result = quadrature_overlap(Emitter(), Emitter(), 64, window_lifetimes=2)
        self.assertAlmostEqual(result['overlap'], (1 - np.exp(-2)) ** 2, places=12)
        self.assertAlmostEqual(1 - result['overlap'], result['absolute_truncation_bound'], places=12)

    def test_loss_charges_pair_yield_without_changing_conditional_overlap(self):
        for eta in [0, .1, .5, 1]:
            result = hom_observables(.8, eta)
            self.assertEqual(result['conditional_overlap'], .8)
            self.assertAlmostEqual(result['both_photons_survive_probability'], eta ** 2)
            self.assertAlmostEqual(result['coincidence_probability_per_excitation_pair'], .1 * eta ** 2)
            self.assertAlmostEqual(result['distinguishable_control_coincidence_per_excitation_pair'], .5 * eta ** 2)
            self.assertEqual(result['hom_observable_with_nonzero_efficiency'], eta > 0)

    def test_independent_two_photon_fock_beamsplitter_construction(self):
        # Four output modes: (c_u, c_v, d_u, d_v). The internal modes u,v are
        # orthogonal; c,d label spatial output ports. Apply actual bosonic
        # creation operators to vacuum, including sqrt(occupation+1) factors.
        def create_superposition(state, coefficients):
            output = {}
            for occupation, amplitude in state.items():
                for mode, coefficient in enumerate(coefficients):
                    raised = list(occupation)
                    raised[mode] += 1
                    key = tuple(raised)
                    value = amplitude * coefficient * np.sqrt(occupation[mode] + 1)
                    output[key] = output.get(key, 0j) + value
            return output

        vacuum = {(0, 0, 0, 0): 1.0 + 0j}
        # a_u^dagger -> (c_u^dagger+d_u^dagger)/sqrt(2).
        first_photon = create_superposition(vacuum, np.array([1, 0, 1, 0]) / np.sqrt(2))
        for overlap in [0, .1, .5, .9, 1]:
            with self.subTest(overlap=overlap):
                # b contains sqrt(M)u + sqrt(1-M)v; b_j^dagger maps to
                # (c_j^dagger-d_j^dagger)/sqrt(2), with the relative minus sign.
                second_coefficients = np.array([np.sqrt(overlap), np.sqrt(1 - overlap),
                                                -np.sqrt(overlap), -np.sqrt(1 - overlap)]) / np.sqrt(2)
                state = create_superposition(first_photon, second_coefficients)
                self.assertTrue(all(sum(occupation) == 2 for occupation in state))
                self.assertAlmostEqual(sum(abs(amplitude) ** 2 for amplitude in state.values()), 1, places=13)
                coincidence = sum(abs(amplitude) ** 2 for occupation, amplitude in state.items()
                                  if sum(occupation[:2]) == 1 and sum(occupation[2:]) == 1)
                self.assertAlmostEqual(coincidence, (1 - overlap) / 2, places=13)
                self.assertAlmostEqual(coincidence, hom_observables(overlap, .2)['conditional_coincidence_probability'], places=13)

    def test_trap_joint_has_same_marginals_for_every_correlation(self):
        for p in [0, .02, .1, .5, 1]:
            joint = stationary_trap_joint(p)
            np.testing.assert_allclose(joint.sum(axis=0), [.5, .5])
            np.testing.assert_allclose(joint.sum(axis=1), [.5, .5])
            self.assertAlmostEqual(joint[0, 1] + joint[1, 0], p)
        np.testing.assert_allclose(stationary_trap_joint(.5), np.full((2, 2), .25))

    def test_correlated_pairs_not_product_of_marginals(self):
        emitter = Emitter(1e-9, 1e8)
        equal = hom_overlap(emitter, emitter)
        shifted = hom_overlap(emitter, Emitter(1e-9, 1e8, .5e9))
        self.assertAlmostEqual(trap_pair_overlap(emitter, .25e9, .5), (equal + shifted) / 2)
        self.assertAlmostEqual(trap_pair_overlap(emitter, .25e9, 0), equal)
        self.assertGreater(trap_pair_overlap(emitter, .25e9, .02), trap_pair_overlap(emitter, .25e9, .5))

    def test_seeded_pair_sampling_matches_exact_joint_and_accounting(self):
        emitter, p, eta, n = Emitter(1e-9, 1e8), .1, .5, 100_000
        result = simulate_trap_pairs(emitter, .25e9, p, eta, n, 1919)
        expected = hom_observables(trap_pair_overlap(emitter, .25e9, p), eta)
        for count, probability in [(result['switched_pair_count'], p),
                                    (result['both_survived_pairs'], eta ** 2),
                                    (result['coincidence_pairs'], expected['coincidence_probability_per_excitation_pair'])]:
            self.assertLess(abs(count / n - probability), 5 * np.sqrt(probability * (1 - probability) / n))
        self.assertEqual(result['emitted_photons'], 2 * n)
        self.assertLessEqual(result['coincidence_pairs'], result['both_survived_pairs'])
        self.assertEqual(result['seed_spawn_keys'], [[0], [1], [2]])

    def test_zero_loss_limit_and_seed_reproducibility(self):
        args = (Emitter(), .25e9, .1, 0, 32, 22)
        first = simulate_trap_pairs(*args)
        self.assertEqual(first, simulate_trap_pairs(*args))
        self.assertEqual(first['coincidence_pairs'], 0)
        self.assertIsNone(first['observed_conditional_coincidence_rate'])
        self.assertIsNone(first['conditional_coincidence_wilson95'])

    def test_wilson_zero_counts_has_nonzero_upper_bound(self):
        low, high = wilson_interval(0, 1000)
        self.assertAlmostEqual(low, 0)
        self.assertGreater(high, 0)
        self.assertLess(high, .004)
        with self.assertRaises(ValueError):
            wilson_interval(0, 0)


if __name__ == '__main__':
    unittest.main()
