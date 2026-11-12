"""1 - The QRSM step as a Qiskit dynamic circuit, and click records from it.

v5's experiment 4 system, built gate by gate: an emitter, one hidden defect and a light qubit. Each step drives the
emitter (RY theta), turns the defect (RZ zeta), lets the emitter and the defect exchange (a real Givens rotation by
phi), lets the emitter emit into the light (the same rotation by alpha, sin(alpha)^2 = gamma), then measures the light
mid-circuit and resets it. The measured bit is the click. The emitter and the defect are never measured.

Click records come from three sources:
- the perfect simulator (Aer, no noise);
- a simulated noisy IBM device: a qiskit-ibm-runtime fake backend's noise model in Aer, on the transpiled and
  scheduled circuit, so the emitter and the defect also relax and dephase while the light is read out;
- real IBM hardware, from experiments/3_hardware.py, only with the user's own IBM Quantum account.
Detector imperfections are applied afterwards to the clicks, as in v5: a click is kept with the efficiency, and a dark
count adds one.

Run with v6's Qiskit environment (-B writes nothing into v6):
  & "..\\Quantum research v6\\.venv-qiskit\\Scripts\\python.exe" -B experiments\\1_qrsm_circuit.py
  ... --quick for a smoke test (8 steps, few records)
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")  # the circuit drawing uses box characters

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import fake_provider

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "results" / "1_qrsm_circuit"

THETA, GAMMA, PHI, ZETA = 0.6, 0.2, 0.45, 0.3  # v5 experiment 4's emitter and its first defect
ALPHA = float(np.arcsin(np.sqrt(GAMMA)))  # the emission rotation: sin(alpha)^2 = gamma
T = 64  # steps per record, as v5
N_TRAIN, N_VAL, N_COUNT = 4096, 512, 4096  # v5's training and counting sizes; 512 validation records
DEVICE = "FakeMarrakesh"  # a 156-qubit Heron r2 snapshot, the kind of device on IBM's open plan
GOOD = (0.5, 0.005)  # v5's "good" detector: efficiency, dark counts per step
CAL_SHOTS = 1024  # readout calibration: shots of a 64-step circuit that prepares the light in a known pattern
SEED_TRANSPILE = 7


# ----------------------------------------------------------------------------
# The circuit


def exchange(qc: QuantumCircuit, angle: float, src, dst) -> None:
    """v5's exchange, a real Givens rotation: with dst empty and src excited, |dst=0, src=1> -> cos(angle) |0, 1> +
    sin(angle) |1, 0>, and |1, 0> -> cos(angle) |1, 0> - sin(angle) |0, 1>; |00> and |11> are left alone."""
    qc.cx(dst, src)
    qc.cry(2 * angle, src, dst)
    qc.cx(dst, src)


def emission(qc: QuantumCircuit, alpha: float, emitter, light) -> None:
    """The exchange from the emitter into the light. The light always starts the step reset to |0>, so the
    exchange's first CNOT (controlled by the light) never acts and is left out."""
    qc.cry(2 * alpha, emitter, light)
    qc.cx(light, emitter)


def registers(k: int, T_steps: int, measured: bool = True):
    regs = [QuantumRegister(1, "emitter")] + ([QuantumRegister(k, "defect")] if k else []) + [QuantumRegister(1, "light")]
    if measured:
        regs.append(ClassicalRegister(T_steps, "click"))
    return QuantumCircuit(*regs)


def add_step(qc: QuantumCircuit, k: int, theta, phi, zeta, alpha, t: int = None) -> None:
    """One QRSM step, in v5's order: drive, the defect's turn, exchange, emission; then (with t) read and reset."""
    e, l = qc.qubits[0], qc.qubits[-1]
    qc.ry(theta, e)
    for j in range(k):
        qc.rz(zeta[j], qc.qubits[1 + j])
    for j in range(k):
        exchange(qc, phi[j], src=qc.qubits[1 + j], dst=e)
    emission(qc, alpha, e, l)
    if t is not None:
        qc.measure(l, qc.clbits[t])
        qc.reset(l)


def qrsm_circuit(k: int, T_steps: int = T, theta=THETA, phi=(PHI,), zeta=(ZETA,), gamma=GAMMA) -> QuantumCircuit:
    """The whole record: T_steps steps, each ending in a mid-circuit measurement of the light and its reset."""
    qc = registers(k, T_steps)
    alpha = float(np.arcsin(np.sqrt(gamma)))
    for t in range(T_steps):
        add_step(qc, k, theta, phi[:k], zeta[:k], alpha, t)
    return qc


def step_operator(k: int) -> np.ndarray:
    """One step's gates as a matrix, with the emitter as the most significant qubit and the light the least (v5's
    order, with the light appended): reversed from Qiskit's little-endian convention."""
    qc = registers(k, 0, measured=False)
    add_step(qc, k, THETA, [PHI][:k], [ZETA][:k], ALPHA)
    return Operator(qc).reverse_qargs().data


def calibration_circuit(n_qubits_like: QuantumCircuit, T_steps: int) -> tuple:
    """Readout calibration in the experiment's own timing: each step prepares the light in a known bit (alternating 0
    and 1, starting from a random-looking but fixed pattern), measures and resets it. Returns the circuit and the
    pattern."""
    pattern = (np.arange(T_steps) + (np.arange(T_steps) // 8)) % 2  # 0101... shifted every 8 steps
    qc = n_qubits_like.copy_empty_like()
    l = qc.qubits[-1]
    for t in range(T_steps):
        if pattern[t]:
            qc.x(l)
        qc.measure(l, qc.clbits[t])
        qc.reset(l)
    return qc, pattern


# ----------------------------------------------------------------------------
# Sampling


def to_array(memory: list) -> np.ndarray:
    """Aer's per-shot strings put clbit 0 last; returns (shots, T) with column t = the click at step t."""
    return np.array([[ch == "1" for ch in s.replace(" ", "")[::-1]] for s in memory], dtype=np.uint8)


def run(sim: AerSimulator, qc: QuantumCircuit, shots: int, seed: int) -> tuple:
    t0 = time.perf_counter()
    res = sim.run(qc, shots=shots, memory=True, seed_simulator=seed).result()
    meta = res.results[0].metadata
    return to_array(res.get_memory()), time.perf_counter() - t0, meta.get("active_input_qubits")


def apply_detector(X: np.ndarray, eta: float, p_dark: float, seed: int) -> np.ndarray:
    """v5's detector as post-processing: each click is kept with probability eta, and a dark count adds a click
    with probability p_dark per step."""
    rng = np.random.default_rng(seed)
    kept = X.astype(bool) & (rng.random(X.shape) < eta)
    return (kept | (rng.random(X.shape) < p_dark)).astype(np.uint8)


def split(X: np.ndarray, sizes: tuple) -> dict:
    out, i = {}, 0
    for part, n in zip(("train", "val", "count"), sizes):
        out[part] = X[i:i + n]
        i += n
    return out


def save(name: str, X: np.ndarray, sizes: tuple, meta: dict, data_dir: Path) -> None:
    parts = split(X, sizes)
    np.savez_compressed(data_dir / f"{name}.npz", **parts)
    meta = {**meta, "name": name, "records": {p: int(len(v)) for p, v in parts.items()}, "steps": int(X.shape[1]),
            "click_rate": float(X.mean())}
    (data_dir / f"{name}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"  {name}: {X.shape[0]} records x {X.shape[1]} steps, click rate {X.mean():.4f}", flush=True)


def counts_per_step(isa: QuantumCircuit, T_steps: int) -> dict:
    ops = isa.count_ops()
    return {name: round(n / T_steps, 2) for name, n in sorted(ops.items())}


def device_qubits(isa: QuantumCircuit) -> list:
    """The physical qubits the transpiler chose for the circuit's qubits, in their order (emitter, defect, light)."""
    return [int(q) for q in isa.layout.initial_index_layout(filter_ancillas=True)]


def qubit_info(backend, qubits: list, step_seconds: float) -> list:
    """T1, T2 and readout error of each chosen qubit, and what relaxation and dephasing they imply per step."""
    out = []
    for q in qubits:
        p = backend.target.qubit_properties[q]
        t1, t2 = p.t1, p.t2
        out.append({"qubit": q, "T1_us": t1 * 1e6, "T2_us": t2 * 1e6,
                    "readout_error": backend.target["measure"][(q,)].error,
                    "relax_per_step": 1 - float(np.exp(-step_seconds / t1)),
                    "coherence_per_step": float(np.exp(-step_seconds / t2))})
    return out


# ----------------------------------------------------------------------------
# Main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--device", default=DEVICE)
    args = ap.parse_args()
    out = OUT / "quick" if args.quick else OUT
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    T_steps = 8 if args.quick else T
    sizes = (64, 16, 64) if args.quick else (N_TRAIN, N_VAL, N_COUNT)
    shots = sum(sizes)
    cal_shots = 64 if args.quick else CAL_SHOTS
    truth = {"theta": THETA, "gamma": GAMMA, "phi": [PHI], "zeta": [ZETA]}

    for k in (0, 1):
        np.save(out / f"step_operator_k{k}.npy", step_operator(k))
    print(qrsm_circuit(1, 2).draw("text", fold=-1), flush=True)

    # the perfect simulator
    ideal = AerSimulator(method="statevector")
    info = {}
    for k in (1, 0):
        qc = qrsm_circuit(k, T_steps)
        X, secs, active = run(ideal, qc, shots, seed=100 + k)
        meta = {"source": "ideal", "k_true": k, "truth": truth if k else {"theta": THETA, "gamma": GAMMA},
                "detector": {"eta": 1.0, "p_dark": 0.0, "how": "perfect"}, "seconds": secs}
        save(f"ideal-k{k}-perfect", X, sizes, meta, data_dir)
        Xg = apply_detector(X, *GOOD, seed=200 + k)
        save(f"ideal-k{k}-good", Xg, sizes, {**meta, "detector": {"eta": GOOD[0], "p_dark": GOOD[1],
                                                                    "how": "v5's good detector, applied to the "
                                                                           "ideal clicks"}}, data_dir)
        info[f"ideal k{k} seconds"] = secs

    # the noisy device: transpiled to its gates and qubits, scheduled, and simulated with its noise model
    backend = getattr(fake_provider, args.device)()
    noisy = AerSimulator.from_backend(backend)
    qc1 = qrsm_circuit(1, T_steps)
    isa1 = transpile(qc1, backend=backend, optimization_level=3, seed_transpiler=SEED_TRANSPILE,
                     scheduling_method="alap")
    layout1 = device_qubits(isa1)
    emitter_q, light_q = layout1[0], layout1[-1]
    qc0 = qrsm_circuit(0, T_steps)
    isa0 = transpile(qc0, backend=backend, optimization_level=3, seed_transpiler=SEED_TRANSPILE,
                     scheduling_method="alap", initial_layout=[emitter_q, light_q])
    cal, pattern = calibration_circuit(qc0, T_steps)
    isa_cal = transpile(cal, backend=backend, optimization_level=3, seed_transpiler=SEED_TRANSPILE,
                        scheduling_method="alap", initial_layout=[emitter_q, light_q])
    Xc, secs_cal, _ = run(noisy, isa_cal, cal_shots, seed=300)
    sent = np.broadcast_to(pattern, Xc.shape)
    p10 = float(Xc[sent == 0].mean())  # read 1 when the light held 0
    p01 = float(1 - Xc[sent == 1].mean())  # read 0 when it held 1
    eta, p_dark = 1 - p01 / (1 - p10), p10  # the same click probabilities in v5's detector numbers
    calibration = {"P(1|0)": p10, "P(0|1)": p01, "eta": eta, "p_dark": p_dark, "shots": cal_shots,
                   "measurements_each": int((sent == 0).sum()), "seconds": secs_cal,
                   "how": "fitted from a calibration circuit with the experiment's timing"}
    print(f"  readout calibration on qubit {light_q}: P(1|0) = {p10:.4f}, P(0|1) = {p01:.4f}", flush=True)
    for k, qc, isa in ((1, qc1, isa1), (0, qc0, isa0)):
        dur = isa.estimate_duration(backend.target, unit="s")
        step_s = dur / T_steps
        qubits = device_qubits(isa)
        X, secs, active = run(noisy, isa, shots, seed=400 + k)
        meta = {"source": "noisy device simulator", "device": args.device, "k_true": k,
                "truth": truth if k else {"theta": THETA, "gamma": GAMMA},
                "detector": {"eta": eta, "p_dark": p_dark, "how": "the device's own readout, calibrated"},
                "calibration": calibration, "physical_qubits": qubits, "active_qubits_simulated": active,
                "ops_per_step": counts_per_step(isa, T_steps), "depth": isa.depth(),
                "record_seconds": dur, "step_seconds": step_s, "qubits": qubit_info(backend, qubits, step_s),
                "seconds": secs}
        save(f"device-k{k}", X, sizes, meta, data_dir)
        print(f"    physical qubits {qubits}, {step_s * 1e6:.2f} us per step, ops per step "
              f"{meta['ops_per_step']}, simulated {secs:.1f} s", flush=True)
    (out / "circuit.txt").write_text(qrsm_circuit(1, 2).draw("text", fold=-1).single_string(), encoding="utf-8")


if __name__ == "__main__":
    main()
