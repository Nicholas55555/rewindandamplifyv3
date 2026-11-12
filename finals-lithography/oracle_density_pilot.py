"""Deterministic density-matrix check on the synthetic line-target pilot.

The seed, logical circuits, target, compilation settings and local gate/readout
noise come from oracle_noise_pilot.py. A compacted circuit contains only active
physical qubits. Measurement is removed before simulation and its independent
readout matrices are applied analytically afterward. This avoids finite-shot
uncertainty but remains a toy noise model, not hardware evidence.

Every case runs in a fresh subprocess with an explicit time limit; a timeout is
recorded as unavailable, never as a numerical result. Aer memory is capped, but
the cap does not bound total operating-system process memory.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import platform
import sys
import time
from pathlib import Path

import numpy as np
import qiskit
import qiskit_aer
from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.noise.device.models import basic_device_gate_errors, basic_device_readout_errors

from lithography import exact_distribution
from oracle_comparison import amplified_circuit


def apply_readout(probabilities: np.ndarray, readout_matrices: list[np.ndarray]):
    """Apply P(measured | prepared) matrices in little-endian bit order.

    Each input matrix is in Qiskit's convention: rows = true values,
    columns = measured values. This assumes independent per-qubit readout.
    """
    n = len(readout_matrices)
    if probabilities.shape != (2**n,):
        raise ValueError('probability shape does not match readout matrices')
    arr = probabilities.reshape((2,)*n)
    for bit, matrix in enumerate(readout_matrices):
        matrix = np.asarray(matrix, dtype=float)
        if matrix.shape != (2, 2) or not np.allclose(matrix.sum(axis=1), 1):
            raise ValueError('each readout matrix must be 2x2 row stochastic')
        axis = n - 1 - bit
        arr = np.moveaxis(np.tensordot(matrix.T, arr, axes=(1, axis)), 0, axis)
    return arr.reshape(-1)


def score_probabilities(distribution: np.ndarray, n: int, p: float = .8):
    if distribution.shape != (2**n,):
        raise ValueError('distribution size does not match n')
    expected = exact_distribution(n, p, 2)['conditional_histories']
    hit = sum(distribution[i] for i in range(2**n) if i.bit_count() < 2)
    if hit <= 0:
        return {'hit_probability': float(hit), 'conditional_tv': None}
    conditional = {}
    for i in range(2**n):
        if i.bit_count() < 2:
            key = ''.join(str((i >> bit) & 1) for bit in range(n))
            conditional[key] = float(distribution[i]/hit)
    tv = .5*sum(abs(conditional[k]-v) for k,v in expected.items())
    return {'hit_probability': float(hit), 'conditional_tv': float(tv),
            'conditional_histories': conditional}


def compact_and_measurement_map(compiled, n_data: int):
    """Remove terminal measurements; retain physical-to-compact mapping.

    This model has only terminal measurements, each mapping one physical
    qubit to its original data bit. Refuse unexpected classical operations.
    """
    physical = {q: i for i, q in enumerate(compiled.qubits)}
    active = sorted({physical[q] for inst in compiled.data if inst.operation.name != 'barrier' for q in inst.qubits})
    to_compact = {q: i for i, q in enumerate(active)}
    measured = [None]*n_data
    small = QuantumCircuit(len(active))
    saw_measurement = False
    for inst in compiled.data:
        op = inst.operation
        if op.name == 'barrier':
            continue
        if op.name == 'measure':
            saw_measurement = True
            cb = compiled.find_bit(inst.clbits[0]).index
            if cb >= n_data or measured[cb] is not None:
                raise ValueError('unexpected or duplicate measurement target')
            measured[cb] = physical[inst.qubits[0]]
            continue
        if saw_measurement or inst.clbits:
            raise ValueError('expected only terminal measurements and no classical operations')
        small.append(op, [to_compact[physical[q]] for q in inst.qubits])
    if any(q is None for q in measured):
        raise ValueError('missing logical data measurement')
    return small, active, measured


def simulate_compacted(isa, backend, n: int, max_aer_memory_mb: int = 512):
    """Simulate a compiled circuit on active qubits and apply readout noise."""
    small, active, measurement_phys = compact_and_measurement_map(isa, n)
    mapping = {phys: i for i, phys in enumerate(active)}
    small.save_probabilities([mapping[q] for q in measurement_phys], label='true_data_probabilities')

    # This is the same target-derived local error construction used by Aer
    # from_backend and by the main project's predict() routine. Readout is
    # applied separately and deterministically after the saved probabilities.
    noise = NoiseModel(basis_gates=['rz', 'sx', 'x', 'cx', 'id'])
    for gate, qubits, error in basic_device_gate_errors(target=backend.target):
        if all(q in mapping for q in qubits):
            noise.add_quantum_error(error, gate, [mapping[q] for q in qubits], warnings=False)
    readout = {q[0]: error for q, error in basic_device_readout_errors(target=backend.target)}
    simulator = AerSimulator(method='density_matrix', noise_model=noise, max_parallel_threads=1,
                             max_memory_mb=max_aer_memory_mb)
    result = simulator.run(small, shots=1).result()
    if not result.success:
        raise RuntimeError(f'Aer simulation failed: {result.status}')
    true_probs = np.asarray(result.data(0)['true_data_probabilities'], dtype=float)
    readout_matrices = [np.asarray(readout[q].probabilities, dtype=float) for q in measurement_phys]
    raw_probs = apply_readout(true_probs, readout_matrices)
    return true_probs, raw_probs, active, measurement_phys


def deterministic_case(n: int, style: str, seed: int = 77, max_aer_memory_mb: int = 512):
    start = time.monotonic()
    backend = GenericBackendV2(num_qubits=10, basis_gates=['rz', 'sx', 'x', 'cx'],
                               coupling_map=CouplingMap.from_line(10), seed=seed, noise_info=True)
    unitary, _ = amplified_circuit(n, .8, style)
    measured = QuantumCircuit(unitary.num_qubits, n)
    measured.compose(unitary, inplace=True)
    measured.measure(range(n), range(n))
    isa = transpile(measured, backend=backend, optimization_level=1, seed_transpiler=13)
    true_probs, raw_probs, active, measurement_phys = simulate_compacted(isa, backend, n, max_aer_memory_mb)
    return {'status': 'completed', 'sites': n, 'oracle': style, 'seconds': time.monotonic()-start,
            'logical_qubits': unitary.num_qubits, 'active_physical_qubits': active,
            'data_measurement_physical_qubits_in_bit_order': measurement_phys,
            'compiled_cx': int(isa.count_ops().get('cx', 0)), 'compiled_depth': int(isa.depth()),
            'before_readout': score_probabilities(true_probs, n),
            'after_readout': score_probabilities(raw_probs, n),
            'before_readout_probability_sum': float(true_probs.sum()),
            'after_readout_probability_sum': float(raw_probs.sum())}


def worker(n, style, seed, max_aer_memory_mb, queue):
    try:
        queue.put(deterministic_case(n, style, seed, max_aer_memory_mb))
    except Exception as exc:
        queue.put({'status': 'failed', 'sites': n, 'oracle': style,
                   'error': f'{type(exc).__name__}: {exc}'})


def bounded_case(n, style, seed, max_aer_memory_mb, timeout):
    ctx = mp.get_context('spawn')
    queue = ctx.Queue()
    process = ctx.Process(target=worker, args=(n, style, seed, max_aer_memory_mb, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        queue.close()
        return {'status': 'timeout', 'sites': n, 'oracle': style, 'timeout_seconds': timeout}
    if process.exitcode != 0:
        queue.close()
        return {'status': 'process_failed', 'sites': n, 'oracle': style, 'exitcode': process.exitcode}
    try:
        value = queue.get(timeout=2)
    except Exception as exc:
        value = {'status': 'no_result', 'sites': n, 'oracle': style, 'error': str(exc)}
    queue.close()
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', type=int, choices=(5, 7), default=5)
    parser.add_argument('--timeout', type=float, default=45, help='maximum wall seconds per case')
    parser.add_argument('--memory-mb', type=int, default=512, help='Aer internal memory limit, not OS limit')
    parser.add_argument('--output', type=Path, help='write JSON without overwriting an existing file')
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.memory_mb < 64:
        parser.error('timeout must be finite and positive and memory limit >= 64 MB')
    if args.output and args.output.exists():
        parser.error('output already exists; choose a fresh path')
    rows = []
    for style in ('enumerated', 'counter'):
        print(f'Density simulation: n={args.sites}, {style}, {args.timeout:g}s limit...',
              file=sys.stderr, flush=True)
        row = bounded_case(args.sites, style, 77, args.memory_mb, args.timeout)
        rows.append(row)
        print(f"  {row['status']}", file=sys.stderr, flush=True)
    report = {'configuration': {'synthetic_target': 'seeded GenericBackendV2 10-qubit bidirectional line; not real hardware',
                                 'qiskit_version': qiskit.__version__, 'qiskit_aer_version': qiskit_aer.__version__,
                                 'python_version': platform.python_version(), 'seed_transpiler': 13,
                                 'target_seed': 77, 'optimization_level': 1,
                                 'method': 'density_matrix, no shot sampling; independent readout applied analytically',
                                 'aer_internal_memory_limit_mb': args.memory_mb, 'per_case_timeout_seconds': args.timeout},
              'rows': rows,
              'limitations': ['Synthetic threshold process and synthetic noisy target, not a real wafer or processor.',
                              'Error model has local gate/readout errors; it does not establish performance under device drift, crosstalk or unmodeled effects.',
                              'Oracle circuits use different qubit counts and can have different physical layouts.',
                              'Probabilities are deterministic only within this finite synthetic model; no hardware or end-to-end advantage is established.']}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if any(row['status'] != 'completed' for row in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
