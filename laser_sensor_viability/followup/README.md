# Unknown-onset monitoring across synthetic sessions

Adding the atomic channel still helps the chosen conventional receiver when the event time is hidden, but its benefit is much smaller than in the earlier known-time, long-average experiment. A second stable conventional reference performs best. Requiring two references to agree reduces one serious false-diagnosis failure, while sacrificing sensitivity; it does not solve common-path ambiguity.

This is a **new, separate follow-up**. The parent directory's finals model, results, plots and presentation evidence are unchanged. No laser, wafer or quantum processor was measured, and no IBM account or API is needed for these calculations.

## What changed

The finite-pulse 698 nm sensor physics is imported unchanged from `../model.py`. Its 64 independent atoms, 25 ms interrogation, 1 s cycle, source/reference noise and conventional optical receiver models remain hypothetical laboratory assumptions. Atomic laser-noise spectroscopy is established precedent: [Bishof et al., PRL 111, 093604 (2013)](https://arxiv.org/html/1303.6741v2). This study evaluates a declared classical monitoring algorithm, not a new quantum measurement principle.

Each 128 s record contains either no injected frequency event or a random-sign 0.5 Hz step. Its onset is drawn uniformly from cycles 48–96 and is **never supplied to the detector**. The first 32 s provide detector warm-up. Consequently this is unknown-onset monitoring within a stated interior interval, not validation for arbitrary onset, repeated events or uninterrupted industrial operation.

The causal statistic compares the most recent 16 samples with the preceding 16. At endpoint t it uses only observations acquired before t. A noiseless step reaches its maximum contrast after 16 changed samples and disappears when both windows contain the changed level. This filtering has substantial smoothing and latency; it does not measure arbitrary fast laser noise. The underlying 1 Hz sampling and 97.5% interrogation dead time remain limitations.

Linear fusion weights come from separately generated null training contrasts, with a declared unit local frequency response after the finite response calibration. The optional agreement rule requires same-sign contrasts from both frequency references and scores the smaller standardized magnitude. Both C+Q and C+C receive this alternative, without additional measurements. It is a conservative coincidence test, not a source/reference-identification algorithm.

Every method's threshold is independently calibrated on the **maximum over all 97 scored times in a null record**. The nominal 5% target is therefore an alarm anywhere in 128 s, not a 5% chance at every sample. One null record from each of 256 independently generated calibration sessions provides exchangeable record maxima under the nominal population. The strict upper order statistic does not guarantee the realized false-alarm rate of a fixed calibration, and its protection does not transfer to nuisance shifts.

## Independent sessions and calibration uncertainty

`protocol.json` was written before the first main evaluation. This is a local, specified-before-evaluation protocol, not an external preregistration. Its SHA-256 and the source hashes were saved in `main/provenance_start.json` before generating main held-out results. A tiny, separately seeded `software_smoke/` run exercised the program first; it is not evidence of performance and did not change the scientific settings.

There are **eight independent calibration pipelines**. Each has a separate response scan, 12 training sessions with 16 null records each, 256 threshold-calibration sessions with one record each, and 12 unseen test sessions. Each test session supplies 20 frequency-null and 20 source-event records for each of six scenarios: **1,920 records per class per scenario, 23,040 test records total**.

Session-specific T2, readout errors, reference random-walk strengths, reference offsets and static photodiode gain are independently drawn from the declared distribution. They persist across records in a session; within-record stochastic paths are newly generated. This hierarchy represents separate acquisitions with common apparatus parameters, not one continuous multi-day trajectory. No nuisance parameters or thresholds are fitted to test sessions.

The reported 95% intervals resample **calibration pipelines, then entire sessions** (2,000 hierarchical bootstrap replicates). This captures more than trajectory counting error, but eight calibration repetitions are still few. The intervals are descriptive, conditional on the assumed populations, and have no multiplicity correction. A boundary result with every observed outcome equal can yield a degenerate bootstrap interval, such as [1,1]; that is a resampling limitation, not proof of certainty. `validation.json` additionally supplies a conservative bounded-mean interval over the eight independent pipeline means, including such boundary cases. Neither interval covers physical-model error.

## Nominal held-out result

| Measurements and rule | First post-onset alarm within 32 s | Any alarm in a frequency-null 128 s record | Mean restricted alarm delay |
|---|---:|---:|---:|
| Conventional C | 51.35% | 5.42% | 22.14 s |
| Atomic Q + power | 7.66% | 4.69% | 30.79 s |
| C+Q, linear fusion | 58.02% | 5.16% | 20.78 s |
| C+C, linear fusion | 97.97% | 4.06% | 9.06 s |
| C+Q, agreement | 40.83% | 5.42% | 24.66 s |
| C+C, agreement | 80.68% | 3.80% | 14.95 s |

Adding Q to C increases 32 s detection by **6.67 percentage points**, with a paired pipeline/session-bootstrap interval of **3.96–9.38 points**. C+Q's absolute detection interval is **51.25–64.53%**; its false-alarm interval is **2.60–8.60%**. The broad false-alarm uncertainty is meaningful calibration variability, not hidden by treating thousands of correlated observations as independent.

The first alarm stops the monitor. An alarm at or before the injected onset is a pre-onset failure, even if another threshold crossing later follows the event. The restricted-delay statistic caps delay at 32 s and charges every miss or pre-onset alarm 32 s; it does not average only successful detections. Detected-only delay quantiles are exported separately and must not be presented as the complete operational result. Under nuisance cases, an alarm after the source event may have been caused by the nuisance; temporal coincidence is not correct causal diagnosis.

![Unknown-onset comparison](main/unknown_onset_comparison.png)

The atom is noisy on a 16-sample window. The previous experiment averaged 64 samples on each side of a **known** onset and did not pay the unknown-onset search penalty. These numerical studies have different tasks, nuisance distributions and calibrations. Their percentages must not be interpreted as a controlled before/after comparison of one change, or as an intrinsic sensitivity limit of atomic sensing. More sophisticated classical state-space/change-point inference and separately tuned window choices remain possible.

## Fresh negative controls and the agreement tradeoff

Nuisance steps occur independently at cycles 40–104 in **both** null and source-event populations; their timing and sign are unrelated to the source event. The power disturbance is always +10%. New-session short-coherence tests multiply T2 by 0.06. All previously calibrated rules stay frozen.

| Disturbance | C+Q fusion false alarms | C+Q agreement false alarms | C+C fusion false alarms |
|---|---:|---:|---:|
| Atomic reference steps ±0.7 Hz | 5.83% | 6.88% | 4.11% |
| Primary optical reference steps ±0.7 Hz | 84.53% | 15.57% | 4.79% |
| Shared sampled path steps ±0.7 Hz | 94.11% | 68.23% | 100% observed |
| Source power increases 10%, no injected frequency change | 5.26% | 5.68% | 4.22% |

The agreement rule was motivated by failure cases seen in the old study, but its decision rule and this new test matrix were fixed before these fresh evaluations. It reduces C+Q's primary-reference false alarms by **68.96 percentage points** (paired interval **61.98–75.63 points** reduction). It still misses the nominal 5% goal under that disturbance and reduces nominal detection by **17.19 points**. It is a tradeoff, not a solved diagnostic method. For C+C, requiring agreement actually worsens primary-reference-shift false alarms relative to its optimized fusion rule and reduces detection; a safeguard can discard useful statistical weighting.

Under degraded atomic coherence, C+Q detection falls to **47.34%**, below C's **52.76%** on the same records (paired difference −5.42 points, interval −7.71 to −3.44). Adding a degraded channel with stale calibration can make the system worse.

The shared-path failure is structural. Every frequency channel sees source frequency plus the same path contribution. Without a measurement that distinguishes those quantities, no agreement rule can identify which moved. Lower false alarms obtained by becoming insensitive do not restore identifiability. The power monitor correctly reacts to a power step; calling that a source-frequency alarm would mislabel the measurand.

![Session stress tests](main/session_stress_tests.png)

## Resource and application limits

The original signal-photon allocation is bookkeeping, not a validated coupling/energy/cost match. Reference lasers, atom preparation, cooling, fluorescence readout and support optics remain uncounted. The atomic probe's specified Rabi coupling is not derived from beam geometry and allotted photons. All architectures use the same task duration and shared source paths, but equal information or engineering cost is not claimed.

Per calibration pipeline, the finite response scan represents 2,880 one-second cycles, and training/threshold records represent another 57,344 s. Collecting that serially would take **16.73 hours per pipeline**, or **5.58 days across eight pipelines**, excluding apparatus setup and transitions between sessions. The held-out synthetic records represent another 34.13 days of serial acquisition. These are Monte Carlo simulations, not a proposed turnkey calibration schedule or real acquisition.

Nothing here maps a Hz shift at 698 nm to wafer dose, critical dimension or yield. The intensity control tests cross-sensitivity only. A lithography application requires a compatible monitoring point, wavelength, bandwidth, calibrated sampling path and a measured link from the chosen measurand to exposure quality. The unchanged [research roadmap](../../LASER_DIAGNOSTICS_ROADMAP.md) describes those requirements. Atomic sensing and this classical alarm detector are separate from the project's reversible quantum-model query.

## Reproduce

From the workspace root, with NumPy and Matplotlib installed:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest discover -s laser_sensor_viability/followup -p test_followup.py -v
python laser_sensor_viability/followup/run_followup.py --out laser_sensor_viability/followup/reproduction
python laser_sensor_viability/followup/validate_results.py --run laser_sensor_viability/followup/main
```

The experiment refuses an already used output directory. The checked main run took about 37 s on this computer using Python 3.12.10 and NumPy 2.3.1; Matplotlib 3.10.3 produced the figures. SciPy/QuTiP are not used by this follow-up's numerical dynamics or detector. `record_outcomes.npz` retains every method's null/event first alarm and event onset in pipeline/session order. Six fixed first-test examples retain actual observations, hidden truth, score traces and thresholds; they were not selected for visual appearance.

Nine tests check no future-information access, step/window timing, pre-event alarm accounting, record-maximum calibration, fusion response, agreement veto, cluster uncertainty, photodiode frequency blindness, and deterministic independent session generation. The pre-existing 17 physics/statistics tests and the independent parent Lindblad validation remain applicable to the unchanged imported physics.
