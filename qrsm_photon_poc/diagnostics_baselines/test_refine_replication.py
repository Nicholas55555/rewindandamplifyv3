"""Verify HMM gradient and training-only local refinement."""
import unittest

import numpy as np

if __package__:
    from .compare import hmm_likelihood_and_stats
    from .refine_replication import objective_gradient, pack, refine_hmm, unpack
else:
    from compare import hmm_likelihood_and_stats
    from refine_replication import objective_gradient, pack, refine_hmm, unpack


class RefinementTests(unittest.TestCase):
    def setUp(self):
        self.records=np.random.default_rng(18).binomial(1,.3,size=(25,9))
        self.initial=np.array([.4,.35,.25])
        self.transition=np.array([[.5,.3,.2],[.2,.65,.15],[.1,.3,.6]])
        self.emissions=np.array([.1,.35,.7])

    def test_pack_unpack_round_trip(self):
        decoded=unpack(pack(self.initial,self.transition,self.emissions),3)
        for actual,expected in zip(decoded,(self.initial,self.transition,self.emissions)):
            np.testing.assert_allclose(actual,expected,atol=1e-12)

    def test_gradient_against_finite_difference(self):
        vector=pack(self.initial,self.transition,self.emissions)
        value,analytic=objective_gradient(vector,self.records,3)
        eps=1e-5
        numeric=np.empty_like(vector)
        for i in range(len(vector)):
            step=np.zeros_like(vector);step[i]=eps
            numeric[i]=(objective_gradient(vector+step,self.records,3)[0]-
                        objective_gradient(vector-step,self.records,3)[0])/(2*eps)
        np.testing.assert_allclose(analytic,numeric,atol=1e-6,rtol=1e-6)

    def test_refinement_never_reduces_training_likelihood(self):
        before=hmm_likelihood_and_stats(self.records,self.initial,self.transition,self.emissions).sum()
        params,info=refine_hmm(self.records,self.initial,self.transition,self.emissions,max_iter=30)
        after=hmm_likelihood_and_stats(self.records,*params).sum()
        self.assertGreaterEqual(after,before)
        self.assertAlmostEqual(after,info['train_selected'])


if __name__=='__main__':
    unittest.main()
