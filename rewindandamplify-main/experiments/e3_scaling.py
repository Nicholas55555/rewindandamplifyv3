"""E3: the post-selection wall, and who wins at what scale.

Three honest measurements:

  1. Calls of the machine per conditioned sample, against how rare the condition is, for rejection sampling, for
     amplification with p known, and for amplification with p unknown (BBHT). Simulated exactly at T = 18.
  2. The wall itself: real 64-step records from the hidden-defect project, scored by the exact filter.
  3. The classical exact sampler's cost as the hidden memory grows. It wins at every size we can test; this measures
     how fast that lead shrinks.

    python experiments/e3_scaling.py [--quick]
"""

import argparse
import time

from common import DATA, save

import numpy as np

from qrsm_grover.amplify import (amplified_state, best_calls_per_hit, bbht_expected_calls, iterations_to_peak, success_probability)
from qrsm_grover.classical import BackwardSampler
from qrsm_grover.fastsim import FastPurified
from qrsm_grover.model import QRSM, history_to_string
from qrsm_grover.predicates import any_click

MODEL = QRSM()


def fit_slope(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def rarity_sweep(T: int, targets: np.ndarray, rng: np.random.Generator) -> dict:
    fast = FastPurified(MODEL, T)
    psi = fast.forward(fast.zero_state())
    probs = (np.abs(psi) ** 2).reshape(2 ** T, fast.dim).sum(axis=1)
    rows = []
    for target in targets:
        y = int(np.argmin(np.abs(np.log(np.maximum(probs, 1e-300)) - np.log(target))))
        p = float(probs[y])
        r_peak = iterations_to_peak(p)
        r_best, cost_known = best_calls_per_hit(p)
        marked = np.zeros(2 ** T, dtype=bool)
        marked[y] = True
        t0 = time.time()
        state = amplified_state(psi, np.repeat(marked, fast.dim), r_peak)
        hit = float((np.abs(state) ** 2).reshape(2 ** T, fast.dim).sum(axis=1)[y])
        seconds = time.time() - t0
        cost_bbht = bbht_expected_calls(p, rng, trials=400 if p < 1e-4 else 2000)
        rows.append({"record": history_to_string(y, T), "clicks": bin(y).count("1"), "p": p, "r_peak": r_peak,
                     "hit_at_peak": hit, "theory_at_peak": float(success_probability(p, r_peak)),
                     "rejection_calls": 1 / p, "best_r": r_best, "amplified_calls": cost_known, "bbht_calls": cost_bbht,
                     "seconds": seconds})
        print(f"  p = {p:.3e}: peak r = {r_peak:4d}, hit {hit:.4f} (theory {rows[-1]['theory_at_peak']:.4f}); calls per "
              f"sample: rejection {1 / p:12,.0f}, amplified {cost_known:9,.1f}, unknown p {cost_bbht:9,.1f}", flush=True)
    p = np.array([r["p"] for r in rows])
    fit_range = p <= 0.05
    slopes = {name: fit_slope(p[fit_range], np.array([r[key] for r in rows])[fit_range])
              for name, key in (("rejection", "rejection_calls"), ("amplified", "amplified_calls"), ("bbht", "bbht_calls"))}
    print(f"  slopes of log(calls) against log(p): {slopes}", flush=True)
    ratio = np.array([r["bbht_calls"] / r["amplified_calls"] for r in rows])
    return {"T": T, "rows": rows, "slopes": slopes, "bbht_over_known": {"min": ratio.min(), "median": np.median(ratio),
                                                                       "max": ratio.max()}}


def the_wall() -> dict:
    """How expensive it is to condition on one real 64-step record, and on growing prefixes of real records."""
    data = np.load(DATA / "ideal-k1-perfect.npz")
    records = data["count"]
    K = MODEL.kraus()
    log_p = np.zeros((len(records), records.shape[1]))
    psi = np.zeros((len(records), 2 ** MODEL.n_memory), dtype=complex)
    psi[:, 0] = 1.0
    running = np.zeros(len(records))
    for t in range(records.shape[1]):
        nxt = np.where(records[:, t:t + 1] == 1, psi @ K[1].T, psi @ K[0].T)
        norm = np.linalg.norm(nxt, axis=1)
        running += 2 * np.log(norm)
        psi = nxt / norm[:, None]
        log_p[:, t] = running
    final = log_p[:, -1]
    median_p = float(np.exp(np.median(final)))
    # steering: every step that clicks can be set to emit with certainty, which raises the record's weight by 1 / gamma
    clicks = records.sum(axis=1)
    steered_log_p = final - clicks * np.log(MODEL.gamma)
    median_steered = float(np.exp(np.median(steered_log_p)))
    steered_r = float(iterations_to_peak(median_steered))
    print(f"  steering every clicked step (median {np.median(clicks):.0f} clicks): median P rises to {median_steered:.3e}, so "
          f"rejection needs {1 / median_steered:,.0f} runs and amplification r = {steered_r:,.0f}", flush=True)
    steps = np.arange(1, records.shape[1] + 1)
    med = np.median(log_p, axis=0)
    q10, q90 = np.quantile(log_p, [0.1, 0.9], axis=0)
    typical_r = float(iterations_to_peak(median_p))
    print(f"  {len(records)} records of {records.shape[1]} steps: median P(record) {median_p:.3e}, so rejection needs "
          f"{1 / median_p:,.0f} runs per match", flush=True)
    print(f"  amplification would need r = {typical_r:,.0f} iterations, {2 * typical_r + 1:,.0f} calls", flush=True)

    # what those calls mean in gates, at 4 CZ per step and a 1 CZ memory reflection or a full one
    T = records.shape[1]
    cz_per_call = 4 * T
    cz_oracle_and_reflection = 2 * (2 + T)  # a generous linear-cost multi-controlled gate with ancillas
    cz_total = typical_r * (2 * cz_per_call + cz_oracle_and_reflection) + cz_per_call
    return {"records": len(records), "steps": int(records.shape[1]), "median_p": median_p,
            "median_clicks": float(np.median(clicks)), "median_steered_p": median_steered,
            "steered_rejection_runs": 1 / median_steered, "steered_r": steered_r, "steered_calls": 2 * steered_r + 1,
            "median_rejection_runs": 1 / median_p, "r_needed": typical_r, "amplified_calls": 2 * typical_r + 1,
            "qubits_needed": MODEL.n_qubits(T), "cz_total_estimate": cz_total,
            "error_rate_needed_for_one_expected_error": 1 / cz_total, "prefix_steps": steps,
            "prefix_log_p_median": med, "prefix_log_p_q10": q10, "prefix_log_p_q90": q90,
            "nats_per_step": float(-np.median(final) / records.shape[1])}


def classical_cost(n_values: list, T: int, samples: int) -> list:
    """Time for the exact sampler as the hidden memory grows: one emitter and n - 1 defects."""
    rows = []
    rng = np.random.default_rng(7)
    for n in n_values:
        k = n - 1
        model = QRSM(phi=tuple(0.45 - 0.02 * j for j in range(k)), zeta=tuple(0.3 + 0.1 * j for j in range(k)))
        t0 = time.time()
        sampler = BackwardSampler(model, any_click().automaton(T), T)
        t_build = time.time() - t0
        t0 = time.time()
        for _ in range(samples):
            sampler.sample(rng)
        t_sample = (time.time() - t0) / samples
        rows.append({"n_memory": n, "build_seconds": t_build, "seconds_per_sample": t_sample, "p": sampler.probability()})
        print(f"  n = {n:2d} hidden qubits: build {t_build:9.4f} s, {t_sample * 1e3:9.3f} ms per sample", flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    rng = np.random.default_rng(2026)
    T = 12 if args.quick else 18
    targets = 10.0 ** np.arange(-1.0, -4.1 if args.quick else -6.6, -0.5)
    print(f"E3: calls per conditioned sample, T = {T}", flush=True)
    sweep = rarity_sweep(T, targets, rng)
    print("E3: the wall", flush=True)
    wall = the_wall()
    print("E3: the exact classical sampler against hidden qubits", flush=True)
    classical = classical_cost(list(range(1, 8 if args.quick else 12)), 8, 20)
    build = np.array([r["build_seconds"] for r in classical])
    ns = np.array([r["n_memory"] for r in classical])
    late = ns >= max(ns.max() - 3, 1)
    growth = float(np.exp(np.polyfit(ns[late], np.log(build[late]), 1)[0]))
    print(f"E3: classical build time grows {growth:.1f} times per hidden qubit at the largest sizes", flush=True)
    save("e3_scaling", {"sweep": sweep, "wall": wall, "classical": classical, "classical_growth_per_qubit": growth})


if __name__ == "__main__":
    main()
