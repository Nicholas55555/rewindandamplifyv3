"""E7: the resilient architecture against textbook Grover. Purify, steer, amplify locally, verify.

All on the question "a click at step T", on which every build below can run:

    plain            no amplification: just run the machine
    textbook         amplitude amplification at its peak iteration count, reflecting about the whole start state
    local            the same, with the question-local reflection
    steered          textbook reflection, on the machine steered to p' = 1/4, one iteration
    steered+local    question-local reflection on the steered machine, one iteration

    --noiseless     exact simulation of each build
    --noisy NAME    an IBM device snapshot
    --horizon       the bounded-rewind test: does the hit rate at a fixed rewind depth hold as T grows?
    --future        the gate-error budget each build needs as records grow

    python experiments/e7_resilience.py --noiseless --horizon --future --noisy FakeFez
"""

import argparse
import time

from common import save

import numpy as np

from qrsm_grover.amplify import iterations_to_peak, steered_gamma, success_probability
from qrsm_grover.classical import conditional_distribution, total_variation
from qrsm_grover.fastsim import FastPurified, light_distribution, reflection_qubits
from qrsm_grover.model import QRSM
from qrsm_grover.predicates import click_at

MODEL = QRSM()
LOCAL = "memory+last-1"
NOISY_SHOTS = 32768


def builds(T: int) -> list:
    """Each build's name, steered emission (or None), reflection, and iteration count."""
    probs = MODEL.history_probabilities(T)
    p = float(probs[click_at(T).mask(T)].sum())
    r_peak = iterations_to_peak(p)
    steer = steered_gamma(p, MODEL.gamma)
    return [("plain", None, "full", 0), ("textbook", None, "full", r_peak), ("local", None, LOCAL, r_peak),
            ("steered", steer, "full", 1), ("steered+local", steer, LOCAL, 1)]


def memory_fidelity(state: np.ndarray, branches: np.ndarray, mask: np.ndarray, T: int, dim: int) -> float:
    S = state.reshape(2 ** T, dim)[mask]
    B = branches[mask]
    weight = np.sum(np.abs(S) ** 2, axis=1)
    keep = weight > 1e-14
    overlap = np.abs(np.sum(S[keep].conj() * B[keep], axis=1)) ** 2
    fid = overlap / (weight[keep] * np.sum(np.abs(B[keep]) ** 2, axis=1))
    return float(np.dot(weight[keep] / weight[keep].sum(), fid))


def noiseless(T_values: list) -> list:
    rows = []
    for T in T_values:
        mask = click_at(T).mask(T)
        branches = MODEL.branches(T)
        probs = np.sum(np.abs(branches) ** 2, axis=1)
        cond = conditional_distribution(probs, mask)
        for name, steer, kind, r in builds(T):
            fast = FastPurified(MODEL, T, None if steer is None else [None] * (T - 1) + [steer])
            state = dict(fast.amplify(mask, r, reflection_qubits(MODEL, T, kind)))[r]
            d = light_distribution(state, T, fast.dim)
            rows.append({"T": T, "build": name, "steer": steer, "reflection": kind, "r": r, "p": float(probs[mask].sum()),
                         "hit": float(d[mask].sum()), "tvd": total_variation(conditional_distribution(d, mask), cond),
                         "memory_fidelity": memory_fidelity(state, branches, mask, T, fast.dim)})
            x = rows[-1]
            print(f"  T = {T:2d} {name:14s} r = {r}: hit {x['hit']:.4f}, TVD {x['tvd']:.4f}, memory fidelity "
                  f"{x['memory_fidelity']:.4f}", flush=True)
    return rows


def horizon(T_values: list, w_values: list) -> list:
    """Rewind only the last w steps, with the reflection on those w lights."""
    rows = []
    n = MODEL.n_memory
    for T in T_values:
        fast = FastPurified(MODEL, T)
        branches = MODEL.branches(T)
        probs = np.sum(np.abs(branches) ** 2, axis=1)
        mask = click_at(T).mask(T)
        p = float(probs[mask].sum())
        cond = conditional_distribution(probs, mask)
        lights = list(range(n, n + T))
        for w in w_values:
            if w > T:
                continue
            for r, state in fast.amplify(mask, 2, lights[T - w:], rewind=w):
                if r == 0:
                    continue
                d = light_distribution(state, T, fast.dim)
                rows.append({"T": T, "w": w, "r": r, "p": p, "exact_hit": float(success_probability(p, r)),
                             "hit": float(d[mask].sum()), "tvd": total_variation(conditional_distribution(d, mask), cond),
                             "memory_fidelity": memory_fidelity(state, branches, mask, T, fast.dim)})
            x = rows[-1]
            print(f"  T = {T:2d} p = {p:.3f} rewind {w:2d}: r = 2 hit {x['hit']:.3f} (exact {x['exact_hit']:.3f}), TVD "
                  f"{x['tvd']:.3f}, memory fidelity {x['memory_fidelity']:.3f}", flush=True)
    return rows


def future() -> list:
    """Two-qubit gates per conditioned sample as records grow, and the gate error each build needs.

    Gate counts are logical, from the structure: 4 CZ per step per machine call, a multi-controlled Z of about
    6 (m - 2) + 1 CZ with ancillas on m qubits, 7 CZ for a question-local reflection. The budget is one expected error
    per sample, so the error rate needed is 1 / gates. This is a scale estimate, not a compiled circuit.
    """
    rows = []
    for T in (4, 8, 16, 32, 64, 128):
        n = 2
        # a click after a typical run: the machine's long-run click rate
        p = 0.09
        r_text = iterations_to_peak(p)
        call = 4 * T
        mcz = 6 * (n + T - 2) + 1
        textbook = call + r_text * (2 * call + mcz)
        resilient = call + 1 * (2 * call + 7)
        horizon_w = 8
        bounded = call + 2 * (2 * 4 * min(horizon_w, T) + 6 * (min(horizon_w, T) - 2) + 1)
        rows.append({"T": T, "textbook_cz": textbook, "steered_local_cz": resilient, "bounded_rewind_cz": bounded,
                     "textbook_error_budget": 1 / textbook, "steered_local_error_budget": 1 / resilient,
                     "bounded_rewind_error_budget": 1 / bounded})
        print(f"  T = {T:3d}: textbook {textbook:7,d} CZ, steered + local {resilient:6,d}, bounded rewind {bounded:6,d}", flush=True)
    return rows


def noisy(backend_name: str, T_values: list, seeds: int, heavy_shots: int = NOISY_SHOTS) -> dict:
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime import fake_provider

    from qrsm_grover.hardware import compile_best, history_experiment

    backend = getattr(fake_provider, backend_name)()
    sim = AerSimulator.from_backend(backend)
    n = MODEL.n_memory
    rows = []
    for T in T_values:
        probs = MODEL.history_probabilities(T)
        pred = click_at(T)
        mask = pred.mask(T)
        cond = conditional_distribution(probs, mask)
        for name, steer, kind, r in builds(T):
            t0 = time.time()
            exp = history_experiment(name, MODEL, T, pred, kind, r, steer)
            isa, info = compile_best(exp.circuit, backend, seeds=seeds)
            # wide circuits can fall back to one trajectory per shot, which is slow: heavy_shots keeps those cells practical
            shots = heavy_shots if (T >= 6 and kind == "full" and r > 0) else NOISY_SHOTS
            counts = sim.run(isa, shots=shots, seed_simulator=31 + T).result().get_counts()
            hist = np.zeros(2 ** T)
            for bits, c in counts.items():
                hist[(int(bits.replace(" ", ""), 2) >> n) & (2 ** T - 1)] += c
            hit = hist[mask].sum() / shots
            tvd = total_variation(np.where(mask, hist, 0) / hist[mask].sum(), cond)
            rows.append({"T": T, "build": name, "steer": steer, "reflection": kind, "r": r, "hit": hit, "tvd": tvd,
                         "cz": info["two_qubit_gates"], "depth": info["depth"], "estimated_success": info["estimated_success"],
                         "qubits": exp.circuit.num_qubits, "shots": shots})
            print(f"  {backend_name} T = {T} {name:14s} r = {r}: {info['two_qubit_gates']:3d} CZ, hit {hit:.3f}, TVD {tvd:.3f} "
                  f"[{time.time() - t0:.0f}s]", flush=True)
    return {"backend": backend_name, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--noiseless", action="store_true")
    ap.add_argument("--horizon", action="store_true")
    ap.add_argument("--future", action="store_true")
    ap.add_argument("--noisy")
    ap.add_argument("--heavy-shots", type=int, default=NOISY_SHOTS, help="shots for full-reflection cells at T = 6")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.noiseless:
        print("E7: the builds, noiseless", flush=True)
        save("e7_resilience", {"rows": noiseless([3, 4] if args.quick else list(range(3, 15)))}, "noiseless.json")
    if args.horizon:
        print("E7: bounded rewinding", flush=True)
        save("e7_resilience", {"rows": horizon([10, 12] if args.quick else [10, 12, 14, 16, 18], [4, 6, 8, 10])}, "horizon.json")
    if args.future:
        print("E7: error budgets", flush=True)
        save("e7_resilience", {"rows": future()}, "future.json")
    if args.noisy:
        print(f"E7: noisy, {args.noisy}", flush=True)
        data = noisy(args.noisy, [3] if args.quick else [3, 4, 5, 6], 2 if args.quick else 6, args.heavy_shots)
        save("e7_resilience", data, f"noisy_{args.noisy}.json")


if __name__ == "__main__":
    main()
