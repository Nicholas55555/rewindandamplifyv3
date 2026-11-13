"""A small lithography toy, its circuits, and the bundle that freezes them before anything is submitted.

    python applied/contact/exposure.py            print the exact answers and each circuit's size
    python applied/contact/exposure.py --freeze   write applied/contact/hardware_bundle/ once; it is never rebuilt

The model: one contact, exposed once.

    source      the dose is low with probability 0.2. Nothing downstream shows it directly: it is the hidden cause.
    cell        the contact's cell comes out dark with probability 0.1 at normal dose and 0.5 at low dose
    failure     a dark cell fails to print with probability 0.2. This is the rare event: 3.6% of exposures.
    neighbour   the next cell is exposed by the same source, with the same probabilities

Two questions about the rare failures:

    the cause       was the dose low?                 55.6% of the time, against 20% beforehand
    what follows    is the neighbouring cell dark?    32.2% of the time, against 18% for any cell

A second model, "clean", gives every cell the same 18% chance of being dark with nothing shared behind them. There
a failure says nothing about the neighbour: 18%. Failures that come in pairs point at the source.

The four moves of the main project, on this model:

    purify      nothing is measured until the end, so one exposure is one reversible circuit
    steer       for the amplified step, a dark cell fails with certainty instead of with probability 0.2. Every
                failing history is multiplied by the same factor, so the answers about failures do not change
    amplify     one round, built by the main project's own function, with a reflection on the three qubits the
                rewind touches. The neighbour is exposed afterwards, as the after-click steps are in the main result
    verify      the failure flag is measured, and a shot without it is dropped. A failed contact must be a dark
                cell, so the cell bit is a second check that needs no knowledge of the right answer

The qubits sit on a line: neighbour, source, cell, flag. Every gate of the model itself joins neighbours on that
line. The one exception is inside the amplification: its reflection is a three-qubit gate on source, cell and flag,
which the compiler has to lay out along the line. Outcome bit q is qubit q.

This file is recorded by hash in the bundle it writes. After a job has been submitted from that bundle, do not edit
it: a new experiment gets a new file and a new bundle.

It is a toy. The cells are dark or bright: no photon counts, no blur, no resist. Bayes' rule answers both questions
by hand, and that hand calculation is the reference the circuits are checked against.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qpy, transpile
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "rewindandamplify-main"))

from qrsm_grover.amplify import hardware_amplified  # noqa: E402
from qrsm_grover.hardware import echo_experiment, measured  # noqa: E402
from qrsm_grover.model import QRSM  # noqa: E402

NEIGHBOUR, SOURCE, CELL, FLAG = 0, 1, 2, 3
MODELS = {
    "dose": {"low_dose": 0.2, "dark_at_normal_dose": 0.1, "dark_at_low_dose": 0.5, "dark_cell_fails": 0.2, "hidden_source": True},
    "clean": {"low_dose": 0.2, "dark_at_normal_dose": 0.1, "dark_at_low_dose": 0.5, "dark_cell_fails": 0.2, "hidden_source": False},
}
BUILDS = ("plain", "steered", "rewound")
DEST = HERE / "hardware_bundle"


def angle(probability: float) -> float:
    """The RY angle that takes |0> to |1> with this probability."""
    return 2 * float(np.arcsin(np.sqrt(probability)))


def dark_at_all(model: dict) -> float:
    """The chance that a cell is dark, whatever the source did."""
    return (1 - model["low_dose"]) * model["dark_at_normal_dose"] + model["low_dose"] * model["dark_at_low_dose"]


def expose(qc: QuantumCircuit, model: dict, cell: int) -> None:
    """Expose one cell: dark with a chance set by the source, or by nothing at all in the clean model."""
    if model["hidden_source"]:
        qc.ry(angle(model["dark_at_normal_dose"]), cell)
        qc.cry(angle(model["dark_at_low_dose"]) - angle(model["dark_at_normal_dose"]), SOURCE, cell)
    else:
        qc.ry(angle(dark_at_all(model)), cell)


def contact(model: dict, fails: float) -> QuantumCircuit:
    """The reversible exposure of the contact: source, cell, and the failure flag. The neighbour is not touched."""
    qc = QuantumCircuit(4, name="contact")
    if model["hidden_source"]:
        qc.ry(angle(model["low_dose"]), SOURCE)
    expose(qc, model, CELL)
    qc.cry(angle(fails), CELL, FLAG)
    return qc


def circuit(model_name: str, build: str) -> QuantumCircuit:
    """One experiment, without measurements.

    plain     the model as it is
    steered   a dark cell fails with certainty; no amplification
    rewound   steered, then one round of rewind and amplify
    """
    model = MODELS[model_name]
    A = contact(model, model["dark_cell_fails"] if build == "plain" else 1.0)
    oracle = QuantumCircuit(4, name="failed")
    oracle.z(FLAG)
    touched = [SOURCE, CELL, FLAG] if model["hidden_source"] else [CELL, FLAG]
    body = hardware_amplified(A, oracle, 1 if build == "rewound" else 0, n_ancilla=0, reflect_on=touched)
    expose(body, model, NEIGHBOUR)
    body.name = f"{model_name}-{build}"
    return body


def truth(model_name: str) -> dict:
    """The answers by Bayes' rule."""
    model = MODELS[model_name]
    dark = dark_at_all(model)
    out = {"fail": model["dark_cell_fails"] * dark, "cell_dark_given_fail": 1.0, "neighbour_dark": dark}
    if model["hidden_source"]:
        low = model["low_dose"] * model["dark_at_low_dose"] / dark
        out["dose_low_given_fail"] = low
        out["neighbour_dark_given_fail"] = low * model["dark_at_low_dose"] + (1 - low) * model["dark_at_normal_dose"]
    else:
        out["dose_low_given_fail"] = None
        out["neighbour_dark_given_fail"] = dark
    return out


def tally(weights: np.ndarray) -> dict:
    """Sums over outcomes, from a probability vector or a vector of counts."""
    index = np.arange(weights.size)
    bit = lambda q: ((index >> q) & 1) == 1  # noqa: E731
    failed = bit(FLAG)
    return {"all": weights.sum(), "fail": weights[failed].sum(), "fail_and_dose_low": weights[failed & bit(SOURCE)].sum(),
            "fail_and_neighbour_dark": weights[failed & bit(NEIGHBOUR)].sum(), "fail_and_cell_dark": weights[failed & bit(CELL)].sum(),
            "neighbour_dark": weights[bit(NEIGHBOUR)].sum()}


def answers(weights: np.ndarray, model_name: str) -> dict:
    """The same quantities as truth(), read from an outcome distribution."""
    t = tally(weights)
    return {"fail": float(t["fail"] / t["all"]), "cell_dark_given_fail": float(t["fail_and_cell_dark"] / t["fail"]),
            "neighbour_dark": float(t["neighbour_dark"] / t["all"]),
            "dose_low_given_fail": float(t["fail_and_dose_low"] / t["fail"]) if MODELS[model_name]["hidden_source"] else None,
            "neighbour_dark_given_fail": float(t["fail_and_neighbour_dark"] / t["fail"])}


def ideal(model_name: str, build: str) -> dict:
    """What a circuit returns on a perfect device."""
    return answers(Statevector.from_instruction(circuit(model_name, build)).probabilities(), model_name)


def two_qubit_gates_on_a_line(body: QuantumCircuit) -> int:
    line = [[0, 1], [1, 0], [1, 2], [2, 1], [2, 3], [3, 2]]
    compiled = transpile(body, basis_gates=["cz", "rz", "sx", "x"], coupling_map=line, optimization_level=3, seed_transpiler=1)
    return int(compiled.count_ops().get("cz", 0))


def experiments() -> list[dict]:
    """Every circuit of the job: six exposures, and the main project's two echo circuits to size the day's noise."""
    out = []
    for model_name in MODELS:
        for build in BUILDS:
            out.append({"name": f"{model_name}-{build}", "circuit": measured(circuit(model_name, build)),
                        "metadata": {"kind": "contact", "model": model_name, "build": build, **MODELS[model_name]},
                        "reference": {"qubits": {"neighbour": NEIGHBOUR, "source": SOURCE, "cell": CELL, "flag": FLAG},
                                      "truth": truth(model_name)}})
    for steps in (3, 5):
        echo = echo_experiment(QRSM(), steps, 1)
        out.append({"name": echo.name, "circuit": echo.circuit, "metadata": dict(echo.meta), "reference": {}})
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze() -> None:
    if (DEST / "manifest.json").exists():
        raise SystemExit("applied/contact/hardware_bundle already exists. A frozen bundle is not rebuilt: use a new folder.")
    DEST.mkdir(exist_ok=True)
    rows, arrays, exported = [], {}, []
    for index, item in enumerate(experiments()):
        before = Statevector.from_instruction(item["circuit"].remove_final_measurements(inplace=False))
        stored = transpile(item["circuit"], basis_gates=["u", "cx"], optimization_level=0)       # plain gates store safely
        after = Statevector.from_instruction(stored.remove_final_measurements(inplace=False))
        assert before.equiv(after), item["name"]
        key = f"p{index:03d}"
        arrays[key] = after.probabilities()
        exported.append(stored)
        rows.append({"name": item["name"], "index": index, "num_qubits": stored.num_qubits, "metadata": item["metadata"],
                     "reference": item["reference"], "ideal_probability_key": key})
    with open(DEST / "logical.qpy", "wb") as handle:
        qpy.dump(exported, handle)
    with open(DEST / "logical.qpy", "rb") as handle:
        assert all(a == b for a, b in zip(exported, qpy.load(handle))), "the stored circuits must read back unchanged"
    np.savez_compressed(DEST / "ideal_probabilities.npz", **arrays)
    sources = {path.relative_to(ROOT).as_posix(): digest(path)
               for path in sorted((ROOT / "rewindandamplify-main" / "qrsm_grover").glob("*.py"))}
    sources["applied/contact/exposure.py"] = digest(Path(__file__))
    manifest = {"schema": "ra-hardware-bundle-v1", "circuits": rows, "source_sha256": sources,
                "scope": "A four-qubit lithography toy: a hidden source dose, a contact cell, a rare printing failure and a "
                         "neighbouring cell, with and without the hidden source. Programmed models; no resist or wafer.",
                "qpy_file": "logical.qpy", "ideal_probabilities_file": "ideal_probabilities.npz"}
    for name in ("logical.qpy", "ideal_probabilities.npz"):
        manifest[name + "_sha256"] = digest(DEST / name)
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"circuits": len(rows), "widest": max(c.num_qubits for c in exported), "path": DEST.relative_to(ROOT).as_posix()}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--freeze", action="store_true", help="write the hardware bundle (once)")
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return
    show = lambda value: "    -  " if value is None else f"{100 * value:6.2f}%"  # noqa: E731
    for model_name in MODELS:
        t = truth(model_name)
        print(f"{model_name}: a contact fails in {show(t['fail'])} of exposures. Dose low, given a failure: {show(t['dose_low_given_fail'])}. "
              f"Neighbour dark, given a failure: {show(t['neighbour_dark_given_fail'])} (any cell: {show(t['neighbour_dark'])}).")
        for build in BUILDS:
            got = ideal(model_name, build)
            print(f"   {build:8s} {two_qubit_gates_on_a_line(circuit(model_name, build)):3d} two-qubit gates   failure in {show(got['fail'])} of shots   "
                  f"dose low {show(got['dose_low_given_fail'])}   neighbour dark {show(got['neighbour_dark_given_fail'])}   "
                  f"cell dark {show(got['cell_dark_given_fail'])}")


if __name__ == "__main__":
    main()
