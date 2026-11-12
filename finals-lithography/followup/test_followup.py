"""Independent behavioral checks of the model, oracle, and sampler."""
import math
import unittest
import numpy as np
from scipy.stats import poisson
from qiskit.quantum_info import Statevector
from model import (DEFAULT, capped_pmf, joint_probabilities, dp_solution, accepted,
                   conditional_draws, encode, independent_control, summarize, decode)
from quantum import preparation, counter_oracle, enumerated_oracle, score_adder, ideal_case, apply_readout


class ModelTests(unittest.TestCase):
    def test_cap_matches_poisson_tail_and_event_is_exact(self):
        for lam in (.2, 1.5, 2.5, 9.):
            np.testing.assert_allclose(capped_pmf(lam)[:3], poisson.pmf([0,1,2], lam))
            self.assertAlmostEqual(capped_pmf(lam)[3], poisson.sf(2,lam))
        # Any capped/overflow cell contributes at least the failure threshold.
        for i, weight in enumerate(DEFAULT.weights):
            self.assertGreaterEqual(weight*DEFAULT.cap, DEFAULT.threshold)
        truth = joint_probabilities()
        expected = sum(p*math.exp(-4*lam)*(1+3*lam+lam*lam/2)
                       for p,lam in zip(DEFAULT.prior,DEFAULT.rates))
        self.assertAlmostEqual(sum(truth[i] for i in range(512) if accepted(i)), expected, places=14)
        self.assertAlmostEqual(dp_solution()[0], expected, places=14)
        self.assertAlmostEqual(truth.sum(), 1.)

    def test_independent_control_same_marginals_and_different_joint(self):
        pmf = sum(p*capped_pmf(r) for p,r in zip(DEFAULT.prior,DEFAULT.rates))
        joint = joint_probabilities()
        for site in range(4):
            marginal = np.zeros(4)
            for i,v in enumerate(joint): marginal[decode(i)[1][site]] += v
            np.testing.assert_allclose(marginal,pmf,atol=1e-14)
        self.assertGreater(dp_solution()[0], independent_control())

    def test_conditional_sampler_no_rejection_and_correct_law(self):
        z, maps = conditional_draws(20000,np.random.default_rng(99102))
        self.assertTrue(np.all(maps @ np.array(DEFAULT.weights)<DEFAULT.threshold))
        p = np.bincount([encode(a,b) for a,b in zip(z,maps)],minlength=512)/len(z)
        self.assertLess(summarize(p)['conditional_joint_tv'],.02)

    def test_readout_bit_order_and_normalization(self):
        p=np.zeros(512);p[1]=1
        q=apply_readout(p,.1)
        self.assertAlmostEqual(q[1],.9**9)
        self.assertAlmostEqual(q[0],.1*.9**8)
        self.assertAlmostEqual(q.sum(),1.)


class CircuitTests(unittest.TestCase):
    def test_preparation_all_512_amplitudes(self):
        state=Statevector.from_instruction(preparation())
        np.testing.assert_allclose(state.data,np.sqrt(joint_probabilities()),atol=1e-13)

    def test_oracle_marks_every_basis_component_and_uncomputes(self):
        # Unique complex coefficients expose permutation/phase errors, unlike
        # a uniform superposition. Each of 512 data components is populated.
        rng=np.random.default_rng(613)
        amplitudes=rng.normal(size=512)+1j*rng.normal(size=512)
        amplitudes/=np.linalg.norm(amplitudes)
        expected=amplitudes*np.array([-1 if accepted(i) else 1 for i in range(512)])
        for oracle in (enumerated_oracle(),counter_oracle()):
            initial=np.zeros(2**oracle.num_qubits,dtype=complex);initial[:512]=amplitudes
            actual=Statevector(initial).evolve(oracle).data
            np.testing.assert_allclose(actual[:512],expected,atol=1e-12)
            self.assertLess(np.linalg.norm(actual[512:]),1e-12)

    def test_weighted_adder_maps_all_populated_components(self):
        amp=np.arange(1,513,dtype=float);amp/=np.linalg.norm(amp)
        initial=np.zeros(16384,dtype=complex);initial[:512]=amp
        expected=np.zeros_like(initial)
        for i in range(512):
            score=sum(a*b for a,b in zip(DEFAULT.weights,decode(i)[1]))
            expected[i+(score<<9)]=amp[i]
        np.testing.assert_allclose(Statevector(initial).evolve(score_adder()).data,expected,atol=1e-12)

    def test_two_rounds_preserve_conditioned_maps(self):
        p=dp_solution()[0]
        for style in ('counter','enumerated'):
            row=ideal_case(2,style)
            self.assertAlmostEqual(row['ideal']['hit_probability'],math.sin(5*math.asin(math.sqrt(p)))**2,places=11)
            self.assertLess(row['ideal']['conditional_joint_tv'],1e-11)
            self.assertLess(row['dirty_workspace_probability'],1e-20)


if __name__=='__main__': unittest.main()
