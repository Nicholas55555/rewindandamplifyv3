"""Synthetic retained-memory records and conventional sequence predictors."""
import numpy as np

from physical_model import observed_instrument, gap_superoperator

MASTER_SEED = 20261112031


def rng_for(*namespace):
    return np.random.default_rng(np.random.SeedSequence(MASTER_SEED, spawn_key=tuple(namespace)))


def maps_for(parameters, controls):
    unique = {float(c): observed_instrument(parameters, c)[0] for c in set(controls)}
    gap = gap_superoperator(parameters)
    return [unique[float(c)] if t == 0 else unique[float(c)] @ gap for t, c in enumerate(controls)]


def generate_records(parameters, controls, count, rng):
    maps = maps_for(parameters, controls)
    rho = np.tile(np.array([.5, 0., 0., .5], dtype=complex), (count, 1))
    records = np.zeros((count, len(controls)), dtype=np.uint8)
    for t, instruments in enumerate(maps):
        candidates = np.einsum('yij,nj->nyi', instruments, rho)
        p = np.real(candidates[:, :, 0]+candidates[:, :, 3])
        if np.min(p) < -1e-11 or np.max(abs(p.sum(axis=1)-1)) > 1e-10:
            raise AssertionError('Invalid conditional probabilities')
        p = np.maximum(p, 0); p /= p.sum(axis=1, keepdims=True)
        outcomes = (rng.random(count)[:, None] > np.cumsum(p, axis=1)).sum(axis=1)
        records[:, t] = outcomes
        rho = candidates[np.arange(count), outcomes] / p[np.arange(count), outcomes, None]
    return records


def log_likelihood(parameters, controls, records):
    n, length = records.shape
    if length != len(controls):
        raise ValueError('Record and control lengths differ')
    rho = np.tile(np.array([.5, 0., 0., .5], dtype=complex), (n, 1))
    logp = np.zeros(n)
    for t, instruments in enumerate(maps_for(parameters, controls)):
        rho = np.einsum('nij,nj->ni', instruments[records[:, t]], rho)
        p = np.real(rho[:, 0]+rho[:, 3])
        if np.any(p <= 0):
            raise ValueError('Observed outcome has zero likelihood under this model')
        rho /= p[:, None]
        logp += np.log(p)
    return logp


def likelihood_ratio(quantum, classical, controls, records):
    values = log_likelihood(quantum, controls, records)-log_likelihood(classical, controls, records)
    values[np.abs(values) < 1e-10] = 0.
    return values


def markov_fit(records, contexts, context_count=3):
    counts = np.full((context_count, 4, 3), .5)
    for t, context in enumerate(contexts):
        previous = records[:, t-1] if t else np.full(len(records), 3)
        np.add.at(counts[context], (previous, records[:, t]), 1.)
    return counts/counts.sum(axis=-1, keepdims=True)


def markov_score(model, records, contexts):
    scores = np.zeros(len(records))
    for t, context in enumerate(contexts):
        previous = records[:, t-1] if t else np.full(len(records), 3)
        scores += np.log(model[context, previous, records[:, t]])
    return scores


def hmm_forward(initial, transition, emission, records, contexts):
    n, length = records.shape
    states = len(initial)
    alpha = np.empty((length, n, states))
    scales = np.empty((length, n))
    prior = np.tile(initial, (n, 1))
    for t, context in enumerate(contexts):
        if t:
            prior = alpha[t-1] @ transition
        current = prior * emission[context][:, records[:, t]].T
        scales[t] = current.sum(axis=1)
        alpha[t] = current/scales[t, :, None]
    return alpha, scales


def hmm_score(model, records, contexts):
    _, scales = hmm_forward(model['initial'], model['transition'], model['emission'], records, contexts)
    return np.log(scales).sum(axis=0)


def hmm_fit(records, contexts, states, regime, starts=3, iterations=100):
    """Ordinary HMM: context-dependent emissions and a shared hidden transition.

    This general predictor is not the same parameterization as the source model.
    Baum-Welch is multi-start/local; no guarantee of globally optimal fitting.
    """
    candidates = []
    for start in range(starts):
        rng = rng_for(50, regime, states, start)
        initial = rng.dirichlet(np.ones(states))
        transition = rng.dirichlet(np.ones(states), size=states)
        emission = rng.dirichlet(np.ones(3), size=(3, states))
        history = []
        for iteration in range(iterations):
            alpha, scales = hmm_forward(initial, transition, emission, records, contexts)
            likelihood = float(np.log(scales).sum())
            history.append(likelihood)
            if iteration > 0 and abs(history[-1]-history[-2])/(records.size) < 2e-6:
                break
            beta = np.ones_like(alpha)
            for t in range(records.shape[1]-2, -1, -1):
                next_emission = emission[contexts[t+1]][:, records[:, t+1]].T
                beta[t] = (beta[t+1]*next_emission) @ transition.T / scales[t+1, :, None]
            gamma = alpha*beta
            gamma /= gamma.sum(axis=2, keepdims=True)
            initial = gamma[0].mean(axis=0)
            transition_counts = np.full((states, states), 1e-8)
            for t in range(records.shape[1]-1):
                next_emission = emission[contexts[t+1]][:, records[:, t+1]].T
                right = beta[t+1]*next_emission / scales[t+1, :, None]
                transition_counts += transition*(alpha[t].T @ right)
            transition = transition_counts/transition_counts.sum(axis=1, keepdims=True)
            counts = np.full((3, states, 3), 1e-8)
            for t, context in enumerate(contexts):
                for outcome in range(3):
                    counts[context, :, outcome] += gamma[t, records[:, t] == outcome].sum(axis=0)
            emission = counts/counts.sum(axis=2, keepdims=True)
        model = {'initial': initial, 'transition': transition, 'emission': emission}
        score = float(hmm_score(model, records, contexts).sum())
        candidates.append({'model': model, 'training_log_likelihood': score,
                           'start': start, 'iterations': len(history), 'trace': history})
    best = max(candidates, key=lambda c: c['training_log_likelihood'])
    report = {key: value for key, value in best.items() if key != 'model'}
    report['states'] = states
    report['training_records'] = len(records)
    report['parameters'] = (states-1) + states*(states-1) + 3*states*2
    report['all_start_final_scores'] = [x['training_log_likelihood'] for x in candidates]
    report['model'] = {k: v.tolist() for k, v in best['model'].items()}
    return best['model'], report


def mean_interval(values):
    values = np.asarray(values, dtype=float)
    mean = float(np.mean(values))
    se = float(np.std(values, ddof=1)/np.sqrt(len(values)))
    return {'mean': mean, 'standard_error_across_records': se,
            'approximate_interval95': [mean-1.95996398454*se, mean+1.95996398454*se],
            'independent_records': len(values)}


def wilson(successes, count):
    z = 1.95996398454; p = successes/count
    center = (p+z*z/(2*count))/(1+z*z/count)
    radius = z*np.sqrt(p*(1-p)/count+z*z/(4*count*count))/(1+z*z/count)
    return [max(0., center-radius), min(1., center+radius)]
