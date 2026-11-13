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


def research(src: Sources) -> dict:
    """Saved results of the follow-up studies that the Lab's three research tabs quote. Copied, never recomputed."""
    # --- photons: equal brightness, unequal interference; published GaAs data; detector dead time
    dot = src.json(ROOT / "quantum_dot_bridge" / "results.json")
    trap = dot["classical_trap_pair_comparison"]
    shared, independent = trap[0], trap[-1]
    assert shared["switch_probability_between_endpoints"] == 0 and independent["switch_probability_between_endpoints"] == 0.5
    cases = {c["case"]: c for c in dot["benchmark_cases"]}
    different = cases["differential_detuning"]
    hom = src.json(ROOT / "quantum_dot_bridge" / "hom_analysis" / "results.json")
    fits = ROOT / "qrsm_photon_poc" / "followup" / "inference_results"
    ignored, aware = src.json(fits / "fixed_411101_dead1_fit0.json"), src.json(fits / "fixed_411101_dead1_fit1.json")
    photons = {
        "survival": shared["single_photon_survival_probability"],
        "marginals": shared["each_single_photon_marginal_offset_probabilities"],
        "overlap": {"shared": shared["conditional_overlap"], "independent": independent["conditional_overlap"]},
        "coincidence_per_attempt": {"shared": shared["coincidence_probability_per_excitation_pair"],
                                    "independent": independent["coincidence_probability_per_excitation_pair"]},
        "overlap_when_different": different["conditional_overlap"],
        "detuning_in_linewidths": different["differential_angular_detuning_per_s"] / dot["config"]["radiative_rate_per_s"],
        "trap": [{"switch_probability": t["switch_probability_between_endpoints"], "overlap": t["conditional_overlap"],
                  "coincidence_per_attempt": t["coincidence_probability_per_excitation_pair"]} for t in trap],
        "benchmark": [{"case": c["case"], "overlap": c["conditional_overlap"],
                       "coincidence_per_attempt": c["coincidence_probability_per_excitation_pair"]} for c in dot["benchmark_cases"]],
        "gaas": [{"separation_ns": case["excitation_separation_ns"], "visibility": case["primary"]["corrected_visibility"],
                  "interval95": mc["corrected"]["interval95"], "co_only": case["primary"]["co_only_corrected_visibility"]}
                 for case, mc in zip(hom["cases"], hom["monte_carlo"]["cases"])],
        "dead_time": {"ignored": ignored["joint_parameters"]["g_defect"], "modelled": aware["joint_parameters"]["g_defect"],
                      "truth": aware["generator_parameters"]["g_defect"]},
    }
    assert photons["marginals"] == independent["each_single_photon_marginal_offset_probabilities"] == [0.5, 0.5]
    families = src.json(CAMPAIGN / "results.json")["family_results"]
    pairs = {row["name"]: row for row in families["dot_frozen"] if row["run"] == "dots_plain_v1"}
    photons["on_ibm"] = {key: {"overlap": pairs[name]["observables"]["raw_swap_overlap_estimate"],
                               "interval95": pairs[name]["observables"]["raw_swap_overlap_interval95"],
                               "ideal": pairs[name]["observables"]["ideal_overlap"], "shots": pairs[name]["shots"],
                               "two_qubit_gates": pairs[name]["native_two_qubit_gate_count"], "qubits": pairs[name]["logical_qubits"]}
                         for key, name in (("shared", "frozen_pair_p0"), ("independent", "frozen_pair_p0.5"))}
    assert photons["on_ibm"]["shared"]["ideal"] == photons["overlap"]["shared"]
    assert photons["on_ibm"]["independent"]["ideal"] == photons["overlap"]["independent"]

    # --- chipmaking: exposure quality against dose, phase inspection, and the size of the full spatial query
    exposure = src.json(ROOT / "quantum_lithography_poc" / "exposure_followup" / "results.json")["cases"][1]
    methods = {}
    for key in ("noon", "phase_cycled", "phase_cycled_burst"):
        best = exposure["methods"][key]["best_threshold_accuracy"]
        methods[key] = {"cell_accuracy": best["guard_cell_accuracy"], "all_correct": best["all_guard_cells_correct_probability"],
                        "photons": best["sample_incident_photons"]}
    phase = src.json(ROOT / "quantum_lithography_poc" / "phase_inspection_followup" / "results.json")["cases"][1]
    budget = phase["budgets"]["equal_sample_photons"]
    spatial = src.json(ROOT / "finals-lithography" / "full_spatial_circuit" / "results.json")
    coverage = src.json(CAMPAIGN / "coverage.json")
    floor = spatial["circuits"][1]
    assert floor["qubits"] == spatial["circuits"][3]["qubits"]
    chips = {
        "threshold_events": exposure["setup"]["threshold_events"],
        "methods": methods,
        "phase": {key: {"rmse_rad": budget[key]["global"]["rmse_full_2pi_rad"], "wrong_branch": budget[key]["global"]["wrong_pi_branch_rate"],
                        "trials": budget[key]["global"]["repetitions"]} for key in ("coherent", "noon", "hybrid")},
        "full_query": {
            "cells": spatial["configuration"]["cells"], "qubits": floor["qubits"],
            "count_qubits": floor["metadata"]["data_qubits"], "score_qubits": floor["metadata"]["score_qubits"],
            "clean_qubits": floor["metadata"]["extra_clean_qubits"],
            "cx_upper_bound": {k: spatial["explicit_synthesis_costs"][k]["complete_one_round_generic_cx_constructive_upper_bound"]
                               for k in ("floor", "ceil")},
            "event_probability": spatial["bounds"][0]["finite_capped_integer_lattice_cdf"],
            "device_qubits": coverage["confirmed_device_qubits"],
        },
    }

    # --- lasers: catching a frequency step at an unknown time, with and without an atomic sensor
    sensor_dir = ROOT / "laser_sensor_viability" / "followup" / "main"
    sensor = src.json(sensor_dir / "results.json")
    traces = src.json(sensor_dir / "example_traces.json")
    scenarios = {s["id"]: s for s in sensor["scenarios"]}
    shown = {"nominal": "unseen_nominal_sessions", "short_coherence": "unseen_short_coherence",
             "shared_path": "common_sampled_path_changes"}
    monitors = ("classical", "quantum", "classical_quantum", "two_classical")
    lasers = {"config": {k: sensor["config"][k] for k in ("wavelength_nm", "atoms", "pulse_s", "dark_s", "cycle_s", "cycles", "t1_s", "t2_s")},
              "step_hz": abs(traces["unseen_nominal_sessions"]["amplitude_hz"]), "window_s": 32, "scenarios": {}}
    for key, scenario_id in shown.items():
        scenario, trace = scenarios[scenario_id], traces[scenario_id]
        observed = list(zip(*trace["observations"]))            # photodiode, receiver, receiver (fusion), atoms, second receiver
        lasers["scenarios"][key] = {
            "id": scenario_id, "records": scenario["records_per_class"],
            "monitors": {m: {"caught": scenario["methods"][m]["detection_within_32s"],
                             "false_alarm": scenario["methods"][m]["false_alarm_rate"],
                             "median_delay_s": scenario["methods"][m]["detected_only_delay_median_s"]} for m in monitors},
            # one stored record of this scenario, rounded to 0.0001 Hz for display
            "example": {
                "onset_s": trace["onset_cycle"], "nuisance_onset_s": trace["nuisance_onset_cycle"], "step_hz": trace["amplitude_hz"],
                "laser_hz": [round(v, 4) for v in trace["source_frequency_hz"]],
                "path_hz": [round(v, 4) for v in trace["common_path_hz"]],
                "receiver_hz": [round(v, 4) for v in observed[1]],
                "atoms_hz": [round(v, 4) for v in observed[3]],
                "atoms_excited": [round(v * sensor["config"]["atoms"]) for v in trace["atomic_excited_fraction"]],
                "score_times_s": [trace["score_end_time_s"][0], trace["score_end_time_s"][-1]],
                "scores": {m: [round(v / trace["thresholds"][m], 4) for v in trace["scores"][m]] for m in monitors},
                "first_alarm_s": {m: trace["first_alarm_s"][m] for m in monitors},
            },
        }
        assert len(trace["score_end_time_s"]) == len(trace["scores"]["classical"]) == 97
    atomic = {row["name"]: row for row in families["atomic"]}
    lasers["atomic_on_ibm"] = [{"detuning_hz": hz, "model": atomic[name]["observables"]["ideal_system_zero_probability"],
                                "measured": atomic[name]["observables"]["raw_system_zero_probability"],
                                "interval95": atomic[name]["observables"]["raw_system_zero_wilson95"], "shots": atomic[name]["shots"],
                                "qubits": atomic[name]["logical_qubits"], "two_qubit_gates": atomic[name]["native_two_qubit_gate_count"]}
                               for hz, name in ((-5, "atomic_d-5_Z"), (0, "atomic_d+0_Z"), (5, "atomic_d+5_Z"))]
    return {"photons": photons, "lasers": lasers, "chips": chips}


def applied(src: Sources) -> dict:
    """Our own machine asked the three fields' question (applied/). Copied from its saved results, never recomputed."""
    r = src.json(ROOT / "applied" / "results.json")
    predicted = src.json(ROOT / "applied" / "predictions.json")["comparisons"]["echo_scaled"]
    truth = {name: machine["truth"] for name, machine in r["machines"].items()}
    rows, model = r["ibm"]["rows"], r["noise_model"]["rows"]
    pair = ("defect", "clean")
    stat = lambda x: {k: x[k] for k in ("probability", "successes", "of", "wilson95")}  # noqa: E731
    out = {
        "event": truth["defect"]["event"], "window_steps": r["window_steps"],
        "jobs": sorted({row["job_id"] for row in rows.values()}),
        "another": {
            "exact": {k: truth[k]["another"] for k in ("defect", "clean", "stepped")},
            "ibm": {how: {k: stat(rows[f"window/{k}/{how}"]["another"]) for k in pair} for how in ("plain", "rewound")},
            "records": {how: {k: rows[f"window/{k}/{how}"]["event"]["successes"] for k in pair} for how in ("plain", "rewound")},
            "shots": rows["window/defect/rewound"]["shots"],
            "clean_minus_defect": {"exact": truth["clean"]["another"] - truth["defect"]["another"],
                                   **r["ibm"]["clean_minus_defect_another"]},
            "noise_model": {how: {k: model[f"window/{k}/{how}"]["another"] for k in pair} for how in ("plain", "rewound")},
        },
        "pairs": {"one_in_runs": r["readings"]["chipmaking"]["one_pair_in_runs"],
                  "rarer_by": r["readings"]["chipmaking"]["defect_makes_pairs_rarer_by"]},
        "cause": {
            "exact": {"after_event": truth["defect"]["defect_after_event"], "typical": truth["defect"]["defect_typical"]},
            "ibm": {how: stat(rows[f"cause/defect/{how}"]["defect_after_event"]) for how in ("plain", "steered", "rewound")},
            "emitter_after_event": {how: rows[f"cause/defect/{how}"]["emitter_after_event"]["probability"]
                                    for how in ("plain", "steered", "rewound")},
            "noise_model": model["cause/defect/rewound"]["defect_after_event"],
        },
        "g2": {"exact": {k: truth[k]["g2"] for k in pair}, "ibm": r["ibm"]["g2"]},
        "frequency_step": {
            "before": truth["defect"]["another"], "after": truth["stepped"]["another"],
            "predicted_gain": predicted["lasers: second event, stepped minus defect (rewound)"],
            "records_needed": r["readings"]["lasers"]["records_needed_per_side"],
            "model_runs": r["readings"]["lasers"]["model_runs_needed"],
        },
        "predicted_clean_minus_defect": {how: predicted[f"chipmaking: second event, clean minus defect ({how})"]
                                         for how in ("plain", "rewound")},
        "new_job": None,
    }
    fresh = r.get("new_job")
    if fresh:
        window = lambda machine, how: stat(fresh["rows"][f"window-{machine}-{how}"]["another"])  # noqa: E731
        out["new_job"] = {
            "job_id": fresh["job_id"], "backend": fresh["backend"], "quantum_seconds": fresh["quantum_seconds"],
            "another": {how: {k: window(k, how) for k in ("defect", "clean", "stepped")} for how in ("plain", "rewound")},
            "comparisons": fresh["comparisons"],
            "cause": {how: stat(v["measured"]) for how, v in fresh["cause"].items()},
            "g2": fresh["g2"],
        }
    return out


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
    # The offline noise-model study of the same compiled circuits (hardware_campaign/noise_model).
    study = src.json(CAMPAIGN / "noise_model" / "results.json")
    assert study["job_id"] == data["hero"]["precision"]["job_id"]
    data["noise_model"] = {
        "gate_error_scale": study["echo_fit"]["scale"],
        "echoes": [{"two_qubit_gates": e["two_qubit_gates"], "measured_return": e["measured_return"],
                    "calibration_return": e["calibration_return"], "echo_scaled_return": e["echo_scaled_return"]}
                   for e in study["echo_fit"]["echoes"]],
        "gap": study["hit_rate_gap_local_minus_full"],
    }
    for key in ("local", "full"):
        row = study["featured_pair"][key]
        assert round(row["measured"]["hit_rate"] * row["shots"]) == data["hero"]["precision"][key]["accepted"]
        data["noise_model"][key] = {label: {"hit_rate": row[label]["hit_rate"], "answer_error_tv": row[label]["answer_error_tv"]}
                                    for label in ("ideal", "calibration", "echo_scaled")}
    data["noise_model"]["after_click_step6"] = {
        row["circuit"]: {label: row[label]["later_click_rates"][2] for label in ("ideal", "calibration", "echo_scaled", "measured")}
        for row in study["after_click"]}
    data["research"] = research(src)
    data["applied"] = applied(src)
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
