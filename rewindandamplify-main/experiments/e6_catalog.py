"""E6: the reader QRSM as a Grover oracle: find a table in an unsorted catalogue from a vague request.

Measures three things, kept apart as the research note asks:

  1. Does it find the right entry? 20 vague requests with a known intended table, against the classical score.
  2. What does it cost? Oracle gates and search iterations against a plain scan, for catalogues up to 1,024 entries.
  3. Does it survive noise? 8 entries, compiled for IBM device snapshots.

    python experiments/e6_catalog.py [--noisy FakeFez ...]
"""

import argparse

from common import save

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

from qrsm_grover.search import (amplified_probabilities, best_iterations, catalog_circuit, classical_scores, demo_catalog,
                                phases, tokenise, tokens_of)

REQUESTS = [
    ("how much did we sell in each area", "quarterly_sales_by_region"),
    ("what do we pay staff per team", "employee_payroll_by_department"),
    ("which clients are leaving by location", "customer_churn_by_region"),
    ("chip errors at readout", "qubit_readout_errors_by_device"),
    ("how long do qubits live on each machine", "qubit_t1_times_by_device"),
    ("stock in the warehouse for each item", "warehouse_inventory_by_product"),
    ("visitors to the site every day", "website_traffic_by_day"),
    ("what we spend on ads per channel", "marketing_spend_by_channel"),
    ("complaints from each client", "support_tickets_by_customer"),
    ("delivery costs for every area", "shipping_costs_by_region"),
    ("refunds each month", "product_returns_by_month"),
    ("electricity for each building", "energy_usage_by_building"),
    ("marks of pupils in every class", "student_grades_by_course"),
    ("broken sensors on the machines", "sensor_faults_by_device"),
    ("yearly revenue per team", "annual_revenue_by_department"),
    ("monthly sales of each product", "monthly_sales_by_product"),
    ("sales for the quarter by region", "quarterly_sales_by_region"),
    ("t1 lifetime of the chips", "qubit_t1_times_by_device"),
    ("salaries in each department", "employee_payroll_by_department"),
    ("customer churn", "customer_churn_by_region"),
]


def accuracy() -> dict:
    catalog = demo_catalog(16)
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    rows = []
    for request, target in REQUESTS:
        query = tokenise(request, vocabulary)
        scores = classical_scores(catalog, query)
        ph = phases(catalog, query)
        r = best_iterations(ph, 8)
        probs = amplified_probabilities(ph, r)
        one = amplified_probabilities(ph, 1)
        top_classical = catalog[int(np.argmax(scores))]
        top_quantum = catalog[int(np.argmax(probs))]
        target_index = catalog.index(target)
        order_ok = bool(np.all(np.diff(one[np.argsort(scores)]) >= -1e-9))
        rows.append({"request": request, "tokens": query, "target": target, "best_score": float(scores.max()),
                     "matches_at_top_score": int((scores == scores.max()).sum()), "classical_top": top_classical,
                     "quantum_top": top_quantum, "r": r, "target_probability": float(probs[target_index]),
                     "ranked_by_score_at_r1": order_ok, "start_probability": 1 / len(catalog)})
        print(f"  {request:42s} -> {str(query):44s} r = {r}: {top_quantum:34s} {probs[target_index]:.3f}", flush=True)
    summary = {"requests": len(rows),
               "classical_top1": float(np.mean([x["classical_top"] == x["target"] for x in rows])),
               "quantum_top1": float(np.mean([x["quantum_top"] == x["target"] for x in rows])),
               "agree": float(np.mean([x["classical_top"] == x["quantum_top"] for x in rows])),
               "ranked_at_r1": float(np.mean([x["ranked_by_score_at_r1"] for x in rows])),
               "median_target_probability": float(np.median([x["target_probability"] for x in rows]))}
    print(f"  {summary}", flush=True)
    return {"rows": rows, "summary": summary}


def costs() -> list:
    """Logical two-qubit gates, on an all-to-all device, for the search against a plain scan."""
    rows = []
    for n in range(3, 11):
        N = 2 ** n
        r = int(round(np.pi / 4 * np.sqrt(N)))
        rng = np.random.default_rng(n)
        diag = np.exp(1j * np.pi * rng.integers(0, 2, N))
        from qiskit.circuit.library import DiagonalGate

        qc = QuantumCircuit(n)
        qc.append(DiagonalGate(list(diag)), range(n))
        oracle = transpile(qc, basis_gates=["cz", "rz", "sx", "x"], optimization_level=1).count_ops().get("cz", 0)
        ds = QuantumCircuit(n)
        ds.h(range(n))
        ds.x(range(n))
        ds.h(n - 1)
        ds.mcx(list(range(n - 1)), n - 1)
        ds.h(n - 1)
        ds.x(range(n))
        ds.h(range(n))
        diffusion = transpile(ds, basis_gates=["cz", "rz", "sx", "x"], optimization_level=1).count_ops().get("cz", 0)
        rows.append({"n": n, "N": N, "classical_scan_steps": N, "grover_queries": r, "oracle_cz": oracle,
                     "diffusion_cz": diffusion, "total_cz": r * (oracle + diffusion)})
        print(f"  N = {N:5d}: scan {N:5d} steps; Grover {r:3d} queries of {oracle:5d} + {diffusion:5d} CZ = "
              f"{rows[-1]['total_cz']:8,d} CZ", flush=True)
    return rows


def reader_costs() -> list:
    """The oracle for "at least 2 clicks": a lookup table of all histories, against the recurrent reader."""
    from qrsm_grover.predicates import at_least, counter_bits, recurrent_counter_oracle

    rows = []
    for T in (4, 6, 8, 10, 12):
        lights = list(range(T))
        basis = ["cz", "rz", "sx", "x"]
        table = transpile(at_least(2).oracle(T, lights), basis_gates=basis, optimization_level=1).count_ops().get("cz", 0)
        reader = transpile(recurrent_counter_oracle(T, lights, 2), basis_gates=basis, optimization_level=1).count_ops().get("cz", 0)
        rows.append({"T": T, "lookup_cz": table, "reader_cz": reader, "counter_qubits": counter_bits(T)})
        print(f"  T = {T:2d}: lookup table {table:5d} CZ; reader {reader:4d} CZ with {counter_bits(T)} counter qubits", flush=True)
    return rows


def noisy(backend_name: str) -> dict:
    from qrsm_grover.hardware import compile_best, measured
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime import fake_provider

    backend = getattr(fake_provider, backend_name)()
    sim = AerSimulator.from_backend(backend)
    catalog = demo_catalog(8)
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    request = "what do we pay staff per team"
    query = tokenise(request, vocabulary)
    target = "employee_payroll_by_department"
    ph = phases(catalog, query)
    rows = []
    for r in (0, 1, 2):
        qc = measured(catalog_circuit(catalog, request, r))
        isa, info = compile_best(qc, backend, seeds=6)
        counts = sim.run(isa, shots=16384, seed_simulator=3 + r).result().get_counts()
        hist = np.zeros(8)
        for bits, c in counts.items():
            hist[int(bits.replace(" ", ""), 2)] += c
        hist /= hist.sum()
        ideal = amplified_probabilities(ph, r)
        rows.append({"r": r, "two_qubit_gates": info["two_qubit_gates"], "ideal": float(ideal[catalog.index(target)]),
                     "measured": float(hist[catalog.index(target)]), "distribution": hist, "ideal_distribution": ideal})
        print(f"  {backend_name} r = {r}: {info['two_qubit_gates']:3d} CZ; target {rows[-1]['measured']:.3f} (ideal "
              f"{rows[-1]['ideal']:.3f})", flush=True)
    return {"backend": backend_name, "request": request, "tokens": query, "target": target, "catalog": catalog, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--noisy", nargs="*", default=["FakeFez", "FakeTorino", "FakeKingston", "FakePittsburgh", "FakeMiami"])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--reader-only", action="store_true", help="only the oracle size comparison")
    args = ap.parse_args()
    if args.reader_only:
        print("E6: the recurrent reader against a lookup table", flush=True)
        save("e6_catalog", {"rows": reader_costs()}, "reader.json")
        return
    print("E6: accuracy on 20 vague requests, 16 entries", flush=True)
    acc = accuracy()
    print("E6: cost against a plain scan", flush=True)
    cost = [] if args.quick else costs()
    print("E6: noise, 8 entries", flush=True)
    noise = [noisy(b) for b in args.noisy[:1 if args.quick else None]]
    # one circuit check: the Qiskit circuit gives the same probabilities as the direct calculation
    check = []
    catalog = demo_catalog(8)
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    ph = phases(catalog, tokenise("what do we pay staff per team", vocabulary))
    for r in (0, 1, 2):
        d = np.abs(Statevector(catalog_circuit(catalog, "what do we pay staff per team", r)).data) ** 2
        check.append(float(np.abs(d - amplified_probabilities(ph, r)).max()))
    print(f"E6: circuit against direct calculation: largest difference {max(check):.1e}", flush=True)
    save("e6_catalog", {"accuracy": acc, "costs": cost, "noisy": noise, "circuit_check": check})


if __name__ == "__main__":
    main()
