"""E4b: the question-local reflection. Watch the memory, plus the lights the question reads.

Added after E5 showed that the memory reflection scrambles the hidden state. For "a click at step T" this watches the
memory and one light, whatever T is: 3 qubits with one defect.

    --noiseless       T = 3 to 12: hit rate, history distortion and hidden-memory fidelity, for each reflection
    --noisy NAME      an IBM device snapshot: T = 3 to 6, r = 1 to 3, for the question-local reflection

    python experiments/e4b_local.py --noiseless --noisy FakeFez
"""

import argparse
import time

from common import save

import numpy as np

from qrsm_grover.amplify import success_probability
from qrsm_grover.classical import conditional_distribution, total_variation
from qrsm_grover.fastsim import FastPurified, light_distribution, reflection_qubits
from qrsm_grover.model import QRSM
from qrsm_grover.predicates import click_at

MODEL = QRSM()
KINDS = ("full", "memory", "memory+last-1", "memory+last-2")
LOCAL = "memory+last-1"
NOISY_SHOTS = 32768


def memory_fidelity(state: np.ndarray, branches: np.ndarray, mask: np.ndarray, T: int, dim: int) -> float:
    """The mean overlap of the hidden memory, history by history, with what the exact machine leaves.

    Weighted by how often each marked history comes up, so 1.0 means the hidden state after every marked history is
    exactly right. This is what hit rate and history distributions cannot see.
    """
    S = state.reshape(2 ** T, dim)[mask]
    B = branches[mask]
    weight = np.sum(np.abs(S) ** 2, axis=1)
    keep = weight > 1e-14
    overlap = np.abs(np.sum(S[keep].conj() * B[keep], axis=1)) ** 2
    fid = overlap / (weight[keep] * np.sum(np.abs(B[keep]) ** 2, axis=1))
    return float(np.dot(weight[keep] / weight[keep].sum(), fid))


def noiseless(T_values: list, r_max: int = 4) -> list:
    rows = []
    for T in T_values:
        fast = FastPurified(MODEL, T)
        branches = MODEL.branches(T)
        probs = np.sum(np.abs(branches) ** 2, axis=1)
        pred = click_at(T)
        mask = pred.mask(T)
        p = float(probs[mask].sum())
        cond = conditional_distribution(probs, mask)
        for kind in KINDS:
            if kind == "memory+last-2" and T < 2:
                continue
            rq = reflection_qubits(MODEL, T, kind)
            series = []
            for r, state in fast.amplify(mask, r_max, rq):
                d = light_distribution(state, T, fast.dim)
                hit = float(d[mask].sum())
                series.append({"r": r, "hit": hit, "exact_hit": float(success_probability(p, r)),
                               "tvd": total_variation(conditional_distribution(d, mask), cond),
                               "memory_fidelity": memory_fidelity(state, branches, mask, T, fast.dim)})
            rows.append({"T": T, "p": p, "reflection": kind, "watched_qubits": len(rq), "series": series})
            s = series[min(3, r_max)]
            print(f"  T = {T:2d} p = {p:.4f} {kind:14s} watches {len(rq):2d} of {MODEL.n_qubits(T):2d} qubits; r = 3: hit "
                  f"{s['hit']:.3f} (exact {s['exact_hit']:.3f}), TVD {s['tvd']:.4f}, memory fidelity {s['memory_fidelity']:.4f}",
                  flush=True)
    return rows


def noisy(backend_name: str, T_values: list, r_values: list, seeds: int) -> dict:
    from qiskit import QuantumCircuit
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime import fake_provider

    from qrsm_grover.amplify import hardware_amplified

    backend = getattr(fake_provider, backend_name)()
    sim = AerSimulator.from_backend(backend)
    n = MODEL.n_memory
    rows = []
    for T in T_values:
        A = MODEL.purified(T)
        fast = FastPurified(MODEL, T)
        probs = MODEL.history_probabilities(T)
        pred = click_at(T)
        mask = pred.mask(T)
        p = float(probs[mask].sum())
        cond = conditional_distribution(probs, mask)
        oracle = pred.oracle(n + T, list(range(n, n + T)))
        kinds = (LOCAL,) if T <= 5 else (LOCAL, "memory")  # T <= 5 has full and memory from e4_reflection.py; e7 covers full at T = 6
        for kind in kinds:
            rq = reflection_qubits(MODEL, T, kind)
            noiseless_d = {r: light_distribution(s, T, fast.dim) for r, s in fast.amplify(mask, max(r_values), rq)}
            for r in r_values:
                t0 = time.time()
                body = hardware_amplified(A, oracle, r, reflect_on=rq)
                qc = QuantumCircuit(body.num_qubits, body.num_qubits)
                qc.compose(body, inplace=True)
                qc.measure(list(range(body.num_qubits)), list(range(body.num_qubits)))
                best = None
                for seed in range(seeds):
                    pm = generate_preset_pass_manager(optimization_level=3, backend=backend, seed_transpiler=seed)
                    isa = pm.run(qc)
                    cz = isa.count_ops().get("cz", 0)
                    if best is None or cz < best[0]:
                        best = (cz, isa)
                cz, isa = best
                counts = sim.run(isa, shots=NOISY_SHOTS, seed_simulator=17 + r).result().get_counts()
                hist = np.zeros(2 ** T)
                for bits, c in counts.items():
                    hist[(int(bits.replace(" ", ""), 2) >> n) & (2 ** T - 1)] += c
                hit = hist[mask].sum() / NOISY_SHOTS
                d = noiseless_d[r]
                rows.append({"T": T, "question": pred.name, "p": p, "reflection": kind, "r": r, "cz": cz,
                             "depth": isa.depth(), "qubits": body.num_qubits, "noiseless_hit": float(d[mask].sum()),
                             "noiseless_tvd": total_variation(conditional_distribution(d, mask), cond), "hit": hit,
                             "tvd": total_variation(np.where(mask, hist, 0) / hist[mask].sum(), cond), "shots": NOISY_SHOTS})
                print(f"  {backend_name} T={T} {kind:14s} r={r}: {cz:3d} CZ, hit {hit:.3f} (noiseless {d[mask].sum():.3f}), "
                      f"TVD {rows[-1]['tvd']:.3f} [{time.time() - t0:.0f}s]", flush=True)
    return {"backend": backend_name, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--noiseless", action="store_true")
    ap.add_argument("--noisy")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.noiseless:
        print("E4b: noiseless", flush=True)
        save("e4_reflection", {"rows": noiseless([3, 4] if args.quick else list(range(3, 13)))}, "local_noiseless.json")
    if args.noisy:
        print(f"E4b: noisy, {args.noisy}", flush=True)
        data = noisy(args.noisy, [3] if args.quick else [3, 4, 5, 6], [1, 2, 3], 2 if args.quick else 6)
        save("e4_reflection", data, f"local_noisy_{args.noisy}.json")


if __name__ == "__main__":
    main()
