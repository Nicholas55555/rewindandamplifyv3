"""Every headline number in the deck and the reports, computed from the saved results, in one file.

    python experiments/summarise.py        writes results/numbers.json and prints the scorecard against the predictions
"""

import glob
import json

from common import RESULTS, load, save

import numpy as np


def noisy(pattern: str) -> list:
    rows = []
    for f in sorted(glob.glob(str(RESULTS / pattern))):
        d = json.load(open(f, encoding="utf-8"))
        rows.extend({**row, "backend": d["backend"]} for row in d["rows"])
    return rows


def share(values) -> float:
    return float(np.mean(values)) if len(values) else float("nan")


def e4_numbers() -> dict:
    rows = noisy("e4_reflection/noisy_*.json")
    key = lambda x: (x["backend"], x["T"], x["question"], x["r"])  # noqa: E731
    full = {key(x): x for x in rows if x["reflection"] == "full"}
    mem = {key(x): x for x in rows if x["reflection"] == "memory"}
    out = {"devices": sorted({r["backend"] for r in rows})}
    for label, test in (("r1", lambda k: k[3] == 1), ("r2plus", lambda k: k[3] >= 2)):
        ks = [k for k in mem if test(k) and k in full]
        out[label] = {"cells": len(ks), "memory_hit_wins": share([mem[k]["hit"] >= full[k]["hit"] for k in ks]),
                      "memory_tvd_wins": share([mem[k]["tvd"] <= full[k]["tvd"] for k in ks]),
                      "gate_ratio": share([full[k]["cz"] / mem[k]["cz"] for k in ks])}
    return out


def e4b_numbers() -> dict:
    local = noisy("e4_reflection/local_noisy_*.json")
    base = noisy("e4_reflection/noisy_*.json")
    key = lambda x: (x["backend"], x["T"], x["r"])  # noqa: E731
    loc = {key(x): x for x in local if x["reflection"] == "memory+last-1"}
    others = [x for x in base + local if x["question"].startswith("click at")]
    full = {key(x): x for x in others if x["reflection"] == "full"}
    mem = {key(x): x for x in others if x["reflection"] == "memory"}
    ks_full = [k for k in loc if k in full and k[2] >= 2]
    ks_mem = [k for k in loc if k in mem and k[2] >= 2]
    return {"devices": sorted({x["backend"] for x in local}), "against_full": {
        "cells": len(ks_full), "hit_wins": share([loc[k]["hit"] >= full[k]["hit"] for k in ks_full]),
        "tvd_wins": share([loc[k]["tvd"] <= full[k]["tvd"] for k in ks_full]),
        "gate_ratio": share([full[k]["cz"] / loc[k]["cz"] for k in ks_full])},
        "against_memory": {"cells": len(ks_mem), "hit_wins": share([loc[k]["hit"] >= mem[k]["hit"] for k in ks_mem]),
                           "tvd_wins": share([loc[k]["tvd"] <= mem[k]["tvd"] for k in ks_mem])}}


def e5_numbers() -> dict:
    rows = noisy("e5_inside_loop/noisy_*.json")
    out = {"devices": sorted({x["backend"] for x in rows})}
    for model in ("one defect", "no defect"):
        plain = {x["backend"]: x for x in rows if x["model"] == model and x["r"] == 0}
        amp = {x["backend"]: x for x in rows if x["model"] == model and x["r"] == 1 and x.get("steer") is not None
               and x["reflection"] == "memory+last-1"}
        ks = [b for b in plain if b in amp]
        out[model] = {"devices": len(ks),
                      "rmse_plain": np.mean([plain[b]["rmse_at_chunk"] for b in ks], axis=0).tolist() if ks else [],
                      "rmse_amplified": np.mean([amp[b]["rmse_at_chunk"] for b in ks], axis=0).tolist() if ks else [],
                      "kept_plain": share([plain[b]["kept_per_chunk"] for b in ks]),
                      "kept_amplified": share([amp[b]["kept_per_chunk"] for b in ks]),
                      "cz_plain": share([plain[b]["cz"] for b in ks]), "cz_amplified": share([amp[b]["cz"] for b in ks]),
                      "devices_better_tau23": sum(all(amp[b]["rmse_at_chunk"][j] < plain[b]["rmse_at_chunk"][j] for j in (1, 2)) for b in ks)}

    # can 4,096 shots tell the machine with a defect from the one without? The separation of the two estimates, in standard errors
    def pick(model, backend, amplified):
        for x in rows:
            if x["model"] != model or x["backend"] != backend:
                continue
            if not amplified and x["r"] == 0:
                return x
            if amplified and x["r"] == 1 and x.get("steer") is not None and x["reflection"] == "memory+last-1":
                return x
        return None

    separation = {}
    for label, amplified in (("plain", False), ("amplified", True)):
        per_device = {}
        for b in out["devices"]:
            a, c = pick("one defect", b, amplified), pick("no defect", b, amplified)
            if a is None or c is None:
                continue
            z = []
            for j in range(3):
                pa, pc = a["conditional"][j], c["conditional"][j]
                se = np.sqrt(pa * (1 - pa) / a["kept_per_chunk"] + pc * (1 - pc) / c["kept_per_chunk"])
                z.append(abs(pa - pc) / se)
            per_device[b] = z
        separation[label] = {"per_device": per_device,
                             "mean_by_tau": np.mean(list(per_device.values()), axis=0).tolist() if per_device else []}
    out["separation_in_standard_errors_at_4096_shots"] = separation
    return out


def e7_numbers() -> dict:
    rows = noisy("e7_resilience/noisy_*.json")
    out = {"devices": sorted({x["backend"] for x in rows}), "by_T": {}}
    key = lambda x: (x["backend"], x["T"])  # noqa: E731
    book = {key(x): x for x in rows if x["build"] == "textbook"}
    fused = {key(x): x for x in rows if x["build"] == "steered+local"}
    ks = [k for k in fused if k in book]
    for T in sorted({x["T"] for x in rows}):
        out["by_T"][T] = {}
        for build in ("plain", "textbook", "local", "steered", "steered+local"):
            sel = [x for x in rows if x["T"] == T and x["build"] == build]
            if sel:
                out["by_T"][T][build] = {"r": sel[0]["r"], "cz_median": float(np.median([x["cz"] for x in sel])),
                                         "hit_median": float(np.median([x["hit"] for x in sel])),
                                         "hit_range": [float(min(x["hit"] for x in sel)), float(max(x["hit"] for x in sel))],
                                         "tvd_median": float(np.median([x["tvd"] for x in sel]))}
    out["cells"] = len(ks)
    out["gate_ratio"] = {"min": min(book[k]["cz"] / fused[k]["cz"] for k in ks) if ks else None,
                         "median": float(np.median([book[k]["cz"] / fused[k]["cz"] for k in ks])) if ks else None,
                         "max": max(book[k]["cz"] / fused[k]["cz"] for k in ks) if ks else None}
    out["fused_hit_wins"] = share([fused[k]["hit"] >= book[k]["hit"] for k in ks])
    out["fused_tvd_wins"] = share([fused[k]["tvd"] <= book[k]["tvd"] for k in ks])
    return out


def device_quality(names: list) -> dict:
    """Each device snapshot's median two-qubit error and readout error, as IBM reported them."""
    from qiskit_ibm_runtime import fake_provider

    out = {}
    for name in names:
        target = getattr(fake_provider, name)().target
        two = [v.error for v in target["cz"].values() if v is not None and v.error is not None]
        read = [v.error for v in target["measure"].values() if v is not None and v.error is not None]
        out[name] = {"two_qubit_error": float(np.median(two)), "readout_error": float(np.median(read))}
    return out


def trend(quality: dict) -> dict:
    """How the resilient build's lead over textbook changes with device quality, at T = 5."""
    rows = noisy("e7_resilience/noisy_*.json")
    out = {}
    for name, q in quality.items():
        pick = {r["build"]: r for r in rows if r["backend"] == name and r["T"] == 5}
        if "textbook" in pick and "steered+local" in pick:
            out[name] = {**q, "textbook_hit": pick["textbook"]["hit"], "resilient_hit": pick["steered+local"]["hit"],
                         "textbook_tvd": pick["textbook"]["tvd"], "resilient_tvd": pick["steered+local"]["tvd"]}
    return out


def main() -> None:
    e1 = load("e1_purify")
    e2 = load("e2_amplify")
    e3 = load("e3_scaling")
    e4 = load("e4_reflection", "noiseless.json")
    e5n = load("e5_inside_loop", "noiseless.json")
    e6 = load("e6_catalog")
    horizon = load("e7_resilience", "horizon.json")["rows"]
    wall = e3["wall"]
    T = wall["steps"]
    per_iteration = 2 * 4 * T + 2 * (2 + T)  # as in e3_scaling.py: two machine calls, and a generous oracle and reflection
    steered_cz = wall["steered_r"] * per_iteration + 4 * T

    numbers = {
        "e1": {"worst_amplitude_error": max(r["max_amplitude_error"] for r in e1["amplitude_rows"]), "chi2_p": e1["sampling"]["p_value"],
               "shots": e1["sampling"]["shots"]},
        "e2": e2["worst"],
        "e3": {"slopes": e3["sweep"]["slopes"], "bbht_over_known": e3["sweep"]["bbht_over_known"],
               "rarest": {k: e3["sweep"]["rows"][-2][k] for k in ("p", "rejection_calls", "amplified_calls", "r_peak")},
               "classical_growth_per_qubit": e3["classical_growth_per_qubit"],
               "classical_at_n2_ms_per_sample": 1e3 * next(r["seconds_per_sample"] for r in e3["classical"] if r["n_memory"] == 2),
               "classical_at_n11_build_s": e3["classical"][-1]["build_seconds"]},
        "wall": {"rejection_runs": wall["median_rejection_runs"], "r": wall["r_needed"], "calls": wall["amplified_calls"],
                 "steered_runs": wall["steered_rejection_runs"], "steered_r": wall["steered_r"], "steered_calls": wall["steered_calls"],
                 "steering_gain": wall["median_rejection_runs"] / wall["steered_rejection_runs"],
                 "grover_gain_after_steering": wall["steered_rejection_runs"] / wall["steered_calls"],
                 "total_gain": wall["median_rejection_runs"] / wall["steered_calls"],
                 "textbook_cz": wall["cz_total_estimate"], "steered_cz": steered_cz,
                 "textbook_error_budget": 1 / wall["cz_total_estimate"], "steered_error_budget": 1 / steered_cz},
        "e4_noiseless": e4["summary"],
        "e4_noisy": e4_numbers(),
        "e4b": e4b_numbers(),
        "e5": {"worst_full_error": e5n["worst_full_error"], **e5_numbers()},
        "e6": e6["accuracy"]["summary"],
        "e6_noisy": {x["backend"]: {r["r"]: r["measured"] for r in x["rows"]} for x in e6["noisy"]},
        "e6_cost_at_1024": e6["costs"][-1] if e6["costs"] else None,
        "e7": e7_numbers(),
        "horizon": {str(w): {"hit": [round(r["hit"], 3) for r in horizon if r["w"] == w and r["r"] == 2],
                             "tvd": [round(r["tvd"], 3) for r in horizon if r["w"] == w and r["r"] == 2],
                             "fidelity": [round(r["memory_fidelity"], 3) for r in horizon if r["w"] == w and r["r"] == 2]}
                    for w in (4, 6, 8, 10)},
    }
    numbers["devices"] = trend(device_quality(numbers["e7"]["devices"]))
    if (RESULTS / "hardware" / "comparison.json").exists():
        numbers["hardware"] = load("hardware", "comparison.json")
    save(".", numbers, "numbers.json")
    print(json.dumps(numbers, indent=1)[:6000])


if __name__ == "__main__":
    main()
