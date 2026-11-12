"""Numerical Stinespring feasibility check for the photon-count instruments.

The input instruments are finite-dimensional column-vectorized channels from
``qrsm_photon.instruments``.  We diagonalize the two Choi matrices and build a
flagged isometry on a power-of-two padded system.  We do not synthesize a
unitary extension, compile gates, or claim that the physical experiment itself
can be reversed.  See README for the assumptions and numerical-rank caveats.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from qrsm_photon import Parameters, instruments


def choi_matrix(superoperator: np.ndarray, dimension: int) -> np.ndarray:
    """Return Choi J[(a,i),(b,j)] = E(|i><j|)[a,b], using column vec.

    Superoperator indices are ``(a + d*b, i + d*j)`` and Choi indices are
    ``(a + d*i, b + d*j)``.  With this convention an eigenvector of J, reshaped
    column-wise, yields a Kraus operator without transposing it.
    """
    d = dimension
    if superoperator.shape != (d*d, d*d):
        raise ValueError('superoperator shape does not match dimension')
    return (superoperator.reshape((d, d, d, d), order='F')
            .transpose(0, 2, 1, 3).reshape((d*d, d*d), order='F'))


def kraus_from_superoperator(superoperator: np.ndarray, dimension: int,
                             cutoff: float = 1e-12, negative_tolerance: float = 1e-10):
    """Return thresholded Choi-eigenvector Kraus operators and diagnostics.

    The absolute cutoff removes numerically small positive eigenvalues; the
    resulting map is only approximately the original map and the retained
    rank is cutoff-dependent.  Large negative eigenvalues raise an error.
    """
    if cutoff < 0 or negative_tolerance < 0:
        raise ValueError('tolerances must be nonnegative')
    choi = choi_matrix(superoperator, dimension)
    hermiticity_error = float(np.linalg.norm(choi - choi.conj().T))
    eigenvalues, eigenvectors = np.linalg.eigh((choi + choi.conj().T) / 2)
    if eigenvalues[0] < -negative_tolerance:
        raise ValueError(f'Choi matrix has negative eigenvalue {eigenvalues[0]:.3g}')
    keep = eigenvalues > cutoff
    vectors = eigenvectors[:, keep]
    values = eigenvalues[keep]
    operators = np.stack([np.sqrt(value) * vector.reshape((dimension, dimension), order='F')
                          for value, vector in zip(values, vectors.T)]) if len(values) else np.zeros((0, dimension, dimension), complex)
    reconstructed = np.einsum('kai,kbj->abij', operators, operators.conj(), optimize=True)
    reconstructed = reconstructed.reshape((dimension*dimension, dimension*dimension), order='F')
    return operators, {
        'rank_above_cutoff': int(keep.sum()),
        'minimum_choi_eigenvalue': float(eigenvalues[0]),
        'maximum_choi_eigenvalue': float(eigenvalues[-1]),
        'choi_hermiticity_frobenius_error': hermiticity_error,
        'discarded_positive_choi_eigenvalue_sum': float(eigenvalues[(eigenvalues > 0) & ~keep].sum()),
        'reconstructed_superoperator_frobenius_error': float(np.linalg.norm(reconstructed-superoperator)),
        'ranks_by_absolute_cutoff': {str(tol): int(np.count_nonzero(eigenvalues > tol))
                                     for tol in (1e-8, 1e-10, 1e-12, 1e-14)},
    }


def flagged_isometry(no_kraus: np.ndarray, click_kraus: np.ndarray):
    """Build V: input system -> system + one outcome flag + environment.

    Environment basis index k and binary flag b use row block ``2*k+b``.
    The non-power-of-two system is zero-padded. Its unused basis subspace is
    given identity evolution in the first no-click Kraus operator, so the
    extension is defined on every padded input; physical states stay physical.
    No full unitary completion is constructed.
    """
    if no_kraus.ndim != 3 or click_kraus.ndim != 3 or len(no_kraus) == 0:
        raise ValueError('nonempty no-click and compatible Kraus arrays required')
    d = no_kraus.shape[1]
    if no_kraus.shape[1:] != (d, d) or click_kraus.shape[1:] != (d, d):
        raise ValueError('Kraus operators must be square with matching dimensions')
    dpad = 1 << (d-1).bit_length()
    rank = max(len(no_kraus), len(click_kraus), 1)
    env_dim = 1 << (rank-1).bit_length()
    isometry = np.zeros((2*env_dim*dpad, dpad), dtype=complex)
    for flag, operators in enumerate((no_kraus, click_kraus)):
        for k, op in enumerate(operators):
            start = (2*k + flag)*dpad
            isometry[start:start+d, :d] = op
    if dpad > d:
        isometry[d:dpad, d:dpad] = np.eye(dpad-d)
    return isometry, dpad, env_dim


def normalize_completeness(no_kraus: np.ndarray, click_kraus: np.ndarray):
    """Make the truncated combined channel trace preserving by right whitening.

    Dropping tiny Choi eigenvalues gives an approximate instrument whose Kraus
    completeness matrix M is close to, but not exactly, the identity.  Replace
    every K by K M^(-1/2). This changes both branches slightly while preserving
    their outcome labels and creates a valid TP approximation (up to floating
    point rounding). Its numerical errors against the input maps are measured.
    """
    d = no_kraus.shape[1]
    completeness = np.zeros((d, d), complex)
    for op in list(no_kraus) + list(click_kraus):
        completeness += op.conj().T @ op
    completeness = (completeness + completeness.conj().T)/2
    values, vectors = np.linalg.eigh(completeness)
    if np.min(values) <= 0:
        raise ValueError('truncated Kraus completeness matrix is not positive definite')
    inverse_root = (vectors * (1/np.sqrt(values))) @ vectors.conj().T
    return (no_kraus @ inverse_root, click_kraus @ inverse_root,
            {'pre_normalization_completeness_spectral_error': float(np.linalg.norm(completeness-np.eye(d), ord=2)),
             'right_normalization_spectral_change': float(np.linalg.norm(inverse_root-np.eye(d), ord=2))})


def kraus_superoperator(operators: np.ndarray, d: int) -> np.ndarray:
    """Build the column-vectorized superoperator of a supplied Kraus family."""
    return np.einsum('kai,kbj->abij', operators, operators.conj(), optimize=True).reshape((d*d, d*d), order='F')


def branch_from_isometry(isometry: np.ndarray, rho: np.ndarray, flag: int,
                         padded_dimension: int, env_dimension: int) -> np.ndarray:
    """Trace environment after selecting an outcome, returning an unnormalized state."""
    if flag not in (0, 1):
        raise ValueError('flag must be 0 or 1')
    result = np.zeros((padded_dimension, padded_dimension), dtype=complex)
    for k in range(env_dimension):
        start = (2*k + flag)*padded_dimension
        block = isometry[start:start+padded_dimension, :]
        result += block @ rho @ block.conj().T
    return result


def assess(parameters: Parameters, cutoff: float = 1e-12, seed: int = 41,
           random_states: int = 8) -> dict:
    """Reconstruct each outcome and check probabilities and conditional states."""
    if random_states < 1:
        raise ValueError('random_states must be positive')
    no, click, total = instruments(parameters)
    d = 4*parameters.n_cavity
    no_ops, no_info = kraus_from_superoperator(no, d, cutoff)
    click_ops, click_info = kraus_from_superoperator(click, d, cutoff)
    no_ops, click_ops, normalization = normalize_completeness(no_ops, click_ops)
    no_info['corrected_superoperator_frobenius_error'] = float(np.linalg.norm(kraus_superoperator(no_ops, d)-no))
    click_info['corrected_superoperator_frobenius_error'] = float(np.linalg.norm(kraus_superoperator(click_ops, d)-click))
    V, dpad, env_dim = flagged_isometry(no_ops, click_ops)
    isometry_error = float(np.linalg.norm(V.conj().T @ V - np.eye(dpad), ord=2))
    rng = np.random.default_rng(seed)
    max_branch_error = max_probability_error = max_conditioned_error = max_total_trace_error = 0.0
    tested_conditionals = 0
    for sample in range(random_states):
        # Alternate pure and full-rank mixed states, all inside physical space.
        x = rng.normal(size=(d, 1 if sample % 2 == 0 else d)) + 1j*rng.normal(size=(d, 1 if sample % 2 == 0 else d))
        rho = x @ x.conj().T
        rho /= np.trace(rho)
        rho_pad = np.zeros((dpad, dpad), complex)
        rho_pad[:d, :d] = rho
        for b, S in enumerate((no, click)):
            expected = (S @ rho.reshape(-1, order='F')).reshape((d, d), order='F')
            actual = branch_from_isometry(V, rho_pad, b, dpad, env_dim)[:d, :d]
            p_exp, p_act = float(np.trace(expected).real), float(np.trace(actual).real)
            max_branch_error = max(max_branch_error, float(np.linalg.norm(expected-actual)))
            max_probability_error = max(max_probability_error, abs(p_exp-p_act))
            if p_exp > 1e-12 and p_act > 1e-12:
                max_conditioned_error = max(max_conditioned_error, float(np.linalg.norm(expected/p_exp-actual/p_act)))
                tested_conditionals += 1
        max_total_trace_error = max(max_total_trace_error, abs(float(np.trace((total @ rho.reshape(-1, order='F')).reshape((d, d), order='F')).real)-1.0))
    r0, r1 = len(no_ops), len(click_ops)
    joint_env_qubits = math.ceil(math.log2(r0+r1)) if r0+r1 > 1 else 0
    return {
        'model': {'n_cavity': parameters.n_cavity, 'physical_system_dimension': d,
                  'padded_system_dimension': dpad, 'system_qubits': int(math.log2(dpad)),
                  'absolute_choi_cutoff': cutoff, 'seed': seed, 'random_states': random_states},
        'no_click': no_info, 'click': click_info, 'normalization': normalization,
        'dilation': {
            'outcome_flag_qubits': 1, 'environment_qubits': int(math.log2(env_dim)),
            'flag_and_environment_qubits': 1 + int(math.log2(env_dim)),
            'total_qubits_per_step': int(math.log2(dpad)) + 1 + int(math.log2(env_dim)),
            'effective_rank_based_joint_ancilla_qubits': joint_env_qubits,
            'isometry_shape': list(V.shape), 'isometry_spectral_error': isometry_error,
            'full_unitary_constructed': False, 'gates_compiled': False,
        },
        'checks': {'outcome_state_frobenius_error_max': max_branch_error,
                   'outcome_probability_error_max': max_probability_error,
                   'normalized_conditional_state_frobenius_error_max': max_conditioned_error,
                   'nonzero_conditional_states_checked': tested_conditionals,
                   'original_total_trace_error_max': max_total_trace_error},
        'limitations': [
            'Numerical effective ranks depend on absolute Choi cutoff; they are not certified exact ranks or a lower bound on every possible approximation.',
            'For the retained trace-preserving approximation, the sum of its retained Choi ranks gives a lower bound on combined outcome-plus-environment dimension in exact arithmetic; it does not certify the exact rank of the original maps.',
            'This is a classical matrix calculation on a finite truncated-cavity simulator, not a compiled circuit, optical processor, or physical rewind.',
            'A reversible unitary extension, gate synthesis, repeated-step resource accounting and noise analysis have not been performed.',
            'Retaining the environment and outcome per bin is required in this generic purification if one intends to reverse the entire modeled history.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cavity-dim', type=int, default=3)
    parser.add_argument('--cutoff', type=float, default=1e-12)
    parser.add_argument('--states', type=int, default=8)
    parser.add_argument('--output', type=Path, help='write JSON summary; refuses to overwrite existing file')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('output exists; choose a fresh path')
    result = assess(Parameters(n_cavity=args.cavity_dim), cutoff=args.cutoff, random_states=args.states)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
