"""Grover inside the recurrent loop: amplify a rare event, then keep running the machine.

The research note's experiment C asks to insert retrieval at selected timesteps. Here that means:

    run t0 steps  ->  amplify "a click at step t0"  ->  run tau more steps on fresh lights  ->  measure

Every shot that kept its click at step t0 is one sample of what the machine does AFTER that rare event. The bit at step
t0 is measured, so a shot that failed amplification is simply thrown away: post-selection on a bit you can see.

That query is physical. P(click at t0 + tau | click at t0), divided by the plain click rate, is the correlation g2(tau)
that optics labs measure. A two-level emitter cannot click twice at once, and with no hidden defect a click wipes the
machine clean, so the clicks after a click repeat the start of the run. A hidden defect remembers across the click. So
this one curve is a fingerprint of hidden memory.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from .amplify import hardware_amplified
from .fastsim import reflection_qubits
from .model import QRSM
from .predicates import click_at


def loop_circuit(model: QRSM, t0: int, tau: int, r: int, reflection: str = "memory+last-1",
                 steer: float | None = None) -> QuantumCircuit:
    """The whole query as one circuit. Qubits: memory, t0 lights, any ancillas, then tau fresh lights.

    `steer` replaces the emission strength of step t0 only. The steps after it are the machine's own.
    """
    n = model.n_memory
    A = model.purified(t0, gammas=None if steer is None else [None] * (t0 - 1) + [steer])
    oracle = click_at(t0).oracle(n + t0, list(range(n, n + t0)))
    body = hardware_amplified(A, oracle, r, reflect_on=reflection_qubits(model, t0, reflection))
    qc = QuantumCircuit(body.num_qubits + tau, name=f"loop(t0={t0},tau={tau},r={r},{reflection})")
    qc.compose(body, qubits=list(range(body.num_qubits)), inplace=True)
    emitter = qc.qubits[0]
    defects = qc.qubits[1:n]
    for j in range(tau):
        model.add_step(qc, emitter, defects, qc.qubits[body.num_qubits + j])
    return qc


def exact_after_click(model: QRSM, t0: int, tau: int) -> dict:
    """The exact answers from the filter: click rates, conditional click rates, and g2, for tau = 1 .. tau."""
    T = t0 + tau
    probs = model.history_probabilities(T)
    y = np.arange(2 ** T)
    at = lambda t: ((y >> (t - 1)) & 1) == 1  # noqa: E731
    p_click = float(probs[at(t0)].sum())
    plain = np.array([probs[at(t0 + j)].sum() for j in range(1, tau + 1)])
    conditional = np.array([probs[at(t0) & at(t0 + j)].sum() / p_click for j in range(1, tau + 1)])
    return {"p_click": p_click, "plain": plain, "conditional": conditional, "g2": conditional / plain}


def read_after_click(counts: dict, n_light_offset: int, t0: int, offset_new: int, tau: int) -> dict:
    """From raw counts, the shots with a click at t0 and the click rate at each later step among them.

    `n_light_offset` is the bit of light 1, and `offset_new` the bit of the first fresh light. Counts keys are bitstrings
    with qubit 0 last.
    """
    kept = 0
    clicks = np.zeros(tau)
    total = 0
    for bits, c in counts.items():
        v = int(bits.replace(" ", ""), 2)
        total += c
        if (v >> (n_light_offset + t0 - 1)) & 1:
            kept += c
            for j in range(tau):
                clicks[j] += c * ((v >> (offset_new + j)) & 1)
    return {"shots": total, "kept": kept, "conditional": clicks / max(kept, 1)}
