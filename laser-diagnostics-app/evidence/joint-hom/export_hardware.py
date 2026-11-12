"""Export validated logical circuits and exact references; no Runtime/API use."""
import argparse
from dataclasses import asdict
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import ClassicalRegister, qpy, transpile

from physical_model import Parameters, branch_states, probabilities, json_matrix
from circuits import frozen_pair_circuit, sequential_circuit, circuit_branches

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=HERE / 'hardware_bundle_v2')
    args = parser.parse_args()
    folder = args.output_dir
    if folder.exists():
        raise SystemExit('Refusing to overwrite existing hardware bundle')
    specs = []
    for switch in [0., .02, .1, .5]:
        specs.append((f'frozen_pair_p{switch:g}', frozen_pair_circuit(switch), None, None, 'primary_frozen_bridge'))
    for control_name, controls in [('passive', [0.]), ('controlled_one', [1.]), ('controlled_two', [1., -1.])]:
        for hypothesis, dephase in [('coherent', 0.), ('classical', 1.)]:
            p = Parameters(gap_dephasing=dephase)
            name = f'{control_name}_{hypothesis}_Z'
            specs.append((name, sequential_circuit(p, controls), p, controls, 'primary_new_instrument'))
    # Optional memory tomography completes conditional-state checks if budget permits.
    for control_name, controls in [('controlled_one', [1.]), ('controlled_two', [1., -1.])]:
        for basis in ['X', 'Y']:
            p = Parameters()
            name = f'{control_name}_coherent_{basis}'
            specs.append((name, sequential_circuit(p, controls, basis), p, controls, 'optional_conditional_memory'))
    rows, circuits, arrays = [], [], {}
    for index, (name, circuit, p, controls, priority) in enumerate(specs):
        branches, vector, resources = circuit_branches(circuit)
        zprob = np.abs(vector)**2
        key = f'circuit_{index:02d}_ideal_z_probabilities'
        arrays[key] = zprob
        flag_probs = {''.join(map(str, bits)): float(np.trace(state).real) for bits, state in branches.items()}
        # Photon-only benchmark's retained memory is not used as a recurrent state.
        exact = branch_states(p, controls) if p is not None else None
        if exact is not None:
            expected = {''.join(map(str, bits)): value for bits, value in probabilities(exact).items()}
            max_error = max(abs(flag_probs[h]-expected[h]) for h in expected)
            if max_error > 1e-10:
                raise AssertionError(f'Flag distribution mismatch: {name}')
        else:
            expected = {'0': 1-circuit.metadata['expected_coincidence_probability'],
                        '1': circuit.metadata['expected_coincidence_probability']}
            max_error = max(abs(flag_probs[h]-expected[h]) for h in expected)
        # QPY2.6.1 cannot reload an undecomposed Isometry instruction. Store its
        # validated generic gate decomposition, preserving the physical circuit.
        measured = transpile(circuit, basis_gates=['u', 'cx'], optimization_level=1, seed_transpiler=31)
        measured.name = name
        meas = ClassicalRegister(measured.num_qubits, 'meas')
        measured.add_register(meas)
        measured.measure(range(measured.num_qubits), meas)
        circuits.append(measured)
        rows.append({'name': name, 'index': index, 'priority': priority,
                     'metadata': circuit.metadata, 'parameters': asdict(p) if p is not None else None,
                     'num_qubits': measured.num_qubits, 'classical_register': 'meas',
                     'measurement_qubits': list(range(measured.num_qubits)),
                     'classical_bit_to_logical_qubit': list(range(measured.num_qubits)),
                     'bitstring_convention': 'Qiskit integer: qubit0 is least significant/rightmost. Flag-history strings are chronological.',
                     'ideal_z_probabilities_npz_key': key,
                     'exact_flag_history_probabilities': expected,
                     'circuit_flag_history_probabilities': flag_probs,
                     'ideal_flag_max_error': max_error,
                     'conditional_memory_in_measurement_basis': {''.join(map(str, h)): json_matrix(state / np.trace(state).real)
                         for h, state in branches.items() if np.trace(state).real > 1e-12},
                     'exact_memory_before_basis_rotation': {''.join(map(str, h)): json_matrix(state / np.trace(state).real)
                         for h, state in exact.items() if np.trace(state).real > 1e-12} if exact is not None else None,
                     'generic_compilation': resources})
    folder.mkdir(parents=True)
    with (folder/'logical.qpy').open('wb') as stream:
        qpy.dump(circuits, stream)
    np.savez_compressed(folder/'ideal_probabilities.npz', **arrays)
    sources = ['PROTOCOL.md', 'physical_model.py', 'circuits.py', 'test_physical.py', 'export_hardware.py']
    manifest = {'schema': 'ra-hardware-bundle-v1', 'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'study': 'Sequential quantum-dot emitter/environment joint-photon instrument',
                'scope': 'Gate-model digital emulation of exponential temporal modes and joint SWAP symmetry; no optical source or detector validated',
                'circuits': rows, 'circuit_file': 'logical.qpy', 'reference_file': 'ideal_probabilities.npz',
                'source_sha256': {name: digest(HERE/name) for name in sources},
                'artifact_sha256': {name: digest(folder/name) for name in ['logical.qpy', 'ideal_probabilities.npz']},
                'submission_status': 'not submitted by this exporter; parent owns separate hardware authorization/runner',
                'optical_survival_and_readout_confusion': 'Excluded from logical circuits; synthetic acquisition study models them separately. Hardware readout noise is a distinct effect.'}
    (folder/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    # Verify serialization, preserving the submitted measurement mapping.
    with (folder/'logical.qpy').open('rb') as stream:
        restored = qpy.load(stream)
    assert len(restored) == len(circuits)
    for original, copy in zip(circuits, restored):
        assert original == copy
    print(json.dumps([{'name':r['name'], 'qubits':r['num_qubits'], 'cx':r['generic_compilation']['cx_gates'],
                       'flag_probabilities':r['exact_flag_history_probabilities']} for r in rows], indent=2))


if __name__ == '__main__':
    main()
