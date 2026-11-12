import math
import unittest
import numpy as np
from scipy.stats import poisson
from qiskit.quantum_info import Statevector
from circuit_model import (capped_poisson,cell_preparation,clean_mcx_gate,layout,
                           addition_plan,oracle,make_circuit,arithmetic_resource_counts)
from process_bounds import integer_weights,capped_cdf


def run_boolean_ccx(circuit,bits):
    bits=list(bits)
    for instruction in circuit.data:
        assert instruction.operation.name=='ccx'
        a,b,t=[circuit.find_bit(q).index for q in instruction.qubits]
        bits[t]^=bits[a]&bits[b]
    return bits


class FullSpatialTests(unittest.TestCase):
    def test_exact_four_bit_poisson_preparation(self):
        for dose in (1.5,1.8):
            p=capped_poisson(dose)
            np.testing.assert_allclose(Statevector.from_instruction(cell_preparation(dose)).data,np.sqrt(p),atol=2e-14)
            self.assertAlmostEqual(p[-1],poisson.sf(14,dose))
            self.assertAlmostEqual(p.sum(),1.)

    def test_clean_toffoli_chain_exhaustive_small_and_large_control_edges(self):
        for c in (2,3,4,5,6,7,23,195):
            circuit=clean_mcx_gate(c).definition
            patterns=list(range(2**c)) if c<=7 else [2**c-1,0]+[(2**c-1)^(1<<j) for j in range(c)]
            for pattern in patterns:
                for target in (0,1):
                    inputs=[(pattern>>j)&1 for j in range(c)]+[target]+[0]*(c-2)
                    output=run_boolean_ccx(circuit,inputs)
                    self.assertEqual(output[:c],inputs[:c])
                    self.assertEqual(output[c],target^(pattern==2**c-1))
                    self.assertTrue(all(x==0 for x in output[c+1:]))
            self.assertEqual(len(circuit.data),2*c-3)

    def test_clean_chain_has_no_hidden_relative_phases(self):
        # Actual statevector of c=5 (9 qubits) with unique complex amplitudes
        # on all populated control/target states. Every workspace is checked.
        c=5;gate=clean_mcx_gate(c);rng=np.random.default_rng(31)
        data=rng.normal(size=2**(c+1))+1j*rng.normal(size=2**(c+1));data/=np.linalg.norm(data)
        initial=np.zeros(2**gate.num_qubits,complex);initial[:len(data)]=data
        expected=initial.copy();a=2**c-1;b=a+2**c;expected[a],expected[b]=initial[b],initial[a]
        np.testing.assert_allclose(Statevector(initial).evolve(gate).data,expected,atol=1e-14)

    def test_controlled_carry_addition_exhaustive_modular_arithmetic(self):
        for width in range(2,8):
            for constant in range(1,2**min(width,4)):
                plan=list(addition_plan([constant],1,width))
                for initial in range(2**width):
                    for control in (0,1):
                        score=initial
                        for _,carry,target in plan:
                            if control and all((score>>j)&1 for j in carry):score^=1<<target
                        self.assertEqual(score,(initial+control*constant)%(2**width))

    def test_full_register_ledger_no_overflow_and_real_ancillas(self):
        _,weights=integer_weights()
        for w in weights.values():
            info=layout(w)
            self.assertEqual(info['data_qubits'],196)
            self.assertEqual(info['score_qubits'],23)
            self.assertEqual(info['extra_clean_qubits'],170)
            self.assertEqual(info['total_qubits'],389)
            self.assertLess(info['maximum_encoded_score'],2**info['score_qubits'])
            self.assertGreaterEqual(info['score_qubits']+info['extra_clean_qubits'],193)
            self.assertGreaterEqual(info['extra_clean_qubits'],info['oracle_clean_ancillas_reserved'])
            self.assertEqual(layout(w,style='compact')['total_qubits'],219)

    def test_actual_small_oracle_and_grover_preserve_predicate(self):
        weights=[1,3];bits=2;k=2;dose=1.5
        n=4;truth=np.kron(capped_poisson(dose,bits),capped_poisson(dose,bits))
        accepted=np.array([(i&3)+3*((i>>2)&3)<2**k for i in range(16)])
        p=float(truth[accepted].sum())
        for style in ('compact','clean'):
            mark=oracle(weights,bits,k,style)
            amp=np.arange(1,17,dtype=float);amp/=np.linalg.norm(amp)
            state=np.zeros(2**mark.num_qubits,complex);state[:16]=amp
            expected=state.copy();expected[:16]*=np.where(accepted,-1,1)
            np.testing.assert_allclose(Statevector(state).evolve(mark).data,expected,atol=1e-13)
            qc=make_circuit(weights,dose,bits,k,style)
            whole=Statevector.from_instruction(qc)
            probs=whole.probabilities(range(n));hit=probs[accepted].sum()
            self.assertAlmostEqual(hit,math.sin(3*math.asin(math.sqrt(p)))**2,places=12)
            np.testing.assert_allclose(probs[accepted]/hit,truth[accepted]/p,atol=1e-13)
            self.assertLess(np.abs(whole.data[16:]).sum(),1e-11)

    def test_finite_classical_dp_matches_complete_small_enumeration(self):
        for dose in (1.5,1.8):
            pmf=capped_poisson(dose,2)
            expected=sum(pmf[a]*pmf[b] for a in range(4) for b in range(4) if a+3*b<4)
            self.assertAlmostEqual(capped_cdf([1,3],dose,4,2),expected,places=14)

    def test_tail_bound_counts_changes_above_cap_not_overflow_category(self):
        for dose in (1.5,1.8):
            changed=poisson.sf(15,dose);overflow=poisson.sf(14,dose)
            self.assertLess(changed,overflow)
            self.assertLessEqual(-np.expm1(49*np.log1p(-changed)),49*changed)


if __name__=='__main__':unittest.main()
