"""Probe conditional-sampling cost and bias in the binary lithography toy.

The system is n independent Bernoulli absorption bits with a missing contact
when fewer than two bits are 1. We compare a direct classical conditional
sampler (which exploits this toy's special structure) with actual Qiskit
circuits for several Grover round counts.  For each quantum circuit we report
the full target-routed counts and density-matrix outcome probabilities under a
seeded, *synthetic* line-target local noise model.  No fabricated device data,
wafer calibration, or generic quantum advantage is claimed.

Noise calculation reuses oracle_density_pilot.simulate_compacted: the measured
data bits are saved exactly, with independent readout matrices applied
analytically. The complete noisy distribution, not just event hits, is scored.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import random
from pathlib import Path

import numpy as np
import qiskit
import qiskit_aer
from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.quantum_info import Statevector
from qiskit.transpiler import CouplingMap

from lithography import exact_distribution
from oracle_comparison import counter_oracle, enumerated_oracle, flip_all_zero
from oracle_density_pilot import score_probabilities, simulate_compacted


def conditional_distribution(n: int, p: float) -> dict[str, float]:
    """Closed-form law given 0/1 absorptions; O(n) output, no rejection.

    It relies on all n sites being independent and having the same p.  This
    tractability is specific to this toy event, not realistic resist physics.
    """
    if not isinstance(n, int) or n < 2 or not math.isfinite(p) or not 0 < p < 1:
        raise ValueError('n must be an integer >= 2 and 0 < p < 1')
    denominator = 1-p+n*p
    zero = '0'*n
    return {zero: (1-p)/denominator, **{
        ''.join('1' if j == i else '0' for j in range(n)): p/denominator
        for i in range(n)}}


def exact_conditional_draw(n: int, p: float, rng: random.Random) -> str:
    """Draw directly from that law with no failed histories discarded."""
    pzero = (1-p)/(1-p+n*p)
    if rng.random() < pzero:
        return '0'*n
    selected = rng.randrange(n)
    return ''.join('1' if i == selected else '0' for i in range(n))


def make_circuit(n: int, p: float, style: str, rounds: int) -> QuantumCircuit:
    """Prepare, then apply r reversible oracle/reflection rounds."""
    conditional_distribution(n, p)  # validates n and p
    if style not in ('counter', 'enumerated') or not isinstance(rounds, int) or rounds < 0:
        raise ValueError('style must be counter or enumerated, rounds a nonnegative integer')
    # At r=0 no oracle/work register is needed. It is the direct quantum
    # sampler. This allows the compiler to allocate only the necessary qubits.
    oracle = (counter_oracle(n) if style == 'counter' else enumerated_oracle(n)) if rounds else None
    width = oracle.num_qubits if oracle is not None else n
    prep = QuantumCircuit(width, name='prepare')
    prep.ry(2*math.asin(math.sqrt(p)), list(range(n)))
    qc = QuantumCircuit(width, name=f'{style}_{rounds}_rounds')
    qc.compose(prep, inplace=True)
    for _ in range(rounds):
        qc.compose(oracle, inplace=True)
        qc.compose(prep.inverse(), inplace=True)
        # All work qubits return to zero in the ideal circuit; data reflection
        # therefore agrees with full reflection within the populated subspace.
        flip_all_zero(qc, list(range(n)))
        qc.compose(prep, inplace=True)
    return qc


def case(n=5, p=.8, style='counter', rounds=1, seed=77):
    """Exact ideal and synthetic-noise metrics with complete routed cost."""
    exact = exact_distribution(n, p, 2)
    circuit = make_circuit(n, p, style, rounds)
    if circuit.num_qubits > 10:
        raise ValueError('the synthetic target has only 10 qubits')
    ideal = Statevector.from_instruction(circuit).probabilities(list(range(n)))
    ideal_score = score_probabilities(ideal, n, p)
    theta = math.asin(math.sqrt(exact['failure_probability']))
    formula = math.sin((2*rounds+1)*theta)**2
    if not np.isclose(ideal_score['hit_probability'], formula, atol=1e-11):
        raise RuntimeError('ideal circuit does not agree with amplitude-amplification formula')

    # Same fake target and seed as previous experiments. Synthetic calibrated
    # values are not a snapshot of a real IBM device.
    backend = GenericBackendV2(num_qubits=10, basis_gates=['rz','sx','x','cx'],
                               coupling_map=CouplingMap.from_line(10), seed=seed, noise_info=True)
    measured = QuantumCircuit(circuit.num_qubits, n)
    measured.compose(circuit, inplace=True)
    measured.measure(range(n), range(n))
    routed = transpile(measured, backend=backend, optimization_level=1, seed_transpiler=13)
    pre, post, active, measurement = simulate_compacted(routed, backend, n, 512)
    noisy = score_probabilities(post, n, p)
    hits = noisy['hit_probability']
    counts = {str(k): int(v) for k, v in routed.count_ops().items()}
    return {
        'n':n, 'p':p, 'style':style, 'rounds':rounds,
        'logical_circuit_qubits':circuit.num_qubits,
        'physical_qubits_used':active, 'measurement_physical_qubits_in_bit_order':measurement,
        'routed_instruction_counts':counts, 'routed_depth':int(routed.depth()),
        'ideal':ideal_score, 'ideal_amplification_formula':formula,
        'noisy_before_readout':score_probabilities(pre,n,p),
        'noisy_after_readout':noisy,
        'noisy_output_normalization':float(post.sum()),
        # Conditional on independent repeated shots on this fixed noise model;
        # an accepted history can be biased. CX proxy excludes all other costs.
        'expected_circuit_shots_per_raw_match': 1/hits if hits > 0 else None,
        'expected_routed_cx_per_raw_match': counts.get('cx',0)/hits if hits > 0 else None,
        'expected_routed_sx_per_raw_match': counts.get('sx',0)/hits if hits > 0 else None,
    }


def study(n=5, p=.8, style='counter', rounds=(0,1,2,3), seed=77):
    exact=exact_distribution(n,p,2)
    closed=conditional_distribution(n,p)
    tv=.5*sum(abs(closed[k]-v) for k,v in exact['conditional_histories'].items())
    return {
        'configuration': {'n':n,'p':p,'style':style,'rounds':list(rounds),
                          'backend':'synthetic GenericBackendV2 10-qubit line, not an IBM device',
                          'device_property_seed':seed,'transpiler_seed':13,'optimization_level':1,
                          'method':'density_matrix plus independent analytic readout, no shot sampling',
                          'qiskit':qiskit.__version__,'qiskit_aer':qiskit_aer.__version__,
                          'python':platform.python_version()},
        'classical_special_case': {
            'exact_event_probability':exact['failure_probability'],
            'exact_conditional_law':closed,'conditional_law_tv_from_enumeration':tv,
            'direct_sampler':'one Bernoulli draw for zero versus one absorption, then a uniform index if needed',
            'complexity_note':'O(n) output bits; no rejected histories; this exploits the special independent identical-site model',
            'setup_cost_note':'The closed form is supplied analytically and its derivation/design costs are not timed.'},
        'quantum_cases':[case(n,p,style,r,seed) for r in rounds],
        'limitations':[
            'Synthetic uncalibrated threshold toy; this is not a wafer process or optical quantum device.',
            'One seeded synthetic target, one compiler seed; different rounds can have different layouts.',
            'Noisy event matches can be false positives; P(hit) and CX per raw match alone do not measure correct output.',
            'The expected counts assume repeated independent circuit runs and exclude single-qubit gates except the separate SX tally, measurement latency, calibration, fault tolerance, and all wall-clock overhead.',
            'Classical direct sampling is a specially tractable exact baseline for this toy, not a solver for the separate spatial process.',
            'No fair wall-clock or total-energy comparison and no quantum speedup is demonstrated.',
            'Density-matrix values are deterministic only within the synthetic local-noise model and not a real hardware result.'
        ]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites',type=int,choices=(5,7),default=5)
    parser.add_argument('--style',choices=('counter','enumerated'),default='counter')
    parser.add_argument('--rounds',type=int,nargs='+',default=[0,1,2,3])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if len(args.rounds)!=len(set(args.rounds)) or any(r<0 or r>5 for r in args.rounds):
        parser.error('rounds must be distinct integers in [0,5]')
    if args.output and args.output.exists():
        parser.error('output exists; choose a fresh path')
    result=study(n=args.sites,style=args.style,rounds=args.rounds)
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Synthetic target; counter/enumerated results may use different qubit layouts.')
    print('rounds  ideal hit  noisy hit  noisy conditional TV  routed CX  CX/raw match')
    for row in result['quantum_cases']:
        a=row['ideal']['hit_probability'];b=row['noisy_after_readout']['hit_probability']
        c=row['noisy_after_readout']['conditional_tv']; cx=row['routed_instruction_counts'].get('cx',0)
        print(f"{row['rounds']:>6}  {a:>9.6f}  {b:>9.6f}  {c:>20.6f}  {cx:>9}  {row['expected_routed_cx_per_raw_match']:>12.2f}")
    print('Raw matches can be biased; the structured classical sampler needs no rejection for this toy.')


if __name__=='__main__':
    main()
