"""Offline scientific analysis tests, including noncontiguous loop bitmaps."""
import math
import unittest
from unittest.mock import patch

import numpy as np

from analyze import (counts_array, wilson, marginal, ideal_sampling_tv,
                     original_observables, dot_observables, calibration_summary,
                     secondary_readout_inverse, load_optical_analyzer)
from analyze import sparse_counts,sparse_marginal_counts,extension_observables


class HardwareAnalysisTests(unittest.TestCase):
    def test_29_qubit_projection_never_allocates_full_hilbert_space(self):
        qubits=[0,5,12,20,28]
        counts={format(0,'029b'):50,format(1<<28,'029b'):30,
                format(sum(1<<q for q in qubits),'029b'):20}
        original_zeros=np.zeros;allocations=[]
        def bounded_zeros(shape,*args,**kwargs):
            self.assertLessEqual(int(np.prod(shape)),1024)
            allocations.append(shape);return original_zeros(shape,*args,**kwargs)
        with patch('analyze.np.zeros',side_effect=bounded_zeros):
            result=sparse_marginal_counts(counts,29,qubits)
        self.assertEqual(result.shape,(32,));self.assertEqual(result[0],50)
        self.assertEqual(result[16],30);self.assertEqual(result[31],20)
        with self.assertRaises(ValueError):counts_array(counts,29)
        row={'metadata':{'kind':'sequential_emitter_environment_joint_photon_instrument',
                         'flag_qubits':qubits[1:],'memory_qubit':0,'memory_readout_basis':'Z'}}
        scored=dot_observables(result/100,row,result/100,100,qubits)
        self.assertEqual(scored['histories']['0001']['observed']['successes'],30)
        self.assertEqual(scored['histories']['1111']['conditional_memory_zero']['successes'],0)
        self.assertEqual(scored['histories']['1111']['conditional_memory_zero']['shots'],20)

    def test_29_qubit_calibration_is_sparse(self):
        all_ones=(1<<29)-1
        rows=[{'kind':'calibration','name':'cal_zero','measurement_physical_qubits':list(range(100,129)),
               'prepared_bits':[0]*29,'counts':{format(0,'029b'):990,format(1<<28,'029b'):10}},
              {'kind':'calibration','name':'cal_one','measurement_physical_qubits':list(range(100,129)),
               'prepared_bits':[1]*29,'counts':{format(all_ones,'029b'):950,format(all_ones^(1<<28),'029b'):50}}]
        with patch('analyze.counts_array',side_effect=AssertionError('No dense calibration allocation')):
            result=calibration_summary(rows)
        self.assertAlmostEqual(result['independent_bit_error_estimates']['128']['e01']['probability'],.01)
        self.assertAlmostEqual(result['independent_bit_error_estimates']['128']['e10']['probability'],.05)

    def test_extension_workspace_is_reported_without_postselection(self):
        base=np.array([.8**i.bit_count()*.2**(3-i.bit_count()) for i in range(8)])
        marked=[0,1,2,4];p=base[marked].sum();ideal=np.r_[base,np.zeros(8)]
        row={'metadata':{'family':'independent_contact','data_qubits':[0,1,2],'workspace_qubits':[3],
                         'marked_data_indices':marked,'conditional_data_target':(base[marked]/p).tolist(),'scope':'synthetic'}}
        observed=np.zeros(16);observed[8]=1
        result=extension_observables(observed,row,ideal,1000)
        self.assertEqual(result['selected']['successes'],1000)
        self.assertEqual(result['workspace_dirty']['successes'],1000)
        self.assertFalse(result['workspace_postselection_applied'])

    def test_independent_count_contrast_is_symmetric_and_bounded(self):
        from feasibility.contrast_analysis import difference
        a=difference(80,100,50,100);b=difference(50,100,80,100)
        self.assertAlmostEqual(a['probability_difference'],.3)
        self.assertGreater(a['independent_shot_wilson_based_interval95'][0],0.)
        np.testing.assert_allclose(a['independent_shot_wilson_based_interval95'],[-x for x in b['independent_shot_wilson_based_interval95'][::-1]])
        endpoint=difference(100,100,0,100)['independent_shot_wilson_based_interval95']
        self.assertGreater(endpoint[0],.9);self.assertEqual(endpoint[1],1.)
        with self.assertRaises(ValueError):difference(0,0,1,1)

    def test_count_bit_order_and_invalid_records(self):
        np.testing.assert_array_equal(counts_array({'10':3,'0x1':2,'0 0':1},2),[1,2,3,0])
        for counts in ({},{'00':1.2},{'00':True},{'100':1}):
            with self.assertRaises(ValueError):counts_array(counts,2)

    def test_wilson_zero_count_is_not_zero_upper_bound(self):
        self.assertGreater(wilson(0,100)[1],.03)
        self.assertIsNone(wilson(0,0))

    def test_expected_tv_formula_against_exact_binomial_sum(self):
        for shots in (1,2,5,12):
            for p in (.01,.2,.5,.93):
                exact=sum(math.comb(shots,k)*p**k*(1-p)**(shots-k)*abs(k/shots-p) for k in range(shots+1))
                self.assertAlmostEqual(ideal_sampling_tv([p,1-p],shots),exact,places=13)
        self.assertEqual(ideal_sampling_tv([1+1e-14,0],100),0.)

    def test_loop_uses_explicit_history_bitmap_across_ancilla_gap(self):
        # q0 memory, q1 first history, q2 second/selected history,
        # q3 uncompute ancilla, q4 future history. q3 must never be step3.
        p=np.zeros(32);p[0b00100]=.3;p[0b10100]=.2;p[0b01000]=.5
        mapping=[1,2,4]
        target=marginal(p,mapping)
        row={'metadata':{'kind':'loop','t0':2,'tau':1},
             'reference':{'chronological_history_qubits':mapping,'unsteered_history_probabilities':target.tolist()}}
        result=original_observables(p,row,p,100)
        self.assertEqual(result['selected']['successes'],50)
        future=result['future_clicks_after_selected_click'][0]
        self.assertEqual(future['step'],3)
        self.assertAlmostEqual(future['raw_or_secondary_conditional']['probability'],.4)
        self.assertEqual(future['raw_or_secondary_conditional']['successes'],20)
        self.assertEqual(future['raw_or_secondary_conditional']['shots'],50)

    def test_empty_selected_history_has_no_invented_conditional_answer(self):
        p=np.array([1.,0.,0.,0.]);ideal=np.array([.5,0.,.5,0.])
        row={'metadata':{'kind':'history','question':'click at step1'},'reference':{}}
        row['metadata']['question']='click at step 1'
        row['reference']={'chronological_history_qubits':[1], 'unsteered_history_probabilities':[.5,.5]}
        result=original_observables(p,row,ideal,100)
        self.assertIsNone(result['selected_history_tv_to_unsteered_target'])
        self.assertEqual(result['selected']['successes'],0)

    def test_original_logical_bias_is_separate_from_hardware_error(self):
        ideal=np.array([.1,.2,.3,.4]);target=[.5,.1,.1,.3]
        row={'metadata':{'kind':'history','question':'any click'},
             'reference':{'chronological_history_qubits':[0,1],'unsteered_history_probabilities':target}}
        result=original_observables(ideal,row,ideal,100)
        self.assertEqual(result['selected_history_tv_to_logical_ideal'],0.)
        self.assertGreater(result['logical_ideal_selected_history_bias_vs_unsteered'],.1)

    def test_dot_memory_basis_conditioning_and_empty_flag(self):
        # q0 memory, q2 flag; the other qubit is a retained environment.
        p=np.zeros(8);p[0]=.5;p[4]=.4;p[5]=.1
        row={'metadata':{'kind':'sequential_emitter_environment_joint_photon_instrument',
                         'flag_qubits':[2],'memory_qubit':0,'memory_readout_basis':'Y'}}
        result=dot_observables(p,row,p,100)
        stat=result['histories']['1']['conditional_memory_zero']
        self.assertEqual(stat['shots'],50);self.assertEqual(stat['successes'],40)
        self.assertAlmostEqual(result['histories']['1']['conditional_memory_pauli'],.6)
        self.assertEqual(result['memory_measurement_basis'],'Y')

    def test_frozen_overlap_is_not_clipped_to_supported_model_range(self):
        row={'metadata':{'kind':'frozen_classical_pair_memory_benchmark','flag_qubits':[0], 'expected_overlap':1.}}
        result=dot_observables([.2,.8],row,[1.,0.],100)
        self.assertAlmostEqual(result['raw_swap_overlap_estimate'],-.6)

    def calibration(self):
        # Different final physical order in zero/one controls.
        return calibration_summary([
            {'kind':'calibration','name':'cal_zero','measurement_physical_qubits':[7,3],
             'prepared_bits':[0,0],'counts':{'00':72,'01':8,'10':18,'11':2}},
            {'kind':'calibration','name':'cal_one','measurement_physical_qubits':[3,7],
             'prepared_bits':[1,1],'counts':{'00':12,'01':28,'10':18,'11':42}}])

    def test_calibration_tracks_physical_qubits_not_classical_positions(self):
        rates=self.calibration()['independent_bit_error_estimates']
        self.assertAlmostEqual(rates['7']['e01']['probability'],.1)
        self.assertAlmostEqual(rates['3']['e01']['probability'],.2)
        self.assertAlmostEqual(rates['7']['e10']['probability'],.4)
        self.assertAlmostEqual(rates['3']['e10']['probability'],.3)

    def test_assignment_inverse_recovers_known_independent_channel(self):
        target=np.array([.1,.2,.3,.4]);cal=self.calibration()
        a=np.array([[.9,.4],[.1,.6]]);b=np.array([[.8,.3],[.2,.7]])
        observed=np.kron(b,a)@target
        result,report=secondary_readout_inverse(observed,[7,3],cal)
        np.testing.assert_allclose(result,target,atol=1e-14)
        self.assertEqual(report['status'],'secondary_sensitivity_only')
        self.assertIn('not a confidence',report['interval'])

    def test_readout_inverse_reports_projection_and_missing_calibration(self):
        cal=self.calibration();corrected,report=secondary_readout_inverse([1.,0.,0.,0.],[7,3],cal)
        self.assertGreater(report['negative_mass_before_projection'],0)
        self.assertAlmostEqual(sum(corrected),1)
        unavailable,report=secondary_readout_inverse([1.,0.],[99],cal)
        self.assertIsNone(unavailable);self.assertEqual(report['status'],'unavailable')

    def test_optical_helper_import_does_not_shadow_other_models(self):
        import sys
        before=sys.modules.get('models')
        module=load_optical_analyzer()
        self.assertIs(sys.modules.get('models'),before)
        self.assertTrue(callable(module.score_counts))


if __name__=='__main__':unittest.main()
