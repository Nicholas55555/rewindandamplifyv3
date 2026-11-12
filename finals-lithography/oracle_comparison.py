"""Compare two exact phase oracles for a tiny synthetic missing-contact model.

The event is that fewer than two of n binary sites absorb. Both full circuits
prepare independent Bernoulli sites, apply one amplitude-amplification round,
and are compiled to the same generic u,cx basis. One oracle marks n+1 failing
patterns individually; the other computes a reversible binary count, marks
counts 0 or 1, then uncomputes the counter. No device or industrial data is
used. This is not a proof of asymptotic complexity or quantum advantage.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
from pathlib import Path

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

from lithography import exact_distribution


def flip_all_zero(circuit: QuantumCircuit, qubits: list[int]) -> None:
    """Phase-flip just the joint |0...0> state on the indicated qubits."""
    if not qubits:
        raise ValueError('at least one qubit is required')
    circuit.x(qubits)
    if len(qubits) == 1:
        circuit.z(qubits[0])
    else:
        circuit.h(qubits[-1])
        circuit.mcx(qubits[:-1], qubits[-1])
        circuit.h(qubits[-1])
    circuit.x(qubits)


def counter_register_bits(n: int) -> int:
    """Enough bits to represent every count in [0,n] without overflow."""
    if n < 2:
        raise ValueError('at least two sites are required')
    return n.bit_length()


def enumerated_oracle(n: int) -> QuantumCircuit:
    """Phase flip the all-zero and n one-hot data states separately."""
    if n < 2:
        raise ValueError('at least two sites are required')
    qc = QuantumCircuit(n, name='enumerated_oracle')
    for pattern in (0, *(1 << i for i in range(n))):
        zeros = [i for i in range(n) if not ((pattern >> i) & 1)]
        if zeros:
            qc.x(zeros)
        qc.h(n-1)
        qc.mcx(list(range(n-1)), n-1)
        qc.h(n-1)
        if zeros:
            qc.x(zeros)
    return qc


def counter_oracle(n: int) -> QuantumCircuit:
    """Compute popcount into a clean counter, mark count < 2, uncompute."""
    width = counter_register_bits(n)
    counter = list(range(n, n + width))  # little endian
    count = QuantumCircuit(n + width, name='compute_popcount')
    for site in range(n):
        # Add the site's bit mod 2**width. High-to-low ordering preserves the
        # original low counter bits until they have controlled each carry.
        for j in range(width-1, -1, -1):
            count.mcx([site] + counter[:j], counter[j])
    qc = QuantumCircuit(n + width, name='counter_oracle')
    qc.compose(count, inplace=True)
    # The count is less than 2 iff all counter bits above bit zero are 0.
    flip_all_zero(qc, counter[1:])
    qc.compose(count.inverse(), inplace=True)
    return qc


def amplified_circuit(n: int, absorption_probability: float, style: str):
    """One round; reflect on data since clean counter remains |0>."""
    if not 0 < absorption_probability < 1:
        raise ValueError('absorption_probability must be in (0,1)')
    if style == 'enumerated':
        oracle = enumerated_oracle(n)
    elif style == 'counter':
        oracle = counter_oracle(n)
    else:
        raise ValueError('unknown oracle style')
    total = oracle.num_qubits
    prep = QuantumCircuit(total, name='prepare')
    prep.ry(2 * math.asin(math.sqrt(absorption_probability)), range(n))
    qc = QuantumCircuit(total, name=f'{style}_one_round')
    qc.compose(prep, inplace=True)
    qc.compose(oracle, inplace=True)
    qc.compose(prep.inverse(), inplace=True)
    # The counter is provably back to |0> after the oracle, so reflecting
    # only the data is equivalent to a joint-zero reflection on this subspace.
    flip_all_zero(qc, list(range(n)))
    qc.compose(prep, inplace=True)
    return qc, oracle


def basis_phase_error(oracle: QuantumCircuit, n: int):
    """Check every data input with workspace initialized to |0>."""
    max_error = 0.0
    for index in range(1 << n):
        initial = Statevector.from_int(index, 2**oracle.num_qubits)
        actual = initial.evolve(oracle).data
        expected = np.zeros_like(actual)
        expected[index] = -1 if index.bit_count() < 2 else 1
        max_error = max(max_error, float(np.max(np.abs(actual-expected))))
    return max_error


def result_for(n: int, p: float, style: str):
    circuit, oracle = amplified_circuit(n, p, style)
    state = Statevector.from_instruction(circuit).data
    distribution = np.abs(state)**2
    data_mask = (1 << n) - 1
    failing = np.array([(i & data_mask).bit_count() < 2 for i in range(len(state))])
    probability = float(distribution[failing].sum())
    if probability <= 0:
        raise ValueError('conditional distribution undefined at zero event probability')
    exact = exact_distribution(n, p, threshold=2)
    actual = {}
    for i, prob in enumerate(distribution):
        pattern = i & data_mask
        if pattern.bit_count() < 2:
            name = ''.join(str((pattern >> site) & 1) for site in range(n))
            actual[name] = actual.get(name, 0.0) + float(prob)/probability
    tv = sum(abs(actual.get(k, 0)-v) for k, v in exact['conditional_histories'].items())/2
    basis_error = basis_phase_error(oracle, n)
    if n == circuit.num_qubits:
        dirty = 0.0
    else:
        dirty = float(distribution[np.arange(len(distribution)) >> n != 0].sum())
    compiled = transpile(circuit, basis_gates=['u', 'cx'], optimization_level=1, seed_transpiler=13)
    return {'style': style, 'data_qubits': n, 'work_qubits': circuit.num_qubits-n,
            'total_qubits': circuit.num_qubits, 'marked_probability_before': exact['failure_probability'],
            'marked_probability_after': probability, 'conditional_history_tv': float(tv),
            'maximum_basis_phase_error': basis_error, 'dirty_work_probability': dirty,
            'generic_cx': int(compiled.count_ops().get('cx', 0)), 'generic_depth': int(compiled.depth())}


def comparison(sizes=range(3, 8), p=.8):
    rows = []
    for n in sizes:
        a, b = result_for(n, p, 'enumerated'), result_for(n, p, 'counter')
        rows.append({'sites': n, 'enumerated': a, 'counter': b,
                     'counter_minus_enumerated_cx': b['generic_cx']-a['generic_cx'],
                     'counter_minus_enumerated_depth': b['generic_depth']-a['generic_depth']})
    return {'configuration': {'absorption_probability': p, 'failure': 'number of absorptions < 2',
                              'grover_rounds': 1, 'simulator': 'ideal Qiskit Statevector',
                              'compilation': 'generic u,cx, optimization level 1, seed_transpiler 13, no backend',
                              'qiskit_version': qiskit.__version__, 'python_version': platform.python_version()},
            'rows': rows,
            'limitations': [
                'Synthetic independent absorption bits and threshold; not a calibrated lithography process.',
                'Oracle behavior is checked for every data basis state with counter initialized to zero.',
                'Gate counts exclude device routing, noise, measurements, sampling repetitions and error correction.',
                'The two implementations use different logical qubit counts; no runtime or real-device advantage is established.',
                'Small n and compiler-specific decomposition do not establish a general scaling law.',
                'No loading or coherent oracle for the separate spatial Poisson/blur model has been constructed.',
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-sites', type=int, default=3)
    parser.add_argument('--max-sites', type=int, default=7)
    parser.add_argument('--output', type=Path, help='write JSON; refuse to overwrite existing files')
    args = parser.parse_args()
    if not 2 <= args.min_sites <= args.max_sites <= 8:
        parser.error('sizes must satisfy 2 <= min-sites <= max-sites <= 8')
    if args.output and args.output.exists():
        parser.error('output already exists; choose a fresh path')
    report = comparison(range(args.min_sites, args.max_sites+1))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('One-round synthetic threshold model, generic compiled u/cx gates')
    print('n   enum cx / depth / qubits    counter cx / depth / qubits   event probability')
    for row in report['rows']:
        e, c = row['enumerated'], row['counter']
        print(f"{row['sites']:<3} {e['generic_cx']:>5} / {e['generic_depth']:<5} / {e['total_qubits']:<3} "
              f"          {c['generic_cx']:>5} / {c['generic_depth']:<5} / {c['total_qubits']:<3} "
              f"      {c['marked_probability_after']:.8f}")
    print('Ideal simulation only; no real wafer, device, or runtime advantage demonstrated.')


if __name__ == '__main__':
    main()
