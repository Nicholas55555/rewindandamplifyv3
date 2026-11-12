"""E1: the same machine, now rewindable.

Swapping each reset for a fresh light must not change a single statistic of the QRSM. Two checks, with pass marks fixed
in docs/design_log.md before this ran:

  1. A|0> equals the Kraus branches, amplitude by amplitude, for 0, 1 and 2 defects, up to 12 steps.
  2. The dynamic circuit (real mid-circuit measure and reset) and the purified circuit click alike, each sampled
     1,000,000 times on Aer.

    python experiments/e1_purify.py [--quick]
"""

import argparse
import time

from common import save

import numpy as np
from qiskit import ClassicalRegister
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator
from scipy import stats

from qrsm_grover.classical import total_variation
from qrsm_grover.model import QRSM, history_to_string

MODELS = {0: QRSM(phi=(), zeta=()), 1: QRSM(), 2: QRSM(phi=(0.45, 0.25), zeta=(0.3, 0.7))}
PASS_AMPLITUDE = 1e-12
PASS_CHI2_P = 1e-3


def amplitude_check(T_max: int) -> list:
    rows = []
    for k, model in MODELS.items():
        for T in range(1, T_max + 1):
            state = Statevector(model.purified(T)).data.reshape(2 ** T, 2 ** model.n_memory)
            err = float(np.abs(state - model.branches(T)).max())
            rows.append({"k": k, "T": T, "qubits": model.n_qubits(T), "max_amplitude_error": err})
        print(f"  {k} defects: largest amplitude error {max(r['max_amplitude_error'] for r in rows if r['k'] == k):.2e}",
              flush=True)
    return rows


def reversibility_check() -> dict:
    """A then its inverse returns to the start exactly: the property the dynamic circuit does not have."""
    model = MODELS[1]
    T = 6
    A = model.purified(T)
    back = A.compose(A.inverse())
    return {"T": T, "return_probability": float(abs(Statevector(back).data[0]) ** 2),
            "A_is_unitary_error": float(np.abs(Operator(model.purified(3)).data.conj().T @ Operator(model.purified(3)).data
                                               - np.eye(2 ** model.n_qubits(3))).max())}


def counts_to_array(counts: dict, T: int) -> np.ndarray:
    out = np.zeros(2 ** T)
    for bits, n in counts.items():
        out[int(bits.replace(" ", ""), 2)] = n  # Qiskit prints clbit 0 last; clbit t is the click at step t + 1
    return out


def sampling_check(T: int, shots: int) -> dict:
    model = MODELS[1]
    sim = AerSimulator(method="statevector")
    t0 = time.time()
    dyn = counts_to_array(sim.run(model.dynamic(T), shots=shots, seed_simulator=101).result().get_counts(), T)
    t_dyn = time.time() - t0
    pure = model.purified(T)
    pure.add_register(ClassicalRegister(T, "click"))
    pure.measure(pure.qregs[-1], pure.cregs[0])
    t0 = time.time()
    pur = counts_to_array(sim.run(pure, shots=shots, seed_simulator=202).result().get_counts(), T)
    t_pur = time.time() - t0

    # chi-square of the two samples against each other, pooling histories too rare to test
    exact = model.history_probabilities(T)
    keep = exact * shots >= 5
    table = np.array([np.append(dyn[keep], dyn[~keep].sum()), np.append(pur[keep], pur[~keep].sum())])
    table = table[:, table.sum(axis=0) > 0]
    chi2, p_value, dof, _ = stats.chi2_contingency(table)
    # each sample against the exact distribution too
    tvd_dyn = total_variation(dyn / shots, exact)
    tvd_pur = total_variation(pur / shots, exact)
    print(f"  dynamic against purified: chi-square {chi2:.1f} on {dof} degrees of freedom, p = {p_value:.3f}", flush=True)
    print(f"  TVD to exact: dynamic {tvd_dyn:.5f}, purified {tvd_pur:.5f} ({shots:,} shots each)", flush=True)
    top = np.argsort(exact)[::-1][:8]
    return {"T": T, "shots": shots, "chi2": chi2, "dof": dof, "p_value": p_value, "tvd_dynamic_to_exact": tvd_dyn,
            "tvd_purified_to_exact": tvd_pur, "seconds_dynamic": t_dyn, "seconds_purified": t_pur,
            "histories": [history_to_string(int(i), T) for i in top], "exact": exact[top],
            "dynamic": dyn[top] / shots, "purified": pur[top] / shots}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    T_max, shots = (6, 50_000) if args.quick else (12, 1_000_000)

    print("E1: amplitudes of A|0> against the Kraus branches", flush=True)
    rows = amplitude_check(T_max)
    print("E1: reversibility", flush=True)
    rev = reversibility_check()
    print(f"  A then A-inverse returns to the start with probability {rev['return_probability']:.12f}", flush=True)
    print("E1: sampling the dynamic and purified circuits", flush=True)
    samp = sampling_check(6, shots)

    worst = max(r["max_amplitude_error"] for r in rows)
    passed = {"amplitudes": worst < PASS_AMPLITUDE, "sampling": samp["p_value"] > PASS_CHI2_P}
    print(f"E1: largest amplitude error {worst:.2e} (pass mark {PASS_AMPLITUDE}); chi-square p {samp['p_value']:.3f} "
          f"(pass mark {PASS_CHI2_P}); passed: {passed}", flush=True)
    save("e1_purify", {"amplitude_rows": rows, "reversibility": rev, "sampling": samp, "passed": passed})


if __name__ == "__main__":
    main()
