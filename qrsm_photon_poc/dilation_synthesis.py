"""Bounded synthesis of a small approximate photon-instrument dilation.

This is a classical Qiskit synthesis experiment on the cavity-dimension-2
simulator, not an optical experiment or a quantum-hardware result. The Choi
cutoff is deliberately aggressive enough to make a generic isometry small.
The instrument maps are compared with the full cutoff-2 simulator; no claim is
made about the higher-dimensional cavity-3 model or real optical systems.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import Isometry
from qiskit.quantum_info import Statevector

from dilation_feasibility import (flagged_isometry, kraus_from_superoperator,
                                  kraus_superoperator, normalize_completeness)
from qrsm_photon import Parameters, instruments


def enforce_memory_limit(memory_mb: int):
    """Enforce per-process address-space limit on Windows or POSIX.

    On Windows this requires pywin32; failure to apply the limit stops the
    worker before synthesis. The job handle remains alive until process exit.
    """
    limit = memory_mb * 1024 * 1024
    if os.name == 'nt':
        try:
            import win32api
            import win32job
            import uuid
            job = win32job.CreateJobObject(None, 'codex-synthesis-' + uuid.uuid4().hex)
            info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
            info['ProcessMemoryLimit'] = limit
            info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
            win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)
            win32job.AssignProcessToJobObject(job, win32api.GetCurrentProcess())
            return job  # retain handle until the worker exits
        except Exception as exc:
            raise RuntimeError(f'could not enforce Windows process memory limit: {exc}') from exc
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    return None


def flag_branch(statevector: np.ndarray, d: int, flag: int):
    """Reduced unnormalized system state for flag b; V rows use 2*k+b blocks."""
    if flag not in (0, 1) or len(statevector) % (2*d):
        raise ValueError('invalid flag or output dimension')
    amplitudes = statevector.reshape((-1, 2, d))[:, flag, :]
    return amplitudes.T @ amplitudes.conj()


def validate_implementation(errors: dict[str, float], tolerance: float = 1e-8):
    """Check numerical circuit implementation, not original-model accuracy."""
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValueError('implementation tolerance must be finite and positive')
    return {'tolerance': tolerance, 'errors': errors,
            'passed': all(math.isfinite(value) and value <= tolerance for value in errors.values())}


def run_case(cutoff=.03, max_qubits=7):
    start = time.monotonic()
    params = Parameters(n_cavity=2)
    d = 8
    maps = instruments(params)[:2]
    no, no_report = kraus_from_superoperator(maps[0], d, cutoff)
    click, click_report = kraus_from_superoperator(maps[1], d, cutoff)
    no, click, normalization = normalize_completeness(no, click)
    V, dpad, env_dim = flagged_isometry(no, click)
    completeness_error = float(np.linalg.norm(V.conj().T @ V-np.eye(dpad), ord=2))
    total_qubits = int(math.log2(V.shape[0]))
    if total_qubits > max_qubits:
        raise ValueError(f'construction needs {total_qubits} qubits, exceeding limit {max_qubits}')
    if dpad != d or V.shape[0] != 2*env_dim*d:
        raise ValueError('unexpected padded isometry dimensions')
    start_circuit = QuantumCircuit(total_qubits, name='photon_isometry')
    start_circuit.append(Isometry(V, 0, 0), list(range(total_qubits)))
    compiled = transpile(start_circuit, basis_gates=['u', 'cx'],
                         optimization_level=1, seed_transpiler=13)

    # Full clean-ancilla action on all 8 input-basis states validates common
    # phases across columns, rather than merely matching each independently.
    columns = []
    for i in range(d):
        columns.append(Statevector.from_int(i, 2**total_qubits).evolve(compiled).data)
    actual = np.stack(columns, axis=1)
    overlap = np.vdot(V, actual)
    common_phase = overlap/abs(overlap) if abs(overlap) else 1.0
    isometry_error = float(np.linalg.norm(actual-common_phase*V, ord=2))

    rng = np.random.default_rng(41)
    inputs = [np.eye(d, dtype=complex)[:,0], np.eye(d, dtype=complex)[:,d-1],
              np.ones(d, dtype=complex)/np.sqrt(d)]
    for _ in range(3):
        psi = rng.normal(size=d) + 1j*rng.normal(size=d)
        inputs.append(psi/np.linalg.norm(psi))
    max_inverse_error = 0.0
    max_approx_probability_error = max_original_probability_error = 0.0
    max_approx_state_error = max_original_state_error = 0.0
    max_original_conditional_error = 0.0
    checked = 0
    for psi in inputs:
        initial = np.zeros(2**total_qubits, complex)
        initial[:d] = psi
        output = Statevector(initial).evolve(compiled)
        rewound = output.evolve(compiled.inverse()).data
        phase = np.vdot(initial, rewound)
        if abs(phase) < 1e-12:
            raise FloatingPointError('inverse result has near-zero overlap with input')
        max_inverse_error = max(max_inverse_error,
                                float(np.linalg.norm(rewound - (phase/abs(phase))*initial)))
        rho = np.outer(psi, psi.conj())
        for b, (S, ops) in enumerate(zip(maps, (no, click))):
            measured = flag_branch(output.data, d, b)
            approx = sum((K @ rho @ K.conj().T for K in ops), np.zeros((d,d), complex))
            original = (S @ rho.reshape(-1, order='F')).reshape((d,d), order='F')
            probabilities = [float(np.trace(x).real) for x in (measured, approx, original)]
            max_approx_probability_error = max(max_approx_probability_error, abs(probabilities[0]-probabilities[1]))
            max_original_probability_error = max(max_original_probability_error, abs(probabilities[0]-probabilities[2]))
            max_approx_state_error = max(max_approx_state_error, float(np.linalg.norm(measured-approx)))
            max_original_state_error = max(max_original_state_error, float(np.linalg.norm(measured-original)))
            if probabilities[0] > 1e-12 and probabilities[2] > 1e-12:
                max_original_conditional_error = max(max_original_conditional_error,
                    float(np.linalg.norm(measured/probabilities[0]-original/probabilities[2])))
                checked += 1

    validation = validate_implementation({
        'retained_isometry_completeness_spectral_error': completeness_error,
        'compiled_isometry_spectral_error': isometry_error,
        'compiled_inverse_vector_error_max': max_inverse_error,
        'synthesized_vs_retained_state_error_max': max_approx_state_error,
        'synthesized_vs_retained_probability_error_max': max_approx_probability_error,
    })
    return {
        'status': 'completed' if validation['passed'] else 'failed_validation',
        'seconds': time.monotonic()-start, 'implementation_validation': validation,
        'model': {'cavity_dimension': 2, 'system_dimension': d, 'absolute_choi_cutoff': cutoff,
                  'retained_no_click_components': len(no), 'retained_click_components': len(click),
                  'system_qubits': 3, 'flag_qubits': 1, 'environment_qubits': int(math.log2(env_dim)),
                  'total_qubits': total_qubits, 'isometry_shape': list(V.shape)},
        'approximation': {'no_click_superoperator_frobenius_error': float(np.linalg.norm(kraus_superoperator(no,d)-maps[0])),
                          'click_superoperator_frobenius_error': float(np.linalg.norm(kraus_superoperator(click,d)-maps[1])),
                          'no_click_choi': no_report, 'click_choi': click_report,
                          'normalization': normalization},
        'synthesis': {'compiler': 'Qiskit Isometry, generic u,cx; optimization level 1; seed 13',
                      'compiled_cx': int(compiled.count_ops().get('cx',0)),
                      'compiled_depth': int(compiled.depth()),
                      'compiled_instruction_count': len(compiled.data),
                      'common_phase_aligned_isometry_spectral_error': isometry_error,
                      'all_input_basis_columns_checked': d,
                      'inverse_vector_error_max': max_inverse_error},
        'state_checks': {'input_states': len(inputs), 'nonzero_branches_compared': checked,
                         'synthesized_vs_retained_unnormalized_state_error_max': max_approx_state_error,
                         'synthesized_vs_retained_probability_error_max': max_approx_probability_error,
                         'synthesized_vs_original_unnormalized_state_error_max': max_original_state_error,
                         'synthesized_vs_original_probability_error_max': max_original_probability_error,
                         'synthesized_vs_original_conditional_state_error_max': max_original_conditional_error},
        'limitations': [
            'Aggressive absolute Choi cutoff discards components; the trace-preserving correction changes the original instrument.',
            'Frobenius and sampled-state errors are not certified diamond-norm bounds.',
            'This is a finite cutoff-2 synthetic system, not the cutoff-3 or a converged optical model.',
            'The gate counts are generic and noiseless; no target routing, measurement, repetitions, resource estimation or quantum hardware.',
            'Inversion applies to the simulated circuit and retained coherent environment, not a measured photon or a dissipative physical experiment.',
        ]}


def worker(cutoff, max_qubits, memory_mb, queue):
    try:
        memory_handle = enforce_memory_limit(memory_mb)
        report = run_case(cutoff, max_qubits)
        report['worker_memory_limit_mb'] = memory_mb
        # Keep the Windows job object alive for the whole computation.
        _ = memory_handle
        queue.put(report)
    except Exception as exc:
        queue.put({'status': 'failed', 'error': f'{type(exc).__name__}: {exc}',
                   'worker_memory_limit_mb': memory_mb})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cutoff', type=float, default=.03)
    parser.add_argument('--timeout', type=float, default=90)
    parser.add_argument('--memory-mb', type=int, default=1024)
    parser.add_argument('--max-qubits', type=int, default=7)
    parser.add_argument('--output', type=Path, help='JSON summary; refuses to overwrite existing file')
    args = parser.parse_args()
    if not math.isfinite(args.cutoff) or args.cutoff <= 0 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('cutoff and timeout must be finite and positive')
    if args.memory_mb < 512 or not 3 <= args.max_qubits <= 8:
        parser.error('memory limit >=512 MB and 3 <= max-qubits <= 8 required')
    if args.output and args.output.exists():
        parser.error('output exists; choose a fresh path')
    ctx = mp.get_context('spawn')
    queue = ctx.Queue()
    process = ctx.Process(target=worker, args=(args.cutoff, args.max_qubits, args.memory_mb, queue))
    print(f'Synthesizing cutoff-2 photon model with cutoff {args.cutoff:g}; time limit {args.timeout:g}s, '
          f'process memory limit {args.memory_mb} MB...', file=sys.stderr, flush=True)
    process.start()
    process.join(args.timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        result = {'status': 'timeout', 'timeout_seconds': args.timeout}
    elif process.exitcode != 0:
        result = {'status': 'process_failed', 'exitcode': process.exitcode}
    else:
        try:
            result = queue.get(timeout=3)
        except Exception as exc:
            result = {'status': 'no_result', 'error': str(exc)}
    queue.close()
    result['environment'] = {'qiskit_version': qiskit.__version__, 'python_version': platform.python_version(),
                             'memory_limit_mb': args.memory_mb, 'timeout_seconds': args.timeout}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if result['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
