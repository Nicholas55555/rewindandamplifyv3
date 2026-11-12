"""Read-only replay of frozen records, inference, calibration and bundle hashes."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from physical_model import Parameters
from inference import (rng_for, generate_records, likelihood_ratio, log_likelihood,
                       markov_fit, markov_score, hmm_score, hmm_fit, wilson)

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--refit',action='store_true');args=parser.parse_args()
    folder=HERE/'main';r=json.loads((folder/'results.json').read_text(encoding='utf-8'))
    provenance=json.loads((folder/'run_provenance.json').read_text(encoding='utf-8'))
    assert provenance==r['provenance']
    for n,h in provenance['source_sha256'].items():assert digest(HERE/n)==h,n
    assert digest(folder/'records.npz')==r['records_sha256']
    raw=np.load(folder/'records.npz',allow_pickle=False)
    nominal=Parameters()
    counts=[int(rng_for(1,i).binomial(20000,p)) for i,p in enumerate([.01,.02,.8])]
    assert counts==list(r['calibration']['counts'].values())
    fitted=replace(nominal,**r['calibration']['estimated']);cf=replace(fitted,gap_dephasing=1.)
    for regime,reg in enumerate(r['regimes']):
        name=reg['name'];controls=reg['controls_over_gamma'];contexts=np.array(reg['context_indices'])
        training=generate_records(nominal,controls,1000,rng_for(10,regime))
        np.testing.assert_array_equal(training,raw[f'{name}_training'])
        null=generate_records(replace(nominal,gap_dephasing=1.),controls,2000,rng_for(20,regime))
        np.testing.assert_array_equal(null,raw[f'{name}_null_calibration'])
        score=likelihood_ratio(fitted,cf,controls,null)
        assert np.sort(score)[1900]==reg['threshold']
        markov=markov_fit(training,contexts)
        np.testing.assert_allclose(markov,reg['markov_predictor'],atol=1e-14)
        for index,case in enumerate(reg['cases']):
            truth=Parameters(**case['true_parameters'])
            records=generate_records(truth,controls,2000,rng_for(30,regime,index))
            np.testing.assert_array_equal(records,raw[f'{name}_{case["name"]}'])
            score=likelihood_ratio(fitted,cf,controls,records)
            np.testing.assert_allclose(score,raw[f'{name}_{case["name"]}_llr'],atol=1e-12)
            hits=int(np.sum(score>reg['threshold']))
            assert hits==case['flagged_records']
            np.testing.assert_allclose(wilson(hits,2000),case['flag_rate_wilson95'],atol=1e-14)
            if case['name']=='coherent_nominal':
                candidates={'physical_coherent_calibrated':log_likelihood(fitted,controls,records),
                            'physical_classical_calibrated':log_likelihood(cf,controls,records),
                            'physical_true_generator':log_likelihood(nominal,controls,records),
                            'markov_previous_outcome':markov_score(markov,records,contexts)}
                for report in reg['classical_predictors']:
                    model={k:np.array(v) for k,v in report['model'].items()}
                    if args.refit:
                        rebuilt,check=hmm_fit(training,contexts,report['states'],regime)
                        for key in model:np.testing.assert_allclose(rebuilt[key],model[key],rtol=1e-9,atol=1e-11)
                        assert check['start']==report['start']
                    candidates[f'hmm_{report["states"]}']=hmm_score(model,records,contexts)
                for label,values in candidates.items():
                    np.testing.assert_allclose(values,raw[f'{name}_{label}_heldout_log_likelihood'],atol=1e-10)
                    saved=reg['heldout_prediction_scores'][label]['log_score_nats_per_pair_trial']['mean']
                    assert abs(values.mean()/64-saved)<1e-12
    bundle=HERE/'hardware_bundle_v2';m=json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    for n,h in m['source_sha256'].items():assert digest(HERE/n)==h,n
    for n,h in m['artifact_sha256'].items():assert digest(bundle/n)==h,n
    plot=json.loads((HERE/'plot_manifest.json').read_text(encoding='utf-8'))
    assert digest(HERE/'plot_results.py')==plot['source_sha256']
    assert digest(folder/'results.json')==plot['results_sha256']
    assert digest(bundle/'manifest.json')==plot['hardware_manifest_sha256']
    for n,h in plot['artifacts'].items():assert digest(HERE/n)==h,n
    review=json.loads((folder/'independent_review.json').read_text(encoding='utf-8'))
    assert review['all_checks_passed']
    for n,h in review['artifact_sha256'].items():assert digest(folder/n)==h,n
    for n,h in review['reviewed_source_sha256'].items():assert digest(HERE/n)==h,n
    validation=HERE/'validation.json'
    if validation.exists():
        receipt=json.loads(validation.read_text(encoding='utf-8'))
        for n,h in receipt['source_sha256'].items():assert digest(HERE/n)==h,n
        for n,h in receipt['artifact_sha256'].items():assert digest(HERE/n)==h,n
    print('Passed: source/raw/bundle hashes, all independent calibration/training/heldout record regeneration, thresholds, flag counts/intervals and prediction scores'+(' including HMM refits.' if args.refit else '.'))


if __name__=='__main__':main()
