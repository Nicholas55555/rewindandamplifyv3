import unittest
import numpy as np
from analyze_counts import parsed_counts,score_counts,aggregate_coherent_sector_scores
from models import coherent_tail


class AnalysisTests(unittest.TestCase):
    def test_no_postselection_on_source_loss(self):
        row={'name':'probe','num_qubits':5,'metadata':{'family':'photon_noon_or_mixture','photons_if_prepared':2},
             'reference':{'occupancy_probabilities':{'0,0':.5,'2,0':.5},
                          'moments':{'mean_a':1.,'mean_b':0.,'factorial2_a':1.,'factorial2_b':0.,'cross_ab':0.}}}
        result=score_counts({'10000':50,'00000':50},row)
        self.assertEqual(result['shots'],100)
        self.assertEqual(result['raw_moments']['mean_a']['mean'],1.)
        self.assertEqual(result['source_flag_failure_fraction'],.5)
        self.assertEqual(result['occupancy_tv'],0)

    def test_atomic_ground_is_one(self):
        row={'name':'a','num_qubits':4,'metadata':{'family':'atomic_finite_pulse','basis':'Z'},
             'reference':{'system_probability_zero_in_measurement_basis':.3}}
        result=score_counts({'0000':30,'0001':70},row)
        self.assertAlmostEqual(result['raw_pauli_expectation'],-.4)
        self.assertEqual(result['absolute_probability_error'],0)

    def test_missing_sectors_remain_missing(self):
        t=coherent_tail();rows=[{'name':'n1','metadata':{'family':'photon_coherent_sector',
              'phase_rad':.35,'photons_if_prepared':1,'poisson_weight':t['weights'][1]}}]
        result=aggregate_coherent_sector_scores([],rows,t)[0]
        self.assertEqual(result['missing_requested_sectors'],[1])
        self.assertEqual(result['retained_occupancy_mass'],t['weights'][0])
        self.assertEqual(result['unmeasured_requested_weight'],t['weights'][1])

    def test_counts_are_bounded_nonnegative_integer(self):
        for c in [{},{'100':1},{'01':-.2},{'01':True}]:
            with self.assertRaises(ValueError):parsed_counts(c,2)
        self.assertEqual(parsed_counts({'0x2':3,'10':2},2),{2:5})


if __name__=='__main__':unittest.main()
