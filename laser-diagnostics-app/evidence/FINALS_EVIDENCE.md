# Finals evidence: the IBM rare-click comparison

Updated 11 November 2026. The first sections trace the original IBM experiment, based on files in `rewindandamplify-main (1).zip`. The final section traces the new local research studies used in the revised presentation. The November 11 campaign adds new actual IBM jobs; its section below supersedes any earlier no-submission status. The archive's `results/hardware/` folder contains raw counts, calibration data, compiled circuits, analysis summaries, and job identifiers. The reports below use the archive's names so the result can be checked without relying on a slide alone.

## November 11: new real IBM execution and photon-memory research

The [hardware campaign](hardware_campaign/README.md) now contains newly submitted
and retrieved real IBM jobs, immutable circuits, raw counts, calibrations and
[analysis](hardware_campaign/RESULTS.md). Its [25-family coverage ledger](hardware_campaign/coverage.json)
distinguishes complete gate-model executions, component emulations, classical
studies and physical/resource limits. A component run does not reproduce an
entire online diagnostic or optical apparatus.

The [joint-photon QRSM extension](quantum_dot_bridge/qrsm_hom_followup/README.md)
is implemented and checked: sequential emission retains an environment state,
then a joint two-photon measurement conditions that state. Passive observations
can contain no information about the tested memory. At the initial controlled
64-pair budget, detection was 5.60% versus 4.50% null flags. A separately selected
and freshly validated control design reached 79.75% versus 4.85% at **2,584
attempted pairs**, with perfect reset/control assumptions. Strong classical HMMs
predicted equally well within uncertainty. At larger budgets, detector, mode or
collection changes produced severe false diagnoses. No physical dot was fitted
or diagnosed, and no quantum computational advantage was established.

Real superconducting circuits now test these specified models. They do not
establish optical coupling, wavelength compatibility, detector calibration,
resist response, manufacturing yield or economic savings. The available devices
have 156 qubits; the full 219/389-qubit spatial constructions cannot fit.

## Archived question and experiment

The test asks for a click at step 3 in the project's emitter-plus-one-defect model. It compares circuits that prepare and sample different amplified versions of the model. The device is an IBM superconducting quantum processor representing the model; it is not an optical wafer experiment and has not identified an unknown microscopic defect.

The first unsuppressed Kingston run, `results/hardware/raw_plain.json`, records job `dbmfqlt8ft8s738uplmg`, submitted 2026-11-05, with 4,096 shots per circuit. The repeat, `raw_plain2.json`, records job `dbmfv758ft8s738upsdg`, also 4,096 shots per circuit. These are archived metadata and counts, not independently retrieved from IBM for this review.

## The key numbers

The event rates commonly presented as **87% versus 59% are readout-corrected**, not the raw observed counts. Both raw and corrected numbers are worth showing. Lower total variation distance (TVD) means the accepted click-history distribution is closer to the exact model's conditional distribution.

| Kingston circuit | Two-qubit gates | Raw event hits, first run | Readout-corrected rate, first run | Corrected conditional-history TVD | Corrected repeat rate |
|---|---:|---:|---:|---:|---:|
| Plain, no steering or Grover | 13 | 248/4096 = 6.05% | 5.98% | 0.071 | 6.16% |
| Steering only | 13 | 875/4096 = 21.36% | 21.43% | 0.090 | 20.00% |
| Steering + full reflection, 1 iteration | 85 | 3215/4096 = 78.49% | 79.29% | 0.069 | 79.34% |
| Steering + local reflection, 1 iteration | 40 | 3525/4096 = 86.06% | 87.36% | 0.055 | 88.18% |
| Full reflection, no steering, 3 iterations | 213 | 2397/4096 = 58.52% | 58.95% | 0.263 | 55.08% |

For the repeat of the older local-versus-unsteered-full-r3 comparison, the uncorrected counts are 3,574/4,096 = 87.26% and 2,196/4,096 = 53.61%, respectively. Raw counts were independently re-counted from `raw_plain.json` and `raw_plain2.json`, using the click-at-step-3 bit convention implemented by `experiments/analyse_hardware.py`. Table entries originate in the project's saved summaries; the targeted reproduction below verifies the closer one-round pair rather than the entire table.

For the **closer steered one-round pair**, `research-validation/verify_hardware.py` subsequently rebuilt both logical circuits and reproduced their raw event rates, calibrated readout correction, ideal event probabilities, and conditional-history TVDs for both saved jobs. All reproduced values matched the archived summaries within numerical tolerance. The repeat raw counts for that pair are 3,574/4,096 (local) and 3,220/4,096 (full). `research-validation/hardware_verification.json` records source hashes and the results. This targeted rerun does not revalidate every other table entry or independently retrieve a job from IBM.

The ideal local-reflection circuit already has conditional TVD 0.0353 in this case, versus essentially zero for the ideal full reflection. It is an approximation even before hardware noise. The table's conditional TVD refers to **observed history distributions**, not a measurement of hidden quantum state fidelity.

## What this comparison does and does not establish

- The steered local circuit had a higher readout-corrected event rate and lower conditional-history TVD in these two saved jobs than the selected unsteered, full-reflection, three-iteration comparison. It also compiled to fewer two-qubit gates on this device.
- The headline comparison changes **steering, reflection, iteration count, and physical-qubit placement** together. The local circuit uses physical qubits `[142, 143, 136, 144, 141]`; the full r=3 circuit uses `[126, 124, 117, 125, 127, 123, 105]`. It is evidence for the combined design on these runs, not a clean causal measurement of the local reflection or gate count alone.
- For a closer reflection comparison, the two steered r=1 variants are in the table, although their physical placements and compiled circuits still differ. The no-steering r=3 local circuit is another useful ablation: 112 two-qubit gates, 75.68% raw hit rate, 76.28% corrected, corrected TVD 0.0923 in the first run. It is in the same source files under `click3-memory+last-1-r3`.
- Readout correction uses independent single-qubit flip rates from all-zero and all-one calibration circuits and clips the inferred probabilities to a valid distribution. It is an estimate based on that calibration model; correlated measurement errors and drift are not fully captured. The raw counts remain available.
- 4,096 is the number of shots **per circuit per job**. Approximate binomial shot error alone is about 0.54 percentage points for 86.06% and 0.77 points for 58.52%; this ignores readout-calibration uncertainty, drift and other systematic effects. Treat the two nearby jobs as a repeat, not as evidence of broad performance across all hardware or days.
- `summary_noisemodel_ibm_kingston.json` is a local noisy simulation, not a chip run. For the same featured circuits its readout-corrected event rates are 90.09% and 76.25%, respectively. The comparison illustrates that the device performed differently from its snapshot noise model; do not mix simulator values into the hardware column.
- At this scale the project's classical sampler is faster. The work does not demonstrate quantum computational advantage. It rewinds a reversible **model circuit**, not a measured photon, an actual defect, or a semiconductor wafer.

## Archived Kingston explanation (historical comparison)

> “We asked our model for a click at a particular step. On IBM Kingston, both circuits used steering and one amplification round. The local-reflection circuit gave the event in 86% of raw shots, compared with 78% for full reflection. Their readout-corrected estimates were 87% and 79%. The compiled circuits used 40 and 85 two-qubit gates, and their accepted histories were both close to the exact model. Their physical-qubit placements and compiled circuits differed, so the comparison does not isolate reflection alone. A classical computer is faster at this small scale.”

For a slide footnote: “IBM Kingston, 4,096 shots/circuit, 5 Nov 2026; 86%/78% raw, 87%/79% readout-corrected; placements differ.” Keep the 40-versus-213-gate full-design comparison and the repeat in backup material.

## Quick Q&A

**Why check the distribution as well as the hit rate?** Amplifying an event can make it common while biasing which matching histories are returned. TVD compares the distribution of accepted histories with the exact conditional model, so a successful-looking event rate alone is not enough.

**What is new?** The team's documented contribution is the mapping to a recurrent hidden-state model and the hardware-aware exploration of steering and local reflections. Amplitude amplification and quantum rejection sampling are established ideas.

**What would make the evidence stronger?** Repeat on additional days and devices; compare physical-qubit placements and suppression settings under a prespecified design; quantify systematic and calibration uncertainty; report cost against strong classical baselines; and test conditional-history accuracy beyond this small example.

## Current research evidence for the revised finals materials

The studies in this table are local synthetic or circuit-construction results. The new campaign separately executes selected components on IBM; it does not turn their simulated diagnostic rates into physical optical or wafer measurements. `RESEARCH_CURRENT.md` and the study READMEs provide the full methods, controls and remaining questions.

| Topic | Result used in the presentation | Canonical evidence |
|---|---|---|
| Detector-aware inference | Simulated coupling truth 0.65; omitted dead time fit 0.069; included dead time fit 0.706. Correcting the detector improves held-out prediction by 0.4584 nats per 24-bin record, but other parameters remain biased or at a bound. | `qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit0.json`, `fixed_411101_dead1_fit1.json`, and `../independent_review.json` |
| Unknown-onset frequency monitoring | Timely detection within 32 s: C 51.35%, C+Q 58.02%, C+C 97.97%. Full 128 s record false alarms: 5.42%, 5.16%, 4.06%. Eight independent calibration pipelines, fresh sessions, 1,920 records per class/scenario. | `laser_sensor_viability/followup/main/results.json`, `record_outcomes.npz`, `../validation.json` |
| Frequency-monitor failures | Primary-reference drift: C+Q fusion 84.53% false alarms, agreement 15.57%. Agreement also lowers nominal detection to 40.83%. Common-path shift remains ambiguous. | Same unknown-onset sensor results; preserve method and scenario labels. |
| Changing effective drive | +20% field step: physical-history 19/512 timely detections (3.71%), HMM 16/512 (3.13%). Stable-source record false alarms 6.84% and 5.27%. These are 96 arbitrary-time bins, not seconds. | `qrsm_photon_poc/drive_diagnostics_followup/main/results.json`, four raw NPZ archives and `independent_review.json` |
| Prior-only diagnostic control | On +20% steps, normalized RMSE 0.11251 with observed bits versus 0.11362 using the same fitted prior alone. Other evaluated source-change scenarios worsen relative to that prior. This is a post-holdout descriptive control. | `qrsm_photon_poc/drive_diagnostics_followup/main/prior_only_estimation_control.json` and `prior_only_independent_review.json` |
| Optical phase inspection | At 20,000 mean object-incident photons, transmission/detection efficiency 0.81 and preparation success 1, global phase RMSE is 0.006371 rad for a charged 10/90 hybrid versus 0.007908 rad for the specified coherent reference. Pure NOON is π-ambiguous. | `quantum_lithography_poc/phase_inspection_followup/results.json` and `verification.json` |
| Quantum-light exposure | Five source strategies, nine cases, 540,000 weak-activation realizations. Loss, blur, linear response and source failure can erase a favorable contrast or threshold result. Optical moments and material response are separated. | `quantum_lithography_poc/exposure_followup/results.json`, `moments_supplement.json` and `verification.json` |
| Full 49-cell circuit | Two explicit 389-qubit circuits constructed and independently read back. Constructive one-round generic CX upper bounds: 2,874,028 and 3,382,108. No full-state or noisy 389-qubit simulation. | `finals-lithography/full_spatial_circuit/results.json` and `independent_review.json` |
| Strong spatial baseline | Exact conditional sampling for the correlated 2×2 model; original 7×7 deterministic probability brackets and 12 million evaluation maps. Tuned importance sampling reduces empirical SD 4.36×/7.32× versus the old fixed proposal at two tested doses. | `finals-lithography/followup/correlated_spatial_results.json`, `spatial_coverage_refined_results.json`, `validation.json` |
| Three-bin coherent optical query | Finer retained model: all-three-click probability 0.0141777% to 0.1275509%, 18 qubits, 19,864 generic CX. The earlier noise check was one-bin; the new hardware campaign now also executes the expensive two/three-bin circuits as noise stress tests. | `qrsm_photon_poc/multibin_followup/main/ideal_0p003.json`, `noise_0p003.json`, `validation.json` |
| Numerical validity and identification | Independent finite-model QuTiP agreement, cutoff sensitivity, six joint fits, HMM/telegraph baselines and parameter audits. Controlled settings break an exact sign symmetry but do not establish confident finite-data detuning-sign identification. | `qrsm_photon_poc/followup/dynamics_results.json`, `inference_results/`, `parameter_validation_v2/`, `independent_review.json` |

The unknown-onset sensor numbers replace the earlier known-time result in the main talk. Earlier values such as 85.98% detection, 0.161 Hz RMSE and 80.10% atomic-drift false alarms remain valid only for their original experiment. The app labels that older study separately. Do not combine its rates, errors or scenario names with the newer experiment.

For phase inspection, low preparation success costs time at equal photon dose. It does not automatically erase the equal-dose precision benefit. At equal time, inefficient preparation removes the benefit in the tested setting. Greater loss can remove the precision benefit even at equal dose. The hybrid's coherent pilot photons and both object-incident modes count toward the budget; pump/herald energy and apparatus costs remain outside the model.

The research archive's independent checks include 79 focused tests from a fresh extraction. This validates the declared numerical implementation and provenance, not real-source performance. A physical diagnostic claim still requires calibrated source/detector/reference measurements and independent alternative-cause tests.

## Later semiconductor exploration

The quantum-dot work is separate from the earlier frozen research snapshot and the IBM hardware experiment. The [study README](quantum_dot_bridge/README.md) connects confined semiconductor states to photon quality and gives the source literature.

| Evidence | Supported conclusion | Canonical files |
|---|---|---|
| Illustrative optical-dot model | Equal imposed brightness and ideal single-photon purity can coexist with overlaps 1.00, 0.50, 0.20 and 0.25. Pair correlations can matter even at fixed single-photon marginals. | `quantum_dot_bridge/results.json`, `PROTOCOL.md`, `independent_review.json` |
| Acquisition accounting | Independent per-photon survival 0.2 instead of 0.8 requires 16 times as many attempts for equal expected surviving-pair counts. This is conditional cost accounting, not measured hardware expense. | Same benchmark; its assumptions exclude correlated loss and apparatus cost. |
| External experimental histograms | Six co/cross-polarized GaAs HOM records are retained unchanged with Zenodo checksums and CC BY 4.0 attribution. Published author values and our derived values have distinct labels. | `quantum_dot_bridge/reference_hom/provenance_manifest.json`, `DATA_LICENSE.md` |
| Bounded HOM reanalysis | Integrated-peak estimates depend on declared reference normalization and calibration. Conditional statistical uncertainty and protocol sensitivity are separate; microscopic noise identification is unsupported. | `quantum_dot_bridge/hom_analysis/PROTOCOL.md`, `results.json`, `README.md` |

These optical measurements come from Münzberg and colleagues, not the team. The toy coherence model is not fitted to them. The reanalysis cannot establish that a hidden defect caused an observed reduction, that a quantum algorithm speeds up diagnosis, or that a source is suitable for a lithography tool.

For the judges, the connection is a requirement for the next QRSM observation model. Its original sequential binary record does not include a joint two-photon interference measurement. The illustrative offset example also gives overlap 1.00 versus 0.60 for persistent versus independently redrawn offsets while each photon's frequency distribution stays fixed. This supports checking temporal correlations and appropriate measurements; it does not establish coherent defect memory. The joint-photon extension is now implemented and has synthetic and real gate-model checks. A physical device fit remains absent. Its acquisition and nuisance tests show why calibrated controls and strong classical alternatives are essential for source qualification.
