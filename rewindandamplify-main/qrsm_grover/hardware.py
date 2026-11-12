"""Everything needed to take these circuits to a real device.

The pipeline is the same for a real IBM backend and for a local fake one, so a dry run on a device snapshot exercises
exactly the code path of the real job. Nothing here reads your API key: QiskitRuntimeService() finds the account you
saved yourself with tools/save_ibm_account.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager

from .amplify import hardware_amplified, steered_gamma
from .fastsim import reflection_qubits
from .model import QRSM
from .predicates import Predicate, any_click, click_at
from .queries import loop_circuit
from .search import catalog_circuit, demo_catalog

ONE = QRSM()
NONE = QRSM(phi=(), zeta=())


@dataclass
class Experiment:
    """One circuit in the job, and what it means."""

    name: str
    circuit: QuantumCircuit
    meta: dict = field(default_factory=dict)


def measured(body: QuantumCircuit) -> QuantumCircuit:
    qc = QuantumCircuit(body.num_qubits, name=body.name)
    qc.compose(body, inplace=True)
    qc.measure_all()
    return qc


def history_experiment(tag: str, model: QRSM, T: int, pred: Predicate, kind: str, r: int,
                       steer: float | None = None) -> Experiment:
    n = model.n_memory
    oracle = pred.oracle(n + T, list(range(n, n + T)))
    A = model.purified(T, gammas=None if steer is None else [None] * (T - 1) + [steer])
    body = hardware_amplified(A, oracle, r, reflect_on=reflection_qubits(model, T, kind))
    label = f"{tag}-{'steered-' if steer is not None else ''}{kind}-r{r}"
    return Experiment(label, measured(body), {"kind": "history", "group": tag, "k": model.k, "T": T, "question": pred.name,
                                              "reflection": kind, "r": r, "steer": steer})


def echo_experiment(model: QRSM, T: int, repeats: int) -> Experiment:
    """Run the machine forwards and backwards. Perfect hardware returns to all zeros: a direct measure of its noise."""
    A = model.purified(T)
    qc = QuantumCircuit(A.num_qubits)
    for _ in range(repeats):
        qc.compose(A, inplace=True)
        qc.barrier()  # or the transpiler rightly cancels A and its inverse, and nothing is measured
        qc.compose(A.inverse(), inplace=True)
        qc.barrier()
    return Experiment(f"echo-T{T}-x{repeats}", measured(qc), {"kind": "echo", "k": model.k, "T": T, "repeats": repeats})


def steer_for(model: QRSM, T: int) -> float:
    """The emission strength for step T that makes one iteration enough, from the exact click rate."""
    p = float(model.history_probabilities(T)[click_at(T).mask(T)].sum())
    return steered_gamma(p, model.gamma)


def suite(quick: bool = False) -> list[Experiment]:
    """The whole hardware experiment, from the cheapest rung to the hardest."""
    local = "memory+last-1"
    request = "what do we pay staff per team"
    out: list[Experiment] = []
    rs = (0, 1, 2, 3)

    # 1. the hero: a click at step 3 with one hidden defect. Textbook Grover against the resilient builds.
    s3 = steer_for(ONE, 3)
    out.append(history_experiment("click3", ONE, 3, click_at(3), "full", 0))
    out.append(history_experiment("click3", ONE, 3, click_at(3), "full", 0, s3))
    out.append(history_experiment("click3", ONE, 3, click_at(3), local, 1, s3))
    out.append(history_experiment("click3", ONE, 3, click_at(3), "full", 1, s3))
    for kind in ("full", local):
        for r in rs[1:]:
            out.append(history_experiment("click3", ONE, 3, click_at(3), kind, r))
    if quick:
        return out + [Experiment("catalog-r1", measured(catalog_circuit(demo_catalog(8), request, 1)),
                                 {"kind": "catalog", "N": 8, "query": request, "r": 1})]
    for r in rs[1:]:
        out.append(history_experiment("click3", ONE, 3, click_at(3), "memory", r))

    # 2. the coherence check: with no defect the hit rate peaks at r = 1 and then falls, which noise alone cannot do
    for r in rs:
        out.append(history_experiment("any3-nodefect", NONE, 3, any_click(), "full", r))

    # 3. any click, one defect: no steering is possible here, so this is plain Grover against the memory reflection
    for r in rs:
        out.append(history_experiment("any3", ONE, 3, any_click(), "full", r))
    for r in rs[1:]:
        out.append(history_experiment("any3", ONE, 3, any_click(), "memory", r))

    # 4. a longer record
    s5 = steer_for(ONE, 5)
    out.append(history_experiment("click5", ONE, 5, click_at(5), "full", 0))
    out.append(history_experiment("click5", ONE, 5, click_at(5), "full", 1))
    out.append(history_experiment("click5", ONE, 5, click_at(5), local, 3))
    out.append(history_experiment("click5", ONE, 5, click_at(5), local, 1, s5))
    out.append(history_experiment("click5", ONE, 5, click_at(5), "full", 1, s5))

    # 5. Grover inside the loop: what happens after the click, with and without a hidden defect
    for tag, model in (("loop-defect", ONE), ("loop-nodefect", NONE)):
        steer = steer_for(model, 3)
        for r, kind, st in ((0, "full", None), (1, local, steer)):
            body = loop_circuit(model, 3, 3, r, kind, st)
            out.append(Experiment(f"{tag}-r{r}", measured(body), {"kind": "loop", "group": tag, "k": model.k, "t0": 3, "tau": 3,
                                                                  "reflection": kind, "r": r, "steer": st,
                                                                  "width": body.num_qubits}))

    # 6. Timofey's keyword search, on 8 catalogue entries
    for r in (0, 1, 2):
        out.append(Experiment(f"catalog-r{r}", measured(catalog_circuit(demo_catalog(8), request, r)),
                              {"kind": "catalog", "N": 8, "query": request, "r": r}))

    # 7. noise calibration: the echo
    for T, repeats in ((3, 1), (3, 2), (5, 1)):
        out.append(echo_experiment(ONE, T, repeats))
    return out


# ---------------------------------------------------------------------------- compiling


def estimated_success(isa: QuantumCircuit, backend) -> float:
    """The product of (1 - error) over every gate: the transpiler's output scored with the device's own numbers."""
    target = backend.target
    index = {q: i for i, q in enumerate(isa.qubits)}
    log_f = 0.0
    for inst in isa.data:
        name = inst.operation.name
        if name in ("barrier", "delay") or name not in target.operation_names:
            continue
        props = target[name].get(tuple(index[q] for q in inst.qubits))
        if props is not None and props.error is not None and props.error < 1:
            log_f += float(np.log1p(-props.error))
    return float(np.exp(log_f))


def without_qubits(target, avoid: set):
    """A copy of a device's target with some qubits taken out, so that the compiler can't use them."""
    from qiskit.transpiler import Target

    reduced = Target(num_qubits=target.num_qubits, dt=target.dt, qubit_properties=target.qubit_properties)
    for name in target.operation_names:
        operation, properties = target.operation_from_name(name), target[name]
        if None in properties:  # a global instruction, such as control flow
            reduced.add_instruction(operation, name=name)
        else:
            reduced.add_instruction(operation, {q: p for q, p in properties.items() if not avoid & set(q)}, name=name)
    return reduced


def compile_best(qc: QuantumCircuit, backend, seeds: int = 8, initial_layout=None, avoid=()) -> tuple[QuantumCircuit, dict]:
    """Transpile at the highest level with several seeds, and keep the layout the device's own error rates favour.

    `avoid` names physical qubits to stay off, for when a device's reported numbers can't be trusted on them.
    """
    device = {"target": without_qubits(backend.target, set(avoid))} if avoid else {"backend": backend}
    best = None
    for seed in range(seeds):
        pm = generate_preset_pass_manager(optimization_level=3, seed_transpiler=seed, initial_layout=initial_layout, **device)
        isa = pm.run(qc)
        score = estimated_success(isa, backend)
        if best is None or score > best[0]:
            best = (score, isa)
    score, isa = best
    ops = isa.count_ops()
    two_qubit = sum(n for name, n in ops.items() if name in ("cz", "ecr", "cx", "rzz"))
    layout = isa.layout.final_index_layout(filter_ancillas=True) if isa.layout else list(range(qc.num_qubits))
    return isa, {"two_qubit_gates": int(two_qubit), "depth": int(isa.depth()), "estimated_success": score,
                 "physical_qubits": [int(q) for q in layout]}


def readout_calibration(physical_qubits: list, num_device_qubits: int) -> list[QuantumCircuit]:
    """All-zeros and all-ones on these physical qubits, for correcting readout afterwards."""
    circuits = []
    for flip in (False, True):
        qc = QuantumCircuit(num_device_qubits, len(physical_qubits), name=f"readout-{int(flip)}")
        if flip:
            qc.x(physical_qubits)
        qc.measure(physical_qubits, list(range(len(physical_qubits))))
        circuits.append(qc)
    return circuits


def readout_correct(probabilities: np.ndarray, flip_rates: list) -> np.ndarray:
    """Undo independent readout errors on a distribution over n bits, then clip back to a true distribution.

    `flip_rates[q]` is (P(read 1 | was 0), P(read 0 | was 1)) for bit q.
    """
    n = len(flip_rates)
    p = probabilities.reshape((2,) * n)
    for q, (p01, p10) in enumerate(flip_rates):
        M = np.array([[1 - p01, p10], [p01, 1 - p10]])
        axis = n - 1 - q  # bit q is axis n - 1 - q in a C-ordered reshape
        p = np.moveaxis(np.tensordot(np.linalg.inv(M), p, axes=(1, axis)), 0, axis)
    flat = np.clip(p.reshape(-1), 0, None)
    return flat / flat.sum()
