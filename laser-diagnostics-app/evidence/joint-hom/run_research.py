"""Prespecified synthetic calibration, held-out hypotheses, classical controls."""
import argparse
from dataclasses import asdict, replace
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy
import qiskit

from physical_model import (Parameters, true_instrument, effect, json_matrix,
                             branch_states, probabilities, source_isometries,
                             gap_superoperator, apply)
from inference import (MASTER_SEED, rng_for, generate_records, log_likelihood,
                       likelihood_ratio, hmm_fit, hmm_score, markov_fit,
                       markov_score, mean_interval, wilson)

HERE = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def physics_summary():
    q, c = Parameters(), Parameters(gap_dephasing=1.)
    rows = []
    for name, controls in [('passive', [0., 0., 0.]), ('controlled', [0., 1., -1.])]:
        qb, cb = branch_states(q, controls), branch_states(c, controls)
        qp, cp = probabilities(qb), probabilities(cb)
        rows.append({'regime': name, 'controls_over_gamma': controls,
                     'coherent_history_probabilities': {''.join(map(str,k)):v for k,v in qp.items()},
                     'classical_history_probabilities': {''.join(map(str,k)):v for k,v in cp.items()},
                     'history_tvd': .5*sum(abs(qp[k]-cp[k]) for k in qp),
                     'coherent_conditional_memory': {''.join(map(str,k)): json_matrix(v/qp[k]) for k,v in qb.items() if qp[k]>1e-12},
                     'classical_conditional_memory': {''.join(map(str,k)): json_matrix(v/cp[k]) for k,v in cb.items() if cp[k]>1e-12}})
    effects, marginals = {}, []
    for control in [0., 1., -1.]:
        maps, info = true_instrument(q, control)
        effects[str(control)] = {'coincidence_effect': json_matrix(effect(maps[1])),
                                 'gram': info,
                                 'scalar_effect_distance': float(np.linalg.norm(effect(maps[1])-np.trace(effect(maps[1]))/2*np.eye(2)))}
        per_hypothesis = []
        for p in [q, c]:
            source, info = source_isometries(p, control); d=info['dimension']
            pair = np.zeros((d*d,d*d),complex)
            for v in source:
                for a in range(2):
                    for b in range(2):
                        vector = v[a,:,:,b].reshape(-1)
                        pair += .5*np.outer(vector, vector.conj())
            pair = pair.reshape(d,d,d,d)
            per_hypothesis.append([np.einsum('abcb->ac',pair),np.einsum('abad->bd',pair)])
        marginals.append({'control_over_gamma': control,
                          'first_photon_marginal_difference_frobenius':float(np.linalg.norm(per_hypothesis[0][0]-per_hypothesis[1][0])),
                          'second_photon_marginal_difference_frobenius':float(np.linalg.norm(per_hypothesis[0][1]-per_hypothesis[1][1]))})
    return {'three_pair_exact_records':rows,'effect_operators':effects,'same_marginals_checks':marginals,
            'passive_exact_formula':'E_coin=.4*sin(theta/2)^2 I for delta/Gamma=1; independent of memory. Passive outcomes cannot identify these gap dynamics.',
            'controlled_scope':'Known second-emission source frequency shifts change the measurement setting. Distinguishing these two fixed models does not certify quantum memory against every classical process.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=HERE/'main')
    args=parser.parse_args();folder=args.output_dir
    if folder.exists(): raise SystemExit('Refusing to overwrite an existing research run')
    folder.mkdir(parents=True)
    begin=time.perf_counter()
    source_names=['physical_model.py','circuits.py','inference.py','run_research.py','PROTOCOL.md','INFERENCE_NUMERICS.md','test_physical.py','test_inference.py']
    provenance={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                'source_sha256':{n:sha256(HERE/n) for n in source_names},
                'master_seed':MASTER_SEED,
                'seed_namespaces':{'detector_calibration':[1,'parameter0to2'],'training':[10,'regime0to1'],
                                   'null_threshold':[20,'regime0to1'],'heldout':[30,'regime0to1','case0to5'],
                                   'HMM_initialization':[50,'regime0to1','states2or4','start0to2']},
                'record_counts':{'training':1000,'null_threshold':2000,'heldout_per_case':2000,'pair_trials_per_record':64},
                'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'qiskit':qiskit.__version__}}
    (folder/'run_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    nominal=Parameters();ncal=20000
    calibration_counts=[int(rng_for(1,0).binomial(ncal,nominal.e01)),int(rng_for(1,1).binomial(ncal,nominal.e10)),int(rng_for(1,2).binomial(ncal,nominal.eta))]
    fitted=replace(nominal,e01=calibration_counts[0]/ncal,e10=calibration_counts[1]/ncal,eta=calibration_counts[2]/ncal)
    classical_fit=replace(fitted,gap_dephasing=1.)
    calibration={'trials_per_quantity':ncal,'counts':dict(zip(['e01_errors','e10_errors','survived_photons'],calibration_counts)),
                 'true':{'e01':nominal.e01,'e10':nominal.e10,'eta':nominal.eta},
                 'estimated':{'e01':fitted.e01,'e10':fitted.e10,'eta':fitted.eta},
                 'interval95':{n:wilson(v,ncal) for n,v in zip(['e01','e10','eta'],calibration_counts)},
                 'other_parameters':'Gamma,delta,theta and nominal mode overlap are fixed known model settings, not inferred from the records.',
                 'scope':'Independent synthetic calibration; one fitted calibration held fixed for subsequent conditional performance intervals.'}
    scenarios=[('coherent_nominal','source_hypothesis',nominal),
               ('classical_nominal','nominal_null',replace(nominal,gap_dephasing=1.)),
               ('classical_readout_shift','nuisance_null',replace(nominal,gap_dephasing=1.,e01=.05,e10=.03)),
               ('classical_loss_shift','nuisance_null',replace(nominal,gap_dephasing=1.,eta=.5)),
               ('classical_mode_mismatch','nuisance_null',replace(nominal,gap_dephasing=1.,mode_overlap=.85)),
               ('coherent_partial_dephasing','source_model_shift',replace(nominal,gap_dephasing=.25))]
    regimes=[];raw={}
    for regime,name in enumerate(['passive','controlled']):
        controls=([0.]*64 if regime==0 else ([0.,1.,-1.]*22)[:64])
        contexts=np.array([0 if x==0 else 1 if x>0 else 2 for x in controls])
        training=generate_records(nominal,controls,1000,rng_for(10,regime));raw[f'{name}_training']=training
        predictors={};hmm_reports=[]
        for states in [2,4]:
            model,report=hmm_fit(training,contexts,states,regime)
            predictors[f'hmm_{states}']=model;hmm_reports.append(report)
        markov=markov_fit(training,contexts)
        null=generate_records(replace(nominal,gap_dephasing=1.),controls,2000,rng_for(20,regime));raw[f'{name}_null_calibration']=null
        null_score=likelihood_ratio(fitted,classical_fit,controls,null)
        k=int(np.ceil(.95*(len(null)+1)))
        threshold=float(np.sort(null_score)[k-1])
        rows=[];baseline_scores=None
        for case,(case_name,kind,truth) in enumerate(scenarios):
            records=generate_records(truth,controls,2000,rng_for(30,regime,case));raw[f'{name}_{case_name}']=records
            score=likelihood_ratio(fitted,classical_fit,controls,records)
            flags=score>threshold;hits=int(flags.sum())
            rows.append({'name':case_name,'kind':kind,'true_parameters':asdict(truth),
                         'records':len(records),'pair_trials_per_record':len(controls),
                         'flagged_records':hits,'flag_rate':hits/len(records),'flag_rate_wilson95':wilson(hits,len(records)),
                         'likelihood_ratio':mean_interval(score),
                         'mean_usable_pairs_per_record':float(np.mean(np.sum(records!=0,axis=1))),
                         'scope':'Flags favor the specified coherent hypothesis under nominal calibration; nuisance flags are false source interpretations, not proof of coherent memory.'})
            raw[f'{name}_{case_name}_llr']=score
            if case_name=='coherent_nominal':
                likelihoods={'physical_coherent_calibrated':log_likelihood(fitted,controls,records),
                             'physical_classical_calibrated':log_likelihood(classical_fit,controls,records),
                             'physical_true_generator':log_likelihood(nominal,controls,records),
                             'markov_previous_outcome':markov_score(markov,records,contexts)}
                for label,model in predictors.items():likelihoods[label]=hmm_score(model,records,contexts)
                baseline_scores={label:{'log_score_nats_per_pair_trial':mean_interval(value/len(controls)),
                                       'paired_gain_vs_physical_coherent_nats_per_trial':mean_interval((value-likelihoods['physical_coherent_calibrated'])/len(controls))}
                                 for label,value in likelihoods.items()}
                for label,value in likelihoods.items():raw[f'{name}_{label}_heldout_log_likelihood']=value
        regimes.append({'name':name,'controls_over_gamma':controls,'context_indices':contexts.tolist(),
                        'threshold':threshold,'threshold_order_statistic_1based':k,'null_calibration_records':len(null),
                        'nominal_false_alarm_target':.05,'strict_threshold_comparison':True,
                        'calibration_flag_rate':float(np.mean(null_score>threshold)),
                        'numerically_zero_llr_tolerance':1e-10,'cases':rows,'classical_predictors':hmm_reports,
                        'markov_predictor':markov.tolist(),'heldout_prediction_scores':baseline_scores})
        print(json.dumps({'regime':name,'threshold':threshold,'flags':{r['name']:r['flag_rate'] for r in rows}},indent=2),flush=True)
    np.savez_compressed(folder/'records.npz',**raw)
    result={'schema':'qrsm-hom-retained-instrument-v1','provenance':provenance,'calibration':calibration,
            'physics':physics_summary(),'regimes':regimes,
            'resource_accounting':{'each_record_attempted_excitations':128,'heldout_record_count':24000,
                                   'training_records_total':2000,'null_calibration_records_total':4000,
                                   'independent_detector_calibration_trials':60000,
                                   'optical_resources_excluded':['pump energy','collection apparatus','memory-control timing','source-frequency shift implementation','number-resolving detector overhead'],
                                   'hardware_bundle':'../hardware_bundle_v2/manifest.json','no_QPU_submission_in_this_runner':True},
            'records_sha256':sha256(folder/'records.npz'),
            'limitations':['Ideal single-photon preparation and full decay','Environment static during each wavepacket',
                           'Only specified coherent versus fully dephased gap hypotheses tested',
                           'Known Gamma,delta,theta; no microscopic parameter discovery',
                           'HMM EM is locally optimized with three starts and different parameter count',
                           'Performance intervals condition on one training and calibration realization',
                           'Synthetic controls do not validate real quantum-dot hardware or causal diagnosis'],
            'runtime_seconds':time.perf_counter()-begin}
    (folder/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(folder/'results.json'),'runtime_seconds':result['runtime_seconds']},indent=2),flush=True)


if __name__=='__main__':main()
