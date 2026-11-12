from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from parameter_diagnostics import hessian
import inference_model as m


class DiagnosticsTests(unittest.TestCase):
    def test_hessian_against_analytic_nonlinear_function(self):
        matrix=np.array([[2.,.4,-.2],[.4,1.,.1],[-.2,.1,3.]])
        x=np.array([.2,-.3,.4])
        def function(z):
            return .5*z@matrix@z+np.logaddexp(0,z).sum()
        sigmoid=1/(1+np.exp(-x))
        expected=matrix+np.diag(sigmoid*(1-sigmoid))
        np.testing.assert_allclose(hessian(function,x,.0005),expected,atol=2e-7)

    def test_fixed_protocol_detuning_sign_is_global_alias(self):
        p=m.Parameters(n_cavity=2,defect_detuning=.3)
        from dataclasses import replace
        opposite=replace(p,defect_detuning=-.3)
        np.testing.assert_allclose(m.exact_distribution(p,steps=6)[1],
                                   m.exact_distribution(opposite,steps=6)[1],atol=1e-12)
        first=m.exact_distribution(p,control=(1.,.5),steps=6)[1]
        second=m.exact_distribution(opposite,control=(1.,.5),steps=6)[1]
        self.assertGreater(np.max(np.abs(first-second)),.001)


if __name__=='__main__':
    unittest.main()
