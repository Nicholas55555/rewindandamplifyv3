"""Causal, unknown-onset follow-up. Never alters the frozen finals evidence."""
from pathlib import Path
import argparse
from dataclasses import asdict, replace
import hashlib
import json
import os
import platform
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from model import (Config, response_calibration, ramsey_probability, ou,
                   random_walk, coherent_frequency, photodiode)

LABELS = {
    "power_only": "Power monitor (nonspecific control)",
    "classical": "Conventional C",
    "quantum": "Atomic Q + power",
    "classical_quantum": "C + atomic Q, fusion",
    "two_classical": "C + independent C, fusion",
    "classical_quantum_agreement": "C + atomic Q, agreement",
    "two_classical_agreement": "C + independent C, agreement",
}
COLS = {"power_only": [0], "classical": [0, 1], "quantum": [0, 3],
        "classical_quantum": [0, 2, 3], "two_classical": [0, 2, 4]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seed(base, *ids):
    return np.random.SeedSequence([base, *ids])


def rng_for(base, *ids):
    return np.random.default_rng(seed(base, *ids))


def session_parameters(rng, config, protocol):
    """One independent session; nuisance values persist across its records."""
    d = protocol["session_distribution"]
    return {
        "t2_s": float(config.t2_s * np.exp(rng.normal(0, d["t2_log_sd"]))),
        "readout_01": float(np.clip(config.readout_01 + rng.normal(0, d["readout_01_normal_sd"]), .001, .08)),
        "readout_10": float(np.clip(config.readout_10 + rng.normal(0, d["readout_10_normal_sd"]), .001, .10)),
        "reference_rw_multipliers": np.exp(rng.normal(0, d["reference_random_walk_log_sd"], 3)).tolist(),
        "reference_offsets_hz": rng.normal(0, d["reference_initial_offset_sd_hz"], 3).tolist(),
        "diode_static_gain": float(np.exp(rng.normal(0, d["diode_static_gain_log_sd"]))),
    }


def generate(n, seed_sequence, config, response, session, protocol,
             frequency_amplitudes=0., scenario=None):
    """Generate observations separately from hidden truth, with random onset.

    Sampling each record restarts stationary source noise and zero-referenced
    random walks; the session's apparatus parameters/offsets persist. This is
    a hierarchical acquisition model, not one uninterrupted multi-day stream.
    """
    scenario = scenario or {}
    r = [np.random.default_rng(s) for s in seed_sequence.spawn(13)]
    m = config.cycles
    onset = r[0].integers(*[protocol["event_onset_inclusive_cycles"][0],
                            protocol["event_onset_inclusive_cycles"][1] + 1], n)
    nuisance_onset = r[0].integers(protocol["nuisance_onset_inclusive_cycles"][0],
                                 protocol["nuisance_onset_inclusive_cycles"][1] + 1, n)
    sign = r[0].choice([-1., 1.], n)
    a = np.broadcast_to(np.asarray(frequency_amplitudes, float), (n,))
    event = np.arange(m)[None, :] >= onset[:, None]
    nuisance = np.arange(m)[None, :] >= nuisance_onset[:, None]
    source = ou(r[1], n, m, config.source_frequency_ou_sd_hz,
                config.source_frequency_ou_time_s, config.cycle_s) + a[:, None] * event
    power = np.exp(ou(r[2], n, m, config.intensity_ou_sd, 5., config.cycle_s)
                   - config.intensity_ou_sd**2/2)
    primary, secondary, atomic = [
        random_walk(r[j+3], n, m, sigma * session["reference_rw_multipliers"][j], config.cycle_s)
        + session["reference_offsets_hz"][j]
        for j, sigma in enumerate([config.primary_reference_rw_hz_per_sqrt_s,
                                   config.secondary_reference_rw_hz_per_sqrt_s,
                                   config.atomic_reference_rw_hz_per_sqrt_s])]
    common = ou(r[6], n, m, config.common_path_ou_sd_hz, 5., config.cycle_s)
    kind = scenario.get("nuisance")
    size = scenario.get("magnitude", 0.)
    if kind == "power":
        power *= 1 + size*nuisance
    elif kind:
        arr = {"atomic": atomic, "primary": primary, "path": common}[kind]
        arr += sign[:, None]*size*nuisance
    gain = session["diode_static_gain"]*np.exp(
        ou(r[7], n, m, config.diode_gain_ou_sd, 10., config.cycle_s)-config.diode_gain_ou_sd**2/2)
    pd = photodiode(r[7], power, gain, config)
    photons = config.source_photons_per_cycle*(1-config.diode_fraction)
    hfull = coherent_frequency(r[8], source+common-primary, power, photons, config)
    hhalf = coherent_frequency(r[9], source+common-primary, power, photons/2, config)
    hsecond = coherent_frequency(r[10], source+common-secondary, power, photons/2, config)
    actual = replace(config, t2_s=session["t2_s"]*scenario.get("t2_multiplier", 1.),
                     readout_01=session["readout_01"], readout_10=session["readout_10"])
    qprob = ramsey_probability(source+common-atomic, power, actual)
    qfraction = r[11].binomial(actual.atoms, qprob)/actual.atoms
    q = (qfraction-response["q_intercept"]-response["q_power_coefficient"]*(pd-1))/response["q_slope_per_hz"]
    def hcal(h):
        return (h-response["h_intercept_hz"]-response["h_power_coefficient_hz"]*(pd-1))/response["h_slope"]
    observations = np.stack([pd, hcal(hfull), hcal(hhalf), q, hcal(hsecond)], axis=-1)
    hidden = {"source_frequency_hz": source, "source_relative_power": power,
              "primary_reference_hz": primary, "secondary_reference_hz": secondary,
              "atomic_reference_hz": atomic, "common_path_hz": common,
              "onset_cycle": onset, "nuisance_onset_cycle": nuisance_onset,
              "amplitude_hz": a, "atomic_excited_fraction": qfraction}
    return observations, hidden


def contrasts(observations, window):
    """Causal adjacent-window mean difference, output index0 ends at2w seconds."""
    x = np.asarray(observations, float)
    if x.ndim != 3 or x.shape[1] < 2*window:
        raise ValueError("shape(records,time,channels), with at least two windows, required")
    c = np.concatenate([np.zeros((len(x), 1, x.shape[2])), np.cumsum(x, axis=1)], axis=1)
    return (c[:, 2*window:] - 2*c[:, window:-window] + c[:, :-2*window])/window


def fit_models(training_contrasts):
    x = np.concatenate(training_contrasts, axis=0).reshape(-1, 5)
    mean = x.mean(axis=0)
    covariance = np.cov(x, rowvar=False)
    models = {}
    for key, cols in COLS.items():
        if key == "power_only":
            weights = np.ones(1)
        else:
            response = np.array([0. if col == 0 else 1. for col in cols])
            sub = covariance[np.ix_(cols, cols)]
            raw = np.linalg.solve(sub, response)
            weights = raw/(response @ raw)
        models[key] = {"columns": cols, "weights": weights.tolist(),
                       "center": mean[cols].tolist(), "null_covariance": covariance[np.ix_(cols, cols)].tolist()}
    for key, pair in [("classical_quantum_agreement", [2, 3]), ("two_classical_agreement", [2, 4])]:
        models[key] = {"columns": pair, "center": mean[pair].tolist(),
                       "standard_deviation": np.sqrt(np.diag(covariance)[pair]).tolist()}
    return models


def score_series(contrast, models):
    """No onset or hidden-state argument is accepted by the detector."""
    scores = {}
    for key, model in models.items():
        x = contrast[:, :, model["columns"]] - np.array(model["center"])
        if key.endswith("_agreement"):
            z = x/np.array(model["standard_deviation"])
            scores[key] = np.where(z[:, :, 0]*z[:, :, 1] > 0,
                                   np.min(np.abs(z), axis=-1), 0.)
        else:
            scores[key] = np.abs(x @ np.array(model["weights"]))
    return scores


def threshold_order(scores, alpha):
    """Strict-exceedance upper order statistic on independent record maxima."""
    values = np.sort(np.asarray(scores, float))
    k = int(np.ceil((len(values)+1)*(1-alpha)))
    return float(values[k-1]) if k <= len(values) else float("inf")


def first_alarms(scores, thresholds, window):
    result = {}
    for key, s in scores.items():
        hits = s > thresholds[key]
        result[key] = np.where(hits.any(axis=1), np.argmax(hits, axis=1)+2*window, -1)
    return result


def event_metrics(alarm, onset, limit):
    alarm = np.asarray(alarm); onset = np.asarray(onset)
    before = (alarm >= 0) & (alarm <= onset)
    valid = alarm > onset
    delay = alarm-onset
    within = valid & (delay <= limit)
    restricted = np.where(valid, np.minimum(delay, limit), limit)
    return {"pre_onset_alarm": before.astype(float), "eventual_detection": valid.astype(float),
            "detection_within_32s": within.astype(float), "no_alarm": (alarm < 0).astype(float),
            "restricted_delay_s": restricted.astype(float)}


def hierarchical_ci(cells, bootstrap_seed, repetitions):
    """Resample independent pipelines, then whole test sessions within each."""
    cells = np.asarray(cells, float)
    if cells.ndim != 2:
        raise ValueError("one mean per calibration pipeline and test session required")
    r = np.random.default_rng(bootstrap_seed)
    n_outer, n_session = cells.shape
    outer = r.integers(n_outer, size=(repetitions, n_outer))
    sessions = r.integers(n_session, size=(repetitions, n_outer, n_session))
    sampled = cells[outer[:, :, None], sessions].mean(axis=(1, 2))
    return np.quantile(sampled, [.025, .975]).tolist()


def summarize(records, protocol):
    result = []
    methods = protocol["algorithms"]
    rcount, scount = protocol["outer_calibrations"], protocol["test_sessions"]
    n = protocol["test_records_per_class_per_session"]
    for si, scenario in enumerate(protocol["scenarios"]):
        row = {**scenario, "records_per_class": rcount*scount*n, "test_sessions": rcount*scount,
               "methods": {}, "paired_comparisons": {}}
        cells_by_method = {}
        for mi, key in enumerate(methods):
            x = records[scenario["id"]][key]
            null = np.asarray(x["null_alarm"]).reshape(rcount, scount, n)
            alt = np.asarray(x["event_alarm"]).reshape(rcount, scount, n)
            onset = np.asarray(x["onset"]).reshape(rcount, scount, n)
            em = event_metrics(alt, onset, protocol["restricted_delay_s"])
            values = {"false_alarm_rate": (null >= 0).astype(float), **em}
            cells_by_method[key] = {k: v.mean(axis=-1) for k, v in values.items()}
            summary = {"label": LABELS[key], "counts": {}, "per_calibration": []}
            for ki, (metric, value) in enumerate(values.items()):
                summary[metric] = float(value.mean())
                summary[metric+"_ci95"] = hierarchical_ci(value.mean(axis=-1),
                    seed(protocol["base_seed"], 900, si, mi, ki), protocol["bootstrap_repetitions"])
                if metric != "restricted_delay_s":
                    summary["counts"][metric] = int(value.sum())
            delays = (alt-onset)[alt > onset]
            summary["detected_only_delay_median_s"] = float(np.median(delays)) if len(delays) else None
            summary["detected_only_delay_p10_p90_s"] = np.quantile(delays, [.1, .9]).tolist() if len(delays) else None
            for ri in range(rcount):
                summary["per_calibration"].append({k: float(v[ri].mean()) for k, v in values.items()})
            row["methods"][key] = summary
        pairs = [("classical", "classical_quantum"), ("classical", "two_classical"),
                 ("classical_quantum", "classical_quantum_agreement"),
                 ("two_classical", "two_classical_agreement")]
        for pi, (a, b) in enumerate(pairs):
            delta = cells_by_method[b]["detection_within_32s"]-cells_by_method[a]["detection_within_32s"]
            fp = cells_by_method[b]["false_alarm_rate"]-cells_by_method[a]["false_alarm_rate"]
            row["paired_comparisons"][a+"_to_"+b] = {
                "detection_difference": float(delta.mean()),
                "detection_difference_ci95": hierarchical_ci(delta, seed(protocol["base_seed"], 901, si, pi), protocol["bootstrap_repetitions"]),
                "false_alarm_difference": float(fp.mean()),
                "false_alarm_difference_ci95": hierarchical_ci(fp, seed(protocol["base_seed"], 902, si, pi), protocol["bootstrap_repetitions"])}
        result.append(row)
    return result


def plots(result, examples, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = ["classical", "classical_quantum", "two_classical", "classical_quantum_agreement", "two_classical_agreement"]
    labels = ["C", "C+Q fusion", "C+C fusion", "C+Q agreement", "C+C agreement"]
    colors = ["#278ba8", "#ca821d", "#34866a", "#a15796", "#536d9d"]
    nominal = result["scenarios"][0]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout="constrained")
    for ax, metric, title, factor in zip(axes, ["detection_within_32s", "false_alarm_rate", "restricted_delay_s"],
            ["First valid alarm within32s", "False alarm anywhere in128s", "Restricted alarm delay; failures=32s"], [100, 100, 1]):
        y = np.array([nominal["methods"][k][metric] for k in keys])
        ci = np.array([nominal["methods"][k][metric+"_ci95"] for k in keys])
        ax.bar(range(len(keys)), y*factor, color=colors)
        ax.errorbar(range(len(keys)), y*factor, yerr=np.maximum(0, np.stack([y-ci[:, 0], ci[:, 1]-y]))*factor, fmt="none", color="black", capsize=3)
        ax.set_xticks(range(len(keys)), labels, rotation=35, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11); ax.set_ylabel("Percent" if factor == 100 else "Seconds")
        if metric == "false_alarm_rate": ax.axhline(5, ls="--", color="gray")
    fig.suptitle("Unknown onset, independent calibration pipelines and unseen synthetic sessions")
    fig.savefig(out/"unknown_onset_comparison.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), layout="constrained")
    for key, label, color in zip(keys, labels, colors):
        for ax, metric in zip(axes, ["detection_within_32s", "false_alarm_rate"]):
            ax.plot([100*s["methods"][key][metric] for s in result["scenarios"]], "o-", label=label, color=color)
    axes[0].set_ylabel("Detect within32s (%)"); axes[0].legend(ncol=3)
    axes[1].set_ylabel("Frequency-null alarms (%)"); axes[1].axhline(5, ls="--", color="gray")
    short = ["Nominal sessions", "Short coherence", "Atom step", "Primary LO step", "Common path step", "Power step"]
    for ax in axes: ax.set_xticks(range(len(short)), short, rotation=25, ha="right"); ax.set_ylim(-2, 102)
    fig.suptitle("Fresh negative-control tests: an agreement rule may reduce attribution errors")
    fig.savefig(out/"session_stress_tests.png", dpi=160); plt.close(fig)
    ex = examples["unseen_nominal_sessions"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), layout="constrained")
    obs = np.asarray(ex["observations"])
    axes[0].plot(ex["source_frequency_hz"], "k", lw=2, label="Source truth, scoring only")
    axes[0].plot(obs[:, 2], alpha=.7, label="Primary coherent measurement")
    axes[0].plot(obs[:, 3], alpha=.4, label="Atomic measurement")
    axes[0].set_ylabel("Hz"); axes[0].legend(fontsize=8)
    for key, label, color in zip(keys[:3], labels[:3], colors[:3]):
        axes[1].plot(ex["score_end_time_s"], np.asarray(ex["scores"][key])/ex["thresholds"][key], label=label, color=color)
    axes[1].axhline(1, color="gray", ls="--"); axes[1].legend(); axes[1].set(xlabel="Time(s)", ylabel="Score / calibrated threshold")
    for ax in axes: ax.axvline(ex["onset_cycle"], color="black", ls=":")
    fig.suptitle("Fixed first test example; only observations enter causal scores")
    fig.savefig(out/"causal_trace.png", dpi=160); plt.close(fig)


def run(out, protocol, mode="main"):
    out.mkdir(parents=True, exist_ok=True)
    if (out/"provenance_start.json").exists() or (out/"results.json").exists():
        raise FileExistsError("Use a new output directory; prior runs are retained.")
    sources = {str(p.relative_to(HERE.parent)): sha(p) for p in
               [HERE/"protocol.json", HERE/"run_followup.py", HERE.parent/"model.py"]}
    start = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "mode": mode, "source_sha256": sources, "protocol": protocol,
             "first_heldout_evaluation_not_yet_started": True}
    (out/"provenance_start.json").write_text(json.dumps(start, indent=2), encoding="utf-8")
    t0 = time.perf_counter()
    base = protocol["base_seed"]; w = protocol["window_cycles"]
    config = replace(Config(), cycles=protocol["record_cycles"])
    methods = protocol["algorithms"]
    records = {s["id"]: {k: {"null_alarm": [], "event_alarm": [], "onset": []} for k in methods} for s in protocol["scenarios"]}
    calibrations, examples, session_log = [], {}, []
    for ri in range(protocol["outer_calibrations"]):
        response_seed = int(seed(base, ri, 0).generate_state(1)[0])
        response = response_calibration(config, response_seed, protocol["response_scan_repetitions_per_setting"])
        training = []
        for si in range(protocol["fit_sessions"]):
            sp = session_parameters(rng_for(base, ri, 1, si), config, protocol)
            obs, _ = generate(protocol["fit_records_per_session"], seed(base, ri, 2, si), config, response, sp, protocol)
            training.append(contrasts(obs, w))
        models = fit_models(training)
        maxima = {k: [] for k in methods}
        for si in range(protocol["threshold_sessions"]):
            sp = session_parameters(rng_for(base, ri, 3, si), config, protocol)
            obs, _ = generate(1, seed(base, ri, 4, si), config, response, sp, protocol)
            scores = score_series(contrasts(obs, w), models)
            for key in methods: maxima[key].append(float(scores[key].max()))
        thresholds = {k: threshold_order(maxima[k], protocol["record_false_alarm_target"]) for k in methods}
        calibrations.append({"pipeline": ri, "response": response, "models": models, "thresholds": thresholds,
                             "independent_threshold_maxima": maxima})
        print(f"Pipeline{ri+1}: calibration frozen; evaluating fresh sessions", flush=True)
        for si in range(protocol["test_sessions"]):
            sp = session_parameters(rng_for(base, ri, 5, si), config, protocol)
            session_log.append({"pipeline": ri, "session": si, **sp})
            n = protocol["test_records_per_class_per_session"]
            for ci, scenario in enumerate(protocol["scenarios"]):
                a = np.concatenate([np.zeros(n), rng_for(base, ri, 6, si, ci).choice([-1., 1.], n)*protocol["frequency_step_magnitude_hz"]])
                obs, hidden = generate(2*n, seed(base, ri, 7, si, ci), config, response, sp, protocol, a, scenario)
                scores = score_series(contrasts(obs, w), models)
                alarms = first_alarms(scores, thresholds, w)
                for key in methods:
                    rec = records[scenario["id"]][key]
                    rec["null_alarm"].extend(alarms[key][:n].tolist())
                    rec["event_alarm"].extend(alarms[key][n:].tolist())
                    rec["onset"].extend(hidden["onset_cycle"][n:].tolist())
                if ri == si == 0:
                    examples[scenario["id"]] = {k: np.asarray(v[n]).tolist() for k, v in hidden.items()}
                    examples[scenario["id"]].update({"observations": obs[n].tolist(), "session": sp,
                        "score_end_time_s": list(range(2*w, config.cycles+1)),
                        "scores": {k: v[n].tolist() for k, v in scores.items()}, "thresholds": thresholds,
                        "first_alarm_s": {k: int(v[n]) for k, v in alarms.items()}})
        print(f"Pipeline{ri+1}: all{len(protocol['scenarios'])} scenarios complete", flush=True)
    arrays = {}
    for s, by_method in records.items():
        for method, fields in by_method.items():
            for field, values in fields.items(): arrays[f"{s}__{method}__{field}"] = np.asarray(values, dtype=np.int16)
    np.savez_compressed(out/"record_outcomes.npz", **arrays)
    result = {"schema_version": 1, "evidence_type": "synthetic finite-pulse sensor and classical causal inference; no hardware data",
              "protocol": protocol, "config": asdict(config), "calibrations": calibrations,
              "test_session_parameters": session_log, "scenarios": summarize(records, protocol),
              "source_sha256": sources, "record_outcomes_sha256": sha(out/"record_outcomes.npz"),
              "created_utc": start["created_utc"], "mode": mode,
              "runtime": {"python": platform.python_version(), "numpy": np.__version__, "seconds": time.perf_counter()-t0},
              "uncertainty": "95% hierarchical percentile bootstrap: calibration pipelines then sessions; only8 independent pipeline repetitions, conditional on assumed distributions. Descriptive intervals, no multiplicity correction.",
              "false_alarm_unit": "Any first alarm during a128s frequency-null record; not per-sample or per-hour FPR.",
              "operational_rule": "Stop at first alarm. Pre-onset alarms cannot count as event detections.32s restricted delay penalizes misses and pre-onset alarms.",
              "resource_note": "Same frozen source-photon bookkeeping; apparatus/LO/atomic support resources remain unmatched. All computations local; no IBM API used."}
    (out/"results.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    (out/"example_traces.json").write_text(json.dumps(examples, indent=2, allow_nan=False), encoding="utf-8")
    plots(result, examples, out)
    for scenario in result["scenarios"]:
        print(scenario["id"]+": "+"; ".join(f"{key} detect32={scenario['methods'][key]['detection_within_32s']:.3f}, FPR={scenario['methods'][key]['false_alarm_rate']:.3f}" for key in methods if key != "power_only"), flush=True)
    print(f"Finished in{time.perf_counter()-t0:.1f}s. Output:{out}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="Separate tiny software exercise, never the main evaluation")
    args = p.parse_args()
    protocol = json.loads((HERE/"protocol.json").read_text(encoding="utf-8"))
    if args.smoke:
        protocol.update(base_seed=343050, outer_calibrations=2, fit_sessions=2,
                        fit_records_per_session=4, threshold_sessions=24,
                        test_sessions=2, test_records_per_class_per_session=3,
                        response_scan_repetitions_per_setting=16, bootstrap_repetitions=30)
    run(args.out, protocol, "software_smoke" if args.smoke else "main")
