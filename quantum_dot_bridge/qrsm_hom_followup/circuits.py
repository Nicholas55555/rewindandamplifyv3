"""Gate-level digital emulation of emitted modes and joint symmetry readout."""
import math

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import Isometry, StatePreparation
from qiskit.quantum_info import Statevector

from physical_model import (Parameters, photon_modes, gram_embedding,
                            branch_states, trace_distance)


def append_emission(circuit, memory, photons, states):
    """Input memory is retained. Fresh mode register is a fiducial one-photon code.

    Computational all-zero mode bits encode an internal mode, NOT optical vacuum.
    The fixed one-photon excitation/complete-decay sector is assumed explicitly.
    """
    d = states.shape[0]
    v = np.zeros((2*d, 2), complex)
    for z in range(2):
        v[z::2, z] = states[:, z]
    circuit.append(Isometry(v, 0, 0), [memory]+list(photons))


def sequential_circuit(parameters, controls, memory_basis="Z"):
    if parameters.gap_dephasing not in (0., 1.):
        raise ValueError("Logical hardware family uses coherent or fully dephased gap")
    if memory_basis not in ("X", "Y", "Z"):
        raise ValueError("Unknown memory measurement basis")
    models = [photon_modes(parameters, c) for c in controls]
    sizes = [int(math.log2(m.shape[0])) for m, _ in models]
    baths = (2*len(controls)-1) if parameters.gap_dephasing else 0
    width = 2 + sum(2*n+1 for n in sizes) + baths
    if width > 15:
        raise ValueError("Logical circuit cap is15qubits")
    circuit = QuantumCircuit(width, name=f"hom_{len(controls)}pair_{'classical' if baths else 'coherent'}_{memory_basis}")
    circuit.h(0); circuit.cx(0, 1) # Purified initial memory I/2.
    next_qubit, flags, source_registers, bath_registers = 2, [], [], []

    def gap():
        nonlocal next_qubit
        circuit.ry(parameters.theta, 0)
        if parameters.gap_dephasing:
            circuit.cx(0, next_qubit)
            bath_registers.append(next_qubit)
            next_qubit += 1

    for t, ((modes, info), n) in enumerate(zip(models, sizes)):
        if t:
            gap()
        first = list(range(next_qubit, next_qubit+n)); next_qubit += n
        second = list(range(next_qubit, next_qubit+n)); next_qubit += n
        flag = next_qubit; next_qubit += 1; flags.append(flag)
        append_emission(circuit, 0, first, modes[:, :2])
        gap()
        append_emission(circuit, 0, second, modes[:, 2:])
        circuit.h(flag)
        for a, b in zip(first, second):
            circuit.cswap(flag, a, b)
        circuit.h(flag)
        source_registers.append({"first": first, "second": second, "gram_rank": info["rank"]})
    if next_qubit != width:
        raise AssertionError("Register accounting failed")
    if memory_basis == "X":
        circuit.h(0)
    elif memory_basis == "Y":
        circuit.sdg(0); circuit.h(0)
    circuit.metadata = {"kind": "sequential_emitter_environment_joint_photon_instrument",
                        "memory_qubit": 0, "initial_memory_purifier": 1,
                        "memory_readout_basis": memory_basis, "flag_qubits": flags,
                        "photon_mode_registers": source_registers, "dephasing_bath_qubits": bath_registers,
                        "controls_over_gamma": list(controls), "gap_dephasing": parameters.gap_dephasing,
                        "theta": parameters.theta, "delta_over_gamma": parameters.delta_over_gamma,
                        "optical_scope": "Digitally encoded one-photon modes; swap-parity flag1 emulates ideal HOM coincidence. Optical loss and detector confusion excluded from this circuit.",
                        "all_other_registers_retained_until_final_measurement": True}
    return circuit


def frozen_pair_circuit(switch_probability):
    """Five-qubit purification of the earlier classical joint endpoint law."""
    if not 0 <= switch_probability <= 1:
        raise ValueError("Invalid pair switch probability")
    modes, _ = gram_embedding([-1., 1.])
    circuit = QuantumCircuit(5, name=f"frozen_pair_p{switch_probability:g}")
    circuit.h(0)
    circuit.ry(2*np.arcsin(np.sqrt(switch_probability)), 1)
    circuit.cx(0, 1)
    append_emission(circuit, 0, [2], modes)
    append_emission(circuit, 1, [3], modes)
    circuit.h(4); circuit.cswap(4, 2, 3); circuit.h(4)
    circuit.metadata = {"kind": "frozen_classical_pair_memory_benchmark", "switch_probability": switch_probability,
                        "flag_qubits": [4], "trap_endpoint_registers": [0, 1],
                        "expected_overlap": 1-.8*switch_probability,
                        "expected_coincidence_probability": .4*switch_probability,
                        "scope": "Actual nonorthogonal photon-state preparation and SWAP measurement, no loaded final probability. Digital emulation, not optical apparatus."}
    return circuit


def circuit_branches(circuit, flags=None):
    if circuit.num_qubits > 15:
        raise ValueError("Statevector cap exceeded")
    flags = circuit.metadata["flag_qubits"] if flags is None else flags
    # Compile once so expensive generic isometry definitions are not interpreted repeatedly.
    compiled = transpile(circuit, basis_gates=["u", "cx"], optimization_level=1, seed_transpiler=31)
    vector = np.asarray(Statevector.from_instruction(compiled).data)
    amplitudes = vector.reshape(-1, 2) # memory is qubit0.
    ancilla = np.arange(len(amplitudes))
    result = {}
    for value in range(1 << len(flags)):
        bits = tuple((value >> t) & 1 for t in range(len(flags)))
        mask = np.ones(len(amplitudes), bool)
        for q, bit in zip(flags, bits):
            mask &= ((ancilla >> (q-1)) & 1) == bit
        selected = amplitudes[mask]
        result[bits] = selected.T @ selected.conj()
    return result, vector, {"qubits": compiled.num_qubits,
                            "cx_gates": int(compiled.count_ops().get("cx", 0)),
                            "u_gates": int(compiled.count_ops().get("u", 0)),
                            "depth": compiled.depth(), "basis": ["u", "cx"],
                            "routing": "none; generic all-to-all synthesis"}


def validate_circuit(parameters, controls):
    circuit = sequential_circuit(parameters, controls)
    branches, _, resources = circuit_branches(circuit)
    expected = branch_states(parameters, controls)
    errors = []
    conditional_errors = []
    for key in expected:
        errors.append(float(np.linalg.norm(branches[key]-expected[key])))
        p = float(np.trace(expected[key]).real)
        q = float(np.trace(branches[key]).real)
        if p > 1e-12 and q > 1e-12:
            conditional_errors.append(trace_distance(branches[key]/q, expected[key]/p))
    return {"branch_frobenius_error_max": max(errors),
            "conditional_memory_trace_distance_max": max(conditional_errors, default=0.),
            "resources": resources}
