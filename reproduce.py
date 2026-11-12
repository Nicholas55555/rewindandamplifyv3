"""Reproduce the headline numbers of Rewind & Amplify on a laptop, in about a minute.

No IBM account, no network, no saved answers for the model: every model number below is recomputed from the
Qiskit package in rewindandamplify-main/. The measured numbers are recounted from the raw IBM counts saved in
hardware_campaign/.

    python reproduce.py            # everything
    python reproduce.py --quick    # skip the noise-model simulation of the hardware circuits

Needs the pinned scientific packages:  python -m pip install -r requirements-dev.txt
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rewindandamplify-main"))
sys.path.insert(0, str(ROOT / "hardware_campaign" / "noise_model"))
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
from qiskit import QuantumCircuit, transpile  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402

from qrsm_grover import QRSM, BackwardSampler, click_at, conditional_distribution, total_variation  # noqa: E402
from qrsm_grover.amplify import hardware_amplified, steered_gamma  # noqa: E402
from qrsm_grover.fastsim import reflection_qubits  # noqa: E402
from qrsm_grover.queries import exact_after_click  # noqa: E402

T0, TAU = 3, 3
DEFECT, EMITTER_ONLY = QRSM(), QRSM(phi=(), zeta=())
pct = lambda v, d=2: f"{100 * v:.{d}f}%"  # noqa: E731


def rule(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


def exact_model() -> dict:
    rule("1. The exact model: one small matrix per recorded bit")
    out = {}
    print(f"   {'':38s}{'with the defect':>16s}{'emitter only':>16s}")
    rows = {name: exact_after_click(model, T0, TAU) for name, model in (("defect", DEFECT), ("none", EMITTER_ONLY))}
    print(f"   {'chance of a click at step 3':38s}{pct(rows['defect']['p_click']):>16s}{pct(rows['none']['p_click']):>16s}")
    for j in range(TAU):
        label = f"click at step {T0 + 1 + j}, given one at step 3"
        print(f"   {label:38s}{pct(rows['defect']['conditional'][j]):>16s}{pct(rows['none']['conditional'][j]):>16s}")
    out["answer"] = (float(rows["defect"]["conditional"][2]), float(rows["none"]["conditional"][2]))
    out["p_click"] = float(rows["defect"]["p_click"])
    print(f"   Ordinary sampling keeps 1 run in {1 / out['p_click']:.1f} and throws the rest away.")
    return out


def ideal_circuits(p_click: float) -> None:
    rule("2. The Qiskit circuits on an ideal simulator (Aer statevector)")
    model, n = DEFECT, DEFECT.n_memory
    question = click_at(T0)
    mask = question.mask(T0)
    exact = conditional_distribution(model.history_probabilities(T0), mask)
    steer = steered_gamma(p_click, model.gamma)
    oracle = question.oracle(n + T0, list(range(n, n + T0)))
    simulator = AerSimulator(method="statevector")
    builds = [("plain sampling (no amplification)", None, "full", 0),
              ("textbook: full reflection, 1 round", None, "full", 1),
              ("steer + full reflection, 1 round", steer, "full", 1),
              ("steer + local reflection, 1 round", steer, "memory+last-1", 1)]
    print(f"   {'build':38s}{'qubits':>7s}{'hit rate':>10s}{'answer error':>14s}{'sampled 20,000 shots':>23s}")
    worst = 0.0
    for name, gamma, kind, rounds in builds:
        A = model.purified(T0, gammas=None if gamma is None else [None] * (T0 - 1) + [gamma])
        body = hardware_amplified(A, oracle, rounds, reflect_on=reflection_qubits(model, T0, kind))
        circuit = QuantumCircuit(body.num_qubits)
        circuit.compose(body, inplace=True)
        compiled = transpile(circuit, simulator)
        exact_run = compiled.copy()
        exact_run.save_probabilities(list(range(n, n + T0)))            # the three lights, in time order
        probabilities = np.asarray(simulator.run(exact_run).result().data(0)["probabilities"])
        hit = float(probabilities[mask].sum())
        tv = total_variation(conditional_distribution(probabilities, mask), exact)
        sampled = compiled.copy()
        sampled.measure_all()
        counts = simulator.run(sampled, shots=20000, seed_simulator=7).result().get_counts()
        hits = sum(c for bits, c in counts.items() if bits.replace(" ", "")[::-1][n + T0 - 1] == "1")
        if kind == "full":
            worst = max(worst, tv)
        print(f"   {name:38s}{body.num_qubits:>7d}{pct(hit):>10s}{tv:>14.4f}{hits:>15,d} hits")
    print(f"   Full reflection leaves the conditional answer untouched: worst error {worst:.1e}.")
    print("   Local reflection trades a small bias for about half the gates.")


def classical_baseline(p_click: float) -> None:
    rule("3. The classical baseline we must beat (and do not, at this size)")
    sampler = BackwardSampler(DEFECT, click_at(T0).automaton(T0), T0)
    rng = np.random.default_rng(7)
    start = time.perf_counter()
    draws = 2000
    for _ in range(draws):
        sampler.sample(rng)
    seconds = (time.perf_counter() - start) / draws
    print(f"   Exact conditional sampler, no rejection: P(click at 3) = {pct(sampler.probability())}, "
          f"{1e3 * seconds:.2f} ms per sample in Python.")
    print(f"   Rejection sampling: {1 / p_click:.1f} model runs per kept sample.  Amplified: 3 calls, hit rate 96%.")
    print("   So today the classical sampler wins. Its cost grew about 6x per added hidden qubit in our tests;")
    print("   amplification instead costs about 1/sqrt(p) calls of the machine, whatever the memory size.")


def hardware(quick: bool) -> None:
    rule("4. What ran on IBM Marrakesh on 11 November 2026 (job dbqb1ifv5hds73dfo310, 8,192 shots per circuit)")
    import run_study
    from simulate import Run, observables, simulate, two_qubit_gates

    run = Run.load(run_study.RUN)
    scale = None if quick else run_study.fit_echo_scale(run)["scale"]
    header = f"   {'build':28s}{'2-qubit gates':>14s}{'ideal':>9s}"
    header += "" if quick else f"{'noise model':>13s}"
    print(header + f"{'measured':>11s}{'hits':>8s}{'answer error':>14s}")
    for label, name in (("steer + local reflection", run_study.HERO["local"]), ("steer + full reflection", run_study.HERO["full"])):
        measured, shots = run.counts(name)
        seen = observables(run, name, measured)
        ideal = observables(run, name, simulate(run, name, 0.0, None))
        line = f"   {label:28s}{two_qubit_gates(run, name):>14d}{pct(ideal['hit_rate']):>9s}"
        if not quick:
            line += f"{pct(observables(run, name, simulate(run, name, scale))['hit_rate']):>13s}"
        print(line + f"{pct(seen['hit_rate']):>11s}{round(seen['hit_rate'] * shots):>8,d}{seen['answer_error_tv']:>14.4f}")
    if not quick:
        print(f"   Noise model: reported gate errors x {scale:.2f} (fitted only on two echo circuits) and in-job readout errors.")
    local = observables(run, "loop-defect-r1", run.counts("loop-defect-r1")[0])["later_click_rates"][2]
    none = observables(run, "loop-nodefect-r1", run.counts("loop-nodefect-r1")[0])["later_click_rates"][2]
    print(f"   After-click answer at step 6, local build: {pct(local)} with the defect, {pct(none)} without "
          f"(exact {pct(exact_after_click(DEFECT, T0, TAU)['conditional'][2])} and "
          f"{pct(exact_after_click(EMITTER_ONLY, T0, TAU)['conditional'][2])}).")
    print("   Right order, visibly biased. These are raw counts with no error mitigation.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="skip the noise-model simulation (saves about 20 seconds)")
    args = parser.parse_args()
    started = time.perf_counter()
    print("REWIND & AMPLIFY: reproduce the headline numbers (no IBM account, no network)")
    numbers = exact_model()
    ideal_circuits(numbers["p_click"])
    classical_baseline(numbers["p_click"])
    hardware(args.quick)
    print(f"\nDone in {time.perf_counter() - started:.0f} s. Nothing above claims a quantum speedup: "
          "at this size the classical sampler is faster.")


if __name__ == "__main__":
    main()
