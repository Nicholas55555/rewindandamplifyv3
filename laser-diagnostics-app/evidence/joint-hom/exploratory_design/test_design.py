import itertools
import math
import unittest
import numpy as np
from dataclasses import replace
from design import Parameters,distribution,information,settings


class Tests(unittest.TestCase):
    def test_grid(self):
        self.assertEqual(len(list(settings())),648)

    def test_passive_and_single_pair(self):
        for theta in [0.,.4,np.pi/2,np.pi]:
            p=Parameters(theta=theta);q=replace(p,gap_dephasing=1.)
            np.testing.assert_allclose(distribution(p,[0.]*4),distribution(q,[0.]*4),atol=3e-14)
            for shift in [0.,.5,2.,4.]:
                np.testing.assert_allclose(distribution(p,[shift]),distribution(q,[shift]),atol=3e-14)

    def test_bosonic_probability_distribution(self):
        for d in [0.,1.]:
            p=Parameters(theta=.7,gap_dephasing=d)
            a=distribution(p,[2.,-2.,2.,-2.]);b=distribution(p,[2.,-2.,2.,-2.],True)
            np.testing.assert_allclose(a,b,atol=3e-14)
            self.assertAlmostEqual(a.sum(),1.)
            self.assertGreaterEqual(a.min(),-1e-14)

    def test_likelihood_moments_and_bound(self):
        p=np.array([.8,.2]);q=np.array([.3,.7]);s=information(p,q)
        self.assertAlmostEqual(s['llr_mean_quantum'],sum(p*np.log(p/q)))
        self.assertAlmostEqual(s['bhattacharyya_coefficient'],sum(np.sqrt(p*q)))
        n=s['sufficient_independent_blocks_alpha05_power80'];cut=s['rigorous_llr_threshold']
        false=miss=0.
        # Exchangeable binomial enumeration is independent of the bound formula.
        for k in range(n+1):
            score=k*np.log(p[0]/q[0])+(n-k)*np.log(p[1]/q[1])
            cp=math.comb(n,k)*q[0]**k*q[1]**(n-k)
            qp=math.comb(n,k)*p[0]**k*p[1]**(n-k)
            false+=cp*(score>=cut);miss+=qp*(score<cut)
        self.assertLessEqual(false,.05);self.assertLessEqual(miss,.20)

    def test_zero_information(self):
        s=information([.2,.8],[.2,.8])
        self.assertIsNone(s['sufficient_independent_blocks_alpha05_power80'])
        self.assertEqual(s['total_variation'],0.)


if __name__=='__main__':unittest.main()
