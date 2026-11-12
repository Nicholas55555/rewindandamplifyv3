"""Run the fixed protocol, refusing to overwrite an existing analysis."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy

from analysis import (CYCLE_NS, G_MEAN, G_SD, R_MEAN, R_SD, WIDTHS_NS,
                      REFERENCE_SETS, extract, load_histograms, monte_carlo,
                      point_metrics, reference_diagnostic, sha256)

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "reference_hom"


def run(samples=200000):
    start = time.perf_counter()
    manifest, records = load_histograms(RAW)
    separations = sorted({x["source"]["excitation_pulse_separation_ns"] for x in records})
    by_case = []
    for separation in separations:
        pair = {x["source"]["polarization"]: x for x in records
                if x["source"]["excitation_pulse_separation_ns"] == separation}
        by_case.append(pair)
    pairs = [(extract(p["co"]), extract(p["cross"])) for p in by_case]
    mc = monte_carlo(pairs, samples=samples)
    # Secondary background-adjusted conditional intervals, never replace primary.
    background_mc = monte_carlo(pairs, samples=samples, seed=63376972027,
                               subtract_background=True)
    cases = []
    paper_values = [(.803, .005), (.826, .004), (.774, .004)]
    for index, (separation, pair, exts) in enumerate(zip(separations, by_case, pairs)):
        co, cross = exts
        point = point_metrics(co, cross)
        summary = mc["cases"][index]
        point.update({"corrected_interval95": summary["corrected"]["interval95"],
                      "corrected_sd": summary["corrected"]["sd"],
                      "count_only_sd": summary["count_only_sd"],
                      "calibration_only_sd": summary["calibration_only_sd"],
                      "cross_ratio_interval95": summary["cross_central_reference_ratio"]["interval95"],
                      "co_only_corrected_interval95": summary["co_only_corrected"]["interval95"],
                      "co_only_corrected_sd": summary["co_only_corrected"]["sd"]})
        sensitivity = []
        for width in WIDTHS_NS:
            ec, ex = extract(pair["co"], width), extract(pair["cross"], width)
            for subtract in (False, True):
                for name, references in REFERENCE_SETS.items():
                    sensitivity.append({"half_width_ns": width, "subtract_background": subtract,
                                        "reference_set": name,
                                        **point_metrics(ec, ex, references, subtract)})
        shifts = [{"shift_ns": shift, **point_metrics(extract(pair["co"], shift_ns=shift),
                                                     extract(pair["cross"], shift_ns=shift))}
                  for shift in (-.1, 0., .1)]
        scale = [{"ratio_multiplier": factor,
                  **point_metrics(co, cross, ratio_multiplier=factor)} for factor in (.95, 1., 1.05)]
        primary_background = point_metrics(co, cross, subtract_background=True)
        primary_background["corrected_interval95"] = background_mc["cases"][index]["corrected"]["interval95"]
        primary_background["corrected_sd"] = background_mc["cases"][index]["corrected"]["sd"]
        all_values = [row["corrected_visibility"] for row in sensitivity]
        broad_values = [row["corrected_visibility"] for row in sensitivity if row["half_width_ns"] >= 1.5]
        cases.append({
            "excitation_separation_ns": separation,
            "sources": {p: pair[p]["source"]["path"] for p in ("co", "cross")},
            "primary": point,
            "primary_with_background_subtraction": primary_background,
            "extractions": {"co": co, "cross": cross},
            "reference_diagnostics": {"co": reference_diagnostic(co), "cross": reference_diagnostic(cross)},
            "sensitivity": sensitivity, "registration_sensitivity": shifts,
            "illustrative_normalization_sensitivity": scale,
            "sensitivity_range_all_declared_variants": [min(all_values), max(all_values)],
            "sensitivity_range_halfwidth_ge_1_5_ns": [min(broad_values), max(broad_values)],
            "paper_reported": {"corrected_visibility": paper_values[index][0], "sd": paper_values[index][1],
                               "independent_comparison": False},
            "difference_from_printed_paper_value": point["corrected_visibility"] - paper_values[index][0],
        })
    source_files = ["analysis.py", "run_analysis.py", "test_analysis.py", "PROTOCOL.md"]
    return {
        "schema": "hom-area-analysis-v1",
        "scope": "New conditional side-peak-normalized reanalysis of external experimental histograms; not exact author-pipeline reproduction or microscopic inference",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_fixed_before_first_normalized_analysis": True,
        "source_sha256": {name: sha256(HERE / name) for name in source_files},
        "raw_sha256": {r["source"]["path"]: r["source"]["sha256"] for r in records},
        "reference_manifest_sha256": sha256(RAW / "provenance_manifest.json"),
        "attribution": {k: manifest[k] for k in ("source_authors", "dataset_doi", "record_url", "license", "paper_url")},
        "supplement_url": "https://arxiv.org/src/2203.08682v1/anc/supplementary_material.pdf",
        "configuration": {"cycle_ns": CYCLE_NS, "primary_half_width_ns": 2.0,
                          "primary_background_subtraction": False,
                          "references": [-2, -1, 1, 2],
                          "reflectivity_mean_sd": [R_MEAN, R_SD], "g2_mean_sd": [G_MEAN, G_SD]},
        "uncertainty_scope": "Conditional independent-Poisson count plus shared Gaussian R/g2 calibration; excludes normalization, source drift, polarization, routing and timing-response systematics",
        "missing_information": ["exact author integration windows and normalization pipeline", "per-acquisition exposure durations",
                                "event time tags/repeated acquisitions for covariance and stationarity", "per-HOM-run polarization/routing/brightness and matched R/g2 calibration covariance"],
        "cases": cases,
        "monte_carlo": mc, "background_subtracted_monte_carlo": background_mc,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "runtime_seconds": time.perf_counter() - start,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    parser.add_argument("--samples", type=int, default=200000)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite existing results; use a new --output path")
    if args.samples < 1000:
        raise SystemExit("Use at least 1000 Monte Carlo draws")
    results = run(args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "runtime_seconds": results["runtime_seconds"],
                      "cases": [{"separation_ns": c["excitation_separation_ns"],
                                 "V": c["primary"]["corrected_visibility"],
                                 "interval95": c["primary"]["corrected_interval95"],
                                 "A_cross": c["primary"]["cross_central_reference_ratio"],
                                 "co_only_V": c["primary"]["co_only_corrected_visibility"]}
                                for c in results["cases"]]}, indent=2))


if __name__ == "__main__":
    main()
