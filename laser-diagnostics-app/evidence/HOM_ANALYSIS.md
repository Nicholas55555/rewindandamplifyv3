# Measured quantum-dot HOM data: a conditional reanalysis

Six published GaAs quantum-dot coincidence histograms support a useful, reproducible interference analysis. Our fixed peak-area procedure gives corrected contrasts of **0.8024, 0.8258 and 0.7724**. The third value becomes **0.7938** with the alternative co-only normalization. That discrepancy is a practical reminder: interpreting source quality requires trustworthy measurement controls, as well as counts.

These are **external measurements**, analyzed here by classical software. The original experiment and data are by Julian Münzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil. The [dataset](https://doi.org/10.5281/zenodo.6337697) is CC BY 4.0; unchanged inputs and their [attribution](../reference_hom/DATA_LICENSE.md) remain in `../reference_hom/`. Our new extraction, uncertainty analysis and plots are separate from those original data.

## Results and what the uncertainty means

| Generation separation | Raw co/cross contrast | Corrected contrast | 95% conditional interval | Co-only corrected diagnostic |
|---|---:|---:|---:|---:|
| 13.1 ns | 0.7724 | 0.8024 | [0.7943, 0.8113] | 0.8063 |
| 26.2 ns | 0.7954 | 0.8258 | [0.8181, 0.8344] | 0.8271 |
| 39.4 ns | 0.7428 | 0.7724 | [0.7647, 0.7808] | 0.7938 |

The intervals include independent-Poisson counting uncertainty and the stated splitter/multiphoton calibration uncertainty. They **exclude normalization, polarization, routing, source drift and detector-response systematics**. They are parametric Monte Carlo intervals under those assumptions, not experimentally established coverage guarantees. The co-only column reuses the same data and is a diagnostic, not an independent measurement.

The paper reports 0.803(5), 0.826(4) and 0.774(4), and explicitly discusses the last pair's polarization-control concern. Our approximate agreement is reassuring computationally, but **does not reproduce an exactly specified author pipeline**: its precise windows, acquisition durations and complete normalization algorithm are not supplied. [Paper, Section IV](https://arxiv.org/html/2203.08682v1#S4)

![Conditional interference estimates and normalization checks](analysis.png)

[Full numerical output](results.json) · [PDF figure](analysis.pdf) · [Protocol fixed before calculation](PROTOCOL.md)

## Transparent extraction

The histogram axis is detection-time difference. The row labels above are separation at **photon generation**, not the locations of the histogram's central peaks.

The routing cycle is four excitation periods, about 52.49 ns. We normalize to the four main reference peaks at ±1 and ±2 cycles; smaller intervening routing peaks are excluded. Registration uses only those reference peaks, giving an electronic offset of −0.25 ns in every file. We integrate **±2 ns half-open windows** around bin-aligned centers, with no primary background subtraction. Each acquisition has its own reference mean, so unequal overall acquisition scales cancel under the stable-reference assumption. This does not equate photon fluxes or prove stability.

For each polarization, `A = central area / mean reference area`. Then

```text
Vraw = 1 − Aco / Across
Vcorrected = (Vraw + g) / (1 − g) × [R² + (1−R)²] / [2R(1−R)]
```

The correction follows the paper's Eq. 4, using `R=0.514±0.007` and `g=g⁽²⁾(0)=0.016±0.001`. Here `g⁽²⁾(0)` denotes the conventional second-order correlation, written `g2` in code. The diagnostic instead uses `Vraw = 1−2Aco`. [Paper, Eqs. 3–4](https://arxiv.org/html/2203.08682v1#S4)

Two hundred thousand count/calibration draws propagate the ratio nonlinearity. The **same** R and g draw is shared across all three generation separations, preserving their calibration covariance; R and g are assumed mutually independent because their covariance is unavailable. No corrected value is clipped. Numerical registration is held fixed within the Monte Carlo and separately stress-tested by ±0.1 ns.

## Sensitivity is separate from statistical precision

The predeclared sweep covers seven half-widths (0.5–4 ns), five reference subsets and two background treatments: **70 variants per pair**. Local background uses disjoint strips 4–6 ns from each peak center. The narrowest windows deliberately truncate peak tails. These alternative procedures are not independent experiments or a probability distribution over systematics.

| Separation | Range across all 70 variants | Primary window with local background removed | ±5% normalized-ratio stress |
|---|---:|---:|---:|
| 13.1 ns | 0.7980–0.8144 | 0.8052 | 0.7909–0.8140 |
| 26.2 ns | 0.8221–0.8393 | 0.8293 | 0.8154–0.8363 |
| 39.4 ns | 0.7691–0.7877 | 0.7744 | 0.7593–0.7855 |

The ±5% ratio perturbation is an illustrative assumption, **not a data-derived error bound**. Main reference areas within each acquisition agree to about 1% or better, and ±0.1 ns shifts alter primary contrast by less than 0.0002. Those checks do not constrain a shared reference bias or a polarization-dependent change.

The cross-polarized center/reference ratios are **0.4916, 0.4969 and 0.4591**. The last lies clearly below the approximate 0.5 balanced-input idealization. Consequently its co-only normalization changes corrected contrast by about 0.0214, much more than its conditional standard deviation of 0.0041. Imperfect orthogonality is one plausible explanation; intensity imbalance, routing and other differential effects are not excluded by these files.

## What this adds, and what remains unidentified

This analysis connects the project to a real semiconductor-photon observable. It demonstrates how to extract an interference statistic, propagate shared calibration, and expose a control limitation instead of treating an attractive point estimate as a defect diagnosis. It is a suitable reference for a future QRSM observation model; **no QRSM has been fitted to these histograms here**. The separate [illustrative dot model](../README.md) is not calibrated or validated by this agreement.

Without the stable-reference assumption, an unknown relative acquisition/normalization scale can change the co/cross ratio and hence the inferred contrast. Even with a known contrast, source-state overlap, polarization overlap and temporal overlap can produce the same effective two-photon interference. For example, under an ideal single-photon model, an overlap reduction in the source state can trade against a polarization mismatch. These aggregate data cannot distinguish those explanations uniquely.

We therefore **do not fit a charge-trap switching rate, microscopic defect, pure-dephasing rate or unique photon density matrix**, and do not claim a monotonic deterioration with delay. Useful next evidence would be independently documented integration and normalization, matched polarization/brightness/routing controls, per-run R and g2 calibration, repeated time-tagged acquisitions, and a broader range of pulse separations. The unrelated 15-hour count-rate record is not a substitute for these per-HOM controls. The [supplement](https://arxiv.org/src/2203.08682v1/anc/supplementary_material.pdf) documents separate acquisitions and changed alignment conditions, reinforcing why records must not be silently combined.

No new physical experiment, QPU run, quantum advantage, photolithography process validation or semiconductor fault diagnosis is claimed. No IBM credential is needed to reproduce this work.

## Reproduce

From the repository root:

```bash
python -m pip install -r quantum_dot_bridge/hom_analysis/requirements.txt
python -m unittest discover -s quantum_dot_bridge/hom_analysis -p test_analysis.py -v
python quantum_dot_bridge/hom_analysis/run_analysis.py --output /path/to/new-results.json
python quantum_dot_bridge/hom_analysis/verify_results.py
python quantum_dot_bridge/hom_analysis/independent_check.py
python quantum_dot_bridge/hom_analysis/plot_analysis.py
```

The runner refuses to overwrite a saved result. `--samples` is available for explicit alternative runs; the canonical analysis uses 200,000. The source and raw-file hashes, versions, seed, calibration covariance, exact areas, all variants and intervals are saved in `results.json`. The independent standard-library implementation originated with a separate reviewer and uses no analysis-module imports; it checks areas, contrasts and a delta-method counting uncertainty. Fourteen tests cover known synthetic contrasts, normalization scale cancellation, background, timing, correction conventions and shared calibration. These are computational checks, not proof of physical-model adequacy.
