"""A calibration-based noise simulation of the exact circuits that ran on IBM Marrakesh.

The campaign saved, for every job, the compiled circuits that were submitted (ISA QPY), the device's calibration
snapshot (backend_properties.json) and the raw counts. That is enough to ask a simple question offline:

    if the only errors were the gate and readout errors the device reported that morning,
    what would these circuits have returned?

The model is deliberately plain, and each simplification is a stated limit, not a hidden one:

    sx, x      one-qubit depolarizing error with the reported average gate infidelity
    cz         two-qubit depolarizing error with the reported average gate infidelity
    rz         exact (a virtual frame change on this hardware)
    readout    P(read 1 | prepared 0) and P(read 0 | prepared 1) for each measured qubit, taken from the all-zeros
               and all-ones calibration circuits that ran inside the same job (the reported values were a day
               old, and for some qubits several times off; they remain available as readout="reported")
    absent     idle decoherence, crosstalk, leakage, drift between calibration and execution

`scale` multiplies every gate error. scale = 1 is the calibration as reported. The study in run_study.py also fits
one scale to the campaign's own echo circuits and uses it to predict the science circuits it never saw.

Circuits are simulated as density matrices and probabilities are read out exactly, so results have no shot noise
and are the same on every machine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qpy
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
ROOT = CAMPAIGN.parent


def read_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class Run:
    """Everything saved for one hardware job."""

    name: str
    plan: dict
    raw: dict
    properties: dict
    circuits: list
    manifest: dict

    @classmethod
    def load(cls, name: str) -> "Run":
        folder = CAMPAIGN / "runs" / name
        plan = read_json(folder / "plan.json")
        with open(folder / plan["compiled_qpy_file"], "rb") as handle:
            circuits = qpy.load(handle)
        manifest = read_json(ROOT / plan["bundle"] / "manifest.json")
        return cls(name, plan, read_json(folder / "raw.json"), read_json(folder / "backend_properties.json"),
                   circuits, {c["name"]: c for c in manifest["circuits"]})

    def pub(self, circuit: str) -> tuple[int, dict]:
        for index, pub in enumerate(self.plan["pubs"]):
            if pub["name"] == circuit:
                return index, pub
        raise KeyError(circuit)

    def counts(self, circuit: str) -> tuple[np.ndarray, int]:
        """The measured distribution over the logical qubits (qubit 0 is the last character of each key)."""
        row = next(r for r in self.raw["rows"] if r["name"] == circuit)
        out = np.zeros(1 << row["logical_qubits"])
        for key, value in row["counts"].items():
            out[int(key.replace(" ", ""), 2)] += value
        assert out.sum() == row["shots"]
        return out / row["shots"], row["shots"]

    # ------------------------------------------------------------------ the device as calibrated

    def qubit_properties(self, physical: int) -> dict:
        return {entry["name"]: entry["value"] for entry in self.properties["qubits"][physical]}

    def readout_errors(self, physical: int, source: str = "job") -> tuple[float, float]:
        """(P(read 1 | prepared 0), P(read 0 | prepared 1)) for one physical qubit.

        "job" uses this job's own all-zeros and all-ones circuits. They include state-preparation error, so they
        are preparation-plus-readout rates. "reported" uses the backend's calibration snapshot.
        """
        if source == "reported":
            prop = self.qubit_properties(physical)
            return prop["prob_meas1_prep0"], prop["prob_meas0_prep1"]
        assert source == "job", source
        if not hasattr(self, "_job_readout"):
            rates = {}
            for circuit, prepared in (("cal_zero", 0), ("cal_one", 1)):
                row = next(r for r in self.raw["rows"] if r["name"] == circuit)
                wrong = np.zeros(len(row["measurement_physical_qubits"]))
                for key, value in row["counts"].items():
                    bits = key.replace(" ", "")[::-1]              # bit i is the i-th measured qubit
                    wrong += value * np.array([int(b) != prepared for b in bits])
                for qubit, rate in zip(row["measurement_physical_qubits"], wrong / row["shots"]):
                    rates.setdefault(qubit, {})[prepared] = float(rate)
            self._job_readout = rates
        return self._job_readout[physical][0], self._job_readout[physical][1]

    def gate_error(self, gate: str, qubits: tuple) -> float:
        for entry in self.properties["gates"]:
            if entry["gate"] == gate and tuple(entry["qubits"]) == tuple(qubits):
                return next(p["value"] for p in entry["parameters"] if p["name"] == "gate_error")
        raise KeyError((gate, qubits))


def compact(isa: QuantumCircuit) -> tuple[QuantumCircuit, list[int], list[tuple[int, int]]]:
    """The same circuit on only the physical qubits it touches, without measurements.

    Returns the small circuit, the physical qubit behind each of its qubits, and (small qubit, classical bit) for
    every measurement that was removed.
    """
    index = {qubit: i for i, qubit in enumerate(isa.qubits)}
    clbit = {bit: i for i, bit in enumerate(isa.clbits)}
    active = sorted({index[q] for inst in isa.data if inst.operation.name != "barrier" for q in inst.qubits})
    small_of = {physical: i for i, physical in enumerate(active)}
    small = QuantumCircuit(len(active))
    measured = []
    for inst in isa.data:
        name = inst.operation.name
        if name == "barrier":
            continue
        qubits = [small_of[index[q]] for q in inst.qubits]
        if name == "measure":
            measured.append((qubits[0], clbit[inst.clbits[0]]))
        else:
            assert name in ("sx", "x", "rz", "cz"), f"unexpected native gate {name}"
            small.append(inst.operation, qubits)
    assert not any(inst.operation.name == "measure" for inst in small.data)
    return small, active, measured


def gate_noise(run: Run, active: list[int], small: QuantumCircuit, scale: float) -> NoiseModel:
    """Depolarizing errors with the reported infidelities. For d-dimensional depolarizing, infidelity = p (d - 1) / d."""
    noise = NoiseModel(basis_gates=["cz", "sx", "x", "rz"])
    if scale <= 0:
        return noise
    for i, physical in enumerate(active):
        for gate in ("sx", "x"):
            error = min(scale * run.gate_error(gate, (physical,)), 0.49)
            noise.add_quantum_error(depolarizing_error(2 * error, 1), gate, [i], warnings=False)
    pairs = {tuple(small.find_bit(q).index for q in inst.qubits) for inst in small.data if inst.operation.name == "cz"}
    for a, b in sorted(pairs):
        error = min(scale * run.gate_error("cz", (active[a], active[b])), 0.74)
        noise.add_quantum_error(depolarizing_error(4 * error / 3, 2), "cz", [a, b], warnings=False)
    return noise


def apply_readout(run: Run, probabilities: np.ndarray, physical_of_bit: list[int], source: str = "job") -> np.ndarray:
    """Push a distribution through each measured qubit's assignment errors. Bit q is axis n - 1 - q."""
    n = len(physical_of_bit)
    p = probabilities.reshape((2,) * n)
    for bit, physical in enumerate(physical_of_bit):
        p10, p01 = run.readout_errors(physical, source)                    # read 1 | was 0, read 0 | was 1
        assignment = np.array([[1 - p10, p01], [p10, 1 - p01]])
        axis = n - 1 - bit
        p = np.moveaxis(np.tensordot(assignment, p, axes=(1, axis)), 0, axis)
    return p.reshape(-1)


def simulate(run: Run, circuit: str, scale: float = 1.0, readout: str | None = "job") -> np.ndarray:
    """The distribution over the logical qubits that this noise model predicts for one submitted circuit.

    `readout` is "job", "reported" or None for perfect readout.
    """
    index, pub = run.pub(circuit)
    small, active, measured = compact(run.circuits[index])
    n = pub["logical_qubits"]
    assert sorted(bit for _, bit in measured) == list(range(n)), "every logical qubit is measured exactly once"
    qubit_of_bit = [q for q, _ in sorted(measured, key=lambda item: item[1])]
    assert [active[q] for q in qubit_of_bit] == pub["measurement_physical_qubits"]
    small.save_probabilities(qubit_of_bit)
    simulator = AerSimulator(method="density_matrix", noise_model=gate_noise(run, active, small, scale),
                             max_parallel_threads=1)
    probabilities = np.asarray(simulator.run(small, shots=1).result().data(0)["probabilities"], dtype=float)
    if readout:
        probabilities = apply_readout(run, probabilities, pub["measurement_physical_qubits"], readout)
    return probabilities / probabilities.sum()


# ---------------------------------------------------------------------------- what the campaign reports


def marginal(distribution: np.ndarray, qubits: list[int]) -> np.ndarray:
    """The distribution over chosen qubits, with qubits[0] as the lowest bit of the new index."""
    index = np.arange(distribution.size)
    packed = np.zeros(distribution.size, dtype=np.int64)
    for j, qubit in enumerate(qubits):
        packed |= ((index >> qubit) & 1) << j
    return np.bincount(packed, weights=distribution, minlength=1 << len(qubits))


def observables(run: Run, circuit: str, distribution: np.ndarray) -> dict:
    """Hit rate, answer error and (for after-click circuits) later click rates, as the campaign defines them."""
    entry = run.manifest[circuit]
    meta, reference = entry["metadata"], entry["reference"]
    if meta["kind"] == "echo":
        return {"all_zero_return": float(distribution[0])}
    history = marginal(distribution, reference["chronological_history_qubits"])
    step = meta["t0"] if meta["kind"] == "loop" else meta["T"]
    index = np.arange(history.size)
    hit = ((index >> (step - 1)) & 1) == 1
    target = np.asarray(reference["unsteered_history_probabilities"], dtype=float)
    selected = history[hit] / history[hit].sum()
    out = {"hit_rate": float(history[hit].sum()),
           "answer_error_tv": 0.5 * float(np.abs(selected - target[hit] / target[hit].sum()).sum())}
    if meta["kind"] == "loop":
        out["later_click_rates"] = [float(history[hit & (((index >> (step + j - 1)) & 1) == 1)].sum() / history[hit].sum())
                                    for j in range(1, meta["tau"] + 1)]
    return out


def two_qubit_gates(run: Run, circuit: str) -> int:
    return run.pub(circuit)[1]["gate_counts"]["cz"]
