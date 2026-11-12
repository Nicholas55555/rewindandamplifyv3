"""Spatial, synthetic photon-dose example for a missing lithography contact.

This is a classical Monte Carlo model, not a calibrated EUV process. Independent
Poisson absorption counts are blurred with a Gaussian kernel as a crude proxy
for energy spreading, and the average response within a 3x3 contact is compared
with a threshold. The output is dimensionless. It does not model resist
chemistry, photon wavelength, multiple material layers or real wafer data.

The importance sampler changes the Poisson means only in a 5x5 central region.
Its likelihood ratio is the exact target/proposal probability of each complete
count map. Nothing about this model requires or simulates quantum hardware.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter


GRID_SIZE = 7
ROI = (slice(2, 5), slice(2, 5))


def proposal_rates(dose: float, tilt: float) -> np.ndarray:
    """Return a Poisson proposal that reduces dose in the central 5x5 cells."""
    if not np.isfinite(dose) or dose <= 0:
        raise ValueError("dose must be finite and positive")
    if not np.isfinite(tilt) or not 0 < tilt <= 1:
        raise ValueError("tilt must be in (0, 1]")
    rates = np.full((GRID_SIZE, GRID_SIZE), dose, dtype=float)
    rates[1:6, 1:6] *= tilt
    return rates


def response(counts: np.ndarray, blur: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    """Blur each independent count map and return its central-contact mean."""
    if counts.ndim != 3 or counts.shape[1:] != (GRID_SIZE, GRID_SIZE):
        raise ValueError("counts must have shape (records, 7, 7)")
    if not np.isfinite(blur) or blur <= 0:
        raise ValueError("blur must be finite and positive")
    blurred = gaussian_filter(counts.astype(float), sigma=(0, blur, blur), mode="constant")
    return blurred, blurred[:, ROI[0], ROI[1]].mean(axis=(1, 2))


def likelihood_ratio(counts: np.ndarray, dose: float, rates: np.ndarray) -> np.ndarray:
    """Evaluate dP/dQ for complete count maps under independent Poisson laws."""
    if counts.ndim != 3 or counts.shape[1:] != (GRID_SIZE, GRID_SIZE):
        raise ValueError("counts must have shape (records, 7, 7)")
    if not np.isfinite(dose) or dose <= 0:
        raise ValueError("dose must be finite and positive")
    if rates.shape != (GRID_SIZE, GRID_SIZE) or not np.all(np.isfinite(rates)) or np.any(rates <= 0):
        raise ValueError("rates must contain finite positive 7x7 Poisson means")
    return np.exp(np.sum(rates - dose + counts * np.log(dose / rates), axis=(1, 2)))


def run(dose: float = 1.5, threshold: float = 0.8, tilt: float = 0.6,
        blur: float = 0.8, shots: int = 20000, seed: int = 77) -> dict:
    """Compare direct sampling and fixed-proposal importance sampling.

    Both methods sample the same number of independent maps. Estimated errors
    are sample standard errors; no interval is asserted when there are no hits.
    """
    if not isinstance(shots, int) or shots < 2:
        raise ValueError("shots must be an integer >= 2")
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive")
    rates = proposal_rates(dose, tilt)
    direct_rng, proposal_rng = np.random.default_rng(seed), np.random.default_rng(seed + 1)
    direct = direct_rng.poisson(dose, size=(shots, GRID_SIZE, GRID_SIZE))
    proposal = proposal_rng.poisson(rates, size=(shots, GRID_SIZE, GRID_SIZE))
    direct_blur, direct_scores = response(direct, blur)
    proposal_blur, proposal_scores = response(proposal, blur)
    direct_fail = direct_scores < threshold
    proposal_fail = proposal_scores < threshold
    weights = likelihood_ratio(proposal, dose, rates)
    weighted_failures = weights * proposal_fail

    def summary(contributions: np.ndarray, hits: int) -> dict:
        sample_sd = float(contributions.std(ddof=1))
        return {"failure_rate_estimate": float(contributions.mean()),
                # With no variation in sampled contributions, a plug-in SE
                # of zero would give unjustified confidence in a rare event.
                "standard_error": sample_sd / np.sqrt(shots) if sample_sd else None,
                "observed_failures": int(hits), "records": shots}

    weighted_total = float(weighted_failures.sum())
    weighted_sq_total = float(np.square(weighted_failures).sum())
    weighted_ess = weighted_total**2 / weighted_sq_total if weighted_sq_total else 0.0
    # Choose a real simulated failing map for the figure, never a hand-picked
    # purported wafer measurement. The choice is illustrative, not inference.
    where = np.flatnonzero(direct_fail)
    if len(where):
        idx = int(where[0])
        example = {"source": "direct target simulation", "absorption_counts": direct[idx].tolist(),
                   "blurred_response": direct_blur[idx].tolist(), "contact_mean": float(direct_scores[idx])}
    else:
        where = np.flatnonzero(proposal_fail)
        example = None
        if len(where):
            idx = int(where[0])
            example = {"source": "importance proposal simulation", "absorption_counts": proposal[idx].tolist(),
                       "blurred_response": proposal_blur[idx].tolist(), "contact_mean": float(proposal_scores[idx])}

    return {"model": {"grid": [GRID_SIZE, GRID_SIZE], "contact_cells": [3, 3],
                      "dose_mean_per_cell": dose, "blur_sigma_cells": blur,
                      "failure_threshold": threshold, "central_proposal_multiplier": tilt,
                      "shots_per_method": shots, "seed": seed,
                      "scope": "Synthetic dimensionless Poisson/blur/threshold model; not calibrated wafer physics"},
            "direct": summary(direct_fail.astype(float), int(direct_fail.sum())),
            "importance": {**summary(weighted_failures, int(proposal_fail.sum())),
                           "failure_weight_effective_sample_size": weighted_ess},
            "example": example}


def render(result: dict, output: Path) -> None:
    """Save an explanatory figure using the actual simulated example and estimates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    ex = result["example"]
    if ex is None:
        raise ValueError("no failing example was sampled; increase shots or threshold")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout="constrained")
    fig.suptitle("A simulated missing contact: absorption, spreading, and analysis", fontsize=14, weight="bold")
    image = axes[0].imshow(ex["absorption_counts"], cmap="Blues", interpolation="nearest", vmin=0)
    fig.colorbar(image, ax=axes[0], fraction=.05, pad=.03, label="counts / cell")
    axes[0].set_title("1. Absorbed photons\n(synthetic Poisson counts)")
    image = axes[1].imshow(ex["blurred_response"], cmap="magma", interpolation="nearest", vmin=0)
    fig.colorbar(image, ax=axes[1], fraction=.05, pad=.03, label="blurred response")
    axes[1].add_patch(Rectangle((1.5, 1.5), 3, 3, fill=False, edgecolor="cyan", linewidth=2))
    axes[1].set_title("2. Spread and threshold\ncyan: 3 × 3 contact")
    for ax in axes[:2]:
        ax.set_xlabel("cell")
        ax.set_ylabel("cell")
        ax.set_xticks([0, 2, 4, 6])
        ax.set_yticks([0, 2, 4, 6])
    estimates = [result["direct"], result["importance"]]
    means = [100 * e["failure_rate_estimate"] for e in estimates]
    axes[2].bar([0, 1], means, color=["#708c9a", "#268779"], width=.6)
    for i, estimate in enumerate(estimates):
        error = estimate["standard_error"]
        if error is not None:
            axes[2].errorbar(i, means[i], yerr=100 * error, color="#14252c", fmt="none", capsize=4)
        else:
            axes[2].annotate("SE unavailable", (i, means[i]), xytext=(0, 5),
                             textcoords="offset points", ha="center", fontsize=8)
    axes[2].set_xticks([0, 1], ["Direct", "Weighted\nimportance"])
    axes[2].set_ylabel("Estimated failure probability (%)")
    axes[2].set_title("3. Estimate the rare event\nerror bars: one standard error")
    axes[2].set_ylim(bottom=0)
    fig.text(.5, -.04, "Synthetic, dimensionless toy model • classical simulation • not measured wafer data",
             ha="center", fontsize=10, color="#5b5b5b")
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=77)
    parser.add_argument("--json-output", type=Path, help="save exact configuration, results, and example")
    parser.add_argument("--figure", type=Path, help="render a PNG figure")
    args = parser.parse_args()
    result = run(shots=args.shots, seed=args.seed)
    if args.json_output:
        args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.figure:
        render(result, args.figure)
    for key in ("direct", "importance"):
        item = result[key]
        error = f"{item['standard_error']:.6f}" if item['standard_error'] is not None else "unavailable (no sample variation)"
        print(f"{key}: failure estimate {item['failure_rate_estimate']:.6f}, SE {error}; "
              f"observed {item['observed_failures']}/{item['records']} failures")
    print("Synthetic classical model; no actual wafer data or quantum hardware.")


if __name__ == "__main__":
    main()
