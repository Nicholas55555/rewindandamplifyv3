import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from adapters import contact,large_catalog,semantic_catalog,history,bounded,compiled,counter_oracle,enumerated_oracle


class ExtensionTests(unittest.TestCase):
    def test_contact_independent_law_and_clean_work(self):
        for n in [3,5,7]:
            for style in ['counter','enumerated']:
                for rounds in [0,1]:
                    qc,meta,target=contact(n,style,rounds)
                    np.testing.assert_allclose(Statevector.from_instruction(qc).probabilities(),target,atol=2e-12)
                    self.assertAlmostEqual(target.sum(),1,places=12)
                    expected=.2**n+n*.8*.2**(n-1)
                    self.assertAlmostEqual(meta['plain_event_probability'],expected,places=14)

    def test_every_small_oracle_input(self):
        for n in [3,5,7]:
            for builder in [counter_oracle,enumerated_oracle]:
                # A standalone oracle is tested on arbitrary basis inputs.
                # Default zero-input HLS may borrow untouched data as clean
                # ancillas; that assumption is invalid for this unitary check.
                oracle=compiled(builder(n),qubits_initially_zero=False)
                for basis in range(1<<n):
                    actual=Statevector.from_int(basis,1<<oracle.num_qubits).evolve(oracle).data
                    expected=np.zeros_like(actual);expected[basis]=-1 if basis.bit_count()<2 else 1
                    np.testing.assert_allclose(actual,expected,atol=3e-12)

    def test_catalog_cost_is_seeded_mark_table_not_semantic_database(self):
        qc,meta,target=large_catalog(1)
        actual=Statevector.from_instruction(qc).probabilities()
        np.testing.assert_allclose(actual,target,atol=2e-12)
        self.assertEqual(meta['entries'],1024);self.assertEqual(meta['canonical_cost_round_convention'],25)
        self.assertGreater(meta['marked_fraction'],.4);self.assertLess(meta['marked_fraction'],.6)

    def test_real_semantic_catalog(self):
        qc,meta,target=semantic_catalog()
        np.testing.assert_allclose(Statevector.from_instruction(qc).probabilities(),target,atol=1e-12)
        self.assertEqual(meta['catalog'][meta['target_index']],'employee_payroll_by_department')

    def test_history_fast_tensor_and_clean_ancillas(self):
        for r,steer in [(0,False),(1,False),(1,True)]:
            qc,meta,target=history(8,r,steer)
            np.testing.assert_allclose(Statevector.from_instruction(compiled(qc)).probabilities(),target,atol=3e-12)
            if not steer:self.assertLess(meta['ideal_conditional_history_bias_vs_original_tv'],1e-12)

    def test_bounded_rewind_matches_canonical_horizon_rule(self):
        for w in [4,8]:
            qc,meta,target=bounded(10,w,1)
            np.testing.assert_allclose(Statevector.from_instruction(compiled(qc)).probabilities(),target,atol=4e-12)
            self.assertEqual(meta['reflection_qubits'],list(range(12-w,12)))
            self.assertGreater(meta['ideal_conditional_history_bias_vs_original_tv'],0)

    def test_invalid_rungs(self):
        with self.assertRaises(ValueError):contact(9,'counter',1)
        with self.assertRaises(ValueError):large_catalog(7)
        with self.assertRaises(ValueError):history(18,1)
        with self.assertRaises(ValueError):bounded(20,8,1)


if __name__=='__main__':unittest.main()
