"""Simulator against hardware for the featured IBM Marrakesh circuits. Offline: no IBM account, no new jobs.

Three predictions are compared with the measured counts of the 8,192-shot run (job dbqb1ifv5hds73dfo310):

    ideal           the compiled circuit with no noise
    calibration     gate errors exactly as the device reported them (scale = 1), with the readout errors measured
                    by the calibration circuits inside the same job
    echo-scaled     the same model with every gate error multiplied by one number, fitted ONLY to the two echo
                    circuits (run the machine forwards and backwards; a perfect device returns all zeros)

The echo-scaled prediction is out of sample: the scale never sees the science circuits it is then asked to predict.

    python hardware_campaign/noise_model/run_study.py            # rewrite results.json (about a minute)
    python hardware_campaign/noise_model/run_study.py --check    # recompute and compare with the saved file
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from simulate import CAMPAIGN, ROOT, Run, observables, simulate, two_qubit_gates  # noqa: E402

RUN = "original_precision_v1"
ECHOES = ["echo-T3-x1", "echo-T5-x1"]
HERO = {"local": "click3-steered-memory+last-1-r1", "full": "click3-steered-full-r1"}
LOOPS = ["loop-defect-r0", "loop-nodefect-r0", "loop-defect-r1", "loop-nodefect-r1", "loop-defect-full-r1",
         "loop-nodefect-full-r1", "loop-defect-memory-r1", "loop-nodefect-memory-r1"]
OUTPUT = HERE / "results.json"


def wilson(successes: int, shots: int, z: float = 1.959963984540054) -> list[float]:
    p = successes / shots
    centre = (p + z * z / (2 * shots)) / (1 + z * z / shots)
    half = z * np.sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / (1 + z * z / shots)
    return [float(centre - half), float(centre + half)]


def fit_echo_scale(run: Run) -> dict:
    """One multiplier for every gate error, chosen so the model's echo returns match the measured ones."""
    measured = {name: observables(run, name, run.counts(name)[0])["all_zero_return"] for name in ECHOES}

    def loss(scale: float) -> float:
        return sum((observables(run, name, simulate(run, name, scale))["all_zero_return"] - measured[name]) ** 2
                   for name in ECHOES)

    lo, hi, golden = 0.5, 4.0, (np.sqrt(5) - 1) / 2            # the loss has a single minimum in this range
    a, b = hi - golden * (hi - lo), lo + golden * (hi - lo)
    fa, fb = loss(a), loss(b)
    for _ in range(26):
        if fa < fb:
            hi, b, fb = b, a, fa
            a = hi - golden * (hi - lo)
            fa = loss(a)
        else:
            lo, a, fa = a, b, fb
            b = lo + golden * (hi - lo)
            fb = loss(b)
    scale = round((lo + hi) / 2, 4)
    rows = []
    for name in ECHOES:
        gates = two_qubit_gates(run, name)
        row = {"circuit": name, "two_qubit_gates": gates, "measured_return": measured[name],
               "shots": run.counts(name)[1]}
        for label, s in (("calibration", 1.0), ("echo_scaled", scale)):
            row[label + "_return"] = observables(run, name, simulate(run, name, s))["all_zero_return"]
        row["measured_error_per_two_qubit_gate"] = 1 - measured[name] ** (1 / gates)
        row["calibration_error_per_two_qubit_gate"] = 1 - row["calibration_return"] ** (1 / gates)
        rows.append(row)
    return {"scale": scale, "echoes": rows,
            "meaning": "Multiplier on every reported gate error that best reproduces the two echo circuits. "
                       "It absorbs idle decoherence, crosstalk and drift, which the model does not represent."}


def compare(run: Run, circuit: str, scale: float) -> dict:
    measured, shots = run.counts(circuit)
    seen = observables(run, circuit, measured)
    row = {"circuit": circuit, "two_qubit_gates": two_qubit_gates(run, circuit), "shots": shots,
           "logical_qubits": run.pub(circuit)[1]["logical_qubits"], "measured": seen,
           "measured_hit_wilson95": wilson(round(seen["hit_rate"] * shots), shots)}
    for label, s, readout in (("ideal", 0.0, None), ("calibration", 1.0, "job"), ("echo_scaled", scale, "job"),
                              ("calibration_reported_readout", 1.0, "reported")):
        row[label] = observables(run, circuit, simulate(run, circuit, s, readout))
    return row


def build() -> dict:
    run = Run.load(RUN)
    fit = fit_echo_scale(run)
    scale = fit["scale"]
    hero = {key: compare(run, name, scale) for key, name in HERO.items()}
    loops = [compare(run, name, scale) for name in LOOPS]
    gap = {label: hero["local"][label]["hit_rate"] - hero["full"][label]["hit_rate"]
           for label in ("measured", "ideal", "calibration", "echo_scaled")}
    folder = CAMPAIGN / "runs" / RUN
    sources = {}
    for path in [folder / "plan.json", folder / "raw.json", folder / "backend_properties.json",
                 folder / run.plan["compiled_qpy_file"], ROOT / run.plan["bundle"] / "manifest.json",
                 HERE / "simulate.py", HERE / "run_study.py"]:
        sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema": "ra-noise-model-study-v1",
        "run": RUN, "job_id": run.raw["job_id"], "backend": run.raw["backend"],
        "calibration_snapshot": run.properties["last_update_date"],
        "model": "Depolarizing sx, x and cz errors at the reported average gate infidelities, exact rz, and per-qubit "
                 "readout assignment errors measured by this job's own all-zeros and all-ones circuits. No idle "
                 "decoherence, crosstalk, leakage or drift. Exact density-matrix probabilities, so no shot noise.",
        "readout_errors": {str(q): {"job": list(run.readout_errors(q, "job")), "reported": list(run.readout_errors(q, "reported"))}
                           for q in sorted({q for pub in run.plan["pubs"] if pub["kind"] == "science"
                                            for q in pub["measurement_physical_qubits"]})},
        "echo_fit": fit,
        "featured_pair": hero,
        "hit_rate_gap_local_minus_full": gap,
        "after_click": loops,

        "source_sha256": dict(sorted(sources.items())),
    }


def worst_difference(a, b, where: str = "") -> float:
    if isinstance(a, dict):
        assert a.keys() == b.keys(), where
        return max([worst_difference(a[k], b[k], f"{where}/{k}") for k in a] or [0.0])
    if isinstance(a, list):
        assert len(a) == len(b), where
        return max([worst_difference(x, y, f"{where}[{i}]") for i, (x, y) in enumerate(zip(a, b))] or [0.0])
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b)
    assert a == b, f"{where}: {a!r} != {b!r}"
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="recompute and compare with the saved results")
    args = parser.parse_args()
    fresh = build()
    if args.check:
        saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
        fresh_numbers = {k: v for k, v in fresh.items() if k != "source_sha256"}
        saved_numbers = {k: v for k, v in saved.items() if k != "source_sha256"}
        worst = worst_difference(fresh_numbers, saved_numbers)
        assert worst < 2e-6, f"saved results differ from a fresh run by {worst}"
        print(json.dumps({"status": "verified", "file": "hardware_campaign/noise_model/results.json",
                          "largest_difference": worst}))
        return
    OUTPUT.write_text(json.dumps(fresh, indent=1) + "\n", encoding="utf-8", newline="\n")
    hero = fresh["featured_pair"]
    print(f"echo-fitted gate-error scale: {fresh['echo_fit']['scale']}")
    for key in ("local", "full"):
        h = hero[key]
        print(f"{key:5s} {h['two_qubit_gates']:3d} gates  ideal {100 * h['ideal']['hit_rate']:.2f}%  "
              f"calibration {100 * h['calibration']['hit_rate']:.2f}%  echo-scaled {100 * h['echo_scaled']['hit_rate']:.2f}%  "
              f"measured {100 * h['measured']['hit_rate']:.2f}%   answer error: calibration {h['calibration']['answer_error_tv']:.3f}  "
              f"echo-scaled {h['echo_scaled']['answer_error_tv']:.3f}  measured {h['measured']['answer_error_tv']:.3f}")
    print("gap local - full (points):", {k: round(100 * v, 2) for k, v in fresh["hit_rate_gap_local_minus_full"].items()})


if __name__ == "__main__":
    main()
