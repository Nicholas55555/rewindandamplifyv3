import unittest
import itertools
import numpy as np

from physical_model import Parameters, branch_states, probabilities
from inference import (generate_records, log_likelihood, likelihood_ratio,
                       rng_for, markov_fit, markov_score, hmm_forward, hmm_fit, hmm_score)


class InferenceTests(unittest.TestCase):
    def test_likelihood_matches_all_exact_branches(self):
        controls = [0., 1., -1.]
        for d in [0., 1.]:
            p = Parameters(gap_dephasing=d)
            records = np.array(list(itertools.product(range(3), repeat=3)), dtype=np.uint8)
            exact = probabilities(branch_states(p, controls, observed=True))
            np.testing.assert_allclose(np.exp(log_likelihood(p, controls, records)),
                                       [exact[tuple(r)] for r in records], atol=1e-12)

    def test_sampling_matches_distribution(self):
        p = Parameters(); controls = [1., -1.]
        records = generate_records(p, controls, 100000, rng_for(999, 1))
        exact = probabilities(branch_states(p, controls, observed=True))
        for key, value in exact.items():
            observed = np.mean(np.all(records == key, axis=1))
            self.assertLess(abs(observed-value), 6*np.sqrt(value*(1-value)/len(records))+.0001)

    def test_passive_likelihood_ratio_numerically_zero(self):
        controls = [0.]*16
        records = generate_records(Parameters(), controls, 100, rng_for(999, 2))
        result = likelihood_ratio(Parameters(), Parameters(gap_dephasing=1.), controls, records)
        np.testing.assert_array_equal(result, np.zeros(len(records)))

    def test_prefix_filter_does_not_use_future(self):
        p = Parameters(); controls = [1., -1., 0.]
        records = generate_records(p, controls, 100, rng_for(999, 3))
        before = log_likelihood(p, controls[:2], records[:, :2])
        records[:, 2] = (records[:, 2]+1)%3
        np.testing.assert_array_equal(before, log_likelihood(p, controls[:2], records[:, :2]))

    def test_hmm_forward_matches_enumeration(self):
        pi = np.array([.4, .6]); a = np.array([[.7, .3], [.2, .8]])
        b = np.array([[[.2, .5, .3], [.6, .1, .3]]]*3)
        records = np.array([[0, 1, 2]], dtype=np.uint8)
        _, scales = hmm_forward(pi, a, b, records, [0, 1, 2])
        exact = 0.
        for history in itertools.product(range(2), repeat=3):
            value = pi[history[0]]*b[0, history[0], 0]
            for t in range(1, 3):
                value *= a[history[t-1], history[t]]*b[t, history[t], records[0, t]]
            exact += value
        self.assertAlmostEqual(float(scales.prod()), exact, places=13)

    def test_hmm_EM_monotonic_and_finite(self):
        contexts = [0, 1, 2]*4
        records = generate_records(Parameters(), [0., 1., -1.]*4, 100, rng_for(999, 4))
        model, report = hmm_fit(records, contexts, states=2, regime=999, starts=1, iterations=20)
        self.assertGreater(min(np.diff(report['trace'])), -1e-7)
        self.assertTrue(np.all(np.isfinite(hmm_score(model, records, contexts))))
        for row in model['transition']:
            self.assertAlmostEqual(sum(row), 1.)

    def test_markov_predictor_normalized(self):
        records = np.array([[0, 1, 2], [1, 1, 0]], dtype=np.uint8)
        model = markov_fit(records, [0, 1, 2])
        np.testing.assert_allclose(model.sum(axis=2), 1.)
        self.assertTrue(np.all(np.isfinite(markov_score(model, records, [0, 1, 2]))))


if __name__ == '__main__':
    unittest.main()
