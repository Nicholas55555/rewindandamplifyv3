"""What a noise model says IBM will return for the contact toy, written down before the job runs.

    python applied/contact/forecast.py            compile the frozen bundle, simulate it, save (written once)
    python applied/contact/forecast.py --check    re-simulate the saved compiled circuits and compare

The device assumed is the one the 12 November job met (hardware_campaign/runs/applied_v1): its qubits, that
evening's calibration, the readout errors measured inside that job, and the one noise scale fitted afterwards to its
two echo circuits (recorded in applied/results.json). The noise model is the campaign's own
(hardware_campaign/noise_model): depolarizing gate errors at the reported rates times that scale, then readout
errors. It has no idle decoherence, crosstalk, leakage or drift, and on 12 November it was too hopeful about the
device.

predictions.json records the hash of the frozen bundle and of the compiled circuits it was made from, so it cannot be
adjusted afterwards without the hashes showing it. The real job is compiled again on the day and may land on other
qubits with other error rates; the analysis says which.

Nothing is submitted here. The compile step uses qiskit-ibm-runtime's offline copy of the device's wiring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from qiskit import qpy

HERE = Path(__file__).resolve().parent
APPLIED = HERE.parent
ROOT = APPLIED.parent
sys.path.insert(0, str(APPLIED))
sys.path.insert(0, str(HERE))

import exposure  # noqa: E402
import predict  # noqa: E402   applied/predict.py: the campaign's compile recipe and the noisy simulation
import study  # noqa: E402     applied/study.py: the saved runs and the comparison helper

BUNDLE = HERE / "hardware_bundle"
ISA = HERE / "predictions_isa.qpy"
OUT = HERE / "predictions.json"
REFERENCE_RUN = study.NEW_RUN            # "applied_v1", the 12 November job

# What the job is scored on. A rate is one circuit's answer; a difference is the first circuit minus the second.
CLAIMS = {
    "records: a failure is flagged, per shot (rewound)": ("rate", "dose-rewound", "fail"),
    "records: a failure is flagged, per shot (steered)": ("rate", "dose-steered", "fail"),
    "records: a failure is flagged, per shot (plain)": ("rate", "dose-plain", "fail"),
    "cause: the dose was low, after a failure (rewound)": ("rate", "dose-rewound", "dose_low_given_fail"),
    "cause: the dose was low, after a failure (steered)": ("rate", "dose-steered", "dose_low_given_fail"),
    "cause: the dose was low, after a failure (plain)": ("rate", "dose-plain", "dose_low_given_fail"),
    "what follows: neighbour dark after a failure, shared source minus none (rewound)":
        ("difference", "dose-rewound", "clean-rewound", "neighbour_dark_given_fail"),
    "what follows: neighbour dark after a failure, shared source minus none (steered)":
        ("difference", "dose-steered", "clean-steered", "neighbour_dark_given_fail"),
    "what follows: neighbour dark after a failure, shared source minus none (plain)":
        ("difference", "dose-plain", "clean-plain", "neighbour_dark_given_fail"),
    "check: the failed contact's own cell is dark (rewound)": ("rate", "dose-rewound", "cell_dark_given_fail"),
    "check: the failed contact's own cell is dark (steered)": ("rate", "dose-steered", "cell_dark_given_fail"),
    "check: the failed contact's own cell is dark (plain)": ("rate", "dose-plain", "cell_dark_given_fail"),
}

# Stated before the job. Each holds only if the job's 95% interval lies wholly on the stated side.
DIRECTIONS = {
    "cause": "After a failure the dose reads low more often than its 20% prior, in the plain, the steered and the rewound record.",
    "what follows": "After a failure the neighbour reads dark more often with the shared source than without it, in all three records.",
    "records": "The rewound circuit flags a failure in more than half of its shots, the plain circuit in fewer than one in ten.",
    "check": "The failed contact's own cell reads dark more often in the rewound record than in the plain one.",
}


def bundle() -> tuple[dict, list]:
    manifest = study.read_json(BUNDLE / "manifest.json")
    with open(BUNDLE / "logical.qpy", "rb") as handle:
        circuits = qpy.load(handle)
    return manifest, circuits


def reference():
    """The noise simulator, the 12 November job as saved, and the noise scale fitted to that job's echoes."""
    simulate = study.noise_tools()[0]
    run = study.saved_run(simulate, REFERENCE_RUN)
    scale = study.read_json(APPLIED / "results.json")["new_job"]["explained_afterwards"]["echo_scale"]
    return simulate, run, scale


def claims(rows: dict) -> dict:
    """The scored numbers, from one set of answers: {circuit: exposure.answers(...)}."""
    out = {}
    for key, (kind, *spec) in CLAIMS.items():
        if kind == "rate":
            circuit, quantity = spec
            out[key] = rows[circuit][quantity]
        else:
            first, second, quantity = spec
            out[key] = rows[first][quantity] - rows[second][quantity]
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(compiled: list) -> dict:
    simulate, run, scale = reference()
    manifest, _ = bundle()
    rows = {}
    for entry, isa in zip(manifest["circuits"], compiled):
        meta = entry["metadata"]
        row = {"two_qubit_gates": int(isa.count_ops().get("cz", 0)), "depth": int(isa.depth())}
        for label, s, readout in (("ideal", 0.0, False), ("calibration", 1.0, True), ("echo_scaled", scale, True)):
            distribution = predict.predicted(simulate, run, isa, s, readout)
            row[label] = ({"all_zero_return": float(distribution[0])} if meta["kind"] == "echo"
                          else exposure.answers(distribution, meta["model"]))
        rows[entry["name"]] = row
    exposures = [entry["name"] for entry in manifest["circuits"] if entry["metadata"]["kind"] == "contact"]
    folder = study.CAMPAIGN / "runs" / REFERENCE_RUN
    return {
        "schema": "ra-contact-predictions-v1",
        "made_before_the_job": True,
        "device_assumed": {"backend": run.raw["backend"], "physical_qubits": run.plan["physical_patch"][:4],
                           "echo_qubits": run.plan["physical_patch"][:7],
                           "calibration": run.properties["last_update_date"], "noise_scale_from_echoes": scale,
                           "readout": f"measured inside job {run.raw['job_id']}"},
        "model": "depolarizing gate errors at the reported rates times the echo-fitted scale, plus measured readout "
                 "errors; no idle decoherence, crosstalk, leakage or drift",
        "shots_planned": study.SHOTS,
        "rows": rows,
        "claims": {label: claims({name: rows[name][label] for name in exposures}) for label in ("ideal", "echo_scaled")},
        "directions": DIRECTIONS,
        "sha256": {"applied/contact/hardware_bundle/manifest.json": digest(BUNDLE / "manifest.json"),
                   "applied/contact/predictions_isa.qpy": digest(ISA),
                   f"hardware_campaign/runs/{REFERENCE_RUN}/raw.json": digest(folder / "raw.json"),
                   f"hardware_campaign/runs/{REFERENCE_RUN}/backend_properties.json": digest(folder / "backend_properties.json")},
        "caveat": "Made for the qubits and calibration the 12 November 2026 job met. The job is compiled again on the "
                  "day and may land on other qubits with other error rates. On 12 November this noise model was too "
                  "hopeful about the device.",
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
            raise SystemExit(f"applied/contact/predictions.json no longer matches its sources: {gap:.3g} at {where}")
        print(f"applied/contact/predictions.json reproduces from the saved compiled circuits (largest difference {gap:.1e}).")
        return
    if OUT.exists():
        raise SystemExit("applied/contact/predictions.json already exists. Predictions are written once.")
    _, run, _ = reference()
    _, circuits = bundle()
    compiled = predict.compile_on_patch(circuits, run.plan["physical_patch"])
    with open(ISA, "wb") as handle:
        qpy.dump(compiled, handle)
    result = build(compiled)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    show = lambda value: "    -  " if value is None else f"{100 * value:6.2f}%"  # noqa: E731
    for name, row in result["rows"].items():
        got = row["echo_scaled"]
        if "all_zero_return" in got:
            print(f"{name:14s} {row['two_qubit_gates']:4d} two-qubit gates   returns to zero in {show(got['all_zero_return'])}")
        else:
            print(f"{name:14s} {row['two_qubit_gates']:4d} two-qubit gates   failure flagged {show(got['fail'])}   dose low {show(got['dose_low_given_fail'])}"
                  f"   neighbour dark {show(got['neighbour_dark_given_fail'])}   cell dark {show(got['cell_dark_given_fail'])}")
    for key in CLAIMS:
        print(f"{key:86s} exact {show(result['claims']['ideal'][key])}   predicted {show(result['claims']['echo_scaled'][key])}")


if __name__ == "__main__":
    main()
