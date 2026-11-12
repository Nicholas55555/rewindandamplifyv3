"""Refine selected fresh-replication HMMs using a training-only optimizer.

Reads the completed EM analysis and re-creates each synthetic train/holdout
pair from its recorded seed, verifying hashes before use. L-BFGS-B optimizes
only the best training-selected EM restart in each replicate. Selection remains
training-only; the new holdouts are scored once after optimization. This is a
local search, not a proof of the best possible HMM or any physical advantage.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit, softmax

if __package__:
    from .compare import (Parameters, hmm_likelihood_and_stats, markov_scores, paired_comparison,
                          physical_loglikelihood_by_record, to_jsonable, validate_records)
else:
    from compare import (Parameters, hmm_likelihood_and_stats, markov_scores, paired_comparison,
                         physical_loglikelihood_by_record, to_jsonable, validate_records)
from dataclasses import replace
from qrsm_photon import sample_records


def pack(initial, transition, emissions):
    initial = np.clip(np.asarray(initial,dtype=float),1e-12,1-1e-12)
    transition = np.clip(np.asarray(transition,dtype=float),1e-12,1-1e-12)
    emissions = np.clip(np.asarray(emissions,dtype=float),1e-12,1-1e-12)
    return np.concatenate((np.log(initial[:-1]/initial[-1]),
                           np.log(transition[:,:-1]/transition[:,-1,None]).ravel(),
                           logit(emissions)))


def unpack(vector, states):
    d=states-1
    initial=softmax(np.r_[vector[:d],0.])
    rows=vector[d:d+states*d].reshape(states,d)
    transition=softmax(np.column_stack([rows,np.zeros(states)]),axis=1)
    emissions=expit(vector[d+states*d:])
    return initial,transition,emissions


def objective_gradient(vector, records, states):
    """Negative log likelihood and analytic gradient in reference logits."""
    initial,transition,emissions=unpack(vector,states)
    logs, init_sum, trans_sum, state_sum, ones_sum=hmm_likelihood_and_stats(
        records,initial,transition,emissions,stats=True)
    grad_init=init_sum[:-1]-len(records)*initial[:-1]
    grad_trans=trans_sum[:,:-1]-trans_sum.sum(axis=1,keepdims=True)*transition[:,:-1]
    grad_emit=ones_sum-state_sum*emissions
    return -float(logs.sum()), -np.concatenate([grad_init,grad_trans.ravel(),grad_emit])


def refine_hmm(records, initial, transition, emissions, max_iter=1000):
    records=validate_records(records)
    k=len(initial)
    baseline=float(hmm_likelihood_and_stats(records,initial,transition,emissions).sum())
    x0=np.clip(pack(initial,transition,emissions),-20,20)
    opt=minimize(objective_gradient,x0,args=(records,k),method='L-BFGS-B',jac=True,
                 bounds=[(-20,20)]*len(x0),
                 options={'maxiter':max_iter,'ftol':1e-12,'gtol':1e-6,'maxls':30})
    proposed=unpack(opt.x,k)
    after=float(hmm_likelihood_and_stats(records,*proposed).sum())
    accepted=after > baseline
    if not accepted:
        proposed=(np.asarray(initial),np.asarray(transition),np.asarray(emissions))
    diagnostics={'method':'L-BFGS-B on training log likelihood with analytic forward-backward gradient',
                 'optimization_success':bool(opt.success),'status':int(opt.status),'message':str(opt.message),
                 'iterations':int(opt.nit),'max_iterations':max_iter,'train_before':baseline,
                 'train_candidate':after,'accepted_candidate':accepted,
                 'train_selected':after if accepted else baseline,
                 'max_abs_logit_gradient':float(np.max(np.abs(opt.jac))),
                 'max_abs_logit':float(np.max(np.abs(opt.x))),
                 'bounds':[-20,20],
                 'note':'Only the top EM restart was refined; local convergence does not establish a global optimum.'}
    return proposed,diagnostics


def refine_result(original,max_iter=1000):
    out=deepcopy(original)
    for row in out['replicates']:
        seed=row['seed']; print(f'Refining seed {seed} ...',flush=True)
        train=sample_records(Parameters(),n_records=row['train_records'],steps=row['bins'],seed=seed)
        test=sample_records(Parameters(),n_records=row['test_records'],steps=row['bins'],seed=row['test_seed'])
        if hashlib.sha256(train.tobytes()).hexdigest()!=row['train_binary_array_sha256']:
            raise ValueError(f'training record hash differs for seed {seed}')
        if hashlib.sha256(test.tobytes()).hexdigest()!=row['test_binary_array_sha256']:
            raise ValueError(f'test record hash differs for seed {seed}')
        old=row['hmm3_fit']
        best,diagnostics=refine_hmm(train,old['initial'],old['transition'],old['emissions'],max_iter)
        row['hmm3_refinement']=diagnostics
        row['hmm3_refined_parameters']={'initial':best[0].tolist(),'transition':best[1].tolist(),
                                       'emissions':best[2].tolist()}
        true=Parameters()
        wrong=replace(true,detector_eta=.54,dark_rate=.035)
        markov=row['markov_fit']
        scores={'physical_known_nuisance':physical_loglikelihood_by_record(test,replace(true,g_defect=row['known_nuisance_fit']['g_hat'])),
                'physical_mismatched_detector':physical_loglikelihood_by_record(test,replace(wrong,g_defect=row['mismatched_nuisance_fit']['g_hat'])),
                'markov_rate_matched':markov_scores(test,np.asarray(markov['initial']),np.asarray(markov['transition'])),
                'hmm_3_state':hmm_likelihood_and_stats(test,*best)}
        # A saved independent reference confirms re-generated test records and
        # physical likelihoods agree, not merely their random-seed labels.
        prior=np.array([entry['physical_known_nuisance'] for entry in row['per_record_log_likelihoods']])
        if not np.allclose(scores['physical_known_nuisance'],prior,atol=1e-9,rtol=1e-12):
            raise ValueError(f'physical held-out likelihood changed for seed {seed}')
        count=out['config']['bootstrap_replicates_per_seed']
        row['heldout_total_nats']={name:float(values.sum()) for name,values in scores.items()}
        row['paired_differences']={
          'known_physical_minus_hmm3':paired_comparison(scores['physical_known_nuisance'],scores['hmm_3_state'],bootstrap=count),
          'mismatched_physical_minus_hmm3':paired_comparison(scores['physical_mismatched_detector'],scores['hmm_3_state'],bootstrap=count),
          'known_minus_mismatched_physical':paired_comparison(scores['physical_known_nuisance'],scores['physical_mismatched_detector'],bootstrap=count),
          'hmm3_minus_rate_matched_markov':paired_comparison(scores['hmm_3_state'],scores['markov_rate_matched'],bootstrap=count)}
        row['per_record_log_likelihoods']=[{'record_index':i,**{name:float(values[i]) for name,values in scores.items()}}
                                               for i in range(row['test_records'])]
    out['config']['refinement']='Selected best training EM restart, then local L-BFGS-B training-only polish.'
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent/'fresh_replication_results.json')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'fresh_replication_refined.json')
    parser.add_argument('--max-iter',type=int,default=1000)
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    if args.output.exists() and not args.overwrite:
        parser.error('output exists; select a new --output or pass --overwrite')
    original=json.loads(args.input.read_text(encoding='utf-8'))
    result=refine_result(original,args.max_iter)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for row in result['replicates']:
        print(f"seed {row['seed']}: physical-HMM {row['paired_differences']['known_physical_minus_hmm3']['mean_delta_nats_per_record']:+.6f} nats/record; "
              f"L-BFGS success={row['hmm3_refinement']['optimization_success']}, "
              f"train improvement={row['hmm3_refinement']['train_selected']-row['hmm3_refinement']['train_before']:.6f}")


if __name__=='__main__':
    main()
