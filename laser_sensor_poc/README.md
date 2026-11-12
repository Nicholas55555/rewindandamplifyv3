# Exploratory qubit sensor for laser pulse drift

This is a **synthetic, idealized calculation**, inspired by the idea of a quantum sensor watching a sampled laser to diagnose changes relevant to lithography. It simulates neither a laser nor the optical tap, photons, a physical qubit, a chip-making tool, or a wafer. No laboratory data or quantum hardware is used. It asks one limited question: can a temporal sequence of idealized qubit readouts distinguish the two deliberately chosen hidden-drift models when both have the same average readout rate?

## Model and comparison

For each of 128 pulses, initialize a qubit to `|0>`, apply an ideal resonant `Ry(theta)` rotation, then read out and reset. The probability of measuring 1 is `sin²(theta/2)`. The synthetic pulse angle switches between `pi/2 - 0.4` and `pi/2 + 0.4` radians, giving respective probabilities approximately 0.30529 and 0.69471. The hidden state is initially equally likely in either value. One hypothesis switches state with probability 0.02 per step; the matched-rate IID hypothesis switches with probability 0.5, making its hidden states independent. Both have exactly the same theoretical marginal readout probability, 0.5. Individual finite records may have different observed rates.

An ordinary **classical hidden Markov model** calculates the exact likelihood for each hypothesis from the binary sequence. It knows the true emission and switching parameters; no model is fitted or learned. With equal prior probabilities and equal error costs it selects persistent drift when `log P(record | persistent) - log P(record | IID) > 0`. This is the strong, matched known-model classical baseline: it consumes the same readout record, not a weaker summary of it. The only comparison is between two synthetic noise hypotheses, **not between a quantum sensor and an optical/electronic classical instrument**. There is no evidence of a quantum sensing advantage.

For seed 1945 and 2,000 independent records generated under each hypothesis, the saved run gave:

| Measure | Result | Approximate 95% Wilson interval |
|---|---:|---:|
| Persistent records classified correctly | 1,842 / 2,000 = 92.10% | 90.84%–93.20% |
| IID records classified correctly | 1,869 / 2,000 = 93.45% | 92.28%–94.45% |

Balanced accuracy is 92.775%. Average readout rates across the generated samples are 0.49964 and 0.49814, respectively. Wilson intervals reflect finite independent simulated records conditional on this idealized, correctly specified model; they do not account for wrong parameters, model selection, real measurement noise or experimental uncertainty. These choices deliberately create temporally distinguishable noise and are not evidence of expected performance on an actual laser. Zero-prior-knowledge classification, unknown drift parameters, changes in readout quality, and different switching speeds can change results substantially.

`laser_sensor_results.png` shows one simulated trajectory, including its hidden state for illustration, and the distributions of the classical likelihood-ratio score. In a real test the hidden state would not be directly observed. `results.json` contains the numerical summary.

## Physical meaning and limits

- The qubit sees a **pulse area** `theta = integral Omega(t) dt`, not an identified laser-power value. Pulse duration, field amplitude and coupling can produce the same area; without calibrated duration, geometry and coupling, the readout cannot isolate amplitude drift. Detuning, phase noise, decoherence, state preparation and readout errors are omitted. A rotation about an assigned axis assumes a suitable coherent drive and appropriate phase reference.
- The fictional laser-to-qubit link is not a design for a usable optical tap. A real design needs a compatible sensor transition, wavelength, photon flux, collection and coupling efficiency, sampling bandwidth, calibration, detector/reset timing and disturbance budget. Quantum-coherent state evolution alone does not imply the instrument will beat a photodiode, heterodyne receiver or other classical monitor.
- A laser driver and EUV exposure light are different parts of an EUV system. NIST describes industrial EUV radiation near 13.5 nm produced by laser-driven tin plasma; neither the driver's fluctuations nor EUV fluctuations are measured in this simulation, and their relationship requires a validated physical transfer model. See [NIST's EUV working-group report](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1500-208.pdf). For a real discussion of laser-noise effects on atomic-qubit control, see [Day et al., *Limits on atomic qubit control from laser noise*](https://www.nature.com/articles/s41534-022-00586-4). Neither source validates this particular lithography sensor.

A useful next experiment would add calibrated readout/decoherence and uncertain parameters, test on held-out drift patterns, and compare against a physical classical optical monitor at the same tap position, photon budget, bandwidth, acquisition time and error metric. Real feasibility depends on identifying a target measurement and obtaining measured or physically justified system parameters first.

## Fixed-classifier robustness and identifiability

`robustness_check.py` evaluates the **original ideal-readout classifier and its fixed zero log-likelihood-ratio threshold**, without refitting or retuning, on fresh independently seeded synthetic records. It leaves the original `results.json` unchanged. For each scenario, 1,200 persistent and 1,200 IID records use the same pulse-angle processes as above, with a symmetric independent bit-flip readout channel applied to **both** classes. Positive means “persistent”; IID is the null. The theoretical marginal rate remains 0.5 for both classes. The original classifier does not know the noise has been added.

| Bit-flip rate | True positives / 1,200 | Detection rate (95% Wilson) | False positives / 1,200 | False-alarm rate (95% Wilson) |
|---|---:|---:|---:|---:|
| 0% control | 1,102 | 91.83% (90.15%–93.25%) | 93 | 7.75% (6.37%–9.40%) |
| 10% | 911 | 75.92% (73.42%–78.25%) | 77 | 6.42% (5.16%–7.95%) |
| 25% | 403 | 33.58% (30.97%–36.30%) | 81 | 6.75% (5.46%–8.31%) |

The seeded result illustrates substantial detection-power loss under readout mismatch; it does not establish an operational false-alarm rate or compare against a noise-aware retrained classifier. Here symmetric flips leave the IID null as IID Bernoulli(0.5), so differences among its finite-sample false-alarm estimates should not be interpreted as a demonstrated change in the null distribution. Wilson intervals describe Monte Carlo sampling for each stated synthetic case, not measurement uncertainty or generalization to real lasers. The assumed bit-flip rates are illustrative stress settings, not experimentally measured rates.

The same script checks pulse-area identifiability in the constant-drive toy: `theta = amplitude × duration` in normalized units. Replacing amplitude `A` by `sA` and duration `T` by `T/s` leaves both `theta` and `sin²(theta/2)` exactly unchanged for any positive scale `s`. Thus this readout alone cannot separate those changes under this model; example equal-area pairs and probabilities are saved in `robustness_results.json`. Physical bandwidth, pulse shapes and independent calibration could change what can be identified in a richer model.

## Reproduce

Requires Python, NumPy, and Matplotlib. From this directory:

```powershell
python -m unittest -v test_sensor_sim.py
python sensor_sim.py --overwrite
python -m unittest -v test_robustness_check.py
python robustness_check.py --overwrite
```

Both scripts refuse to replace their respective result files unless `--overwrite` is explicitly given. The tests independently enumerate hidden paths to check the forward likelihood, prove the matched IID likelihood for short sequences, and verify the Born probabilities, bit-flip channel endpoints, and pulse-area invariance. If Qiskit is available in the test interpreter, an additional test compares five angles directly with `Statevector` after `ry`; otherwise that test is reported skipped. All nine tests passed using the project's available audit virtual environment, including the Qiskit check.

## Complementary sensor fusion: separate synthetic experiment

`fusion_check.py` explores a different question: can a hypothetical second sensor add information about the same **synthetic hidden regime**? It does not model an actual sensor or a physical causal mechanism for lithography-laser noise. Both readouts share a binary hidden state. The qubit readout uses the same ideal pulse-area model above, with state-conditioned probabilities `[0.30529, 0.69471]`; the hypothetical classical sensor has deliberately chosen, **uncalibrated** response probabilities `[0.35, 0.65]`. The chosen classical response has weaker state contrast (0.30 versus approximately 0.38942); this is an input assumption, not evidence of a sensor-platform advantage. Each readout is binary and has theoretical marginal probability 0.5 in both regimes. No wavelength, efficiency, tap loss, photon budget, sensitivity or real instrument is modeled.

The three tests use the **same simulated records**: classical sensor only, qubit readout only, or both jointly. The analysis for each is the exact *classical* HMM likelihood ratio with its correct prespecified model and a zero threshold fixed before testing (equal prior probabilities and equal error costs); no learning, parameter fit or threshold tuning occurs. A shared hidden path switches with probability 0.02 under the persistent hypothesis and 0.5 under the IID hypothesis. The sensors are assumed **independent conditional on that shared state**. Under IID, their shared state still correlates their outputs within a time step; the joint likelihood explicitly retains that dependence. The qubit is reset each time and its outcomes are sampled classically from the Born probabilities: this is a simulation of readout statistics, not a run on quantum hardware.

With seed 540072, independently generated streams for the two hypotheses, and 1,200 records per hypothesis of 128 steps each, the saved `fusion_results.json` reports:

| Readout used | True positives / 1,200; detection rate (95% Wilson) | False positives / 1,200; false-alarm rate (95% Wilson) |
|---|---:|---:|
| Hypothetical classical only | 971; 80.92% (78.60%–83.04%) | 166; 13.83% (12.00%–15.90%) |
| Qubit only | 1,115; 92.92% (91.32%–94.24%) | 75; 6.25% (5.02%–7.76%) |
| Joint | 1,168; 97.33% (96.26%–98.10%) | 20; 1.67% (1.08%–2.56%) |

These are **fixed-threshold, model-conditional** Monte Carlo outcomes, not performance on a laser. Intervals apply to each rate for the stated synthetic setting; the three tests are paired because they use the same records, and the individual intervals are not confidence intervals for differences between methods. Their false-alarm rates differ, so the table is not a matched-false-alarm comparison. The classical response strengths were chosen by assumption; they do not represent or rank real sensors. The joint method uses an additional measurement resource, and each arm's photon budget is undefined and need not be equal. No two-classical-sensor combination is included. Conditional independence may fail in practice. This shows neither an end-to-end quantum advantage nor a fair comparison of physical instruments. A separate, calibrated experiment would need physical sensor response, shared-noise correlations, tap disturbance, and a classical optical/electronic baseline at the same resource budget.

The additional tests compare the joint forward algorithm with a direct sum over all hidden paths, check the IID shared-state correlation, and show that adding a sensor with `[0.5, 0.5]` response leaves the likelihood-ratio decision unchanged. All 13 tests, including the previous nine, passed in the audit Qiskit environment. To reproduce, from this directory:

```powershell
python -m unittest -v test_fusion_check.py
python fusion_check.py --overwrite
```

This script refuses to replace `fusion_results.json` without `--overwrite` and does not alter the previous experiment's results.
