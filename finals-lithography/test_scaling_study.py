"""Focused regression checks for the ideal threshold scaling study."""
import importlib.util
import unittest

from scaling_study import study


@unittest.skipUnless(importlib.util.find_spec('qiskit'), 'optional qiskit is not installed')
class ScalingStudyTests(unittest.TestCase):
    def test_tiny_cases_have_known_probabilities_and_correct_cost_accounting(self):
        results = study(sizes=[3, 5])['records']
        three, five = results
        self.assertAlmostEqual(three['event_probability_before'], .104)
        self.assertAlmostEqual(three['ideal_qiskit_event_probability_after'], .694413824)
        self.assertAlmostEqual(five['event_probability_before'], .00672)
        self.assertAlmostEqual(five['ideal_qiskit_event_probability_after'], .05940105383116563)
        for row in results:
            self.assertLess(row['conditional_history_total_variation'], 1e-10)
            self.assertEqual(row['preparation_calls_per_circuit'], 2)
            self.assertEqual(row['inverse_preparation_calls_per_circuit'], 1)
            self.assertEqual(row['oracle_calls_per_circuit'], 1)
            self.assertEqual(row['failing_histories_explicitly_marked'], row['sites_and_logical_qubits'] + 1)
            self.assertGreater(row['compiled_generic_cx'], 0)


if __name__ == '__main__':
    unittest.main()
