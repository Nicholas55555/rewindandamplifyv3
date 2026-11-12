"""Plot fixed saved estimates and measured areas; never recompute an estimator."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis import sha256

HERE = Path(__file__).resolve().parent


def main():
    result = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    colors = ["#236ca4", "#cb7a24", "#67862f"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.0), gridspec_kw={"height_ratios": [1.0, 1.15]})
    for i, case in enumerate(result["cases"]):
        ax = axes[0, i]
        for pol, color, label in [("cross", "#8d969e", "Cross-polarized"),
                                  ("co", colors[i], "Co-polarized")]:
            data = np.loadtxt(HERE.parent / "reference_hom" / case["sources"][pol], delimiter=",", skiprows=1)
            ex = case["extractions"][pol]
            t = data[:, 0] / 1000 - ex["peaks"]["0"]["center_ns"]
            reference_mean = case["reference_diagnostics"][pol]["mean"]
            mask = np.abs(t) <= 4
            ax.step(t[mask], data[mask, 1] / reference_mean / .05,
                    where="mid", color=color, lw=1.35, label=label)
        ax.axvspan(-2, 2, color=colors[i], alpha=.07)
        ax.axvline(-2, color="#69727a", ls=":", lw=1)
        ax.axvline(2, color="#69727a", ls=":", lw=1)
        ax.set(xlim=(-4, 4), ylim=(0, .65), xlabel="Registered coincidence delay (ns)",
               title=f"Generation separation {case['excitation_separation_ns']:g} ns")
        if i == 0:
            ax.set_ylabel("Counts / mean reference area / ns")
            ax.legend(frameon=False, loc="upper left", fontsize=9)
        ax.text(.97, .92, "Primary area: ±2 ns", transform=ax.transAxes, ha="right", fontsize=9)

    ax = axes[1, 0]
    for i, case in enumerate(result["cases"]):
        p = case["primary"]
        for offset, key, ci_key, marker, color in [(-.15, "corrected_visibility", "corrected_interval95", "o", colors[i]),
                                                 (.15, "co_only_corrected_visibility", "co_only_corrected_interval95", "s", "#8d969e")]:
            y, ci = p[key], p[ci_key]
            ax.errorbar(i+offset, y, yerr=[[y-ci[0]], [ci[1]-y]], fmt=marker,
                        color=color, capsize=4, ms=6)
    ax.set(xticks=range(3), xticklabels=[f"{c['excitation_separation_ns']:g}" for c in result["cases"]],
           xlabel="Generation separation (ns)", ylabel="Corrected interference contrast",
           xlim=(-.5, 2.5), ylim=(.75, .85), title="Conditional estimates and normalization check")
    ax.plot([], [], "o", color="#236ca4", label="Co/cross ratio (primary)")
    ax.plot([], [], "s", color="#8d969e", label="Co-only 1−2A diagnostic")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.grid(axis="y", alpha=.18)

    ax = axes[1, 1]
    for i, case in enumerate(result["cases"]):
        for subtract, style in [(False, "-"), (True, "--")]:
            rows = [r for r in case["sensitivity"] if r["reference_set"] == "all_four" and r["subtract_background"] == subtract]
            ax.plot([r["half_width_ns"] for r in rows], [r["corrected_visibility"] for r in rows],
                    style, marker=".", color=colors[i], lw=1.6,
                    label=f"{case['excitation_separation_ns']:g} ns" if not subtract else None)
    ax.axvline(2, color="#69727a", ls=":", lw=1)
    ax.set(xlabel="Integration half-width (ns)", ylabel="Corrected co/cross contrast",
           title="Window and background sensitivity", ylim=(.75, .85))
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.text(.97, .94, "Solid: recorded counts\nDashed: local background removed",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5)
    ax.grid(axis="y", alpha=.18)

    ax = axes[1, 2]
    for i, case in enumerate(result["cases"]):
        p = case["primary"]
        y, ci = p["cross_central_reference_ratio"], p["cross_ratio_interval95"]
        ax.errorbar(i, y, yerr=[[y-ci[0]], [ci[1]-y]], fmt="o", color=colors[i], capsize=4, ms=7)
    ax.axhline(.5, color="#69727a", ls="--", lw=1)
    ax.set(xticks=range(3), xticklabels=[f"{c['excitation_separation_ns']:g}" for c in result["cases"]],
           xlabel="Generation separation (ns)", ylabel="Cross center / mean reference area",
           xlim=(-.5, 2.5), ylim=(.445, .52), title="Cross area differs from ideal reference")
    ax.text(.98, .95, "0.5: approximate ideal\nfor balanced inputs / splitter",
            transform=ax.transAxes, ha="right", va="top", fontsize=9)
    ax.grid(axis="y", alpha=.18)

    fig.suptitle("External GaAs quantum-dot data: useful interference contrast, conditional interpretation",
                 fontsize=17, fontweight="bold", y=.98)
    fig.text(.5, .025, "New side-peak-normalized analysis of Münzberg et al., Zenodo 6337697 (CC BY 4.0). No physical device measured by this project.\n"
             "Error bars: 95% conditional Poisson count / shared calibration intervals; exclude normalization systematics. No microscopic defect or switching-rate inference.",
             ha="center", fontsize=9, color="#4b555d")
    fig.subplots_adjust(left=.065, right=.98, top=.89, bottom=.14, wspace=.31, hspace=.4)
    for extension in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if extension == "pdf" else None
        fig.savefig(HERE / f"analysis.{extension}", dpi=180, facecolor="white", metadata=metadata)
    plt.close(fig)
    plot_manifest = {"results_sha256": sha256(HERE / "results.json"),
                     "plot_source_sha256": sha256(Path(__file__)),
                     "artifacts": {name: sha256(HERE / name) for name in ("analysis.png", "analysis.pdf")},
                     "scope": "Saved conditional estimates, fixed sensitivity sweep, and recorded raw histogram bins normalized by saved reference means"}
    (HERE / "plot_manifest.json").write_text(json.dumps(plot_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plot_manifest, indent=2))


if __name__ == "__main__":
    main()
