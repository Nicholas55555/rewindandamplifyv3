"""Amplify click histories in a small coherently dilated photon model.

This explicitly connects the finite-bin open-system photon instrument with
amplitude amplification. Two independently initialized flag/environment
registers retain the information needed to reverse the *model circuit*.

The calculation is an ideal Qiskit statevector experiment using the
cavity-dimension-2 model and an intentionally coarse, normalized Choi
truncation. It is not a real optical measurement, calibrated experiment,
multi-step noise simulation, or quantum speedup claim. See README.md.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import Isometry
from qiskit.quantum_info import Statevector

from dilation_feasibility import (flagged_isometry, kraus_from_superoperator,
                                  kraus_superoperator, normalize_completeness)
from qrsm_photon import Parameters, instruments, init_state


def make_instrument(cutoff: float = .03):
    """Return retained TP instrument, original maps, and padded isometry."""
    if not math.isfinite(cutoff) or cutoff <= 0:
        raise ValueError('cutoff must be finite and positive')
    dimension = 8  # defect qubit × emitter qubit × two-level cavity
    original = instruments(Parameters(n_cavity=2))[:2]
    no_ops = kraus_from_superoperator(original[0], dimension, cutoff)[0]
    click_ops = kraus_from_superoperator(original[1], dimension, cutoff)[0]
    no_ops, click_ops, norm_info = normalize_completeness(no_ops, click_ops)
    retained = [kraus_superoperator(k, dimension) for k in (no_ops, click_ops)]
    isometry, padded, environment = flagged_isometry(no_ops, click_ops)
    if padded != dimension:
        raise RuntimeError('Unexpected physical system padding')
    return original, retained, isometry, environment, norm_info


def prepare_two_bins(isometry: np.ndarray, environment_dimension: int):
    """Compose two isometries with disjoint clean outcome/environment qubits.

    Qubit indices: system 0..2; then first flag and environment; then second
    flag and environment. The system is reused; all record/environment qubits
    remain coherent and available for uncomputation.
    """
    env_bits = int(math.log2(environment_dimension))
    if 2**env_bits != environment_dimension:
        raise ValueError('environment dimension must be a power of two')
    one_width = 4 + env_bits
    flag1, flag2 = 3, 4 + env_bits
    width = 3 + 2*(1+env_bits)
    if isometry.shape != (2**one_width, 8):
        raise ValueError('isometry dimensions do not match register allocation')
    if width > 13:
        raise ValueError('two-bin experiment limited to 13 circuit qubits')
    one = QuantumCircuit(one_width, name='photon_bin')
    one.append(Isometry(isometry, 0, 0), list(range(one_width)))
    out = QuantumCircuit(width, name='two_bin_preparation')
    out.compose(one, qubits=[0, 1, 2, flag1] + list(range(4, 4+env_bits)), inplace=True)
    out.compose(one, qubits=[0, 1, 2, flag2] + list(range(flag2+1, width)), inplace=True)
    return out, (flag1, flag2), env_bits


def amplified_two_bins(preparation: QuantumCircuit, flags: tuple[int, int], event: str):
    """Build one Grover round for the last-click or double-click predicate."""
    if event not in ('last', 'double'):
        raise ValueError("event must be 'last' or 'double'")
    circuit = preparation.copy(name='two_bin_amplified')
    if event == 'double':
        circuit.cz(*flags)
    else:
        circuit.z(flags[1])
    circuit.compose(preparation.inverse(), inplace=True)
    # Phase flip the full all-zero input state, including flags and environment.
    qubits = list(range(circuit.num_qubits))
    circuit.x(qubits)
    circuit.h(qubits[-1])
    circuit.mcx(qubits[:-1], qubits[-1])
    circuit.h(qubits[-1])
    circuit.x(qubits)
    circuit.compose(preparation, inplace=True)
    return circuit


def outcome_states(vector: np.ndarray, env_bits: int):
    """Trace both environment registers, preserving each unnormalized branch."""
    environment = 1 << env_bits
    expected = 8*2*environment*2*environment
    if vector.shape != (expected,):
        raise ValueError('statevector length does not match register layout')
    # Qiskit little-endian order, reshaped from most to least significant:
    # environment2, flag2, environment1, flag1, 8-dimensional system.
    tensor = vector.reshape((environment, 2, environment, 2, 8))
    branches = {}
    for first in (0, 1):
        for second in (0, 1):
            amplitudes = tensor[:, second, :, first, :].reshape(-1, 8)
            branches[(first, second)] = amplitudes.T @ amplitudes.conj()
    return branches


def channel_states(maps):
    """Reference two-step unnormalized branches from column-vectorized maps."""
    initial = init_state(Parameters(n_cavity=2))
    return {(a, b): (maps[b] @ maps[a] @ initial).reshape((8, 8), order='F')
            for a in (0, 1) for b in (0, 1)}


def select(branches, event):
    keys = [(1, 1)] if event == 'double' else [(0, 1), (1, 1)]
    state = sum((branches[k] for k in keys), np.zeros((8, 8), dtype=complex))
    probability = float(np.trace(state).real)
    if probability <= 0:
        raise ValueError('selected event has zero probability')
    return probability, state/probability


def trace_distance(a, b):
    """Trace distance for the two Hermitian conditional density matrices."""
    diff = (a-b + (a-b).conj().T)/2
    return float(.5*np.abs(np.linalg.eigvalsh(diff)).sum())


def run(cutoff=.03, event='double', compile_counts=True):
    original, retained, V, env_dimension, normalization = make_instrument(cutoff)
    prep, flags, env_bits = prepare_two_bins(V, env_dimension)
    base = outcome_states(Statevector.from_instruction(prep).data, env_bits)
    retained_branches = channel_states(retained)
    original_branches = channel_states(original)
    selected_probability, selected_state = select(base, event)
    retained_probability, retained_state = select(retained_branches, event)
    original_probability, original_state = select(original_branches, event)
    amplified = amplified_two_bins(prep, flags, event)
    amplified_branches = outcome_states(Statevector.from_instruction(amplified).data, env_bits)
    amplified_probability, amplified_state = select(amplified_branches, event)
    theory = math.sin(3*math.asin(math.sqrt(selected_probability)))**2
    compiled = (transpile(amplified, basis_gates=['u', 'cx'], optimization_level=1,
                          seed_transpiler=13) if compile_counts else None)
    max_branch_error = max(float(np.linalg.norm(base[k]-retained_branches[k])) for k in base)
    return {
        'model': {'cavity_dimension': 2, 'physical_system_dimension': 8,
                  'choi_absolute_cutoff': cutoff, 'time_bins': 2, 'event': event,
                  'system_qubits': 3, 'outcome_flags': 2,
                  'environment_qubits_per_bin': env_bits, 'total_qubits': prep.num_qubits,
                  'simulator': 'ideal Qiskit statevector; no hardware noise'},
        'event': {'original_open_system_probability': original_probability,
                  'retained_model_probability': retained_probability,
                  'qiskit_preparation_probability': selected_probability,
                  'qiskit_amplified_probability': amplified_probability,
                  'one_round_theoretical_probability': theory,
                  'retained_vs_original_conditional_state_trace_distance': trace_distance(retained_state, original_state),
                  'amplified_vs_retained_conditional_state_trace_distance': trace_distance(amplified_state, retained_state),
                  'preparation_vs_retained_max_branch_frobenius_error': max_branch_error},
        'history_probabilities': {
            ''.join(map(str, k)): {'original': float(np.trace(original_branches[k]).real),
                                   'retained': float(np.trace(retained_branches[k]).real),
                                   'amplified': float(np.trace(amplified_branches[k]).real)}
            for k in original_branches},
        'compilation': (None if compiled is None else {
            'basis': ['u', 'cx'], 'optimization_level': 1, 'seed_transpiler': 13,
            'cx_gates': int(compiled.count_ops().get('cx', 0)), 'depth': int(compiled.depth()),
            'contains': 'two-bin preparation, event oracle, inverse preparation, full reflection, replay'}),
        'normalization': normalization,
        'limitations': [
            'Synthetic cavity-2 model with coarse Choi truncation; physical parameters are not calibrated.',
            'One modeled two-bin query, ideal statevector only; no real photonic hardware or speedup.',
            'Environment and outcome registers are retained; generic circuit costs exclude topology and noise.',
            'State trace distance is for this selected input and event, not a worst-case guarantee.',
            'Inversion reverses the coherent model and retained environment, not photons already detected in a lab.',
        ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cutoff', type=float, default=.03)
    parser.add_argument('--event', choices=('last', 'double'), default='double')
    parser.add_argument('--no-compile', action='store_true', help='skip expensive gate accounting')
    parser.add_argument('--output', type=Path, help='write JSON; refuse to replace existing files')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('output exists; choose a new path')
    result = run(args.cutoff, args.event, not args.no_compile)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
