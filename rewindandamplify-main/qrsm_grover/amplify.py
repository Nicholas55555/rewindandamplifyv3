"""Grover's algorithm in its general form, amplitude amplification, wrapped around the reversible QRSM.

With A the purified machine, p the total probability of the marked histories, and theta = arcsin(sqrt(p)):

    Q = A S_0 A^dagger S_f              one iteration
    P_r = sin^2((2r + 1) theta)         chance of a marked history after r iterations

Three facts carry the whole project.

    It reweights, and does not reshape. Inside the marked set, the relative amplitudes never change. So an amplified
    sample has exactly the conditional distribution P(y | y is marked): conditioning, at about 1/sqrt(p) cost rather
    than the 1/p of throwing runs away.

    Each iteration calls A twice, once forwards and once backwards. So r iterations cost 2r + 1 calls of the machine,
    and cost in calls is what the comparison with plain sampling has to use.

    Too many iterations overshoot, and p is usually unknown. `bbht_expected_calls` prices that in, using the standard
    answer of Boyer, Brassard, Hoyer and Tapp: try random iteration counts, growing slowly.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RCCXGate, ZGate, grover_operator


def rotation_angle(p: float) -> float:
    return float(np.arcsin(np.sqrt(p)))


def success_probability(p: float, r: int | np.ndarray) -> float | np.ndarray:
    """The ideal chance of a marked outcome after r iterations."""
    return np.sin((2 * np.asarray(r) + 1) * rotation_angle(p)) ** 2


def iterations_to_peak(p: float) -> int:
    """The r with the highest P_r: the usual Grover count."""
    th = rotation_angle(p)
    r = int(np.floor(np.pi / (4 * th)))
    return max(r, 0) if success_probability(p, r) >= success_probability(p, r + 1) else r + 1


def calls_per_hit(p: float, r: int) -> float:
    """Expected machine calls per marked sample at r iterations: (2r + 1) calls per try, divided by the hit rate."""
    return (2 * r + 1) / float(success_probability(p, r))


def best_calls_per_hit(p: float) -> tuple[int, float]:
    """The cheapest r for repeated sampling, with its cost. It is below the peak: stopping early pays."""
    r_hi = iterations_to_peak(p) + 2
    rs = np.arange(0, r_hi + 1)
    costs = (2 * rs + 1) / np.maximum(success_probability(p, rs), 1e-300)
    i = int(np.argmin(costs))
    return int(rs[i]), float(costs[i])


def bbht_expected_calls(p: float, rng: np.random.Generator, trials: int = 2000, growth: float = 6 / 5) -> float:
    """Average machine calls to find one marked sample when p is NOT known (BBHT schedule, simulated exactly)."""
    total = 0
    for _ in range(trials):
        m = 1.0
        while True:
            r = int(rng.integers(0, int(np.ceil(m))))
            total += 2 * r + 1
            if rng.random() < success_probability(p, r):
                break
            m = min(growth * m, 1.0 / np.sqrt(p) + 1)
    return total / trials


def steered_gamma(p: float, gamma: float, target: float = 0.25) -> float:
    """The emission strength for the clicked step that makes the marked probability `target`, or 1 if it cannot.

    A click's Kraus operator is sin(alpha) |0><1| on the emitter, so changing that one step's emission strength scales
    every history that clicks there by the same factor. Nothing about those histories changes but their total weight.
    So p can be raised for free, and at p = 1/4 exactly one iteration gives certainty: sin^2(3 pi / 6) = 1.

    It needs a rough value of p. It is forgiving: anything from p' = 0.18 to 0.32 still gives a hit rate above 0.94.
    """
    return min(1.0, target * gamma / p)


# ---------------------------------------------------------------------------- circuits


def grover_iterate(A: QuantumCircuit, oracle: QuantumCircuit, reflection_qubits: list | None = None) -> QuantumCircuit:
    """One iteration Q from Qiskit's own library. `reflection_qubits` defaults to every qubit of A."""
    return grover_operator(oracle, state_preparation=A, reflection_qubits=reflection_qubits)


def amplified(A: QuantumCircuit, oracle: QuantumCircuit, r: int, reflection_qubits: list | None = None) -> QuantumCircuit:
    """A followed by r iterations, on A's qubits, with no measurement."""
    qc = QuantumCircuit(*A.qregs, name=f"amplified(r={r})")
    qc.compose(A, inplace=True)
    if r:
        Q = grover_iterate(A, oracle, reflection_qubits)
        for _ in range(r):
            qc.compose(Q, inplace=True)
    return qc


def mcz_with_ancillas(qc: QuantumCircuit, qubits: Sequence, ancillas: Sequence) -> None:
    """A multi-controlled Z over `qubits`, built as a chain of AND gates into clean ancillas.

    Each AND is a relative-phase Toffoli (3 CNOTs where a true Toffoli needs 6). The unwanted phases cancel because
    every AND is undone exactly. Hardware has plenty of spare qubits and few gates to spare, so this trade is the right
    one: on heavy-hex it takes a 5-qubit reflection from 49 CZ to about half that.
    """
    qubits = list(qubits)
    m = len(qubits)
    if m == 1:
        qc.z(qubits[0])
        return
    if m <= 3:
        qc.append(ZGate().control(m - 1, annotated=True), qubits)
        return
    needed = m - 3
    if len(ancillas) < needed:
        raise ValueError(f"an MCZ on {m} qubits needs {needed} ancillas, got {len(ancillas)}")
    chain = []
    prev = qubits[0]
    rest = qubits[1:]
    for i in range(needed):
        qc.rccx(prev, rest[i], ancillas[i])
        chain.append((prev, rest[i], ancillas[i]))
        prev = ancillas[i]
    qc.append(ZGate().control(2, annotated=True), [prev, rest[needed], rest[needed + 1]])
    for a, b, c in reversed(chain):
        qc.append(RCCXGate().inverse(), [a, b, c])


def hardware_iterate(A: QuantumCircuit, oracle: QuantumCircuit, n_data: int, n_ancilla: int,
                     reflect_on: Sequence[int] | None = None) -> QuantumCircuit:
    """One iteration built by hand for real devices: the same Q, with an ancilla-assisted zero reflection.

    A and the oracle live on the first n_data qubits. `reflect_on` picks the qubits the zero reflection looks at, every
    data qubit by default. Up to a global phase this equals grover_iterate as long as the ancillas start in |0>, which
    the tests check.
    """
    qc = QuantumCircuit(n_data + n_ancilla, name="Q")
    data = list(range(n_data))
    watched = data if reflect_on is None else list(reflect_on)
    ancillas = list(range(n_data, n_data + n_ancilla))
    qc.compose(oracle, qubits=data, inplace=True)
    qc.compose(A.inverse(), qubits=data, inplace=True)
    qc.x(watched)
    mcz_with_ancillas(qc, watched, ancillas)
    qc.x(watched)
    qc.compose(A, qubits=data, inplace=True)
    return qc


def hardware_amplified(A: QuantumCircuit, oracle: QuantumCircuit, r: int, n_ancilla: int | None = None,
                       reflect_on: Sequence[int] | None = None) -> QuantumCircuit:
    """A and r hand-built iterations on n_data + n_ancilla qubits, with no measurement."""
    n_data = A.num_qubits
    watched = n_data if reflect_on is None else len(reflect_on)
    if n_ancilla is None:
        n_ancilla = max(watched - 3, 0)
    qc = QuantumCircuit(n_data + n_ancilla, name=f"hw_amplified(r={r})")
    qc.compose(A, qubits=list(range(n_data)), inplace=True)
    if r:
        Q = hardware_iterate(A, oracle, n_data, n_ancilla, reflect_on)
        for _ in range(r):
            qc.compose(Q, inplace=True)
    return qc


# ---------------------------------------------------------------------------- a fast exact simulator for long runs


def amplified_state(psi: np.ndarray, marked: np.ndarray, r: int) -> np.ndarray:
    """A statevector after r iterations, without building a circuit: for experiments with many qubits.

    `psi` is A|0> as a flat array and `marked` a boolean array of the same length. A S_0 A^dagger is the reflection
    about psi, so an iteration is a sign flip on the marked entries and then that reflection. The sign is chosen so
    that r iterations rotate towards the marked states, as the circuit version does up to a global phase.
    """
    state = psi.copy()
    for _ in range(r):
        state[marked] *= -1
        state = 2 * psi * np.vdot(psi, state) - state
    return state
