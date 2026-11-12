"""Auditable area extraction; no fitted microscopic or waveform model."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import chi2

CYCLE_NS = 4000.0 / 76.2
REFERENCE_INDICES = (-2, -1, 1, 2)
REFERENCE_SETS = {"all_four": (-2, -1, 1, 2), "inner": (-1, 1),
                  "outer": (-2, 2), "negative": (-2, -1), "positive": (1, 2)}
WIDTHS_NS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
R_MEAN, R_SD, G_MEAN, G_SD = 0.514, 0.007, 0.016, 0.001


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_histograms(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "provenance_manifest.json").read_text(encoding="utf-8"))
    records = []
    for entry in manifest["files"]:
        if not entry["path"].startswith("HOM_"):
            continue
        path = folder / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"Raw source SHA-256 mismatch: {path.name}")
        if hashlib.md5(path.read_bytes()).hexdigest() != entry["zenodo_md5"]:
            raise ValueError(f"Published MD5 mismatch: {path.name}")
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        if (data.shape != (5000, 2) or
                not np.array_equal(data[:, 0], np.arange(-125000, 125000, 50)) or
                np.any(data[:, 1] < 0) or not np.all(data[:, 1] == np.floor(data[:, 1]))):
            raise ValueError(f"Unexpected histogram format: {path.name}")
        records.append({"source": entry, "time_ns": data[:, 0] / 1000,
                        "counts": data[:, 1].astype(np.int64)})
    if len(records) != 6:
        raise ValueError("Exactly six Figure 4 histograms are required")
    return manifest, records


def register_offset(time_ns, counts):
    """The central peak is excluded by construction; only ±1/±2 cycles used."""
    numer, denom = 0.0, 0.0
    for k in REFERENCE_INDICES:
        delta = time_ns - k * CYCLE_NS
        mask = np.abs(delta) < 3.0
        numer += float(np.sum(counts[mask] * delta[mask]))
        denom += float(np.sum(counts[mask]))
    if denom <= 0:
        raise ValueError("No counts for side-peak registration")
    step = float(time_ns[1] - time_ns[0])
    return float(np.round((numer / denom) / step) * step)


def peak_masks(time_ns, center_ns, half_width_ns):
    """Use integer source-bin offsets: deterministic equal half-open widths."""
    step = float(time_ns[1] - time_ns[0])
    index = int(np.rint((center_ns - time_ns[0]) / step))
    half_bins = int(np.rint(half_width_ns / step))
    if not np.isclose(half_bins * step, half_width_ns):
        raise ValueError("Window width must be a multiple of the bin spacing")
    offsets = np.arange(len(time_ns)) - index
    peak = (offsets >= -half_bins) & (offsets < half_bins)
    b4, b6 = int(np.rint(4 / step)), int(np.rint(6 / step))
    background = ((offsets >= -b6) & (offsets < -b4)) | ((offsets >= b4) & (offsets < b6))
    if peak.sum() != 2 * half_bins or background.sum() != 2 * (b6 - b4):
        raise ValueError("Window extends outside supplied histogram")
    if np.any(peak & background):
        raise ValueError("Peak and background must be disjoint")
    return peak, background, float(time_ns[index])


def extract(record, half_width_ns=2.0, shift_ns=0.0):
    time_ns, counts = record["time_ns"], record["counts"]
    offset = register_offset(time_ns, counts) + shift_ns
    peaks = {}
    occupied = np.zeros(len(counts), dtype=bool)
    for k in (0,) + REFERENCE_INDICES:
        peak, bg, center = peak_masks(time_ns, offset + k * CYCLE_NS, half_width_ns)
        if np.any(occupied & (peak | bg)):
            raise ValueError("Peak/background regions from different peaks overlap")
        occupied |= peak | bg
        peaks[str(k)] = {
            "center_ns": center, "count": int(counts[peak].sum()),
            "window_bins": int(peak.sum()), "background_count": int(counts[bg].sum()),
            "background_bins": int(bg.sum()),
        }
    return {"registration_offset_ns": offset, "half_width_ns": half_width_ns, "peaks": peaks}


def area(peak, subtract_background=False):
    if not subtract_background:
        return float(peak["count"])
    return peak["count"] - peak["window_bins"] / peak["background_bins"] * peak["background_count"]


def area_ratio(extraction, references=REFERENCE_INDICES, subtract_background=False):
    peaks = extraction["peaks"]
    mean_reference = np.mean([area(peaks[str(k)], subtract_background) for k in references])
    if mean_reference <= 0:
        raise ValueError("Nonpositive reference area")
    return float(area(peaks["0"], subtract_background) / mean_reference)


def correct_visibility(raw, reflectivity=R_MEAN, g2=G_MEAN):
    r, g = np.asarray(reflectivity), np.asarray(g2)
    if np.any((r <= 0) | (r >= 1)) or np.any((g < 0) | (g >= 1)):
        raise ValueError("Calibration outside physical domain")
    factor = (r * r + (1-r) ** 2) / (2 * r * (1-r))
    return (np.asarray(raw) + g) / (1-g) * factor


def point_metrics(co, cross, references=REFERENCE_INDICES, subtract_background=False,
                  ratio_multiplier=1.0):
    aco = area_ratio(co, references, subtract_background)
    across = area_ratio(cross, references, subtract_background)
    if across <= 0:
        raise ValueError("Nonpositive cross-polarized area")
    raw = 1 - ratio_multiplier * aco / across
    alt_raw = 1 - 2 * aco
    return {"co_central_reference_ratio": aco, "cross_central_reference_ratio": across,
            "raw_visibility": raw, "corrected_visibility": float(correct_visibility(raw)),
            "co_only_raw_visibility": alt_raw,
            "co_only_corrected_visibility": float(correct_visibility(alt_raw))}


def reference_diagnostic(extraction):
    values = np.array([extraction["peaks"][str(k)]["count"] for k in REFERENCE_INDICES])
    expected = float(values.mean())
    statistic = float(np.sum((values - expected) ** 2 / expected))
    return {"counts_in_order_negative2_negative1_positive1_positive2": values.tolist(),
            "mean": expected, "max_min_ratio": float(values.max() / values.min()),
            "equal_mean_pearson_statistic": statistic, "degrees_of_freedom": 3,
            "descriptive_poisson_p": float(chi2.sf(statistic, 3))}


def draw_calibration(rng, samples):
    r = rng.normal(R_MEAN, R_SD, samples)
    g = rng.normal(G_MEAN, G_SD, samples)
    invalid = (r <= 0) | (r >= 1) | (g < 0) | (g >= 1)
    rejected = 0
    while np.any(invalid):
        n = int(invalid.sum())
        rejected += n
        r[invalid] = rng.normal(R_MEAN, R_SD, n)
        g[invalid] = rng.normal(G_MEAN, G_SD, n)
        invalid = (r <= 0) | (r >= 1) | (g < 0) | (g >= 1)
    return r, g, rejected


def draw_area_ratio(extraction, rng, samples, subtract_background=False):
    draws = []
    for k in (0,) + REFERENCE_INDICES:
        peak = extraction["peaks"][str(k)]
        draw = rng.poisson(peak["count"], samples).astype(float)
        if subtract_background:
            draw -= peak["window_bins"] / peak["background_bins"] * rng.poisson(peak["background_count"], samples)
        draws.append(draw)
    denom = np.mean(draws[1:], axis=0)
    if np.any(denom <= 0):
        raise ValueError("Monte Carlo denominator nonpositive; approximation unsuitable")
    return draws[0] / denom


def summarize_draws(values):
    return {"sd": float(np.std(values, ddof=1)),
            "interval95": np.quantile(values, [0.025, 0.975]).tolist(),
            "monte_carlo_mean": float(np.mean(values))}


def monte_carlo(pairs, samples=200000, seed=63376972026, subtract_background=False):
    """Independent raw counts, common R/g2 across all separations and formulas."""
    rng = np.random.default_rng(seed)
    r, g, rejected = draw_calibration(rng, samples)
    cases, full_draws, calibration_draws = [], [], []
    for co, cross in pairs:
        ac = draw_area_ratio(co, rng, samples, subtract_background)
        ax = draw_area_ratio(cross, rng, samples, subtract_background)
        if np.any(ax <= 0):
            raise ValueError("Monte Carlo cross-area denominator nonpositive")
        raw = 1 - ac / ax
        alt_raw = 1 - 2 * ac
        full = correct_visibility(raw, r, g)
        count_only = correct_visibility(raw)
        point = point_metrics(co, cross, subtract_background=subtract_background)
        calibration_only = correct_visibility(point["raw_visibility"], r, g)
        alt = correct_visibility(alt_raw, r, g)
        full_draws.append(full)
        calibration_draws.append(calibration_only)
        cases.append({
            "corrected": summarize_draws(full), "raw": summarize_draws(raw),
            "co_only_corrected": summarize_draws(alt),
            "cross_central_reference_ratio": summarize_draws(ax),
            "count_only_sd": float(np.std(count_only, ddof=1)),
            "calibration_only_sd": float(np.std(calibration_only, ddof=1)),
            "co_only_minus_cocross_corrected": summarize_draws(alt - full),
        })
    difference = []
    for i in range(len(full_draws)):
        for j in range(i+1, len(full_draws)):
            difference.append({"first_case_index": i, "second_case_index": j,
                               **summarize_draws(full_draws[j] - full_draws[i])})
    return {"samples": samples, "seed": seed, "rejected_calibration_draws": rejected,
            "cases": cases, "paired_differences_second_minus_first": difference,
            "corrected_covariance": np.cov(np.array(full_draws)).tolist(),
            "calibration_only_covariance": np.cov(np.array(calibration_draws)).tolist()}
