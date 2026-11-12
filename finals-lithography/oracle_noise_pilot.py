"""Small target-aware noise-model pilot, not a real IBM hardware run.

Compare the enumerated and reversible-counter oracles on the same seeded,
synthetic 10-qubit line target. Qiskit's GenericBackendV2 samples made-up
device properties from historical ranges; Aer uses its generated gate and
readout noise. The circuits, logical sizes and resulting layouts differ. This
is a limited diagnostic, not a benchmark of a real device or of lithography.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from pathlib import Path

import qiskit
import qiskit_aer
from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator

from lithography import exact_distribution
from oracle_comparison import amplified_circuit


def wilson(successes: int, trials: int, z: float = 1.959963984540054):
    """Binomial Wilson interval: statistical shot uncertainty only."""
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError('invalid binomial counts')
    p = successes/trials
    z2 = z*z
    center = (p + z2/(2*trials))/(1+z2/trials)
    radius = z*math.sqrt(p*(1-p)/trials + z2/(4*trials*trials))/(1+z2/trials)
    return [0.0 if successes == 0 else max(0.0, center-radius),
            1.0 if successes == trials else min(1.0, center+radius)]


def conditional_score(counts: dict[str, int], n: int, p: float):
    """Calculate accepted-history TV and a conservative finite-shot bound.

    The 95% bound follows from a union bound over the n+1 accepted histories
    and Hoeffding's inequality. It is conditional on the number accepted and
    applies to independent shots and the fixed model. It does not capture
    model mismatch, hardware drift or any calibration uncertainty.
    """
    histogram = {}
    total = hits = 0
    for bitstring, count in counts.items():
        value = int(bitstring.replace(' ', ''), 2)
        total += count
        if value.bit_count() < 2:
            hits += count
            key = ''.join(str((value >> i) & 1) for i in range(n))
            histogram[key] = histogram.get(key, 0) + count
    output = {'shots': total, 'accepted': hits, 'hit_probability': hits/total,
              'hit_wilson_95_percent_interval': wilson(hits, total),
              'accepted_counts': histogram, 'conditional_tv': None,
              'conditional_tv_95_percent_finite_shot_bound': None}
    if not hits:
        return output
    expected = exact_distribution(n, p, 2)['conditional_histories']
    tv = .5*sum(abs(histogram.get(k, 0)/hits-v) for k, v in expected.items())
    categories = len(expected)
    radius = .5*categories*math.sqrt(math.log(2*categories/.05)/(2*hits))
    output['conditional_tv'] = tv
    output['conditional_tv_95_percent_finite_shot_bound'] = [max(0, tv-radius), min(1, tv+radius)]
    return output


def pilot(sizes=(5, 7), shots=256, seed=77):
    if shots < 1:
        raise ValueError('shots must be positive')
    backend = GenericBackendV2(num_qubits=10, basis_gates=['rz', 'sx', 'x', 'cx'],
                               coupling_map=CouplingMap.from_line(10), seed=seed, noise_info=True)
    simulator = AerSimulator.from_backend(backend, method='matrix_product_state', max_parallel_threads=1)
    rows = []
    for n in sizes:
        for offset, style in enumerate(('enumerated', 'counter')):
            unitary, _ = amplified_circuit(n, .8, style)
            if unitary.num_qubits > 10:
                raise ValueError('pilot target has only 10 qubits')
            measured = QuantumCircuit(unitary.num_qubits, n)
            measured.compose(unitary, inplace=True)
            measured.measure(range(n), range(n))
            isa = transpile(measured, backend=backend, optimization_level=1, seed_transpiler=13)
            sim_seed = 5000 + 10*n + offset
            print(f'Running n={n}, {style}, {shots} noisy shots on the local simulator...',
                  file=sys.stderr, flush=True)
            counts = simulator.run(isa, shots=shots, seed_simulator=sim_seed).result().get_counts()
            score = conditional_score(counts, n, .8)
            active = sorted({isa.find_bit(q).index for item in isa.data
                             if item.operation.name != 'barrier' for q in item.qubits})
            final = isa.layout.final_index_layout(filter_ancillas=True) if isa.layout else list(range(unitary.num_qubits))
            rows.append({'sites': n, 'oracle': style,
                         'logical_qubits': unitary.num_qubits,
                         'active_physical_qubits': active,
                         'final_physical_layout_by_logical_qubit': [int(x) for x in final],
                         'compiled_cx': int(isa.count_ops().get('cx', 0)),
                         'compiled_depth': int(isa.depth()),
                         'simulator_seed': sim_seed, 'results': score})
    return {'configuration': {'backend': 'synthetic GenericBackendV2, not an actual IBM device',
                              'target_qubits': 10, 'topology': 'bidirectional line',
                              'device_property_seed': seed,
                              'compilation': 'target-aware level 1, seed_transpiler 13',
                              'noise': 'Aer noise model generated from synthetic target properties, not observed calibrations',
                              'simulator_method': 'matrix_product_state stochastic trajectories',
                              'readout_correction': False, 'shots_per_circuit': shots,
                              'qiskit_version': qiskit.__version__, 'qiskit_aer_version': qiskit_aer.__version__,
                              'python_version': platform.python_version()},
            'rows': rows,
            'limitations': [
                'The wafer model and device target are synthetic; there are no QPU or measured wafer results.',
                'Different qubit counts and compiler-selected layouts confound any attribution of changes to oracle design.',
                'Raw accepted outcomes include false hits from gate and readout noise; higher hit rate is not proof of better sampling.',
                'The conditional TV bound covers finite-shot error only for independent simulator draws and a fixed reference model; it is conservative and often broad.',
                'Noise-model fidelity to actual hardware is unvalidated; topology, calibration, drift, idle noise, and compiler settings can alter results.',
                'Single target, one simulator seed per circuit, and a modest shot budget cannot establish general performance or a speed advantage.',
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shots', type=int, default=256)
    parser.add_argument('--seed', type=int, default=77)
    parser.add_argument('--output', type=Path, help='write JSON without overwriting an existing file')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('output already exists; choose a fresh path')
    result = pilot(shots=args.shots, seed=args.seed)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    for row in result['rows']:
        x = row['results']
        print(f"n={row['sites']} {row['oracle']}: {row['compiled_cx']} CX, depth {row['compiled_depth']}, "
              f"hits {x['accepted']}/{x['shots']}, TV {x['conditional_tv']}")
    print('Synthetic target + Aer noise simulation only, not real hardware.')


if __name__ == '__main__':
    main()
