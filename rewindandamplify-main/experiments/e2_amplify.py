"""E2: Grover on the QRSM's histories, built from real Qiskit circuits.

For six questions about a 6-step click history, this builds A, the oracle and Qiskit's grover_operator, and checks
three things at every iteration count, with pass marks fixed before the run:

  - the chance of a marked history follows sin^2((2r+1) theta);
  - inside the marked set, the distribution is exactly the conditional P(y | marked);
  - the hidden qubits, read from the amplified state, have exactly the populations the exact filter gives.

It then draws real shots from Aer, to show what the same number of shots gives with and without amplification.

    python experiments/e2_amplify.py [--quick]
"""

import argparse

from common import save

import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from qrsm_grover.amplify import amplified, iterations_to_peak, success_probability
from qrsm_grover.classical import conditional_distribution, expected_memory_population, total_variation
from qrsm_grover.model import QRSM, history_to_string
from qrsm_grover.predicates import any_click, at_least, click_at, contains, exact_record, odd_clicks

PASS = 1e-9
T = 6
MODEL = QRSM()


def predicates(T: int) -> list:
    return [any_click(), click_at(T), at_least(2), contains("11"), odd_clicks(), exact_record("001000")]


def curve(pred, r_extra: int) -> dict:
    n = MODEL.n_memory
    mask = pred.mask(T)
    probs = MODEL.history_probabilities(T)
    p = float(probs[mask].sum())
    r_peak = iterations_to_peak(p)
    A = MODEL.purified(T)
    lights = list(range(n, n + T))
    oracle = pred.oracle(n + T, lights)
    cond = conditional_distribution(probs, mask)
    pops_exact = expected_memory_population(MODEL.branches(T), mask, n)

    rows = []
    for r in range(0, r_peak + r_extra + 1):
        state = Statevector(amplified(A, oracle, r)).data
        joint = (np.abs(state) ** 2).reshape(2 ** T, 2 ** n)
        marginal = joint.sum(axis=1)
        hit = float(marginal[mask].sum())
        theory = float(success_probability(p, r))
        marked_joint = joint[mask] / joint[mask].sum()
        basis = np.arange(2 ** n)
        pops = np.array([marked_joint[:, ((basis >> q) & 1) == 1].sum() for q in range(n)])
        rows.append({"r": r, "hit": hit, "theory": theory, "error": abs(hit - theory),
                     "conditional_tvd": total_variation(conditional_distribution(marginal, mask), cond),
                     "population_error": float(np.abs(pops - pops_exact).max())})
    worst = {key: max(row[key] for row in rows) for key in ("error", "conditional_tvd", "population_error")}
    print(f"  {pred.name:22s} p = {p:.5f}, peak at r = {r_peak:2d}; worst errors: curve {worst['error']:.1e}, "
          f"conditional {worst['conditional_tvd']:.1e}, hidden qubits {worst['population_error']:.1e}", flush=True)
    return {"name": pred.name, "p": p, "r_peak": r_peak, "rows": rows, "worst": worst,
            "emitter_excited_given_marked": pops_exact[0], "defect_excited_given_marked": pops_exact[1]}


def shots_demo(shots: int) -> dict:
    """The same shots with and without amplification, on a question with real structure: any click in 4 steps."""
    T3 = 4
    pred = any_click()
    n = MODEL.n_memory
    mask = pred.mask(T3)
    probs = MODEL.history_probabilities(T3)
    p = float(probs[mask].sum())
    cond = conditional_distribution(probs, mask)
    A = MODEL.purified(T3)
    oracle = pred.oracle(n + T3, list(range(n, n + T3)))
    sim = AerSimulator(method="statevector")
    out = {"T": T3, "p": p, "shots": shots, "predicate": pred.name, "runs": []}
    order = np.nonzero(mask)[0][np.argsort(cond[mask])[::-1]]
    out["histories"] = [history_to_string(int(i), T3) for i in order]
    out["exact"] = cond[order]
    for r in (0, 1, 2):
        qc = amplified(A, oracle, r)
        qc.measure_all()
        tqc = transpile(qc, sim, optimization_level=0)
        counts = sim.run(tqc, shots=shots, seed_simulator=1000 + r).result().get_counts()
        hist = np.zeros(2 ** T3)
        for bits, c in counts.items():
            hist[(int(bits, 2) >> n) & (2 ** T3 - 1)] += c
        accepted = hist[mask].sum()
        est = np.where(mask, hist, 0) / max(accepted, 1)
        out["runs"].append({"r": r, "accepted": accepted, "estimate": est[order],
                            "tvd_to_exact": total_variation(est, cond)})
        print(f"  r = {r}: {int(accepted)} of {shots} shots usable; TVD to the exact conditional {out['runs'][-1]['tvd_to_exact']:.4f}",
              flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    r_extra = 1 if args.quick else 3
    print(f"E2: amplification curves, T = {T}, 1 hidden defect ({MODEL.n_qubits(T)} qubits)", flush=True)
    curves = [curve(pred, r_extra) for pred in predicates(T)]
    worst = {key: max(c["worst"][key] for c in curves) for key in ("error", "conditional_tvd", "population_error")}
    passed = {key: val < PASS for key, val in worst.items()}
    print(f"E2: worst over all questions {worst}; pass mark {PASS}; passed: {passed}", flush=True)
    print("E2: 2,048 shots with and without amplification", flush=True)
    demo = shots_demo(2048)
    save("e2_amplify", {"T": T, "curves": curves, "worst": worst, "passed": passed, "shots_demo": demo})


if __name__ == "__main__":
    main()
