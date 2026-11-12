"""Piecewise-constant drive instruments and causal hybrid-state inference.

The quantum state is retained between bins. Source regime is classical and
unobserved. All rates retain original arbitrary units. No device is calibrated.
"""
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
import sys
import numpy as np
from scipy.special import logsumexp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'followup'))
from inference_model import instrument, traces
sys.path.insert(0, str(HERE.parent))
from qrsm_photon import Parameters, init_state


def schedule_transition(kind, time, switch=.06, first=16, last=48):
    if kind == 'baseline':
        return np.ones((1, 1))
    if kind == 'step':
        hazard = 0. if time < first else (1. if time >= last else 1. / (last - time + 1))
        return np.array([[1-hazard, hazard], [0., 1.]])
    if kind == 'telegraph':
        r = switch if time >= first else 0.
        return np.array([[1-r, r], [r, 1-r]])
    raise ValueError(kind)


def source_schedules(n, steps, seed, kind='baseline', switch=.06, first=16, last=48):
    rng = np.random.default_rng(seed)
    states = np.zeros((n, steps), dtype=np.uint8)
    if kind == 'step':
        onset = rng.integers(first, last+1, n)
        states = (np.arange(steps)[None, :] >= onset[:, None]).astype(np.uint8)
    elif kind == 'telegraph':
        for t in range(first, steps):
            states[:, t] = (states[:, t-1] if t else 0) ^ (rng.random(n) < switch)
    elif kind != 'baseline':
        raise ValueError(kind)
    return states


@lru_cache(maxsize=64)
def maps(base, fraction=0., emitter_detuning=0., eta_factor=1., dark_add=0., loss_factor=1.):
    changed = replace(base, drive=base.drive*(1+fraction),
                      detector_eta=base.detector_eta*eta_factor,
                      dark_rate=base.dark_rate+dark_add, kappa=base.kappa*loss_factor)
    return instrument(changed, (1., emitter_detuning))


def generate(base, n, steps, seed, case, *, schedule_seed, nuisance_seed):
    """Sample actual source schedule and retained conditional physical states.

    For an added afterpulse with no instrument click, retain the no-click state.
    The base instrument click already includes independent dark counts; it is
    not a pure emitted-photon label. Marginalizing the unobserved afterpulse
    cause gives the mixture tested below. Blind bins evolve the full channel.
    """
    latent = source_schedules(n, steps, schedule_seed, case.get('source', 'baseline'),
                              case.get('switch', .06))
    rng = np.random.default_rng(seed)
    nuisance_onset = np.random.default_rng(nuisance_seed).integers(16, 49, n)
    rho = np.tile(init_state(base)[:, None], (1, n))
    records = np.zeros((n, steps), dtype=np.uint8)
    pre_afterpulse_clicks = np.zeros_like(records)
    nuisance = case.get('nuisance', {})
    operators = {}
    for source in (0, 1):
        for active in (0, 1):
            kw = {k:v for k,v in nuisance.items() if k in ('emitter_detuning', 'eta_factor', 'dark_add', 'loss_factor')} if active else {}
            operators[source, active] = maps(base, source*case.get('fraction', 0.), **kw)
    dim = 4*base.n_cavity
    for t in range(steps):
        active = t >= nuisance_onset
        previous = records[:, t-1].astype(bool) if t else np.zeros(n, bool)
        blind = previous & active & bool(nuisance.get('dead_bins', 0))
        draws = rng.random(n)
        pulse_draws = rng.random(n)
        for source in (0, 1):
            for is_active in (0, 1):
                indices = np.flatnonzero((latent[:, t] == source) & (active == is_active))
                if not len(indices):
                    continue
                no, yes, full = operators[source, is_active]
                state = rho[:, indices]
                s0 = no @ state
                p0 = np.clip(traces(s0, dim), 0, 1)
                hit = (draws[indices] >= p0) & ~blind[indices]
                nxt = np.where(hit[None, :], yes @ state, s0)
                if np.any(blind[indices]):
                    nxt[:, blind[indices]] = full @ state[:, blind[indices]]
                prob = traces(nxt, dim)
                if np.min(prob) <= 0:
                    raise FloatingPointError('Invalid sampled branch')
                rho[:, indices] = nxt / prob
                ap = (previous[indices] & bool(is_active) & ~blind[indices]
                      & (pulse_draws[indices] < nuisance.get('afterpulse', 0.)))
                records[indices, t] = hit | ap
                pre_afterpulse_clicks[indices, t] = hit
    return {'records': records, 'source_states': latent, 'pre_afterpulse_clicks': pre_afterpulse_clicks,
            'fraction': latent*case.get('fraction', 0.), 'nuisance_onset': nuisance_onset}


def forward(records, base, fraction, kind, switch=.06, first=16, last=48):
    """Exact quantum/classical source filter, excluding detector mismatch.

    rho[regime] is its unnormalized conditional density given the entire past.
    Transition mixing preserves quantum memory, then the current instrument acts.
    """
    records = np.asarray(records)
    if records.ndim != 2 or not np.all((records == 0) | (records == 1)):
        raise ValueError('binary matrix required')
    n, steps = records.shape
    k = 1 if kind == 'baseline' else 2
    rho = np.zeros((k, (4*base.n_cavity)**2, n), complex)
    rho[0] = init_state(base)[:, None]
    bank = [maps(base, fraction*j)[:2] for j in range(k)]
    log_prefix = np.zeros((n, steps))
    active_probability = np.zeros_like(log_prefix)
    accumulated = np.zeros(n)
    for t in range(steps):
        transition = schedule_transition(kind, t, switch, first, last)
        mixed = np.einsum('ij,ivn->jvn', transition, rho)
        for j in range(k):
            no, yes = bank[j]
            rho[j] = np.where(records[:, t][None, :], yes @ mixed[j], no @ mixed[j])
        weights = np.array([traces(r, 4*base.n_cavity) for r in rho])
        prob = weights.sum(axis=0)
        if np.any(prob < -1e-9):
            raise FloatingPointError('Negative likelihood')
        prob = np.maximum(prob, 1e-300)
        accumulated += np.log(prob)
        rho /= prob[None, None, :]
        log_prefix[:, t] = accumulated
        if k == 2:
            active_probability[:, t] = weights[1]/prob
    return log_prefix, active_probability


def physical_predictions(records, base, fraction):
    null, _ = forward(records, base, 0., 'baseline')
    step, ps = forward(records, base, fraction, 'step')
    tele, pt = forward(records, base, fraction, 'telegraph')
    alt = np.logaddexp(step, tele) - np.log(2.)
    whole = logsumexp(np.array([null+np.log(.5), step+np.log(.25), tele+np.log(.25)]), axis=0)
    estimate = fraction*(np.exp(step+np.log(.25)-whole)*ps + np.exp(tele+np.log(.25)-whole)*pt)
    return {'statistic': alt-null, 'log_predictive': whole[:, -1], 'estimate': estimate,
            'null_log_prefix': null, 'source_log_prefix': alt}


def hmm_prefix(records, initial, transition, emission):
    """Independent vectorized filtering of the trained classical HMM."""
    n, steps = records.shape
    state = np.tile(np.asarray(initial)[None, :], (n, 1))
    emission = np.asarray(emission)
    accumulated = np.zeros(n)
    result = np.zeros((n, steps))
    for t in range(steps):
        if t:
            state = state @ np.asarray(transition)
        state *= np.where(records[:, t, None], emission[None, :], 1-emission[None, :])
        z = np.maximum(state.sum(axis=1), 1e-300)
        state /= z[:, None]
        accumulated += np.log(z)
        result[:, t] = accumulated
    return result


def count_contrast(records, window=16):
    n, steps = records.shape
    cumulative = np.c_[np.zeros(n), np.cumsum(records, axis=1)]
    score = np.zeros((n, steps))
    for end in range(2*window, steps+1):
        score[:, end-1] = np.abs(cumulative[:, end] - 2*cumulative[:, end-window] + cumulative[:, end-2*window])/window
    return score


def threshold(maxima, alpha=.05):
    """Strict > threshold; finite order statistic controls fresh null rank."""
    a = np.sort(np.asarray(maxima))
    rank = int(np.ceil((len(a)+1)*(1-alpha)))
    return float(a[rank-1]) if rank <= len(a) else float('inf')


def readout_maps(no, yes, previous_click, afterpulse=0., dead=False):
    """Reference detector forward maps, used to test the mismatch generator."""
    if dead and previous_click:
        return no+yes, np.zeros_like(yes)
    p = afterpulse if previous_click else 0.
    return (1-p)*no, yes+p*no
