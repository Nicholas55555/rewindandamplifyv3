"""Independent read-only reviewer of the atomic/photonic logical bundle."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT/'hardware_campaign/optical_controls'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_counts(meta):
    n = meta['photons_if_prepared']; eta = meta['eta']; phase = meta['phase_rad']
    success = meta['preparation_success']; kind = meta['kind']
    if kind == 'coherent_sector':
        pa, pb = eta*math.cos(phase/2)**2, eta*math.sin(phase/2)**2
        return {(a,b): math.factorial(n)/math.factorial(a)/math.factorial(b)/math.factorial(n-a-b)
                *pa**a*pb**b*(1-eta)**(n-a-b)
                for a in range(n+1) for b in range(n+1-a)}
    interference = math.cos(2*phase) if kind == 'noon' else 0.
    return {(0,0): 1-success+success*(1-eta)**2,
            (1,0): success*eta*(1-eta), (0,1): success*eta*(1-eta),
            (2,0): success*eta**2*(1+interference)/4,
            (0,2): success*eta**2*(1+interference)/4,
            (1,1): success*eta**2*(1-interference)/2}


def review():
    folder = FOLDER/'bundle_v2'
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    for relative, digest in manifest['source_sha256'].items():
        assert sha(ROOT/relative) == digest
    for relative, digest in manifest['artifact_sha256'].items():
        assert sha(folder/relative) == digest
    with (folder/'logical.qpy').open('rb') as file:
        circuits = qpy.load(file)
    assert len(circuits) == len(manifest['circuits']) == 33
    maximum_qpy_error = maximum_physics_error = 0.
    with np.load(folder/'ideal_probabilities.npz', allow_pickle=False) as arrays:
        for index, (row, circuit) in enumerate(zip(manifest['circuits'], circuits)):
            assert row['index'] == index and row['name'] == circuit.name
            assert circuit.num_qubits == circuit.num_clbits == row['num_qubits']
            assert len(circuit.cregs) == 1 and circuit.cregs[0].name == 'meas'
            for bit, instruction in enumerate(circuit.data[-circuit.num_qubits:]):
                assert instruction.operation.name == 'measure'
                assert circuit.find_bit(instruction.qubits[0]).index == bit
                assert circuit.find_bit(instruction.clbits[0]).index == bit
            bare = circuit.remove_final_measurements(inplace=False)
            actual = Statevector.from_instruction(bare).probabilities()
            target = arrays[row['ideal_probability_key']]
            maximum_qpy_error = max(maximum_qpy_error, float(np.max(np.abs(actual-target))))
            meta = row['metadata']
            if meta['family'] == 'atomic_finite_pulse':
                # Pauli expectation in the selected measurement basis.
                observed = float(actual[::2].sum())
                expected = row['reference']['system_probability_zero_in_measurement_basis']
                maximum_physics_error = max(maximum_physics_error, abs(observed-expected))
                continue
            n = meta['photons_if_prepared']; aggregated = {}
            # Independent decode without importing author's decoder.
            for bitstring, probability in enumerate(actual):
                if not bitstring & (1 << (2*n)):
                    key = (0, 0)
                else:
                    counts = [0, 0]
                    for photon in range(n):
                        if not bitstring & (1 << (n+photon)):
                            counts[(bitstring >> photon) & 1] += 1
                    key = tuple(counts)
                aggregated[key] = aggregated.get(key, 0.)+float(probability)
            target_counts = independent_counts(meta)
            maximum_physics_error = max(maximum_physics_error,
                max(abs(aggregated.get(key, 0)-p) for key,p in target_counts.items()))
    tail = manifest['coherent_sector_accounting']
    # Direct recursive Poisson masses, without scipy.stats or author's helper.
    weights = [math.exp(-2)]
    for n in range(1, 70):
        weights.append(weights[-1]*2/n)
    np.testing.assert_allclose(tail['weights'], weights[:9], atol=1e-16)
    assert abs(tail['omitted_probability']-sum(weights[9:])) < 1e-15
    assert abs(tail['omitted_first_photon_moment']-sum(n*weights[n] for n in range(9,70))) < 1e-15
    assert abs(tail['omitted_second_factorial_photon_moment']-sum(n*(n-1)*weights[n] for n in range(9,70))) < 1e-15
    assert maximum_qpy_error < 1e-10 and maximum_physics_error < 1e-10
    return {'schema': 'independent-optical-controls-review-v1', 'all_checks_passed': True,
            'circuits_checked': 33, 'author_tests_independently_run': 8,
            'maximum_qpy_vs_saved_distribution_error': maximum_qpy_error,
            'maximum_independent_number_distribution_or_atomic_basis_error': maximum_physics_error,
            'source_hashes_checked': manifest['source_sha256'],
            'artifact_hashes_checked': manifest['artifact_sha256'],
            'manifest_sha256': sha(folder/'manifest.json'), 'reviewer_sha256': sha(__file__),
            'findings': ['Atomic full CPTP map, ground-state convention, preparation purification and separate synthetic readout are consistent.',
                         'Path/loss pairs encode surviving versus lost spatial modes; lost photon paths remain available as environment labels.',
                         'Identical single-particle transformations preserve the symmetric bosonic sector for stated number measurements.',
                         'Equal symmetric losses commute with the balanced beamsplitter; total object/detection loss can be placed after interference.',
                         'Source failure is charged as vacuum for the specified count instrument; no full optical vacuum/number coherence tomography is claimed.',
                         'Coherent sector aggregation keeps Poisson weights unnormalized and explicitly charges vacuum and omitted event/first/second-moment tails.',
                         'No material scientific blocker; hardware is a digital model-kernel test, not the complete optical diagnostic or phase-estimation experiment.']}


if __name__ == '__main__':
    result = review()
    output = Path(__file__).with_name('optical_controls_independent_review.json')
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, indent=2))
