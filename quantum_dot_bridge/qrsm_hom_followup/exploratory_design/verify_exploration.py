"""Replay exact exploratory design, prospective sampled records and their scores."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import numpy as np
from design import Parameters,setting,settings,distribution
from validation import (BLOCKS,BUDGETS,rng,normalized,sample_blocks,block_indices,fit_categorical,
                        fit_hmm,namespaces)
from inference import hmm_score,mean_interval,wilson

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--refit',action='store_true');args=parser.parse_args()
    design=json.loads((HERE/'design_results.json').read_text(encoding='utf-8'))
    for n,h in design['source_sha256'].items():assert digest(HERE/n)==h,n
    for old,(theta,a,label,controls) in zip(design['all_settings'],settings(),strict=True):
        new=setting(Parameters(theta=theta),controls)
        for field in ['probabilities_quantum','probabilities_classical']:
            np.testing.assert_allclose(new[field],old[field],atol=1e-13)
        for name,value in new['information'].items():
            if value is None:assert old['information'][name] is None
            else:np.testing.assert_allclose(value,old['information'][name],atol=1e-12)
    assert max(design['all_settings'],key=lambda r:r['score_nats_per_attempted_pair'])==design['selected']
    folder=HERE/'validation_run';r=json.loads((folder/'results.json').read_text(encoding='utf-8'))
    provenance=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    assert provenance==r['provenance']
    for n,h in provenance['source_sha256'].items():assert digest(HERE/n)==h,n
    assert digest(HERE/'design_results.json')==provenance['design_results_sha256']
    assert digest(folder/'records.npz')==r['records_sha256']
    assert provenance['rng_namespaces']==[list(n) for n in namespaces()]
    raw=np.load(folder/'records.npz',allow_pickle=False)
    nominal=Parameters(**r['parameters']);controls=r['controls_over_gamma']
    counts=[int(rng(1,i).binomial(20000,p)) for i,p in enumerate([.01,.02,.8])]
    assert counts==r['calibration']['counts']
    estimated=dict(zip(['e01','e10','eta'],np.array(counts)/20000))
    assert estimated==r['calibration']['estimated']
    fitted=replace(nominal,**estimated)
    p=normalized(distribution(nominal,controls));q=normalized(distribution(replace(nominal,gap_dephasing=1.),controls))
    fitp=normalized(distribution(fitted,controls));fitq=normalized(distribution(replace(fitted,gap_dephasing=1.),controls))
    llr=np.log(fitp/fitq);exact_llr=np.log(p/q)
    training=sample_blocks(p,20000,(2,));heldout=sample_blocks(p,20000,(3,))
    np.testing.assert_array_equal(training,raw['predictor_training_blocks'])
    np.testing.assert_array_equal(heldout,raw['predictor_heldout_blocks'])
    candidates={'physical_coherent_calibrated':fitp,'physical_classical_calibrated':fitq,
                'exact_classical_categorical_oracle':p,'saturated_categorical_fit':fit_categorical(training)}
    for report in r['classical_hmms']:
        model={k:np.array(v) for k,v in report['model'].items()}
        if args.refit:
            fitted_hmm,new=fit_hmm(training,report['states'])
            for k,v in model.items():np.testing.assert_allclose(fitted_hmm[k],v,rtol=1e-9,atol=1e-11)
            assert new['start']==report['start']
        candidates[f'hmm_{report["states"]}']=np.exp(hmm_score(model,BLOCKS,np.zeros(4,dtype=int)))
    indices=block_indices(heldout);ref=np.log(fitp[indices])/4
    for name,law in candidates.items():
        saved=r['prediction_scores'][name]
        np.testing.assert_allclose(law,saved['block_probabilities'],atol=1e-13)
        values=np.log(law[indices])/4
        np.testing.assert_allclose(values,raw[f'prediction_{name}'],atol=1e-13)
        assert mean_interval(values)==saved['log_score_nats_per_attempted_pair']
        assert mean_interval(values-ref)==saved['paired_gain_vs_calibrated_physical']
    usable=(BLOCKS>0).sum(axis=1)
    for j,trial in enumerate(r['power_trials']):
        budget=BUDGETS[j];assert trial['independent_blocks']==budget
        calibration=rng(4,j).multinomial(budget,q,size=2000)
        np.testing.assert_array_equal(calibration,raw[f'blocks{budget}_null_calibration_counts'])
        threshold=float(np.sort(calibration@llr)[1900]);assert threshold==trial['threshold_calibrated']
        for k,row in enumerate(trial['cases']):
            law=normalized(distribution(Parameters(**row['true_parameters']),controls))
            records=rng(5,j,k).multinomial(budget,law,size=2000)
            np.testing.assert_array_equal(records,raw[f'blocks{budget}_{row["name"]}_counts'])
            hits=int(np.sum(records@llr>threshold));exact_hits=int(np.sum(records@exact_llr>=np.log(4)))
            assert hits==row['flags'] and exact_hits==row['exact_nominal_model_log4_flags']
            assert wilson(hits,2000)==row['wilson95']
            assert wilson(exact_hits,2000)==row['exact_nominal_model_log4_wilson95']
            assert float(np.mean(records@usable))==row['mean_usable_pairs']
    review=json.loads((folder/'independent_review.json').read_text(encoding='utf-8'))
    assert review['all_checks_passed']
    for name,expected in review['input_sha256'].items():assert digest(folder/name)==expected,name
    plot=json.loads((HERE/'plot_manifest.json').read_text(encoding='utf-8'))
    assert digest(HERE/'plot_validation.py')==plot['source_sha256']
    assert digest(HERE/'design_results.json')==plot['design_results_sha256']
    assert digest(folder/'results.json')==plot['validation_results_sha256']
    for name,expected in plot['artifacts'].items():assert digest(HERE/name)==expected,name
    bundle=HERE/'hardware_bundle';manifest=json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['source_sha256'].items():assert digest(HERE/name)==expected,name
    for name,expected in manifest['artifact_sha256'].items():assert digest(bundle/name)==expected,name
    references=np.load(bundle/'ideal_probabilities.npz',allow_pickle=False)
    from selected_hardware import marginal_reference
    from qiskit import qpy
    with (bundle/'logical.qpy').open('rb') as stream:circuits=qpy.load(stream)
    for row,qc in zip(manifest['circuits'],circuits,strict=True):
        expected,_=marginal_reference(Parameters(**row['parameters']),row['metadata']['controls_over_gamma'])
        saved=references[row['ideal_z_probabilities_npz_key']]
        assert row['reference_kind']=='declared_marginal' and saved.shape==(32,)
        assert row['reference_marginal_qubits']==row['metadata']['flag_qubits']+[0]
        np.testing.assert_allclose(saved,expected,atol=1e-13)
        assert qc.num_qubits==row['num_qubits'] and qc.num_clbits==row['num_qubits']
    hardware_review=json.loads((bundle/'independent_review.json').read_text(encoding='utf-8'))
    assert hardware_review['all_checks_passed']
    assert digest(bundle/'logical.qpy')==hardware_review['qpy_sha256']
    assert digest(bundle/'manifest.json')==hardware_review['manifest_sha256']
    receipt_path=HERE/'validation_receipt.json'
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
        for name,expected in receipt['source_sha256'].items():assert digest(HERE/name)==expected,name
        for name,expected in receipt['artifact_sha256'].items():assert digest(HERE/name)==expected,name
    print('Passed: all648 exact design laws, sources,73 namespaces, all validation raw records, thresholds, flag intervals and classical predictions'+(' with full20-start HMM refit.' if args.refit else '.'))


if __name__=='__main__':main()
