import unittest
import numpy as np
from fringe_compare import signals


class FringeTests(unittest.TestCase):
    def test_values_and_equal_loss(self):
        phi = np.array([0, np.pi/2, np.pi, 2*np.pi])
        noon, coherent = signals(phi)
        np.testing.assert_allclose(noon, [1, 0, 1, 1], atol=1e-14)
        np.testing.assert_allclose(coherent, [4, 1, 0, 4], atol=1e-14)
        a, b = signals(phi, .5)
        np.testing.assert_allclose(a, noon/4, atol=1e-14)
        np.testing.assert_allclose(b, coherent/4, atol=1e-14)

    def test_matches_independent_fock_space_calculation(self):
        a1 = np.diag(np.sqrt([1., 2.]), 1)
        a = np.kron(a1, np.eye(3))
        b = np.kron(np.eye(3), a1)
        psi = np.zeros(9, dtype=complex)
        psi[6] = psi[2] = 1/np.sqrt(2)  # |2,0> and |0,2>
        for phi in np.linspace(0, 2*np.pi, 9):
            c = (a + np.exp(1j*phi)*b)/np.sqrt(2)
            value = np.linalg.norm(c @ c @ psi)**2
            self.assertAlmostEqual(value, float(signals(phi)[0]))

    def test_input_checks(self):
        for eta in [-.1, 1.1]:
            with self.assertRaises(ValueError):
                signals(0, eta)
        with self.assertRaises(ValueError):
            signals(np.nan)


if __name__ == '__main__':
    unittest.main()
