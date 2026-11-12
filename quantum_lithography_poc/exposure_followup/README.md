# Quantum-light exposure after loss, blur and finite counts

This is a new numerical follow-up to the original ideal fringe calculation. It tests a **conditional research opportunity: lower background in a fine-period activation pattern**, against the costs of making that pattern. It is a classical calculation of specified quantum states and an explicitly uncalibrated material response. No light source, resist, fabricated structure, wafer yield, manufacturing speedup or quantum-computer advantage was demonstrated. The original work and finals materials were preserved.

The central finding is a tradeoff. Under our nominal assumptions, the two-photon NOON state has higher activation contrast than two classical references. The brighter classical reference has better second-harmonic counting precision at the same average sample photon budget and time. Allowing each method its best exposure duration, the quantum state gives cleaner thresholded toy patterns but needs substantially more photons. Modest source inefficiency plus time-dependent background can reverse that result. These are model-dependent comparisons, not an optimal classical bound or a fabrication feasibility result.

## What was actually run

- Nine specified cases, five illumination methods, 140 one-parameter sensitivity rows.
- 6,000 independent Poisson realizations per case/method at equal sample photon dose, and another 6,000 at each method's analytically chosen best exposure duration: **540,000 synthetic exposure realizations**.
- Ten tests, including an independent density-matrix/Fock calculation with explicit loss Kraus operators, classical phase-exposure averaging, numerical jitter/blur integration, photon conservation and Poisson sampling checks.
- Results in `results.json`; sweep data in `sensitivity.csv`; console summary in `run_summary.json`; test log in `test_results.txt`. The three PNG figures were visually checked.

The spatial period is an illustrative 800 nm, obtained from an assumed 800 nm wavelength and two beams at ±30°. The second harmonic has a 400 nm period. This is **not a measured linewidth**, and the model is not an EUV or DUV exposure process. The 32 sampling/response cells are a fixed toy geometry, not 32 independently focused subwavelength beams.

## Fair normalization and stronger classical references

The original code evaluates one normalized output `c=(a+exp(iφ)b)/√2`. Treating every plotted phase point as another such output would duplicate the photon budget. Here we use two orthogonal spatial mode columns over `M=32` cells:

```text
u_a[j] = 1/√M
u_b[j] = exp(iφ_j)/√M,   φ_j = 2πj/M
```

Additional vacuum inputs can complete a passive unitary. They do not contribute to normally ordered moments. With independent transmissions `a=η_a`, `b=η_b`, the spatial moments per delivered quantum pair or ordinary coherent slot are:

```text
NOON:       G1 = (a+b)/M
            G2 = [a²+b²+2ab cos(2φ)]/M²
Mixture:    G1 = (a+b)/M
            G2 = (a²+b²)/M²
Coherent:   G1 = [a+b+2√(ab)cosφ]/M
            G2 = G1²
Phase cycle:G1 = (a+b)/M
            G2 = [(a+b)²+2ab+2ab cos(2φ)]/M²
```

The incoherent mixture is half `|2,0><2,0|` plus half `|0,2><0,2|`. The coherent inputs have amplitude one in each arm. Both inputs therefore have two mean source photons. `Σ_j G1_j = a+b` checks conservation of the mean photons reaching the sample. `G2` is the local factorial moment `⟨n(n−1)⟩`, not an absorbed-photon count.

The phase-cycled reference uses half its exposures at relative phase zero and half at π. It averages their **positive deposited signals**, canceling the fundamental harmonic without subtracting exposure or doubling the allowed photon budget. It already has the same doubled spatial period as NOON, though more uniform two-photon background.

The stronger coherent reference is active in 10% of slots with ten times the mean photons per active slot. Its average source photons and elapsed slots match, while `G2` increases tenfold and `G1` stays fixed. Active-slot mean source photons rise from 2 to 20. This is a change in peak brightness, explicitly charged as a separate resource; the optical temporal mode is otherwise assumed identical. It demonstrates why a fixed average photon budget alone is not a complete resource bound for nonlinear exposure. We have not optimized over all classical fields, spatial modes, pulse widths, wavelengths, materials or phase schedules.

At equal symmetric loss with only two-photon response, NOON has ideal visibility 1, and phase-cycled coherent light has visibility 1/3. Both second-harmonic amplitudes are equal, but the classical DC component is three times larger. Loss multiplies the pair moments by η². Once linear response is present, its η scaling causes contrast to deteriorate at low transmission. Asymmetric loss additionally reduces NOON coherence relative to its DC background.

## From moments to explicitly hypothetical activation

For a successful slot, the expected activation-event field is

```text
r_j = α G1_j + β G2_j.
```

The nominal coefficients are **α = 2×10⁻⁵ events per incident photon** and **β = 10⁻³ events per local factorial moment per slot**. They are arbitrary effective couplings. The missing material cross-section, optical temporal overlap, spatial cell volume and chemistry are absorbed into these numbers; they are not measured resist parameters. The factor of two in `n(n−1)` is part of our definition of β. A pair activation consumes two photons for the photon-drain check.

Independent, rapidly varying Gaussian relative-phase jitter with σ=0.15 rad damps harmonic `h` by `exp(−h²σ²/2)`. A box-average aperture of one cell damps it by `sinc(h/M)`. A phenomenological Gaussian displacement of activation events with σ=40 nm damps it by `exp[−(h·2πσ/Λ)²/2]` while preserving the total expected activation. That last step represents blur after deposition, not an optical propagation calculation or validated reaction–diffusion chemistry. We model fast averaged jitter, **not slow drift shared by an entire exposure**. Coefficients and cell count cannot be independently changed to claim a continuum material limit.

After `N` attempted slots, activations are approximated as independent Poisson counts with means `N r_j`. This is a weak-event approximation, not an exact joint quantum photon-count trajectory. The largest local active-slot event mean across the nine cases is 0.001563; the largest modeled mean absorbed-photon fraction is 0.001875. Those checks support staying within our declared weak-response regime but do not validate the chosen material. Saturation, bleaching, damage, multiple absorption channels and correlations between chemical products are omitted.

The default scheduling scale is **1 MHz**. It converts ten million attempted slots to ten seconds; it is not a demonstrated source rate. No optical pulse duration or actual available pair flux has been measured. Source success `p` means that failed quantum preparations emit vacuum and still consume their clock slots. Pump energy, herald photons and equipment costs are unknown and excluded. The incoherent control has the same success assumption as NOON. Ordinary and phase-cycled coherent sources are assumed available every clock; this is a declared source model, not a characterization of laboratory devices.

## Results and what they mean

In the finite nominal case, all three references below receive **16 million mean sample-incident photons**, using ten million attempted clocks at `p=1`. Noise and geometry are shared.

| Method | Activation visibility | Expected events | Second-harmonic signal / Poisson SD |
|---|---:|---:|---:|
| NOON | 0.4332 | 720 | 8.22 |
| Phase-cycled coherent | 0.2052 | 1,520 | 5.66 |
| Phase-cycled coherent, 10% duty | 0.2532 | 12,320 | 19.87 |

The Fourier metric is a **known-phase, second-harmonic amplitude** estimate across the cells, not a task of estimating an unknown source phase. Its standard deviation is computed from all cell counts. The figure's error bars show the central 95% range of realized estimates across 6,000 trials, not uncertainty in a material parameter or a confidence interval for the Monte Carlo mean. The NOON state suppresses background compared with ordinary phase cycling, while brighter classical pulses provide stronger statistical precision in this chosen counting task. A high SNR is not proof of reliable pattern formation.

For a deliberately simple pattern task, a cell activates if its count reaches **20 events**. Bright guard cells satisfy `cos(2φ)≥0.7`; dark guard cells satisfy `cos(2φ)≤−0.7`. The ambiguous boundary cells are excluded. There are 20 included cells. This is an assumed binary activation rule with fixed threshold, **not a development model**. We report both mean cell accuracy and the probability that all 20 included cells are correct; the latter prevents a good average from hiding a poor entire pattern.

Holding one exposure duration fixed overexposes the stronger classical source. Therefore we also optimize duration separately for every method using its known model, keep the same absolute 20-event threshold, and charge the resulting photons:

| Method, nominal setup | Best guard-cell accuracy | Mean sample photons at that duration | All 20 guard cells correct |
|---|---:|---:|---:|
| NOON | 95.16% | 14.88 million | 36.76% |
| Phase-cycled coherent | 78.28% | 6.81 million | 0.73% |
| Phase-cycled coherent, 10% duty | 83.29% | 0.845 million | 2.52% |

The independent optimized-duration Monte Carlo gives 95.10% ±0.061 percentage points (one Monte Carlo standard error) for NOON mean cell accuracy; its all-cell result is 36.25%, with a Wilson interval stored in JSON. The other methods and all cases also have finite-count checks. These intervals quantify simulation sampling only. Material and model uncertainty are much larger and have not been quantified.

The threshold and chosen geometry create this tradeoff; the numbers are not evidence of a physical quantum advantage. The optimizer has exact knowledge of the assumed response. It does not test calibration generalization, unknown material parameters or a practical controller. `equal_mean_activation_20` separately equalizes mean deposited events and explicitly reports the different photon budgets needed. It must not be presented as equal incident dose.

### Failure cases

- At 20% transmission per arm, the optimized NOON guard-cell accuracy falls to 76.02%; the 10% duty coherent reference reaches 81.47% with fewer sample photons.
- At 120 nm Gaussian blur, the NOON visibility falls to 0.0893 and best mean guard-cell accuracy to 63.28%. The doubled spatial frequency does not survive as a useful thresholded pattern here.
- Multiplying the linear response coefficient by ten reduces the NOON best accuracy to 62.90%; the brighter coherent reference reaches 78.28%.
- At 1% quantum preparation success with zero time-dependent background, equal sample photon dose takes **1,000 s rather than 10 s**. Equal clock time instead reduces NOON harmonic SNR from 8.22 to 0.822. Neither comparison is labeled as satisfying both budgets.
- Add only `10⁻⁷` background activation events per cell per attempted clock at 1% success: during a sample-dose-matched quantum exposure, this accumulates for 100 times longer. NOON visibility becomes 0.0796. Its best mean guard-cell accuracy is 61.88%, below the ordinary phase-cycled reference's 77.80% and the bright reference's 83.23%.

## Primary-source basis and new work

The operator-response premise is established physics, not our invention. [Boto et al., PRL 85, 2733 (2000)](https://arxiv.org/abs/quant-ph/9912052) proposed entangled-state interference for an N-photon absorber. [D'Angelo, Chekhova and Shih, PRL 87, 013602 (2001)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.87.013602) reported a two-photon diffraction/interference demonstration; that is not evidence that this code prints a semiconductor resist. [Tsang, PRA 75, 043813 (2007)](https://www.ece.nus.edu.sg/stfpage/tmk/papers/tsang_quantum_lithography_PRA.pdf), especially its normally ordered absorption formalism and resolution/rate analysis, explains why spatially finer structure need not improve multiphoton absorption efficiency.

Our contribution here is a reproducible sensitivity comparison: explicit finite spatial photon accounting, a phase-cycled and a duty-cycled classical reference, losses and blur, separate photon/time/activation budgets, and finite-count task evaluation. The Gaussian blur, linear leakage, threshold, source success and scheduling values are **our declared assumptions**, not values taken from those papers. AI assistance: Codex with OpenAI models implemented and checked the study; no manual team experiment is implied.

## Reproduce and next decision

Use Python 3.12 with the versions in `requirements.txt`, from this directory:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
python -m unittest -v test_model.py
python run_study.py
```

The runner writes only this new directory and records package versions, seeds and SHA256 hashes of its source and original inputs. The run used NumPy 2.3.1, SciPy 1.18.1 and Matplotlib 3.10.3. It does not submit hardware jobs or access credentials. A source-success clock is not an actual sensor acquisition record.

Before treating direct exposure as viable, obtain measured pair brightness and success, spectral/temporal mode overlap, asymmetric transmission, phase stability, wavelength-specific linear and two-photon response, blur/development behavior, damage and allowed peak brightness. Then rerun against an experimentally feasible classical illumination family with calibration errors and a defined material feature. The present useful decision is that **contrast can be worth studying, but photons, peak brightness, time and full-pattern errors cannot be hidden behind a finer fringe**. Phase or patterned-structure inspection is a separate study; these exposure results do not establish an inspection advantage.
