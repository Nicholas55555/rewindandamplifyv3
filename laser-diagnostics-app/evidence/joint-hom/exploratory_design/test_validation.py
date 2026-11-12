import unittest
import numpy as np
from dataclasses import replace
from design import Parameters,distribution
from validation import BLOCKS,block_indices,fit_categorical,namespaces,fit_hmm,normalized
from inference import log_likelihood,hmm_score


class Tests(unittest.TestCase):
    def test_invalid_probability_law_fails(self):
        for p in [[np.nan,1.],[-.01,1.01],[.2,.2]]:
            with self.assertRaises(ValueError):normalized(p)

    def test_indexing_and_count_score(self):
        np.testing.assert_array_equal(block_indices(BLOCKS),np.arange(81))
        p=Parameters(theta=3*np.pi/4);controls=[2.]*4
        probs=distribution(p,controls)
        np.testing.assert_allclose(np.log(probs),log_likelihood(p,controls,BLOCKS),atol=1e-13)
        counts=np.arange(81)%4
        explicit=np.repeat(BLOCKS,counts,axis=0)
        self.assertAlmostEqual(counts@np.log(probs),log_likelihood(p,controls,explicit).sum())

    def test_namespaces_unique(self):
        ns=namespaces();self.assertEqual(len(ns),len(set(ns)));self.assertEqual(len(ns),73)

    def test_categorical_fit_and_hmm_normalization(self):
        records=np.tile(BLOCKS,(2,1));model=fit_categorical(records)
        np.testing.assert_allclose(model,np.ones(81)/81)
        fitted,report=fit_hmm(records,4,starts=2,max_iterations=8)
        law=np.exp(hmm_score(fitted,BLOCKS,np.zeros(4,dtype=int)))
        self.assertAlmostEqual(law.sum(),1.)
        self.assertTrue(np.all(np.diff(report['training_trace'])>=-1e-8))


if __name__=='__main__':unittest.main()
