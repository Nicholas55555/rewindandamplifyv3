"""Held-out photon-record comparison with classical hidden Markov models.

This analyzes the bundled *synthetic* data. It neither runs quantum hardware nor
proves an advantage over classical models. The physical model gets the correct
generative family and fixed nuisance parameters; only its coupling is fitted.
Two- and three-state Bernoulli HMMs are fitted by scaled forward-backward EM
from multiple random starts using training records only.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from qrsm_photon import Parameters, fit_coupling, init_state, instruments, _traces


def validate_records(records: np.ndarray) -> np.ndarray:
    data = np.asarray(records)
    if data.ndim != 2 or data.shape[0] < 1 or data.shape[1] < 2 or not np.all((data == 0) | (data == 1)):
        raise ValueError('records must be a nonempty 2-D binary array with at least two bins')
    return data.astype(np.uint8)


def hmm_likelihood_and_stats(records, initial, transition, emissions, *, stats=False):
    """Scaled forward-backward per-record log likelihood and expected counts.

    Hidden state is sampled initially, emits a Bernoulli value, transitions,
    emits the next value, etc. Rows of transition are stochastic.
    """
    obs = validate_records(records)
    initial = np.asarray(initial, dtype=float)
    transition = np.asarray(transition, dtype=float)
    emissions = np.asarray(emissions, dtype=float)
    k = initial.size
    if (initial.shape != (k,) or transition.shape != (k, k) or emissions.shape != (k,)
            or np.any(initial <= 0) or np.any(transition <= 0)
            or np.any(emissions <= 0) or np.any(emissions >= 1)
            or not np.isclose(initial.sum(), 1) or not np.allclose(transition.sum(axis=1), 1)):
        raise ValueError('invalid HMM probabilities')
    n, steps = obs.shape
    # e[n,t,k] is the probability of the observed bit given hidden state k.
    e = np.where(obs[:, :, None] == 1, emissions[None, None, :], 1-emissions[None, None, :])
    alpha = np.empty((n, steps, k), dtype=float)
    scales = np.empty((n, steps), dtype=float)
    alpha[:, 0, :] = initial[None, :] * e[:, 0, :]
    scales[:, 0] = alpha[:, 0, :].sum(axis=1)
    alpha[:, 0, :] /= scales[:, 0, None]
    for t in range(1, steps):
        alpha[:, t, :] = (alpha[:, t-1, :] @ transition) * e[:, t, :]
        scales[:, t] = alpha[:, t, :].sum(axis=1)
        alpha[:, t, :] /= scales[:, t, None]
    logs = np.log(scales).sum(axis=1)
    if not stats:
        return logs
    beta = np.ones((n, k), dtype=float)
    state_sum = np.zeros(k)
    ones_sum = np.zeros(k)
    trans_sum = np.zeros((k, k))
    for t in range(steps-1, -1, -1):
        gamma = alpha[:, t, :] * beta
        gamma /= gamma.sum(axis=1, keepdims=True)
        state_sum += gamma.sum(axis=0)
        ones_sum += (gamma * obs[:, t, None]).sum(axis=0)
        if t == 0:
            initial_sum = gamma.sum(axis=0)
        else:
            weighted_next = e[:, t, :] * beta
            xi = (alpha[:, t-1, :, None] * transition[None, :, :]
                  * weighted_next[:, None, :])
            xi /= xi.sum(axis=(1, 2), keepdims=True)
            trans_sum += xi.sum(axis=0)
            beta = (weighted_next @ transition.T) / scales[:, t, None]
    return logs, initial_sum, trans_sum, state_sum, ones_sum


def fit_hmm(records, states, starts=12, max_iter=300, tolerance=1e-7, seed=90210):
    obs = validate_records(records)
    if states < 1 or starts < 1 or max_iter < 1 or tolerance <= 0:
        raise ValueError('invalid HMM optimization arguments')
    rng = np.random.default_rng(seed)
    best = None
    diagnostics = []
    for start in range(starts):
        initial = rng.dirichlet(np.ones(states))
        transition = np.vstack([rng.dirichlet(np.ones(states)) for _ in range(states)])
        emissions = rng.uniform(.05, .95, states)
        previous = -np.inf
        converged = False
        max_decline = 0.0
        for iteration in range(1, max_iter+1):
            logs, init_sum, trans_sum, state_sum, ones_sum = hmm_likelihood_and_stats(
                obs, initial, transition, emissions, stats=True)
            total = float(logs.sum())
            if np.isfinite(previous):
                max_decline = max(max_decline, previous-total)
                if total-previous >= 0 and (total-previous)/obs.shape[0] < tolerance:
                    converged = True
                    break
            previous = total
            # A tiny floor keeps exact 0/1 estimates numerically valid. It can
            # cause negligible differences from an unconstrained MLE.
            floor = 1e-12
            initial = np.maximum(init_sum, floor)
            initial /= initial.sum()
            transition = np.maximum(trans_sum, floor)
            transition /= transition.sum(axis=1, keepdims=True)
            emissions = np.clip(ones_sum/state_sum, floor, 1-floor)
        # Re-evaluate after the final M-step if the iteration cap was reached.
        total = float(hmm_likelihood_and_stats(obs, initial, transition, emissions).sum())
        diagnostics.append({'start': start, 'train_log_likelihood': total,
                            'iterations': iteration, 'converged': converged,
                            'largest_em_step_decline': max_decline})
        if best is None or total > best['train_log_likelihood']:
            best = {'initial': initial.copy(), 'transition': transition.copy(),
                    'emissions': emissions.copy(), 'train_log_likelihood': total,
                    'selected_start': start, 'converged': converged,
                    'iterations': iteration}
    best['starts'] = diagnostics
    return best


def physical_loglikelihood_by_record(records, parameters):
    """Same finite-bin physical likelihood as qrsm_photon, per sequence."""
    obs = validate_records(records)
    no, click, _ = instruments(parameters)
    dimension = 4*parameters.n_cavity
    states = np.tile(init_state(parameters)[:, None], (1, len(obs)))
    logs = np.zeros(len(obs))
    for t in range(obs.shape[1]):
        hits = obs[:, t].astype(bool)
        next_state = np.where(hits[None, :], click @ states, no @ states)
        probability = _traces(next_state, dimension)
        if np.any(probability < -1e-8):
            raise FloatingPointError('negative observation probability')
        probability = np.maximum(probability, 1e-300)
        logs += np.log(probability)
        states = next_state / probability[None, :]
    return logs


def iid_fit(train):
    return float(np.clip(validate_records(train).mean(), 1e-9, 1-1e-9))


def iid_scores(records, p):
    obs = validate_records(records)
    return (obs*np.log(p)+(1-obs)*np.log1p(-p)).sum(axis=1)


def markov_fit(train):
    obs = validate_records(train)
    initial = np.bincount(obs[:, 0], minlength=2).astype(float)+1
    initial /= initial.sum()
    transition = np.ones((2, 2), dtype=float)
    for a in (0, 1):
        for b in (0, 1):
            transition[a, b] += np.sum((obs[:, :-1] == a) & (obs[:, 1:] == b))
    transition /= transition.sum(axis=1, keepdims=True)
    return initial, transition


def markov_scores(records, initial, transition):
    obs = validate_records(records)
    return np.log(initial[obs[:, 0]])+np.log(transition[obs[:, :-1], obs[:, 1:]]).sum(axis=1)


def paired_comparison(first, second, *, bootstrap=5000, seed=271828):
    """Uncertainty across independent held-out sequences, not fitted-model uncertainty."""
    delta = np.asarray(first, dtype=float)-np.asarray(second, dtype=float)
    if delta.ndim != 1 or len(delta) < 2 or bootstrap < 2 or not np.all(np.isfinite(delta)):
        raise ValueError('need >= 2 finite paired records and bootstrap replicates')
    rng = np.random.default_rng(seed)
    means = np.mean(delta[rng.integers(0, len(delta), size=(bootstrap, len(delta)))], axis=1)
    lower, upper = np.quantile(means, [.025, .975])
    return {'total_delta_nats': float(delta.sum()),
            'mean_delta_nats_per_record': float(delta.mean()),
            'standard_error_nats_per_record': float(delta.std(ddof=1)/math.sqrt(len(delta))),
            'bootstrap_95_percentile_nats_per_record': [float(lower), float(upper)],
            'positive_record_fraction': float(np.mean(delta > 0)),
            'n_heldout_records': int(len(delta)), 'bootstrap_replicates': bootstrap,
            'bootstrap_seed': seed}


def to_jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def run(path=ROOT/'synthetic_click_records.csv', *, starts=12, max_iter=300, seed=90210, bootstrap=5000):
    path = Path(path)
    records = validate_records(np.loadtxt(path, delimiter=',', dtype=float, ndmin=2))
    split = int(.7*len(records))
    if split < 2 or len(records)-split < 2:
        raise ValueError('at least two train and two test sequences are required')
    train, test = records[:split], records[split:]
    params = Parameters()
    physical_fit = fit_coupling(train, params, np.linspace(0, 1.25, 26))
    physical_params = replace(params, g_defect=physical_fit['g_hat'])
    physical = physical_loglikelihood_by_record(test, physical_params)
    p = iid_fit(train)
    mi, mt = markov_fit(train)
    scores = {'physical_fixed_nuisance': physical,
              'bernoulli_iid': iid_scores(test, p),
              'markov_1': markov_scores(test, mi, mt)}
    fits = {}
    for k in (2, 3):
        fit = fit_hmm(train, k, starts=starts, max_iter=max_iter, seed=seed+k)
        scores[f'hmm_{k}_state'] = hmm_likelihood_and_stats(
            test, fit['initial'], fit['transition'], fit['emissions'])
        fits[f'hmm_{k}_state'] = to_jsonable(fit)
    per_record = [{'sequence_index': int(split+i),
                   **{name: float(logs[i]) for name, logs in scores.items()}}
                  for i in range(len(test))]
    return {'data': {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'records': int(len(records)), 'bins_per_record': int(records.shape[1]),
                     'train_records': int(len(train)), 'heldout_records': int(len(test)),
                     'split': 'first 70% train, final 30% held out; no held-out selection',
                     'origin': 'synthetic records from the same known physical model family'},
            'physical_model': {'fitted_parameter': 'g_defect', 'fitted_g': physical_fit['g_hat'],
                               'grid': physical_fit['grid'].tolist(),
                               'other_parameters': 'fixed to synthetic generator values',
                               'training_total_log_likelihood': float(max(physical_fit['log_likelihood']))},
            'iid_train_click_rate': p, 'markov_initial': mi.tolist(), 'markov_transition': mt.tolist(),
            'hmm_training': {'starts_per_model': starts, 'max_iterations': max_iter,
                             'seed_base': seed, 'convergence_tolerance_nats_per_training_record': 1e-7,
                             'fitted_parameters': {'2_state': 5, '3_state': 11},
                             'selected_by': 'maximum training likelihood', 'models': fits},
            'heldout_total_log_likelihoods': {k: float(v.sum()) for k, v in scores.items()},
            'paired_physical_minus_baselines': {
                k: paired_comparison(physical, v, bootstrap=bootstrap)
                for k, v in scores.items() if k != 'physical_fixed_nuisance'},
            'per_record_log_likelihoods': per_record,
            'limitations': ['same-family synthetic data, not measured photons',
                            'held-out records are reused from the previous companion evaluation, not a newly untouched test set',
                            'physical model knows every nuisance parameter and the generating family',
                            'HMMs are fitted from finite random starts and are not all classical baselines',
                            'paired uncertainty conditions on the fitted models; it does not include model-selection, training-set, or misspecification uncertainty',
                            'one dataset/split and one physical parameter setting',
                            'no quantum-hardware experiment, speedup, or quantum advantage demonstrated']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'synthetic_click_records.csv')
    parser.add_argument('--starts', type=int, default=12)
    parser.add_argument('--max-iter', type=int, default=300)
    parser.add_argument('--seed', type=int, default=90210)
    parser.add_argument('--bootstrap', type=int, default=5000)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent/'heldout_hmm_results.json')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        parser.error('output exists; select a new --output or pass --overwrite')
    result = run(args.data, starts=args.starts, max_iter=args.max_iter, seed=args.seed, bootstrap=args.bootstrap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'heldout_total_log_likelihoods': result['heldout_total_log_likelihoods'],
                      'paired_physical_minus_baselines': result['paired_physical_minus_baselines']}, indent=2))


if __name__ == '__main__':
    main()
