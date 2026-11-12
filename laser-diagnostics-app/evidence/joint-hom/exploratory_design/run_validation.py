"""Generate prospective selected-design data; refuse existing output directory."""
import argparse
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy
from design import Parameters,distribution
from validation import (BLOCKS,BUDGETS,MASTER,rng,normalized,sample_blocks,block_indices,
                        fit_categorical,fit_hmm,namespaces)
from inference import hmm_score,mean_interval,wilson

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=HERE/'validation_run');args=parser.parse_args()
    if args.output_dir.exists():raise FileExistsError(args.output_dir)
    ns=namespaces();assert len(ns)==len(set(ns))
    sources=['VALIDATION_PROTOCOL.md','validation.py','run_validation.py','test_validation.py','design.py','../physical_model.py','../inference.py']
    provenance={'created_utc':datetime.now(timezone.utc).isoformat(),'master_seed':MASTER,'rng_namespaces':[list(x) for x in ns],
                'source_sha256':{s:digest(HERE/s) for s in sources},'design_results_sha256':digest(HERE/'design_results.json')}
    args.output_dir.mkdir();(args.output_dir/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    start=time.perf_counter();raw={}
    nominal=Parameters(theta=3*np.pi/4);controls=[2.]*4
    counts=[int(rng(1,i).binomial(20000,p)) for i,p in enumerate([.01,.02,.8])]
    estimated=dict(zip(['e01','e10','eta'],np.array(counts)/20000))
    fitted=replace(nominal,**estimated);fitted_c=replace(fitted,gap_dephasing=1.)
    truth_q=normalized(distribution(nominal,controls));truth_c=normalized(distribution(replace(nominal,gap_dephasing=1.),controls))
    probs_q=normalized(distribution(fitted,controls));probs_c=normalized(distribution(fitted_c,controls))
    llr=np.log(probs_q/probs_c);exact_llr=np.log(truth_q/truth_c)
    training=sample_blocks(truth_q,20000,(2,));heldout=sample_blocks(truth_q,20000,(3,))
    raw['predictor_training_blocks']=training;raw['predictor_heldout_blocks']=heldout
    predictors={'physical_coherent_calibrated':probs_q,'physical_classical_calibrated':probs_c,
                'exact_classical_categorical_oracle':truth_q,'saturated_categorical_fit':fit_categorical(training)}
    reports=[]
    for states in [4,8]:
        model,report=fit_hmm(training,states)
        reports.append(report)
        predictors[f'hmm_{states}']=np.exp(hmm_score(model,BLOCKS,np.zeros(4,dtype=int)))
    indices=block_indices(heldout);scores={}
    reference=np.log(probs_q[indices])/4
    for name,probs in predictors.items():
        values=np.log(probs[indices])/4;raw[f'prediction_{name}']=values
        scores[name]={'log_score_nats_per_attempted_pair':mean_interval(values),
                      'paired_gain_vs_calibrated_physical':mean_interval(values-reference),
                      'block_probabilities':probs.tolist()}
    cases=[('coherent_nominal',nominal),('classical_nominal',replace(nominal,gap_dephasing=1.)),
           ('classical_readout_shift',replace(nominal,gap_dephasing=1.,e01=.05,e10=.03)),
           ('classical_loss_shift',replace(nominal,gap_dephasing=1.,eta=.5)),
           ('classical_mode_mismatch',replace(nominal,gap_dephasing=1.,mode_overlap=.85)),
           ('coherent_partial_dephasing',replace(nominal,gap_dephasing=.25)),
           ('classical_gap_angle_shift',replace(nominal,gap_dephasing=1.,theta=nominal.theta+.1))]
    case_laws=[normalized(distribution(p,controls)) for _,p in cases]
    trials=[];usable=np.sum(BLOCKS>0,axis=1)
    for j,budget in enumerate(BUDGETS):
        calibration=rng(4,j).multinomial(budget,truth_c,size=2000)
        raw[f'blocks{budget}_null_calibration_counts']=calibration
        threshold=float(np.sort(calibration@llr)[1900]);rows=[]
        for k,((name,parameters),law) in enumerate(zip(cases,case_laws)):
            records=rng(5,j,k).multinomial(budget,law,size=2000)
            raw[f'blocks{budget}_{name}_counts']=records
            score=records@llr;hits=int(np.sum(score>threshold))
            exact_score=records@exact_llr;exact_hits=int(np.sum(exact_score>=np.log(4)))
            rows.append({'name':name,'true_parameters':vars(parameters),'records':2000,'flags':hits,'flag_rate':hits/2000,
                         'wilson95':wilson(hits,2000),'mean_calibrated_llr':float(score.mean()),
                         'mean_usable_pairs':float(np.mean(records@usable)),
                         'exact_nominal_model_log4_flags':exact_hits,'exact_nominal_model_log4_rate':exact_hits/2000,
                         'exact_nominal_model_log4_wilson95':wilson(exact_hits,2000)})
        trials.append({'independent_blocks':budget,'attempted_pairs':budget*4,'source_excitations':budget*8,
                       'threshold_calibrated':threshold,'calibration_records':2000,'cases':rows})
        print(f'Budget {budget}: Q={rows[0]["flag_rate"]:.3f}, null={rows[1]["flag_rate"]:.3f}',flush=True)
    np.savez_compressed(args.output_dir/'records.npz',**raw)
    result={'schema':'qrsm-hom-selected-design-validation-v1','provenance':provenance,
            'scope':'Fresh prospective simulation of an exploratorily selected, perfectly reset four-pair design; not quantum-memory identification or optical validation.',
            'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
            'parameters':vars(nominal),'controls_over_gamma':controls,'calibration':{'counts':counts,'trials_each':20000,'estimated':estimated},
            'predictor_training_blocks':20000,'predictor_heldout_blocks':20000,'classical_hmms':reports,'prediction_scores':scores,
            'power_trials':trials,'exact_nominal_block_law_quantum':truth_q.tolist(),'exact_nominal_block_law_classical':truth_c.tolist(),
            'records_sha256':digest(args.output_dir/'records.npz'),'runtime_s':time.perf_counter()-start,
            'uncertainty_scope':'Conditional on one calibration/training realization, fixed physics, independent perfect resets; no uncertainty in control implementation or empirical source physics.'}
    (args.output_dir/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.output_dir),'runtime_s':result['runtime_s'],'records_sha256':result['records_sha256']},indent=2))


if __name__=='__main__':main()
