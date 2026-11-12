"""Uncalibrated correlated 2x2 Poisson exposure; exact classical inference.

Bit 0 stores a shared dose component z. Bits 1+2*i,2+2*i encode
min(N_i,3), little endian. The score uses Gaussian corner-response weights
[1,2,2,4]. Counts capped at 3 preserve the event score<3 and every accepted
map exactly; the unconditional count distribution and moments are changed.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import itertools
import math
import numpy as np


@dataclass(frozen=True)
class Config:
    rates: tuple = (1.5, 2.5)
    prior: tuple = (.2, .8)
    weights: tuple = (1, 2, 2, 4)
    threshold: int = 3
    cap: int = 3

    def __post_init__(self):
        if (len(self.rates) != 2 or len(self.prior) != 2 or
            any(not math.isfinite(x) or x <= 0 for x in self.rates + self.prior) or
            not math.isclose(sum(self.prior), 1) or self.weights != (1, 2, 2, 4) or
            self.threshold != 3 or self.cap != 3):
            raise ValueError('This verified experiment requires two positive rates, normalized prior, and fixed spatial predicate.')


DEFAULT = Config()


def capped_pmf(rate):
    p0 = math.exp(-rate)
    p1 = p0 * rate
    p2 = p1 * rate / 2
    return np.array([p0, p1, p2, 1-p0-p1-p2])


def decode(index):
    return index & 1, tuple((index >> (1+2*i)) & 3 for i in range(4))


def encode(z, counts):
    return int(z) + sum(int(n) << (1+2*i) for i, n in enumerate(counts))


def accepted(index, config=DEFAULT):
    _, counts = decode(index)
    return sum(w*n for w, n in zip(config.weights, counts)) < config.threshold


def joint_probabilities(config=DEFAULT):
    result = np.empty(512)
    pmfs = [capped_pmf(r) for r in config.rates]
    for index in range(512):
        z, ns = decode(index)
        result[index] = config.prior[z] * math.prod(pmfs[z][n] for n in ns)
    return result


def backward_messages(pmfs, weights, threshold):
    """B[i,b] = P(sum_{j>=i} w_j N_j < b), b=0..threshold.

    Supports nonidentical independent counts. Only n with w*n<b contribute;
    no tail approximation enters this event. O(cells*threshold^2) setup.
    """
    table = np.zeros((len(weights)+1, threshold+1))
    table[-1, 1:] = 1
    for i in range(len(weights)-1, -1, -1):
        w = weights[i]
        for b in range(1, threshold+1):
            table[i, b] = sum(pmfs[i][n]*table[i+1, b-w*n]
                              for n in range((b-1)//w+1))
    return table


def dp_solution(config=DEFAULT):
    tables = [backward_messages([capped_pmf(r)]*4, config.weights, config.threshold)
              for r in config.rates]
    component = np.array([x[0, config.threshold] for x in tables])
    probability = float(np.dot(config.prior, component))
    posterior = np.asarray(config.prior)*component/probability
    return probability, posterior, tables


def conditional_draws(shots, rng, config=DEFAULT):
    """Exact rejection-free sampler, after a finite DP setup; no QPU needed."""
    _, posterior, tables = dp_solution(config)
    z = rng.choice(2, size=shots, p=posterior)
    output = np.empty((shots, 4), dtype=int)
    for row, component in enumerate(z):
        budget = config.threshold
        pmf = capped_pmf(config.rates[component])
        for i, weight in enumerate(config.weights):
            values = np.arange((budget-1)//weight+1)
            probs = pmf[values]*tables[component][i+1, budget-weight*values]
            probs /= probs.sum()
            output[row, i] = rng.choice(values, p=probs)
            budget -= weight*output[row, i]
    return z, output


def independent_control(config=DEFAULT):
    """Same one-cell mixed-Poisson law, but independently mixed at each cell."""
    marginal = sum(p*capped_pmf(r) for p, r in zip(config.prior, config.rates))
    table = backward_messages([marginal]*4, config.weights, config.threshold)
    return float(table[0, config.threshold])


def summarize(distribution, config=DEFAULT):
    truth = joint_probabilities(config)
    mask = np.array([accepted(i, config) for i in range(512)])
    hit = float(distribution[mask].sum())
    expected = truth[mask]/truth[mask].sum()
    actual = distribution[mask]/hit
    indices = np.flatnonzero(mask)
    low = np.array([(i & 1) == 0 for i in indices])
    maps = np.array([decode(i)[1] for i in indices])
    return {'hit_probability': hit,
            'conditional_joint_tv': float(np.abs(actual-expected).sum()/2),
            'conditional_low_dose_probability': float(actual[low].sum()),
            'conditional_mean_counts': (actual @ maps).tolist(),
            'conditional_probabilities': {str(i): float(v) for i, v in zip(indices, actual)}}


def classical_experiment(config=DEFAULT, shots=20000, repeats=40, seed=20261110):
    """Direct vs fixed, prespecified exponential tilt of the joint (z,N) law.

    Proposal keeps the prior unchanged, reducing each conditional Poisson
    rate by .35. Exact *uncapped* Poisson likelihood is used per full map.
    This comparator is supplemental; exact DP is the strongest baseline.
    """
    target, _, _ = dp_solution(config)
    records = {'direct': [], 'importance': []}
    for k in range(repeats):
        for j, name in enumerate(records):
            rng = np.random.default_rng(seed+2*k+j)
            tilt = 1 if name == 'direct' else .35
            z = rng.choice(2, size=shots, p=config.prior)
            lam = np.asarray(config.rates)[z]
            counts = rng.poisson(lam[:, None]*tilt, size=(shots, 4))
            hit = counts @ np.array(config.weights) < config.threshold
            logw = 4*lam*(tilt-1) + counts.sum(axis=1)*math.log(1/tilt)
            values = hit*np.exp(logw)
            se = float(values.std(ddof=1)/math.sqrt(shots))
            records[name].append({'estimate': float(values.mean()), 'se': se,
                                  'hits': int(hit.sum())})
    out = {}
    for name, rows in records.items():
        estimates = np.array([r['estimate'] for r in rows])
        out[name] = {'mean_estimate': float(estimates.mean()),
                     'empirical_sd': float(estimates.std(ddof=1)),
                     'mean_reported_se': float(np.mean([r['se'] for r in rows])),
                     'rmse': float(np.sqrt(np.mean((estimates-target)**2))), 'runs': rows}
    return {'shots_per_run': shots, 'independent_repeats': repeats, 'seed': seed,
            'importance_rate_multiplier': .35, 'tuning_budget': 0, 'methods': out}
