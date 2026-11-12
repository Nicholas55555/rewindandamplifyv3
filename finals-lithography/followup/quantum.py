"""Actual finite circuits for the correlated spatial process, no QRAM oracle.

Explicit controlled RY tree prepares the conditional capped Poisson law.
The structured oracle computes a weighted integer sum, phase marks 0..2,
then uncomputes. A data-only enumerated oracle is a lower-memory comparator,
not a scalable general construction. Noise uses complete compiled circuits.
"""
from __future__ import annotations
import math
import time
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from model import DEFAULT, capped_pmf, accepted, summarize


def preparation(config=DEFAULT):
    qc = QuantumCircuit(9, name='shared_dose_capped_Poisson')
    qc.ry(2*math.asin(math.sqrt(config.prior[1])), 0)
    for z in range(2):
        pmf = capped_pmf(config.rates[z])
        if z == 0: qc.x(0)
        for site in range(4):
            lo, hi = 1+2*site, 2+2*site
            qc.cry(2*math.asin(math.sqrt(pmf[2]+pmf[3])), 0, hi)
            for upper in range(2):
                p = pmf[2*upper+1]/sum(pmf[2*upper:2*upper+2])
                if upper == 0: qc.x(hi)
                qc.append(RYGate(2*math.asin(math.sqrt(p))).control(2), [0, hi, lo])
                if upper == 0: qc.x(hi)
        if z == 0: qc.x(0)
    return qc


def phase_pattern(qc, qubits, value):
    for i, q in enumerate(qubits):
        if not (value >> i) & 1: qc.x(q)
    qc.h(qubits[-1])
    qc.mcx(qubits[:-1], qubits[-1])
    qc.h(qubits[-1])
    for i, q in enumerate(qubits):
        if not (value >> i) & 1: qc.x(q)


def enumerated_oracle(config=DEFAULT):
    qc = QuantumCircuit(9, name='enumerated_spatial_event')
    # The event does not depend on latent z: mark five count maps, not ten
    # separate joint latent/count strings. No state-preparation lookup table.
    for packed_counts in range(256):
        if accepted(packed_counts << 1, config):
            phase_pattern(qc, list(range(1, 9)), packed_counts)
    return qc


def score_adder(config=DEFAULT):
    qc = QuantumCircuit(14, name='weighted_integer_sum')
    counter = list(range(9, 14))
    for i, weight in enumerate(config.weights):
        shift0 = weight.bit_length()-1
        for bit in range(2):
            control = 1+2*i+bit
            shift = shift0+bit
            for j in range(4, shift, -1):
                qc.mcx([control]+counter[shift:j], counter[j])
            qc.cx(control, counter[shift])
    return qc


def counter_oracle(config=DEFAULT):
    adder = score_adder(config)
    qc = QuantumCircuit(14, name='computed_spatial_event')
    qc.compose(adder, inplace=True)
    for score in range(config.threshold):
        phase_pattern(qc, list(range(9, 14)), score)
    qc.compose(adder.inverse(), inplace=True)
    return qc


def circuit(rounds=1, style='counter', config=DEFAULT):
    if not isinstance(rounds, int) or rounds < 0 or style not in ('counter', 'enumerated'):
        raise ValueError('invalid round count or oracle style')
    prep = preparation(config)
    oracle = counter_oracle(config) if style == 'counter' else enumerated_oracle(config)
    qc = QuantumCircuit(oracle.num_qubits if rounds else 9)
    qc.compose(prep, range(9), inplace=True)
    for _ in range(rounds):
        qc.compose(oracle, inplace=True)
        qc.compose(prep.inverse(), range(9), inplace=True)
        # Work is clean in the exact circuit. Noise can violate this invariant;
        # this experiment's density runs use the no-work enumerated circuit.
        phase_pattern(qc, list(range(9)), 0)
        qc.compose(prep, range(9), inplace=True)
    return qc


def compiled(qc):
    return transpile(qc, basis_gates=['u', 'cx'], optimization_level=1, seed_transpiler=13)


def cost(qc):
    isa = compiled(qc)
    return {'qubits': isa.num_qubits, 'depth': isa.depth(),
            'counts': {str(k): int(v) for k, v in isa.count_ops().items()}}


def ideal_case(rounds, style, config=DEFAULT):
    qc = circuit(rounds, style, config)
    state = Statevector.from_instruction(qc)
    probs = state.probabilities(list(range(9)))
    dirty = float(np.abs(state.data[512:]).dot(np.abs(state.data[512:])))
    return {'rounds': rounds, 'style': style, 'cost': cost(qc),
            'ideal': summarize(probs, config), 'dirty_workspace_probability': dirty,
            'prep_calls': rounds+1, 'inverse_prep_calls': rounds,
            'oracle_calls': rounds, 'reflection_calls': rounds}


def apply_readout(probabilities, error):
    if not 0 <= error <= 1: raise ValueError('readout probability must be in [0,1]')
    p = np.asarray(probabilities, dtype=float).copy()
    for bit in range(9):
        p = (1-error)*p + error*p[np.arange(512) ^ (1 << bit)]
    return p


def noise_case(rounds, p2, readout, config=DEFAULT):
    start = time.monotonic()
    isa = compiled(circuit(rounds, 'enumerated', config))
    counts = {str(k): int(v) for k, v in isa.count_ops().items()}
    isa.save_probabilities(list(range(9)), label='probabilities')
    noise = NoiseModel(basis_gates=['u', 'cx'])
    if p2:
        noise.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ['cx'])
        noise.add_all_qubit_quantum_error(depolarizing_error(p2/10, 1), ['u'])
    sim = AerSimulator(method='density_matrix', noise_model=noise,
                       max_parallel_threads=1, max_memory_mb=256)
    result = sim.run(isa, shots=1).result()
    if not result.success: raise RuntimeError(str(result.status))
    true = np.asarray(result.data(0)['probabilities'])
    raw = apply_readout(true, readout)
    score = summarize(raw, config)
    return {'status': 'completed', 'rounds': rounds, 'style': 'enumerated',
            'cx_depolarizing_parameter': p2, 'u_depolarizing_parameter': p2/10,
            'symmetric_independent_readout_flip_probability': readout,
            'before_readout': summarize(true, config), 'after_readout': score,
            'normalization': float(raw.sum()), 'compiled_counts': counts,
            'generic_cx_per_raw_match': counts.get('cx', 0)/score['hit_probability'],
            'seconds': time.monotonic()-start}
