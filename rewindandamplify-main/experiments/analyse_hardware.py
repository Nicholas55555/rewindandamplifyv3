"""Turn raw device counts into results: hit rates, conditional distributions, the after-click fingerprint, the noise.

It reads every results/hardware/raw_*.json, from real jobs and from local dry runs alike, and scores each circuit
against its noiseless answer, computed fresh from the same logical circuit.

    python experiments/analyse_hardware.py
"""

import glob
import json
from pathlib import Path

from common import RESULTS, save

import numpy as np
from qiskit.quantum_info import Statevector, hellinger_fidelity
from scipy.stats import spearmanr

from qrsm_grover.classical import conditional_distribution, total_variation
from qrsm_grover.hardware import NONE, ONE, readout_correct, suite
from qrsm_grover.predicates import any_click, click_at
from qrsm_grover.queries import exact_after_click
from qrsm_grover.search import demo_catalog

OUT = "hardware"


def to_distribution(counts: dict, n_bits: int) -> np.ndarray:
    d = np.zeros(2 ** n_bits)
    for bits, c in counts.items():
        d[int(bits.replace(" ", ""), 2)] += c
    return d / d.sum()


def device_flip_rates(calibration: dict) -> dict:
    """Each physical qubit's readout error rates, from the all-zeros and all-ones circuits."""
    if "flip_rates" in calibration:  # a simulation already knows its own readout errors
        return {q: tuple(rates) for q, rates in zip(calibration["qubits"], calibration["flip_rates"])}
    zeros, ones = calibration["counts"]
    rates = {}
    for i, qubit in enumerate(calibration["qubits"]):
        flips = []
        for counts, wrong in ((zeros, 1), (ones, 0)):
            total = sum(counts.values())
            flips.append(sum(c for bits, c in counts.items() if (int(bits.replace(" ", ""), 2) >> i) & 1 == wrong) / total)
        rates[qubit] = tuple(flips)
    return rates


def model_of(meta: dict):
    return ONE if meta.get("k", 1) == 1 else NONE


def question_mask(meta: dict) -> np.ndarray:
    T = meta["T"]
    return (any_click() if meta["question"] == "any click" else click_at(T)).mask(T)


def score_history(meta: dict, measured: np.ndarray, ideal: np.ndarray) -> dict:
    model = model_of(meta)
    T, n = meta["T"], model.n_memory
    mask = question_mask(meta)
    values = np.arange(measured.size)
    histories = (values >> n) & (2 ** T - 1)
    hist = np.bincount(histories, weights=measured, minlength=2 ** T)
    hist_ideal = np.bincount(histories, weights=ideal, minlength=2 ** T)
    exact = conditional_distribution(model.history_probabilities(T), mask)
    hit = float(hist[mask].sum())
    return {"hit": hit, "ideal_hit": float(hist_ideal[mask].sum()), "tvd": total_variation(np.where(mask, hist, 0) / max(hit, 1e-12), exact),
            "ideal_tvd": total_variation(conditional_distribution(hist_ideal, mask), exact)}


def score_loop(meta: dict, measured: np.ndarray) -> dict:
    model = model_of(meta)
    n, t0, tau, width = model.n_memory, meta["t0"], meta["tau"], meta["width"]
    values = np.arange(measured.size)
    kept = ((values >> (n + t0 - 1)) & 1) == 1
    base = width - tau
    weight = float(measured[kept].sum())
    conditional = np.array([measured[kept & (((values >> (base + j)) & 1) == 1)].sum() / max(weight, 1e-12) for j in range(tau)])
    exact = exact_after_click(model, t0, tau)
    return {"kept": weight, "conditional": conditional, "exact": exact["conditional"],
            "error": float(np.abs(conditional - exact["conditional"]).max())}


def score_catalog(meta: dict, measured: np.ndarray, ideal: np.ndarray) -> dict:
    from qrsm_grover.search import classical_scores, tokenise, tokens_of

    catalog = demo_catalog(meta["N"])
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    scores = classical_scores(catalog, tokenise(meta["query"], vocabulary))
    target = int(np.argmax(scores))
    return {"target": catalog[target], "hit": float(measured[target]), "ideal_hit": float(ideal[target]),
            "distribution": measured, "ideal_distribution": ideal}


def analyse(path: Path, ideals: dict) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    device_rates = device_flip_rates(raw["calibration"])
    rows = []
    for item in raw["experiments"]:
        name, meta = item["name"], item["meta"]
        n_bits = item["logical_qubits"]
        measured = to_distribution(item["counts"], n_bits)
        ideal = ideals[name]
        rates = [device_rates[q] for q in item["physical_qubits"]]
        corrected = readout_correct(measured, rates)
        row = {"name": name, "meta": meta, "two_qubit_gates": item["two_qubit_gates"], "depth": item["depth"],
               "estimated_success": item["estimated_success"], "physical_qubits": item["physical_qubits"],
               "fidelity_raw": float(hellinger_fidelity(dict(enumerate(measured)), dict(enumerate(ideal)))),
               "fidelity_corrected": float(hellinger_fidelity(dict(enumerate(corrected)), dict(enumerate(ideal))))}
        if meta["kind"] == "history":
            row["raw"] = score_history(meta, measured, ideal)
            row["corrected"] = score_history(meta, corrected, ideal)
        elif meta["kind"] == "loop":
            row["raw"] = score_loop(meta, measured)
            row["corrected"] = score_loop(meta, corrected)
        elif meta["kind"] == "catalog":
            row["raw"] = score_catalog(meta, measured, ideal)
            row["corrected"] = score_catalog(meta, corrected, ideal)
        elif meta["kind"] == "echo":
            row["raw"] = {"return": float(measured[0])}
            row["corrected"] = {"return": float(corrected[0])}
        rows.append(row)
    return {"meta": raw["meta"], "rows": rows}


def table(result: dict) -> str:
    lines = [f"### {result['meta'].get('backend')}: {result['meta'].get('mode')} ({result['meta'].get('suppression')})", "",
             "| circuit | 2q gates | hit, ideal | hit, measured | hit, readout-corrected | conditional TVD | fidelity |",
             "|---|---|---|---|---|---|---|"]
    for row in result["rows"]:
        kind = row["meta"]["kind"]
        if kind == "history":
            lines.append(f"| {row['name']} | {row['two_qubit_gates']} | {row['raw']['ideal_hit']:.3f} | {row['raw']['hit']:.3f} | "
                         f"{row['corrected']['hit']:.3f} | {row['corrected']['tvd']:.3f} | {row['fidelity_corrected']:.3f} |")
        elif kind == "catalog":
            lines.append(f"| {row['name']} | {row['two_qubit_gates']} | {row['raw']['ideal_hit']:.3f} | {row['raw']['hit']:.3f} | "
                         f"{row['corrected']['hit']:.3f} | | {row['fidelity_corrected']:.3f} |")
        elif kind == "loop":
            lines.append(f"| {row['name']} | {row['two_qubit_gates']} | exact {np.round(row['raw']['exact'], 3).tolist()} | "
                         f"{np.round(row['raw']['conditional'], 3).tolist()} | {np.round(row['corrected']['conditional'], 3).tolist()} | "
                         f"kept {row['raw']['kept']:.3f} | {row['fidelity_corrected']:.3f} |")
        elif kind == "echo":
            lines.append(f"| {row['name']} | {row['two_qubit_gates']} | 1.000 | {row['raw']['return']:.3f} | "
                         f"{row['corrected']['return']:.3f} | | |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------- real device against simulators

HERO = (("T = 3", "plain sampling", "click3-full-r0"), ("T = 3", "textbook Grover, r = 3", "click3-full-r3"),
        ("T = 3", "local reflection, r = 3", "click3-memory+last-1-r3"), ("T = 3", "steer + textbook reflection", "click3-steered-full-r1"),
        ("T = 3", "steer + local (resilient)", "click3-steered-memory+last-1-r1"),
        ("T = 5", "plain sampling", "click5-full-r0"), ("T = 5", "local reflection, r = 3", "click5-memory+last-1-r3"),
        ("T = 5", "steer + textbook reflection", "click5-steered-full-r1"), ("T = 5", "steer + local (resilient)", "click5-steered-memory+last-1-r1"))


def by_name(result: dict) -> dict:
    return {row["name"]: row for row in result["rows"]}


def standard_error(p: float, shots: int) -> float:
    return float(np.sqrt(max(p * (1 - p), 0.0) / shots))


def hero_table(sources: dict, shots: int) -> list:
    out = []
    for question, label, name in HERO:
        row = {"question": question, "build": label, "name": name}
        for tag, result in sources.items():
            item = by_name(result)[name]
            row["cz"] = item["two_qubit_gates"]
            row["ideal_hit"] = item["raw"]["ideal_hit"]
            row[tag] = {"hit": item["corrected"]["hit"], "hit_raw": item["raw"]["hit"], "tvd": item["corrected"]["tvd"],
                        "se": standard_error(item["corrected"]["hit"], shots)}
        out.append(row)
    return out


def coherence_curves(sources: dict) -> dict:
    """Hit rate against r, for the two textbook series."""
    out = {}
    for group, prefix in (("no defect, any click", "any3-nodefect-full"), ("one defect, click at step 3", "click3-full")):
        names = [f"{prefix}-r{r}" for r in range(4)]
        first = next(iter(sources.values()))
        out[group] = {"ideal": [by_name(first)[n]["raw"]["ideal_hit"] for n in names],
                      "cz": [by_name(first)[n]["two_qubit_gates"] for n in names],
                      **{tag: [by_name(result)[n]["corrected"]["hit"] for n in names] for tag, result in sources.items()}}
    return out


def fingerprint(sources: dict, shots: int) -> dict:
    """Can a run tell the machine with a hidden defect from the one without? Same arithmetic as E5, on the same 3 tau."""
    out = {}
    for tag, result in sources.items():
        rows = by_name(result)
        out[tag] = {}
        for label, r in (("plain", 0), ("amplified", 1)):
            a, c = rows[f"loop-defect-r{r}"]["corrected"], rows[f"loop-nodefect-r{r}"]["corrected"]
            na, nc = a["kept"] * shots, c["kept"] * shots
            z = []
            for pa, pc in zip(a["conditional"], c["conditional"]):
                se = np.sqrt(pa * (1 - pa) / max(na, 1) + pc * (1 - pc) / max(nc, 1))
                z.append(float(abs(pa - pc) / se) if se > 0 else 0.0)
            out[tag][label] = {"defect": list(a["conditional"]), "no_defect": list(c["conditional"]), "exact_defect": list(a["exact"]),
                               "exact_no_defect": list(c["exact"]), "kept_defect": a["kept"], "kept_no_defect": c["kept"],
                               "shots_defect": na, "shots_no_defect": nc, "separation": z}
    return out


def catalog_table(sources: dict) -> dict:
    out = {}
    for tag, result in sources.items():
        rows = by_name(result)
        out[tag] = []
        for r in (0, 1, 2):
            item = rows[f"catalog-r{r}"]
            dist = np.array(item["corrected"]["distribution"])
            target = int(np.argmax(np.array(item["corrected"]["ideal_distribution"])))
            out[tag].append({"r": r, "cz": item["two_qubit_gates"], "ideal": item["corrected"]["ideal_hit"], "hit": item["corrected"]["hit"],
                             "hit_raw": item["raw"]["hit"], "target_is_top": bool(int(np.argmax(dist)) == target)})
    return out


def echo_table(sources: dict, reported: float | None) -> dict:
    """Each echo returns to all zeros on perfect hardware. The shortfall, spread over its gates, is an all-in error per gate."""
    out = {"reported_two_qubit_error": reported}
    for tag, result in sources.items():
        rows = [r for r in result["rows"] if r["meta"]["kind"] == "echo"]
        out[tag] = [{"name": r["name"], "cz": r["two_qubit_gates"], "return": r["corrected"]["return"], "return_raw": r["raw"]["return"],
                     "error_per_gate": float(1 - r["corrected"]["return"] ** (1 / r["two_qubit_gates"]))} for r in rows]
    return out


def history_rows(result: dict) -> list:
    return [r for r in result["rows"] if r["meta"]["kind"] == "history"]


def against(result: dict, other: dict) -> dict:
    """How two sources differ, circuit by circuit, on hit-rate error, conditional TVD and fidelity. `other` is the challenger."""
    rows, rival = history_rows(result), by_name(other)
    hit = lambda row: abs(row["corrected"]["hit"] - row["corrected"]["ideal_hit"])  # noqa: E731
    deep = [r for r in rows if r["two_qubit_gates"] >= 100]
    amplified = [r for r in rows if r["meta"]["r"] >= 1]

    def summary(subset: list) -> dict:
        return {"circuits": len(subset),
                "hit_error_improved": float(np.mean([hit(rival[r["name"]]) < hit(r) for r in subset])),
                "tvd_improved": float(np.mean([rival[r["name"]]["corrected"]["tvd"] < r["corrected"]["tvd"] for r in subset])),
                "fidelity_improved": float(np.mean([rival[r["name"]]["fidelity_corrected"] > r["fidelity_corrected"] for r in subset])),
                "median_hit_error": [float(np.median([hit(r) for r in subset])), float(np.median([hit(rival[r["name"]]) for r in subset]))],
                "median_tvd": [float(np.median([r["corrected"]["tvd"] for r in subset])),
                               float(np.median([rival[r["name"]]["corrected"]["tvd"] for r in subset]))],
                "median_fidelity": [float(np.median([r["fidelity_corrected"] for r in subset])),
                                    float(np.median([rival[r["name"]]["fidelity_corrected"] for r in subset]))]}

    return {"all": summary(rows), "amplified": summary(amplified), "deep": summary(deep) if deep else None}


def model_gap(model: dict, device: dict) -> dict:
    """How far the real device falls short of the noise model built from its own reported errors."""
    rows = [r for r in history_rows(model) if r["corrected"]["ideal_hit"] >= 0.5]
    rival = by_name(device)
    gaps = [r["corrected"]["hit"] - rival[r["name"]]["corrected"]["hit"] for r in rows]
    every = history_rows(model)
    return {"circuits": len(rows), "median_shortfall": float(np.median(gaps)), "share_below_model": float(np.mean([g > 0 for g in gaps])),
            "rank_correlation": float(spearmanr([r["corrected"]["hit"] for r in every], [rival[r["name"]]["corrected"]["hit"] for r in every]).statistic),
            "rms_hit_difference": float(np.sqrt(np.mean([(r["corrected"]["hit"] - rival[r["name"]]["corrected"]["hit"]) ** 2 for r in every])))}


def fidelity_decay(result: dict) -> dict:
    """Fidelity against two-qubit gates: the slope of log fidelity is an effective error per gate."""
    rows = history_rows(result)
    x = np.array([r["two_qubit_gates"] for r in rows], float)
    y = np.log(np.maximum([r["fidelity_corrected"] for r in rows], 1e-6))
    slope, intercept = np.polyfit(x, y, 1)
    return {"slope_per_gate": float(-slope), "intercept": float(np.exp(intercept)),
            "points": [[int(a), float(np.exp(b))] for a, b in zip(x, y)]}


def run_row(tag: str, result: dict) -> dict:
    """One real job's key numbers."""
    rows = by_name(result)
    meta = result["meta"]
    point = lambda name: {"hit": rows[name]["corrected"]["hit"], "tvd": rows[name]["corrected"]["tvd"], "cz": rows[name]["two_qubit_gates"]}  # noqa: E731
    fp = fingerprint({tag: result}, int(meta["shots"]))[tag]
    return {"backend": meta["backend"], "job_id": meta.get("job_id"), "qpu_seconds": meta.get("qpu_seconds"),
            "t3_resilient": point("click3-steered-memory+last-1-r1"), "t3_textbook": point("click3-full-r3"),
            "t5_resilient": point("click5-steered-memory+last-1-r1"), "t5_textbook": point("click5-steered-full-r1"),
            "no_defect_curve": [rows[f"any3-nodefect-full-r{r}"]["corrected"]["hit"] for r in range(4)],
            "catalog_r2": rows["catalog-r2"]["corrected"]["hit"],
            "echo_error_per_gate": [float(1 - r["corrected"]["return"] ** (1 / r["two_qubit_gates"])) for r in result["rows"] if r["meta"]["kind"] == "echo"],
            "fidelity_slope": fidelity_decay(result)["slope_per_gate"], "median_tvd": float(np.median([r["corrected"]["tvd"] for r in history_rows(result)])),
            "after_click": {"defect": fp["amplified"]["defect"], "no_defect": fp["amplified"]["no_defect"],
                            "separation": fp["amplified"]["separation"], "plain_sampling_separation": fp["plain"]["separation"],
                            "signed_tau3": float(fp["amplified"]["no_defect"][2] - fp["amplified"]["defect"][2])}}


def score_followups(runs: dict, primary: str) -> list:
    """Score the follow-up predictions in docs/design_log.md, committed before the follow-up jobs were sent."""
    if "plain2" not in runs:
        return []
    first, again = runs["plain"], runs["plain2"]
    out = []

    def add(key: str, text: str, measured: str, verdict: str) -> None:
        out.append({"id": key, "prediction": text, "measured": measured, "verdict": verdict})

    gaps = [abs(first[k]["hit"] - again[k]["hit"]) for k in ("t3_resilient", "t3_textbook")]
    add("F1", "A second plain run repeats both T = 3 hit rates to within 0.05",
        f"resilient {first['t3_resilient']['hit']:.3f} then {again['t3_resilient']['hit']:.3f}; textbook {first['t3_textbook']['hit']:.3f} then {again['t3_textbook']['hit']:.3f}",
        "held" if max(gaps) <= 0.05 else "partly" if max(gaps) <= 0.1 else "missed")

    z = again["after_click"]["separation"][2]
    right_way = again["after_click"]["signed_tau3"] > 0
    add("F2", "The repeat again puts no defect above defect at tau = 3, by at least 3 standard errors", f"{z:.1f} standard errors, {'the right way' if right_way else 'the wrong way'} round",
        "held" if right_way and z >= 3 else "partly" if right_way and z >= 1 else "missed")

    if "dd" in runs and "twirl" in runs:
        zd, zt = (runs[k]["after_click"]["separation"][2] * (1 if runs[k]["after_click"]["signed_tau3"] > 0 else -1) for k in ("dd", "twirl"))
        add("F3", "Twirling, not DD, is what erases the separation: DD alone keeps at least 3 standard errors, and twirling alone doesn't",
            f"DD alone {zd:.1f}, twirling alone {zt:.1f}", "held" if zd >= 3 > zt else "partly" if zd > zt else "missed")

    other = next((r for r in runs.values() if r["backend"] != primary), None)
    if other:
        wins = [other["t3_resilient"]["hit"] > other["t3_textbook"]["hit"], other["t3_resilient"]["tvd"] < other["t3_textbook"]["tvd"],
                other["t5_resilient"]["hit"] > other["t5_textbook"]["hit"], other["t5_resilient"]["tvd"] < other["t5_textbook"]["tvd"]]
        add("F4", f"A second chip: steer + local beats its rival on hit rate and TVD at T = 3 and T = 5, on {other['backend']}",
            f"T = 3: {other['t3_resilient']['hit']:.3f} vs {other['t3_textbook']['hit']:.3f}, TVD {other['t3_resilient']['tvd']:.3f} vs {other['t3_textbook']['tvd']:.3f}; "
            f"T = 5: {other['t5_resilient']['hit']:.3f} vs {other['t5_textbook']['hit']:.3f}, TVD {other['t5_resilient']['tvd']:.3f} vs {other['t5_textbook']['tvd']:.3f}",
            "held" if all(wins) else "partly" if any(wins) else "missed")
        hit = other["t3_resilient"]["hit"]
        add("F5", "A second chip: steer + local reaches at least 0.70 at T = 3", f"{hit:.3f}", "held" if hit >= 0.7 else "partly" if hit >= 0.55 else "missed")
    moved = runs.get("plain_marrakesh2")
    if moved:
        worst = max(moved["echo_error_per_gate"])
        add("F6", "Off qubits 5, 6, 7, 8 and 17, the echo's all-in error per two-qubit gate on ibm_marrakesh falls below 1%, from 1.5% to 3.4%",
            ", ".join(f"{g:.2%}" for g in moved["echo_error_per_gate"]), "held" if worst < 0.01 else "partly" if worst < 0.015 else "missed")
        wins = [moved["t3_resilient"]["hit"] > moved["t3_textbook"]["hit"], moved["t3_resilient"]["tvd"] < moved["t3_textbook"]["tvd"],
                moved["t5_resilient"]["hit"] > moved["t5_textbook"]["hit"], moved["t5_resilient"]["tvd"] < moved["t5_textbook"]["tvd"]]
        tight = moved["t3_resilient"]["tvd"] <= 0.15
        add("F7", "Off those qubits, steer + local beats its rival on hit rate and TVD at T = 3 and T = 5, with TVD at T = 3 of 0.15 or less",
            f"T = 3: {moved['t3_resilient']['hit']:.3f} vs {moved['t3_textbook']['hit']:.3f}, TVD {moved['t3_resilient']['tvd']:.3f} vs {moved['t3_textbook']['tvd']:.3f}; "
            f"T = 5: {moved['t5_resilient']['hit']:.3f} vs {moved['t5_textbook']['hit']:.3f}, TVD {moved['t5_resilient']['tvd']:.3f} vs {moved['t5_textbook']['tvd']:.3f}",
            "held" if all(wins) and tight else "partly" if any(wins) else "missed")
    return out


def score_predictions(c: dict) -> list:
    """Score the predictions in docs/design_log.md. They and this function were committed before the first job was sent."""
    jobs = [t for t in ("plain", "suppressed") if t in c["jobs"]]
    hero = {(r["question"], r["build"]): r for r in c["hero"]}
    t3, t3_book = hero[("T = 3", "steer + local (resilient)")], hero[("T = 3", "textbook Grover, r = 3")]
    t5, t5_book = hero[("T = 5", "steer + local (resilient)")], hero[("T = 5", "steer + textbook reflection")]
    curve = c["curves"]["no defect, any click"]
    out = []

    def add(key: str, text: str, measured: str, verdict: str) -> None:
        out.append({"id": key, "prediction": text, "measured": measured, "verdict": verdict})

    wins = sum(t3[j]["hit"] > t3_book[j]["hit"] for j in jobs) + sum(t3[j]["tvd"] < t3_book[j]["tvd"] for j in jobs)
    add("H1", "T = 3: steer + local beats textbook r = 3 on hit rate and TVD, in both jobs",
        "; ".join(f"{j}: hit {t3[j]['hit']:.3f} vs {t3_book[j]['hit']:.3f}, TVD {t3[j]['tvd']:.3f} vs {t3_book[j]['tvd']:.3f}" for j in jobs),
        "held" if wins == 2 * len(jobs) else "partly" if wins else "missed")

    best = max(t3[j]["hit"] for j in jobs)
    add("H2", "T = 3: steer + local reaches a hit rate of at least 0.75 in either job", f"best {best:.3f}",
        "held" if best >= 0.75 else "partly" if best >= 0.6 else "missed")

    strict = [curve[j][1] >= 0.75 and curve[j][3] <= 0.45 for j in jobs]
    loose = [curve[j][1] > curve[j][0] and curve[j][3] < curve[j][1] - 0.2 for j in jobs]
    add("H3", "No defect: hit rate at least 0.75 at r = 1, then back to 0.45 or less at r = 3, in either job",
        "; ".join(f"{j}: {' '.join(f'{v:.3f}' for v in curve[j])}" for j in jobs), "held" if any(strict) else "partly" if any(loose) else "missed")

    gap = c["model_gap"]["plain"]
    tests = [gap["share_below_model"] >= 0.7, gap["median_shortfall"] >= 0.02]
    add("H4", "The device falls short of its noise model: below it on at least 70% of circuits with ideal hit 0.5 or more, by a median of at least 0.02",
        f"below on {gap['share_below_model']:.0%}, median shortfall {gap['median_shortfall']:.3f}", "held" if all(tests) else "partly" if any(tests) else "missed")

    if "suppression" in c and c["suppression"]["deep"]:
        share = c["suppression"]["deep"]["tvd_improved"]
        add("H5", "DD + twirling lowers TVD on at least 60% of circuits with 100 or more two-qubit gates",
            f"{share:.0%} of {c['suppression']['deep']['circuits']}", "held" if share >= 0.6 else "partly" if share >= 0.5 else "missed")

    fp = c["fingerprint"]
    tests = [(fp[j]["amplified"]["separation"][2], fp[j]["plain"]["separation"][2]) for j in jobs]
    add("H6", "Defect against no defect at tau = 3: amplified separation at least 3 standard errors, and above plain sampling, in either job",
        "; ".join(f"{j}: {x:.1f} vs {y:.1f}" for j, (x, y) in zip(jobs, tests)),
        "held" if any(x >= 3 and x > y for x, y in tests) else "partly" if any(x > y for x, y in tests) else "missed")

    r2 = [c["catalog"][j][2] for j in jobs]
    add("H7", "Catalogue, r = 2: the right entry on top with a hit rate of at least 0.70 in either job", "; ".join(f"{j}: {x['hit']:.3f}" for j, x in zip(jobs, r2)),
        "held" if any(x["hit"] >= 0.7 and x["target_is_top"] for x in r2) else "partly" if any(x["hit"] >= 0.5 for x in r2) else "missed")

    tests = [(t5[j]["hit"] >= 0.6, t5[j]["hit"] > t5_book[j]["hit"]) for j in jobs]
    add("H8", "T = 5: steer + local reaches at least 0.60 and beats the same steer with the textbook reflection, in either job",
        "; ".join(f"{j}: {t5[j]['hit']:.3f} vs {t5_book[j]['hit']:.3f}" for j in jobs),
        "held" if any(x and y for x, y in tests) else "partly" if any(x or y for x, y in tests) else "missed")

    per_gate = [e["error_per_gate"] for e in c["echo"]["plain"]]
    reported = c["echo"]["reported_two_qubit_error"]
    tests = [all(g > reported for g in per_gate), all(g <= 0.01 for g in per_gate)]
    add("H9", "Echo: the all-in error per two-qubit gate is above the reported median and at most 1%, on all three echoes",
        f"{', '.join(f'{g:.2%}' for g in per_gate)} against {reported:.2%} reported", "held" if all(tests) else "partly" if any(tests) else "missed")
    return out


def compare(analysed: dict) -> dict | None:
    """Put the real jobs beside the noise model and the ideal answer."""
    device_tags = [t for t in ("plain", "suppressed") if t in analysed]
    if not device_tags:
        return None
    meta = analysed[device_tags[0]]["meta"]
    backend = meta["backend"]
    sources = {"model": analysed[f"noisemodel_{backend}"], **{t: analysed[t] for t in device_tags}}
    shots = int(meta["shots"])
    plan = json.loads((RESULTS / OUT / f"plan_{backend}.json").read_text(encoding="utf-8"))
    out = {"backend": backend, "shots": shots, "circuits": len(analysed[device_tags[0]]["rows"]),
           "jobs": {t: {"job_id": analysed[t]["meta"].get("job_id"), "qpu_seconds": analysed[t]["meta"].get("qpu_seconds"),
                        "submitted": analysed[t]["meta"].get("submitted"), "fetched": analysed[t]["meta"].get("fetched")} for t in device_tags},
           "calibration": plan.get("calibration"), "hero": hero_table(sources, shots), "curves": coherence_curves(sources),
           "fingerprint": fingerprint(sources, shots), "catalog": catalog_table(sources),
           "echo": echo_table(sources, (plan.get("calibration") or {}).get("median_two_qubit_error")),
           "decay": {t: fidelity_decay(r) for t, r in sources.items()},
           "scatter": {t: [row["corrected"]["hit"] for row in history_rows(r)] for t, r in sources.items()},
           "model_gap": {t: model_gap(sources["model"], analysed[t]) for t in device_tags}}
    if len(device_tags) == 2:
        out["suppression"] = against(analysed["plain"], analysed["suppressed"])
    out["by_mode"] = {tag: against(analysed["plain"], analysed[tag]) for tag in ("plain2", "dd", "twirl", "suppressed") if tag in analysed}
    readout = {}
    for t in device_tags:
        rows = history_rows(analysed[t])
        err = lambda key, row: abs(row[key]["hit"] - row[key]["ideal_hit"])  # noqa: E731
        readout[t] = {"median_hit_error_raw": float(np.median([err("raw", r) for r in rows])),
                      "median_hit_error_corrected": float(np.median([err("corrected", r) for r in rows]))}
    out["readout_correction"] = readout
    out["predictions"] = score_predictions(out)
    out["runs"] = {tag: run_row(tag, result) for tag, result in analysed.items() if result["meta"].get("mode") == "real IBM Quantum hardware"}
    out["followups"] = score_followups(out["runs"], backend)
    return out


def main() -> None:
    files = sorted(glob.glob(str(RESULTS / OUT / "raw_*.json")))
    if not files:
        print("no raw results yet: run experiments/run_ibm.py first")
        return
    ideals = {}
    for exp in suite(False):
        logical = exp.circuit.remove_final_measurements(inplace=False)
        ideals[exp.name] = np.abs(Statevector(logical).data) ** 2
    report = []
    analysed = {}
    for f in files:
        path = Path(f)
        print(f"analysing {path.name}", flush=True)
        result = analyse(path, ideals)
        tag = path.stem.replace("raw_", "")
        analysed[tag] = result
        save(OUT, result, f"summary_{tag}.json")
        report.append(table(result))
    (RESULTS / OUT / "summary.md").write_text("\n\n".join(report) + "\n", encoding="utf-8")
    print("\n\n".join(report))
    comparison = compare(analysed)
    if comparison:
        save(OUT, comparison, "comparison.json")
        print("wrote results/hardware/comparison.json", flush=True)


if __name__ == "__main__":
    main()
