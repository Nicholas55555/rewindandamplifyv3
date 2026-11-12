"""Illustrative single-photon temporal states and ideal two-photon interference.

All times are seconds, frequencies are cycles/second (Hz), and decay rates are
inverse seconds. The angular detuning in the kernel is explicitly 2*pi*nu.
Exactly one radiative photon per excitation is imposed. Frequency-independent
excitation, no re-excitation/multiphoton events, ideal mode/polarization matching,
independent Markov dephasing baths, and a balanced beamsplitter are assumptions.
This is a known quantum-optics benchmark, not a fitted quantum-dot device model.
"""
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from numpy.polynomial.legendre import leggauss


def _finite(value, name, minimum=None, maximum=None, strict_minimum=False):
    value = float(value)
    if not np.isfinite(value):
        raise ValueError(f'{name} must be finite')
    if minimum is not None and (value <= minimum if strict_minimum else value < minimum):
        raise ValueError(f'{name} is below its allowed range')
    if maximum is not None and value > maximum:
        raise ValueError(f'{name} is above its allowed range')
    return value


@dataclass(frozen=True)
class Emitter:
    lifetime_s: float = 1e-9
    pure_dephasing_per_s: float = 0.0
    frequency_offset_hz: float = 0.0

    def __post_init__(self):
        _finite(self.lifetime_s, 'lifetime_s', 0, strict_minimum=True)
        _finite(self.pure_dephasing_per_s, 'pure_dephasing_per_s', 0)
        _finite(self.frequency_offset_hz, 'frequency_offset_hz')

    @property
    def radiative_rate_per_s(self):
        return 1.0 / self.lifetime_s

    @property
    def coherence_time_s(self):
        return 1.0 / (self.radiative_rate_per_s / 2 + self.pure_dephasing_per_s)


def temporal_density(time_s, other_time_s, emitter):
    """rho(t,t'), in 1/second; integral rho(t,t) dt = 1 on [0,infinity).

    The state is conditioned on an emitted photon. This function does not include
    collection loss; the unconditioned field additionally has a vacuum sector.
    Broadcasting permits independent quadrature of two temporal density kernels.
    """
    t, u = np.broadcast_arrays(np.asarray(time_s, dtype=float),
                               np.asarray(other_time_s, dtype=float))
    if np.any(~np.isfinite(t)) or np.any(~np.isfinite(u)) or np.any(t < 0) or np.any(u < 0):
        raise ValueError('Emission times must be finite and nonnegative')
    gamma = emitter.radiative_rate_per_s
    return gamma * np.exp(-gamma * (t + u) / 2
                          - emitter.pure_dephasing_per_s * np.abs(t - u)
                          - 2j * np.pi * emitter.frequency_offset_hz * (t - u))


def hom_overlap(first, second):
    """Tr(rho_first rho_second) for independent photons with the given states.

    Allows unequal radiative lifetimes. For equal Gamma and gamma*, this reduces
    to Gamma*(Gamma+2*gamma*) / ((Gamma+2*gamma*)**2 + (2*pi*delta_nu)**2).
    A common frequency shift cancels. For equal frequency/lifetime/dephasing,
    M = T2/(2*T1). The photon pair must be temporally aligned at the beamsplitter.
    """
    ga, gb = first.radiative_rate_per_s, second.radiative_rate_per_s
    a = (ga + gb) / 2 + first.pure_dephasing_per_s + second.pure_dephasing_per_s
    delta = 2 * np.pi * (first.frequency_offset_hz - second.frequency_offset_hz)
    return float(2 * ga * gb * a / ((ga + gb) * (a * a + delta * delta)))


def hom_observables(overlap, efficiency):
    """Ideal balanced-beamsplitter outcomes per excitation pair.

    Each excitation emits one photon. eta is independent per-photon survival to
    an otherwise ideal HOM apparatus; output detectors are ideal. Pair yield is
    eta**2, not a conditional visibility. Zero eta supplies no observable HOM data.
    """
    overlap = _finite(overlap, 'overlap', 0, 1)
    efficiency = _finite(efficiency, 'efficiency', 0, 1)
    return {
        'emitted_photons_per_excitation': 1.0,
        'ideal_g2_zero_imposed': 0.0,
        'single_photon_survival_probability': efficiency,
        'both_photons_survive_probability': efficiency ** 2,
        'conditional_overlap': overlap,
        'conditional_coincidence_probability': (1 - overlap) / 2,
        'coincidence_probability_per_excitation_pair': efficiency ** 2 * (1 - overlap) / 2,
        'distinguishable_control_coincidence_per_excitation_pair': efficiency ** 2 / 2,
        'hom_observable_with_nonzero_efficiency': efficiency > 0,
    }


def quadrature_overlap(first, second, order=128, window_lifetimes=24.0):
    """Numerically integrate the actual kernels on a finite triangular domain.

    Uses t in [0,T], u in [0,t], then 2*Re(rho_a(t,u)*rho_b(u,t)). Splitting at
    t=u avoids the dephasing cusp; no analytic overlap integrand is substituted.
    The finite-window result is NOT renormalized. The returned absolute tail
    bound follows from dropping dephasing in |rho_a rho_b| outside [0,T]^2.
    This bound covers truncation, not floating-point or quadrature discretization.
    """
    if isinstance(order, bool) or not isinstance(order, (int, np.integer)) or order < 4:
        raise ValueError('order must be an integer at least 4')
    _finite(window_lifetimes, 'window_lifetimes', 0, strict_minimum=True)
    end = float(window_lifetimes) * max(first.lifetime_s, second.lifetime_s)
    nodes, weights = leggauss(order)
    t = (nodes[:, None] + 1) * end / 2
    u = (nodes[None, :] + 1) * t / 2
    integrand = temporal_density(t, u, first) * temporal_density(u, t, second)
    integral = 2 * np.sum(weights[:, None] * end / 2
                          * weights[None, :] * t / 2 * integrand.real)
    ga, gb = first.radiative_rate_per_s, second.radiative_rate_per_s
    a = (ga + gb) / 2
    tail = ga * gb / a ** 2 * (2 * np.exp(-a * end) - np.exp(-2 * a * end))
    return {'overlap': float(integral), 'order': int(order),
            'window_s': end, 'absolute_truncation_bound': float(tail)}


def stationary_trap_joint(switch_probability):
    """Joint probabilities for two ± endpoints with identical uniform marginals.

    switch_probability is P(second endpoint differs), not a switching rate.
    Each endpoint is assumed constant throughout its photon wavepacket. p=0.5
    means fresh independent offsets; p<0.5 represents correlated endpoints.
    This pair law does not specify a continuous-time trap or a full record.
    """
    p = _finite(switch_probability, 'switch_probability', 0, 1)
    return np.array([[(1 - p) / 2, p / 2], [p / 2, (1 - p) / 2]])


def trap_pair_overlap(emitter, offset_hz, switch_probability):
    """Average conditional overlap, preserving the classical joint pair law.

    Independent fast dephasing remains in each photon. A shared quasi-static
    shift can cancel in the pair even though the single-photon marginal is mixed.
    Multiplying marginal density matrices is appropriate only for p=0.5.
    """
    offset = _finite(offset_hz, 'offset_hz', 0)
    joint = stationary_trap_joint(switch_probability)
    states = [Emitter(emitter.lifetime_s, emitter.pure_dephasing_per_s,
                      emitter.frequency_offset_hz + sign * offset) for sign in (-1, 1)]
    overlaps = np.array([[hom_overlap(a, b) for b in states] for a in states])
    return float(np.sum(joint * overlaps))


def wilson_interval(successes, trials, confidence=0.95):
    """Descriptive binomial Wilson interval for independent simulated pairs."""
    if not isinstance(trials, (int, np.integer)) or trials <= 0:
        raise ValueError('trials must be a positive integer')
    if not isinstance(successes, (int, np.integer)) or not 0 <= successes <= trials:
        raise ValueError('successes must be an integer between zero and trials')
    _finite(confidence, 'confidence', 0, 1, strict_minimum=True)
    if confidence == 1:
        raise ValueError('confidence must be below 1')
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p, n = successes / trials, trials
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [float(max(0, center - radius)), float(min(1, center + radius))]


def simulate_trap_pairs(emitter, offset_hz, switch_probability, efficiency,
                        pairs=100_000, seed=20261111):
    """Sample independent photon PAIRS; the two trap endpoints within each pair correlate.

    Three SeedSequence child streams independently draw trap endpoints, survival,
    and ideal interference outcomes. No source/detector records are measured here.
    Repeated overlapping pairs from one trap trajectory would not be independent.
    """
    if isinstance(pairs, bool) or not isinstance(pairs, (int, np.integer)) or pairs <= 0:
        raise ValueError('pairs must be a positive integer')
    p = _finite(switch_probability, 'switch_probability', 0, 1)
    eta = _finite(efficiency, 'efficiency', 0, 1)
    offset = _finite(offset_hz, 'offset_hz', 0)
    streams = np.random.SeedSequence(seed).spawn(3)
    trap_rng, loss_rng, hom_rng = [np.random.default_rng(s) for s in streams]
    first_positive = trap_rng.random(pairs) < 0.5
    switched = trap_rng.random(pairs) < p
    same = hom_overlap(emitter, emitter)
    shifted = Emitter(emitter.lifetime_s, emitter.pure_dephasing_per_s,
                      emitter.frequency_offset_hz + 2 * offset)
    different = hom_overlap(emitter, shifted)
    pair_overlap = np.where(switched, different, same)
    survived = loss_rng.random((pairs, 2)) < eta
    both = survived.all(axis=1)
    coincidence = both & (hom_rng.random(pairs) < (1 - pair_overlap) / 2)
    both_count, coincidence_count = int(both.sum()), int(coincidence.sum())
    conditional_rate = coincidence_count / both_count if both_count else None
    expected_overlap = trap_pair_overlap(emitter, offset, p)
    expected_coincidence = eta ** 2 * (1 - expected_overlap) / 2
    sampling_error = coincidence_count / pairs - expected_coincidence
    model_standard_error = float(np.sqrt(expected_coincidence * (1 - expected_coincidence) / pairs))
    return {
        'seed': int(seed), 'seed_spawn_keys': [list(s.spawn_key) for s in streams],
        'independent_excitation_pairs': int(pairs),
        'first_trap_positive_count': int(first_positive.sum()),
        'second_trap_positive_count': int(np.logical_xor(first_positive, switched).sum()),
        'switched_pair_count': int(switched.sum()),
        'emitted_photons': int(2 * pairs), 'survived_photons': int(survived.sum()),
        'both_survived_pairs': both_count, 'coincidence_pairs': coincidence_count,
        'observed_pair_survival_rate': both_count / pairs,
        'observed_coincidence_per_excitation_pair': coincidence_count / pairs,
        'expected_coincidence_per_excitation_pair': expected_coincidence,
        'sampling_error_per_pair': sampling_error,
        'binomial_standard_error_at_model_probability': model_standard_error,
        'sampling_error_in_standard_errors': sampling_error / model_standard_error if model_standard_error else None,
        'coincidence_per_pair_wilson95': wilson_interval(coincidence_count, pairs),
        'observed_conditional_coincidence_rate': conditional_rate,
        'conditional_coincidence_wilson95': wilson_interval(coincidence_count, both_count) if both_count else None,
        'mean_sampled_pair_overlap': float(pair_overlap.mean()),
        'expected_pair_overlap': expected_overlap,
        'uncertainty_scope': 'Binomial sampling of independent simulated pairs; no physical-model uncertainty or calibrated device coverage.',
    }
