# Conditional HOM peak-area reanalysis protocol

Specified on 2026-11-11 before the first calculation of normalized visibilities in this module. This is a locally recorded analysis plan, not an externally registered protocol. The six raw histograms and the published answers were already visible; the published answers will not select windows, normalization or corrections. An initial shape audit inspected only the four main side-peak positions and their centroids (roughly −0.23 ns electronic offset). This protocol is included in the result source hashes.

## Question and identifiable endpoint

Can a transparent peak-area normalization of the six unchanged Figure 4 GaAs quantum-dot histograms yield useful interference contrasts, and how sensitive are they to integration and normalization assumptions? This is an independent conditional reanalysis, **not a reproduction of an exactly specified author pipeline**, physical device validation, QRSM fit or defect diagnosis.

Primary sources read: Münzberg et al., [arXiv:2203.08682v1, Section IV, Eqs. 3–4](https://arxiv.org/html/2203.08682v1#S4), [all supplementary sections S1–S9](https://arxiv.org/src/2203.08682v1/anc/supplementary_material.pdf), [Zenodo 6337697](https://doi.org/10.5281/zenodo.6337697) and its unchanged mapping README. The CSVs and these documents do not specify the exact Figure 4 integration windows, per-acquisition durations, full normalization algorithm or calibration covariance. No filename time is treated as a duration. Other acquisitions are not substituted as calibration records.

## Fixed extraction rule

1. Read the six files named in `../reference_hom/provenance_manifest.json`; verify SHA-256 and format. The time axis is coincidence delay, not photon generation separation. Pair labels 13.1, 26.2 and 39.4 ns are generation separations.
2. At a 76.2 MHz excitation repetition rate, four-pulse routing cycles repeat every `4000/76.2` ns ≈52.4934 ns. The main uncorrelated reference peaks are at cycle indices −2, −1, +1, +2. Peaks between these arise from routing errors and are not normalization references. Use the period from the stated repetition rate, not a fit.
3. Estimate an electronic timing offset separately for each histogram: pool count-weighted offsets from the four reference peaks inside ±3 ns of their nominal positions, then round the pooled offset to the nearest 50 ps bin. Never use the central peak to register timing. Each final peak center is the nominal position plus this offset rounded to the nearest source bin. Use equal-width half-open windows `[center−h, center+h)` to obtain equal bin counts. The primary half-width is **2 ns**, wide compared with the reported 167 ps radiative lifetime, while staying clear of the adjacent 13.1 ns routing peaks. This choice does not assert the unknown APD impulse response is 167 ps.
4. Primary analysis uses recorded areas without background subtraction. For each acquisition define `A = central counts / mean(four reference counts)`. The raw contrast is `1−A_co/A_cross`. This cancels an acquisition-wide multiplicative scale **if** reference coincidence probabilities are stable and comparable across polarization acquisitions. It does not remove changing routing, brightness imbalance, polarization errors or other differential effects.
5. Apply the paper's stated correction, `V = (Vraw+g)/(1−g) * (R²+(1−R)²)/(2R(1−R))`, using `R=.514`, `g=.016`. Keep corrected values unbounded; do not clip statistical outputs to [0,1]. Also calculate the paper's alternative co-only contrast `1−2A_co`, corrected the same way, as a normalization diagnostic rather than an independent replicate or a better selected answer.

## Fixed uncertainty calculation

Use 200,000 parametric Monte Carlo draws, seed 63376972026. Independently Poisson-resample the disjoint central and individual reference area counts at their observed means. Draw one `R ~ Normal(.514,.007)` and one `g ~ Normal(.016,.001)` **per draw, shared across all three generation separations and both contrast formulas**. Interpret quoted calibration uncertainties as one standard deviation; assume R and g independent because their covariance is unavailable. Reject unphysical calibration draws, not contrast draws. Save the corrected covariance matrix and paired differences. Report plug-in point estimates, Monte Carlo standard deviations and 2.5/97.5 percentiles. Separately report count-only and calibration-only standard deviations.

These are **conditional counting/calibration uncertainty intervals**, not calibrated coverage guarantees and not total experimental uncertainty. The independent-Poisson approximation cannot be checked for slow drift or event-pair correlations without time-tag records or repeated acquisitions. Timing registration is conditioned on the observed side peaks; the fixed registration-offset sensitivity below addresses only bounded numerical shifts, not a distribution of all timing errors.

## Predeclared diagnostics (do not select a preferred answer afterward)

- Half-widths: 0.5, 0.75, 1, 1.5, 2, 3, 4 ns. The narrowest windows are deliberately stress tests, not equally justified whole-peak estimates.
- At every width, evaluate no background subtraction and local constant-background subtraction. For each peak independently, estimate per-bin background from offsets `[−6,−4)` and `[4,6)` ns relative to its registered center. Subtract the expected number of background counts in that peak's integration window, preserving signed net counts. These sidebands assume locally flat background and no substantial peak tails; disagreement is a sensitivity, not a fitted correction.
- At every width/background choice use references: all four, inner pair (±1 cycle), outer pair (±2 cycles), negative pair, positive pair. Save all 70 variants. These are not 70 independent experiments.
- At the primary width/no-background/all-four setting, shift the common registered centers by −0.1, 0, +0.1 ns and report changes.
- Report each reference area and an equal-Poisson-mean Pearson dispersion diagnostic (3 degrees of freedom for four areas); treat it descriptively, without using a p-value to select normalization.
- Report `A_cross`, its conditional interval, and its difference from 0.5. Approximately half a reference area is the balanced-source/balanced-splitter idealization used by the paper's co-only alternative; this is not a universal property of arbitrary input intensities or routing. A discrepancy does not uniquely identify polarization error.
- Explicitly perturb the normalized co/cross ratio by ±5% (multipliers .95,1,1.05), displaying the resulting corrected contrasts. This is an illustrative nuisance stress, **not** an inferred systematic-error bound.
- Compare with the three printed paper values only after the fixed computations. Do not call agreement an independent experimental validation, nor combine these reanalyses with author errors as if independent data.

## Tests, outputs and stopping point

Tests will include a synthetic known-visibility ratio, arbitrary acquisition-scale cancellation, zero/complete interference, splitter correction limits, side-peak-only registration, equal nonoverlapping windows, local background subtraction, shared-calibration covariance and source integrity. Produce `results.json`, `analysis.png`/PDF and reproducible source/tests. Record source/raw hashes, versions and timing. Root performs independent review.

Do not fit a charge-noise switching rate, laser defect, pure-dephasing rate or uniquely reconstructed photon density matrix: three aggregate contrasts and uncalibrated differential nuisance effects do not identify these quantities. Explicitly state what additional measurements would enable such inference (time tags/repeats, polarization/brightness/routing controls, documented windows/exposure, paired calibrations and broader pulse separations). No IBM API or new hardware is required for this bounded classical reanalysis.
