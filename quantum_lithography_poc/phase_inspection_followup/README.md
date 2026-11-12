# Phase inspection: loss, source cost and the missing phase branch

This is a separate numerical inspection study, following the exposure study in `../exposure_followup/`. It estimates one unknown **relative optical phase**, which could be a calibrated observable of a test object. It does not simulate an image, identify a material defect, expose a resist or measure a chip. There is no quantum-computer speedup claim.

The useful result is conditional. With efficient preparation and detection, a two-photon quantum probe improves local phase precision over the specified coherent reference. Its fine fringe alone cannot resolve an unknown phase over a full 2π. A hybrid that spends part of its budget on ordinary coherent measurements resolves that ambiguity and retains a precision benefit in the efficient case. At larger loss or poor preparation success, the conventional reference wins. All source attempts and all reference-probe photons are charged.

## Protocol fixed before the full run

Both spatial modes illuminate the object, for example two regions of one test sample. Their relative-phase generator is `(n_a−n_b)/2`; **neither arm bypasses the object as an external optical reference**. Both arms' incident photons therefore count toward the sample dose. Inputs are either the state `(|2,0>+|0,2>)/√2`, or a product of coherent states with amplitudes one and one. The latter notation means **one mean photon in each arm**, not a one-photon Fock state. Each successful NOON trial or coherent clock delivers two mean photons **to the object input, before object transmission**. A different experiment with a bypass reference arm would require separate sample-arm and apparatus photon budgets.

Object transmission `T` and detection efficiency `D` are separate parameters; `η=T·D`. Neither loss reduces the incident photons charged to the object. Failed quantum preparations emit vacuum, consume their clock slot and are included in the outcome record. Success probability is `p`. A coherent source is assumed available every clock. The simulation uses mean photon budgets; the coherent state's actual photon number fluctuates, and the number of successfully prepared quantum trials fluctuates.

Both methods receive the same independently calibrated phase-bias settings `δ={0,π/4,π/2,3π/4}`, each for one quarter of their allocated trials. These settings are a reference, not knowledge of the unknown object phase. Their calibration is assumed ideal and equally available. Both output ports of the recombiner are measured. Photon-number-resolving detection is assumed, with ideal discrimination conditional on the stated efficiency. There is no additional, uncounted bright optical local oscillator; both illumination-arm photon budgets are charged. Control/calibration energy, pump photons, herald photons, equipment and switching time are not modeled.

For each bias let `ψ=φ+δ`. Exact probabilities for one attempted quantum clock are:

```text
P(0,0) = 1 − p + p(1−η)²
P(1,0) = P(0,1) = pη(1−η)
P(2,0) = P(0,2) = pη²[1+cos(2ψ)]/4
P(1,1) = pη²[1−cos(2ψ)]/2.
```

These sum to one and include every no-click and one-photon-loss outcome. The ordinary coherent output counts are independent Poisson variables with means `η[1+cosψ]` and `η[1−cosψ]` per clock. Aggregated records are drawn from the exact multinomial/Poisson likelihoods; this phase study does **not** use the exposure study's rare-activation approximation.

Two estimation tasks are kept separate:

1. **Calibrated local phase:** every method knows the same prior interval `[0.15,0.55]` rad. The benchmark truth is 0.35 rad. Maximum likelihood searches that interval. This models tracking near an already calibrated operating point; it is not blind phase discovery.
2. **Unknown global phase:** 2,000 independent true phases are drawn uniformly over `[-π,π)`. Coherent estimation searches that full domain. Pure NOON estimation returns one representative branch in `[0,π)`, because its likelihood is exactly unchanged by `φ→φ+π`. We never supply the true branch to its estimator. Both full-2π error and modulo-π error are reported, with different meanings.

The **10/90 hybrid** uses a separately generated coherent coarse record and a NOON record in a joint full-2π likelihood. Under equal incident dose, 10% of its photons go to coherent observations and 90% to quantum observations. Under equal attempted clocks, 10% of clocks are coherent and 90% attempt quantum preparation; inefficient preparation therefore changes its photon mix. The pilot is not free, and the allocation is fixed rather than tuned on the test records. This is an application of established coarse/fine phase-estimation logic, not an invention claim.

## Checks before the main experiment

The regular-phase, local Fisher-information reference values per attempted clock in this symmetric model are

```text
Coherent: F = 2η
NOON:     F = 4pη².
```

Numerical likelihood derivatives reproduce those formulas at the tested regular phase 0.35 rad. At exact dark-fringe nodes, zero-probability outcomes make the pointwise numeric formula nonregular; the displayed expressions describe the continuous phase limit. The implementation omits zero-probability terms and does not claim their continuous-limit value at an exact node. At unit transmission/detection/preparation, the regular values are 2 and 4 respectively. The ideal local standard deviations at 10,000 clocks are therefore approximately 0.007071 rad and 0.005000 rad for an unbiased efficient estimator. These are **local**, asymptotic reference bounds for the specified measurement, not a global error guarantee or an optimization over all quantum/classical experiments.

Independent tests construct a Fock-space beamsplitter and check output probabilities. A separate binomial thinning calculation verifies loss and vacuum outcomes. Further checks cover photon conservation, prior/branch structure, charged hybrid photons, finite-sample estimator behavior and grid convergence. **Nine tests pass.**

## Experiments and findings

The run contains seven source/loss cases, two budget rules, three probe methods and two phase regimes, with **2,000 independent records per combination: 168,000 estimation trials**. Outcomes are independently drawn conditional on their true phases. The same 2,000 global phase values are reused across combinations, so these comparisons share a phase cohort; all 168,000 trials are not globally independent draws of the object. Random seeds and package versions are stored. No hardware was used.

Budget A fixes **20,000 mean photons incident before the object**. Budget B fixes **10,000 attempted clocks**. At the declared 1 MHz clock, that is 0.01 seconds; this is a scheduling convention, not a measured pair-source rate. In the inefficient-preparation cases, Budget A requires longer time, while Budget B delivers fewer quantum photons. The study never labels those cases as matching both time and incident dose.

Local RMSE in radians under equal incident photon dose:

| Case | `T` | `D` | `p` | NOON | Coherent | 10/90 hybrid |
|---|---:|---:|---:|---:|---:|---:|
| Ideal | 1 | 1 | 1 | 0.005041 | 0.007238 | 0.005175 |
| High efficiency | 0.9 | 0.9 | 1 | 0.006173 | 0.007853 | 0.006446 |
| Moderate loss | 0.6 | 0.8 | 1 | 0.010509 | 0.010108 | 0.010295 |
| Severe loss | 0.2 | 0.6 | 1 | 0.041726 | 0.020835 | 0.036243 |
| Detector loss | 0.9 | 0.3 | 1 | 0.018658 | 0.013611 | 0.017563 |

These results recover the expected efficiency tradeoff. At matched photons with otherwise identical parameters, the specified NOON measurement has more local information than this coherent comparator only when `η>1/2`. At matched attempted clocks, the requirement tightens to `pη>1/2`. The hybrid cannot evade those preparation/loss costs merely by resolving ambiguity.

For `T=D=0.9` and **1% preparation success**, pure NOON needs 1.0 s to deliver 20,000 expected incident photons, versus 0.01 s for coherent light. Its dose-matched local RMSE is 0.006169 rad. With only 0.01 s allowed, it delivers 200 expected photons and its RMSE becomes **0.061963 rad**, versus **0.007906 rad** for coherent light. The hybrid's equal-time RMSE is 0.023449 rad, using 2,180 expected incident photons. A fixed prior clips 0.2% of the low-success pure-NOON local estimates at its boundaries; this is reported rather than interpreted as an unbiased Cramér–Rao comparison.

For the **global phase task** at high efficiency and equal 20,000-photon dose:

| Probe | Full-2π RMSE, rad | 95% Monte Carlo interval | Modulo-π RMSE, rad | Wrong π-branch rate |
|---|---:|---|---:|---:|
| NOON | 2.22674 | 2.17778–2.27464 | 0.006265 | 50.4% |
| Coherent | 0.007908 | 0.007666–0.008143 | 0.007908 | 0/2,000 |
| 10/90 hybrid | 0.006371 | 0.006170–0.006565 | 0.006371 | 0/2,000 |

The pure-NOON branch error is structural: its measurement cannot tell phases separated by π apart. Reporting only the smaller modulo-π error would hide the question it fails to answer. The fully charged coherent pilot resolves the branch in this finite test. Zero observed branch errors in 2,000 trials has a Wilson 95% upper bound of approximately **0.192%**, not zero failure probability. These efficient-case results establish a conditional simulation benefit for the declared hybrid over this coherent reference, not a physical instrument or a universal classical-limit violation.

RMSE intervals derive from the sampling uncertainty of mean squared error across independent repeats within each combination, then transform to square roots. They do not include uncertainty about the assumed phase reference, losses or source model. Maximum likelihood uses 512 local grid points or 2,048 global points with parabolic refinement. Doubling the grid for the first 50 records in every combination changes estimates by at most **9.1×10⁻⁵ rad** in this run; the JSON records each check. Pure NOON grid convergence is compared modulo π, its likelihood period, while the actual global task error remains measured over the full 2π.

## What remains untested

The model assumes a pure prepared NOON state, symmetric known losses, a stable correctly calibrated phase reference, ideal number discrimination, and no dark counts, mode mismatch, drift, background or saturation. We did not optimize the 10/90 allocation, compare all classical receivers, or infer unknown losses and phase jointly. A conventional instrument may use higher power or longer integration when sample damage and time permit; the result here fixes those budgets by definition.

Relating a single measured phase to a patterned structure requires an optical forward model, wavelength, refractive index, illumination/detection geometry and calibration of competing mechanisms. No phase-to-feature-size conversion, wafer classification accuracy, lithography yield or printed resolution follows from this study. A realistic next inspection experiment would acquire synchronized known-phase test-object records with an independent conventional reference, then fit both phase and nuisance parameters on held-out conditions. Its reference photons and calibration time must also be counted.

## Primary sources and provenance

- [Slussarenko et al., Nature Photonics 11, 700–703 (2017)](https://arxiv.org/abs/1707.08977) demonstrated photonic phase estimation with losses and imperfections included in the experimental accounting. It motivates counting all photons here; it does not validate our simulated apparatus.
- [Demkowicz-Dobrzański, PRA 83, 061802(R) (2011)](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.83.061802) treats the distinction between local prior knowledge and global phase estimation. Our explicit π-periodicity follows directly from the displayed likelihood.
- [Lee et al., PRA 80, 063803 (2009)](https://arxiv.org/abs/0908.3008) investigates how photon loss changes favorable probe states. We compare a specified two-photon state, coherent reference and hybrid; we do not reproduce its broad state optimization.

AI assistance: Codex with OpenAI models implemented the numerical study and checks. The equations were independently audited within the research task; no manual laboratory validation is implied. The original project files, exposure results, deck and application were not rewritten.

From this directory, with Python 3.12 and `requirements.txt`:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
python -m unittest -v test_phase_model.py
python run_phase_study.py
```

`results.json` contains complete metrics, resource accounting, seeds, example estimates, grid checks and source hashes. `run_summary.json` is a compact numeric summary. `local_phase_tradeoffs.png` and `global_phase_ambiguity.png` were visually inspected. These files are research artifacts, not replacements for the finals' already verified presentation evidence.
