import unittest
from dataclasses import replace
import numpy as np
from scipy.linalg import expm
from math import comb
from phase_model import Setup,BIASES,OUTCOMES,quantum_probabilities,coherent_means,fisher_information,draw_records,estimate,estimate_hybrid,resources,wrap


class PhaseTests(unittest.TestCase):
    def test_probabilities_conserve_and_count_losses(self):
        phi=np.linspace(-np.pi,np.pi,31)
        for t,d,p in [(1,1,1),(.6,.7,.1),(0,1,.1),(1,0,1)]:
            s=Setup(t,d,p);q=quantum_probabilities(phi,s)
            np.testing.assert_allclose(q.sum(axis=-1),1,atol=1e-14)
            np.testing.assert_allclose(q@OUTCOMES.sum(axis=1),2*p*s.eta,atol=1e-14)
            np.testing.assert_allclose(coherent_means(phi,s).sum(axis=-1),2*s.eta,atol=1e-14)

    def test_independent_fock_beamsplitter_limit(self):
        a1=np.diag(np.sqrt([1.,2.]),1);a=np.kron(a1,np.eye(3));b=np.kron(np.eye(3),a1)
        unitary=expm(np.pi/4*(a.conj().T@b-a@b.conj().T))
        for phase in [.13,.35,.7,1.1]:
            psi=np.zeros(9,complex);psi[6]=1/np.sqrt(2);psi[2]=np.exp(2j*phase)/np.sqrt(2)
            measured=abs(unitary@psi)**2
            formula=quantum_probabilities(phase,Setup(1,1,1))[0,0]
            np.testing.assert_allclose(formula[[3,4,5]],measured[[6,2,4]],atol=1e-14)

    def test_known_fisher_limits_and_loss_scaling(self):
        for eta in [1,.8,.5,.1]:
            for p in [1,.1,.01]:
                s=Setup(eta,1,p)
                self.assertAlmostEqual(fisher_information('coherent',s),2*eta,places=7)
                self.assertAlmostEqual(fisher_information('noon',s),4*p*eta**2,places=7)
        self.assertEqual(fisher_information('noon',Setup(0,1,1)),0)

    def test_loss_matches_independent_binomial_thinning_of_fock_outputs(self):
        a1=np.diag(np.sqrt([1.,2.]),1);a=np.kron(a1,np.eye(3));b=np.kron(np.eye(3),a1)
        unitary=expm(np.pi/4*(a.conj().T@b-a@b.conj().T))
        for phase in [.17,.43,1.2]:
            psi=np.zeros(9,complex);psi[6]=1/np.sqrt(2);psi[2]=np.exp(2j*phase)/np.sqrt(2)
            ideal=abs(unitary@psi)**2
            for eta,p in [(.8,1),(.3,.1),(0,.01)]:
                expected=np.zeros(6);expected[0]=1-p
                for n0,n1 in [(2,0),(0,2),(1,1)]:
                    for index,(k0,k1) in enumerate(OUTCOMES):
                        if k0<=n0 and k1<=n1:
                            thin=comb(n0,k0)*comb(n1,k1)*eta**(k0+k1)*(1-eta)**(n0+n1-k0-k1)
                            expected[index]+=p*ideal[3*n0+n1]*thin
                np.testing.assert_allclose(expected,quantum_probabilities(phase,Setup(eta,1,p))[0,0],atol=1e-14)

    def test_charged_coarse_record_resolves_global_branch(self):
        rng=np.random.default_rng(227);s=Setup();truth=rng.uniform(-np.pi,np.pi,600)
        q=draw_records('noon',truth,s,9000,rng);c=draw_records('coherent',truth,s,1000,rng)
        joint=estimate_hybrid(q,c,s,'global',2048)
        pure=estimate('noon',q,s,'global',2048)
        self.assertLess(np.sqrt(np.mean(wrap(joint-truth)**2)),.012)
        self.assertGreater(np.mean(abs(wrap(pure-truth))>np.pi/2),.4)
        dose=resources('noon',s,9000)['sample_incident_mean_photons_before_object']+resources('coherent',s,1000)['sample_incident_mean_photons_before_object']
        self.assertEqual(dose,20000)

    def test_global_ambiguity_is_not_given_to_estimator(self):
        s=Setup()
        np.testing.assert_allclose(quantum_probabilities(.37,s),quantum_probabilities(.37+np.pi,s),atol=1e-14)
        self.assertGreater(np.max(abs(coherent_means(.37,s)-coherent_means(.37+np.pi,s))),.1)

    def test_sample_dose_counted_before_object_and_detector_loss(self):
        for t,d in [(1,1),(.1,.2)]:
            s=Setup(t,d,.01)
            self.assertEqual(resources('noon',s,1000000)['sample_incident_mean_photons_before_object'],20000)
            self.assertEqual(resources('coherent',s,10000)['sample_incident_mean_photons_before_object'],20000)

    def test_exact_finite_records_and_estimator_convergence(self):
        rng=np.random.default_rng(9324);s=Setup();truth=np.full(2000,.35)
        for method in ['noon','coherent']:
            counts=draw_records(method,truth,s,10000,rng)
            if method=='noon':np.testing.assert_array_equal(counts.sum(axis=2),np.full((2000,4),2500))
            estimates=estimate(method,counts,s,'local')
            rmse=np.sqrt(np.mean((estimates-truth)**2))
            bound=resources(method,s,10000)['local_unbiased_cramer_rao_sd']
            self.assertLess(abs(rmse/bound-1),.08)
            fine=estimate(method,counts[:100],s,'local',2048)
            self.assertLess(np.max(abs(fine-estimates[:100])),3e-5)

    def test_wrap_and_invalid_settings(self):
        self.assertAlmostEqual(float(wrap(2*np.pi+.1)),.1)
        with self.assertRaises(ValueError):Setup(-.1,1,1).validate()
        with self.assertRaises(ValueError):draw_records('noon',[.3],Setup(),7,np.random.default_rng(1))


if __name__=='__main__':unittest.main()
