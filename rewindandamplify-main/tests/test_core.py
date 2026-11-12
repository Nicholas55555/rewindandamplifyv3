"""The checks that the architecture is right. Every number here has a pass mark that follows from theory, so a failure
means a bug, not bad luck. Sampling tests use fixed seeds and generous bounds."""

from pathlib import Path

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import ZGate
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator

from qrsm_grover.amplify import (amplified, amplified_state, calls_per_hit, hardware_amplified, iterations_to_peak,
                                 mcz_with_ancillas, steered_gamma, success_probability)
from qrsm_grover.classical import (BackwardSampler, conditional_distribution, expected_memory_population,
                                   total_variation)
from qrsm_grover.fastsim import FastPurified, reflection_qubits, step_unitary
from qrsm_grover.model import QRSM, history_to_string, string_to_history
from qrsm_grover.queries import exact_after_click, loop_circuit
from qrsm_grover.predicates import (any_click, at_least, click_at, contains, counter_bits, exact_record, odd_clicks,
                                    recurrent_counter_oracle)

DATA = Path(__file__).parent / "data"
M1 = QRSM()
M0 = QRSM(phi=(), zeta=())
ALL_PREDICATES = [any_click(), exact_record("0010"), click_at(3), at_least(2), contains("11"), odd_clicks()]


def light_marginal(state: np.ndarray, model: QRSM, T: int) -> np.ndarray:
    return (np.abs(state) ** 2).reshape(2 ** T, 2 ** model.n_memory).sum(axis=1)


# ------------------------------------------------------------------ the purified machine is the same machine


@pytest.mark.parametrize("model", [M0, M1], ids=["no defect", "one defect"])
def test_step_equals_the_checked_step_from_the_defect_project(model):
    """The step's matrix equals the one the hidden-defect project verified against its exact model."""
    qc = QuantumCircuit(model.n_memory + 1)
    model.add_step(qc, qc.qubits[0], qc.qubits[1:model.n_memory], qc.qubits[-1])
    saved = np.load(DATA / f"step_operator_k{model.k}.npy")
    assert np.abs(Operator(qc).reverse_qargs().data - saved).max() < 1e-12


@pytest.mark.parametrize("model", [M0, M1], ids=["no defect", "one defect"])
def test_kraus_operators_are_complete(model):
    K0, K1 = model.kraus()
    assert np.abs(K0.conj().T @ K0 + K1.conj().T @ K1 - np.eye(2 ** model.n_memory)).max() < 1e-12


@pytest.mark.parametrize("model", [M0, M1], ids=["no defect", "one defect"])
@pytest.mark.parametrize("T", [1, 2, 3, 5, 7])
def test_purified_state_holds_every_history_with_the_right_amplitude(model, T):
    """A|0> = sum_y |m_y>|y>: not only the probabilities, the amplitudes themselves match the Kraus branches."""
    state = Statevector(model.purified(T)).data.reshape(2 ** T, 2 ** model.n_memory)
    assert np.abs(state - model.branches(T)).max() < 1e-12


def test_dynamic_and_purified_circuits_click_alike():
    """Measure-and-reset on Aer against the purified probabilities: the deferred-measurement principle, sampled."""
    T, shots = 4, 200_000
    counts = AerSimulator().run(M1.dynamic(T), shots=shots, seed_simulator=11).result().get_counts()
    probs = M1.history_probabilities(T)
    observed = np.zeros(2 ** T)
    for bits, n in counts.items():
        observed[int(bits, 2)] = n / shots  # Qiskit prints clbit 0 last, and clbit t is the click at step t + 1
    assert total_variation(observed, probs) < 0.01


def test_record_probability_matches_enumeration():
    T = 6
    probs = M1.history_probabilities(T)
    for y in (0, 5, 37, 63):
        assert M1.record_probability([(y >> t) & 1 for t in range(T)]) == pytest.approx(probs[y], rel=1e-10)


def test_history_string_round_trip():
    for y in range(64):
        assert string_to_history(history_to_string(y, 6)) == y
    assert history_to_string(1, 4) == "1000"


# ------------------------------------------------------------------ predicates: mask, automaton and oracle agree


@pytest.mark.parametrize("pred", ALL_PREDICATES, ids=lambda p: p.name)
def test_automaton_agrees_with_mask(pred):
    T = 4 if pred.name.startswith("record") else 6
    mask = pred.mask(T)
    auto = pred.automaton(T)
    for y in range(2 ** T):
        assert auto.run([(y >> t) & 1 for t in range(T)]) == mask[y]


@pytest.mark.parametrize("pred", ALL_PREDICATES, ids=lambda p: p.name)
def test_oracle_flips_exactly_the_marked_histories(pred):
    T, n = 4, 2
    oracle = pred.oracle(n + T, list(range(n, n + T)))
    U = Operator(oracle).data
    expected = np.repeat(np.where(pred.mask(T), -1.0, 1.0), 2 ** n)
    assert np.abs(U - np.diag(expected)).max() < 1e-9


@pytest.mark.parametrize("T,c", [(3, 1), (4, 2), (5, 2), (6, 3)])
def test_recurrent_reader_equals_the_lookup_table(T, c):
    """The reversible counter marks the same histories and leaves its counter clean."""
    n = 1
    nq = n + T
    oracle = recurrent_counter_oracle(nq, list(range(n, nq)), c)
    assert oracle.num_qubits == nq + counter_bits(T)
    mask = at_least(c).mask(T)
    U = Operator(oracle).data
    for y in range(2 ** T):
        index = y << n  # memory 0 and counter 0 (the counter is the highest bits)
        assert abs(U[index, index] - (-1 if mask[y] else 1)) < 1e-9, "wrong sign, or a dirty counter"


# ------------------------------------------------------------------ amplification: theory, exactly


@pytest.mark.parametrize("pred", ALL_PREDICATES, ids=lambda p: p.name)
@pytest.mark.parametrize("r", [0, 1, 2, 3])
def test_circuit_follows_the_grover_curve(pred, r):
    """P_r from the real Qiskit circuit equals sin^2((2r+1) theta): the note's curve, on the QRSM itself."""
    T, n = 4, M1.n_memory
    A = M1.purified(T)
    mask = pred.mask(T)
    p = M1.history_probabilities(T)[mask].sum()
    oracle = pred.oracle(n + T, list(range(n, n + T)))
    state = Statevector(amplified(A, oracle, r)).data
    assert light_marginal(state, M1, T)[mask].sum() == pytest.approx(success_probability(p, r), abs=1e-9)


@pytest.mark.parametrize("pred", ALL_PREDICATES, ids=lambda p: p.name)
@pytest.mark.parametrize("r", [1, 2])
def test_amplification_gives_exact_conditional_samples(pred, r):
    """Inside the marked set the distribution is exactly P(y | marked), hidden memory included."""
    T, n = 4, M1.n_memory
    A = M1.purified(T)
    mask = pred.mask(T)
    probs = M1.history_probabilities(T)
    state = Statevector(amplified(A, pred.oracle(n + T, list(range(n, n + T))), r)).data
    marginal = light_marginal(state, M1, T)
    assert total_variation(conditional_distribution(marginal, mask), conditional_distribution(probs, mask)) < 1e-9
    joint = (np.abs(state) ** 2).reshape(2 ** T, 2 ** n)
    joint_marked = joint[mask] / joint[mask].sum()
    exact = np.abs(M1.branches(T)[mask]) ** 2
    assert np.abs(joint_marked - exact / exact.sum()).max() < 1e-9


def test_fast_simulator_matches_the_circuit():
    T, n = 4, M1.n_memory
    pred = any_click()
    A = M1.purified(T)
    psi = Statevector(A).data
    marked = np.repeat(pred.mask(T), 2 ** n)
    for r in (1, 2, 3):
        fast = amplified_state(psi, marked, r)
        slow = Statevector(amplified(A, pred.oracle(n + T, list(range(n, n + T))), r)).data
        assert abs(abs(np.vdot(fast, slow)) - 1) < 1e-9


def test_reader_oracle_amplifies_like_the_lookup_table():
    """The full stack: a QRSM prepares the histories and a QRSM reader marks them."""
    T, c = 5, 2
    n = M0.n_memory
    A = M0.purified(T)
    probs = M0.history_probabilities(T)
    mask = at_least(c).mask(T)
    p = probs[mask].sum()
    reader = recurrent_counter_oracle(n + T, list(range(n, n + T)), c)
    b = counter_bits(T)
    data = list(range(n + T))
    wide = QuantumCircuit(n + T + b)
    wide.compose(A, qubits=data, inplace=True)
    Q = QuantumCircuit(n + T + b)
    Q.compose(reader, inplace=True)
    Q.compose(A.inverse(), qubits=data, inplace=True)
    Q.x(data)
    Q.append(ZGate().control(n + T - 1), data)
    Q.x(data)
    Q.compose(A, qubits=data, inplace=True)
    for r in (1, 2):
        qc = wide.copy()
        for _ in range(r):
            qc.compose(Q, inplace=True)
        out = (np.abs(Statevector(qc).data) ** 2).reshape(2 ** b, 2 ** T, 2 ** n)
        assert out[1:].sum() < 1e-9, "the counter must come back clean"
        assert out[0].sum(axis=1)[mask].sum() == pytest.approx(success_probability(p, r), abs=1e-9)


def test_the_note_example_and_counts():
    """The research note's worked example: 10% becomes about 99.9% in two iterations, and its table of counts holds."""
    assert success_probability(0.10, 0) == pytest.approx(0.10)
    assert success_probability(0.10, 2) == pytest.approx(0.9986, abs=5e-4)
    for N, r in ((16, 3), (64, 6), (256, 12), (1024, 25)):
        assert iterations_to_peak(1 / N) == r


def test_calls_per_hit_counts_both_directions():
    assert calls_per_hit(0.25, 1) == pytest.approx(3.0)  # one iteration, a certain hit, three calls
    assert calls_per_hit(0.25, 0) == pytest.approx(4.0)


# ------------------------------------------------------------------ the hardware build


@pytest.mark.parametrize("m,anc", [(4, 1), (5, 2), (6, 3)])
def test_ancilla_mcz_is_a_true_mcz_on_clean_ancillas(m, anc):
    qc = QuantumCircuit(m + anc)
    mcz_with_ancillas(qc, list(range(m)), list(range(m, m + anc)))
    U = Operator(qc).data
    for x in range(2 ** m):
        assert abs(U[x, x] - (-1 if x == 2 ** m - 1 else 1)) < 1e-9
    assert np.abs(U[2 ** m:, :2 ** m]).max() < 1e-9, "the ancillas must come back clean"


@pytest.mark.parametrize("r", [1, 2])
def test_hardware_build_equals_the_library_build(r):
    T, n = 3, M1.n_memory
    A = M1.purified(T)
    oracle = any_click().oracle(n + T, list(range(n, n + T)))
    state_hw = Statevector(hardware_amplified(A, oracle, r, n + T - 3)).data
    state_lib = Statevector(amplified(A, oracle, r)).data
    assert abs(abs(np.vdot(state_hw[:2 ** (n + T)], state_lib)) - 1) < 1e-9
    assert np.linalg.norm(state_hw[2 ** (n + T):]) < 1e-9


# ------------------------------------------------------------------ the classical baseline


@pytest.mark.parametrize("pred", [any_click(), at_least(2), contains("11"), exact_record("0100"), click_at(2)],
                         ids=lambda p: p.name)
def test_backward_sampler_probability_is_exact(pred):
    T = 4
    probs = M1.history_probabilities(T)
    sampler = BackwardSampler(M1, pred.automaton(T), T)
    assert sampler.probability() == pytest.approx(probs[pred.mask(T)].sum(), rel=1e-9)


def test_backward_sampler_draws_the_conditional_distribution():
    T, n_samples = 5, 40_000
    pred = at_least(2)
    sampler = BackwardSampler(M1, pred.automaton(T), T)
    rng = np.random.default_rng(3)
    counts = np.bincount([sampler.sample(rng)[0] for _ in range(n_samples)], minlength=2 ** T)
    exact = conditional_distribution(M1.history_probabilities(T), pred.mask(T))
    assert counts[~pred.mask(T)].sum() == 0
    assert total_variation(counts / n_samples, exact) < 0.02


def test_retrodiction_helper_is_a_probability():
    T = 3
    pop = expected_memory_population(M1.branches(T), any_click().mask(T), M1.n_memory)
    assert pop.shape == (2,) and np.all((pop >= 0) & (pop <= 1))


# ------------------------------------------------------------------ the fast simulator and the memory reflection


@pytest.mark.parametrize("kind", ["full", "memory", "emitter", "lights", "memory+last-1"])
def test_fast_simulator_equals_qiskit_for_every_reflection(kind):
    """The matrix-free simulator and Qiskit's grover_operator agree, whatever the reflection looks at."""
    T, n = 4, M1.n_memory
    pred = click_at(4)
    A = M1.purified(T)
    oracle = pred.oracle(n + T, list(range(n, n + T)))
    fast = FastPurified(M1, T)
    rq = reflection_qubits(M1, T, kind)
    states = dict(fast.amplify(pred.mask(T), 3, rq))
    for r in (1, 2, 3):
        assert abs(abs(np.vdot(Statevector(amplified(A, oracle, r, rq)).data, states[r])) - 1) < 1e-9


@pytest.mark.parametrize("pred", [any_click(), click_at(4), at_least(2), odd_clicks()], ids=lambda p: p.name)
def test_the_leak_formula_for_one_iteration(pred):
    """Q'|psi> = (1 - 4p)|psi> + 2|g> - 4A|l>, exactly, where |l> is what the reflection cannot see."""
    T = 4
    fast = FastPurified(M1, T)
    mask = pred.mask(T)
    psi = fast.forward(fast.zero_state())
    marked = np.repeat(mask, fast.dim)
    g = np.where(marked, psi, 0)
    p = float(np.vdot(g, g).real)
    rewound = fast.backward(g)
    seen = fast.zero_mask(reflection_qubits(M1, T, "memory"))
    leak = np.where(seen, rewound, 0)
    leak[0] -= p  # the part along |0> is what the full reflection handles
    predicted = (1 - 4 * p) * psi + 2 * g - 4 * fast.forward(leak)
    states = dict(fast.amplify(mask, 1, reflection_qubits(M1, T, "memory")))
    assert np.abs(predicted - states[1]).max() < 1e-10


def test_full_reflection_has_no_leak():
    T = 3
    fast = FastPurified(M1, T)
    mask = any_click().mask(T)
    psi = fast.forward(fast.zero_state())
    g = np.where(np.repeat(mask, fast.dim), psi, 0)
    rewound = fast.backward(g)
    seen = fast.zero_mask(None)
    assert seen.sum() == 1 and abs(rewound[0] - np.vdot(g, g)) < 1e-12


@pytest.mark.parametrize("r", [1, 2])
def test_hardware_memory_reflection_equals_the_library_one(r):
    T, n = 3, M1.n_memory
    A = M1.purified(T)
    oracle = click_at(3).oracle(n + T, list(range(n, n + T)))
    rq = reflection_qubits(M1, T, "memory")
    hw = hardware_amplified(A, oracle, r, reflect_on=rq)
    assert hw.num_qubits == n + T, "a two-qubit reflection needs no ancillas"
    assert abs(abs(np.vdot(Statevector(hw).data, Statevector(amplified(A, oracle, r, rq)).data)) - 1) < 1e-9


# ------------------------------------------------------------------ steering


@pytest.mark.parametrize("gamma2", [0.05, 0.5, 1.0])
def test_a_click_operator_only_changes_by_a_constant(gamma2):
    """The whole basis of steering: K_1 at any emission strength is a multiple of K_1 at the machine's own."""
    K1 = M1.kraus()[1]
    K1b = M1.kraus(gamma=gamma2)[1]
    assert np.abs(K1b - np.sqrt(gamma2 / M1.gamma) * K1).max() < 1e-12


@pytest.mark.parametrize("T", [3, 5, 6])
def test_steering_keeps_marked_histories_exact(T):
    """Steering step T: every history that clicks there keeps its relative weight and its exact hidden state."""
    mask = click_at(T).mask(T)
    p = M1.history_probabilities(T)[mask].sum()
    steer = steered_gamma(p, M1.gamma)
    before = M1.branches(T)[mask]
    after = M1.branches(T, gammas=[None] * (T - 1) + [steer])[mask]
    assert np.abs(after - np.sqrt(steer / M1.gamma) * before).max() < 1e-12


@pytest.mark.parametrize("T", [5, 6, 8])
def test_steered_single_iteration_is_certain_and_exact(T):
    """Tuned to p' = 1/4, one iteration gives a hit rate of 1, with the exact conditional distribution."""
    mask = click_at(T).mask(T)
    probs = M1.history_probabilities(T)
    p = probs[mask].sum()
    steer = steered_gamma(p, M1.gamma)
    assert steer < 1, "these lengths can reach p' = 1/4"
    fast = FastPurified(M1, T, [None] * (T - 1) + [steer])
    states = dict(fast.amplify(mask, 1, None))
    d = (np.abs(states[1]) ** 2).reshape(2 ** T, fast.dim).sum(axis=1)
    assert d[mask].sum() == pytest.approx(1.0, abs=1e-9)
    assert total_variation(conditional_distribution(d, mask), conditional_distribution(probs, mask)) < 1e-9


def test_steered_loop_gives_the_exact_future():
    """Steer, amplify, keep running: the clicks after the click match the exact filter."""
    exact = exact_after_click(M1, 3, 3)
    qc = loop_circuit(M1, 3, 3, 1, "full", steer=1.0)
    probs = np.abs(Statevector(qc).data) ** 2
    index = np.arange(probs.size)
    keep = ((index >> (M1.n_memory + 2)) & 1) == 1
    base = qc.num_qubits - 3
    got = [probs[keep & (((index >> (base + j)) & 1) == 1)].sum() / probs[keep].sum() for j in range(3)]
    assert np.abs(np.array(got) - exact["conditional"]).max() < 1e-9


# ------------------------------------------------------------------ the web page


@pytest.mark.parametrize("gamma", [0.2, 0.62, 1.0])
def test_the_page_builds_the_same_step_as_the_package(gamma):
    """demo/template.html builds V from W and an analytic emission. This is that formula, against the real step."""
    import sys

    sys.path.insert(0, str(Path(__file__).parents[1] / "demo"))
    from build_page import memory_unitary

    a = np.arcsin(np.sqrt(gamma))
    c, s = np.cos(a), np.sin(a)
    E = np.zeros((4, 4))  # index l * 2 + e, the same matrix as emission() in the page
    E[0, 0] = 1
    E[1, 1], E[2, 1] = c, s
    E[3, 2] = 1
    E[1, 3], E[2, 3] = -s, c
    W = memory_unitary(M1)
    V = np.zeros((8, 8), dtype=complex)
    for lo in range(2):
        for d in range(2):
            for eo in range(2):
                row = lo * 4 + d * 2 + eo
                for li in range(2):
                    for ei in range(2):
                        V[row, li * 4:li * 4 + 4] += E[lo * 2 + eo, li * 2 + ei] * W[d * 2 + ei]
    assert np.abs(V - step_unitary(M1, gamma).reshape(8, 8)).max() < 1e-12


# ------------------------------------------------------------------ the hardware pipeline


def experiment_module(name: str):
    import importlib
    import sys

    sys.path.insert(0, str(Path(__file__).parents[1] / "experiments"))
    return importlib.import_module(name)


def test_compact_hands_a_simulator_only_the_qubits_a_circuit_touches():
    """A circuit compiled for a device names all 156 qubits, and simulating that can take down a laptop."""
    wide = QuantumCircuit(156, 2)
    wide.h(151)
    wide.cx(151, 7)
    wide.barrier()
    wide.measure([7, 151], [0, 1])
    small, active = experiment_module("run_ibm").compact(wide)
    assert active == [7, 151]
    assert small.num_qubits == 2
    counts = AerSimulator(method="statevector", seed_simulator=1).run(small, shots=2000).result().get_counts()
    assert set(counts) == {"00", "11"}


def test_readout_rates_come_from_the_calibration_circuits():
    """Bit i of each count belongs to the i-th calibrated qubit: one qubit misreads 0, the other misreads 1."""
    rates = experiment_module("analyse_hardware").device_flip_rates(
        {"qubits": [4, 9], "counts": [{"00": 90, "01": 10}, {"11": 80, "01": 20}]})
    assert rates == {4: (0.1, 0.0), 9: (0.0, 0.2)}


def test_a_simulation_can_state_its_readout_rates_directly():
    rates = experiment_module("analyse_hardware").device_flip_rates({"qubits": [4, 9], "flip_rates": [[0.01, 0.02], [0.03, 0.04]]})
    assert rates == {4: (0.01, 0.02), 9: (0.03, 0.04)}


def test_the_compiler_stays_off_the_qubits_it_is_told_to_avoid():
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2

    from qrsm_grover.hardware import compile_best

    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()
    backend = FakeManilaV2()
    isa, stats = compile_best(bell, backend, seeds=2, avoid=(0, 1))
    touched = {isa.find_bit(q).index for inst in isa.data if inst.operation.name != "barrier" for q in inst.qubits}
    assert touched and not touched & {0, 1}
    assert stats["two_qubit_gates"] >= 1

