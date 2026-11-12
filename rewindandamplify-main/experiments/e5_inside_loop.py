"""E5: Grover inside the recurrent loop. What does the machine do right after a rare click?

    --noiseless       exact simulation: does the amplified circuit give the filter's conditional click rates?
    --noisy NAME      an IBM device snapshot: at equal shots, is amplified or plain sampling closer to the truth?

    python experiments/e5_inside_loop.py --noiseless --noisy FakeFez
"""

import argparse
import time

from common import save

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qrsm_grover.amplify import steered_gamma
from qrsm_grover.model import QRSM
from qrsm_grover.queries import exact_after_click, loop_circuit, read_after_click

ONE = QRSM()
NONE = QRSM(phi=(), zeta=())
T0, TAU = 3, 3
PASS = 1e-9


def state_answer(model: QRSM, t0: int, tau: int, r: int, reflection: str) -> dict:
    qc = loop_circuit(model, t0, tau, r, reflection)
    probs = np.abs(Statevector(qc).data) ** 2
    n = model.n_memory
    index = np.arange(probs.size)
    base = qc.num_qubits - tau
    keep = ((index >> (n + t0 - 1)) & 1) == 1
    kept = probs[keep].sum()
    conditional = [probs[keep & (((index >> (base + j)) & 1) == 1)].sum() / kept for j in range(tau)]
    return {"kept": float(kept), "conditional": np.array(conditional)}


def noiseless() -> dict:
    out = {}
    for name, model in (("one defect", ONE), ("no defect", NONE)):
        exact = exact_after_click(model, T0, TAU)
        rows = []
        for reflection in ("full", "memory+last-1", "memory"):
            for r in range(0, 5):
                ans = state_answer(model, T0, TAU, r, reflection)
                err = float(np.abs(ans["conditional"] - exact["conditional"]).max())
                rows.append({"reflection": reflection, "r": r, "kept": ans["kept"], "conditional": ans["conditional"],
                             "max_error": err})
                print(f"  {name:10s} {reflection:13s} r = {r}: click kept {ans['kept']:.3f}, conditional "
                      f"{np.round(ans['conditional'], 4)}, largest error {err:.1e}", flush=True)
        out[name] = {"exact": exact, "rows": rows}
    # a longer curve for the figure, from the exact filter
    curves = {name: {t0: exact_after_click(model, t0, 10) for t0 in (3, 6)}
              for name, model in (("one defect", ONE), ("no defect", NONE))}
    worst_full = max(row["max_error"] for v in out.values() for row in v["rows"] if row["reflection"] == "full")
    print(f"  worst error with the full reflection: {worst_full:.1e} (pass mark {PASS})", flush=True)
    return {"T0": T0, "tau": TAU, "models": out, "curves": curves, "worst_full_error": worst_full,
            "passed": worst_full < PASS}


def noisy(backend_name: str, shots: int, chunk: int) -> dict:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime import fake_provider

    backend = getattr(fake_provider, backend_name)()
    sim = AerSimulator.from_backend(backend)
    rows = []
    for name, model in (("one defect", ONE), ("no defect", NONE)):
        n = model.n_memory
        exact = exact_after_click(model, T0, TAU)
        steer = steered_gamma(exact["p_click"], model.gamma)
        for reflection, r, st in (("full", 0, None), ("memory+last-1", 1, steer), ("full", 1, steer), ("memory+last-1", 1, None),
                                  ("memory+last-1", 2, None), ("memory+last-1", 3, None), ("full", 2, None), ("full", 3, None)):
            t0 = time.time()
            logical = loop_circuit(model, T0, TAU, r, reflection, st)
            qc = QuantumCircuit(logical.num_qubits, logical.num_qubits)
            qc.compose(logical, inplace=True)
            qc.measure(list(range(logical.num_qubits)), list(range(logical.num_qubits)))
            best = None
            for seed in range(6):
                pm = generate_preset_pass_manager(optimization_level=3, backend=backend, seed_transpiler=seed)
                isa = pm.run(qc)
                cz = isa.count_ops().get("cz", 0)
                if best is None or cz < best[0]:
                    best = (cz, isa)
            cz, isa = best
            result = sim.run(isa, shots=shots, seed_simulator=23 + r, memory=True).result()
            memory = result.get_memory()
            base = logical.num_qubits - TAU
            whole = read_after_click({m: memory.count(m) for m in set(memory)}, n, T0, base, TAU)
            errors = []
            kept = []
            for start in range(0, shots, chunk):
                part = memory[start:start + chunk]
                counts = {m: part.count(m) for m in set(part)}
                got = read_after_click(counts, n, T0, base, TAU)
                kept.append(got["kept"])
                errors.append(got["conditional"] - exact["conditional"])
            errors = np.array(errors)
            rmse = np.sqrt((errors ** 2).mean(axis=0))
            bias = whole["conditional"] - exact["conditional"]
            rows.append({"model": name, "reflection": reflection, "r": r, "steer": st, "cz": cz, "qubits": logical.num_qubits,
                         "kept_per_chunk": float(np.mean(kept)), "conditional": whole["conditional"], "bias": bias,
                         "rmse_at_chunk": rmse, "exact": exact["conditional"]})
            print(f"  {backend_name} {name:10s} {reflection:13s} r = {r}: {cz:3d} CZ, kept {np.mean(kept):7.1f} of {chunk}; "
                  f"conditional {np.round(whole['conditional'], 4)} (exact {np.round(exact['conditional'], 4)}); RMSE per "
                  f"{chunk} shots {np.round(rmse, 4)} [{time.time() - t0:.0f}s]", flush=True)
    return {"backend": backend_name, "shots": shots, "chunk": chunk, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--noiseless", action="store_true")
    ap.add_argument("--noisy")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.noiseless:
        print("E5: noiseless", flush=True)
        save("e5_inside_loop", noiseless(), "noiseless.json")
    if args.noisy:
        print(f"E5: noisy, {args.noisy}", flush=True)
        shots, chunk = (8192, 2048) if args.quick else (65536, 4096)
        save("e5_inside_loop", noisy(args.noisy, shots, chunk), f"noisy_{args.noisy}.json")


if __name__ == "__main__":
    main()
