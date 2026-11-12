"""The short demo: ask a quantum recurrent model about its rare histories.

Every number below comes from a real Qiskit circuit run on Aer, in about a minute. No account is needed.

    python demo/demo.py                     the whole demo
    python demo/demo.py --pause             waits for Enter between parts, for presenting live
    python demo/demo.py --noisy FakeFez     runs it on an IBM device's noise model
    python demo/demo.py --query "how much did we sell in each area"
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from qrsm_grover.amplify import hardware_amplified, steered_gamma
from qrsm_grover.classical import conditional_distribution, total_variation
from qrsm_grover.fastsim import reflection_qubits
from qrsm_grover.hardware import measured
from qrsm_grover.model import QRSM, history_to_string
from qrsm_grover.predicates import click_at
from qrsm_grover.queries import exact_after_click, loop_circuit, read_after_click
from qrsm_grover.search import best_iterations, catalog_circuit, classical_scores, demo_catalog, phases, tokenise, tokens_of

ONE = QRSM()
NONE = QRSM(phi=(), zeta=())
LOCAL = "memory+last-1"
SHOTS = 1000

BOLD, DIM, ORANGE, BLUE, RESET = "\033[1m", "\033[2m", "\033[38;5;208m", "\033[38;5;33m", "\033[0m"


def heading(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}")


def bar(value: float, width: int = 36, colour: str = ORANGE) -> str:
    n = int(round(value * width))
    return f"{colour}{'█' * n}{RESET}{DIM}{'·' * (width - n)}{RESET}"


def run(sim, circuit, shots: int, seed: int) -> dict:
    return sim.run(transpile(circuit, sim, optimization_level=1), shots=shots, seed_simulator=seed).result().get_counts()


def histories_from(counts: dict, n: int, T: int) -> np.ndarray:
    hist = np.zeros(2 ** T)
    for bits, c in counts.items():
        hist[(int(bits.replace(" ", ""), 2) >> n) & (2 ** T - 1)] += c
    return hist


def part_rare_event(sim) -> None:
    T = 6
    n = ONE.n_memory
    heading(f"1. A rare event in a {T}-step run of the hidden-defect machine")
    pred = click_at(T)
    mask = pred.mask(T)
    probs = ONE.history_probabilities(T)
    p = float(probs[mask].sum())
    exact = conditional_distribution(probs, mask)
    print(f"   Question: what do the runs with a click at step {T} look like? Only {p:.1%} of runs have one.")
    print(f"   The reset is gone: each step gets a fresh light, so the {T}-step run is one reversible circuit A.")

    oracle = pred.oracle(n + T, list(range(n, n + T)))
    plain = hardware_amplified(ONE.purified(T), oracle, 0)
    steer = steered_gamma(p, ONE.gamma)
    steered = ONE.purified(T, gammas=[None] * (T - 1) + [steer])
    fused = hardware_amplified(steered, oracle, 1, reflect_on=reflection_qubits(ONE, T, LOCAL))
    exact_build = hardware_amplified(steered, oracle, 1)

    rows = []
    for label, circuit, seed in (("plain sampling", plain, 1), ("steer + 1 Grover iteration", exact_build, 2),
                                 ("steer + local reflection", fused, 3)):
        t0 = time.time()
        hist = histories_from(run(sim, measured(circuit), SHOTS, seed), n, T)
        hit = hist[mask].sum() / SHOTS
        est = np.where(mask, hist, 0) / max(hist[mask].sum(), 1)
        rows.append((label, hit, total_variation(est, exact), time.time() - t0))

    print(f"\n   {SHOTS} shots each, on Aer. Usable shots are the ones with the click:\n")
    for label, hit, tvd, _ in rows:
        print(f"   {label:28s} {bar(hit)} {hit:6.1%}   distance from the exact answer {tvd:.3f}")
    print(f"\n   Steering tuned the last emission from γ = {ONE.gamma} to {steer:.3f}, so p' = 1/4 and one iteration is enough.")
    print("   That scales every matching history by the same factor, so the answer stays exact.")
    top = np.argsort(exact)[::-1][:3]
    print("   Most likely runs with that click: " + ", ".join(f"{history_to_string(int(i), T)} ({exact[i]:.0%})" for i in top))


def part_after_click(sim) -> None:
    heading("2. Grover inside the loop: what happens right after the click?")
    print("   Amplify the click at step 3, then keep running the machine on fresh lights.\n")
    print("   With no hidden defect, a click wipes the machine, so what follows just restarts the run.")
    print("   A hidden defect remembers across the click. That difference is a fingerprint of hidden memory.\n")
    t0, tau = 3, 3
    print(f"   {'':12s} {'P(click 1, 2, 3 steps later | click)':42s} usable shots")
    for name, model in (("no defect", NONE), ("one defect", ONE)):
        n = model.n_memory
        exact = exact_after_click(model, t0, tau)
        steer = steered_gamma(exact["p_click"], model.gamma)
        circuit = loop_circuit(model, t0, tau, 1, LOCAL, steer)
        counts = run(sim, measured(circuit), 8 * SHOTS, 5)
        got = read_after_click(counts, n, t0, circuit.num_qubits - tau, tau)
        shown = "  ".join(f"{x:.3f}" for x in got["conditional"])
        truth = "  ".join(f"{x:.3f}" for x in exact["conditional"])
        print(f"   {name:12s} amplified {shown}   {got['kept']:,} of {got['shots']:,}")
        print(f"   {'':12s} {DIM}exact     {truth}{RESET}")


def part_search(sim, request: str) -> None:
    heading("3. The reader in the oracle slot: search an unsorted catalogue from a vague request")
    catalog = demo_catalog(16)
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    print(f'   Request: "{request}"')
    query = tokenise(request, vocabulary)
    print(f"   Classical step, tokenising: {query}")
    if not query:
        print("   No keywords matched this catalogue. Try another request.")
        return
    print(f"   The reader reads {len(query)} token(s), turning the phase of each of the {len(catalog)} entries that contains them.")
    ph = phases(catalog, query)
    scores = classical_scores(catalog, query)
    r = best_iterations(ph, 6)
    qc = catalog_circuit(catalog, request, r)
    counts = run(sim, measured(qc), SHOTS, 9)
    got = np.zeros(len(catalog))
    for bits, c in counts.items():
        got[int(bits.replace(" ", ""), 2) & (len(catalog) - 1)] += c
    got /= got.sum()
    print(f"\n   After {r} Grover iterations, from {SHOTS} shots on Aer:\n")
    for i in np.argsort(got)[::-1][:4]:
        print(f"   {catalog[i]:34s} {bar(float(got[i]), 30)} {got[i]:6.1%}   keyword score {scores[i]:.2f}")
    print(f"\n   Every entry started at {1 / len(catalog):.1%}. Partial matches get a partial boost: that is the vague part.")


def closing() -> None:
    heading("The honest part")
    print("   At this size a classical program answers all of this in about a millisecond, and exactly.")
    print("   The classical cost grew about 6 times per hidden qubit in our tests; these circuits grow slowly with it.")
    print("   So this shows an architecture that could matter for large hidden memories on future hardware,")
    print("   not a speedup today. The keyword search compiles its oracle from the catalogue, so it has no speedup at all")
    print("   on arbitrary data. See docs/REPORT.md.\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pause", action="store_true", help="wait for Enter between parts")
    ap.add_argument("--noisy", metavar="FAKE_BACKEND", help="an IBM device snapshot, such as FakeFez")
    ap.add_argument("--query", default="how much did we sell in each area")
    args = ap.parse_args()

    if args.noisy:
        from qiskit_ibm_runtime import fake_provider

        sim = AerSimulator.from_backend(getattr(fake_provider, args.noisy)())
        print(f"{DIM}Running on the noise model of {args.noisy}.{RESET}")
    else:
        sim = AerSimulator(method="statevector")
    print(f"{BOLD}Rewind & Amplify{RESET}: Grover's algorithm inside a quantum recurrent state machine")

    def wait():
        if args.pause:
            input(f"\n{DIM}Press Enter to continue ...{RESET}")

    part_rare_event(sim)
    wait()
    part_after_click(sim)
    wait()
    part_search(sim, args.query)
    wait()
    closing()


if __name__ == "__main__":
    main()
