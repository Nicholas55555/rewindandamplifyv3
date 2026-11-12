"""Fresh synthetic photon-model replication with detector misspecification.

This is a classical numerical comparison. Three independent training/holdout
datasets come from the existing fixed quantum-emitter model, with independent
random seeds for their 400 training and 150 held-out records. A rate-matched
observed-bit Markov chain and a multistart three-state binary HMM are trained on
each training set. We also fit coupling in the known physical family with (a)
true nuisance parameters and (b) deliberately wrong detector parameters.
The benchmark says nothing by itself about a real emitter or quantum advantage.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize_scalar

if __package__:
    from .compare import (Parameters, fit_coupling, fit_hmm, hmm_likelihood_and_stats,
                          markov_scores, paired_comparison, physical_loglikelihood_by_record,
                          to_jsonable, validate_records)
else:
    from compare import (Parameters, fit_coupling, fit_hmm, hmm_likelihood_and_stats,
                         markov_scores, paired_comparison, physical_loglikelihood_by_record,
                         to_jsonable, validate_records)
from qrsm_photon import sample_records


def train_rate_matched_markov(records):
    """Fit a stationary binary Markov chain with training mean as its rate.

    The chain has stationary distribution [1-p, p] and off-diagonal entries
    alpha*p and alpha*(1-p). Optimize alpha on training sequences only.
    """
    obs = validate_records(records)
    p = float(np.clip(obs.mean(), 1e-9, 1-1e-9))
    initial = np.array([1-p, p])
    # Strictly positive entries avoid log(0) and cover negative correlation.
    upper = min(1/p, 1/(1-p)) * (1-1e-10)
    def matrix(alpha):
        return np.array([[1-alpha*p, alpha*p], [alpha*(1-p), 1-alpha*(1-p)]])
    opt = minimize_scalar(lambda alpha: -float(markov_scores(obs, initial, matrix(alpha)).sum()),
                          bounds=(1e-10, upper), method='bounded',
                          options={'xatol': 1e-10, 'maxiter': 1000})
    if not opt.success:
        raise RuntimeError('rate-matched Markov fitting failed: '+opt.message)
    return {'initial': initial, 'transition': matrix(opt.x), 'training_click_rate': p,
            'alpha': float(opt.x), 'training_log_likelihood': float(-opt.fun),
            'stationary_click_rate': p, 'optimizer_success': bool(opt.success)}


def train_physical(records, parameters):
    fit = fit_coupling(records, parameters, np.linspace(0, 1.25, 26))
    return {'g_hat': float(fit['g_hat']), 'train_log_likelihood': float(max(fit['log_likelihood'])),
            'g_grid': fit['grid'].tolist(),
            'fixed_nuisance': {key: value for key, value in asdict(parameters).items() if key != 'g_defect'}}


def compare_seed(seed, n_train=400, n_test=150, bins=40, starts=6, max_iter=800, bootstrap=2000):
    """Generate independent train/test records and fit all models from train."""
    if n_train < 2 or n_test < 2 or bins < 2:
        raise ValueError('training and test sizes and bins must each be >= 2')
    if not 0 <= seed < 1000000:
        raise ValueError('seed must be in [0, 1000000)')
    true_parameters = Parameters()
    # Shift the test seed by a large amount, guaranteeing separation for the
    # allowed set of train seeds. The data are still from the same family.
    test_seed = seed+1000000
    train = sample_records(true_parameters, n_records=n_train, steps=bins, seed=seed)
    test = sample_records(true_parameters, n_records=n_test, steps=bins, seed=test_seed)

    correct = train_physical(train, true_parameters)
    # Chosen in advance for a deliberate, illustrative calibration error;
    # neither value is estimated from data or representative of a real device.
    wrong_parameters = replace(true_parameters, detector_eta=.54, dark_rate=.035)
    mismatched = train_physical(train, wrong_parameters)
    markov = train_rate_matched_markov(train)
    hmm = fit_hmm(train, states=3, starts=starts, max_iter=max_iter, seed=seed+2000000)
    scores = {
        'physical_known_nuisance': physical_loglikelihood_by_record(
            test, replace(true_parameters, g_defect=correct['g_hat'])),
        'physical_mismatched_detector': physical_loglikelihood_by_record(
            test, replace(wrong_parameters, g_defect=mismatched['g_hat'])),
        'markov_rate_matched': markov_scores(test, markov['initial'], markov['transition']),
        'hmm_3_state': hmm_likelihood_and_stats(test, hmm['initial'], hmm['transition'], hmm['emissions']),
    }
    comparisons = {
        'known_physical_minus_hmm3': paired_comparison(scores['physical_known_nuisance'], scores['hmm_3_state'], bootstrap=bootstrap),
        'mismatched_physical_minus_hmm3': paired_comparison(scores['physical_mismatched_detector'], scores['hmm_3_state'], bootstrap=bootstrap),
        'known_minus_mismatched_physical': paired_comparison(scores['physical_known_nuisance'], scores['physical_mismatched_detector'], bootstrap=bootstrap),
        'hmm3_minus_rate_matched_markov': paired_comparison(scores['hmm_3_state'], scores['markov_rate_matched'], bootstrap=bootstrap),
    }
    return {'seed': seed, 'test_seed': test_seed,
            'train_records': n_train, 'test_records': n_test, 'bins': bins,
            'training_click_fraction': float(train.mean()), 'test_click_fraction': float(test.mean()),
            'train_binary_array_sha256': hashlib.sha256(train.tobytes()).hexdigest(),
            'test_binary_array_sha256': hashlib.sha256(test.tobytes()).hexdigest(),
            'known_nuisance_fit': correct, 'mismatched_nuisance_fit': mismatched,
            'markov_fit': to_jsonable(markov), 'hmm3_fit': to_jsonable(hmm),
            'heldout_total_nats': {key: float(value.sum()) for key, value in scores.items()},
            'paired_differences': comparisons,
            'per_record_log_likelihoods': [
                {'record_index': i, **{name: float(values[i]) for name, values in scores.items()}}
                for i in range(n_test)]}


def run(seeds=(31001, 31002, 31003), *, n_train=400, n_test=150, bins=40,
        starts=6, max_iter=800, bootstrap=2000):
    seeds = tuple(seeds)
    if len(seeds) < 1 or len(set(seeds)) != len(seeds):
        raise ValueError('seeds must be distinct and nonempty')
    replicates = []
    for seed in seeds:
        print(f'Running fresh synthetic seed {seed} ...', flush=True)
        replicates.append(compare_seed(seed, n_train, n_test, bins, starts, max_iter, bootstrap))
    return {'config': {'generation': 'independent train and held-out records from the existing synthetic generator',
                       'generator_parameters': asdict(Parameters()), 'seeds': list(seeds),
                       'n_train': n_train, 'n_test': n_test, 'bins': bins,
                       'hmm_starts': starts, 'hmm_max_iterations': max_iter,
                       'bootstrap_replicates_per_seed': bootstrap,
                       'numpy_version': np.__version__, 'scipy_version': scipy.__version__,
                       'source_data': 'new in-memory simulated records; prior CSVs unmodified'},
            'replicates': replicates,
            'limits': ['all datasets share one synthetic generator and one fixed physical parameter set',
                       'true physical family and most nuisance parameters are assumed known',
                       'mismatch is one deliberately chosen detector error, not an uncertainty distribution',
                       '3-state Bernoulli HMM and first-order Markov chain are not exhaustive classical baselines',
                       'training convergence and random-start search do not prove a global optimum',
                       'paired bootstrap intervals condition on each fitted model and omit training/model-selection uncertainty',
                       'only three simulated replicates; do not infer real-device performance',
                       'no measured optical system, quantum hardware, or computational quantum speedup demonstrated']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, nargs='+', default=[31001,31002,31003])
    parser.add_argument('--train', type=int, default=400)
    parser.add_argument('--test', type=int, default=150)
    parser.add_argument('--bins', type=int, default=40)
    parser.add_argument('--starts', type=int, default=6)
    parser.add_argument('--max-iter', type=int, default=800)
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent/'fresh_replication_results.json')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        parser.error('output exists; select a new --output or pass --overwrite')
    result = run(args.seeds, n_train=args.train, n_test=args.test, bins=args.bins,
                 starts=args.starts, max_iter=args.max_iter, bootstrap=args.bootstrap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    for row in result['replicates']:
        print(f"seed {row['seed']} known-HMM3 {row['paired_differences']['known_physical_minus_hmm3']['mean_delta_nats_per_record']:+.6f} "
              f"mismatched-HMM3 {row['paired_differences']['mismatched_physical_minus_hmm3']['mean_delta_nats_per_record']:+.6f}; "
              f"HMM selected converged={row['hmm3_fit']['converged']} iterations={row['hmm3_fit']['iterations']}")


if __name__ == '__main__':
    main()
