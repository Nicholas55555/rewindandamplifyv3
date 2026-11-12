"""Check a synthetic spatial missing-contact model over a range of doses.

This deliberately dimensionless classical experiment is not a calibrated EUV
process or a quantum computation. For each dose, compare multiple independent
direct and weighted-proposal estimates of the same rare-event probability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from spatial_model import run


def study(doses=(1.2, 1.35, 1.5, 1.65, 1.8), *, shots=20000, repeats=10,
          seed=1000, tilt=.6):
    if repeats < 2:
        raise ValueError("at least two independent repeats are needed")
    rows = []
    for dose in doses:
        # Independent random streams within each dose: run uses seed and seed+1.
        results = [run(dose=dose, shots=shots, seed=seed + 2 * i, tilt=tilt)
                   for i in range(repeats)]
        row = {"dose_mean_per_cell": dose}
        for method in ("direct", "importance"):
            estimates = np.asarray([r[method]["failure_rate_estimate"] for r in results])
            within_ses = [r[method]["standard_error"] for r in results]
            row[method] = {
                "mean_estimate": float(np.mean(estimates)),
                "between_run_sd": float(np.std(estimates, ddof=1)),
                "mean_estimate_se_from_repeats": float(np.std(estimates, ddof=1) / np.sqrt(repeats)),
                "mean_within_run_se": float(np.mean([x for x in within_ses if x is not None]))
                                     if any(x is not None for x in within_ses) else None,
                "zero_failure_runs": int(sum(r[method]["observed_failures"] == 0 for r in results)),
                "estimates": estimates.tolist(),
            }
            if method == "importance":
                row[method]["median_event_weight_ess"] = float(np.median([
                    r[method]["failure_weight_effective_sample_size"] for r in results]))
        rows.append(row)
    return {"model": "Synthetic spatial Poisson absorption, Gaussian blur and contact threshold",
            "note": "Classical Monte Carlo, arbitrary dimensionless units; not a wafer measurement or quantum simulation.",
            "doses": list(doses), "shots_per_method_per_repeat": shots,
            "independent_repeats_per_dose": repeats, "first_seed": seed,
            "proposal_multiplier": tilt, "rows": rows}


def render(result, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.6), layout="constrained")
    for name, label, color in [("direct", "Direct sampling", "#547889"),
                               ("importance", "Weighted importance sampling", "#158c78")]:
        vals = [100 * r[name]["mean_estimate"] for r in result["rows"]]
        errs = [100 * r[name]["mean_estimate_se_from_repeats"] for r in result["rows"]]
        ax.errorbar(result["doses"], vals, yerr=errs, marker="o", capsize=3,
                    label=label, color=color)
    ax.set_yscale("log")
    ax.set_xlabel("Mean photons per cell (arbitrary units)")
    ax.set_ylabel("Estimated missing-contact probability (%)")
    ax.set_title("Toy spatial model: rarer failures at higher dose", weight="bold")
    ax.grid(True, alpha=.2, which="both")
    ax.legend()
    fig.text(.5, -.025, f"Synthetic model; mean ± 1 SE across {result['independent_repeats_per_dose']} repeats; "
             f"{result['shots_per_method_per_repeat']:,} maps per method per repeat",
             ha="center", fontsize=9, color="#555")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=int, default=20000)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()
    result = study(shots=args.shots, repeats=args.repeats, seed=args.seed)
    if args.json_output:
        args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.figure:
        render(result, args.figure)
    for r in result["rows"]:
        d, w = r["direct"], r["importance"]
        print(f"dose={r['dose_mean_per_cell']:.2f} direct={d['mean_estimate']:.6g} "
              f"±{d['mean_estimate_se_from_repeats']:.2g} weighted={w['mean_estimate']:.6g} "
              f"±{w['mean_estimate_se_from_repeats']:.2g}; zero-direct-runs={d['zero_failure_runs']}")
    print("Synthetic classical model: uncertainty excludes model error and proposal design costs.")


if __name__ == "__main__":
    main()
