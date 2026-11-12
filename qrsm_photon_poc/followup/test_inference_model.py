import itertools
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import inference_model as m
import qrsm_photon as original


class InstrumentTests(unittest.TestCase):
    def setUp(self):
        self.p=m.Parameters(n_cavity=2)

    def test_uncontrolled_matches_original(self):
        for got,wanted in zip(m.instrument(self.p),original.instruments(self.p)):
            np.testing.assert_allclose(got,wanted,atol=1e-11)

    def test_likelihood_sum_matches_original(self):
        x=original.sample_records(self.p,8,5,91)
        self.assertAlmostEqual(m.logs(x,self.p).sum(),original.record_loglikelihood(x,self.p),places=10)

    def test_deadtime_normalizes_and_forbids_adjacent_clicks(self):
        for control in [(1.,0.),(.8,-.5)]:
            bits,p=m.exact_distribution(self.p,control,6,dead_bins=1)
            self.assertAlmostEqual(p.sum(),1.,places=10)
            impossible=(bits[:,:-1]*bits[:,1:]).any(axis=1)
            np.testing.assert_array_equal(p[impossible],0.)

    def test_deadtime_evolves_unconditionally_in_blind_bin(self):
        no,yes,full=m.instrument(self.p)
        rho=original.init_state(self.p)
        expected=m.traces((yes@full@yes@rho)[:,None],8)[0]
        observed=np.exp(m.logs(np.array([[1,0,1]]),self.p,dead_bins=1)[0])
        self.assertAlmostEqual(observed,expected,places=12)

    def test_samples_agree_with_exact_records(self):
        bits,prob=m.exact_distribution(self.p,steps=4,dead_bins=1)
        records=m.sample(self.p,[(1.,0.)],20000,4,11881,dead_bins=1)[0]
        keys=(records*(1<<np.arange(4))).sum(axis=1)
        counts=np.bincount(keys,minlength=16)/len(records)
        self.assertLess(np.abs(prob-counts).max(),.015)
        self.assertFalse((records[:,:-1]*records[:,1:]).any())

    def test_control_preserves_trace_and_probability(self):
        for c in m.PROTOCOLS['controlled']:
            bits,p=m.exact_distribution(self.p,c,5)
            self.assertAlmostEqual(p.sum(),1.,places=10)
            self.assertGreaterEqual(p.min(),0)

    def test_parameter_coordinates_roundtrip(self):
        q=m.parameters(m.vector(self.p),self.p)
        for name in m.NAMES:
            self.assertAlmostEqual(getattr(q,name),getattr(self.p,name))


if __name__=='__main__':
    unittest.main()
