"""The QRSM: a recurrent machine whose hidden memory is quantum, and its reversible (purified) form.

The machine is the one from our hidden-defect project: a driven emitter, k hidden defects behind it, and a light qubit.
Each step drives the emitter, turns the defects, lets the emitter and defects swap energy, and lets the emitter emit
into the light. The light is the only thing anybody sees: click, or no click.

There are two ways to run those same gates:

    dynamic     one light qubit, measured and reset every step. Cheap in qubits, but irreversible: a reset throws
                information away, so the circuit has no inverse and Grover cannot use it.

    purified    a fresh light qubit for every step, nothing measured until the end. This is the deferred-measurement
                principle: the click statistics are identical, and the whole T-step run is now ONE unitary A.

The purified state holds every possible click history at once, each with amplitude sqrt(P(history)):

    A|0> = sum over histories y of  |m_y> |y>         where   <m_y|m_y> = P(y)

That is the object Grover works on. Qubit order is (emitter, defects..., light_1 ... light_T), so in a statevector the
memory is the low bits and the history is the high bits. History integers use bit t for the click at step t + 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Operator


def exchange(qc: QuantumCircuit, angle: float, src, dst) -> None:
    """A real Givens rotation between two qubits: they swap one excitation by `angle`; |00> and |11> are left alone."""
    qc.cx(dst, src)
    qc.cry(2 * angle, src, dst)
    qc.cx(dst, src)


def emission(qc: QuantumCircuit, alpha: float, emitter, light) -> None:
    """The same rotation from the emitter into a light that is known to start in |0>, so its first CNOT is dropped."""
    qc.cry(2 * alpha, emitter, light)
    qc.cx(light, emitter)


@dataclass(frozen=True)
class QRSM:
    """An emitter with len(phi) hidden defects. The defaults are the numbers from the hidden-defect project."""

    theta: float = 0.6  # the drive on the emitter, per step
    gamma: float = 0.2  # the chance an excited emitter emits, per step
    phi: tuple = (0.45,)  # each defect's coupling to the emitter
    zeta: tuple = (0.3,)  # each defect's own rotation per step (its detuning)

    @property
    def k(self) -> int:
        return len(self.phi)

    @property
    def n_memory(self) -> int:
        return 1 + self.k

    @property
    def alpha(self) -> float:
        return float(np.arcsin(np.sqrt(self.gamma)))

    def n_qubits(self, T: int) -> int:
        return self.n_memory + T

    # ------------------------------------------------------------------ circuits

    def add_step(self, qc: QuantumCircuit, emitter, defects: Sequence, light, theta: float | None = None,
                 gamma: float | None = None) -> None:
        """One step's gates, in the hidden-defect project's order: drive, detune, exchange, emit.

        `gamma` overrides this step's emission strength, which is how a steered machine is built.
        """
        qc.ry(self.theta if theta is None else theta, emitter)
        for d, z in zip(defects, self.zeta):
            qc.rz(z, d)
        for d, f in zip(defects, self.phi):
            exchange(qc, f, src=d, dst=emitter)
        emission(qc, self.alpha if gamma is None else float(np.arcsin(np.sqrt(gamma))), emitter, light)

    def purified(self, T: int, thetas: Sequence[float] | None = None,
                 gammas: Sequence[float | None] | None = None) -> QuantumCircuit:
        """The reversible machine A: T steps, a fresh light for each, no measurement and no reset.

        `thetas` and `gammas` optionally give each step its own drive and emission strength. A step's entry of None
        keeps the machine's own value.
        """
        emitter = QuantumRegister(1, "emitter")
        regs = [emitter]
        defects = []
        if self.k:
            defects = QuantumRegister(self.k, "defect")
            regs.append(defects)
        lights = QuantumRegister(T, "light")
        qc = QuantumCircuit(*regs, lights, name=f"A(T={T})")
        for t in range(T):
            self.add_step(qc, emitter[0], list(defects), lights[t], None if thetas is None else thetas[t],
                          None if gammas is None else gammas[t])
        return qc

    def dynamic(self, T: int) -> QuantumCircuit:
        """The irreversible machine: one light, measured mid-circuit into its click bit and reset, every step."""
        emitter = QuantumRegister(1, "emitter")
        regs = [emitter]
        defects = []
        if self.k:
            defects = QuantumRegister(self.k, "defect")
            regs.append(defects)
        light = QuantumRegister(1, "light")
        click = ClassicalRegister(T, "click")
        qc = QuantumCircuit(*regs, light, click, name=f"dynamic(T={T})")
        for t in range(T):
            self.add_step(qc, emitter[0], list(defects), light[0])
            qc.measure(light[0], click[t])
            qc.reset(light[0])
        return qc

    # ------------------------------------------------------------------ the exact model

    def kraus(self, theta: float | None = None, gamma: float | None = None) -> tuple[np.ndarray, np.ndarray]:
        """K_0 and K_1: what one step does to the memory, given no click or a click. K_y = <y| V |0>."""
        emitter = QuantumRegister(1, "emitter")
        regs = [emitter]
        defects = []
        if self.k:
            defects = QuantumRegister(self.k, "defect")
            regs.append(defects)
        light = QuantumRegister(1, "light")
        qc = QuantumCircuit(*regs, light)
        self.add_step(qc, emitter[0], list(defects), light[0], theta, gamma)
        dim = 2 ** self.n_memory
        V = Operator(qc).data.reshape(2, dim, 2, dim)  # [light out, memory out, light in, memory in]
        return V[0, :, 0, :], V[1, :, 0, :]

    def branches(self, T: int, thetas: Sequence[float] | None = None,
                 gammas: Sequence[float | None] | None = None) -> np.ndarray:
        """Every history's unnormalised memory vector |m_y>, as an array of shape (2**T, 2**n_memory).

        Row y is K_{y_T} ... K_{y_1} |0>, so |row|^2 = P(y). Costs 2**T: this is the brute-force ground truth, used
        for checking, not the method.
        """
        dim = 2 ** self.n_memory
        psi = np.zeros((1, dim), dtype=complex)
        psi[0, 0] = 1.0
        for t in range(T):
            K0, K1 = self.kraus(None if thetas is None else thetas[t], None if gammas is None else gammas[t])
            psi = np.concatenate([psi @ K0.T, psi @ K1.T], axis=0)  # a click at step t sets bit t
        return psi

    def history_probabilities(self, T: int, thetas: Sequence[float] | None = None,
                              gammas: Sequence[float | None] | None = None) -> np.ndarray:
        """P(y) for all 2**T histories."""
        return np.sum(np.abs(self.branches(T, thetas, gammas)) ** 2, axis=1)

    def record_probability(self, record: Sequence[int]) -> float:
        """P(one record) by the exact filter: 2**n_memory work per step. Works for 64-step records."""
        return float(np.exp(self.record_log_probability(record)))

    def record_log_probability(self, record: Sequence[int]) -> float:
        """log P(one record), renormalising as it goes so that long records do not underflow."""
        K = self.kraus()
        psi = np.zeros(2 ** self.n_memory, dtype=complex)
        psi[0] = 1.0
        log_p = 0.0
        for y in record:
            psi = K[int(y)] @ psi
            norm = np.linalg.norm(psi)
            if norm == 0.0:
                return -np.inf
            log_p += 2 * np.log(norm)
            psi = psi / norm
        return float(log_p)


def history_to_string(y: int, T: int) -> str:
    """A history integer as a string read in time order: the first character is step 1."""
    return "".join(str((y >> t) & 1) for t in range(T))


def string_to_history(s: str) -> int:
    """The inverse of history_to_string."""
    return sum(int(c) << t for t, c in enumerate(s))
