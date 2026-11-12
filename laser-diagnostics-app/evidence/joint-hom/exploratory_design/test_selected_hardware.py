import unittest
import numpy as np
from dataclasses import replace
from design import Parameters
from selected_hardware import build,marginal_reference,compile_and_verify
from circuits import sequential_circuit
from qiskit.quantum_info import Statevector
from qiskit import transpile


class Tests(unittest.TestCase):
    def test_small_builder_matches_original(self):
        for d in [0.,1.]:
            p=Parameters(theta=3*np.pi/4,gap_dephasing=d)
            for controls in [[2.],[2.,2.]]:
                a=transpile(build(p,controls),basis_gates=['u','cx'],optimization_level=1,seed_transpiler=31)
                b=transpile(sequential_circuit(p,controls),basis_gates=['u','cx'],optimization_level=1,seed_transpiler=31)
                np.testing.assert_allclose(Statevector.from_instruction(a).data,Statevector.from_instruction(b).data,atol=2e-13)

    def test_marginal_order_and_mps(self):
        p=Parameters(theta=3*np.pi/4)
        qc=build(p,[2.,2.]);compiled,prob,branches,report=compile_and_verify(qc,p,[2.,2.])
        self.assertAlmostEqual(prob.sum(),1.)
        for bits,rho in branches.items():
            i=bits[0]+2*bits[1]
            self.assertAlmostEqual(prob[i]+prob[i+4],np.trace(rho).real)
        self.assertLess(report['marginal_max_abs_error'],2e-10)

    def test_bounded_register_count(self):
        self.assertEqual(build(Parameters(),[2.]*4).num_qubits,22)
        self.assertEqual(build(Parameters(gap_dephasing=1.),[2.]*4).num_qubits,29)
        with self.assertRaises(ValueError):build(Parameters(gap_dephasing=1.),[2.]*5)


if __name__=='__main__':unittest.main()
