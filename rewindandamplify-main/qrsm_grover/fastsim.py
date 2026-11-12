"""A fast exact simulator of the purified QRSM, for runs too long to build as dense matrices.

It holds the state as an array of shape (2**T, 2**n_memory), lights in the high bits as in Qiskit, and applies each step
as one small tensor contraction. A and A^dagger then cost about T * 2**(n + T) operations, so hundreds of Grover
iterations at T = 18 take seconds. The tests check it against real Qiskit circuits.

It supports any reflection: `reflect_on` lists which qubits the zero reflection looks at, with qubit 0 the emitter, as
in the circuits. Looking at every qubit gives textbook amplitude amplification; looking at fewer gives a cheaper,
approximate reflection.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from .model import QRSM


def step_unitary(model: QRSM, gamma: float | None = None) -> np.ndarray:
    """The full step V on (memory, light) as a tensor [light out, memory out, light in, memory in]."""
    qc = QuantumCircuit(model.n_memory + 1)
    model.add_step(qc, qc.qubits[0], qc.qubits[1:model.n_memory], qc.qubits[-1], None, gamma)
    dim = 2 ** model.n_memory
    return Operator(qc).data.reshape(2, dim, 2, dim)


class FastPurified:
    """The purified machine as a matrix-free operator."""

    def __init__(self, model: QRSM, T: int, gammas: Sequence[float | None] | None = None):
        self.model, self.T = model, T
        self.n = model.n_memory
        self.dim = 2 ** self.n
        # rows (light out, memory out), columns (light in, memory in); one matrix per step, since a steered step differs
        self.Vs = [step_unitary(model, None if gammas is None else gammas[t]).reshape(2 * self.dim, 2 * self.dim)
                   for t in range(T)]
        self.size = self.dim * 2 ** T

    def zero_state(self) -> np.ndarray:
        psi = np.zeros(self.size, dtype=complex)
        psi[0] = 1.0
        return psi

    def _apply(self, state: np.ndarray, U: np.ndarray, t: int) -> np.ndarray:
        """Apply a two-register unitary to the memory and light t, leaving every other light alone."""
        # index = (lights above t) (light t) (lights below t) (memory)
        high = 2 ** (self.T - t - 1)
        low = 2 ** t
        view = state.reshape(high, 2, low, self.dim)
        view = view.transpose(0, 2, 1, 3).reshape(high * low, 2 * self.dim)
        view = view @ U.T
        view = view.reshape(high, low, 2, self.dim).transpose(0, 2, 1, 3)
        return np.ascontiguousarray(view).reshape(-1)

    def forward(self, state: np.ndarray, first_step: int = 0) -> np.ndarray:
        """Run the steps from first_step on (steps count from 0 here)."""
        for t in range(first_step, self.T):
            state = self._apply(state, self.Vs[t], t)
        return state

    def backward(self, state: np.ndarray, first_step: int = 0) -> np.ndarray:
        """Rewind back to just before first_step."""
        for t in range(self.T - 1, first_step - 1, -1):
            state = self._apply(state, self.Vs[t].conj().T, t)
        return state

    def zero_mask(self, reflect_on: Sequence[int] | None) -> np.ndarray:
        """Which basis states the zero reflection flips: those where every listed qubit is 0."""
        index = np.arange(self.size)
        qubits = range(self.n + self.T) if reflect_on is None else reflect_on
        mask = np.ones(self.size, dtype=bool)
        for q in qubits:
            mask &= ((index >> q) & 1) == 0
        return mask

    def amplify(self, marked_histories: np.ndarray, r_max: int, reflect_on: Sequence[int] | None = None,
                rewind: int | None = None):
        """The state after each iteration 0..r_max, yielded in turn: the same operator as the Qiskit circuit.

        `rewind` limits each iteration to rewinding only the last `rewind` steps, not the whole history.
        """
        marked = np.repeat(marked_histories, self.dim)
        zero = self.zero_mask(reflect_on)
        first = 0 if rewind is None else self.T - rewind
        state = self.forward(self.zero_state())
        yield 0, state
        for r in range(1, r_max + 1):
            state = np.where(marked, -state, state)
            state = self.backward(state, first)
            state[zero] *= -1
            state = -self.forward(state, first)
            yield r, state


def light_distribution(state: np.ndarray, T: int, dim: int) -> np.ndarray:
    """P(history) from a state."""
    return (np.abs(state) ** 2).reshape(2 ** T, dim).sum(axis=1)


def reflection_qubits(model: QRSM, T: int, kind: str) -> list[int]:
    """Named reflections: 'full' (every qubit), 'memory', 'emitter', 'lights', or 'memory+last-w' for a window."""
    n = model.n_memory
    lights = list(range(n, n + T))
    if kind == "full":
        return list(range(n + T))
    if kind == "memory":
        return list(range(n))
    if kind == "emitter":
        return [0]
    if kind == "lights":
        return lights
    if kind.startswith("memory+last-"):
        w = int(kind.split("-")[-1])
        return list(range(n)) + lights[T - w:]
    if kind.startswith("memory+first-"):
        w = int(kind.split("-")[-1])
        return list(range(n)) + lights[:w]
    raise ValueError(kind)
