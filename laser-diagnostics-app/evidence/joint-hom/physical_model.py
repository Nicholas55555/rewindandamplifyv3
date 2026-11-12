"""Exact finite-family exponential photon modes and a retained-memory instrument.

Frequency arguments are angular frequencies divided by Gamma. The full emitted
wavepacket family is compressed by its complex Gram matrix, not sampled in time.
No semiconductor device parameters are inferred by this module.
"""
from dataclasses import dataclass, replace
import itertools
import math

import numpy as np


@dataclass(frozen=True)
class Parameters:
    lifetime_s: float = 1e-9
    delta_over_gamma: float = 1.0
    theta: float = math.pi / 3
    gap_dephasing: float = 0.0
    eta: float = 0.8
    e01: float = 0.01
    e10: float = 0.02
    mode_overlap: float = 1.0

    def __post_init__(self):
        for name, value in vars(self).items():
            if not np.isfinite(value):
                raise ValueError(f"Nonfinite {name}")
        if self.lifetime_s <= 0 or self.delta_over_gamma < 0:
            raise ValueError("Positive lifetime and nonnegative detuning required")
        for name in ("gap_dephasing", "eta", "e01", "e10", "mode_overlap"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be a probability")


def ry(theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def gram_embedding(frequencies, tolerance=1e-12):
    """Columns are exact compressed modes; B†B_ij=1/[1+i(wj−wi)]."""
    w = np.asarray(frequencies, dtype=float)
    gram = 1 / (1 + 1j * (w[None, :] - w[:, None]))
    vals, vecs = np.linalg.eigh(gram)
    if vals.min() < -tolerance:
        raise ValueError("Photon Gram matrix is not positive")
    keep = vals > tolerance
    rank = int(keep.sum())
    dimension = max(2, 1 << (rank-1).bit_length())
    modes = np.zeros((dimension, len(w)), dtype=complex)
    modes[:rank] = np.sqrt(vals[keep])[:, None] * vecs[:, keep].conj().T
    return modes, {"frequencies_over_gamma": w.tolist(), "rank": rank,
                   "dimension": dimension, "eigenvalues": vals.tolist(),
                   "gram_reconstruction_frobenius_error": float(np.linalg.norm(modes.conj().T @ modes-gram)),
                   "numerical_eigenvalue_threshold": tolerance}


def photon_modes(parameters, control=0.):
    delta = parameters.delta_over_gamma
    return gram_embedding([-delta, delta, control-delta, control+delta])


def dephasing_kraus(strength):
    operators = []
    if strength < 1:
        operators.append(np.sqrt(1-strength)*np.eye(2))
    if strength > 0:
        operators.extend([np.sqrt(strength)*np.diag([1., 0.]),
                          np.sqrt(strength)*np.diag([0., 1.])])
    return operators


def gap_kraus(parameters):
    return [d @ ry(parameters.theta) for d in dephasing_kraus(parameters.gap_dephasing)]


def source_isometries(parameters, control=0.):
    """Kraus isometries [env_out,photon1,photon2,env_in].

    An unobserved gap bath may make this a list rather than one isometry.
    Complete emitter decay is already included in the normalized photon modes.
    """
    modes, info = photon_modes(parameters, control)
    dimension = modes.shape[0]
    operators = []
    for gap in gap_kraus(parameters):
        v = np.zeros((2, dimension, dimension, 2), dtype=complex)
        for a in range(2):
            for b in range(2):
                v[a, :, :, b] = gap[a, b] * np.outer(modes[:, b], modes[:, 2+a])
        operators.append(v)
    return operators, info


def superoperator(kraus):
    return sum((np.kron(k.conj(), k) for k in kraus), np.zeros((4, 4), complex))


def gap_superoperator(parameters):
    return superoperator(gap_kraus(parameters))


def true_instrument(parameters, control=0.):
    """Return [symmetric/bunch,antisymmetric/coincidence] memory CP maps."""
    isometries, info = source_isometries(parameters, control)
    dimension = info["dimension"]
    symmetric, antisymmetric = [], []
    for v in isometries:
        symmetric.extend([v[:, i, i, :] for i in range(dimension)])
        for i in range(dimension):
            for j in range(i+1, dimension):
                symmetric.append((v[:, i, j, :]+v[:, j, i, :])/np.sqrt(2))
                antisymmetric.append((v[:, i, j, :]-v[:, j, i, :])/np.sqrt(2))
    maps = [superoperator(symmetric), superoperator(antisymmetric)]
    return maps, {**info, "kraus_counts": [len(symmetric), len(antisymmetric)]}


def observed_instrument(parameters, control=0.):
    """No pair / registered bunch / registered coincidence; no state reset."""
    (symmetric, anti), info = true_instrument(parameters, control)
    mu = parameters.mode_overlap
    coin = (1+mu)/2*anti + (1-mu)/2*symmetric
    bunch = (1+mu)/2*symmetric + (1-mu)/2*anti
    pair = parameters.eta**2
    registered_bunch = (1-parameters.e01)*bunch + parameters.e10*coin
    registered_coin = parameters.e01*bunch + (1-parameters.e10)*coin
    maps = np.array([(1-pair)*(symmetric+anti), pair*registered_bunch, pair*registered_coin])
    return maps, info


def effect(mapping):
    trace = np.eye(2).reshape(-1, order="F")
    return (trace @ mapping).reshape((2, 2), order="F").T


def apply(mapping, rho):
    return (mapping @ rho.reshape(-1, order="F")).reshape((2, 2), order="F")


def choi(mapping):
    result = np.zeros((4, 4), dtype=complex)
    for i in range(2):
        for j in range(2):
            matrix = np.zeros((2, 2)); matrix[i, j] = 1
            result[i*2:(i+1)*2, j*2:(j+1)*2] = apply(mapping, matrix)
    return result


def branch_states(parameters, controls, observed=False, initial=None):
    rho = np.eye(2)/2 if initial is None else np.asarray(initial, dtype=complex)
    branches = {(): rho}
    gap = gap_superoperator(parameters)
    for t, control in enumerate(controls):
        maps = (observed_instrument(parameters, control)[0] if observed
                else true_instrument(parameters, control)[0])
        branches = {key+(y,): apply(mapping, apply(gap, state) if t else state)
                    for key, state in branches.items() for y, mapping in enumerate(maps)}
    return branches


def probabilities(branches):
    return {key: float(np.trace(rho).real) for key, rho in branches.items()}


def trace_distance(a, b):
    diff = a-b
    return float(.5*np.abs(np.linalg.eigvalsh((diff+diff.conj().T)/2)).sum())


def classical_matrices(parameters, control=0., observed=True):
    """Classical transition-observation matrices, for the fully dephased case."""
    if parameters.gap_dephasing != 1:
        raise ValueError("Only complete gap dephasing is a classical diagonal model")
    maps = observed_instrument(parameters, control)[0] if observed else true_instrument(parameters, control)[0]
    return np.array([[[apply(m, np.diag(np.eye(2)[b]))[a, a].real for b in range(2)]
                      for a in range(2)] for m in maps])


def bosonic_instrument(parameters, control=0.):
    """Independent creation-operator beamsplitter construction, two photons.

    Uses occupation-number outputs, sqrt(n+1) factors and explicit port counting;
    no SWAP matrix or precomputed overlap probability enters this construction.
    """
    source, info = source_isometries(parameters, control)
    d = info["dimension"]
    occupations = []
    for a in range(2*d):
        for b in range(a, 2*d):
            o = [0]*(2*d); o[a] += 1; o[b] += 1
            occupations.append(tuple(o))
    lookup = {o: i for i, o in enumerate(occupations)}
    beam = np.zeros((len(occupations), d*d), complex)
    for i in range(d):
        for j in range(d):
            # a_i† -> (c_i†+d_i†)/sqrt2; b_j† ->(c_j†−d_j†)/sqrt2.
            for first, first_amp in [(i, 1/np.sqrt(2)), (d+i, 1/np.sqrt(2))]:
                for second, second_amp in [(j, 1/np.sqrt(2)), (d+j, -1/np.sqrt(2))]:
                    o = [0]*(2*d); o[first] = 1
                    amp = first_amp*second_amp*np.sqrt(o[second]+1)
                    o[second] += 1
                    beam[lookup[tuple(o)], i*d+j] += amp
    bunch, coin = [], []
    for v in source:
        output = np.einsum("fi,aib->afb", beam, v.reshape(2, d*d, 2))
        for index, o in enumerate(occupations):
            (coin if sum(o[:d]) == 1 else bunch).append(output[:, index, :])
    return [superoperator(bunch), superoperator(coin)]


def json_matrix(matrix):
    return {"real": np.asarray(matrix).real.tolist(), "imag": np.asarray(matrix).imag.tolist()}
