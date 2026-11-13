"""Predictions for the next IBM job, written down before it runs.

    python applied/predict.py            compile the frozen bundle, simulate it with the device noise model, save
    python applied/predict.py --check    re-simulate the saved compiled circuits and compare

The 11 November campaign left three things behind: the qubits it ran on, the device's calibration that morning, and a
noise scale fitted to two echo circuits (hardware_campaign/noise_model). This file compiles the new circuits onto the
same qubits and asks that same noise model what IBM should return. applied/study.py shows the model already explains
the 11 November answers to within one to three points, without having been fitted to them.

A prediction is only worth something if it cannot be adjusted afterwards, so predictions.json records the hash of the
bundle and of the compiled circuits it was made from. The real job will be compiled against the device as it is on
the day, possibly on other qubits; the comparison will say so.

Nothing is submitted here. The compile step uses qiskit-ibm-runtime's offline copy of the device's wiring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "rewindandamplify-main"))

import study  # noqa: E402
from qrsm_grover.hardware import without_qubits  # noqa: E402

BUNDLE = HERE / "hardware_bundle"
ISA = HERE / "predictions_isa.qpy"
OUT = HERE / "predictions.json"
REFERENCE_RUN = study.PRECISION
SEED = 20261111                      # the campaign's transpiler seed


def load_simulator():
    return study.noise_tools()[0]


def reference_run(simulate):
    folder = study.CAMPAIGN / "runs" / REFERENCE_RUN
    plan = study.read_json(folder / "plan.json")
    return simulate.Run(REFERENCE_RUN, plan, study.read_json(folder / "raw.json"),
                        study.read_json(folder / "backend_properties.json"), [], {})


def bundle():
    manifest = study.read_json(BUNDLE / "manifest.json")
    with open(BUNDLE / "logical.qpy", "rb") as handle:
        circuits = qpy.load(handle)
    return manifest, circuits


def compile_on_patch(circuits: list, patch: list[int]) -> list:
    """The campaign's own recipe: restrict the device to the chosen qubits, highest optimisation, fixed seed."""
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

    backend = FakeMarrakesh()
    target = without_qubits(backend.target, set(range(backend.num_qubits)) - set(patch))
    out = []
    for circuit in circuits:
        manager = generate_preset_pass_manager(target=target, optimization_level=3, seed_transpiler=SEED,
                                               initial_layout=patch[:circuit.num_qubits])
        out.append(manager.run(circuit))
    return out


def gate_error(run, gate: str, qubits: tuple) -> float:
    try:
        return run.gate_error(gate, qubits)
    except KeyError:
        return run.gate_error(gate, tuple(reversed(qubits)))


def predicted(simulate, run, isa, scale: float, readout: bool = True) -> np.ndarray:
    """The outcome distribution of one compiled circuit under the noise model. Outcome bit i is classical bit i."""
    small, active, measured = simulate.compact(isa)
    qubit_of_bit = [q for q, _ in sorted(measured, key=lambda item: item[1])]
    noise = NoiseModel(basis_gates=["cz", "sx", "x", "rz"])
    if scale > 0:
        for i, physical in enumerate(active):
            for gate in ("sx", "x"):
                noise.add_quantum_error(depolarizing_error(2 * min(scale * gate_error(run, gate, (physical,)), 0.49), 1),
                                        gate, [i], warnings=False)
        pairs = {tuple(small.find_bit(q).index for q in inst.qubits) for inst in small.data if inst.operation.name == "cz"}
        for a, b in sorted(pairs):
            error = min(scale * gate_error(run, "cz", (active[a], active[b])), 0.74)
            noise.add_quantum_error(depolarizing_error(4 * error / 3, 2), "cz", [a, b], warnings=False)
    small.save_probabilities(qubit_of_bit)
    simulator = AerSimulator(method="density_matrix", noise_model=noise, max_parallel_threads=1)
    probabilities = np.asarray(simulator.run(small, shots=1).result().data(0)["probabilities"], dtype=float)
    if readout:
        probabilities = simulate.apply_readout(run, probabilities, [active[q] for q in qubit_of_bit], "job")
    return probabilities / probabilities.sum()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(compiled: list) -> dict:
    simulate = load_simulator()
    run = reference_run(simulate)
    manifest, _ = bundle()
    scale = study.read_json(study.CAMPAIGN / "noise_model" / "results.json")["echo_fit"]["scale"]
    rows = {}
    for entry, isa in zip(manifest["circuits"], compiled):
        meta, reference = entry["metadata"], entry["reference"]
        row = {"two_qubit_gates": int(isa.count_ops().get("cz", 0)), "depth": int(isa.depth())}
        for label, s, readout in (("ideal", 0.0, False), ("calibration", 1.0, True), ("echo_scaled", scale, True)):
            distribution = predicted(simulate, run, isa, s, readout)
            if meta["kind"] == "echo":
                row[label] = {"all_zero_return": float(distribution[0])}
            else:
                row[label] = study.answers(study.tally(distribution, reference["chronological_history_qubits"],
                                                       reference["memory_qubits"], meta["tau"]))
        rows[entry["name"]] = row
    another = lambda name, label="echo_scaled": rows[name][label]["another"]  # noqa: E731
    cause = lambda name, label="echo_scaled": rows[name][label]["defect_after_event"]  # noqa: E731
    comparisons = {}
    for label in ("ideal", "echo_scaled"):
        comparisons[label] = {
            "chipmaking: second event, clean minus defect (rewound)": another("window-clean-rewound", label) - another("window-defect-rewound", label),
            "chipmaking: second event, clean minus defect (plain)": another("window-clean-plain", label) - another("window-defect-plain", label),
            "lasers: second event, stepped minus defect (rewound)": another("window-stepped-rewound", label) - another("window-defect-rewound", label),
            "lasers: second event, stepped minus defect (plain)": another("window-stepped-plain", label) - another("window-defect-plain", label),
            "cause: defect holds the energy after the event (rewound)": cause("site-defect-rewound", label),
            "cause: defect holds the energy after the event (plain)": cause("site-defect-plain", label),
        }
    return {
        "schema": "ra-applied-predictions-v1",
        "made_before_the_job": True,
        "device_assumed": {"backend": run.raw["backend"], "physical_qubits": run.plan["physical_patch"][:8],
                           "calibration": run.properties["last_update_date"], "noise_scale_from_echoes": scale,
                           "readout": f"measured inside job {run.raw['job_id']}"},
        "model": "depolarizing gate errors at the reported rates times the echo-fitted scale, plus measured readout "
                 "errors; no idle decoherence, crosstalk, leakage or drift",
        "shots_planned": study.SHOTS,
        "rows": rows,
        "comparisons": comparisons,
        "sha256": {"applied/hardware_bundle/manifest.json": digest(BUNDLE / "manifest.json"),
                   "applied/predictions_isa.qpy": digest(ISA)},
        "caveat": "Made for the qubits and calibration of 11 November 2026. The job is compiled again on the day and may "
                  "land on other qubits with other error rates.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="re-simulate the saved compiled circuits and compare")
    args = parser.parse_args()
    if args.check:
        with open(ISA, "rb") as handle:
            compiled = qpy.load(handle)
        gap, where = study.worst_difference(build(compiled), study.read_json(OUT))
        if gap > 1e-6:
            raise SystemExit(f"applied/predictions.json no longer matches its sources: {gap:.3g} at {where}")
        print(f"applied/predictions.json reproduces from the saved compiled circuits (largest difference {gap:.1e}).")
        return
    if OUT.exists():
        raise SystemExit("applied/predictions.json already exists. Predictions are written once; delete it deliberately to redo them.")
    simulate = load_simulator()
    patch = reference_run(simulate).plan["physical_patch"]
    _, circuits = bundle()
    compiled = compile_on_patch(circuits, patch)
    with open(ISA, "wb") as handle:
        qpy.dump(compiled, handle)
    result = build(compiled)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, row in result["rows"].items():
        print(f"{name:26s} {row['two_qubit_gates']:4d} two-qubit gates   {json.dumps({k: round(v, 4) if not isinstance(v, list) else [round(x, 4) for x in v] for k, v in row['echo_scaled'].items()})}")
    print(json.dumps(result["comparisons"], indent=2))


if __name__ == "__main__":
    main()
