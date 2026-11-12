"""Small, uncalibrated missing-via model for conditional rare-event sampling.

Five independent binary absorption sites replace real EUV/resist physics. A via
fails when fewer than two sites absorb. See README.md for scope and limitations.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics


def _validate(n, p, threshold):
    if not isinstance(n, int) or n < 1 or n > 12:
        raise ValueError("n must be an integer in [1, 12]")
    if not 0 < p < 1:
        raise ValueError("p must be strictly between 0 and 1")
    if not isinstance(threshold, int) or not 1 <= threshold <= n:
        raise ValueError("threshold must be an integer in [1, n]")


def exact_distribution(n=5, p=0.8, threshold=2):
    """Return exact failure probability and its conditional bit-string law."""
    _validate(n, p, threshold)
    joint = {}
    for bits in itertools.product((0, 1), repeat=n):
        if sum(bits) < threshold:
            k = sum(bits)
            joint[''.join(map(str, bits))] = p**k * (1-p)**(n-k)
    probability = sum(joint.values())
    return {"failure_probability": probability,
            "conditional_histories": {k: v/probability for k, v in joint.items()}}


def _sample(n, p, threshold, q, shots, rng):
    contributions, weighted_histories = [], {}
    hits = 0
    for _ in range(shots):
        bits = tuple(int(rng.random() < q) for _ in range(n))
        k = sum(bits)
        if k < threshold:
            hits += 1
            weight = (p/q)**k * ((1-p)/(1-q))**(n-k)
            key = ''.join(map(str, bits))
            weighted_histories[key] = weighted_histories.get(key, 0.0) + weight
            contributions.append(weight)
        else:
            contributions.append(0.0)
    total = sum(weighted_histories.values())
    # A constant contribution sample (including no failures) has zero sample
    # variance, but does not establish zero uncertainty about a rare event.
    sample_sd = statistics.stdev(contributions)
    return {"proposal_absorption_probability": q, "shots": shots,
            "proposal_failures": hits,
            "estimated_failure_probability": statistics.mean(contributions),
            "standard_error": sample_sd/math.sqrt(shots) if sample_sd else None,
            "conditional_histories": {k: v/total for k,v in weighted_histories.items()} if total else {}}


def _tv(a, b):
    return sum(abs(a.get(k, 0)-b.get(k, 0)) for k in a.keys() | b.keys())/2


def simulate(n=5, p=0.8, threshold=2, q=0.3, shots=20000, seed=77):
    """Compare estimators at equal record count, then conditional histograms."""
    _validate(n, p, threshold)
    if not 0 < q < 1:
        raise ValueError("q must be strictly between 0 and 1")
    if not isinstance(shots, int) or shots < 2:
        raise ValueError("shots must be an integer >= 2")
    exact = exact_distribution(n, p, threshold)
    plain = _sample(n, p, threshold, p, shots, random.Random(seed))
    importance = _sample(n, p, threshold, q, shots, random.Random(seed+1))
    for result in (plain, importance):
        result['conditional_total_variation'] = (_tv(result['conditional_histories'], exact['conditional_histories'])
                                                   if result['conditional_histories'] else None)
    return {"model": {"n": n, "absorption_probability": p, "failure_threshold": threshold,
                       "proposal_probability": q, "shots_per_method": shots, "seed": seed},
            "exact": exact, "direct_monte_carlo": plain, "importance_sampling": importance}


def quantum_demo(n=5, p=0.8, threshold=2, iterations=None):
    """Simulate an actual Qiskit prepare/mark/amplify circuit, if installed.

    Oracle marks *each* failing bit string explicitly. This transparent approach
    scales badly and is not an efficient oracle for realistic lithography.
    """
    _validate(n, p, threshold)
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit.quantum_info import Statevector
    except ImportError as exc:
        raise RuntimeError("Qiskit is required for --quantum: pip install qiskit") from exc
    exact = exact_distribution(n, p, threshold)
    probability = exact['failure_probability']
    theta = math.asin(math.sqrt(probability))
    if iterations is None:
        estimate = math.pi/(4*theta)-0.5
        candidates = {max(0, math.floor(estimate)), max(0, math.ceil(estimate))}
        iterations = max(candidates, key=lambda r: math.sin((2*r+1)*theta)**2)
    if not isinstance(iterations, int) or iterations < 0 or iterations > 200:
        raise ValueError("iterations must be an integer in [0, 200]")

    def phase_mark(circuit, bits):
        # bits[j] corresponds to qubit j; phase flip precisely that basis state.
        for j, bit in enumerate(bits):
            if bit == '0':
                circuit.x(j)
        if n == 1:
            circuit.z(0)
        else:
            circuit.h(n-1)
            circuit.mcx(list(range(n-1)), n-1)
            circuit.h(n-1)
        for j, bit in enumerate(bits):
            if bit == '0':
                circuit.x(j)

    prep = QuantumCircuit(n, name='prepare')
    for i in range(n):
        prep.ry(2*math.asin(math.sqrt(p)), i)
    circuit = QuantumCircuit(n)
    circuit.compose(prep, inplace=True)
    for _ in range(iterations):
        for history in exact['conditional_histories']:
            phase_mark(circuit, history)
        circuit.compose(prep.inverse(), inplace=True)
        phase_mark(circuit, '0'*n)
        circuit.compose(prep, inplace=True)
    state = Statevector.from_instruction(circuit)
    # Qiskit labels most significant qubit first; reverse to our site order.
    values = {f'{i:0{n}b}'[::-1]: float(abs(a)**2) for i,a in enumerate(state.data)}
    mass = sum(values[k] for k in exact['conditional_histories'])
    conditioned = {k: values[k]/mass for k in exact['conditional_histories']} if mass else {}
    compiled = transpile(circuit, basis_gates=['u', 'cx'], optimization_level=1)
    return {"iterations": iterations, "event_probability_before": probability,
            "event_probability_after": mass,
            "theoretical_after": math.sin((2*iterations+1)*theta)**2,
            "conditional_total_variation": _tv(conditioned, exact['conditional_histories']),
            "conditional_histories": conditioned,
            "logical_qubits": n, "oracle_marked_histories": len(exact['conditional_histories']),
            "preparation_calls": iterations + 1, "inverse_preparation_calls": iterations,
            "oracle_calls": iterations, "zero_reflection_calls": iterations,
            "compiled_basis": ['u', 'cx'], "compiled_cx_gates": int(compiled.count_ops().get('cx', 0)),
            "compiled_depth": compiled.depth(),
            "scope": "Ideal Qiskit statevector; no hardware, loss, measurement noise, or timing claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shots', type=int, default=20000)
    parser.add_argument('--seed', type=int, default=77)
    parser.add_argument('--quantum', action='store_true', help='also run ideal Qiskit circuit')
    parser.add_argument('--iterations', type=int, default=None,
                        help='Grover rounds for --quantum (default: nearest first ideal peak)')
    parser.add_argument('--json', action='store_true', help='emit machine-readable JSON')
    args = parser.parse_args()
    if args.iterations is not None and not args.quantum:
        parser.error('--iterations requires --quantum')
    result = simulate(shots=args.shots, seed=args.seed)
    if args.quantum:
        result['qiskit_statevector'] = quantum_demo(iterations=args.iterations)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print('Toy EUV missing-via model; synthetic, uncalibrated, not a real manufacturing process')
        print(f"Exact failure probability: {result['exact']['failure_probability']:.6f}")
        for label, key in [('Direct Monte Carlo', 'direct_monte_carlo'), ('Importance sampling', 'importance_sampling')]:
            r = result[key]
            uncertainty = (f"± {r['standard_error']:.6f} (1 SE)"
                           if r['standard_error'] is not None else "(SE unavailable)")
            tv = (f"{r['conditional_total_variation']:.4f}"
                  if r['conditional_total_variation'] is not None else "unavailable")
            print(f"{label}: estimate {r['estimated_failure_probability']:.6f} {uncertainty}, "
                  f"proposal failures {r['proposal_failures']}/{r['shots']}, conditional TV {tv}")
        if args.quantum:
            r = result['qiskit_statevector']
            print(f"Ideal Qiskit circuit: {r['iterations']} Grover iterations; event probability "
                  f"{r['event_probability_before']:.6f} -> {r['event_probability_after']:.6f}; "
                  f"conditional TV {r['conditional_total_variation']:.3g}; "
                  f"{r['logical_qubits']} qubits, {r['compiled_cx_gates']} CX, depth {r['compiled_depth']}")


if __name__ == '__main__':
    main()
