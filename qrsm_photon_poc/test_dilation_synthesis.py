"""Checks for the bounded photon-isometry circuit experiment."""
import importlib.util
import unittest

import numpy as np

if importlib.util.find_spec('qiskit'):
    from dilation_synthesis import flag_branch, run_case, validate_implementation


@unittest.skipUnless(importlib.util.find_spec('qiskit'), 'optional qiskit not installed')
class DilationSynthesisTests(unittest.TestCase):
    def test_flag_branch_reduces_environment_and_preserves_complex_coherence(self):
        # Row index = (2*environment + flag)*system_dimension + system.
        vector = np.zeros(8, complex)
        vector[2] = 1/np.sqrt(3)       # environment 0, flag 1, system 0
        vector[3] = 1j/np.sqrt(3)      # environment 0, flag 1, system 1
        vector[4] = 1/np.sqrt(3)       # environment 1, flag 0, system 0
        expected_yes = np.array([[1, -1j], [1j, 1]], complex)/3
        expected_no = np.array([[1, 0], [0, 0]], complex)/3
        np.testing.assert_allclose(flag_branch(vector, 2, 1), expected_yes, atol=1e-12)
        np.testing.assert_allclose(flag_branch(vector, 2, 0), expected_no, atol=1e-12)

    def test_synthesis_matches_retained_isometry_and_inverse(self):
        result = run_case(cutoff=.1, max_qubits=6)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['implementation_validation']['passed'])
        self.assertEqual(result['model']['total_qubits'], 6)
        self.assertEqual(result['synthesis']['all_input_basis_columns_checked'], 8)
        self.assertLess(result['synthesis']['common_phase_aligned_isometry_spectral_error'], 1e-9)
        self.assertLess(result['synthesis']['inverse_vector_error_max'], 1e-9)
        self.assertLess(result['state_checks']['synthesized_vs_retained_unnormalized_state_error_max'], 1e-9)
        # This deliberately crude cutoff is not the original instrument.
        self.assertGreater(result['approximation']['no_click_superoperator_frobenius_error'], .1)

    def test_validation_rejects_numerical_errors_and_nan(self):
        self.assertTrue(validate_implementation({'error': 1e-10})['passed'])
        self.assertFalse(validate_implementation({'error': 1e-4})['passed'])
        self.assertFalse(validate_implementation({'error': float('nan')})['passed'])

    def test_preflight_rejects_oversized_isometry_before_compilation(self):
        with self.assertRaisesRegex(ValueError, 'exceeding limit'):
            run_case(cutoff=.03, max_qubits=6)


if __name__ == '__main__':
    unittest.main()
