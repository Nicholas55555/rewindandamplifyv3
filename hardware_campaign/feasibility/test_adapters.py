"""Focused independent checks; no account, hardware, or full study reruns."""
import io
import math
import sys
import unittest

import numpy as np
from qiskit import qpy

from adapters import (build_optical, build_spatial, exact_reference, marginal,
                      measured, score_counts, spatial_modules, event_mask)


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.optical = build_optical(1, .03, 'last', 0)
        cls.spatial = build_spatial('counter', 0)

    def test_spatial_import_restores_existing_generic_module(self):
        before = sys.modules.get('model')
        spatial_modules()
        self.assertIs(sys.modules.get('model'), before)

    def test_marginal_little_endian_order(self):
        p = np.zeros(32); p[0b10010] = .25; p[0b01001] = .75
        np.testing.assert_array_equal(marginal(p, [4, 1, 0]), [0,0,0,.25,.75,0,0,0])

    def test_real_optical_instrument_vs_channel_reference(self):
        probs, check = exact_reference(self.optical)
        self.assertTrue(check['all_checks_passed'])
        self.assertAlmostEqual(probs.sum(), 1., places=10)
        self.assertEqual(self.optical.metadata['measurement']['chronological_flag_qubits'], [3])

    def test_real_optical_amplification_preserves_selected_z_distribution(self):
        item = build_optical(1, .03, 'last', 1)
        exact_reference(item)
        mask = event_mask(item.metadata)
        before = self.optical.target_marginal[mask]; after = item.target_marginal[mask]
        np.testing.assert_allclose(before/before.sum(), after/after.sum(), atol=1e-12)
        self.assertAlmostEqual(after.sum(), math.sin(3*math.asin(math.sqrt(before.sum())))**2, places=12)

    def test_spatial_exact_joint_law_and_clean_padded_workspace(self):
        probs, check = exact_reference(self.spatial)
        self.assertEqual(self.spatial.circuit.num_qubits, 14)
        self.assertLess(abs(check['dirty_workspace_probability']), 1e-10)
        self.assertAlmostEqual(self.spatial.target_marginal[event_mask(self.spatial.metadata)].sum(), .0037065659808740337, places=13)

    def test_real_computed_spatial_oracle(self):
        item = build_spatial('counter', 1)
        _, check = exact_reference(item)
        self.assertLess(abs(check['dirty_workspace_probability']), 1e-10)
        self.assertAlmostEqual(item.metadata['expected_event_probability'], .03303018144527116, places=13)

    def test_qpy_and_measurement_identity(self):
        circuit = measured(self.optical)
        file = io.BytesIO(); qpy.dump(circuit, file); file.seek(0)
        restored = qpy.load(file)[0]
        self.assertEqual(circuit, restored)
        self.assertEqual(restored.cregs[0].name, 'meas')
        for q in range(circuit.num_qubits):
            instruction = restored.data[-circuit.num_qubits+q]
            self.assertEqual(restored.find_bit(instruction.qubits[0]).index, q)
            self.assertEqual(restored.find_bit(instruction.clbits[0]).index, q)

    def test_score_empty_selected_records_is_defined(self):
        result = score_counts({'0'*7: 100}, self.optical.metadata, self.optical.target_marginal)
        self.assertIsNone(result['selected_data_z_distribution_tv'])
        self.assertEqual(result['accepted_shots'], 0)
        self.assertGreater(result['raw_event_wilson95'][1], 0)

    def test_dirty_workspace_not_postselected(self):
        result = score_counts({format(1 << 9, '014b'): 10, format(6, '014b'): 90},
                              self.spatial.metadata, self.spatial.target_marginal)
        self.assertEqual(result['accepted_shots'], 10)
        self.assertEqual(result['dirty_workspace_shots'], 10)
        self.assertEqual(result['shots'], 100)

    def test_count_validation_and_width_guards(self):
        with self.assertRaises(ValueError): build_optical(4)
        with self.assertRaises(ValueError): build_optical(cutoff=.02)
        with self.assertRaises(ValueError): build_spatial(rounds=9)
        for counts in ({}, {'0': -.1}, {'1'*8: 1}):
            with self.assertRaises(ValueError): score_counts(counts, self.optical.metadata, self.optical.target_marginal)


if __name__ == '__main__':
    unittest.main()
