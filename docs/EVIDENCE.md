# Evidence map (V3)

Every headline number, the file it comes from, and how to check it yourself. Nothing here needs an IBM account or a network connection.

Three kinds of evidence appear, and they are never mixed:

- **Exact**: computed from the model's mathematics. No sampling, no hardware.
- **Simulated**: a Qiskit circuit run on an Aer simulator, with or without a noise model.
- **Measured**: raw counts returned by a real IBM quantum processor running a circuit we programmed. The processor's superconducting qubits play the roles of the model. No optical photons were detected.

## The model and the question

| Claim | Value | Kind | Source | Check |
|---|---|---|---|---|
| Chance of a click at step 6, given one at step 3, with no defect | 10.10% | Exact | [`research-validation/original_after_click_verification.json`](../research-validation/original_after_click_verification.json) | `python reproduce.py` |
| The same with the hidden defect | 4.67% | Exact | same | `python reproduce.py` |
| Chance of the click at step 3, with the defect | 3.95% | Exact | same | `python reproduce.py` |
| Runs to match one 64-step record by rejection | 27,495,891 | Exact | [`rewindandamplify-main/results/numbers.json`](../rewindandamplify-main/results/numbers.json), `wall.rejection_runs` | `python rewindandamplify-main/experiments/e3_scaling.py` |
| The same with steering, then with amplification on top | 6,240 runs; 125 machine calls | Exact | same, `wall.steered_runs`, `wall.steered_calls` | same |
| The reversible circuit clicks exactly like the resetting one | amplitudes agree to 4 × 10⁻¹⁶ | Simulated | `numbers.json`, `e1.worst_amplitude_error` | `python rewindandamplify-main/experiments/e1_purify.py` |
| Full amplification leaves the conditional answer untouched | error below 10⁻¹⁴ | Simulated | `numbers.json`, `e2` | `python reproduce.py`, section 2 |
| One round, ideal: lighter build and textbook build | 96.10% and 96.49% | Simulated | `original_after_click_verification.json`, `ideal_circuits` | `python reproduce.py`, section 2 |
| Bias of the lighter build in the ideal circuit | 0.035 (TV distance) | Simulated | [`lab/reference.json`](../lab/reference.json) | `python lab/make_reference.py --check` |
| Classical exact sampler cost per added hidden qubit | about 6× | Exact timing | `numbers.json`, `e3.classical_growth_per_qubit` | `python rewindandamplify-main/experiments/e3_scaling.py` |

## The featured hardware result

IBM Marrakesh, 11 November 2026, job `dbqb1ifv5hds73dfo310`, 8,192 shots per circuit, raw counts, no error mitigation.

| Claim | Value | Source | Check |
|---|---|---|---|
| Lighter build: shots with the click | 6,300 of 8,192 = 76.90% | [`hardware_campaign/runs/original_precision_v1/raw.json`](../hardware_campaign/runs/original_precision_v1/raw.json) | `python reproduce.py`, section 4 |
| Textbook build: shots with the click | 5,674 of 8,192 = 69.26% | same | same |
| Native two-qubit gates | 58 and 125 | [`plan.json`](../hardware_campaign/runs/original_precision_v1/plan.json), and the compiled circuits in `selected_isa.qpy` | `python -m unittest discover -s hardware_campaign/noise_model -p "test_*.py"` |
| Difference and its interval | 7.64 points, 95% interval 6.29 to 8.99 | [`hero_acceptance_contrast.json`](../hardware_campaign/runs/original_precision_v1/hero_acceptance_contrast.json) | `python hardware_campaign/verify_campaign.py` |
| Error in the answer (TV distance of accepted histories from exact) | 0.1177 and 0.1814 | same | `node --test lab/test_data.cjs` recomputes both from the measured histories |
| Two-qubit gates spent per accepted shot | 75.4 and 180.5 | [`hardware_campaign/results.json`](../hardware_campaign/results.json) | `node --test lab/test_data.cjs` |
| No amplification, same chip | 138 of 2,048 = 6.74% | [`runs/original_plain_v2/analysis.json`](../hardware_campaign/runs/original_plain_v2/analysis.json), `click3-full-r0` | `python hardware_campaign/verify_campaign.py` |
| The other two runs that day, lighter against textbook | 77.39% against 64.26% (2,048 shots); 76.46% against 61.96% (with suppression) | `runs/original_plain_v2/`, `runs/original_suppressed_v1/` | same |
| The two futures on hardware, lighter build | 8.79% and 11.66% | [`loop_contrasts.json`](../hardware_campaign/runs/original_precision_v1/loop_contrasts.json) | `node --test lab/test_data.cjs` |

The interval covers shot noise within one job. It does not cover drift between jobs: the same compiled circuits gave a 13.1-point gap in the first run, minutes earlier.

## Simulator against hardware

| Claim | Value | Source | Check |
|---|---|---|---|
| The chip was noisier than its calibration said | gate-error scale 1.54 from two echo circuits | [`hardware_campaign/noise_model/results.json`](../hardware_campaign/noise_model/results.json), `echo_fit` | `python hardware_campaign/noise_model/run_study.py --check` |
| Calibration-only noise model | 83.15% and 76.29% | same, `featured_pair` | same |
| Echo-fitted noise model | 78.40% and 69.72% | same | same |
| Predicted gap against measured gap | 8.68 against 7.64 points; the ideal circuits differ by 0.39 the other way | same, `hit_rate_gap_local_minus_full` | same |
| Predicted two futures, lighter build | 8.44% and 11.29% | same, `after_click` | same |
| Suppression did not help | answer error 0.107 to 0.145 (lighter), 0.201 to 0.244 (textbook) | `runs/original_plain_v2/` against `runs/original_suppressed_v1/` | `python hardware_campaign/verify_campaign.py` |

What the noise model contains and leaves out is stated in [its README](../hardware_campaign/noise_model/README.md).

## The first campaign (qualifying round)

IBM Kingston, 5 November 2026, 4,096 shots per circuit. Kept as it was reported, with its own job IDs.

| Claim | Value | Source |
|---|---|---|
| Lighter build against textbook build, one round each, raw | 3,525 against 3,215 of 4,096: 86.06% against 78.49%, on 40 against 85 two-qubit gates | [`research-validation/hardware_verification.json`](../research-validation/hardware_verification.json) |
| Lighter build against unsteered textbook Grover at three rounds | 0.87 against 0.59, readout-corrected, on 40 against 213 gates | [`rewindandamplify-main/results/hardware/summary.md`](../rewindandamplify-main/results/hardware/summary.md) |
| Noise model against hardware, that campaign | hardware fell below the model on most circuits; about three times the loss per gate | [`rewindandamplify-main/docs/REPORT.md`](../rewindandamplify-main/docs/REPORT.md), section 13 |

The two campaigns used different compilation settings, so the same logical pair is 40 and 85 gates on Kingston and 58 and 125 on Marrakesh. Do not put the two on one chart without that label.

## Follow-up studies

These are simulations, or a reanalysis of data published by others. None is a measurement by our team.

| Claim | Value | Kind | Source |
|---|---|---|---|
| Ignoring detector dead time distorts a fitted coupling | 0.069 fitted, 0.706 once modelled, 0.65 true | Simulated records | [`qrsm_photon_poc/followup/README.md`](../qrsm_photon_poc/followup/README.md) |
| Sources of equal brightness can differ in photon overlap | 1.00, 0.50, 0.20, 0.25 | Calculation | [`quantum_dot_bridge/README.md`](../quantum_dot_bridge/README.md) |
| Laser-frequency monitor, timely detection | 51.35% conventional; 58.02% with an atomic channel; 97.97% with a second conventional reference | Simulated | [`laser_sensor_viability/followup/README.md`](../laser_sensor_viability/followup/README.md) |
| Click-based monitoring of drive amplitude | 3.71% timely detection, with 6.84% false alarms: a negative result | Simulated | [`qrsm_photon_poc/drive_diagnostics_followup/README.md`](../qrsm_photon_poc/drive_diagnostics_followup/README.md) |
| Published GaAs photon-interference data, reanalysed | contrasts 0.8024, 0.8258, 0.7724, matching the authors' values | Reanalysis of data by Münzberg et al. | [`quantum_dot_bridge/hom_analysis/README.md`](../quantum_dot_bridge/hom_analysis/README.md) |
| Two-photon exposure of a resist | 95.16% of scored cells right with entangled pairs, against 78.28% and 83.29% for two laser routes, at 14.9, 6.8 and 0.84 million photons | Simulated, with an assumed resist | [`quantum_lithography_poc/exposure_followup/README.md`](../quantum_lithography_poc/exposure_followup/README.md) |
| Reading a phase with entangled pairs | wrong half-turn 50.4% of the time alone; with a 10% laser pilot, error 0.0064 rad against 0.0079 for laser light | Simulated | [`quantum_lithography_poc/phase_inspection_followup/README.md`](../quantum_lithography_poc/phase_inspection_followup/README.md) |
| The rare-event question for a 49-cell exposure | 389 qubits and about 3.4 million two-qubit gates as an upper bound; the device has 156 qubits | Circuit constructed and checked, not run | [`finals-lithography/full_spatial_circuit/README.md`](../finals-lithography/full_spatial_circuit/README.md) |
| The two photon-pair cases as circuits | measured overlap 0.81 and 0.52, against ideal 1.00 and 0.60 | Ran on IBM Marrakesh, as digital circuits | [`hardware_campaign/RESULTS.md`](../hardware_campaign/RESULTS.md) |
| The atomic sensor channel as a circuit | 32.3%, 48.2% and 72.8% excited, against 20.9%, 50.0% and 79.1% in the model | Ran on IBM Marrakesh, as a digital circuit | [`hardware_campaign/optical_controls/README.md`](../hardware_campaign/optical_controls/README.md) |

The Lab's Photons, Lasers and Chipmaking tabs animate these studies, and `node --test lab/test_research.cjs` holds every formula and number on those tabs to the files above.

The full account, with every limitation, is in [`RESEARCH_CURRENT.md`](../RESEARCH_CURRENT.md). The V2 evidence note, which describes the earlier Kingston comparison in detail, is [`FINALS_EVIDENCE.md`](../FINALS_EVIDENCE.md).

## The Lab

| Claim | Check |
|---|---|
| The Lab's engine computes what Qiskit computes | `node --test lab/test_engine.cjs`: Kraus operators, history probabilities and the full query circuit agree with Qiskit to 10⁻¹² |
| The Lab shows the measured numbers and no others | `node --test lab/test_data.cjs`: every displayed value is recomputed from the campaign's files, whose hashes are recorded |
| The research tabs follow the studies they illustrate | `node --test lab/test_research.cjs`: the photon overlap formula, the atomic response and the exposure model reproduce the studies' saved values; the Lasers tab replays stored records |
| The single file is the folder app | `python lab/build.py --check` |
| The video on slide 10 is the running page | `python lab/capture.py tour` records it again, frame by frame, with a fixed seed |

## Run everything

```bash
python -m pip install -r requirements-dev.txt
python reproduce.py
python .github/scripts/run_tests.py
node --test lab/test_engine.cjs lab/test_data.cjs lab/test_research.cjs laser-diagnostics-app/test_model.cjs
python check_finals.py --public
python verify_research_pack.py .
python hardware_campaign/verify_campaign.py
```
