"""Behavioral correctness checks for the structured threshold oracle."""
import importlib.util
import math
import unittest

if importlib.util.find_spec('qiskit'):
    from oracle_comparison import basis_phase_error, counter_oracle, enumerated_oracle, result_for


@unittest.skipUnless(importlib.util.find_spec('qiskit'), 'optional qiskit not installed')
class OracleComparisonTests(unittest.TestCase):
    def test_all_basis_states_are_marked_exactly_and_workspace_is_clean(self):
        for n in range(3, 8):
            for factory in (enumerated_oracle, counter_oracle):
                with self.subTest(n=n, oracle=factory.__name__):
                    self.assertLess(basis_phase_error(factory(n), n), 1e-10)

    def test_full_one_round_circuits_preserve_conditional_law(self):
        for n in (3, 5, 7):
            enumerated = result_for(n, .8, 'enumerated')
            counter = result_for(n, .8, 'counter')
            self.assertAlmostEqual(enumerated['marked_probability_after'], counter['marked_probability_after'], places=10)
            theta = math.asin(math.sqrt(counter['marked_probability_before']))
            self.assertAlmostEqual(counter['marked_probability_after'], math.sin(3*theta)**2, places=10)
            self.assertLess(counter['conditional_history_tv'], 1e-10)
            self.assertLess(enumerated['conditional_history_tv'], 1e-10)
            self.assertLess(counter['dirty_work_probability'], 1e-12)


if __name__ == '__main__':
    unittest.main()
