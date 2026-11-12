"""Independent checks of Choi ordering and photon-instrument dilation."""
import unittest

import numpy as np

from dilation_feasibility import (assess, branch_from_isometry, choi_matrix,
                                  flagged_isometry, kraus_from_superoperator)
from qrsm_photon import Parameters, instruments


class DilationTests(unittest.TestCase):
    def test_column_vectorization_with_complex_nonsymmetric_unitary(self):
        # Complex nonsymmetric U catches conjugation and transpose mistakes.
        U = np.array([[1, 1j], [1, -1j]], dtype=complex) / np.sqrt(2)
        S = np.kron(U.conj(), U)
        expected_vector = U.reshape(-1, order='F')
        np.testing.assert_allclose(choi_matrix(S, 2), np.outer(expected_vector, expected_vector.conj()), atol=1e-12)
        Ks, diagnostics = kraus_from_superoperator(S, 2)
        self.assertEqual(len(Ks), 1)
        self.assertLess(diagnostics['reconstructed_superoperator_frobenius_error'], 1e-12)

    def test_flagged_amplitude_damping_reconstructs_unnormalized_branches(self):
        gamma = .37
        K0 = np.diag([1, np.sqrt(1-gamma)]).astype(complex)
        K1 = np.array([[0, np.sqrt(gamma)], [0, 0]], complex)
        no, _ = kraus_from_superoperator(np.kron(K0.conj(), K0), 2)
        click, _ = kraus_from_superoperator(np.kron(K1.conj(), K1), 2)
        V, dim, env = flagged_isometry(no, click)
        np.testing.assert_allclose(V.conj().T @ V, np.eye(2), atol=1e-12)
        rho = np.array([[.6, .2j], [-.2j, .4]], complex)
        for flag, K in enumerate((K0, K1)):
            np.testing.assert_allclose(branch_from_isometry(V, rho, flag, dim, env), K @ rho @ K.conj().T, atol=1e-12)

    def test_unused_system_basis_is_identity_in_no_click_branch(self):
        # A three-level identity channel is padded to four levels. The extra
        # basis state is defined as no-click identity, not silently discarded.
        no = np.eye(3, dtype=complex)[None, :, :]
        click = np.zeros((0, 3, 3), dtype=complex)
        V, dim, env = flagged_isometry(no, click)
        self.assertEqual(dim, 4)
        rho = np.diag([0, 0, 0, 1]).astype(complex)
        np.testing.assert_allclose(V.conj().T @ V, np.eye(dim), atol=1e-12)
        np.testing.assert_allclose(branch_from_isometry(V, rho, 0, dim, env), rho, atol=1e-12)
        np.testing.assert_allclose(branch_from_isometry(V, rho, 1, dim, env), 0, atol=1e-12)

    def test_photon_simulator_outcomes_and_power_of_two_padding(self):
        result = assess(Parameters(n_cavity=3), random_states=4)
        self.assertEqual(result['model']['physical_system_dimension'], 12)
        self.assertEqual(result['model']['padded_system_dimension'], 16)
        self.assertEqual(result['checks']['nonzero_conditional_states_checked'], 8)
        self.assertLess(result['dilation']['isometry_spectral_error'], 1e-9)
        self.assertLess(result['no_click']['reconstructed_superoperator_frobenius_error'], 1e-9)
        self.assertLess(result['click']['reconstructed_superoperator_frobenius_error'], 1e-9)
        self.assertLess(result['no_click']['corrected_superoperator_frobenius_error'], 1e-9)
        self.assertLess(result['click']['corrected_superoperator_frobenius_error'], 1e-9)
        self.assertLess(result['checks']['outcome_probability_error_max'], 1e-9)
        self.assertLess(result['checks']['normalized_conditional_state_frobenius_error_max'], 1e-9)

    def test_two_step_click_histories_match_original_instruments(self):
        p = Parameters(n_cavity=2)
        d = 4*p.n_cavity
        maps = instruments(p)[:2]
        Ks = [kraus_from_superoperator(S, d)[0] for S in maps]
        V, dim, env = flagged_isometry(*Ks)
        rng = np.random.default_rng(12)
        psi = rng.normal(size=d) + 1j*rng.normal(size=d)
        psi /= np.linalg.norm(psi)
        rho = np.outer(psi, psi.conj())
        for sequence in ((0, 1), (1, 0), (1, 1)):
            expected = rho.copy()
            actual = rho.copy()
            for flag in sequence:
                expected = (maps[flag] @ expected.reshape(-1, order='F')).reshape((d, d), order='F')
                actual = branch_from_isometry(V, actual, flag, dim, env)
            np.testing.assert_allclose(actual, expected, atol=1e-10)


if __name__ == '__main__':
    unittest.main()
