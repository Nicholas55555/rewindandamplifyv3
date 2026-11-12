# Quantum-sensor vision: diagnosing lithography light sources

This is a **proposed research direction**, not a result or a description of existing fab equipment built by the team. The goal is to explore whether photons from a lithography-related light source can interact with a quantum system, and whether the system's readout can help detect or characterize source instability. The current Rewind & Amplify code has **not** diagnosed a physical laser, measured a fab, or shown a sensing advantage.

This continues the project's earlier idea of a **complementary diagnostic lens**, alongside existing instruments. The supplied `relevantconversationswithai/QRSM_Complete_Conversation_Photonics_Diagnostics.pdf` discusses that question on pages 8, 11–12 and 17–18, including how to hold observations fixed when comparing inference models. Its cover describes it as a reconstructed and condensed conversation, not a verbatim export.

## First choose which source is being diagnosed

“The lithography laser” can refer to different physical signals:

1. **DUV exposure source:** deep-ultraviolet lithography uses, for example, 193 nm argon-fluoride excimer laser light. A proposed monitor could investigate some measured property of that source, such as pulse-energy fluctuation or wavelength drift, provided the sensor and sampling path actually support that wavelength and timing.
2. **EUV drive laser:** in the laser-produced-plasma architecture described by ASML, a CO₂ laser delivers pulses to tin droplets. A sample of the drive laser would characterize the *drive*, not directly measure the EUV light produced downstream.
3. **EUV exposure light:** the tin plasma emits 13.5 nm EUV light, which travels through reflective optics in a vacuum. EUV pulse energy, spatial distribution, spectrum and stability need their own suitable sampling and detection system. A sensor that works on a separate visible or infrared beam cannot simply be assumed to sense this EUV radiation.

Sources: [ASML, light and lasers in lithography](https://www.asml.com/en/technology/lithography-principles/light-and-lasers); [ASML, EUV source and optical path](https://www.asml.com/en/products/euv-lithography-systems). Source architectures and monitoring points vary by tool; consult actual equipment specifications and experts before making device-specific claims.

## The sensing concept

An engineering hypothesis for a **laboratory surrogate**, not yet a fab design:

```
laser under test → calibrated small sampled beam → compatible quantum sensor
                                                → sensor readout → time-stamped record
                 ↘ synchronized conventional reference → comparison
```

The quantum sensor could be an atom, ion, or solid-state system with a suitable optical transition. The sampled field interacts with the system; repeated state readouts or fluorescence detections are used to estimate a defined property of the source. Atomic transitions are already used in optical frequency metrology; for example, NIST describes [compact atomic optical frequency standards](https://www.nist.gov/publications/high-performance-compact-optical-standard) and [optical frequency references](https://www.nist.gov/programs-projects/compact-ultrastable-optical-references). This establishes the **physical plausibility of atomic-reference metrology**, not the performance of our proposed sensor on a lithography tool.

The sampling optics must be designed for the selected wavelength, peak power, repetition rate and noise bandwidth. A tap removes some light and can itself introduce drift, loss, conversion noise or back-reflection. “Non-invasive” should mean **a characterized small tap whose effects on the main process are acceptable**, not that the sampled photons are measured without absorption or that the main beam is unaffected. A quantum nondemolition measurement would require its own device and evidence.

There is a direct physical precedent for the complementary-lens idea. [Bishof et al., PRL 111, 093604 (2013)](https://arxiv.org/abs/1303.6741) used lattice-trapped strontium atoms to characterize the frequency-noise spectrum of an ultrastable laser. Atomic spectroscopy supplies a different reference from an optical beat between lasers. This prior work supports the choice of a Ramsey sensor model, but means that atomic laser-noise spectroscopy itself is not our invention.

The first lab experiment should use an accessible laser, known modulation and a sensor platform whose transition and detector are actually compatible. A visible/near-infrared experiment can establish methods, but it is **not** automatically a measurement of a 193 nm excimer laser, a CO₂ drive laser, or 13.5 nm EUV. Any wavelength conversion needs a physical implementation, calibration and its own noise and efficiency accounting.

## What the existing project can and cannot model

`qrsm_photon_poc/qrsm_photon.py` contains a driven two-level emitter coupled to a hidden two-level system and a truncated cavity, with loss, dephasing, efficiency and dark counts. Its output is a simulated **fluorescence/cavity-detection click record**. Its current drive is represented by a classical control parameter in a quantum-system Hamiltonian: the output click is not automatically an individual incident laser photon or a direct measurement of laser energy.

The newer standalone two-bin circuit coherently simulates and amplifies a rare record of a simplified, approximated version of that open-system model. It reverses the **model circuit and retained environment**, not a physical sensor or already detected photon. The cavity model, two-bin circuit and IBM hardware experiment are not currently a calibrated laser sensor or an integrated fab system. The same `click/no-click` history machinery may nevertheless provide a starting point for **model-based sensing experiments**, if laser perturbations and detector confounders are introduced and validated explicitly.

## A concrete, testable first simulation

**Physical surrogate completed:** `laser_sensor_viability/` now models finite optical Ramsey pulses, 64 independent atoms, relaxation/dephasing, readout errors, conventional power/coherent receivers, source/reference/path noise, and independent calibration. At a nominal 5% false-alarm target, adding the atomic channel improves detection of a known-time 0.5 Hz step from 45.33% to 85.98% in held-out simulations (realized false alarms 4.73% and 4.95%). A stronger conventional addition reaches 100% observed detection and 5.73% false alarms. The atomic combination reduces estimation RMSE from 0.271 to 0.161 Hz, while the stronger conventional alternative reaches 0.083 Hz. These are conditional simulation results for a 698 nm laboratory surrogate, not measured sensor performance. Photon allocation is bookkeeping with unvalidated coupling and unmatched apparatus resources. Atomic drift yields 80.10% false alarms, exposing the need for independent references. See the package README for full scope, intervals, calibration costs and eight stress cases.

**Earlier abstract probe:** `laser_sensor_poc/` separately tests a simplified, ideal reset-qubit model with a classical persistent or IID pulse-area regime. A known-parameter classical HMM distinguishes the chosen matched-mean synthetic records with 92.775% balanced accuracy over 4,000 simulated records. It does not model an optical field or a physical conventional comparator. Its assumptions remain documented in `laser_sensor_poc/README.md`; use the stronger physical surrogate for the revised finals demonstration.

A follow-on fusion toy adds an invented classical observation to the same hidden regime and compares each readout with their joint likelihood. In the chosen model, the joint method detects 97.33% of persistent records with a 1.67% false-alarm rate at the fixed threshold. It uses an extra observation and assumes independent sensor errors conditioned on the regime; the classical channel's contrast was chosen weaker, no two-classical-channel benchmark was run, and photon budgets are undefined. This illustrates a possible source of complementary information, not real-laser performance or an advantage of a quantum sensor. See `laser_sensor_poc/fusion_results.json` and its README.

**Continuing research question:** Given a fixed observation time and sample budget, can a specified sensor and inference method detect a small, deliberately programmed change in the laser drive from the sensor readout, and distinguish it from detector or emitter drift? The frequency-sensing surrogate tests part of this question; the emitter–cavity amplitude experiment below remains a separate proposed extension.

1. **Define the signal.** For the first experiment choose relative drive-amplitude drift over time. Specify whether the latent quantity represents optical field amplitude, intensity, or pulse energy; they are not interchangeable. Treat the existing coupling/drive parameter as an effective field-amplitude proxy only within a documented toy mapping.
2. **Generate independent synthetic records.** Extend the time-bin simulator to switch between two known effective drives, e.g. baseline and a modest programmed offset, using a known schedule or a telegraph process. Precompute the two quantum instruments rather than recomputing a matrix exponential for every record. Keep the emitter's hidden state across bins. Record the latent schedule for simulation scoring; do not give it to the estimators.
3. **Calibrate and split.** Use separate calibration records for baseline drive, detector efficiency, dark counts and response. Fit and select models on training histories; use independently seeded held-out histories, different modulation schedules, and multiple parameter settings for evaluation. Preserve raw inputs, seeds, code, and output.
4. **Test confounders.** Evaluate frequency detuning, emitter spectral drift, fluctuating collection efficiency, loss, dark counts, detector dead time and afterpulsing separately and in combinations. Do not label an inferred change “laser drift” if multiple causes produce indistinguishable observations. NIST details these [photon-detector nonidealities](https://www.nist.gov/programs-projects/sources-detectors-and-metrology).
5. **Measure outcomes.** Report drive estimation bias and uncertainty, change-detection rate at a preset false-alarm rate, delay, held-out predictive likelihood and calibration. Report results versus collected photons, observation time and bandwidth. Include null and negative controls, repeat seeds and uncertainty intervals. Failure to separate causes is a useful result, not a reason to silently tune the model on the holdout.

For **frequency** sensing, an optical transition responds to detuning between the laser and the transition; a single response channel can confuse source drift with movement of the sensor's own transition. A calibrated stable reference and/or controlled measurements at two operating points may help, but their identifiability and extra measurement cost must be demonstrated. Experimental work on a driven hBN quantum emitter shows how laser detuning and emitter spectral diffusion both affect photon correlations, and why the model matters: [Fournier et al., Phys. Rev. B 107, 195304 (2023)](https://doi.org/10.1103/PhysRevB.107.195304). Their public figure data in `photon_reference/` are **external context**, not a fit or validation of our sensor model.

## Compare against strong classical instruments and algorithms

The task must be compared on the **same measurand and resources**, not merely against a memoryless guess:

- Calibrated conventional photodiode or pulse-energy monitor, appropriate to the source wavelength and required bandwidth; include shot noise, electronics, saturation, timing, calibration and available tap power. NIST documents [pulsed laser-energy metrology](https://www.nist.gov/publications/cw-calibrated-laser-pulse-energy-meter-range-1-pj-100mj).
- Classical estimation of the *same sensor record*: rate model, change-point/CUSUM filter, and an HMM or telegraph model with comparable training data and unknown nuisance parameters.
- Where frequency or phase is the measurand, an appropriate calibrated classical reference and interferometric/heterodyne readout. This is a different benchmark from pulse-energy measurement.

Match acquisition duration, photons delivered to the sensor or allowed tap fraction, detection efficiency, bandwidth, dynamic range, latency, and false-alarm rate. Account for any reference beam, external clock, calibration runs, wavelength conversion, reset, dead time, electronics, and sensor preparation. Classical and quantum techniques can each have advantages depending on the resource regime; neither a qubit interaction nor a low click rate alone proves quantum-enhanced sensitivity.

## Where amplification could fit

Amplitude amplification is a **separate computational hypothesis**: after learning a compatible reversible model, it may produce simulated histories matching a rare condition. It does not amplify a detector's physical sensitivity or cause an actual unstable laser event to occur. For time-varying drive, one must specify how the stochastic source schedule is prepared coherently, how click histories and all required environment information are retained, how the event is marked, and what state-preparation, oracle, gate, shot and error-correction costs result. Compare those total costs against exact inference, direct sampling, importance sampling, and appropriate classical hidden-state models.

The present small two-bin result is a useful feasibility checkpoint, not an industrial resource estimate: its 11-qubit, 6,663-generic-CX count pertains to one ideal, coarsely approximated cavity-two query with no routing or hardware noise. A sensing benefit or an end-to-end computational advantage remains unproven.

## Suggested stage gates

1. **Now:** choose one observable and one physically compatible surrogate platform; extend the simulator with a controlled source perturbation and detector-confounder tests; benchmark classical inference.
2. **Lab collaboration:** obtain time-tagged sensor output plus synchronized conventional-reference measurements and detector characterization. Refit and evaluate on genuinely independent runs.
3. **Circuit viability:** only after the inference task is defined, synthesize a coherent model and oracle for that task; report accuracy versus full quantum resources and strong classical alternatives.
4. **Industrial relevance:** with a photolithography-source or metrology partner, identify an allowed monitoring point, target metrics, realistic environmental constraints and acceptable process impact. Adapt the sensor to the actual DUV, EUV-drive, or EUV signal rather than assuming a surrogate transfers unchanged.

If the sensor cannot distinguish source changes from its own drift or a matched conventional monitor meets the objective more simply, that result rules out the proposed use case in the tested regime. Other source parameters, sensor platforms, and operating regimes would remain separate hypotheses.

## A falsifiable path from the surrogate to a useful instrument

An initial laboratory study should use an existing compatible atomic-spectroscopy platform with a synchronized conventional optical reference. Choose a frequency-noise band that both instruments actually sample. Measure the atomic contrast, reference stability, state-readout errors, cycle timing, optical tap, and conventional receiver noise independently before choosing detection thresholds. Alternate calibration and measurement runs to expose drift rather than assuming one calibration lasts indefinitely.

Use blinded, randomly ordered source perturbations and negative controls. The controls should change the optical reference, the atom's transition, and the source intensity separately. A programmed modulation command is an intervention, but an independently measured modulation amplitude is still needed to establish the actual delivered signal. Hold back entire acquisition runs or days for evaluation so adjacent correlated samples do not leak across the train/test split.

Compare the existing power and coherent diagnostics with two additions: the atomic sensor and a second independent coherent reference. Report source-change detection at the same tolerated false-alarm rate, estimation error, response time, and data quality. Charge all configurations for their observation time and sampled source light. Separately report the cooling/trapping apparatus, atom number, reference laser, preparation, and readout resources; equal sampled light does not mean equal cost.

The useful result is a reproducible reduction in diagnostic uncertainty that survives changes to nuisance parameters. If improvement occurs only because the atomic reference is assumed more stable, the next experimental requirement is to measure that stability under the intended conditions. Simultaneous drift of all references cannot be separated from absolute source drift from relative-frequency observations alone.

The chip-making connection has a concrete existing benchmark. [Cymer and imec's 2014 study](https://www.cymer.com/wp-content/uploads/2018/12/Cymer_SPIE_AdvancedLithography_2014.pdf) correlated controlled source bandwidth, wavelength, and energy changes with on-wafer pattern measurements, using conventional source monitoring. A future sensor must add information beyond those relevant measurements. A narrow-line visible/near-infrared frequency experiment does not yet reproduce a pulsed 193 nm excimer source, and improved Hz-level estimation alone does not establish improved wafer yield. Before a lithography claim, identify the source, measurand, bandwidth, monitoring point, compatible interaction, and measured relationship to an imaging or process outcome.
