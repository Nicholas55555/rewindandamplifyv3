"""Checks independent of the rare-event reference and variance claims."""
import unittest
import numpy as np
from scipy.stats import poisson
from spatial_coverage import (lattice_cdf,response_weights,reference_bounds,
                              sample,tune,coverage_summary,wilson,response,fft_check)


class CoverageTests(unittest.TestCase):
    def test_lattice_recurrence_matches_poisson_closed_form(self):
        for lam in (.1,2.,10.):
            for threshold in (1,3,20):
                self.assertAlmostEqual(lattice_cdf([1,1],[lam/3,2*lam/3],threshold),
                                       poisson.cdf(threshold-1,lam),places=13)

    def test_nonunit_weights_and_zero_weight_tail(self):
        # Exact independent double sum, and ignored zero-weight Poisson tail.
        expected=sum(poisson.pmf(a,.7)*poisson.pmf(b,1.1)
                     for a in range(7) for b in range(4) if a+2*b<7)
        self.assertAlmostEqual(lattice_cdf([1,2,0],[.7,1.1,100.],7),expected,places=13)

    def test_linear_response_matches_original_for_random_maps(self):
        maps=np.random.default_rng(198).poisson(2.,size=(50,7,7))
        np.testing.assert_allclose(response(maps)[1],maps.reshape(-1,49)@response_weights(),atol=2e-15)

    def test_rounding_bounds_contain_known_nonlattice_probability(self):
        # .21*N1+.37*N2<.8, direct sum covers every accepted count.
        truth=sum(poisson.pmf(a,1.5)*poisson.pmf(b,1.5)
                  for a in range(4) for b in range(3) if .21*a+.37*b<.8)
        for cutoff in (10,100,1000):
            ref=reference_bounds(1.5,cutoff,weights=np.array([.21,.37]))
            self.assertLessEqual(ref['lower'],truth+1e-14)
            self.assertGreaterEqual(ref['upper'],truth-1e-14)

    def test_longdouble_and_float64_recurrence_agree(self):
        weights=np.floor(response_weights()/.8*10000).astype(int)
        rates=np.full(49,1.8)
        self.assertLess(abs(lattice_cdf(weights,rates,10000)-
                            lattice_cdf(weights,rates,10000,dtype=np.longdouble)),1e-14)

    def test_fft_inversion_agrees_with_recurrence_and_negligible_alias(self):
        result=fft_check(1.8)
        self.assertLess(result['absolute_disagreement'],1e-12)
        self.assertLess(result['log_chernoff_upper_bound_on_wraparound'],-100)

    def test_no_tilt_monte_carlo_matches_known_poisson_event(self):
        weights=np.zeros(49);weights[0]=1
        rates=np.ones(49)
        row=sample(rates,1.,weights,30000,617,threshold=1,direct=True)
        truth=np.exp(-1)
        self.assertLess(abs(row['estimate']-truth),5*row['se'])

    def test_pilot_respects_nondefault_threshold(self):
        # One active cell: threshold 1.2 accepts N=0,1; the default .8 would
        # accept only N=0 and give a clearly different target probability.
        weights=np.zeros(49);weights[0]=1
        _,report=tune(1.5,weights,pilot_shots=5000,seed=9910,threshold=1.2)
        truth=poisson.cdf(1,1.5)
        for row in report['candidates']:
            self.assertLess(abs(row['estimate']-truth),5*row['se'])

    def test_coverage_bracket_and_zero_hit_interval(self):
        self.assertGreater(wilson(0,100)[1],0)
        rows=[{'estimate':.2,'se':.01,'interval95':[.1,.3],'hits':2,'event_weight_ess':2},
              {'estimate':.3,'se':.01,'interval95':[.2,.4],'hits':3,'event_weight_ess':3}]
        summary=coverage_summary(rows,{'lower':.19,'upper':.21})
        self.assertEqual(summary['coverage95_fraction_bounds'],[.5,1.])


if __name__=='__main__':unittest.main()
