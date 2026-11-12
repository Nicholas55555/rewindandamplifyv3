"""Write lab/data.js: the measured IBM numbers the Lab displays, copied from the saved analyses.

Nothing is computed here beyond rounding-free copying and two ratios. Every value is read from a file that the
hardware campaign already hashes and verifies, and this script records the SHA-256 of each file it read so that
lab/test_data.cjs can confirm the Lab still shows exactly what was measured.

    python lab/make_data.py            # rewrite lab/data.js
    python lab/make_data.py --check    # fail if lab/data.js is stale

Standard library only. No IBM account, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = HERE / "data.js"
CAMPAIGN = ROOT / "hardware_campaign"
RUNS = {"precision": "original_precision_v1", "first": "original_plain_v2", "suppressed": "original_suppressed_v1"}
HERO = {"local": "click3-steered-memory+last-1-r1", "full": "click3-steered-full-r1"}
LOOPS = {
    "plain": ("loop-defect-r0", "loop-nodefect-r0"),
    "local": ("loop-defect-r1", "loop-nodefect-r1"),
    "full": ("loop-defect-full-r1", "loop-nodefect-full-r1"),
    "memory": ("loop-defect-memory-r1", "loop-nodefect-memory-r1"),
}


class Sources:
    """Reads files and remembers what it read."""

    def __init__(self) -> None:
        self.seen: dict[str, str] = {}

    def json(self, path: Path):
        data = path.read_bytes()
        self.seen[path.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
        return json.loads(data)


def history_row(row: dict) -> dict:
    """One measured 'click at step 3' circuit: how often it hit, and which histories the hits were."""
    o = row["observables"]
    return {
        "name": row["name"],
        "shots": row["shots"],
        "accepted": o["selected"]["successes"],
        "probability": o["selected"]["probability"],
        "wilson95": o["selected"]["wilson95"],
        "ideal_probability": o["logical_ideal_selected_probability"],
        "unsteered_probability": o["unsteered_selected_probability"],
        "two_qubit_gates": row["native_two_qubit_gate_count"],
        "depth": row["compiled_depth"],
        "duration_us": row["circuit_duration_seconds"] * 1e6,
        "logical_qubits": row["logical_qubits"],
        "tv_to_exact": o["selected_history_tv_to_unsteered_target"],
        "tv_to_ideal_circuit": o["selected_history_tv_to_logical_ideal"],
        "history_probabilities": o["history_probabilities"],
    }


def loop_row(row: dict) -> dict:
    """One measured after-click circuit: shots kept, and the click rate at steps 4, 5 and 6 among them."""
    out = history_row(row)
    del out["history_probabilities"]
    out["future"] = [{
        "step": f["step"],
        "probability": f["raw_or_secondary_conditional"]["probability"],
        "successes": f["raw_or_secondary_conditional"]["successes"],
        "kept": f["raw_or_secondary_conditional"]["shots"],
        "wilson95": f["raw_or_secondary_conditional"]["wilson95"],
        "exact": f["unsteered_target"],
        "ideal_circuit": f["logical_ideal_target"],
    } for f in o_future(row)]
    return out


def o_future(row: dict) -> list:
    return row["observables"]["future_clicks_after_selected_click"]


def build() -> bytes:
    src = Sources()
    summary = src.json(CAMPAIGN / "results.json")
    data = {
        "schema": 1,
        "what": "Raw counts from real IBM Quantum hardware running digital model circuits. No optical photons were detected.",
        "backend": summary["backend"],
        "campaign": {
            "date": "2026-11-11",
            "jobs": summary["jobs"],
            "science_circuits": summary["science_circuit_executions"],
            "calibration_circuits": summary["calibration_circuit_executions"],
            "total_shots": summary["total_shots"],
            "qpu_seconds": summary["actual_campaign_quantum_seconds"],
        },
        "jobs": [{"run": r["id"], "job_id": r["job_id"], "shots_per_circuit": r["shots_per_pub"],
                  "science_circuits": r["science_circuits"], "calibration_circuits": r["calibration_circuits"],
                  "qpu_seconds": r["actual_quantum_seconds"]} for r in summary["runs"]],
        "hero": {},
        "loops": {},
    }
    for label, run in RUNS.items():
        folder = CAMPAIGN / "runs" / run
        analysis = src.json(folder / "analysis.json")
        job = src.json(folder / "job.json")
        rows = {row["name"]: row for row in analysis["rows"]}
        hero = {key: history_row(rows[name]) for key, name in HERO.items()}
        for h in hero.values():
            h["gates_per_accepted_shot"] = h["two_qubit_gates"] * h["shots"] / h["accepted"]
        entry = {"run": run, "job_id": analysis["job_id"], "submitted_utc": job["submitted_utc"],
                 "shots": hero["local"]["shots"], **hero}
        contrast_path = folder / "hero_acceptance_contrast.json"
        if contrast_path.exists():
            contrast = src.json(contrast_path)
            assert contrast["first_name"] == HERO["local"] and contrast["second_name"] == HERO["full"]
            assert contrast["first"]["successes"] == hero["local"]["accepted"]
            assert contrast["second"]["successes"] == hero["full"]["accepted"]
            entry["difference"] = {"probability": contrast["probability_difference"],
                                   "interval95": contrast["independent_shot_wilson_based_interval95"]}
        data["hero"][label] = entry
        if label == "first":
            # every "click at step 3" build that ran in the full 2,048-shot suite, for the Lab's build switches
            data["variants"] = {name: {k: v for k, v in history_row(row).items() if k != "history_probabilities"}
                                for name, row in sorted(rows.items()) if name.startswith("click3-")}
        data["loops"][label] = {
            "run": run, "job_id": analysis["job_id"],
            "builds": {build: {"defect": loop_row(rows[pair[0]]), "no_defect": loop_row(rows[pair[1]])}
                       for build, pair in LOOPS.items()},
        }
    headline = summary["headline_original"]
    assert headline["job_id"] == data["hero"]["precision"]["job_id"]
    assert headline["local"]["accepted"] == data["hero"]["precision"]["local"]["accepted"] == 6300
    assert headline["full"]["accepted"] == data["hero"]["precision"]["full"]["accepted"] == 5674

    # The qualifying-round runs on ibm_kingston (5 November 2026), from the original project's own summary.
    numbers = src.json(ROOT / "rewindandamplify-main" / "results" / "numbers.json")["hardware"]
    data["kingston"] = {
        "backend": numbers["backend"], "date": "2026-11-05", "shots": numbers["shots"],
        "job_ids": {mode: job["job_id"] for mode, job in numbers["jobs"].items()},
        "builds": [{"question": h["question"], "build": h["build"], "name": h["name"], "two_qubit_gates": h["cz"],
                    "ideal": h["ideal_hit"], "noise_model_raw": h["model"]["hit_raw"],
                    "hardware_raw": h["plain"]["hit_raw"], "hardware_tv": h["plain"]["tvd"],
                    "suppressed_raw": h["suppressed"]["hit_raw"], "suppressed_tv": h["suppressed"]["tvd"]}
                   for h in numbers["hero"]],
    }
    data["source_sha256"] = dict(sorted(src.seen.items()))
    body = json.dumps(data, separators=(",", ":"), sort_keys=True)
    text = ("// Generated by lab/make_data.py from the saved hardware analyses. Do not edit by hand.\n"
            "(function(root){'use strict';var data=" + body + ";"
            "if(typeof module!=='undefined'&&module.exports)module.exports=data;else root.LAB_DATA=data;"
            "})(typeof globalThis!=='undefined'?globalThis:this);\n")
    return text.encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the checked-in file without rewriting it")
    args = parser.parse_args()
    output = build()
    if args.check:
        assert OUTPUT.read_bytes() == output, "Stale lab/data.js: run python lab/make_data.py"
    else:
        OUTPUT.write_bytes(output)
    print(json.dumps({"status": "verified" if args.check else "written", "file": "lab/data.js",
                      "bytes": len(output), "sha256": hashlib.sha256(output).hexdigest()}))


if __name__ == "__main__":
    main()
