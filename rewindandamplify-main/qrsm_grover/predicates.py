"""Questions you can ask about a click history, and the oracles that mark the histories that answer yes.

Every predicate gives three things that must agree, and the tests check that they do:

    mask(T)        which of the 2**T histories match (plain Python, the ground truth)
    automaton()    a small state machine that reads a history one click at a time and decides
    oracle(...)    a quantum circuit that flips the sign of matching histories

The automaton is the recurrent idea applied to the oracle. A question like "at least 2 clicks" can be answered by a
reader that keeps a running count, so its cost grows with T, where a lookup table of all histories grows with 2**T.
`recurrent_counter_oracle` is that reader as a reversible circuit: a coherent QRSM that reads the click register.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import DiagonalGate, ZGate


def popcount(y: np.ndarray, T: int) -> np.ndarray:
    return sum((y >> t) & 1 for t in range(T))


@dataclass(frozen=True)
class Automaton:
    """A deterministic finite automaton over clicks. delta[state][bit] is the next state; `accept` is a set."""

    n_states: int
    delta: tuple
    accept: frozenset
    start: int = 0

    def run(self, bits) -> bool:
        s = self.start
        for b in bits:
            s = self.delta[s][int(b)]
        return s in self.accept


# ---------------------------------------------------------------------------- building blocks


def mark_pattern(qc: QuantumCircuit, lights: list, pattern: list) -> None:
    """Flip the sign of the one basis state where lights == pattern (pattern[t] is the wanted bit of lights[t])."""
    zeros = [q for q, b in zip(lights, pattern) if not b]
    if zeros:
        qc.x(zeros)
    if len(lights) == 1:
        qc.z(lights[0])
    else:
        qc.append(ZGate().control(len(lights) - 1, annotated=True), lights)
    if zeros:
        qc.x(zeros)


def diagonal_oracle(mask: np.ndarray, n_qubits: int, lights: list) -> QuantumCircuit:
    """The lookup-table oracle: any predicate at all, by a diagonal gate over the whole click register."""
    qc = QuantumCircuit(n_qubits, name="oracle")
    qc.append(DiagonalGate([-1.0 if m else 1.0 for m in mask]), lights)
    return qc


# ---------------------------------------------------------------------------- predicates


@dataclass(frozen=True)
class Predicate:
    """A yes/no question about a click history."""

    name: str
    mask_fn: Callable[[np.ndarray, int], np.ndarray]
    automaton_fn: Callable[[int], Automaton]
    oracle_fn: Callable[[QuantumCircuit, list, int], None] | None = None  # a cheap direct oracle, if there is one

    def mask(self, T: int) -> np.ndarray:
        return self.mask_fn(np.arange(2 ** T), T)

    def automaton(self, T: int) -> Automaton:
        return self.automaton_fn(T)

    def oracle(self, n_qubits: int, lights: list) -> QuantumCircuit:
        """A circuit on n_qubits that flips the sign of matching histories in the `lights` register."""
        T = len(lights)
        if self.oracle_fn is None:
            return diagonal_oracle(self.mask(T), n_qubits, lights)
        qc = QuantumCircuit(n_qubits, name="oracle")
        self.oracle_fn(qc, lights, T)
        return qc


def any_click() -> Predicate:
    """At least one click. Costs one multi-controlled Z: flip the no-click history, and flip everything's sign."""

    def oracle(qc, lights, T):
        mark_pattern(qc, lights, [0] * T)
        qc.global_phase += np.pi

    return Predicate(
        "any click",
        lambda y, T: y != 0,
        lambda T: Automaton(2, ((0, 1), (1, 1)), frozenset({1})),
        oracle,
    )


def exact_record(record: str) -> Predicate:
    """One exact history, written in time order, such as '0010'. Conditioning on a recorded click sequence."""
    bits = [int(c) for c in record]
    target = sum(b << t for t, b in enumerate(bits))
    n = len(bits)

    def automaton(T):
        delta = [(i + 1 if bits[i] == 0 else n + 1, i + 1 if bits[i] == 1 else n + 1) for i in range(n)]
        delta += [(n + 1, n + 1), (n + 1, n + 1)]
        return Automaton(n + 2, tuple(delta), frozenset({n}))

    return Predicate(
        f"record {record}",
        lambda y, T: y == target,
        automaton,
        lambda qc, lights, T: mark_pattern(qc, lights, bits),
    )


def click_at(step: int) -> Predicate:
    """A click at this step (counted from 1), whatever else happened. A single Z gate."""

    def automaton(T):
        # state i < step: still counting steps; then 'yes' or 'no' forever
        yes, no = step, step + 1
        delta = [(i + 1, i + 1) for i in range(step - 1)]
        delta.append((no, yes))
        delta += [(yes, yes), (no, no)]
        return Automaton(step + 2, tuple(delta), frozenset({yes}))

    return Predicate(
        f"click at step {step}",
        lambda y, T: ((y >> (step - 1)) & 1) == 1,
        automaton,
        lambda qc, lights, T: qc.z(lights[step - 1]),
    )


def at_least(c: int) -> Predicate:
    """At least c clicks: a burst. Lookup-table oracle here; see recurrent_counter_oracle for the scalable one."""

    def automaton(T):
        delta = [(i, min(i + 1, c)) for i in range(c + 1)]
        return Automaton(c + 1, tuple(delta), frozenset({c}))

    return Predicate(f"at least {c} clicks", lambda y, T: popcount(y, T) >= c, automaton)


def contains(pattern: str) -> Predicate:
    """The pattern appears somewhere in the history, such as '11' for two clicks in a row."""
    pat = [int(c) for c in pattern]
    m = len(pat)

    def mask(y, T):
        target = sum(b << t for t, b in enumerate(pat))
        out = np.zeros_like(y, dtype=bool)
        for start in range(T - m + 1):
            out |= ((y >> start) & ((1 << m) - 1)) == target
        return out

    def automaton(T):
        # the standard Knuth-Morris-Pratt automaton, with the last state absorbing
        delta = []
        for s in range(m):
            row = []
            for b in (0, 1):
                seq = pat[:s] + [b]
                nxt = 0
                for length in range(min(m, len(seq)), 0, -1):
                    if seq[-length:] == pat[:length]:
                        nxt = length
                        break
                row.append(nxt)
            delta.append(tuple(row))
        delta.append((m, m))
        return Automaton(m + 1, tuple(delta), frozenset({m}))

    return Predicate(f"contains {pattern}", mask, automaton)


def odd_clicks() -> Predicate:
    """An odd number of clicks. The sign flip is one Z on every light: no two-qubit gates at all."""

    def oracle(qc, lights, T):
        for q in lights:
            qc.z(q)

    return Predicate(
        "odd clicks",
        lambda y, T: (popcount(y, T) % 2) == 1,
        lambda T: Automaton(2, ((0, 1), (1, 0)), frozenset({1})),
        oracle,
    )


# ---------------------------------------------------------------------------- the recurrent oracle


def counter_bits(T: int) -> int:
    """Qubits needed to count up to T clicks without wrapping: the counter must be reversible, so it cannot saturate."""
    return int(np.ceil(np.log2(T + 1)))


def _increment(qc: QuantumCircuit, control, counter: list) -> None:
    """If control is 1, add 1 to the counter (a ripple of multi-controlled X, top bit first)."""
    for j in range(len(counter) - 1, -1, -1):
        qc.mcx([control] + list(counter[:j]), counter[j])


def recurrent_counter_oracle(n_qubits: int, lights: list, c: int) -> QuantumCircuit:
    """'At least c clicks' as a reversible state machine that reads the click register one light at a time.

    It adds counter_bits(T) qubits after the n_qubits given. For each light it applies the same small step: add the
    click to a running count. Then it flips the sign of counts >= c, and runs the steps backwards to clean up. This is
    a coherent QRSM in the role of the oracle: no reset is allowed here, and none is needed, since a reader that
    never forgets is exactly what uncomputing requires.

    Its size grows like T log T. The lookup-table oracle's grows like 2**T.
    """
    T = len(lights)
    b = counter_bits(T)
    count = QuantumRegister(b, "count")
    qc = QuantumCircuit(n_qubits, name="reader")
    qc.add_register(count)
    for q in lights:
        _increment(qc, qc.qubits[q] if isinstance(q, int) else q, list(count))
    qc.append(DiagonalGate([-1.0 if v >= c else 1.0 for v in range(2 ** b)]), list(count))
    for q in reversed(lights):
        control = qc.qubits[q] if isinstance(q, int) else q
        for j in range(b):
            qc.mcx([control] + list(count[:j]), count[j])
    return qc
