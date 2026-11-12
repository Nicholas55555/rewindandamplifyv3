import unittest
from dataclasses import replace
import numpy as np
from scipy.stats import poisson
from qiskit import QuantumCircuit
from qiskit.circuit.library import Isometry
from qiskit.quantum_info import Statevector, DensityMatrix, partial_trace
from models import *


class OpticalControlsTests(unittest.TestCase):
    def test_lindblad_trace_cp_and_independent_bloch_all_inputs(self):
        for cfg,delta,power in [(AtomicConfig(),d,p) for d in [-5,-.5,0,.5,5] for p in [1.,1.1]]+[(replace(AtomicConfig(),t2_s=.02),5,1.)]:
            channel=atomic_channel(delta,power,cfg)
            v,ks,eig=channel_isometry(channel)
            np.testing.assert_allclose(v.conj().T@v,np.eye(2),atol=2e-13)
            self.assertGreaterEqual(eig.min(),-1e-13)
            for axis in np.eye(3):
                for sign in [-1,1]:
                    r=sign*axis;rho=(I2+r[0]*X+r[1]*Y+r[2]*Z)/2
                    expected=bloch_reference(delta,power,cfg,r)
                    actual=apply_channel(channel,rho)
                    np.testing.assert_allclose([np.trace(actual@s).real for s in [X,Y,Z]],expected,atol=2e-12)
                    np.testing.assert_allclose(sum(k@rho@k.conj().T for k in ks),actual,atol=1e-13)

    def test_isometry_implements_arbitrary_inputs_not_only_excitation(self):
        v,_,_=channel_isometry(atomic_channel(.5))
        for amps in [[1,0],[0,1],[1/np.sqrt(2),1/np.sqrt(2)],[1/np.sqrt(2),1j/np.sqrt(2)]]:
            qc=QuantumCircuit(3);qc.initialize(amps,0);qc.append(Isometry(v,0,0),[0,1,2])
            result=partial_trace(Statevector.from_instruction(qc),[1,2]).data
            target=apply_channel(atomic_channel(.5),np.outer(amps,np.conj(amps)))
            np.testing.assert_allclose(result,target,atol=1e-12)

    def test_initial_preparation_and_tomography(self):
        cfg=AtomicConfig();r=bloch_reference(.5,config=cfg)
        for idx,basis in enumerate('XYZ'):
            qc=atomic_circuit(.5,basis=basis)
            probs=Statevector.from_instruction(qc).probabilities()
            measured_z=sum(p*(1 if i%2==0 else -1) for i,p in enumerate(probs))
            self.assertAlmostEqual(measured_z,r[idx],places=11)

    def test_fock_reference_exact_all_number_outputs(self):
        for kind,n in [('noon',2),('mixture',2),('coherent_sector',1),('coherent_sector',2),('coherent_sector',3),('coherent_sector',5)]:
            for phase,eta,p in [(0,1,1),(.35,.81,1),(np.pi/4,.48,.1),(1.1,0,1)]:
                qc=photon_circuit(n,phase,eta,kind,p)
                actual=aggregated_photon_probabilities(Statevector.from_instruction(qc).probabilities(),n)
                expected=fock_reference(n,phase,eta,kind,p)
                for k in expected:self.assertAlmostEqual(actual.get(k,0),expected[k],places=11)
                self.assertAlmostEqual(sum(actual.values()),1,places=11)
                moments=photon_moments(actual)
                self.assertAlmostEqual(moments['mean_a']+moments['mean_b'],n*p*eta,places=11)

    def test_noon_known_probability_and_pi_alias(self):
        for phi in [.2,.35,1.1]:
            d=fock_reference(2,phi,.81,'noon')
            self.assertAlmostEqual(d[(1,1)],.81**2*(1-np.cos(2*phi))/2,places=12)
            alias=fock_reference(2,phi+np.pi,.81,'noon')
            np.testing.assert_allclose(list(d.values()),list(alias.values()),atol=1e-14)
        a=fock_reference(2,.35,.81);b=fock_reference(2,.35+np.pi,.81)
        self.assertGreater(max(abs(a[k]-b[k]) for k in a),.1)

    def test_coherent_sector_mixture_and_tail_accounting(self):
        tail=coherent_tail();self.assertAlmostEqual(sum(tail['weights'])+tail['omitted_probability'],1,places=13)
        self.assertAlmostEqual(tail['omitted_probability'],poisson.sf(8,2),places=15)
        for phi in [.35,.35+np.pi]:
            actual={}
            for n,w in enumerate(tail['weights']):
                d={(0,0):1.} if n==0 else fock_reference(n,phi,.81)
                for k,v in d.items():actual[k]=actual.get(k,0.)+w*v
            mu=[.81*(1+np.cos(phi)),.81*(1-np.cos(phi))]
            # Original probability mass remains below1: no silent normalization.
            self.assertAlmostEqual(sum(actual.values()),1-tail['omitted_probability'],places=13)
            error=sum(abs(v-poisson.pmf(k[0],mu[0])*poisson.pmf(k[1],mu[1])) for k,v in actual.items())
            self.assertLessEqual(error,tail['omitted_probability']+1e-12)
            m=photon_moments(actual)
            self.assertLessEqual(abs(m['mean_a']-mu[0]),.81*tail['omitted_first_photon_moment']+1e-12)
            self.assertLessEqual(abs(m['factorial2_a']-mu[0]**2),.81**2*tail['omitted_second_factorial_photon_moment']+1e-12)

    def test_normalized_output_exposure_moments(self):
        for phi in [0,np.pi/4,np.pi/2]:
            m=photon_moments(fock_reference(2,phi,.8,'noon'))
            self.assertAlmostEqual(m['mean_a'],.8,places=12)
            self.assertAlmostEqual(m['factorial2_a'],.8**2*(1+np.cos(2*phi))/2,places=12)
            mm=photon_moments(fock_reference(2,phi,.8,'mixture'))
            self.assertAlmostEqual(mm['factorial2_a'],.8**2/2,places=12)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):atomic_channel(.5,0)
        with self.assertRaises(ValueError):atomic_channel(.5,config=replace(AtomicConfig(),t2_s=201))
        with self.assertRaises(ValueError):photon_circuit(2,0,1.1)
        with self.assertRaises(ValueError):photon_circuit(1,0,kind='noon')


if __name__=='__main__':unittest.main()
