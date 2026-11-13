"""The contact toy read three ways: by hand, on a perfect device, and from the IBM job against its prediction.

    python applied/contact/analysis.py            recompute everything and write results.json
    python applied/contact/analysis.py --check    recompute and compare with the saved results.json

Everything is recomputed from saved files: the model in exposure.py, the frozen bundle, the prediction written before
the job, and the job's raw counts in hardware_campaign/runs/contact_v1. Nothing here contacts IBM.

The counts are raw: no readout correction, nothing pooled. A rate's 95% interval is a Wilson interval and a
difference's is Newcombe's. They cover shot noise only, not drift or calibration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
APPLIED = HERE.parent
ROOT = APPLIED.parent
sys.path.insert(0, str(APPLIED))
sys.path.insert(0, str(HERE))

import exposure  # noqa: E402
import forecast  # noqa: E402
import study  # noqa: E402     applied/study.py: intervals, the saved runs and the comparison helper

RUN = "contact_v1"
OUT = HERE / "results.json"


def exact() -> dict:
    """Bayes' rule by hand, and each circuit on a perfect device."""
    return {name: {"parameters": dict(model), "truth": exposure.truth(name),
                   "perfect_device": {build: exposure.ideal(name, build) for build in exposure.BUILDS}}
            for name, model in exposure.MODELS.items()}


def counted(weights, model_name: str) -> dict:
    """One circuit's counts as rates with intervals: the same quantities as exposure.answers()."""
    t = exposure.tally(weights)
    hidden = exposure.MODELS[model_name]["hidden_source"]
    return {"fail": study.rate(t["fail"], t["all"]),
            "cell_dark_given_fail": study.rate(t["fail_and_cell_dark"], t["fail"]),
            "neighbour_dark": study.rate(t["neighbour_dark"], t["all"]),
            "dose_low_given_fail": study.rate(t["fail_and_dose_low"], t["fail"]) if hidden else None,
            "neighbour_dark_given_fail": study.rate(t["fail_and_neighbour_dark"], t["fail"])}


def checked(weights: np.ndarray, model_name: str) -> dict:
    """The same answers among shots that also pass the model's own check: the flag is set AND the cell reads dark.

    Not part of the prediction. Looked at after the job, because the check turned out to matter.
    """
    index = np.arange(weights.size)
    bit = lambda q: ((index >> q) & 1) == 1  # noqa: E731
    kept = bit(exposure.FLAG) & bit(exposure.CELL)
    hidden = exposure.MODELS[model_name]["hidden_source"]
    return {"kept": study.rate(weights[kept].sum(), weights.sum()),
            "dose_low": study.rate(weights[kept & bit(exposure.SOURCE)].sum(), weights[kept].sum()) if hidden else None,
            "neighbour_dark": study.rate(weights[kept & bit(exposure.NEIGHBOUR)].sum(), weights[kept].sum())}


def scored(rows: dict, predictions: dict) -> dict:
    """Every claim of forecast.CLAIMS: measured with its interval, beside the prediction and the exact value."""
    out = {}
    for key, (kind, *spec) in forecast.CLAIMS.items():
        if kind == "rate":
            circuit, quantity = spec
            got = rows[circuit][quantity]
            entry = {"measured": got["probability"], "interval95": got["wilson95"], "records": got["of"]}
        else:
            first, second, quantity = spec
            got = study.difference(rows[first][quantity], rows[second][quantity])
            entry = {"measured": got["difference"], "interval95": got["interval95"],
                     "records": [rows[first][quantity]["of"], rows[second][quantity]["of"]]}
        entry["predicted"] = predictions["claims"]["echo_scaled"][key]
        entry["exact"] = predictions["claims"]["ideal"][key]
        low, high = entry["interval95"][0] - 1e-12, entry["interval95"][1] + 1e-12       # a rate of exactly 1 sits on the edge
        entry["prediction_inside_interval"] = bool(low <= entry["predicted"] <= high)
        entry["exact_inside_interval"] = bool(low <= entry["exact"] <= high)
        out[key] = entry
    return out


def directions(rows: dict) -> dict:
    """The four statements made before the job. Each holds only if its 95% interval lies wholly on the stated side."""
    prior = exposure.MODELS["dose"]["low_dose"]
    gap = lambda build, quantity: study.difference(rows[f"dose-{build}"][quantity], rows[f"clean-{build}"][quantity])  # noqa: E731
    check = study.difference(rows["dose-rewound"]["cell_dark_given_fail"], rows["dose-plain"]["cell_dark_given_fail"])
    parts = {
        "cause": {build: bool(rows[f"dose-{build}"]["dose_low_given_fail"]["wilson95"][0] > prior) for build in exposure.BUILDS},
        "what follows": {build: bool(gap(build, "neighbour_dark_given_fail")["interval95"][0] > 0) for build in exposure.BUILDS},
        "records": {"rewound over half": bool(rows["dose-rewound"]["fail"]["wilson95"][0] > 0.5),
                    "plain under a tenth": bool(rows["dose-plain"]["fail"]["wilson95"][1] < 0.1)},
        "check": {"rewound minus plain above zero": bool(check["interval95"][0] > 0)},
    }
    return {key: {"statement": statement, "parts": parts[key], "held": all(parts[key].values())}
            for key, statement in forecast.DIRECTIONS.items()}


def job(folder: Path | None = None) -> dict | None:
    """The job frozen in hardware_bundle/, read against the prediction written before it ran.

    Returns None until hardware_campaign/runs/contact_v1/raw.json exists.
    """
    folder = folder or study.CAMPAIGN / "runs" / RUN
    if not (folder / "raw.json").exists():
        return None
    raw, plan = study.read_json(folder / "raw.json"), study.read_json(folder / "plan.json")
    manifest = {c["name"]: c for c in study.read_json(forecast.BUNDLE / "manifest.json")["circuits"]}
    predictions = study.read_json(forecast.OUT)
    rows, filtered = {}, {}
    for row in raw["rows"]:
        if row["kind"] != "science":
            continue
        meta = manifest[row["name"]]["metadata"]
        counts = study.counts_vector(row)
        base = {"shots": row["shots"], "two_qubit_gates": row["gate_counts"].get("cz", 0)}
        if meta["kind"] == "echo":
            rows[row["name"]] = {**base, "all_zero_return": study.rate(counts[0], row["shots"])}
        else:
            rows[row["name"]] = {**base, **counted(counts, meta["model"])}
            filtered[row["name"]] = checked(counts, meta["model"])
    more = study.ratio(rows["dose-rewound"]["fail"], rows["dose-plain"]["fail"])
    claims = predictions["claims"]
    more["predicted"], more["exact"] = (
        claims[label]["records: a failure is flagged, per shot (rewound)"] / claims[label]["records: a failure is flagged, per shot (plain)"]
        for label in ("echo_scaled", "ideal"))
    return {"run": folder.name, "job_id": raw["job_id"], "backend": raw["backend"], "retrieved_utc": raw["retrieved_utc"],
            "quantum_seconds": raw["usage"], "physical_qubits": plan["physical_patch"],
            "predictions_assumed_qubits": predictions["device_assumed"]["physical_qubits"],
            "rows": rows, "claims": scored(rows, predictions), "directions": directions(rows),
            "flagged_shots_rewound_over_plain": more,
            "filtered_by_the_check": {
                "scope": "Not predicted. Looked at after the job: the same answers among shots where the flag is set and "
                         "the cell also reads dark, which the model requires of every real failure.",
                "rows": filtered,
                "neighbour_gap": {build: study.difference(filtered[f"dose-{build}"]["neighbour_dark"], filtered[f"clean-{build}"]["neighbour_dark"])
                                  for build in exposure.BUILDS}},
            "scope": "One job. Predictions were written and committed before it was submitted, for the qubits and "
                     "calibration the 12 November job met. Programmed models on superconducting qubits: no resist, "
                     "mask or wafer was measured.",
            "source_sha256": {f"hardware_campaign/runs/{folder.name}/raw.json": study.sha(folder / "raw.json"),
                              "applied/contact/predictions.json": study.sha(forecast.OUT)}}


def explained_afterwards(name: str = RUN) -> dict:
    """The returned job under the same noise model, now with its own qubits, calibration and echo circuits.

    An explanation made after the answers were known, not a prediction. The one fitted number is the scale that makes
    the model reproduce the job's two echo circuits; the answers themselves are not fitted.
    """
    simulate, run_study = study.noise_tools()
    run = study.saved_run(simulate, name)
    fit = run_study.fit_echo_scale(run)
    rows = {circuit: exposure.answers(simulate.simulate(run, circuit, scale=fit["scale"]), entry["metadata"]["model"])
            for circuit, entry in run.manifest.items() if entry["metadata"]["kind"] == "contact"}
    return {"made_after_the_job": True, "echo_scale": fit["scale"],
            "echoes": [{k: e[k] for k in ("circuit", "two_qubit_gates", "measured_return", "calibration_return", "echo_scaled_return")}
                       for e in fit["echoes"]],
            "calibration": run.properties["last_update_date"], "rows": rows, "claims": forecast.claims(rows)}


def build(noise: bool = True) -> dict:
    predictions = study.read_json(forecast.OUT)
    out = {"schema": "ra-contact-toy-v1",
           "question": "A contact failed to print, which is rare. Was the dose low, and is the neighbouring cell at risk?",
           "models": exact(),
           "predicted": {"device_assumed": predictions["device_assumed"], "claims": predictions["claims"],
                         "two_qubit_gates": {name: row["two_qubit_gates"] for name, row in predictions["rows"].items()}}}
    fresh = job()
    if fresh is not None:
        if noise:
            fresh["explained_afterwards"] = explained_afterwards()
        out["job"] = fresh
    out["limits"] = [
        "A toy with four qubits. Bayes' rule answers both questions by hand, and that is the reference. No speedup is "
        "claimed, and none is possible at this size.",
        "The cells are dark or bright. No photon counts, no blur, no resist chemistry, no mask, no wafer. Nothing here "
        "describes a real scanner.",
        "Rewinding runs a MODEL inside a quantum computer. It cannot rewind a real exposure.",
        "With the model's own check bit used as a filter, plain sampling's answers come back close to the rewound "
        "ones in this toy. What rewinding then adds on hardware is records per shot, not a different answer.",
        "A model worth asking this way is one too large to compute classically. The repository's 49-cell lithography "
        "circuit needs 389 qubits and, as built, up to about 3.4 million two-qubit gates per round; this job's largest "
        "toy circuit has 15. Closing that gap needs many qubits with far lower error rates, most likely "
        "error-corrected ones. That hardware does not exist today.",
        "One job on one device. The intervals are shot noise only.",
    ]
    return out


def compare(result: dict, saved: dict) -> tuple[float, str, float, str]:
    """Largest difference in the exact and counted parts, and separately in the part that goes through the noise simulator.

    The second kind includes one fitted scale rounded to four decimals, which may land on a neighbouring value on
    another machine. hardware_campaign/noise_model allows 2e-3 for the same reason.
    """
    def split(r: dict) -> tuple[dict, dict]:
        exact_part = dict(r)
        simulated = {}
        if "job" in exact_part:
            simulated["explained_afterwards"] = exact_part["job"].get("explained_afterwards")
            exact_part["job"] = {k: v for k, v in exact_part["job"].items() if k != "explained_afterwards"}
        return exact_part, simulated

    (exact_a, simulated_a), (exact_b, simulated_b) = split(result), split(saved)
    return (*study.worst_difference(exact_a, exact_b), *study.worst_difference(simulated_a, simulated_b))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="recompute and compare with the saved results.json")
    args = parser.parse_args()
    result = build()
    if args.check:
        gap, where, noisy_gap, noisy_where = compare(result, study.read_json(OUT))
        if gap > 1e-9:
            raise SystemExit(f"applied/contact/results.json no longer matches its sources: {gap:.3g} at {where}")
        if noisy_gap > 2e-3:
            raise SystemExit(f"applied/contact/results.json: the noise-model part differs by {noisy_gap:.3g} at {noisy_where}")
        print(f"applied/contact/results.json reproduces from the model and the saved IBM counts (largest difference {gap:.1e}; "
              f"noise-model part {noisy_gap:.1e}).")
        return
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")
    if "job" not in result:
        print("no job yet: the exact answers and the prediction only")
        return
    show = lambda value: f"{100 * value:6.2f}%"  # noqa: E731
    for key, c in result["job"]["claims"].items():
        print(f"{key:86s} exact {show(c['exact'])}  predicted {show(c['predicted'])}  measured {show(c['measured'])} "
              f"[{show(c['interval95'][0])}, {show(c['interval95'][1])}]  {'inside' if c['prediction_inside_interval'] else 'OUTSIDE'}")
    for key, d in result["job"]["directions"].items():
        print(f"{'held    ' if d['held'] else 'NOT HELD'} {key}: {d['statement']}  {d['parts']}")


if __name__ == "__main__":
    main()
