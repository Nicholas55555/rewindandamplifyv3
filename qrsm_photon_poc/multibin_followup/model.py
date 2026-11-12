"""General retained-instrument histories and bounded compiled-noise checks."""
from pathlib import Path
import itertools
import math
import sys
import time

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import Isometry
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from qrsm_photon import Parameters, instruments, init_state
from dilation_feasibility import (kraus_from_superoperator, normalize_completeness,
                                  flagged_isometry, kraus_superoperator)


def trace_distance(a, b):
    delta = a-b
    return float(.5*np.abs(np.linalg.eigvalsh((delta+delta.conj().T)/2)).sum())


def instrument(cutoff):
    original = instruments(Parameters(n_cavity=2))[:2]
    ops, reports = zip(*(kraus_from_superoperator(s, 8, cutoff) for s in original))
    no, yes, norm = normalize_completeness(*ops)
    retained = [kraus_superoperator(x, 8) for x in (no, yes)]
    v, dim, env = flagged_isometry(no, yes)
    if dim != 8: raise AssertionError("Unexpected system padding")
    report = {"choi_absolute_cutoff": cutoff, "retained_ranks": [len(no), len(yes)],
              "choi_reports": reports, "normalization": norm,
              "map_frobenius_errors": [float(np.linalg.norm(a-b)) for a, b in zip(retained, original)],
              "isometry_completeness_spectral_error": float(np.linalg.norm(v.conj().T@v-np.eye(8), ord=2))}
    return original, retained, v, int(math.log2(env)), report


def one_bin(v):
    q = int(math.log2(v.shape[0]))
    circuit = QuantumCircuit(q, name="retained_photon_bin")
    circuit.append(Isometry(v, 0, 0), range(q))
    return transpile(circuit, basis_gates=["u", "cx"], optimization_level=1, seed_transpiler=13)


def prepare(compiled_bin, bins, env_bits):
    if bins < 1 or int(bins) != bins: raise ValueError("positive integer bins required")
    width = 3+bins*(1+env_bits)
    if width > 18: raise ValueError("statevector construction capped at18qubits")
    if compiled_bin.num_qubits != 4+env_bits: raise ValueError("register mismatch")
    circuit = QuantumCircuit(width, name=f"prepare_{bins}_bins")
    flags = []
    for j in range(bins):
        flag = 3+j*(1+env_bits); flags.append(flag)
        qargs = [0, 1, 2]+list(range(flag, flag+1+env_bits))
        circuit.compose(compiled_bin, qargs, inplace=True)
    return circuit, flags


def amplify(preparation, flags, event):
    if event not in ("last", "all"): raise ValueError("unknown event")
    out = preparation.copy(name=f"amplified_{event}")
    if event == "last" or len(flags) == 1:
        out.z(flags[-1])
    else:
        out.h(flags[-1]); out.mcx(flags[:-1], flags[-1]); out.h(flags[-1])
    out.compose(preparation.inverse(), inplace=True)
    qubits = list(range(out.num_qubits))
    out.x(qubits); out.h(qubits[-1]); out.mcx(qubits[:-1], qubits[-1]); out.h(qubits[-1]); out.x(qubits)
    out.compose(preparation, inplace=True)
    return transpile(out, basis_gates=["u", "cx"], optimization_level=1, seed_transpiler=13)


def statevector(circuit):
    if circuit.num_qubits > 18: raise ValueError("statevector width guard")
    job = circuit.copy(); job.save_statevector()
    backend = AerSimulator(method="statevector", max_parallel_threads=1,
                           max_parallel_experiments=1, max_memory_mb=1536)
    result = backend.run(job, shots=1).result()
    if not result.success: raise RuntimeError(result.status)
    return np.asarray(result.data(0)["statevector"])


def vector_branches(vector, bins, env_bits):
    width = 3+bins*(1+env_bits)
    if np.asarray(vector).shape != (1 << width,): raise ValueError("statevector shape")
    amplitudes = vector.reshape(-1, 8)
    ancilla = np.arange(len(amplitudes))
    result = {}
    for bits in itertools.product((0, 1), repeat=bins):
        mask = np.ones(len(amplitudes), bool)
        for j, bit in enumerate(bits): mask &= ((ancilla >> (j*(1+env_bits))) & 1) == bit
        selected = amplitudes[mask]
        result[bits] = selected.T@selected.conj()
    return result


def channel_branches(maps, bins):
    result = {(): init_state(Parameters(n_cavity=2))}
    for _ in range(bins):
        result = {key+(bit,): maps[bit]@rho for key, rho in result.items() for bit in (0, 1)}
    return {key: rho.reshape((8, 8), order="F") for key, rho in result.items()}


def event_recursion(maps, bins, event):
    """Linear-in-bins direct event probability and conditional state, no rejection."""
    if event not in ("last", "all"): raise ValueError("unknown event")
    rho = init_state(Parameters(n_cavity=2))
    for j in range(bins):
        rho = (maps[1] if event == "all" or j == bins-1 else maps[0]+maps[1])@rho
    return rho.reshape((8, 8), order="F")


def selected(bits, event): return bits[-1] == 1 if event == "last" else all(bits)


def selection(branches, event):
    rho = sum((rho for bits, rho in branches.items() if selected(bits, event)), np.zeros((8, 8), complex))
    p = float(np.trace(rho).real)
    if p <= 0: raise ValueError("zero selected probability")
    return p, rho/p


def circuit_resources(circuit):
    return {"qubits": circuit.num_qubits, "cx_gates": int(circuit.count_ops().get("cx", 0)),
            "u_gates": int(circuit.count_ops().get("u", 0)), "depth": int(circuit.depth()),
            "instructions": len(circuit.data), "basis": ["u", "cx"], "routing": "none, generic all-to-all"}


def timed(function, repetitions=21):
    function() # warm-up, reported timings exclude this call
    values = []
    for _ in range(repetitions):
        begin = time.perf_counter(); function(); values.append(time.perf_counter()-begin)
    return {"repetitions": repetitions, "median_seconds": float(np.median(values)),
            "minimum_seconds": float(min(values)), "maximum_seconds": float(max(values))}


def conditional_sampler(branches, event, count=100000, seed=481191):
    keys = [key for key in branches if selected(key, event)]
    probs = np.array([np.trace(branches[key]).real for key in keys]); probs /= probs.sum()
    rng = np.random.default_rng(seed)
    begin = time.perf_counter(); indices = rng.choice(len(keys), size=count, p=probs); elapsed = time.perf_counter()-begin
    frequencies = np.bincount(indices, minlength=len(keys))/count
    return {"histories": ["".join(map(str, key)) for key in keys], "probabilities": probs.tolist(),
            "samples": count, "seed": seed, "sample_frequency": frequencies.tolist(),
            "sampling_seconds": elapsed, "empirical_tvd": float(.5*np.abs(frequencies-probs).sum()),
            "rejections": 0, "scope": "Classical samples of the exact finite-model history distribution, not physical preparation of a quantum state."}


def ideal_case(cutoff, bins=3):
    started = time.perf_counter()
    original, retained, v, env_bits, report = instrument(cutoff)
    begin = time.perf_counter(); compiled_bin = one_bin(v); synth = time.perf_counter()-begin
    preparation, flags = prepare(compiled_bin, bins, env_bits)
    begin = time.perf_counter(); vector = statevector(preparation); prep_seconds = time.perf_counter()-begin
    actual = vector_branches(vector, bins, env_bits)
    expected, full = channel_branches(retained, bins), channel_branches(original, bins)
    rows, arrays = {}, {}
    max_branch_error = 0.
    for key in expected:
        name = "".join(map(str, key)); ps = [float(np.trace(x[key]).real) for x in (actual, expected, full)]
        error = float(np.linalg.norm(actual[key]-expected[key])); max_branch_error = max(max_branch_error, error)
        rows[name] = {"compiled_probability": ps[0], "retained_probability": ps[1], "original_cavity2_probability": ps[2],
            "implementation_branch_frobenius_error": error,
            "implementation_conditional_trace_distance": trace_distance(actual[key]/ps[0], expected[key]/ps[1]),
            "retained_vs_original_conditional_trace_distance": trace_distance(expected[key]/ps[1], full[key]/ps[2])}
        for label, state in [("compiled", actual[key]), ("retained", expected[key]), ("original", full[key])]: arrays[f"{label}_{name}"] = state
    events = {}
    implementation_errors = [report["isometry_completeness_spectral_error"], max_branch_error,
                             abs(sum(r["compiled_probability"] for r in rows.values())-1)]
    for event in ("last", "all"):
        p, target = selection(expected, event); po, original_target = selection(full, event)
        begin = time.perf_counter(); circuit = amplify(preparation, flags, event); compile_seconds = time.perf_counter()-begin
        begin = time.perf_counter(); amplified = vector_branches(statevector(circuit), bins, env_bits); simulate_seconds = time.perf_counter()-begin
        pa, target_a = selection(amplified, event)
        theory = math.sin(3*math.asin(math.sqrt(p)))**2
        event_error, state_error = 0., 0.
        for key in expected:
            scale = theory/p if selected(key, event) else (1-theory)/(1-p)
            event_error = max(event_error, float(np.linalg.norm(amplified[key]-scale*expected[key])))
            prob_a = float(np.trace(amplified[key]).real); prob_e = float(np.trace(expected[key]).real)
            state_error = max(state_error, trace_distance(amplified[key]/prob_a, expected[key]/prob_e))
            arrays[f"amplified_{event}_{''.join(map(str, key))}"] = amplified[key]
        recursion = event_recursion(retained, bins, event)
        recursion_error = float(np.linalg.norm(recursion-p*target))
        selected_error = trace_distance(target_a, target)
        implementation_errors += [event_error, state_error, abs(pa-theory), selected_error, recursion_error]
        events[event] = {"retained_probability": p, "original_cavity2_probability": po,
            "amplified_probability": pa, "one_round_theory": theory,
            "selected_conditional_state_implementation_trace_distance": selected_error,
            "retained_vs_original_selected_trace_distance": trace_distance(target, original_target),
            "max_amplified_branch_scaling_frobenius_error": event_error,
            "max_amplified_history_conditional_trace_distance": state_error,
            "event_specific_recursion_error": recursion_error,
            "compilation": circuit_resources(circuit), "compilation_seconds": compile_seconds,
            "classical_statevector_simulation_seconds": simulate_seconds,
            "classical_event_recursion_timing": timed(lambda: event_recursion(retained, bins, event)),
            "exact_conditional_sampler": conditional_sampler(expected, event)}
    growth = []
    for count in [1, 2, 3, 4, 6, 8, 12]:
        q = 3+count*(1+env_bits)
        growth.append({"bins": count, "qubits": q, "dense_statevector_bytes": 16*2**q,
                       "dense_density_matrix_bytes": 16*4**q,
                       "note": "Storage arithmetic, not a simulated case or hardware resource lower bound."})
    validation = {"tolerance": 1e-8, "maximum_error": max(implementation_errors),
                  "passed": bool(max(implementation_errors) < 1e-8)}
    return {"kind": "ideal_multibin", "bins": bins, "instrument": report,
            "system_qubits": 3, "flags": flags, "environment_qubits_per_bin": env_bits,
            "one_bin_compilation": circuit_resources(compiled_bin), "one_bin_synthesis_seconds": synth,
            "preparation": circuit_resources(preparation), "preparation_statevector_seconds": prep_seconds,
            "history_branches": rows, "events": events, "register_growth": growth,
            "history_probability_tvd_retained_vs_original": float(.5*sum(abs(r["retained_probability"]-r["original_cavity2_probability"]) for r in rows.values())),
            "classical_complete_history_timing": timed(lambda: channel_branches(retained, bins)),
            "implementation_validation": validation, "elapsed_seconds": time.perf_counter()-started}, arrays


def density_branches(matrix, env_bits):
    env = 1 << env_bits
    if np.asarray(matrix).shape != (16*env, 16*env): raise ValueError("one-bin density shape")
    tensor = matrix.reshape(env, 2, 8, env, 2, 8)
    return [sum((tensor[k, bit, :, k, bit, :] for k in range(env)), np.zeros((8, 8), complex)) for bit in (0, 1)]


def readout_mix(branches, e01=.01, e10=.02):
    if not (0 <= e01 <= 1 and 0 <= e10 <= 1): raise ValueError("invalid readout errors")
    no, yes = branches
    return [(1-e01)*no+e10*yes, e01*no+(1-e10)*yes]


def noisy_density(circuit, strength):
    if circuit.num_qubits > 8: raise ValueError("density-matrix simulation capped at8qubits")
    if strength < 0 or strength > 1: raise ValueError("depolarization strength in[0,1]required")
    noise = NoiseModel()
    if strength:
        noise.add_all_qubit_quantum_error(depolarizing_error(strength/10, 1), ["u"])
        noise.add_all_qubit_quantum_error(depolarizing_error(strength, 2), ["cx"])
    backend = AerSimulator(method="density_matrix", noise_model=noise, max_parallel_threads=1,
                           max_parallel_experiments=1, max_memory_mb=1536, fusion_max_qubit=2)
    qc = circuit.copy(); qc.save_density_matrix()
    result = backend.run(qc, shots=1).result()
    if not result.success: raise RuntimeError(result.status)
    return np.asarray(result.data(0)["density_matrix"])


def noise_case(cutoff):
    started = time.perf_counter()
    original, retained, v, env_bits, report = instrument(cutoff)
    compiled_bin = one_bin(v)
    preparation, flags = prepare(compiled_bin, 1, env_bits)
    amplified = amplify(preparation, flags, "last")
    if preparation.num_qubits > 8: raise ValueError("density width exceeded")
    target_branches = channel_branches(retained, 1)
    p, target = selection(target_branches, "last")
    po, original_target = selection(channel_branches(original, 1), "last")
    rows, arrays, noiseless_errors = [], {}, []
    for strength in [0., 1e-5, 1e-4, 1e-3]:
        for name, circuit in [("preparation", preparation), ("amplified", amplified)]:
            begin = time.perf_counter(); matrix = noisy_density(circuit, strength); elapsed = time.perf_counter()-begin
            branches = density_branches(matrix, env_bits)
            mixed = readout_mix(branches)
            expected_p = p if name == "preparation" else math.sin(3*math.asin(math.sqrt(p)))**2
            probabilities = [float(np.trace(b).real) for b in branches]
            prob = float(np.trace(mixed[1]).real)
            before_state = branches[1]/probabilities[1]; after_state = mixed[1]/prob
            row = {"circuit": name, "depolarizing_strength_cx": strength, "depolarizing_strength_u": strength/10,
                   "readout_01": .01, "readout_10": .02,
                   "before_readout_acceptance": probabilities[1], "recorded_acceptance": prob,
                   "ideal_retained_acceptance": expected_p,
                   "conditional_trace_distance_before_readout_vs_retained": trace_distance(before_state, target),
                   "conditional_trace_distance_after_readout_vs_retained": trace_distance(after_state, target),
                   "conditional_trace_distance_after_readout_vs_original_cavity2": trace_distance(after_state, original_target),
                   "false_flag_fraction_among_recorded_clicks": float(.01*probabilities[0]/prob),
                   "density_trace_error": float(abs(np.trace(matrix)-1)),
                   "density_hermiticity_frobenius_error": float(np.linalg.norm(matrix-matrix.conj().T)),
                   "minimum_density_eigenvalue": float(np.linalg.eigvalsh((matrix+matrix.conj().T)/2).min()),
                   "exact_density_simulation_seconds": elapsed}
            if strength == 0:
                noiseless_errors += [abs(probabilities[1]-expected_p), trace_distance(before_state, target)]
            rows.append(row)
            for bit in (0, 1):
                arrays[f"{name}_{strength}_trueflag{bit}"] = branches[bit]
                arrays[f"{name}_{strength}_recordedflag{bit}"] = mixed[bit]
    return {"kind": "one_bin_exact_density_noise", "instrument": report,
            "retained_event_probability": p, "original_cavity2_event_probability": po,
            "ideal_retained_vs_original_conditional_trace_distance": trace_distance(target, original_target),
            "circuits": {"preparation": circuit_resources(preparation), "amplified": circuit_resources(amplified)},
            "cases": rows, "implementation_validation": {"tolerance": 1e-8, "maximum_error": max(noiseless_errors), "passed": max(noiseless_errors) < 1e-8},
            "elapsed_seconds": time.perf_counter()-started,
            "noise_scope": "Generic independent gate depolarization and classical flag confusion. No device calibration, routing, idle T1/T2 or15/18qubit noisy query simulated."}, arrays
