"""Read-only validation of a logical hardware bundle, optional new receipt."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import qpy

from adapters import ROOT, event_mask, marginal, resources


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(directory):
    folder = Path(directory)
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    assert manifest['schema'] == 'ra-hardware-bundle-v1'
    assert manifest['all_checks_passed']
    sources = dict(manifest['source_sha256'])
    for row in manifest['circuits']:
        for path, digest in row['metadata']['source_sha256'].items():
            assert path not in sources or sources[path] == digest
            sources[path] = digest
    for path, digest in sources.items():
        assert sha(ROOT/path) == digest, f'Source changed: {path}'
    for path, digest in manifest['artifact_sha256'].items():
        assert sha(folder/path) == digest, f'Artifact changed: {path}'
    with (folder/manifest['logical_qpy']).open('rb') as file:
        circuits = qpy.load(file)
    assert len(circuits) == len(manifest['circuits']) == 19
    max_error, max_event_error, max_dirty = 0., 0., 0.
    with np.load(folder/manifest['reference_npz'], allow_pickle=False) as arrays:
        for index, (row, circuit) in enumerate(zip(manifest['circuits'], circuits)):
            assert row['index'] == index and row['name'] == circuit.name
            assert len(circuit.cregs) == 1 and circuit.cregs[0].name == 'meas'
            assert circuit.num_clbits == circuit.num_qubits
            for qubit, instruction in enumerate(circuit.data[-circuit.num_qubits:]):
                assert instruction.operation.name == 'measure'
                assert circuit.find_bit(instruction.qubits[0]).index == qubit
                assert circuit.find_bit(instruction.clbits[0]).index == qubit
            assert resources(circuit.remove_final_measurements(inplace=False)) == row['metadata']['resources']
            probabilities = arrays[row['reference']['key']]
            assert probabilities.shape == (1 << circuit.num_qubits,)
            assert np.all(np.isfinite(probabilities)) and np.min(probabilities) >= 0
            assert abs(probabilities.sum()-1) < 1e-8
            measurement = row['metadata']['measurement']
            actual = marginal(probabilities, measurement['data_marginal_qubits_lsb_first'])
            target = np.array(row['reference']['target_data_z_marginal'])
            error = float(np.max(np.abs(actual-target)))
            event_error = float(abs(actual[event_mask(row['metadata'])].sum()-row['metadata']['expected_event_probability']))
            dirty = abs(float(1-marginal(probabilities, measurement['workspace_qubits'])[0]))
            max_error, max_event_error, max_dirty = max(max_error, error), max(max_event_error, event_error), max(max_dirty, dirty)
            assert max(error, event_error, dirty) < 1e-8
    full = manifest['unavailable_full_spatial']
    assert sha(ROOT/full['source_results']) == full['source_sha256']
    return {'schema': 'ra-hardware-adapter-verification-v1', 'all_checks_passed': True,
            'circuits': len(circuits), 'source_files_checked': len(sources),
            'maximum_independent_data_marginal_error': max_error,
            'maximum_event_probability_error': max_event_error,
            'maximum_ideal_dirty_workspace_probability_or_roundoff': max_dirty,
            'measurement_wiring_all_checked': True, 'generic_resource_counts_all_checked': True,
            'manifest_sha256': sha(folder/'manifest.json'),
            'artifact_sha256': manifest['artifact_sha256'],
            'verifier_sha256': sha(__file__), 'scope': 'Local immutable logical circuits and exact references; no hardware claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    result = verify(args.directory)
    if args.receipt:
        if args.receipt.exists():
            raise FileExistsError('Receipt exists')
        args.receipt.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, indent=2))
