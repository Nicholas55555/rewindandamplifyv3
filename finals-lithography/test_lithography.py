import unittest

from lithography import _sample, exact_distribution, quantum_demo, simulate


class LithographyTests(unittest.TestCase):
    def test_exact_enumeration_and_conditional_distribution(self):
        exact = exact_distribution()
        self.assertAlmostEqual(exact['failure_probability'], .00672)
        self.assertAlmostEqual(sum(exact['conditional_histories'].values()), 1)
        self.assertEqual(len(exact['conditional_histories']), 6)
        self.assertAlmostEqual(exact['conditional_histories']['00000'], 1/21)

    def test_estimates_and_weighted_conditional_histories(self):
        result = simulate(shots=30000, seed=77)
        self.assertEqual(result, simulate(shots=30000, seed=77))
        for name in ('direct_monte_carlo', 'importance_sampling'):
            r = result[name]
            self.assertLess(abs(r['estimated_failure_probability'] - .00672), 5*r['standard_error'])
            self.assertLess(r['conditional_total_variation'], .15)
        self.assertLess(result['importance_sampling']['standard_error'], result['direct_monte_carlo']['standard_error'])

    def test_validation(self):
        for kwargs in ({'p': 0}, {'q': 1}, {'shots': 1}, {'threshold': 6}):
            with self.assertRaises(ValueError):
                simulate(**kwargs)

    def test_no_sampled_failures_do_not_imply_zero_uncertainty(self):
        result = simulate(shots=2, seed=77)
        direct = result['direct_monte_carlo']
        self.assertEqual(direct['proposal_failures'], 0)
        self.assertIsNone(direct['standard_error'])
        self.assertIsNone(direct['conditional_total_variation'])

        # Likewise, all failures in a small sample cannot establish certainty.
        direct = simulate(n=1, p=.01, q=.01, threshold=1, shots=2, seed=77)['direct_monte_carlo']
        self.assertEqual(direct['proposal_failures'], 2)
        self.assertIsNone(direct['standard_error'])

    def test_importance_weights_recover_exact_probability(self):
        # At q=1/4, these 16 histories exactly realize the proposal law.
        histories = [(0, 0)]*9 + [(0, 1)]*3 + [(1, 0)]*3 + [(1, 1)]
        class DeterministicRandom:
            values = iter(.1 if bit else .9 for history in histories for bit in history)
            def random(self):
                return next(self.values)
        result = _sample(2, .7, 2, .25, 16, DeterministicRandom())
        exact = exact_distribution(2, .7, 2)
        self.assertAlmostEqual(result['estimated_failure_probability'], exact['failure_probability'])
        for history, probability in exact['conditional_histories'].items():
            self.assertAlmostEqual(result['conditional_histories'][history], probability)

    def test_qiskit_circuit_if_available(self):
        try:
            import qiskit  # noqa: F401
        except ImportError:
            self.skipTest('optional qiskit not installed')
        result = quantum_demo()
        self.assertAlmostEqual(result['event_probability_after'], result['theoretical_after'], places=9)
        self.assertLess(result['conditional_total_variation'], 1e-9)
        self.assertGreater(result['event_probability_after'], .99)
        self.assertGreater(result['compiled_cx_gates'], 0)

    def test_quantum_matches_enumeration_across_rounds(self):
        try:
            import qiskit  # noqa: F401
        except ImportError:
            self.skipTest('optional qiskit not installed')
        # Two distinct failure Hamming weights exercise non-uniform conditional
        # probabilities, and multiple rounds also test Grover overshoot.
        for rounds in (0, 1, 2):
            with self.subTest(rounds=rounds):
                result = quantum_demo(n=3, p=.7, threshold=2, iterations=rounds)
                self.assertAlmostEqual(result['event_probability_after'], result['theoretical_after'], places=10)
                self.assertLess(result['conditional_total_variation'], 1e-9)


if __name__ == '__main__':
    unittest.main()
