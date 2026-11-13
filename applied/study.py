"""One question, three fields: our own machine asked what chipmaking, photon sources and laser monitoring need to know.

The follow-up studies in this repository each built a model of their own (a two-photon resist, a quantum dot with a
trap, an atomic frequency monitor). This study goes the other way. It keeps OUR machine, the emitter with one hidden
defect from the main project, and OUR method, and asks the question those fields have in common:

    A rare event has just happened. Was it a one-off, or is something hidden remembering?

In the machine that is two measurements made right after a rare click:

    what follows    the chance of another click in the next three steps
    the cause       where the hidden defect was at the moment of the click

Each field reads the same record in its own words:

    chipmaking   a two-photon resist prints on PAIRS of photons. The pair dose from an emitter is
                 P(first photon) x P(a second within the resist's window | the first).
    photons      the after-click rate divided by the plain click rate is g2, the correlation every photon lab measures.
    lasers       the hidden partner has a frequency (its detuning per step). Step it, and the after-click record moves.

Nothing here is a wafer, a dot or a laser. The machine is a toy with two memory qubits, and an exact classical filter
answers every question below; that filter is how the answers are checked. The point is the mechanism, run on real IBM
hardware: sampling a model's rare events by rewinding it, and reading the hidden memory at that moment.

    python applied/study.py            recompute everything and write results.json
    python applied/study.py --check    recompute and compare with the saved results.json
    python applied/study.py --exact    the exact part only (no simulator needed)

The IBM numbers are a recount of the raw counts saved by the 11 November 2026 campaign. Nothing is submitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rewindandamplify-main"))

from qiskit.quantum_info import Statevector  # noqa: E402

from qrsm_grover.amplify import hardware_amplified  # noqa: E402
from qrsm_grover.fastsim import reflection_qubits  # noqa: E402
from qrsm_grover.hardware import steer_for  # noqa: E402
from qrsm_grover.model import QRSM  # noqa: E402
from qrsm_grover.predicates import click_at  # noqa: E402
from qrsm_grover.queries import loop_circuit  # noqa: E402

T0 = 3            # the rare event: a click at step 3, as in the main result
WINDOW = 3        # how many later steps count as "soon after"
LOCAL = "memory+last-1"
SHOTS = 8192

MACHINES = {
    "defect": QRSM(),                          # the main project's machine: one hidden defect
    "clean": QRSM(phi=(), zeta=()),            # the same emitter with nothing hidden
    "stepped": QRSM(zeta=(0.6,)),              # the hidden defect's frequency doubled: a frequency step
}
ROLES = {"defect": "the main project's machine, with one hidden defect",
         "clean": "the same emitter with nothing hidden behind it",
         "stepped": "the hidden defect's own frequency doubled, from 0.3 to 0.6 radians per step"}

CAMPAIGN = ROOT / "hardware_campaign"
PRECISION, FIRST_RUN = "original_precision_v1", "original_plain_v2"
NEW_RUN = "applied_v1"            # the job frozen in applied/hardware_bundle; read only once its raw counts exist
# (run, circuit as named in that run) -> (reading, machine, how the record was made)
IBM_ROWS = {
    (PRECISION, "loop-defect-r0"): ("window", "defect", "plain"),
    (PRECISION, "loop-defect-r1"): ("window", "defect", "rewound"),
    (PRECISION, "loop-nodefect-r0"): ("window", "clean", "plain"),
    (PRECISION, "loop-nodefect-r1"): ("window", "clean", "rewound"),
    (PRECISION, "click3-steered-memory+last-1-r1"): ("cause", "defect", "rewound"),
    (FIRST_RUN, "click3-full-r0"): ("cause", "defect", "plain"),
    (FIRST_RUN, "click3-steered-full-r0"): ("cause", "defect", "steered"),
    (FIRST_RUN, "click3-steered-memory+last-1-r1"): ("cause", "defect", "rewound, first run"),
}


# ---------------------------------------------------------------------------- reading a record


def bit(index: np.ndarray, qubit: int) -> np.ndarray:
    return ((index >> qubit) & 1) == 1


def tally(weights: np.ndarray, history: list[int], n_memory: int, tau: int) -> dict:
    """Sums over outcomes, from a probability vector or a vector of counts. Outcome bit q is qubit q.

    `history` lists the light qubits in time order; the event is a click on history[T0 - 1].
    """
    index = np.arange(weights.size)
    event = bit(index, history[T0 - 1])
    out = {"all": weights.sum(), "event": weights[event].sum()}
    if tau:
        later = [bit(index, history[T0 + j]) for j in range(tau)]
        out["after"] = [weights[event & step].sum() for step in later]
        out["later_alone"] = [weights[step].sum() for step in later]
        out["another"] = weights[event & np.logical_or.reduce(later)].sum()
    else:
        out["emitter"] = weights[event & bit(index, 0)].sum()
        if n_memory > 1:
            out["defect"] = weights[event & bit(index, 1)].sum()
            out["defect_alone"] = weights[bit(index, 1)].sum()
    return out


def answers(t: dict) -> dict:
    """The same sums as probabilities and conditional probabilities."""
    out = {"event": t["event"] / t["all"]}
    if "after" in t:
        out["after"] = [x / t["event"] for x in t["after"]]
        out["later_alone"] = [x / t["all"] for x in t["later_alone"]]
        out["another"] = t["another"] / t["event"]
        out["pair"] = t["another"] / t["all"]
    else:
        out["emitter_after_event"] = t["emitter"] / t["event"]
        if "defect" in t:
            out["defect_after_event"] = t["defect"] / t["event"]
            out["defect_typical"] = t["defect_alone"] / t["all"]
    return {k: ([float(x) for x in v] if isinstance(v, list) else float(v)) for k, v in out.items()}


def wilson(successes: int, shots: int, z: float = 1.959963984540054) -> list[float]:
    if shots == 0:
        return [0.0, 1.0]
    p = successes / shots
    centre = (p + z * z / (2 * shots)) / (1 + z * z / shots)
    half = z * math.sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / (1 + z * z / shots)
    return [centre - half, centre + half]


def rate(successes: float, shots: float) -> dict:
    successes, shots = int(round(successes)), int(round(shots))
    return {"successes": successes, "of": shots, "probability": successes / shots if shots else None,
            "wilson95": wilson(successes, shots)}


# ---------------------------------------------------------------------------- the exact machine


def truth(model: QRSM, tau: int = WINDOW) -> dict:
    """The machine's own answers, from the exact filter: every history, no sampling, no amplification."""
    T = T0 + tau
    probs = model.history_probabilities(T)
    window = answers(tally(probs, list(range(T)), 0, tau))            # the history index is already light-only
    out = {"event": window["event"], "after": window["after"], "later_alone": window["later_alone"],
           "another": window["another"], "pair": window["pair"],
           "g2": [a / b for a, b in zip(window["after"], window["later_alone"])]}
    branches = np.abs(model.branches(T0)) ** 2                        # (history, memory)
    clicked = bit(np.arange(2 ** T0), T0 - 1)
    memory = np.arange(branches.shape[1])
    given = branches[clicked].sum(axis=0) / branches[clicked].sum()
    out["emitter_after_event"] = float(given[bit(memory, 0)].sum())
    if model.k:
        out["defect_after_event"] = float(given[bit(memory, 1)].sum())
        out["defect_typical"] = float(branches.sum(axis=0)[bit(memory, 1)].sum())
    return out


def circuits(model: QRSM) -> dict:
    """The circuits behind each record: (circuit without measurements, light qubits in time order, steps after)."""
    n = model.n_memory
    steer = steer_for(model, T0)
    lights = list(range(n, n + T0))
    oracle = click_at(T0).oracle(n + T0, lights)

    def site(r: int, steered: bool):
        A = model.purified(T0, gammas=[None] * (T0 - 1) + [steer] if steered else None)
        return hardware_amplified(A, oracle, r, reflect_on=reflection_qubits(model, T0, LOCAL))

    def window(r: int, steered: bool):
        body = loop_circuit(model, T0, WINDOW, r, LOCAL, steer if steered else None)
        return body, lights + list(range(body.num_qubits - WINDOW, body.num_qubits))

    out = {("cause", "plain"): (site(0, False), lights, 0),
           ("cause", "steered"): (site(0, True), lights, 0),
           ("cause", "rewound"): (site(1, True), lights, 0)}
    for how, (r, steered) in (("plain", (0, False)), ("rewound", (1, True))):
        body, history = window(r, steered)
        out["window", how] = (body, history, WINDOW)
    return out


def ideal(model: QRSM) -> dict:
    """What each circuit returns on a perfect device: the method's own bias, before any noise."""
    out = {}
    for (reading, how), (body, history, tau) in circuits(model).items():
        probabilities = Statevector.from_instruction(body).probabilities()
        out.setdefault(reading, {})[how] = answers(tally(probabilities, history, model.n_memory, tau))
    return out


def exact() -> dict:
    out = {}
    for name, model in MACHINES.items():
        out[name] = {"role": ROLES[name], "theta": model.theta, "gamma": model.gamma, "phi": list(model.phi),
                     "zeta": list(model.zeta), "steered_gamma": steer_for(model, T0), "truth": truth(model),
                     "curve": truth(model, 8), "ideal_circuits": ideal(model)}
    return out


# ---------------------------------------------------------------------------- what each field reads


def records_to_tell_apart(p1: float, p2: float, z_alpha: float = 1.959963984540054, z_beta: float = 1.6448536269514722) -> int:
    """Records per arm for a two-sided 5% test to tell two rates apart 95% of the time (normal approximation)."""
    mean = (p1 + p2) / 2
    top = z_alpha * math.sqrt(2 * mean * (1 - mean)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return math.ceil(top * top / (p1 - p2) ** 2)


def readings(ex: dict) -> dict:
    d, c, s = (ex[name]["truth"] for name in ("defect", "clean", "stepped"))
    rewound = ex["defect"]["ideal_circuits"]["cause"]["rewound"]["event"]
    need = records_to_tell_apart(d["another"], s["another"])
    sweep = []
    for zeta in np.round(np.arange(0.0, 1.2001, 0.15), 2):
        t = truth(QRSM(zeta=(float(zeta),)))
        sweep.append({"zeta": float(zeta), "event": t["event"], "another": t["another"],
                      "defect_after_event": t["defect_after_event"]})
    return {
        "chipmaking": {
            "reads": "pair dose for a two-photon resist: P(first photon) x P(a second within three steps | the first)",
            "second_given_first": {"defect": d["another"], "clean": c["another"]},
            "pair_per_run": {"defect": d["pair"], "clean": c["pair"]},
            "one_pair_in_runs": {"defect": 1 / d["pair"], "clean": 1 / c["pair"]},
            "defect_makes_pairs_rarer_by": c["pair"] / d["pair"],
            "defect_holds_the_energy": {"after_a_photon": d["defect_after_event"], "typically": d["defect_typical"]},
        },
        "photons": {
            "reads": "g2(tau) = P(click at 3 + tau | click at 3) / P(click at 3 + tau)",
            "g2": {"defect": d["g2"], "clean": c["g2"]},
            "g2_longer": {"defect": ex["defect"]["curve"]["g2"], "clean": ex["clean"]["curve"]["g2"]},
        },
        "lasers": {
            "reads": "a frequency step of the hidden partner (0.3 to 0.6 radians per step) moves the after-click record",
            "second_given_first": {"before": d["another"], "after": s["another"]},
            "first_event": {"before": d["event"], "after": s["event"]},
            "defect_after_event": {"before": d["defect_after_event"], "after": s["defect_after_event"]},
            "records_needed_per_side": need,
            "model_runs_needed": {"plain": math.ceil(need / d["event"]), "rewound": math.ceil(need / rewound)},
            "sweep": sweep,
        },
        "cost": {
            "shots": SHOTS,
            "records_of_the_event": {"plain": SHOTS * d["event"], "rewound": SHOTS * rewound},
            "more_records_per_shot": rewound / d["event"],
            "scope": "Records per run of the model on a perfect device. A rewound run uses about three times the gates.",
        },
    }


# ---------------------------------------------------------------------------- the saved IBM records


def read_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_run(name: str) -> dict:
    folder = CAMPAIGN / "runs" / name
    plan, raw = read_json(folder / "plan.json"), read_json(folder / "raw.json")
    manifest = read_json(ROOT / plan["bundle"] / "manifest.json")
    return {"name": name, "plan": plan, "raw": raw, "circuits": {c["name"]: c for c in manifest["circuits"]}}


def counts_vector(row: dict) -> np.ndarray:
    out = np.zeros(1 << row["logical_qubits"])
    for key, value in row["counts"].items():
        out[int(key.replace(" ", ""), 2)] += value
    assert out.sum() == row["shots"]
    return out


def counted(t: dict) -> dict:
    """Counts as rates with intervals."""
    out = {"event": rate(t["event"], t["all"])}
    if "after" in t:
        out["after"] = [rate(x, t["event"]) for x in t["after"]]
        out["later_alone"] = [rate(x, t["all"]) for x in t["later_alone"]]
        out["another"] = rate(t["another"], t["event"])
        out["pair"] = rate(t["another"], t["all"])
    else:
        out["emitter_after_event"] = rate(t["emitter"], t["event"])
        if "defect" in t:
            out["defect_after_event"] = rate(t["defect"], t["event"])
            out["defect_typical"] = rate(t["defect_alone"], t["all"])
    return out


def difference(a: dict, b: dict) -> dict:
    """a minus b for two independent rates, with a 95% interval from the two Wilson intervals (Newcombe)."""
    pa, pb = a["probability"], b["probability"]
    (la, ua), (lb, ub) = a["wilson95"], b["wilson95"]
    return {"difference": pa - pb,
            "interval95": [pa - pb - math.sqrt((pa - la) ** 2 + (ub - pb) ** 2), pa - pb + math.sqrt((ua - pa) ** 2 + (pb - lb) ** 2)]}


def ratio(top: dict, bottom: dict) -> dict:
    """top / bottom for two independent rates, with a 95% interval on the log scale (delta method)."""
    p, q = top["probability"], bottom["probability"]
    spread = math.sqrt((1 - p) / (top["of"] * p) + (1 - q) / (bottom["of"] * q))
    return {"ratio": p / q, "interval95": [p / q * math.exp(-1.959963984540054 * spread), p / q * math.exp(1.959963984540054 * spread)]}


def ibm() -> dict:
    """Recount the campaign's raw counts for the questions asked here. Raw counts, no correction, nothing pooled."""
    runs = {name: load_run(name) for name in (PRECISION, FIRST_RUN)}
    rows = {}
    for (run_name, circuit), (reading, machine, how) in IBM_ROWS.items():
        run = runs[run_name]
        row = next(r for r in run["raw"]["rows"] if r["name"] == circuit)
        reference = run["circuits"][circuit]["reference"]
        meta = run["circuits"][circuit]["metadata"]
        tau = meta.get("tau", 0)
        t = tally(counts_vector(row), reference["chronological_history_qubits"], reference["memory_qubits"], tau)
        rows[f"{reading}/{machine}/{how}"] = {
            "run": run_name, "job_id": run["raw"]["job_id"], "circuit": circuit, "shots": row["shots"],
            "two_qubit_gates": row["gate_counts"]["cz"], **counted(t)}
    w = lambda machine, how: rows[f"window/{machine}/{how}"]  # noqa: E731
    return {
        "backend": runs[PRECISION]["raw"]["backend"],
        "scope": "Recount of raw counts saved on 11 November 2026. Programmed models on superconducting qubits: no "
                 "photon, laser, resist or wafer was measured, and no unknown defect was diagnosed.",
        "rows": rows,
        "clean_minus_defect_another": {
            "rewound": difference(w("clean", "rewound")["another"], w("defect", "rewound")["another"]),
            "plain": difference(w("clean", "plain")["another"], w("defect", "plain")["another"]),
        },
        "g2": {machine: [ratio(w(machine, "rewound")["after"][j], w(machine, "plain")["later_alone"][j])
                         for j in range(WINDOW)] for machine in ("defect", "clean")},
        "g2_scope": "After-click rate from the rewound circuit over the plain click rate from the plain circuit, at steps "
                    "4, 5 and 6. Two different circuits of one job, so drift between them is not in the interval.",
        "source_sha256": {f"hardware_campaign/runs/{name}/raw.json": sha(CAMPAIGN / "runs" / name / "raw.json")
                          for name in (PRECISION, FIRST_RUN)},
    }


def explained_afterwards(name: str = NEW_RUN) -> dict:
    """The returned job under the same noise model, now with ITS OWN qubits, calibration and echo circuits.

    This is an explanation made after the answers were known, not a prediction. The one fitted number is again the
    scale that makes the model reproduce the job's two echo circuits; the answers themselves are not fitted.
    """
    simulate, run_study = noise_tools()
    run = saved_run(simulate, name)
    fit = run_study.fit_echo_scale(run)
    rows = {}
    for circuit, entry in run.manifest.items():
        meta, reference = entry["metadata"], entry["reference"]
        if meta["kind"] == "echo":
            continue
        distribution = simulate.simulate(run, circuit, scale=fit["scale"])
        rows[circuit] = answers(tally(distribution, reference["chronological_history_qubits"], reference["memory_qubits"], meta["tau"]))
    another = lambda circuit: rows[circuit]["another"]  # noqa: E731
    return {
        "made_after_the_job": True, "echo_scale": fit["scale"],
        "echoes": [{k: e[k] for k in ("circuit", "two_qubit_gates", "measured_return", "calibration_return", "echo_scaled_return")}
                   for e in fit["echoes"]],
        "calibration": run.properties["last_update_date"], "rows": rows,
        "comparisons": {
            "chipmaking: second event, clean minus defect (rewound)": another("window-clean-rewound") - another("window-defect-rewound"),
            "chipmaking: second event, clean minus defect (plain)": another("window-clean-plain") - another("window-defect-plain"),
            "lasers: second event, stepped minus defect (rewound)": another("window-stepped-rewound") - another("window-defect-rewound"),
            "lasers: second event, stepped minus defect (plain)": another("window-stepped-plain") - another("window-defect-plain"),
        },
        "cause": {how: rows[f"site-defect-{how}"]["defect_after_event"] for how in ("plain", "steered", "rewound")},
    }


def new_job(folder: Path | None = None) -> dict | None:
    """The job frozen in applied/hardware_bundle, read against the predictions written before it ran.

    Returns None until hardware_campaign/runs/applied_v1/raw.json exists. Nothing here contacts IBM.
    """
    folder = folder or CAMPAIGN / "runs" / NEW_RUN
    if not (folder / "raw.json").exists():
        return None
    raw = read_json(folder / "raw.json")
    manifest = {c["name"]: c for c in read_json(HERE / "hardware_bundle" / "manifest.json")["circuits"]}
    predictions = read_json(HERE / "predictions.json")
    rows = {}
    for row in raw["rows"]:
        if row["kind"] != "science":
            continue
        meta, reference = manifest[row["name"]]["metadata"], manifest[row["name"]]["reference"]
        counts = counts_vector(row)
        if meta["kind"] == "echo":
            rows[row["name"]] = {"shots": row["shots"], "two_qubit_gates": row["gate_counts"]["cz"],
                                 "all_zero_return": rate(counts[0], row["shots"])}
            continue
        t = tally(counts, reference["chronological_history_qubits"], reference["memory_qubits"], meta["tau"])
        rows[row["name"]] = {"shots": row["shots"], "two_qubit_gates": row["gate_counts"]["cz"], **counted(t)}
    another = lambda name: rows[name]["another"]  # noqa: E731
    compared = {
        "chipmaking: second event, clean minus defect (rewound)": difference(another("window-clean-rewound"), another("window-defect-rewound")),
        "chipmaking: second event, clean minus defect (plain)": difference(another("window-clean-plain"), another("window-defect-plain")),
        "lasers: second event, stepped minus defect (rewound)": difference(another("window-stepped-rewound"), another("window-defect-rewound")),
        "lasers: second event, stepped minus defect (plain)": difference(another("window-stepped-plain"), another("window-defect-plain")),
    }
    for key, value in compared.items():
        value["predicted"] = predictions["comparisons"]["echo_scaled"][key]
        value["exact"] = predictions["comparisons"]["ideal"][key]
    cause = {how: {"measured": rows[f"site-defect-{how}"]["defect_after_event"],
                   "predicted": predictions["rows"][f"site-defect-{how}"]["echo_scaled"]["defect_after_event"]}
             for how in ("plain", "steered", "rewound")}
    plan = read_json(folder / "plan.json")
    return {"run": folder.name, "job_id": raw["job_id"], "backend": raw["backend"], "retrieved_utc": raw["retrieved_utc"],
            "quantum_seconds": raw["usage"], "physical_qubits": plan["physical_patch"],
            "predictions_assumed_qubits": predictions["device_assumed"]["physical_qubits"],
            "rows": rows, "comparisons": compared, "cause": cause,
            "g2": {machine: [ratio(rows[f"window-{machine}-rewound"]["after"][j], rows[f"window-{machine}-plain"]["later_alone"][j])
                             for j in range(WINDOW)] for machine in ("defect", "clean", "stepped")},
            "scope": "A fresh job. Predictions were written before it ran, for the qubits and calibration of 11 November.",
            "source_sha256": {f"hardware_campaign/runs/{folder.name}/raw.json": sha(folder / "raw.json"),
                              "applied/predictions.json": sha(HERE / "predictions.json")}}


# ---------------------------------------------------------------------------- what a noise model says of those records


def noise_tools():
    """The campaign's noise simulator and its echo fit (hardware_campaign/noise_model). Needs qiskit-aer."""
    folder = str(CAMPAIGN / "noise_model")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import run_study
    import simulate
    return simulate, run_study


def saved_run(simulate, name: str):
    """Everything saved for one hardware job, in the form the noise simulator reads."""
    from qiskit import qpy
    folder = CAMPAIGN / "runs" / name
    plan = read_json(folder / "plan.json")
    with open(folder / plan.get("compiled_qpy_file", "isa.qpy"), "rb") as handle:
        compiled = qpy.load(handle)
    manifest = read_json(ROOT / plan["bundle"] / "manifest.json")
    return simulate.Run(name, plan, read_json(folder / "raw.json"), read_json(folder / "backend_properties.json"),
                        compiled, {c["name"]: c for c in manifest["circuits"]})


def noise_model() -> dict:
    """The campaign's circuits under the device's reported errors, scaled by the echo fit made in noise_model/.

    The scale was fitted to two echo circuits only. Nothing here was fitted to the answers it is compared with.
    """
    simulate, _ = noise_tools()
    scale = read_json(CAMPAIGN / "noise_model" / "results.json")["echo_fit"]["scale"]
    runs = {name: saved_run(simulate, name) for name in (PRECISION, FIRST_RUN)}
    rows = {}
    for (run_name, circuit), (reading, machine, how) in IBM_ROWS.items():
        run = runs[run_name]
        reference = run.manifest[circuit]["reference"]
        tau = run.manifest[circuit]["metadata"].get("tau", 0)
        distribution = simulate.simulate(run, circuit, scale=scale)
        rows[f"{reading}/{machine}/{how}"] = answers(tally(distribution, reference["chronological_history_qubits"],
                                                           reference["memory_qubits"], tau))
    return {"model": "depolarizing gate errors at the reported rates times one echo-fitted scale, and this job's own "
                     "readout errors; no idle decoherence, crosstalk or drift",
            "echo_scale": scale, "rows": rows}


# ---------------------------------------------------------------------------- assembling and checking


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(noise: bool = True) -> dict:
    ex = exact()
    out = {"schema": "ra-applied-v1",
           "question": "A rare event has just happened. Was it a one-off, or is something hidden remembering?",
           "event": f"a click at step {T0}", "window_steps": WINDOW, "machines": ex, "readings": readings(ex),
           "ibm": ibm()}
    if noise:
        out["noise_model"] = noise_model()
    fresh = new_job()
    if fresh is not None:
        if noise:
            fresh["explained_afterwards"] = explained_afterwards()
        out["new_job"] = fresh
    out["limits"] = [
        "The machine is a toy with two memory qubits. An exact classical filter answers every question here, and is "
        "the reference the circuits are checked against.",
        "Rewinding runs a MODEL inside a quantum computer. It cannot rewind a real laser, quantum dot or wafer.",
        "No speedup is claimed. A rewound run uses about three times the gates of a plain run.",
        "On IBM hardware the answers keep their order and lose most of their gap; see ibm and noise_model.",
    ]
    return out


def worst_difference(a, b, where: str = "") -> tuple[float, str]:
    """The largest numerical difference between two JSON-like objects, and where it is."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return math.inf, f"{where}: keys differ"
        return max((worst_difference(a[k], b[k], f"{where}/{k}") for k in a), default=(0.0, where))
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return math.inf, f"{where}: lengths differ"
        return max((worst_difference(x, y, f"{where}[{i}]") for i, (x, y) in enumerate(zip(a, b))), default=(0.0, where))
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        return (0.0 if a == b else math.inf), where
    return abs(float(a) - float(b)), where


def compare(result: dict, saved: dict) -> tuple[float, str, float, str]:
    """Largest difference in the exact and counted parts, and separately in the parts that go through the noise simulator.

    The second kind includes one fitted scale rounded to four decimals, which may land on a neighbouring value on
    another machine. hardware_campaign/noise_model allows 2e-3 for the same reason.
    """
    def split(r: dict) -> tuple[dict, dict]:
        exact = {k: v for k, v in r.items() if k != "noise_model"}
        simulated = {"noise_model": r.get("noise_model")}
        if "new_job" in exact:
            simulated["explained_afterwards"] = exact["new_job"].get("explained_afterwards")
            exact["new_job"] = {k: v for k, v in exact["new_job"].items() if k != "explained_afterwards"}
        return exact, simulated

    (exact_a, simulated_a), (exact_b, simulated_b) = split(result), split(saved)
    return (*worst_difference(exact_a, exact_b), *worst_difference(simulated_a, simulated_b))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="recompute and compare with the saved results.json")
    parser.add_argument("--exact", action="store_true", help="print the exact answers only")
    args = parser.parse_args()
    if args.exact:
        ex = exact()
        print(json.dumps({name: m["truth"] for name, m in ex.items()}, indent=2))
        return
    result = build()
    path = HERE / "results.json"
    if args.check:
        gap, where, noisy_gap, noisy_where = compare(result, read_json(path))
        if gap > 1e-9:
            raise SystemExit(f"applied/results.json no longer matches its sources: {gap:.3g} at {where}")
        if noisy_gap > 2e-3:
            raise SystemExit(f"applied/results.json: the noise-model part differs by {noisy_gap:.3g} at {noisy_where}")
        print(f"applied/results.json reproduces from the model and the saved IBM counts (largest difference {gap:.1e}; "
              f"noise-model part {noisy_gap:.1e}).")
        return
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    r, rows = result["readings"], result["ibm"]["rows"]
    print(f"wrote {path.relative_to(ROOT)}")
    print(f"a second event within {WINDOW} steps of the first: {r['chipmaking']['second_given_first']['defect']:.2%} with the hidden "
          f"defect, {r['chipmaking']['second_given_first']['clean']:.2%} without")
    print(f"IBM, 11 November, rewound: {rows['window/defect/rewound']['another']['probability']:.2%} against "
          f"{rows['window/clean/rewound']['another']['probability']:.2%}")
    if "new_job" in result:
        fresh = result["new_job"]["rows"]
        print(f"IBM, 12 November, rewound: {fresh['window-defect-rewound']['another']['probability']:.2%} against "
              f"{fresh['window-clean-rewound']['another']['probability']:.2%}; after the frequency step "
              f"{fresh['window-stepped-rewound']['another']['probability']:.2%}")


if __name__ == "__main__":
    main()
