"""Verify two-bin coherent click queries and the conditional hidden state."""
import math
import unittest

import numpy as np

from two_bin_amplification import make_instrument, outcome_states, run, trace_distance


class TwoBinAmplificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.double = run(event='double', compile_counts=False)
        cls.last = run(event='last', compile_counts=False)

    def test_all_record_branches_match_channel_and_are_normalized(self):
        record = self.double
        events = record['event']
        self.assertLess(events['preparation_vs_retained_max_branch_frobenius_error'], 1e-9)
        self.assertAlmostEqual(sum(row['retained'] for row in record['history_probabilities'].values()), 1, places=10)
        self.assertAlmostEqual(sum(row['amplified'] for row in record['history_probabilities'].values()), 1, places=10)
        self.assertAlmostEqual(events['qiskit_preparation_probability'], events['retained_model_probability'], places=10)

    def test_double_click_amplifies_theory_and_preserves_hidden_state(self):
        e = self.double['event']
        expected = math.sin(3*math.asin(math.sqrt(e['retained_model_probability'])))**2
        self.assertAlmostEqual(e['qiskit_amplified_probability'], expected, places=10)
        self.assertGreater(e['qiskit_amplified_probability'], e['qiskit_preparation_probability'])
        self.assertLess(e['amplified_vs_retained_conditional_state_trace_distance'], 1e-9)
        # Approximation versus the original channel is reported separately.
        self.assertGreater(e['retained_vs_original_conditional_state_trace_distance'], 1e-5)

    def test_single_click_query_preserves_conditional_history_ratio(self):
        e, history = self.last['event'], self.last['history_probabilities']
        self.assertLess(e['amplified_vs_retained_conditional_state_trace_distance'], 1e-9)
        before = history['11']['retained']/(history['01']['retained'] + history['11']['retained'])
        after = history['11']['amplified']/(history['01']['amplified'] + history['11']['amplified'])
        self.assertAlmostEqual(before, after, places=10)
        self.assertAlmostEqual(e['qiskit_amplified_probability'], e['one_round_theoretical_probability'], places=10)

    def test_input_validation_and_trace_distance(self):
        self.assertAlmostEqual(trace_distance(np.diag([1., 0.]), np.diag([0., 1.])), 1)
        with self.assertRaises(ValueError):
            make_instrument(float('nan'))
        with self.assertRaises(ValueError):
            outcome_states(np.zeros(10), 3)


if __name__ == '__main__':
    unittest.main()
