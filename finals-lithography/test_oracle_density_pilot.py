"""Checks of the deterministic density-pilot scoring and remapping."""
import importlib.util
import unittest

import numpy as np

if importlib.util.find_spec('qiskit_aer'):
    from qiskit import QuantumCircuit, transpile
    from qiskit.providers.fake_provider import GenericBackendV2
    from qiskit.transpiler import CouplingMap
    from qiskit_aer import AerSimulator
    from oracle_density_pilot import (apply_readout, compact_and_measurement_map,
                                      score_probabilities, simulate_compacted)


@unittest.skipUnless(importlib.util.find_spec('qiskit_aer'), 'optional qiskit-aer not installed')
class DensityPilotTests(unittest.TestCase):
    def test_independent_readout_uses_little_endian_bits(self):
        # True state |10> (bit0=0, bit1=1), with different readout matrices.
        true = np.array([0, 0, 1, 0], dtype=float)
        bit0 = np.array([[.8, .2], [.1, .9]])
        bit1 = np.array([[.7, .3], [.4, .6]])
        np.testing.assert_allclose(apply_readout(true, [bit0, bit1]), [.32, .08, .48, .12])

    def test_scoring_exact_three_bit_bernoulli_distribution(self):
        p, n = .8, 3
        distribution = np.array([p**i.bit_count() * (1-p)**(n-i.bit_count()) for i in range(2**n)])
        result = score_probabilities(distribution, n, p)
        self.assertAlmostEqual(result['hit_probability'], .104)
        self.assertAlmostEqual(result['conditional_tv'], 0.0)

    def test_compaction_preserves_measurement_order(self):
        circuit = QuantumCircuit(4, 2)
        circuit.x(3)
        circuit.h(1)
        circuit.measure(3, 0)
        circuit.measure(1, 1)
        small, active, measurement = compact_and_measurement_map(circuit, 2)
        self.assertEqual(active, [1, 3])
        self.assertEqual(measurement, [3, 1])
        self.assertEqual(small.num_qubits, 2)

    def test_compacted_target_noise_matches_full_density_simulator(self):
        # Force a nontrivial physical mapping and compare against Aer built
        # directly from the whole target, independently of our remapping.
        backend = GenericBackendV2(num_qubits=4, basis_gates=['rz', 'sx', 'x', 'cx'],
                                   coupling_map=CouplingMap.from_line(4), seed=77, noise_info=True)
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.x(1)
        circuit.measure(range(2), range(2))
        isa = transpile(circuit, backend=backend, initial_layout=[2, 3],
                        optimization_level=1, seed_transpiler=13)
        compact_probs, _, _, measurement = simulate_compacted(isa, backend, 2)
        full = isa.remove_final_measurements(inplace=False)
        full.save_probabilities(measurement, label='data_probs')
        simulator = AerSimulator.from_backend(backend, method='density_matrix', max_parallel_threads=1)
        expected = np.asarray(simulator.run(full, shots=1).result().data(0)['data_probs'])
        np.testing.assert_allclose(compact_probs, expected, atol=1e-11)


if __name__ == '__main__':
    unittest.main()
