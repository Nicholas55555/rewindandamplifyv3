"""The classical baselines. They are strong on purpose: a quantum method has to be judged against the best we can do.

    rejection sampling      run the machine, throw away runs that do not match. The only general method that stays
                            polynomial in the number of hidden qubits. Costs 1/p runs per accepted sample.

    the backward sampler    an exact classical answer. It needs no rejection at all, and for small hidden memories it
                            beats everything else here by orders of magnitude. Its cost grows as 8**n in the hidden
                            qubits n, which is the only reason a quantum method could ever matter.

The backward sampler uses an operator-valued message. For a predicate read by an automaton, define for each time t and
automaton state s the matrix

    B[t][s] = sum over futures from t that the automaton accepts of  K_future^dagger K_future

Then P(accepted, from memory psi, at (t, s)) = <psi| B[t][s] |psi>, and sampling forward with those weights gives exact
conditional samples: the quantum version of forward-filtering backward-sampling for a hidden Markov model.
"""

from __future__ import annotations

import numpy as np

from .model import QRSM
from .predicates import Automaton


def conditional_distribution(probs: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """P(y | y is marked) as a full-length array."""
    out = np.where(mask, probs, 0.0)
    return out / out.sum()


def total_variation(p: np.ndarray, q: np.ndarray) -> float:
    return 0.5 * float(np.abs(np.asarray(p) - np.asarray(q)).sum())


class BackwardSampler:
    """Exact conditional sampling from a QRSM, with no rejection. Cost: T * states * 8**n to build, T * 4**n to sample."""

    def __init__(self, model: QRSM, automaton: Automaton, T: int):
        self.model, self.automaton, self.T = model, automaton, T
        self.K = model.kraus()
        dim = 2 ** model.n_memory
        S = automaton.n_states
        B = np.zeros((T + 1, S, dim, dim), dtype=complex)
        for s in automaton.accept:
            B[T, s] = np.eye(dim)
        for t in range(T - 1, -1, -1):
            for s in range(S):
                for y in (0, 1):
                    B[t, s] += self.K[y].conj().T @ B[t + 1, automaton.delta[s][y]] @ self.K[y]
        self.B = B
        psi0 = np.zeros(dim, dtype=complex)
        psi0[0] = 1.0
        self.psi0 = psi0

    def probability(self) -> float:
        """P(the predicate holds), exactly, with no enumeration of histories."""
        return float(np.real(self.psi0.conj() @ self.B[0, self.automaton.start] @ self.psi0))

    def sample(self, rng: np.random.Generator) -> tuple[int, np.ndarray]:
        """One exact conditional sample: a history integer, and the normalised memory state it leaves."""
        psi, s, y_out = self.psi0, self.automaton.start, 0
        for t in range(self.T):
            weights = []
            nexts = []
            for y in (0, 1):
                phi = self.K[y] @ psi
                s2 = self.automaton.delta[s][y]
                weights.append(float(np.real(phi.conj() @ self.B[t + 1, s2] @ phi)))
                nexts.append((phi, s2))
            w0, w1 = weights
            y = int(rng.random() * (w0 + w1) >= w0)
            psi, s = nexts[y]
            psi = psi / np.linalg.norm(psi)
            y_out |= y << t
        return y_out, psi


def expected_memory_population(branches: np.ndarray, mask: np.ndarray, n_memory: int) -> np.ndarray:
    """The chance each hidden qubit is excited at the end, given the predicate: exact retrodiction by brute force."""
    weights = np.abs(branches[mask]) ** 2  # (marked histories, memory basis states)
    total = weights.sum()
    basis = np.arange(2 ** n_memory)
    return np.array([weights[:, ((basis >> q) & 1) == 1].sum() / total for q in range(n_memory)])
