"""The reader in the oracle slot: find a table in an unsorted catalogue from a vague request.

This is Timofey's idea from the team chat: "a system that lets you retrieve data from a vague human search". Classical code
does what classical code is good at, and a coherent QRSM does the marking:

    1. classical      a vague request is tokenised into catalogue keywords, by stop words and a synonym table
    2. reader QRSM    the index register holds every entry at once. Reading token s applies one diagonal step D_s, which
                      turns the phase of each entry containing that token. This is the phase-layer QRSM of the circuit
                      diagrams (figure 5): one diagonal gate per symbol, no resets, and no measurement.
    3. Grover         a diffusion step turns those phases into probability.

An entry matching every token ends up with phase pi: a normal Grover mark. An entry matching some of them gets a partial
phase, and gets a partial boost: the first iteration multiplies its probability by about 5 - 4 cos(phase). So the same
circuit ranks partial matches, which is what makes a vague search possible.

The honest limit, which experiments/e6_catalog.py measures: the oracle is compiled FROM the catalogue, so classical code
has already looked at every entry, and at N entries the diagonal costs up to N - 2 two-qubit gates. For arbitrary data
that is no faster than a scan. Grover's square root needs an oracle that is cheaper than reading the data.
"""

from __future__ import annotations

import re

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import DiagonalGate

CATALOG = [
    "quarterly_sales_by_region",
    "monthly_sales_by_product",
    "customer_churn_by_region",
    "employee_payroll_by_department",
    "website_traffic_by_day",
    "warehouse_inventory_by_product",
    "support_tickets_by_customer",
    "marketing_spend_by_channel",
    "qubit_t1_times_by_device",
    "qubit_readout_errors_by_device",
    "shipping_costs_by_region",
    "product_returns_by_month",
    "energy_usage_by_building",
    "student_grades_by_course",
    "sensor_faults_by_device",
    "annual_revenue_by_department",
]

SYNONYMS = {
    "sell": "sales", "sold": "sales", "selling": "sales", "sale": "sales", "revenue": "sales", "income": "sales",
    "area": "region", "areas": "region", "place": "region", "places": "region", "territory": "region",
    "regions": "region", "location": "region",
    "staff": "employee", "worker": "employee", "workers": "employee", "people": "employee", "employees": "employee",
    "pay": "payroll", "salary": "payroll", "salaries": "payroll", "wages": "payroll",
    "stock": "inventory", "goods": "inventory",
    "clients": "customer", "customers": "customer", "client": "customer", "leaving": "churn", "lost": "churn",
    "visits": "traffic", "visitors": "traffic", "site": "website", "web": "website",
    "machine": "device", "machines": "device", "devices": "device", "chip": "device", "chips": "device",
    "qubits": "qubit", "decoherence": "t1", "lifetime": "t1",
    "mistakes": "errors", "failures": "faults", "broken": "faults",
    "items": "product", "products": "product", "ads": "marketing", "advertising": "marketing",
    "power": "energy", "electricity": "energy", "tickets": "tickets", "complaints": "tickets",
    "quarter": "quarterly", "yearly": "annual", "year": "annual", "month": "monthly", "daily": "day",
    "marks": "grades", "class": "course", "classes": "course", "pupils": "student", "students": "student",
    "team": "department", "teams": "department", "delivery": "shipping", "freight": "shipping",
    "refunds": "returns", "returned": "returns",
}
STOP_WORDS = set("a an and are at by did do does each for from get give how i in is it last me much many my of on or our "
                 "per show the their this to us was we were what which who why with you your all any can could please "
                 "want need find".split())


def tokens_of(name: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", name.lower()) if t and t not in STOP_WORDS}


def tokenise(request: str, vocabulary: set) -> list:
    """A vague request to catalogue keywords. Classical on purpose: a real system would use an embedding model here."""
    out = []
    for word in re.findall(r"[a-z0-9]+", request.lower()):
        if word in STOP_WORDS:
            continue
        word = SYNONYMS.get(word, word)
        if word in vocabulary and word not in out:
            out.append(word)
    return out


def demo_catalog(n: int) -> list:
    return CATALOG[:n]


def classical_scores(catalog: list, query_tokens: list) -> np.ndarray:
    """The classical answer: for each entry, the share of the query's tokens it contains."""
    if not query_tokens:
        return np.zeros(len(catalog))
    return np.array([sum(t in tokens_of(name) for t in query_tokens) / len(query_tokens) for name in catalog])


def phases(catalog: list, query_tokens: list) -> np.ndarray:
    """The phase each entry has built up once the reader has read the whole query: pi times the score."""
    return np.pi * classical_scores(catalog, query_tokens)


def reader_steps(catalog: list, query_tokens: list) -> list:
    """The reader's diagonal step for each token, in reading order. Together they give phases(catalog, tokens)."""
    steps = []
    for tok in query_tokens:
        match = np.array([tok in tokens_of(name) for name in catalog], dtype=float)
        steps.append(np.exp(1j * np.pi * match / len(query_tokens)))
    return steps


def catalog_circuit(catalog: list, request: str, r: int) -> QuantumCircuit:
    """Uniform superposition over the index, then r rounds of (read the query, diffuse)."""
    n = int(np.log2(len(catalog)))
    if 2 ** n != len(catalog):
        raise ValueError("the catalogue size must be a power of two")
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    query = tokenise(request, vocabulary)
    qc = QuantumCircuit(n, name=f"catalog(r={r})")
    qc.h(range(n))
    for _ in range(r):
        for diagonal in reader_steps(catalog, query):
            qc.append(DiagonalGate(list(diagonal)), list(range(n)))
        qc.h(range(n))
        qc.x(range(n))
        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1)
        qc.h(n - 1)
        qc.x(range(n))
        qc.h(range(n))
    return qc


def amplified_probabilities(phase: np.ndarray, r: int) -> np.ndarray:
    """The same search as catalog_circuit, computed directly: for any catalogue size, and for checking the circuit."""
    N = len(phase)
    state = np.full(N, 1 / np.sqrt(N), dtype=complex)
    for _ in range(r):
        state = np.exp(1j * phase) * state
        state = 2 * state.mean() - state
    return np.abs(state) ** 2


def best_iterations(phase: np.ndarray, r_max: int = 200) -> int:
    """The r that puts the most probability on the top-scoring entries."""
    top = phase >= phase.max() - 1e-12
    hits = [amplified_probabilities(phase, r)[top].sum() for r in range(r_max + 1)]
    return int(np.argmax(hits))
