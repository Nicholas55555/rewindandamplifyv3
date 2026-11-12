"""Tests for closed-form conditional sampling and multiround circuits."""
import math
import random
import unittest

import numpy as np
from qiskit.quantum_info import Statevector

from lithography import exact_distribution
from oracle_comparison import amplified_circuit
from oracle_density_pilot import score_probabilities
from viability_cost_study import conditional_distribution, exact_conditional_draw, make_circuit


class ViabilityCostTests(unittest.TestCase):
    def test_closed_form_matches_exact_enumeration(self):
        for n in range(2,9):
            for p in (.1,.5,.8,.95):
                a=exact_distribution(n,p,2)['conditional_histories']
                b=conditional_distribution(n,p)
                self.assertEqual(a.keys(),b.keys())
                self.assertAlmostEqual(sum(b.values()),1.0)
                for k in a:self.assertAlmostEqual(a[k],b[k],places=13)

    def test_direct_sampler_matches_probability_and_never_rejects(self):
        n,p=5,.8
        truth=conditional_distribution(n,p)
        rng=random.Random(192)
        draws=[exact_conditional_draw(n,p,rng) for _ in range(20000)]
        self.assertEqual(len(draws),20000)
        self.assertTrue(all(x.count('1')<2 for x in draws))
        self.assertLess(sum(abs(draws.count(k)/len(draws)-v) for k,v in truth.items())/2,.025)

    def test_multiround_ideal_probabilities_and_conditional_law(self):
        n,p=5,.8
        p0=exact_distribution(n,p,2)['failure_probability']
        for style in ('enumerated','counter'):
            for r in (0,1,2,3):
                qc=make_circuit(n,p,style,r)
                measured=Statevector.from_instruction(qc).probabilities(list(range(n)))
                score=score_probabilities(measured,n,p)
                self.assertAlmostEqual(score['hit_probability'],math.sin((2*r+1)*math.asin(math.sqrt(p0)))**2,places=11)
                self.assertLess(score['conditional_tv'],1e-11)

    def test_one_round_matches_existing_circuit(self):
        for style in ('enumerated','counter'):
            existing,_=amplified_circuit(5,.8,style)
            a=Statevector.from_instruction(existing).data
            b=Statevector.from_instruction(make_circuit(5,.8,style,1)).data
            overlap=np.vdot(a,b)
            np.testing.assert_allclose(b,overlap/abs(overlap)*a,atol=1e-12)

    def test_input_validation(self):
        for n,p in [(1,.8),(5,1),(5,0),(5,float('nan'))]:
            with self.assertRaises(ValueError): conditional_distribution(n,p)
        with self.assertRaises(ValueError):make_circuit(5,.8,'bad',1)
        with self.assertRaises(ValueError):make_circuit(5,.8,'counter',-1)


if __name__=='__main__': unittest.main()
