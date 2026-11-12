# Diagnosing a time-varying effective drive from retained-state click histories

This study directly implements the amplitude-schedule experiment proposed in `LASER_DIAGNOSTICS_ROADMAP.md`. The original driven emitter–defect–cavity system now experiences an unknown-onset step or a randomly switching drive. Its quantum state persists through each change. A causal filter tries to infer the source change from the observed binary detector record, alongside classical history and count-based comparisons. Separate source-stable detector and emitter changes test whether the filter attributes the wrong cause.

Everything here is a local synthetic experiment. No laser, fabricated sensor, wafer, IBM processor or API is used. The original photon companion, finals evidence and application are unchanged.

## Result: this regime is a weak amplitude monitor

The implemented inference is mathematically consistent, but the chosen measurement budget does **not** demonstrate a useful source-amplitude diagnostic. With about 20 occupied detection bins per 96-bin record, timely source-change detection is poor. Detector artifacts can produce false source alarms. All cases and negative results are retained.

| Frozen method | Nominal stable-source false alarms per 96-bin record | +20% field step detected within 32 bins | Restricted delay, misses charged 32 bins |
|---|---:|---:|---:|
| Physical-history model | 6.84% | 3.71% | 31.60 |
| Three-state classical HMM | 5.27% | 3.13% | 31.72 |
| Count contrast | 1.95% | 1.76% | 31.70 |

Each nominal/source-step column uses 512 separate held-out records across four pipelines. The physical-model detection fraction is 19/512, with a descriptive hierarchical bootstrap interval of 1.37–7.03%. Its nominal false-alarm interval is 3.90–9.96%. The paired physical-minus-HMM timely-detection difference is only +0.59 percentage points, with interval −1.76 to +3.32 pp. This does not establish a useful advantage. Realized false alarms differ despite the common nominal 5% calibration target, particularly because the count statistic has ties.

The physical model alarms somewhere in 13.28% of +20% step records, but most alarms arrive later than the 32-bin response horizon. Reporting that larger fraction alone would conceal the poor timely response. For the ordinary telegraph source, timely detection is 1.88% among 480 eligible records; eight records never activate and 24 activate too late to provide 32 bins of follow-up. Faster telegraph detection is 0.78%.

With an unchanged source, increased dark counts and afterpulsing produce physical-model false alarms in 10.74% and 10.55% of records; combined detector drift gives 10.35%. A real source step accompanied by independent efficiency loss is detected within 32 bins only 0.78% of the time. These are explicit failures of robust source attribution in the tested regime, not successful laser diagnoses. Reduced alarms under efficiency loss or emitter detuning likewise do not prove the filter identified those nuisance causes.

All four baseline-drive fits select 1.3, but independently trained source increments vary across .20, .10, .30 and .30. Thus even this restricted amplitude fit is sensitive to finite training data. No new threshold, drive candidate or source model was chosen after inspecting the main holdout.

![Detection and false source alarms](main/drive_detection.png)

## How much estimation value comes from the observed bits?

For +20% step records, causal drive-estimation RMSE is 0.11251 in units of the true baseline drive, versus 0.17850 if the calibrated baseline is kept unchanged. That comparison alone is weak: the model already assumes a positive source-change prior.

After seeing the main result, a **separately labeled descriptive control** evaluates the exact same fitted prior while ignoring the per-record detector bits. Its RMSE is 0.11362, almost the same as the observation-based estimate. The paired reduction in mean squared error from using the bits is 0.0002515, with descriptive four-pipeline interval [0.0000788, 0.0004460]. Most of the larger improvement over an unchanged baseline is therefore explained by the source prior. This control does not change the frozen records, fitting, thresholds or detection results and is not a preplanned confirmatory comparison.

The observation-based estimate has worse RMSE than the prior-only predictor for ordinary/faster telegraph cases, the +10% step and the source step with efficiency loss. In the stable-source case, the model reports an average positive drive error of 0.06942 and RMSE 0.07863, while keeping the correctly calibrated baseline unchanged has zero error in this synthetic setting. Accurate inference of an arbitrary unknown drive is not demonstrated.

The control uses each pipeline's actual training-selected increment and baseline. It propagates the step/telegraph schedule distribution without observation updates; it does not use the true source path. Exact per-scenario comparisons, paired errors and hashes are in `main/prior_only_estimation_control.json` and are reproducible with `prior_only_control.py`.

An independent review checked the prior against closed-form step/telegraph marginals, every paired raw error, all 52 summary metrics and the bootstrap intervals. They agree to numerical precision; `main/prior_only_independent_review.json` records that separate review. It does not change the exploratory status of the control.

![Observed-data estimate versus prior-only control](main/prior_only_comparison.png)

## What the amplitude means

The Hamiltonian contains `0.5 Ω (sigma+ + sigma-)`. Ω is an effective driving Rabi frequency, an optical **field-amplitude proxy** when the dipole, beam geometry and coupling are fixed. Under that limited mapping, intensity is proportional to Ω²: +20% field corresponds to +44% intensity, and +10% field to +21%. It is not a calibrated pulse-energy or incident-photon measurement. The emitted cavity/fluorescence response is nonlinear and depends on the sensor's hidden state.

Rates retain the original arbitrary inverse-time units. A record contains 96 bins of duration 1; these are not seconds. The emitter, defect and four-dimensional cavity begin in their common zero state once per record. They are not reset when the source or detector changes. Different records reset independently. Preparation/reset overhead, absolute optical power, wavelength compatibility, saturation limits and real electronics are unmodeled.

The generator carries a conditional physical density matrix through each bin. Its two outcome maps distinguish no registered event from at least one registered event, already including independent dark counts. Binary count totals therefore measure occupied detection bins, **not all emitted photons**. The saved `pre_afterpulse_clicks` field additionally excludes the added afterpulse mechanism; it still includes the base instrument's dark counts and is suppressed during blind bins.

## Unknown schedules and causal inference

A source step starts uniformly between bins 16 and 48. The telegraph source starts low and begins switching at bin 16, with probability .06 per bin; its mean dwell after switching begins is 16.67 bins. A shifted test uses .20 per bin. Actual schedules are generated independently and saved for evaluation. The predictors receive only the bits and the specified schedule distribution, never the true source states or nuisance onset.

The physical-history filter maintains one unnormalized quantum density matrix for each possible classical source regime. Before the next observation, a classical transition mixes those matrices and the appropriate drive-dependent quantum instrument acts. The observed bit then updates both the regime weights and the quantum states. This exactly sums latent source histories for the finite model without resetting or enumerating exponentially many schedules.

There are three hypotheses: baseline, unknown-onset step, and telegraph. Baseline/source class priors are one half each, and step/telegraph share the source prior equally. The causal amplitude estimate is their mixture posterior mean. A good fit to this family does not establish that the change came from the laser rather than an unmodeled sensor or detector perturbation.

The trained alternatives cover **increased** effective drive. They are not a detector for arbitrary signed instability, and decreased source drive is not an evaluated source case. The count contrast is two-sided, a deliberately broader rule with its own independently calibrated threshold.

All inference is classical computation. The comparisons use the **same held-out bits**:

- Physical-history likelihood, with known model structure and finite calibration.
- Separate three-state classical HMMs trained on baseline and source labels, with three EM starts and training-only likelihood refinement. These models retain classical history.
- Absolute count-rate contrast between adjacent 16-bin windows, first available at the end of bin 32.

The physical model has substantial prior information and extra calibration; the HMMs receive the common labeled training histories. This compares ways of analyzing one sensor output. It is not a comparison with an independently engineered photodiode, nor a matched-photon experiment, quantum advantage, or proof that classical methods cannot reproduce the record.

## Independent calibration, training and evaluation

Each of four independent pipelines contains:

| Stage | Data per pipeline | Use |
|---|---:|---|
| Detector calibration | 10,000 one-photon trials; 20,000 dark-only bins | Estimate efficiency and dark rate |
| Baseline response | 128 × 96-bin records | Select Ω from 1.1, 1.3, 1.5 |
| Labeled training | 128 baseline + 128 source records | Select drive increment from .10, .20, .30; fit HMMs |
| Null threshold calibration | 256 × 96-bin records | Set each maximum-over-record threshold |
| Held-out evaluation | 128 records × 13 scenarios | Score all frozen methods and counterfactuals |

The detector calibration is an idealized independently controlled calibration experiment, not measured device characterization. Other physical parameters remain known. Source-training records contain equal numbers of step and telegraph examples; their latent paths are not used to fit the models. Neither drive candidate nor HMM parameters are selected using the holdout.

All four pipelines share the same nominal physical parameter values; they independently repeat finite calibration, training, thresholds and held-out sampling. Changed source amplitudes, switching rates and nuisance settings are the explicitly declared physical counterfactuals. This is not a study of four independently varying devices or broad unknown-parameter robustness.

For each method, the alarm statistic is the largest causal score over the entire 96-bin record. Threshold calibration uses a strict exceedance of order statistic `ceil((N+1)×.95)` in the independent null maxima. This controls the nominal false-alarm probability for a fresh exchangeable **record**, not per bin, second or hour. Discrete count ties can make the count comparator conservative. Drift violates nominal exchangeability; its false alarms are measured explicitly.

The first alarm stops the detector. An alarm before source onset is a failure. Detection-within-32-bin denominators include only actual source changes with at least 32 further bins observed. Telegraph records with no activation or a later first activation are counted separately. Misses and prealarms receive a full 32-bin penalty in the restricted-delay average; the metric does not hide failures by averaging detected events alone.

Drive-estimation errors are calculated from `fitted Ω × (1 + inferred fractional change)` against the true effective drive, and normalized by the true baseline Ω solely for evaluation. The constant comparator keeps the **fitted** baseline unchanged. It does not receive the true baseline. Bias and RMSE uncertainty describe performance across simulated records and calibrations, not calibrated posterior coverage or unique physical identification.

The four pipelines contain 6,656 held-out records / 638,976 modeled observation bins. Response, training and threshold calibration add 2,560 records / 245,760 bins, plus 120,000 detector calibration trials. The model does not assign a physical time cost to preparing each new record or supplying the calibration photons. Performance uncertainty uses a hierarchical bootstrap over the four pipelines and their independent records. Four clusters give limited calibration-variation precision; percentile coverage has not been calibrated. A zero observed count, including a degenerate zero bootstrap interval, does not establish zero population probability.

## Counterfactuals and scope

The 13 scenarios include nominal stability, +20% step/telegraph drive, +10% step, faster switching, collection-efficiency loss, increased dark counts, emitter detuning, increased cavity loss, onset of one-bin detector dead time, onset of afterpulsing, combined detector effects, and a source step plus independent efficiency loss.

Afterpulses add a recorded flag with probability .10 when the previous bin registered a click. Their next-bin Markov approximation includes cascades. For a previous click, the observed maps become `.9 E0` and `E1 + .1 E0`; afterpulse-only flags do not correspond to newly emitted photons. During a blind bin after a click, the observed result is forced to zero while the physical state evolves through `E0+E1`. Neither effect is included in the nominal trained filter, deliberately exposing model mismatch.

An emitter detuning change is a sensor-side perturbation, not automatically laser-frequency motion. Cavity loss changes the physical dynamics; detector efficiency changes the observed fraction. Their distinction matters even when both alter click rates. No nuisance-induced alarm counts as a correct source diagnosis. Continuous spectral diffusion, realistic trap-dependent afterpulsing, thermal fields, multimode cavities and unmodeled environmental memory remain additional research questions.

## Reproduction and audit

Use the recorded NumPy/SciPy environment, with one BLAS thread:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -m unittest discover -s qrsm_photon_poc/drive_diagnostics_followup -p test_model.py -v
python qrsm_photon_poc/drive_diagnostics_followup/run_study.py --out qrsm_photon_poc/drive_diagnostics_followup/reproduction --max-seconds 1800
python qrsm_photon_poc/drive_diagnostics_followup/validate_and_plot.py --run qrsm_photon_poc/drive_diagnostics_followup/reproduction
python qrsm_photon_poc/drive_diagnostics_followup/prior_only_control.py --run qrsm_photon_poc/drive_diagnostics_followup/reproduction
```

The runner refuses existing output directories. A watchdog limits the whole process, preserving any completed pipeline archives. `PROTOCOL.md`, imported source hashes, actual software versions and all 229 random-stream namespaces are saved before the main run. Measurement, latent schedules, nuisance onset, HMM initialization and calibration have explicitly distinct SeedSequence streams. A pre-main independent review caught offset-based seed reuse; it was corrected before main evaluation. Earlier reduced smoke outputs remain preserved as software checks, not scientific evidence.

Ten tests cover source-path marginalization, full-history normalization, retained state versus reset, detector readout mixtures, dead-time exclusions, HMM likelihood, causal count windows, threshold ties and unique stream namespaces. The result validator independently reconstructs first alarms, onset eligibility, penalties, normalized-drive errors and summary metrics from the archived bits/scores, verifies source/archive hashes, and reruns the tests. Cavity-4 versus cavity-5 deterministic schedule predictions are a numerical sensitivity check, not proof of infinite-cavity convergence or hardware validity.

The first main run completed all four pipelines in 207.5 s without a timeout. Ten tests and the stored-result validation passed. An independent reviewer recounted all 273 reported summaries, replayed every held-out HMM/count result and selected physical-model predictions, and checked future-bit causality, calibration, stream uniqueness and hashes; its receipt is `main/independent_review.json`. The largest cavity-4 versus cavity-5 unconditional schedule click-probability difference was 0.000543 across the baseline, step and alternating probes (about 0.0543 percentage points). This limited numerical check does not establish convergence of all conditional likelihoods or all nuisance settings. Figures were visually inspected.

The next physical step requires compatible emitter/cavity hardware, independently characterized source modulation, detector calibration and a synchronized conventional optical monitor. No IBM API is needed to finish the present inference study; a QPU would simulate this model rather than supply missing optical measurements.

A justified next simulation would change the declared acquisition budget or operating point and test a nuisance-aware model on new calibration and holdout records, including decreased drive and calibrated conventional monitoring. It should preserve the present failure rather than tune it away. The current result limits this operating regime; it does not rule out every emitter, interrogation strategy or optical sensor.
