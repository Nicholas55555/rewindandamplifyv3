"""Freeze the circuits of the next IBM job, with their exact answers, before anything is submitted.

    python applied/bundle.py        writes applied/hardware_bundle/ once, then refuses to overwrite it

The bundle uses the same layout as the 11 November campaign, so the campaign's own guarded tool can prepare, submit
and fetch it (hardware_campaign/campaign.py: quota check, time cap, one submission per plan). This file submits
nothing and never touches an IBM account.

Thirteen circuits, all built from the main project's package:

    site-*      three steps, then every qubit is measured: the rare event and where the hidden defect was
    window-*    three steps, the rare event, then three more steps: what follows the rare event
    echo-*      the machine run forwards and then backwards, to size the device's noise on the day

for three machines: the main project's (one hidden defect), the same emitter with nothing hidden, and the defect with
its frequency stepped from 0.3 to 0.6 radians per step.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from qiskit import qpy, transpile
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rewindandamplify-main"))

from qrsm_grover.amplify import hardware_amplified  # noqa: E402
from qrsm_grover.fastsim import reflection_qubits  # noqa: E402
from qrsm_grover.hardware import echo_experiment, measured, steer_for  # noqa: E402
from qrsm_grover.model import QRSM  # noqa: E402
from qrsm_grover.predicates import click_at  # noqa: E402
from qrsm_grover.queries import loop_circuit  # noqa: E402

T0, WINDOW, LOCAL = 3, 3, "memory+last-1"
MACHINES = {"defect": QRSM(), "clean": QRSM(phi=(), zeta=()), "stepped": QRSM(zeta=(0.6,))}
DEST = HERE / "hardware_bundle"


def experiments() -> list[dict]:
    """Every circuit of the job: its name, the measured circuit, and how to read its outcome bits."""
    out = []

    def add(name, body, machine, reading, how, history, tau):
        model = MACHINES[machine]
        out.append({"name": name, "circuit": measured(body),
                    "metadata": {"kind": "applied", "reading": reading, "machine": machine, "how": how, "t0": T0, "tau": tau,
                                 "theta": model.theta, "gamma": model.gamma, "phi": list(model.phi), "zeta": list(model.zeta)},
                    "reference": {"memory_qubits": model.n_memory, "chronological_history_qubits": history}})

    for machine, hows in (("defect", ("plain", "steered", "rewound")), ("stepped", ("plain", "rewound"))):
        model = MACHINES[machine]
        n, steer = model.n_memory, steer_for(model, T0)
        lights = list(range(n, n + T0))
        oracle = click_at(T0).oracle(n + T0, lights)
        for how in hows:
            A = model.purified(T0, gammas=None if how == "plain" else [None] * (T0 - 1) + [steer])
            body = hardware_amplified(A, oracle, 1 if how == "rewound" else 0, reflect_on=reflection_qubits(model, T0, LOCAL))
            add(f"site-{machine}-{how}", body, machine, "cause", how, lights, 0)
    for machine in ("defect", "clean", "stepped"):
        model = MACHINES[machine]
        n, steer = model.n_memory, steer_for(model, T0)
        for how in ("plain", "rewound"):
            body = loop_circuit(model, T0, WINDOW, 1 if how == "rewound" else 0, LOCAL, steer if how == "rewound" else None)
            history = list(range(n, n + T0)) + list(range(body.num_qubits - WINDOW, body.num_qubits))
            add(f"window-{machine}-{how}", body, machine, "window", how, history, WINDOW)
    for steps in (3, 5):
        echo = echo_experiment(MACHINES["defect"], steps, 1)
        out.append({"name": echo.name, "circuit": echo.circuit, "metadata": dict(echo.meta), "reference": {}})
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if (DEST / "manifest.json").exists():
        raise SystemExit("applied/hardware_bundle already exists. A frozen bundle is not rebuilt: use a new folder.")
    DEST.mkdir(exist_ok=True)
    rows, arrays, exported = [], {}, []
    for index, item in enumerate(experiments()):
        before = Statevector.from_instruction(item["circuit"].remove_final_measurements(inplace=False))
        circuit = transpile(item["circuit"], basis_gates=["u", "cx"], optimization_level=0)   # plain gates store safely
        after = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
        assert before.equiv(after), item["name"]
        probabilities = after.probabilities()
        assert abs(probabilities.sum() - 1) < 1e-10
        key = f"p{index:03d}"
        arrays[key] = probabilities
        exported.append(circuit)
        rows.append({"name": item["name"], "index": index, "num_qubits": circuit.num_qubits, "metadata": item["metadata"],
                     "reference": item["reference"], "ideal_probability_key": key})
    with open(DEST / "logical.qpy", "wb") as handle:
        qpy.dump(exported, handle)
    with open(DEST / "logical.qpy", "rb") as handle:
        assert all(a == b for a, b in zip(exported, qpy.load(handle))), "the stored circuits must read back unchanged"
    np.savez_compressed(DEST / "ideal_probabilities.npz", **arrays)
    sources = {path.relative_to(ROOT).as_posix(): digest(path)
               for path in sorted((ROOT / "rewindandamplify-main" / "qrsm_grover").glob("*.py"))}
    sources["applied/bundle.py"] = digest(Path(__file__))
    manifest = {"schema": "ra-hardware-bundle-v1", "circuits": rows, "source_sha256": sources,
                "scope": "The main project's machine asked three fields' questions: with a hidden defect, without one, and "
                         "with the defect's frequency stepped. Programmed models; no photon, laser, resist or wafer.",
                "qpy_file": "logical.qpy", "ideal_probabilities_file": "ideal_probabilities.npz"}
    for name in ("logical.qpy", "ideal_probabilities.npz"):
        manifest[name + "_sha256"] = digest(DEST / name)
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"circuits": len(rows), "widest": max(c.num_qubits for c in exported), "path": str(DEST.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
