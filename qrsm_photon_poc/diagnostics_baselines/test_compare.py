"""Independent checks of inference, likelihood, and reported uncertainty."""
from dataclasses import replace
import itertools
import unittest

import numpy as np

if __package__:
    from .compare import (Parameters, fit_hmm, hmm_likelihood_and_stats,
                          paired_comparison, physical_loglikelihood_by_record,
                          validate_records)
else:
    from compare import (Parameters, fit_hmm, hmm_likelihood_and_stats,
                         paired_comparison, physical_loglikelihood_by_record,
                         validate_records)
from qrsm_photon import record_loglikelihood, sample_records


class ComparisonTests(unittest.TestCase):
    def test_forward_backward_against_exhaustive_hidden_paths(self):
        observation = np.array([[1, 0, 1]], dtype=np.uint8)
        initial = np.array([.4, .6])
        transition = np.array([[.7, .3], [.2, .8]])
        emissions = np.array([.15, .8])
        joint = []
        for states in itertools.product(range(2), repeat=3):
            p = initial[states[0]]
            for t, state in enumerate(states):
                p *= emissions[state] if observation[0, t] else 1-emissions[state]
                if t:
                    p *= transition[states[t-1], state]
            joint.append((states, p))
        total = sum(p for _, p in joint)
        pi = np.zeros(2); transitions = np.zeros((2, 2)); states_sum = np.zeros(2); ones_sum = np.zeros(2)
        for states, probability in joint:
            weight = probability / total
            pi[states[0]] += weight
            for t, state in enumerate(states):
                states_sum[state] += weight
                ones_sum[state] += weight*observation[0, t]
                if t:
                    transitions[states[t-1], state] += weight
        logs, actual_pi, actual_transitions, actual_states, actual_ones = hmm_likelihood_and_stats(
            observation, initial, transition, emissions, stats=True)
        np.testing.assert_allclose(logs, [np.log(total)], atol=1e-12)
        for actual, expected in zip((actual_pi, actual_transitions, actual_states, actual_ones),
                                    (pi, transitions, states_sum, ones_sum)):
            np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_physical_per_record_matches_existing_total(self):
        params = replace(Parameters(), n_cavity=2)
        data = sample_records(params, n_records=6, steps=7, seed=13)
        scores = physical_loglikelihood_by_record(data, params)
        self.assertAlmostEqual(float(scores.sum()), record_loglikelihood(data, params), places=10)

    def test_hmm_training_is_reproducible_and_em_does_not_descend(self):
        data = np.random.default_rng(71).binomial(1, .3, size=(30, 12))
        first = fit_hmm(data, states=2, starts=3, max_iter=30, seed=19)
        second = fit_hmm(data, states=2, starts=3, max_iter=30, seed=19)
        self.assertEqual(first['train_log_likelihood'], second['train_log_likelihood'])
        self.assertTrue(all(s['largest_em_step_decline'] < 1e-8 for s in first['starts']))
        self.assertAlmostEqual(float(first['initial'].sum()), 1)
        np.testing.assert_allclose(first['transition'].sum(axis=1), 1)

    def test_paired_uncertainty_uses_record_differences(self):
        a = np.array([-2., -3., -1., -2.])
        b = np.array([-3., -3., -3., -4.])
        got = paired_comparison(a, b, bootstrap=200, seed=1)
        delta = a-b
        self.assertAlmostEqual(got['mean_delta_nats_per_record'], float(delta.mean()))
        self.assertAlmostEqual(got['standard_error_nats_per_record'], float(delta.std(ddof=1)/2))
        self.assertEqual(got['n_heldout_records'], 4)

    def test_nonbinary_records_rejected(self):
        with self.assertRaises(ValueError):
            validate_records(np.array([[0, .5], [1, 0]]))


if __name__ == '__main__':
    unittest.main()
