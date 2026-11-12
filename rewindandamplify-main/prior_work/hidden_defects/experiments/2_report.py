"""Report for experiment 2 (called by 2_who_finds.py --report): summary.md, results.json and the figure.

Every learner is scored on the same 4,096 held-out counting records of each dataset:
- log loss, and its gap to the best learner on that dataset (nats per record, with the paired standard error);
- on the perfect simulator's data, "share left": the loss above the truth's, as a share of a memoryless predictor's
  loss above the truth (v5's measure; under 5% counts as found);
- the count of defects, with experiment 5's rule;
- the true-size fit's errors against Cramer-Rao standard deviations.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

LEARNERS = ["physics", "physics+decoherence", "physics+gate errors", "free unitary", "LSTM"]
LABEL = {"physics": "physics-shaped QRSM", "physics+decoherence": "physics-shaped QRSM + decoherence",
         "physics+gate errors": "+ decoherence + gate errors", "free unitary": "free-unitary QRSM (black box)",
         "LSTM": "LSTM (black box)"}


def load_parts(out: Path) -> list:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((out / "parts").glob("*.json"))]


def memoryless_nll(w, name: str) -> np.ndarray:
    """A constant click rate, the training records' own, scored per counting record."""
    p = float(w.records(name)["train"][0].double().mean())
    Xc = w.records(name)["test"][0]
    n1 = Xc.sum(1).double()
    return (-(n1 * math.log(p) + (Xc.shape[1] - n1) * math.log(1 - p))).numpy()


def truth_nll(w, name: str) -> np.ndarray:
    """The true model's loss per counting record: only defined for the perfect simulator's data."""
    k = w.meta(name)["k_true"]
    hd = w.hd
    ops = hd.register_ops(k)
    U = hd.step_unitary(ops, hd.THETA, hd.PHI[:k], hd.ZETA[:k])[None]
    eta, p_dark = w.detector(name)
    with torch.no_grad():
        return torch.cat([hd.run_filter(U, x, eta, p_dark)[0][0] for x in w.records(name)["test"][0].split(1024)]).numpy()


def paired(a: np.ndarray, b: np.ndarray) -> tuple:
    diff = a - b
    return float(diff.mean()), float(diff.std(ddof=1) / math.sqrt(len(diff)))


def device_noise(w, name: str):
    """The device's relaxation and dephasing per step for the emitter and the defect, from its T1 and T2 over one
    step's duration: relax = 1 - exp(-t/T1), and dephase from the coherence factor exp(-t/T2) =
    sqrt(1 - relax) sqrt(1 - dephase)."""
    m = w.meta(name)
    if "qubits" not in m:
        return None
    out = {"relax": [], "dephase": []}
    for q in m["qubits"][:-1]:  # the memory qubits: emitter, then defects (the light is last)
        p, c = q["relax_per_step"], q["coherence_per_step"]
        out["relax"].append(p)
        out["dephase"].append(1 - c * c / (1 - p))
    return out


AT_ZERO = 1e-3  # a noise chance below this sits on the boundary, where the likelihood's curvature means nothing


def noisy_sd(w, name: str, k: int, nums: dict, extra: bool = False) -> list:
    """Cramer-Rao standard deviations of a noise-aware fit (theta, phi, zeta, relax, dephase, and with extra: flip
    and the dark-count rate), from all the training records. Noise chances at zero are held there (sd nan): on that
    boundary the Hessian is singular, which made the worker's own standard deviations all nan. Added after the run."""
    hd = w.hd
    X = w.records(name)["train"][0]
    ops = hd.register_ops(k)
    eta, p_dark = w.detector(name)
    flat = [nums["theta"]] + nums["phi"] + nums["zeta"] + nums["relax"] + nums["dephase"]
    if extra:
        flat += nums["flip"] + [nums["p_dark"]]
    v0 = torch.tensor(flat)
    free = [i for i in range(len(v0)) if i < 1 + 2 * k or v0[i] > AT_ZERO or (extra and i == len(v0) - 1)]

    def f(sub):
        v = v0.clone()
        v[free] = sub
        superops = (w.noisy_superops_at(k, v, ops, eta, p_dark, extra) if extra
                    else w.noisy_superops_at(k, v, ops, eta, p_dark))
        return hd.super_filter(*superops, X).sum()

    try:
        sd_free = w.sd_from_hessian(f, v0[free].clone())
    except TypeError:  # an experiment-2 module loaded before the extra model existed (the full run's own report)
        sd_free = [float("nan")] * len(free)
    out = [float("nan")] * len(v0)
    for i, s in zip(free, sd_free):
        out[i] = s
    return out


def gather(parts: list, w, quick: bool) -> dict:
    """Per dataset: the physics fits by size, the noise-aware fits by size, the free-unitary and LSTM runs."""
    one_settings, two_settings = w.search_settings(quick)
    data = {}
    for name in w.all_names():
        k_true = w.meta(name)["k_true"]
        g = {"k_true": k_true, "physics": {}, "noise": {}, "noise2": {}, "free": [], "lstm": [], "search": {}}
        screen = min(one_settings["screen"], w.n_train(name) or one_settings["screen"])
        o = {**one_settings, "screen": screen}
        for r in parts:
            if r.get("data") != name:
                continue
            if r["kind"] == "one" and r["key"] == w.one_key(name, o):
                g["physics"][0], g["physics"][1] = r["fit0"], r["fit1"]
                g["search"]["one"] = r
            elif r["kind"] == "two" and r["key"] == w.two_key(name, o, two_settings):
                g["physics"][2] = r["fit2"]
                g["search"]["two"] = r
            elif r["kind"] == "noise":
                g["noise2" if r.get("extra") else "noise"][r["k"]] = r
            elif r["kind"] == "free":
                g["free"].append(r)
            elif r["kind"] == "lstm":
                g["lstm"].append(r)
        if g["physics"] or g["lstm"]:
            data[name] = g
    return data


def best_by_val(runs: list):
    return min(runs, key=lambda r: r["val_nll"]) if runs else None


def learner_nll(g: dict) -> dict:
    """Each learner's loss per counting record at the true number of defects (the black boxes: the run chosen on
    the validation records)."""
    k = g["k_true"]
    out = {}
    if k in g["physics"]:
        out["physics"] = np.array(g["physics"][k]["count_nll"])
    if k in g["noise"]:
        out["physics+decoherence"] = np.array(g["noise"][k]["count_nll"])
    if k in g["noise2"]:
        out["physics+gate errors"] = np.array(g["noise2"][k]["count_nll"])
    if g["free"]:
        out["free unitary"] = np.array(best_by_val(g["free"])["count_nll"])
    if g["lstm"]:
        out["LSTM"] = np.array(best_by_val(g["lstm"])["count_nll"])
    return out


def report(out: Path, w) -> None:
    hd, sf, T = w.hd, w.sf, w.T
    parts = load_parts(out)
    data = gather(parts, w, out.name == "quick")
    main = [n for n in data if "@" not in n]
    results = {"datasets": {}}
    lines = ["# Experiment 2: who finds the hidden defect?", "",
             "Click records from the Qiskit circuit (experiment 1): an emitter driven by RY(0.6), one hidden defect "
             "(exchange phi = 0.45, detuning zeta = 0.3) and a light qubit (emission 0.2) read mid-circuit and reset "
             "every step. 4,096 training records of 64 steps, 512 validation records, and 4,096 held-out counting "
             "records on which everything below is scored. 'ideal': the perfect simulator, with a perfect detector "
             "or v5's good one (efficiency 0.5, dark counts 0.005 per step) applied afterwards. 'device': the "
             "FakeMarrakesh noise model on the transpiled, scheduled circuit, with its readout calibrated as the "
             "detector. k0: no defect, the controls.", ""]

    # --- prediction
    lines += ["## Predicting held-out clicks", "",
              "Loss per step (nats) of each learner at the true number of defects; the black boxes' run is the one "
              "chosen on the validation records. Gap: to the best learner on the dataset, in nats over all 4,096 "
              "counting records' mean per record (paired standard error). Share left (ideal data only): the loss "
              "above the truth's, as a share of a memoryless predictor's; under 5% counts as found.", "",
              "| data | memoryless | " + " | ".join(LABEL[l] for l in LEARNERS) + " |",
              "|---|---|" + "---|" * len(LEARNERS)]
    for name in main:
        g = data[name]
        nll = learner_nll(g)
        mem = memoryless_nll(w, name)
        ideal = w.meta(name)["source"] == "ideal"
        tru = truth_nll(w, name) if ideal else None
        best = min(nll, key=lambda l: nll[l].mean()) if nll else None
        row = {"memoryless": float(mem.mean() / T), "learners": {}}
        if ideal:
            row["truth"] = float(tru.mean() / T)
        cells = []
        for l in LEARNERS:
            if l not in nll:
                cells.append("-")
                continue
            gap, se = paired(nll[l], nll[best])
            entry = {"loss_per_step": float(nll[l].mean() / T), "gap": gap, "gap_se": se}
            text = f"{nll[l].mean() / T:.5f} (gap {gap:.3f} +- {se:.3f})"
            if ideal:
                share = float((nll[l].mean() - tru.mean()) / (mem.mean() - tru.mean()))
                entry["share"] = share
                text += f", share {share:.2%}"
            row["learners"][l] = entry
            cells.append(text)
        results["datasets"][name] = row
        lines.append(f"| {name} | {mem.mean() / T:.5f} | " + " | ".join(cells) + " |")

    # --- every black-box run
    lines += ["", "## Every black-box run", "",
              "Free unitary: v5's FreeHybrid at the true memory size, Adam from random starts with v5's short-to-long "
              "schedule. LSTM: hidden size, learning rate and seed; early stopping on the validation records.", "",
              "| data | learner | settings | numbers | validation loss per step | held-out loss per step | share left |",
              "|---|---|---|---|---|---|---|"]
    for name in main:
        g = data[name]
        ideal = w.meta(name)["source"] == "ideal"
        tru, mem = (truth_nll(w, name), memoryless_nll(w, name)) if ideal else (None, None)
        for r in sorted(g["free"], key=lambda r: (r["lr"], r["seed"])) + sorted(
                g["lstm"], key=lambda r: (r["hidden"], r["lr"], r["seed"])):
            c = np.array(r["count_nll"])
            share = f"{(c.mean() - tru.mean()) / (mem.mean() - tru.mean()):.2%}" if ideal else "-"
            settings = (f"lr {r['lr']}, seed {r['seed']}" if r["kind"] == "free"
                        else f"hidden {r['hidden']}, lr {r['lr']}, seed {r['seed']}, stopped at {r['best_step']}")
            lines.append(f"| {name} | {'free unitary' if r['kind'] == 'free' else 'LSTM'} | {settings} | "
                         f"{r['numbers']} | {r['val_nll'] / T:.5f} | {c.mean() / T:.5f} | {share} |")

    # --- counting
    lines += ["", "## Counting the defects", "",
              "Experiment 5's rule on the counting records: the smallest number of defects whose loss is within 2 "
              "paired standard errors, or 1 nat in total, of the lowest. Gaps in nats over all 4,096 records "
              "(standard errors).", "",
              "| data | true | physics: gaps | physics count | + decoherence: gaps | + decoherence count "
              "| + gate errors: gaps | + gate errors count |", "|---|---|---|---|---|---|---|---|"]
    counts = {}
    for name in main:
        g = data[name]
        row = {}
        cells = []
        for which in ("physics", "noise", "noise2"):
            fits = g[which]
            nll = {k: np.array(f["count_nll"]) for k, f in fits.items()}
            if len(nll) < 2:
                cells += ["-", "-"]
                continue
            chosen, stats = sf.choose_counting(nll)
            row[which] = {"chosen": chosen, "sizes": sorted(nll),
                          "gaps": {k: [gap * len(nll[k]), gap / se if se > 0 else 0.0]
                                   for k, (_, gap, se) in stats.items()}}
            cells += [", ".join(f"{k}: lowest" if gap == 0 else f"{k}: {gap * len(nll[k]):.1f} ({gap / se:.1f})"
                                for k, (_, gap, se) in stats.items()), str(chosen)]
        counts[name] = row
        lines.append(f"| {name} | {g['k_true']} | " + " | ".join(cells) + " |")
    results["counting"] = counts

    # --- the defect's numbers
    lines += ["", "## The hidden defect's numbers", "",
              "Errors after the symmetries (theta, phi, zeta), against Cramer-Rao standard deviations at each fit "
              "from all 4,096 training records (z = error / sd). For the noise-aware fit, the relaxation and "
              "dephasing chances per step of the emitter and the defect, against what the device's T1 and T2 give "
              "over one step; with gate errors also the depolarizing chance per step of each and the fitted "
              "dark-count rate (the calibration's in brackets).", "",
              "| data | learner | errors (rad) | sd | z | relaxation per step: emitter, defect (device) "
              "| dephasing per step: emitter, defect (device) | depolarizing per step; dark counts |",
              "|---|---|---|---|---|---|---|---|"]
    params = {}
    for name in main:
        g = data[name]
        if g["k_true"] != 1:
            continue
        dev = device_noise(w, name)
        entry = {}
        if 1 in g["physics"]:
            fit = g["physics"][1]["fit"]
            err = hd.aligned(fit, 1)
            sd = w.physics_sd(name, 1, fit)
            z = [e / s for e, s in zip(err, sd)]
            entry["physics"] = {"fit": fit, "errors": err, "sd": sd, "z": z}
            lines.append(f"| {name} | physics | " + ", ".join(f"{e:+.4f}" for e in err) + " | "
                         + ", ".join(f"{s:.4f}" for s in sd) + " | " + ", ".join(f"{v:+.1f}" for v in z)
                         + " | - | - | - |")
        fmt_noise = lambda vals, sds, ref: ", ".join(f"{v:.4f} +- {s:.4f}" for v, s in zip(vals, sds)) + (
            f" ({', '.join(f'{x:.4f}' for x in ref)})" if ref else "")
        for which, learner, label, extra in (("noise", "physics+decoherence", "+ decoherence", False),
                                             ("noise2", "physics+gate errors", "+ decoherence + gate errors", True)):
            if 1 not in g[which]:
                continue
            nums = g[which][1]["fit"]
            sd = noisy_sd(w, name, 1, nums, extra)
            err = hd.aligned(nums, 1)
            z = [e / s if s > 0 else float("nan") for e, s in zip(err, sd[:3])]
            entry[learner] = {"fit": nums, "errors": err, "sd": sd, "z": z, "device": dev}
            last = (fmt_noise(nums["flip"], sd[7:9], None) + f"; {nums['p_dark']:.4f} +- {sd[9]:.4f} "
                    f"({w.detector(name)[1]:.4f})") if extra else "-"
            lines.append(f"| {name} | {label} | " + ", ".join(f"{e:+.4f}" for e in err) + " | "
                         + ", ".join(f"{s:.4f}" for s in sd[:3]) + " | " + ", ".join(f"{v:+.1f}" for v in z) + " | "
                         + fmt_noise(nums["relax"], sd[3:5], dev["relax"] if dev else None) + " | "
                         + fmt_noise(nums["dephase"], sd[5:7], dev["dephase"] if dev else None) + f" | {last} |")
        params[name] = entry
    results["parameters"] = params

    # --- data efficiency
    curve = {}
    lines += ["", "## Data efficiency (ideal-k1-good)", "",
              "The same held-out records; fewer training records (the first 256 or 1,024 of the 4,096). The LSTM's "
              "configuration is chosen on the same 512 validation records at each size.", "",
              "| training records | physics: share left | LSTM, chosen on validation: share left | LSTM, best of all "
              "runs on held-out | LSTM numbers |", "|---|---|---|---|---|"]
    tru, mem = truth_nll(w, "ideal-k1-good"), memoryless_nll(w, "ideal-k1-good")
    share_of = lambda c: float((np.mean(c) - tru.mean()) / (mem.mean() - tru.mean()))
    for n in w.CURVE + [4096]:
        name = "ideal-k1-good" if n == 4096 else f"ideal-k1-good@{n}"
        g = data.get(name)
        if not g:
            continue
        phys = share_of(g["physics"][1]["count_nll"]) if 1 in g["physics"] else None
        chosen = best_by_val(g["lstm"])
        lstm = share_of(chosen["count_nll"]) if chosen else None
        lstm_best = min(share_of(r["count_nll"]) for r in g["lstm"]) if g["lstm"] else None
        curve[n] = {"physics": phys, "lstm": lstm, "lstm_best": lstm_best,
                    "lstm_all": [share_of(r["count_nll"]) for r in g["lstm"]],
                    "lstm_numbers": chosen["numbers"] if chosen else None}
        lines.append(f"| {n} | " + (f"{phys:.2%}" if phys is not None else "-") + " | "
                     + (f"{lstm:.2%}" if lstm is not None else "-") + " | "
                     + (f"{lstm_best:.2%}" if lstm_best is not None else "-") + " | "
                     + (str(chosen["numbers"]) if chosen else "-") + " |")
    results["curve"] = curve

    # --- costs
    lines += ["", "## Cost", ""]
    by_kind = {}
    for r in parts:
        if "quick" in r.get("key", ""):
            continue
        by_kind.setdefault(r["kind"], []).append(r["seconds"] / 60)
    lines += [f"- {kind}: {len(v)} runs, median {np.median(v):.1f} min, total {sum(v):.0f} worker-minutes"
              for kind, v in sorted(by_kind.items())]

    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("\n".join(lines))
    make_figure(data, results, w, out)


def make_figure(data: dict, results: dict, w, out: Path) -> None:
    spec = importlib.util.spec_from_file_location("qlab_style", w.V1 / "qlab" / "style.py")
    style = importlib.util.module_from_spec(spec)
    sys.modules["qlab_style"] = style
    spec.loader.exec_module(style)
    plt = style.plt
    color = {"physics": style.ORANGE, "physics+decoherence": style.AQUA, "physics+gate errors": style.GREEN,
             "free unitary": style.BLUE, "LSTM": style.VIOLET}
    marker = {"physics": "o", "physics+decoherence": "D", "physics+gate errors": "*", "free unitary": "^",
              "LSTM": "s"}
    T = w.T
    fig, axes = plt.subplots(2, 3, figsize=(19, 11.6), gridspec_kw={"hspace": 0.75, "wspace": 0.32})

    # (a) prediction on the perfect simulator's data: every run
    ax = axes[0, 0]
    ideal = [n for n in data if "@" not in n and w.meta(n)["source"] == "ideal"]
    jitter = np.random.default_rng(0)
    floor = 1e-5
    for i, name in enumerate(ideal):
        g = data[name]
        tru, mem = truth_nll(w, name), memoryless_nll(w, name)
        share = lambda c: max(float((np.mean(c) - tru.mean()) / (mem.mean() - tru.mean())), floor)
        groups = [("physics", [g["physics"][g["k_true"]]] if g["k_true"] in g["physics"] else [], -0.3),
                  ("physics+decoherence", [g["noise"][g["k_true"]]] if g["k_true"] in g["noise"] else [], -0.15),
                  ("physics+gate errors", [g["noise2"][g["k_true"]]] if g["k_true"] in g["noise2"] else [], 0.0),
                  ("free unitary", g["free"], 0.15), ("LSTM", g["lstm"], 0.3)]
        for l, runs, dx in groups:
            ys = [share(r["count_nll"]) for r in runs]
            if ys:
                ax.scatter(i + dx + jitter.uniform(-0.04, 0.04, len(ys)), ys, s=70 if l == "physics+gate errors" else 26,
                           marker=marker[l],
                           color=color[l], edgecolors=style.SURFACE, linewidths=0.6, zorder=3,
                           label=LABEL[l] if i == 0 else None)
    ax.axhline(0.05, color=style.MUTED, linewidth=1, linestyle=":")
    ax.set_yscale("log")
    ax.set_ylim(5e-6, 3)
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 0.05, 1])
    ax.set_yticklabels(["0.001%", "0.01%", "0.1%", "1%", "5%", "100%"])
    ax.minorticks_off()
    ax.set_xticks(range(len(ideal)))
    ax.set_xticklabels(ideal, fontsize=8.5)
    ax.set_ylabel("loss left, as a share of a memoryless predictor's")
    ax.set_title("Predicting new clicks, perfect simulator (below the line: found)")
    ax.text(0.99, 0.02, "on the bottom line: as good as the truth", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5, color=style.INK_2)
    ax.legend(fontsize=7.5, loc="upper left")

    # (b) data efficiency
    ax = axes[0, 1]
    curve = results["curve"]
    ns = sorted(int(n) for n in curve)
    phys = [max(curve[n]["physics"], floor) for n in ns]
    lstm = [max(curve[n]["lstm"], floor) for n in ns]
    for n in ns:
        ax.scatter([n] * len(curve[n]["lstm_all"]), [max(v, floor) for v in curve[n]["lstm_all"]], s=12,
                   color=style.VIOLET, alpha=0.35, marker="s", zorder=2)
    ax.plot(ns, phys, color=color["physics"], marker="o", label=LABEL["physics"], zorder=3)
    ax.plot(ns, lstm, color=color["LSTM"], marker="s", label="LSTM, chosen on validation (faint: every run)", zorder=3)
    ax.axhline(0.05, color=style.MUTED, linewidth=1, linestyle=":")
    ax.set_xscale("log")
    ax.set_xticks(ns)
    ax.set_xticklabels([f"{n:,}" for n in ns])
    ax.minorticks_off()
    ax.set_yscale("log")
    ax.set_ylim(5e-6, 3)
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 0.05, 1])
    ax.set_yticklabels(["0.001%", "0.01%", "0.1%", "1%", "5%", "100%"])
    ax.set_xlabel("training records (64 steps each)")
    ax.set_ylabel("loss left, as a share of a memoryless predictor's")
    ax.set_title("Data efficiency (good detector, 1 defect)")
    ax.legend(fontsize=7.5, loc="upper right")

    # (c) counting
    ax = axes[0, 2]
    main = [n for n in data if "@" not in n]
    for i, name in enumerate(main):
        c = results["counting"].get(name, {})
        ax.scatter(data[name]["k_true"], i, s=190, facecolors="none", edgecolors=style.INK, linewidths=1.2,
                   label="the truth" if i == 0 else None, zorder=2)
        for which, l, dy, label in (("physics", "physics", -0.18, "counted by the physics shape"),
                                    ("noise", "physics+decoherence", 0.0, "counted with decoherence"),
                                    ("noise2", "physics+gate errors", 0.18, "counted with decoherence + gate errors")):
            if which in c:
                first = not any(which in results["counting"].get(m, {}) for m in main[:i])
                ax.scatter(c[which]["chosen"], i + dy, s=46 if which == "noise2" else 34, color=color[l],
                           marker=marker[l], zorder=3, label=label if first else None)
    ax.set_yticks(range(len(main)))
    ax.set_yticklabels(main)
    ax.invert_yaxis()
    ax.set_xticks([0, 1, 2])
    ax.set_xlim(-0.6, 2.6)
    ax.set_xlabel("number of hidden defects")
    ax.set_title("Counting them (inside the ring: right)")
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)

    # (d) device: loss above the best learner
    ax = axes[1, 0]
    dev = [n for n in main if not n.startswith("ideal")]
    for i, name in enumerate(dev):
        row = results["datasets"][name]["learners"]
        for j, l in enumerate(LEARNERS):
            if l not in row:
                continue
            y = i + (j - 2) * 0.15
            ax.errorbar(row[l]["gap"], y, xerr=2 * row[l]["gap_se"], fmt=marker[l], color=color[l], markersize=6,
                        elinewidth=1, capsize=0, label=LABEL[l] if i == 0 else None, zorder=3)
    ax.axvline(0, color=style.MUTED, linewidth=1)
    ax.set_yticks(range(len(dev)))
    ax.set_yticklabels(dev)
    ax.invert_yaxis()
    ax.set_xscale("symlog", linthresh=0.01)
    ax.set_xlim(-0.004, 0.4)
    ax.set_xlabel("held-out loss above the best learner (nats per record; bars: 2 standard errors)")
    ax.set_title("Predicting new clicks, noisy device simulator")
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)

    # (e) device: the defect's numbers in standard deviations
    ax = axes[1, 1]
    names = ["theta", "phi", "zeta"]
    rows = [(n, l) for n in main if n in results["parameters"]
            for l in ("physics", "physics+decoherence", "physics+gate errors") if l in results["parameters"][n]]
    ax.axvspan(-3, 3, color=style.NEUTRAL, zorder=0)
    for i, (n, l) in enumerate(rows):
        z = results["parameters"][n][l]["z"]
        for j, (v, mk) in enumerate(zip(z, ("o", "s", "^"))):
            ax.scatter(v, i + (j - 1) * 0.16, s=30, marker=mk, color=color[l], zorder=3,
                       edgecolors=style.SURFACE, linewidths=0.5)
    ax.set_yticks(range(len(rows)))
    short = {"physics": "physics", "physics+decoherence": "+ decoherence", "physics+gate errors": "+ gate errors"}
    ax.set_yticklabels([f"{n}, {short[l]}" for n, l in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xscale("symlog", linthresh=3)
    ax.set_xlim(-8, 20)
    ax.set_xticks([-5, -3, 0, 3, 5, 10])
    ax.set_xticklabels(["-5", "-3", "0", "3", "5", "10"])
    ax.minorticks_off()
    ax.set_xlabel("error / Cramer-Rao standard deviation (circle theta, square phi, triangle zeta)")
    ax.set_title("The defect's numbers (grey band: within 3 sd)")

    # (f) decoherence read from the clicks
    ax = axes[1, 2]
    params = results["parameters"].get("device-k1", {})
    entry = params.get("physics+decoherence")
    if entry and entry.get("device"):
        labels = ["emitter\nrelaxation", "defect\nrelaxation", "emitter\ndephasing", "defect\ndephasing"]
        device = entry["device"]["relax"] + entry["device"]["dephase"]
        xs = np.arange(4)
        ax.scatter(xs, device, s=190, facecolors="none", edgecolors=style.INK, linewidths=1.2,
                   label="from the device's T1 and T2", zorder=2)
        for l, dx, text in (("physics+decoherence", -0.12, "read from the clicks, + decoherence"),
                            ("physics+gate errors", 0.12, "read from the clicks, + gate errors")):
            if l not in params:
                continue
            e = params[l]
            ax.errorbar(xs + dx, e["fit"]["relax"] + e["fit"]["dephase"], yerr=2 * np.array(e["sd"][3:7]),
                        fmt=marker[l], color=color[l], markersize=7, elinewidth=1, capsize=0,
                        label=text + " (bars: 2 sd)", zorder=3)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=8.5)
        ax.set_ylabel("chance per step")
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=7.5, loc="upper left")
    ax.set_title("Decoherence read from the clicks (device-k1)")
    style.figure_note(fig, "The Qiskit QRSM circuit's clicks (an emitter, one hidden defect and a light qubit read "
                           "mid-circuit every step), 4,096 training records of 64 steps; everything scored on 4,096 "
                           "held-out records. Top: the perfect simulator, where the truth is known. Bottom: the "
                           "FakeMarrakesh noise model, where the emitter and the defect also relax and dephase while "
                           "the light is read out. The physics shape knows the emission and the detector; the "
                           "decoherence version adds one relaxation and one dephasing chance per memory qubit, and "
                           "the gate-error version (added after the first results) also a depolarizing chance per "
                           "memory qubit and a fitted dark-count rate.")
    style.savefig(fig, out / "2_who_finds.png")
