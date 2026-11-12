# Does an atomic sensor add useful laser-diagnostic information?

**In this synthetic laboratory surrogate, yes, relative to one noisy conventional reference. A second, stable conventional reference does better.** Adding the atomic channel reduces held-out frequency-change RMSE from **0.271 Hz to 0.161 Hz**. The independent conventional-reference alternative reaches **0.083 Hz**. These are results of an assumed physical model, not measured laser performance, a demonstrated quantum advantage, or a photolithography instrument.

This advances the earlier `laser_sensor_poc/` toy by specifying a physical observable, finite-duration atomic interrogation, conventional optical receivers, independent calibration, a stronger reference comparator, unknown disturbances and failure cases. It tests the user's idea of a **complementary diagnostic lens**. It does not claim to invent atomic laser spectroscopy: [Bishof et al. (2013)](https://arxiv.org/html/1303.6741v2) already demonstrated atomic analysis of a laser's frequency noise. The contribution here is the reproducible project-specific comparison and its explicit viability boundaries.

## What the experiment asks

Can synchronized measurements identify a **random-sign 0.5 Hz frequency step at a known time**, while optical power remains nominally unchanged?

Each record has **128 one-second cycles**. The scheduled step starts at **64 seconds**. The estimator compares the second-half mean with the first-half mean after the whole record is acquired. This is a **batch, known-event-time study**, not an online detector, an unknown-onset alarm or a measurement of detection latency. The source always has small stochastic frequency/intensity fluctuations. “Null” means no injected frequency change, not a perfectly constant laser.

The simulated narrow-line **698 nm** source is a laboratory surrogate compatible in concept with optical atomic spectroscopy. It is not a direct model of a broad pulsed **193 nm excimer laser**, a **CO₂ EUV drive laser**, or **13.5 nm EUV exposure light**. A physical wavelength and noise-bandwidth transfer design is required before claiming relevance to those sources. [ASML describes the distinct lithography light sources and optical paths.](https://www.asml.com/en/technology/lithography-principles/light-and-lasers)

## Frozen held-out comparison

All methods use the same underlying synthetic source paths. There are **4,000 independent null records, 4,000 fault records and a separate 4,000-record estimation set per scenario**. Each method has an independently calibrated **5% nominal false-alarm target**, with no refitting on the scenarios. The realized false-alarm rates differ and are reported explicitly.

| Measurements | Detect 0.5 Hz change | False alarm, no injected change | Frequency-change RMSE |
|---|---:|---:|---:|
| Power photodiode | 192/4,000 = 4.80% | 194/4,000 = 4.85% | 0.577 Hz |
| Conventional C: power + primary coherent receiver | 1,813/4,000 = 45.33% | 189/4,000 = 4.73% | 0.271 Hz |
| Atomic Q + power | 2,795/4,000 = 69.88% | 184/4,000 = 4.60% | 0.199 Hz |
| C + atomic Q | 3,439/4,000 = 85.98% | 198/4,000 = 4.95% | 0.161 Hz |
| C + independent conventional C | 4,000/4,000 = 100.00% | 229/4,000 = 5.73% | 0.083 Hz |

The 95% Wilson interval for C+Q detection is **84.86–87.02%**, and its false-alarm interval is **4.32–5.67%**. The second conventional reference's 4,000 successes give a **99.90–100%** interval, not a guarantee of perfect performance. All intervals describe finite Monte Carlo records conditional on the specified model and fitted calibration. They do not cover unknown physical-model error or the full uncertainty from repeating calibration.

The estimation set draws previously unseen step amplitudes uniformly from −1 to +1 Hz. Relative to C, adding Q reduces mean squared error by **64.5%**. The paired MSE reduction is **0.0473 Hz²** with an approximate 95% interval of **0.0443–0.0503 Hz²**. This quantifies additional useful information in the tested setting. It is not mutual information or a quantum advantage metric. The second conventional reference reduces MSE by **90.7%** relative to C.

`results.json` records all counts, thresholds, intervals, paired comparisons, 0–1 Hz amplitude sweeps and supplementary 1%, 5% and 10% calibration operating points. The latter are descriptive sensitivity checks using independently calibrated thresholds, not a selection of the best hold-out result.

![Held-out comparison](comparison.png)

## The physical model

The quantum channel is an ensemble of **64 independent, unentangled two-level atoms**. A classical coherent optical field drives each atom. For every cycle the atom starts near its ground state, receives a **2.5 ms π/2 pulse**, evolves for **20 ms**, receives a second **2.5 ms π/2 pulse at quadrature**, and is measured and reset. **975 ms** of the one-second cycle is unavailable for interrogation. The source frequency is assumed quasi-static within each 25 ms interrogation window. Noise between cycles has an explicitly correlated process.

The finite pulses evolve the Bloch vector under a detuning-dependent Hamiltonian. The Rabi frequency scales with the square root of relative intensity, so intensity fluctuations perturb pulse area. A calibrated, intensity-dependent probe light shift acts during the pulses. The dark interval accumulates laser-minus-atomic-transition phase. Markov relaxation and dephasing act throughout interrogation. A binomial draw implements quantum projection noise for the finite ensemble; asymmetric readout errors follow it.

| Input assumption | Nominal value | Status |
|---|---:|---|
| Optical carrier | 698 nm | Laboratory-surrogate choice with established spectroscopy precedent |
| Atoms per cycle | 64 | Chosen independent-atom ensemble, not measured |
| π/2 pulse duration | 2.5 ms each | Literature-compatible duration, assumed calibrated coupling |
| Dark interval / total interrogation | 20 ms / 25 ms | Chosen protocol |
| Cycle / record | 1 s / 128 s | Chosen low-bandwidth acquisition |
| Effective T1 / T2 | 100 s / 200 ms | Phenomenological assumptions, not fitted to a device |
| Preparation error | 1% | Assumption |
| Readout 0→1 / 1→0 error | 2% / 4% | Assumptions |
| Primary-reference random-walk increments | 0.04 Hz/√s | Assumed reference stability |
| Atomic / second conventional-reference increments | 0.01 Hz/√s each | Equal assumed long-term reference stability |
| Source frequency noise | OU, 0.08 Hz stationary SD, 8 s time constant | Chosen low-frequency noise model |
| Relative-intensity noise | OU in log intensity, SD 0.015 | Chosen noise model |
| Shared sampled-path frequency noise | OU, 0.025 Hz stationary SD | Correlated nuisance common to channels |

Finite pulses matter: in the ideal coherent limit, the frequency slope at zero detuning corresponds to an effective interrogation time `T_dark + 4*t_pulse/pi`, not just the dark time. The commonly drawn instantaneous-pulse Ramsey sine curve is only an explanatory limit. `response_curve` in the JSON contains the actual finite-pulse probabilities used by this study.

The photodiode has Poisson detected counts, efficiency, dark counts, electronics noise and slowly fluctuating gain. It observes intensity. For the chosen pure frequency perturbation it is a negative control, but it also corrects measured intensity cross-sensitivity in the other channels.

The conventional optical receiver compares the sampled field with a strong external local oscillator (LO). Its phase-difference readout includes coherent-state shot noise, electronics noise, phase wrapping, intensity cross-sensitivity and the LO's own frequency drift. The strong-LO Gaussian approximation specifies phase-difference variance `2/(eta*N_signal)` plus electronics variance. The second conventional receiver has an **independent, more stable reference** whose random-walk stability equals the atomic reference's assumed stability. This is a deliberate strong benchmark.

**Why Q helps here:** the primary coherent receiver observes `source − primary reference`. The atom observes `source − atomic transition`. An independently stable atomic reference supplies additional evidence when the primary reference fluctuates. The result comes from the additional reference and its assumed noise, not from entanglement, squeezing, an inherently superior quantum algorithm, or extra sensitivity magically created by amplitude amplification. A sufficiently stable independent optical reference supplies even better evidence in this model.

## Resource accounting and calibration

The three main architectures share a **bookkept** allowance of `2e10` sampled source photons per cycle. The power diode receives 10%. C allocates the remaining 90% to the primary receiver. C+Q and C+C allocate 45% to each frequency channel. Duration, source paths and task are controlled.

This **is not a validated physical resource match**. At 698 nm, the assumed atomic allocation corresponds to about **0.512 µW during the two pulses**, but beam area, effective dipole coupling and collection geometry are unmodeled. The model assumes that this allocation can produce the specified π/2 pulse. Changing the allotted-photon input alone does not recalculate that physical coupling. Optical local-oscillator power, cooling/trapping/readout/reset light, atom preparation, independent-reference construction and apparatus costs are not matched or counted. No total-energy, size, cost or engineering advantage follows from the bookkeeping.

Calibration uses separate seeds and stages:

1. **Sensor response:** 45 known detuning/intensity settings, 256 repetitions each, to estimate local response slopes and cross-sensitivity. The scan is ±1 Hz and ±10% intensity. Its 11,520 quantum cycles would occupy **3.2 hours** if physically performed at the assumed cycle rate.
2. **Estimator fit:** 4,000 null and 4,000 known-injection synthetic records estimate response and covariance. An ordinary classical linear minimum-variance estimator combines the observed channel changes. It receives no held-out latent source/reference trajectories.
3. **Decision threshold:** 6,000 independent null synthetic records determine an upper order statistic for the 5% target. This threshold remains frozen for every scenario.
4. **Evaluation:** independently seeded null, injected and continuous-amplitude records provide the saved metrics. Example traces use additional seeds and are not hand-selected for appearance.

The 14,000 model-fit/threshold histories would represent **20.74 days of acquisition** if collected serially as 128-second physical records. They are inexpensive **Monte Carlo calibration under an assumed generative model**, not measurements, an implemented fast self-calibration method, or a practical experimental schedule. A real study needs a measured noise model, uncertainty accounting and a smaller feasible calibration protocol.

The null covariance and input distributions are assumed to transfer to the nominal holdout. They fail under deliberate distribution shifts below. The code does not identify arbitrary unknown defects or establish blind generalization outside this family.

## What breaks the result

Each disturbance occurs in **both** the null and fault populations. Thus the false-alarm column tests whether the method mistakes an unrelated change for the target source-frequency event. The estimator is not retuned.

| Scenario | C+Q detection | C+Q false alarms | Meaning |
|---|---:|---:|---|
| Nominal | 85.98% | 4.95% | Additional atomic reference helps |
| T2 falls to 12 ms, readout degrades | 26.40% | 3.60% | Frozen calibration loses useful sensitivity |
| Atomic transition independently steps by ±0.7 Hz | 54.75% | 80.10% | Sensor drift can masquerade as source drift |
| Primary LO steps by ±0.7 Hz | 66.20% | 34.80% | Fusion helps relative to the drifting primary, but still misattributes many events |
| Shared sampled-path frequency steps by ±0.7 Hz | 62.60% | 99.03% | A common optical-path change cannot be isolated from source change by these channels |
| Power increases by 10% | 85.73% | 5.93% | Photodiode-based correction mostly tolerates this calibrated cross-sensitivity |
| Atomic and primary-reference noise correlate at 0.95 | 82.93% | 8.63% | Assumed independence/nominal covariance matters |
| Source changes gradually across the middle half | 63.75% | 5.45% | A frozen known-step estimator loses power on a new time pattern |

The raw differences `source − LO` and `source − atom` provide two relations among three unknown frequency histories. A common frequency shift of source and both references leaves the observations unchanged. Additional stability assumptions or independently characterized references are necessary for attribution. No inference algorithm can fix an exactly unidentifiable physical measurement.

An **exploratory reference-disagreement flag**, added after inspecting these failure cases, is also exported. It checks whether the atomic and primary-reference frequency changes disagree beyond a separately calibrated threshold. It does not identify which reference is wrong and does not modify or improve the saved detection results. Its scenario rates reuse the inspected holdouts, so they are descriptive; a proposed remedy would require fresh confirmation runs.

![Frozen-calibration stress tests](stress_tests.png)

## Reproduce and audit

From the workspace root, with Python, NumPy, SciPy (for the separate independent verifier) and Matplotlib available:

```powershell
python -m unittest discover -s laser_sensor_viability -p test_model.py -v
python laser_sensor_viability/run_experiment.py --out laser_sensor_viability/reproduction
```

The experiment refuses to overwrite an existing `results.json` unless `--overwrite` is supplied. The default run produces 96,000 main scenario test records, 12,000 amplitude-sweep records, separate calibration records, source hashes, full numerical summaries, eight fixed example traces and four scientific figures. This can take a few minutes; it does not submit cloud quantum jobs.

Seventeen package tests cover the instantaneous-pulse and finite-pulse analytic limits, physical probability bounds, readout confusion, complete loss of readout information, norm/relaxation behavior, common-shift ambiguity, projection/shot-noise scaling, colored-noise statistics, photodiode frequency blindness, the threshold order statistic and unbiasedness of the fitted linear estimator under its own calibration.

The root independent verifier in `research-validation/verify_sensor_physics.py` compares the implementation against full density-matrix Lindblad exponentials. With 16 Strang substeps per pulse, its wide detuning/intensity grid has maximum excitation-probability error about **4.4e−6 nominal** and **4.4e−5 under the degraded-coherence condition**. This checks numerical dynamics, not the validity of the assumed apparatus.

The first run used four substeps. Independent numerical review motivated a refinement to sixteen, with the same seeds and scientific parameters. `numerical_refinement.json` preserves the first-run metrics/hashes. Tiny probability changes can alter NumPy's sequence of binomial draws, so finite Monte Carlo counts need not remain identical. No performance-based model tuning was used. The later supplemental operating-point and disagreement diagnostics are identified as descriptive additions.

## What the team can credibly show

The immediate demonstration is an **optical-diagnostics research simulator**: one source, synchronized power and frequency observations, an atomic interrogation response, an honest conventional benchmark, and visible failure cases. It supports a conditional answer to “when is another diagnostic lens useful?”

The next physical test would use a compatible narrow-line laser, programmed frequency and intensity modulation, a characterized atomic platform, synchronized conventional references and independent reference-disturbance controls. Hold back whole acquisition sessions, test unknown event times, measure noise spectra and bandwidth, and recalibrate only on a declared training set. The design must distinguish source noise from sensor/reference/path noise before it can diagnose a laser reliably.

For chip-making relevance, a source/metrology partner would need to identify an actual monitoring point and a consequential measurand, then establish wavelength compatibility, allowable tap, bandwidth and the transfer from that measurand to exposure quality. The current hertz-scale 698 nm calculation does not establish that transfer.

Rewind & Amplify remains a separate **quantum-computing** result: it queries a reversible model to emphasize selected simulated histories. This package uses classical inference on a modeled quantum sensor's readouts. It neither runs that inference on a QPU nor integrates this optical model into a reversible oracle. The proposed eventual connection is to learn a validated sensor model, define a physically relevant rare-history query, retain the required environment coherently and compare full quantum resources with strong classical inference/sampling methods.

Additional physical context: [Day et al., *Limits on atomic qubit control from laser noise* (2022)](https://www.nature.com/articles/s41534-022-00586-4) supports studying laser noise in atomic control. It does not validate this simulator's chosen parameters or its lithography use case.
