"""Export guarded local logical circuits and exact references; never submit.

The default ladder reproduces the existing1/2/3-bin optical models and the
correlated2x2 spatial process. Each circuit is measured into ``meas``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import qiskit
from qiskit import qpy

from adapters import (ROOT, build_optical, build_spatial, exact_reference,
                      measured, source_hashes)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf8')


def ladder():
    specs = []
    for cutoff in (.03, .003):
        specs.extend(('optical', {'bins': 1, 'cutoff': cutoff, 'event': 'last', 'rounds': r}) for r in (0, 1))
    for bins, cutoff in ((2, .03), (3, .03), (3, .003)):
        specs.append(('optical', {'bins': bins, 'cutoff': cutoff, 'event': 'last', 'rounds': 0}))
        specs.extend(('optical', {'bins': bins, 'cutoff': cutoff, 'event': e, 'rounds': 1}) for e in ('last', 'all'))
    for style in ('enumerated', 'counter'):
        specs.extend(('spatial', {'style': style, 'rounds': r}) for r in (0, 1, 2))
    return specs


def export(output):
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    if (output/'manifest.json').exists() or (output/'logical.qpy').exists():
        raise FileExistsError('Refusing to replace an existing circuit bundle')
    start = time.perf_counter()
    rows, circuits, arrays = [], [], {}
    for index, (family, options) in enumerate(ladder()):
        begin = time.perf_counter()
        item = build_optical(**options) if family == 'optical' else build_spatial(**options)
        full, validation = exact_reference(item)
        name = item.metadata['id']
        arrays[name] = full
        circuits.append(measured(item))
        row = {'name': name, 'index': index, 'metadata': item.metadata,
               'reference': {'file': 'ideal_probabilities.npz', 'key': name,
                             'shape': list(full.shape),
                             'basis_order': 'integer index uses logical q0 as least significant bit',
                             'target_data_z_marginal': item.target_marginal.tolist()},
               'validation': validation, 'local_build_seconds': time.perf_counter()-begin}
        rows.append(row)
        write(output/'progress.json', {'status': 'building', 'completed': rows})
        print(f'{index+1}/19 {name}: {item.circuit.num_qubits}q; '
              f'{item.circuit.count_ops().get("cx",0)}CX; '
              f'{row["local_build_seconds"]:.2f}s', flush=True)
    with (output/'logical.qpy').open('wb') as file:
        qpy.dump(circuits, file)
    with (output/'logical.qpy').open('rb') as file:
        recovered = qpy.load(file)
    if len(recovered) != len(circuits):
        raise AssertionError('QPY circuit count')
    for expected, actual in zip(circuits, recovered):
        if expected != actual or len(actual.cregs) != 1 or actual.cregs[0].name != 'meas':
            raise AssertionError('QPY exact circuit or measurement-register roundtrip')
    np.savez_compressed(output/'ideal_probabilities.npz', **arrays)
    with np.load(output/'ideal_probabilities.npz', allow_pickle=False) as saved:
        for key, value in arrays.items():
            if not np.array_equal(value, saved[key]):
                raise AssertionError('Reference array roundtrip')
    own_sources = [Path(__file__).resolve(), Path(__file__).with_name('adapters.py'),
                   Path(__file__).with_name('test_adapters.py')]
    manifest = {
        'schema': 'ra-hardware-bundle-v1', 'status': 'validated_local_export',
        'logical_qpy': 'logical.qpy', 'reference_npz': 'ideal_probabilities.npz',
        'circuits': rows, 'qpy_roundtrip_all_equal': True,
        'source_sha256': source_hashes(own_sources),
        'artifact_sha256': {f: sha(output/f) for f in ('logical.qpy', 'ideal_probabilities.npz')},
        'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'qiskit': qiskit.__version__},
        'scope': 'Logical finite-model circuits and exact classical references only. No backend compilation, hardware submission or hardware observation.',
        'measurement_register': 'meas',
        'pairing': 'Fix physical layout within a matching width/family before comparing plain and amplified circuits. Counter plain is padded to14qubits.',
        'unavailable_full_spatial': {
            'cells': 49, 'compact_qubits': 219, 'explicit_clean_qubits': 389,
            'available_device_qubits_reported_by_campaign_owner': 156,
            'status': 'cannot fit full construction on available device; not replaced by2x2',
            'source_results': 'finals-lithography/full_spatial_circuit/results.json',
            'source_sha256': sha(ROOT/'finals-lithography/full_spatial_circuit/results.json')},
        'interpretation': ['Raw event acceptance alone can be increased by noise.',
                           'Compare conditional system/history Z distribution with exact retained-model target, and report accepted-shot counts.',
                           'Optical original-cavity2 and retained-channel errors remain distinct from hardware errors.',
                           'Report spatial workspace leakage without postselecting it away.',
                           'Z distributions cannot certify full conditional density-state fidelity.',
                           '4096shots leaves sparse rare all-click/spatial plain records; do not infer precise conditional answers.'],
        'elapsed_seconds': time.perf_counter()-start,
        'all_checks_passed': True}
    write(output/'manifest.json', manifest)
    write(output/'progress.json', {'status': 'complete', 'circuits': len(rows)})
    print(f'Exported {len(rows)} circuits to {output}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=900.)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        # Existing cross-platform process memory limiter: importing it does not
        # submit jobs or create scientific output. Limit is applied in child.
        sys.path.insert(0, str(ROOT/'qrsm_photon_poc'))
        from dilation_synthesis import enforce_memory_limit
        memory_guard = enforce_memory_limit(3072)
        export(args.output)
        return
    if args.output.exists():
        parser.error('Output directory exists; choose a new path')
    args.output.mkdir(parents=True)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                       MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--output', str(args.output.resolve())]
    begin = time.perf_counter()
    with (args.output/'build.log').open('w', encoding='utf8') as log:
        try:
            result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=args.timeout, check=False)
            status = {'status': 'completed' if result.returncode == 0 else 'failed',
                      'returncode': result.returncode}
        except subprocess.TimeoutExpired:
            status = {'status': 'timeout', 'returncode': None}
    status.update(timeout_seconds=args.timeout, process_memory_limit_mib=3072,
                  elapsed_seconds=time.perf_counter()-begin)
    write(args.output/'build_status.json', status)
    print(json.dumps(status))
    if status['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
