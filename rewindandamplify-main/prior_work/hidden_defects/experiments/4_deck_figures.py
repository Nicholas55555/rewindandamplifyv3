"""4 - Single-chart figures for the deck, drawn large from experiments 1 and 2's results.

Run with v1's environment, from the hackathon folder, after experiment 2's report:
  & "..\\Quantum research\\.venv\\Scripts\\python.exe" -B experiments\\4_deck_figures.py   (--quick: the quick run's)
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

HERE = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


w = _load("who_finds", HERE / "experiments" / "2_who_finds.py")
rep = _load("who_finds_report", HERE / "experiments" / "2_report.py")
style = _load("qlab_style", w.V1 / "qlab" / "style.py")
plt = style.plt
plt.rcParams.update({"font.size": 17, "axes.titlesize": 19, "axes.labelsize": 17, "xtick.labelsize": 15,
                     "ytick.labelsize": 15, "legend.fontsize": 15, "lines.linewidth": 2.2, "savefig.dpi": 200,
                     "figure.dpi": 100, "axes.titlepad": 14})
COLOR = {"physics": style.ORANGE, "physics+decoherence": style.AQUA, "physics+gate errors": style.GREEN,
         "free unitary": style.BLUE, "LSTM": style.VIOLET}
MARKER = {"physics": "o", "physics+decoherence": "D", "physics+gate errors": "*", "free unitary": "^", "LSTM": "s"}
SHORT = {"physics": "physics-shaped QRSM", "physics+decoherence": "+ decoherence", "free unitary": "free-unitary QRSM",
         "LSTM": "LSTM"}
FLOOR = 1e-5
SHARE_TICKS = ([1e-5, 1e-4, 1e-3, 1e-2, 0.05, 1], ["0.001%", "0.01%", "0.1%", "1%", "5%", "100%"])


def share_axis(ax) -> None:
    ax.set_yscale("log")
    ax.set_ylim(5e-6, 3)
    ax.set_yticks(SHARE_TICKS[0])
    ax.set_yticklabels(SHARE_TICKS[1])
    ax.minorticks_off()
    ax.axhline(0.05, color=style.MUTED, linewidth=1.2, linestyle=":")


def save(fig, out: Path, name: str) -> None:
    fig.savefig(out / name, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"  saved {name}")


def check_figure(out: Path) -> None:
    checks = json.loads((HERE / "results" / "1_qrsm_circuit" / "checks.json").read_text(encoding="utf-8"))
    ideal, device = checks["rows"]["ideal-k1-perfect"], checks["rows"]["device-k1"]
    steps = np.arange(1, len(ideal["rate_per_step"]) + 1)
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.plot(steps, ideal["exact_rate_per_step"], color=style.INK, label="exact model (v5)")
    ax.scatter(steps, ideal["rate_per_step"], s=34, color=style.BLUE, zorder=3, label="Qiskit circuit, perfect simulator")
    ax.scatter(steps, device["rate_per_step"], s=34, marker="s", color=style.ORANGE, zorder=3,
               label="Qiskit circuit, noisy IBM device simulator")
    ax.set_xlabel("step")
    ax.set_ylabel("chance of a click")
    ax.set_ylim(0, 0.13)
    ax.legend(loc="lower right", frameon=False)
    save(fig, out, "deck_check.png")


def who_finds_figure(data: dict, out: Path) -> None:
    names = [n for n in ("ideal-k1-perfect", "ideal-k1-good") if n in data]
    fig, ax = plt.subplots(figsize=(10, 6.4))
    jitter = np.random.default_rng(1)
    order = ["physics", "free unitary", "LSTM"]
    for i, name in enumerate(names):
        g = data[name]
        tru, mem = rep.truth_nll(w, name), rep.memoryless_nll(w, name)
        share = lambda c: max(float((np.mean(c) - tru.mean()) / (mem.mean() - tru.mean())), FLOOR)
        runs = {"physics": [g["physics"][1]] if 1 in g["physics"] else [], "free unitary": g["free"],
                "LSTM": g["lstm"]}
        for j, l in enumerate(order):
            ys = [share(r["count_nll"]) for r in runs[l]]
            if ys:
                x = i + (j - 1) * 0.26
                ax.scatter(x + jitter.uniform(-0.05, 0.05, len(ys)), ys, s=90 if l == "physics" else 60,
                           marker=MARKER[l], color=COLOR[l], edgecolors=style.SURFACE, linewidths=0.8, zorder=3,
                           label=SHORT[l] if i == 0 else None)
    share_axis(ax)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(["perfect detector", "good detector (50%)"][:len(names)])
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_ylabel("prediction error left\n(share of a memoryless guess's)")
    ax.text(len(names) - 0.42, 0.04, "found", ha="right", va="top", color=style.INK_2, fontsize=14)
    ax.text(len(names) - 0.42, 1.3e-5, "bottom line: as good as the truth", ha="right", fontsize=13,
            color=style.INK_2)
    ax.legend(loc="lower left", frameon=False, ncol=3, bbox_to_anchor=(0, 1.0))
    save(fig, out, "deck_who_finds.png")


def efficiency_figure(results: dict, out: Path) -> None:
    curve = results["curve"]
    ns = sorted(int(n) for n in curve)
    if not ns:
        return
    fig, ax = plt.subplots(figsize=(10, 6.2))
    for n in ns:
        ax.scatter([n] * len(curve[str(n)]["lstm_all"]), [max(v, FLOOR) for v in curve[str(n)]["lstm_all"]], s=40,
                   color=style.VIOLET, alpha=0.3, marker="s", zorder=2)
    ax.plot(ns, [max(curve[str(n)]["physics"], FLOOR) for n in ns], color=COLOR["physics"], marker="o",
            markersize=11, label="physics-shaped QRSM", zorder=3)
    ax.plot(ns, [max(curve[str(n)]["lstm"], FLOOR) for n in ns], color=COLOR["LSTM"], marker="s", markersize=10,
            label="LSTM (faint: every setting tried)", zorder=3)
    share_axis(ax)
    ax.set_xscale("log")
    ax.set_xticks(ns)
    ax.set_xticklabels([f"{n:,}" for n in ns])
    ax.minorticks_off()
    ax.set_xlabel("training records (64 steps each)")
    ax.set_ylabel("prediction error left\n(share of a memoryless guess's)")
    ax.legend(loc="upper right", frameon=False)
    save(fig, out, "deck_efficiency.png")


def device_figure(results: dict, out: Path) -> None:
    p = results["parameters"].get("device-k1", {})
    if "physics" not in p:
        return
    fig, ax = plt.subplots(figsize=(10, 5.6))
    labels = ["drive θ", "coupling φ", "detuning ζ"]
    ax.axvspan(-3, 3, color=style.NEUTRAL, zorder=0)
    ax.axvline(0, color=style.MUTED, linewidth=1)
    models = (("physics", "physics shape only"), ("physics+decoherence", "+ decoherence (T1, T2)"),
              ("physics+gate errors", "+ decoherence + gate errors"))
    for row, (l, name) in enumerate(models):
        if l not in p:
            continue
        ys = np.arange(3) + (row - 1) * 0.26
        ax.scatter(p[l]["z"], ys, s=260 if l == "physics+gate errors" else 120, marker=MARKER[l], color=COLOR[l],
                   zorder=3, label=name)
    ax.set_yticks(range(3))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xscale("symlog", linthresh=3)
    ax.set_xlim(-8, 20)
    ax.set_xticks([-5, -3, 0, 3, 5, 10])
    ax.set_xticklabels(["−5", "−3", "0", "3", "5", "10"])
    ax.minorticks_off()
    ax.set_xlabel("error ÷ its standard deviation (grey: within 3)")
    ax.legend(loc="lower left", frameon=False, bbox_to_anchor=(0, 1.0), ncol=2)
    save(fig, out, "deck_device_bias.png")


def decoherence_figure(results: dict, out: Path) -> None:
    entry = results["parameters"].get("device-k1", {}).get("physics+gate errors")
    if not entry or not entry.get("device"):
        return
    fig, ax = plt.subplots(figsize=(10, 5.8))
    labels = ["emitter\nrelaxation", "defect\nrelaxation", "emitter\ndephasing", "defect\ndephasing", "dark\ncounts"]
    fitted = np.array(entry["fit"]["relax"] + entry["fit"]["dephase"] + [entry["fit"]["p_dark"]]) * 100
    sds = np.array(entry["sd"][3:7] + [entry["sd"][9]]) * 100
    device = np.array(entry["device"]["relax"] + entry["device"]["dephase"] + [w.detector("device-k1")[1]]) * 100
    xs = np.arange(5)
    ax.scatter(xs, device, s=420, facecolors="none", edgecolors=style.INK, linewidths=1.8,
               label="the device's T1/T2 and readout calibration", zorder=2)
    ax.errorbar(xs, fitted, yerr=2 * sds, fmt="*", color=COLOR["physics+gate errors"], markersize=16,
                elinewidth=2, capsize=0, label="read from the clicks (±2 sd)", zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    ax.set_ylabel("chance per step (%)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", frameon=False)
    save(fig, out, "deck_decoherence.png")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    src = w.OUT / "quick" if args.quick else w.OUT
    out = HERE / "results" / "deck" / ("quick" if args.quick else "")
    out.mkdir(parents=True, exist_ok=True)
    results = json.loads((src / "results.json").read_text(encoding="utf-8"))
    data = rep.gather(rep.load_parts(src), w, args.quick)
    check_figure(out)
    who_finds_figure(data, out)
    efficiency_figure(results, out)
    device_figure(results, out)
    decoherence_figure(results, out)


if __name__ == "__main__":
    main()
