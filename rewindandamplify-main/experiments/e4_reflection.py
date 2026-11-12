"""E4: the memory reflection. How much of the zero reflection does a QRSM really need?

Textbook amplification reflects about the whole start state, so it needs a multi-controlled gate over every qubit, and
that gate grows with the record length T. This experiment asks what happens if the reflection only looks at some of
the qubits, above all at the small hidden memory.

    --noiseless   exact simulation: reflections x questions x lengths, and the leak diagnostic
    --noisy NAME  Aer with one IBM device snapshot, compiled and scheduled for that device

    python experiments/e4_reflection.py --noiseless
    python experiments/e4_reflection.py --noisy FakeFez
"""

import argparse
import time

from common import save

import numpy as np
from scipy import stats

from qrsm_grover.amplify import iterations_to_peak, success_probability
from qrsm_grover.classical import conditional_distribution, total_variation
from qrsm_grover.fastsim import FastPurified, light_distribution, reflection_qubits
from qrsm_grover.model import QRSM
from qrsm_grover.predicates import any_click, at_least, click_at, contains, odd_clicks

MODEL = QRSM()
NOISY_SHOTS = 32768


def questions(T: int) -> list:
    return [any_click(), click_at(T), odd_clicks(), at_least(2), contains("11")]


def leak_fraction(fast: FastPurified, psi: np.ndarray, mask: np.ndarray, reflect_on) -> float:
    """The share of the rewound marked state that the reflection cannot see: 0 means exact at the first iteration.

    Rewinding the marked part gives a = A^dagger |g>. The full reflection handles the part of a along |0>. What matters
    is the rest, of squared length p - p^2, and how much of it has the watched qubits all at 0.
    """
    g = np.where(np.repeat(mask, fast.dim), psi, 0)
    p = float(np.vdot(g, g).real)
    rewound = fast.backward(g)
    seen = fast.zero_mask(reflect_on)
    hidden = float(np.sum(np.abs(rewound[seen]) ** 2)) - p ** 2
    return hidden / (p - p ** 2)


def noiseless_grid(T_values: list, r_cap: int = 40) -> list:
    rows = []
    for T in T_values:
        fast = FastPurified(MODEL, T)
        psi = fast.forward(fast.zero_state())
        probs = light_distribution(psi, T, fast.dim)
        kinds = ["full", "memory", "emitter", "lights"]
        if T >= 4:
            kinds += ["memory+last-1", "memory+last-2"]
        for pred in questions(T):
            mask = pred.mask(T)
            p = float(probs[mask].sum())
            r_peak = iterations_to_peak(p)
            cond = conditional_distribution(probs, mask)
            r_max = min(max(r_peak + 2, 3), r_cap)
            for kind in kinds:
                rq = reflection_qubits(MODEL, T, kind)
                series = []
                for r, state in fast.amplify(mask, r_max, rq):
                    d = light_distribution(state, T, fast.dim)
                    hit = float(d[mask].sum())
                    series.append({"r": r, "hit": hit, "tvd": total_variation(conditional_distribution(d, mask), cond)})
                exact_gain = [float(success_probability(p, s["r"])) - p for s in series]
                rows.append({"T": T, "question": pred.name, "p": p, "r_peak": r_peak, "reflection": kind,
                             "watched_qubits": len(rq), "leak": leak_fraction(fast, psi, mask, rq), "series": series,
                             "best_hit": max(s["hit"] for s in series), "gain_kept_r1": (series[1]["hit"] - p) / exact_gain[1]})
            print(f"  T = {T:2d}  {pred.name:20s} p = {p:.5f}  r_peak = {r_peak}", flush=True)
    return rows


def summarise_noiseless(rows: list) -> dict:
    mem = [r for r in rows if r["reflection"] == "memory"]
    # the logged expectation: the share of the gain kept at r <= 3, for single-event questions at T <= 6
    single = [r for r in mem if r["question"].startswith(("any click", "click at")) and r["T"] <= 6]
    kept, tvds = [], []
    for row in single:
        for s in row["series"][1:4]:
            exact = float(success_probability(row["p"], s["r"]))
            if exact - row["p"] > 0.05:
                kept.append((s["hit"] - row["p"]) / (exact - row["p"]))
                tvds.append(s["tvd"])
    multi = [r for r in mem if r["question"].startswith(("at least", "contains"))]
    leak = np.array([r["leak"] for r in mem])
    loss = np.array([1 - r["gain_kept_r1"] for r in mem])
    rho = stats.spearmanr(leak, loss)
    out = {"single_event_gain_kept": {"min": min(kept), "median": float(np.median(kept)), "n": len(kept)},
           "single_event_tvd_max": max(tvds),
           "multi_click_best_hit": {"min": min(r["best_hit"] for r in multi), "median": float(np.median([r["best_hit"] for r in multi]))},
           "leak_vs_loss_spearman": float(rho.statistic), "leak_vs_loss_p": float(rho.pvalue), "n_cells": len(mem)}
    print(f"  single-event questions, T <= 6, r <= 3: gain kept {out['single_event_gain_kept']}, worst TVD {out['single_event_tvd_max']:.3f}")
    print(f"  multi-click questions: best hit rate {out['multi_click_best_hit']}")
    print(f"  leak against loss of gain at r = 1: Spearman {rho.statistic:.3f} (p = {rho.pvalue:.1e})", flush=True)
    return out


# ---------------------------------------------------------------------------- noisy device simulators


def noisy_grid(backend_name: str, T_values: list, r_values: list, seeds: int) -> dict:
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
        for pred in (any_click(), click_at(T)):
            mask = pred.mask(T)
            p = float(probs[mask].sum())
            cond = conditional_distribution(probs, mask)
            oracle = pred.oracle(n + T, list(range(n, n + T)))
            for kind in ("full", "memory"):
                rq = reflection_qubits(MODEL, T, kind)
                noiseless = {r: light_distribution(s, T, fast.dim) for r, s in fast.amplify(mask, max(r_values), rq)}
                for r in r_values:
                    if r == 0 and kind == "memory":
                        continue  # r = 0 has no reflection, so the two are the same circuit
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
                    d = noiseless[r]
                    rows.append({"T": T, "question": pred.name, "p": p, "reflection": kind, "r": r, "cz": cz,
                                 "depth": isa.depth(), "qubits": body.num_qubits, "noiseless_hit": float(d[mask].sum()),
                                 "noiseless_tvd": total_variation(conditional_distribution(d, mask), cond),
                                 "hit": hit, "tvd": total_variation(np.where(mask, hist, 0) / hist[mask].sum(), cond),
                                 "shots": NOISY_SHOTS})
                    print(f"  {backend_name} T={T} {pred.name:16s} {kind:6s} r={r}: {cz:3d} CZ, hit {hit:.3f} (noiseless "
                          f"{d[mask].sum():.3f}), TVD {rows[-1]['tvd']:.3f}  [{time.time() - t0:.0f}s]", flush=True)
    return {"backend": backend_name, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--noiseless", action="store_true")
    ap.add_argument("--noisy", help="an IBM fake backend name, such as FakeFez")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.noiseless:
        print("E4: noiseless grid", flush=True)
        rows = noiseless_grid([3, 4] if args.quick else [3, 4, 5, 6, 7, 8, 9, 10])
        save("e4_reflection", {"rows": rows, "summary": summarise_noiseless(rows)}, "noiseless.json")
    if args.noisy:
        print(f"E4: noisy grid on {args.noisy}", flush=True)
        data = noisy_grid(args.noisy, [3] if args.quick else [3, 4, 5], [0, 1, 2, 3], 2 if args.quick else 6)
        save("e4_reflection", data, f"noisy_{args.noisy}.json")


if __name__ == "__main__":
    main()
