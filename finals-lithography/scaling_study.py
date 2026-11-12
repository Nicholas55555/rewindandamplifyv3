"""Compare one ideal amplification round for a family of tiny threshold models.

Each case explicitly marks every failing history. The purpose is to expose
the preparation and gate-accounting issues in a transparent toy experiment,
not to benchmark an industrial process, prove a lower bound, or claim speedup.
No actual chip or wafer data is used.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

from lithography import quantum_demo


def study(sizes=range(3, 8), absorption_probability=.8, threshold=2):
    import qiskit

    records = []
    for n in sizes:
        circuit = quantum_demo(n=n, p=absorption_probability,
                               threshold=threshold, iterations=1)
        p_before = circuit['event_probability_before']
        p_after = circuit['event_probability_after']
        calls = circuit['preparation_calls'] + circuit['inverse_preparation_calls']
        records.append({
            'sites_and_logical_qubits': n,
            'failing_histories_explicitly_marked': circuit['oracle_marked_histories'],
            'event_probability_before': p_before,
            'ideal_qiskit_event_probability_after': p_after,
            'analytic_one_round_probability': circuit['theoretical_after'],
            'conditional_history_total_variation': circuit['conditional_total_variation'],
            'compiled_generic_cx': circuit['compiled_cx_gates'],
            'compiled_generic_depth': circuit['compiled_depth'],
            'preparation_calls_per_circuit': circuit['preparation_calls'],
            'inverse_preparation_calls_per_circuit': circuit['inverse_preparation_calls'],
            'oracle_calls_per_circuit': circuit['oracle_calls'],
            'zero_reflection_calls_per_circuit': circuit['zero_reflection_calls'],
            # Geometric expectations for independent ideal shots, not runtime.
            'expected_direct_shots_per_event': 1 / p_before,
            'expected_ideal_quantum_shots_per_event': 1 / p_after,
            'expected_quantum_preparation_or_inverse_calls_per_event': calls / p_after,
        })
    return {
        'setup': {
            'model': 'independent binary absorption sites, missing contact if absorptions < threshold',
            'absorption_probability': absorption_probability,
            'failure_threshold': threshold,
            'amplification_rounds': 1,
            'oracle': 'explicitly phase-marks each individual failing history',
            'simulator': 'Qiskit Statevector, ideal and noiseless',
            'transpilation': 'generic u,cx basis, optimization_level=1, no hardware target',
            'qiskit_version': qiskit.__version__,
            'python_version': platform.python_version(),
        },
        'records': records,
        'limitations': [
            'Synthetic uncalibrated threshold model; it is not a physical EUV wafer or resist model.',
            'Oracle explicitly enumerates failing histories; results do not establish scalable oracle construction.',
            'Generic circuit counts omit hardware layout, connectivity, noise, readout, latency and error correction.',
            'Shot and preparation-call estimates are ideal geometric expectations, not observed runtimes or a fair end-to-end speed comparison.',
            'Classical importance sampling and exact inference are serious competing methods; no quantum speedup is demonstrated.',
            'The single fixed round is deliberately held constant; other round counts have different probabilities and costs.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-sites', type=int, default=3)
    parser.add_argument('--max-sites', type=int, default=7)
    parser.add_argument('--output', type=Path, help='write detailed JSON results')
    args = parser.parse_args()
    if not 2 <= args.min_sites <= args.max_sites <= 8:
        parser.error('sizes must satisfy 2 <= min-sites <= max-sites <= 8')
    result = study(range(args.min_sites, args.max_sites + 1))
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Synthetic independent-sites threshold model; one ideal amplification round')
    print('n   original P   ideal P     generic CX   generic depth    conditional TV')
    for row in result['records']:
        print(f"{row['sites_and_logical_qubits']:<3} "
              f"{row['event_probability_before']:<12.8f} "
              f"{row['ideal_qiskit_event_probability_after']:<11.8f} "
              f"{row['compiled_generic_cx']:<12} "
              f"{row['compiled_generic_depth']:<16} "
              f"{row['conditional_history_total_variation']:.2g}")
    print('No hardware or end-to-end quantum advantage is demonstrated.')


if __name__ == '__main__':
    main()
