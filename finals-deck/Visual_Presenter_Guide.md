# Finals presenter guide

Use the Visual deck for the main talk. Slides 1–13 form the timed presentation; slides 14–35 are for Q&A. The planned finish is **9:20**, including the **45-second original QRSM application demo**, leaving 40 seconds before the 10-minute limit. Timing is a rehearsal plan, not a measured delivery time.

The thirteen speaking scripts contain approximately 1,224 words. Rehearse aloud with the actual handoffs, application switch and projector. The first nine slides explain the original quantum model and computation. Keep the science language below; shorten examples before removing material limitations.

## Before presenting

- Open the PPTX in the presentation machine’s slideshow software and test the display. The PDF is a static, image-based fallback and does not contain speaker notes.
- Open `laser-diagnostics-app/index.html` locally and select **Focus view**. Leave the original QRSM chapter visible with the selected event at step 3. The application requires no network.
- Keep `animations/laser-diagnostic-lenses.mp4` and `animations/rewind-amplify.mp4` available. These are silent explanatory videos, not recordings of a laboratory or quantum processor. The app evidence chapter has playback controls.
- Agree on speaker handoffs. The team roles on slide 13 reproduce the original README and were confirmed by the user. Suggested handoffs below are a rehearsal plan.
- Stop at slide 13. If switching to the application fails, use the screenshot on slide 9 and the conditional prediction chart on slide 5.

## Timing

| Slide | Time | Purpose |
|---:|---|---|
| 1 | 0:00–0:15 | Rewind & Amplify |
| 2 | 0:15–1:00 | Hidden defects can change the state before readout |
| 3 | 1:00–1:35 | A click is one recorded measurement outcome |
| 4 | 1:35–2:35 | The QRSM connects each bit to a hidden-state model |
| 5 | 2:35–3:20 | Hidden memory changes what follows a click |
| 6 | 3:20–4:05 | Rare conditions waste ordinary samples |
| 7 | 4:05–5:00 | A reversible model makes amplification possible |
| 8 | 5:00–6:00 | Fewer gates, more matching answers |
| 9 | 6:00–6:45 | The query returns a prediction about the next clicks |
| 10 | 6:45–7:25 | Quantum-dot source quality and the QRSM |
| 11 | 7:25–8:10 | The classical reference leads with unknown onset |
| 12 | 8:10–8:50 | The evidence changes our next experiment |
| 13 | 8:50–9:20 | Our contribution and what we learned |

## Forty-five-second original-model demo

| Elapsed | Action | Explanation |
|---|---|---|
| 0–8 s | Point to the QRSM explanation | The model updates its hidden quantum-state estimate from the observed record. |
| 8–15 s | Show selected click at step 3 | The condition accepts any earlier history, not only the illustrative 0010 record. |
| 15–27 s | Change plain sampling to Steering + full | Acceptance increases, while the exact future prediction remains unchanged. |
| 27–38 s | Switch coupled memory to Emitter only | The known model alternatives predict different outcomes after the selected click. |
| 38–45 s | Explain the boundary and return to slides | Real diagnosis needs many records and calibrated competing models. More matching samples must preserve the answer. |

The two-bin cavity query is a separate optical extension available for questions. Do not present its 0.173% to 1.547% result as the original QRSM experiment. The app’s **Current research** chapter contains the frequency, drive, phase, circuit-cost and quantum-dot results. **Earlier sensor study** preserves the separate known-midpoint benchmark; its 86% atomic-fusion result is not the new unknown-onset result.

## Slide 1: Rewind & Amplify

**0:00–0:15**

We are Qubits from Florida Gulf Coast University. We model how hidden defects change quantum measurement patterns, then test a method for querying that model on IBM hardware. Laser diagnosis is a separate research extension.

**Stage cue:** Nicholas introduces the problem. First nine slides cover the original quantum computation.

## Slide 2: Hidden defects can change the state before readout

**0:15–1:00**

Why analyze defects? A hidden two-level system can exchange energy with a qubit or shift its frequency. Then the state evolves differently from the ideal circuit. We infer quantum behavior from repeated preparations and measurements. One readout does not reveal an arbitrary full quantum state. If our analysis ignores hidden dynamics or detector errors, we can assign the wrong cause to the observed statistics. Defect analysis can inform calibration, operating frequencies and device selection, helping preserve useful computation and interpret state estimates. Our project tests a modeling approach to that analysis. It has not diagnosed an unknown physical defect or performed complete state tomography.

**Stage cue:** Nicholas distinguishes physical state evolution from inference about that state. The QRSM models possible causes of the record.

## Slide 3: A click is one recorded measurement outcome

**1:00–1:35**

A click means the model output reads one in a time step. Zero means no click. This example reads zero, zero, one, zero: a click at step three. Our query selects that step alone and allows any earlier history. Optically, the bit represents a detector firing. On IBM, a superconducting qubit represents that output. The emitter and hidden qubit carry memory to the next step. This repeating model is a quantum recurrent state machine, or QRSM.

**Stage cue:** Trace the four columns left to right. Say “a recorded one,” before using “click” again.

## Slide 4: The QRSM connects each bit to a hidden-state model

**1:35–2:35**

The QRSM connects each observation to a physical hidden-state model. Each bit conditions the emitter and possible defect state, contributes to the record likelihood, and changes the next prediction. Across records, classical fitting compares coupling and noise settings. A fresh synthetic test shows why this matters. Ignoring detector dead time pushed inferred coupling from a true 0.65 to 0.069. Modeling the blind detector bin moved it to 0.706 and improved prediction on unused records. Other parameters stayed biased. A detector error can otherwise receive a false physical explanation. Classical hidden-state models also capture history, so the quantum structure must earn its value. Our IBM experiment uses a prepared zero state and known model settings. Grover then queries that model; it does not identify an arbitrary unknown state.

**Stage cue:** Nicholas explains the QRSM itself before any acceleration claim. Distinguish updating the state within a model from estimating the model parameters across many records.

## Slide 5: Hidden memory changes what follows a click

**2:35–3:20**

This is the useful prediction. Given a click at step three, how likely is another later? Without a hidden defect, the click resets the modeled emitter. A coupled hidden qubit retains memory and changes what follows. At step six, these models predict about ten percent and five percent. History gives a richer test than an overall count. A new IBM follow-up separates the programmed alternatives in one circuit, but keeps substantial bias. Other implementations reverse the contrast. The exact curves explain what the query should return. More accepted shots must also preserve that answer.

**Stage cue:** The audience should understand the two curves before hearing how Grover obtains the samples.

## Slide 6: Rare conditions waste ordinary samples

**3:20–4:05**

The selected click occurs in 3.95 percent of ideal runs. Ordinary rejection needs about 25 runs for one match, with cost growing as one over its probability. Amplitude amplification reduces coherent model calls to order one over the square root of that probability. That is the quantum rationale, not a wall-clock speedup. Our strongest classical baseline directly samples conditional answers without rejection and wins at this small size. The possible future opportunity is a hidden quantum memory that becomes expensive to represent classically, provided the reversible quantum circuit stays accurate. That crossover remains unproven.

**Stage cue:** Dan explains the fair classical comparison and why this remains quantum-computing research.

## Slide 7: A reversible model makes amplification possible

**4:05–5:00**

Grover must run the model backward, but a reset discards information. We replace each reset with a fresh output qubit and defer measurement. A prepares the histories. The oracle marks the selected condition. A dagger reverses the preparation. A reflection followed by preparation changes interference so matching histories become more likely. We then reduce hardware cost. Steering is classical tuning of a supported event. Local reflection checks fewer qubits but introduces approximation. We verify both event rate and conditional accuracy. Qiskit builds the circuits, Aer checks the exact model, and compiled circuits run on IBM. Amplification is established. Our contribution is this recurrent-model construction and its tested adaptations.

**Stage cue:** Dan explains A and A dagger. Nicholas explains the implementation changes and verification. Technical model circuit is in backup.

## Slide 8: Fewer gates, more matching answers

**5:00–6:00**

We repeated the comparison on IBM Marrakesh with a common initial qubit mapping. In this fresh follow-up, local reflection returned 76.90 percent matching shots, versus 69.26 percent for full reflection. It used 58 rather than 125 native two-qubit gates. The gain is 7.64 percentage points, with a shot-based interval from 6.29 to 8.99. Shorter circuits use fewer scarce operations per accepted answer here. Conditional error is also lower: 0.118 versus 0.181, where zero is ideal. This still leaves bias. Routing and circuit widths differ, and the follow-up was selected after the first run. Suppression did not improve the earlier comparison. Reliable qubits and accurate circuits matter together. We claim this bounded cost-and-quality result, not dollar savings or a classical speedup.

**Stage cue:** Dillon identifies this as the new precision follow-up. Separate raw quality, event yield and native operations. Backup 14 preserves first run, suppression and historical context.

## Slide 9: The query returns a prediction about the next clicks

**6:00–6:45**

In the app, we select a click at step three. Switching from plain sampling to full amplification raises acceptance while preserving the predicted future probabilities. Now switch the hidden-memory model to an emitter alone. The step-six probability changes from about five percent to ten percent. That is the answer we wanted: how a candidate hidden interaction changes later observations. These are saved, verified model calculations. The separate IBM data measure circuits representing those models. Neither is a live laser measurement, and amplification does not increase photons from a real source.

**Stage cue:** Timofey demonstrates for 45 seconds: 0–8 explain the QRSM role, 8–15 define the selected click, 15–27 choose Steering + full, 27–38 switch to Emitter only, 38–45 explain the diagnosis boundary and return to slides. Pre-open Focus view and the original QRSM chapter. Do not troubleshoot during the talk.

## Slide 10: Quantum-dot source quality and the QRSM

**6:45–7:25**

Quantum dots connect our question to semiconductor photon sources. Photonic operations rely on predictable interference, which equal brightness cannot guarantee. Engineers need to qualify and tune sources for photonic chips. We now implement a joint-photon observation model: the hidden environment changes emitted modes, and each pair outcome updates its conditional state. Classical calculations verify it, and IBM circuits test its digital representation. The first small-data test barely distinguishes the hypotheses. More controlled data helps, but calibration errors can imitate the signal. No real dot is fitted. Next is our separate frequency-monitoring study.

**Stage cue:** Nicholas explains the implemented observation model and its limits. Keep the engineering task concrete: source qualification and tuning. Backups 30–33 show why correlations, calibration and acquisition budget matter. Transition to the distinct atomic-frequency benchmark on 11.

## Slide 11: The classical reference leads with unknown onset

**7:25–8:10**

The test hides when frequency changes and holds out simulated sessions. Can the monitor respond within 32 seconds? The conventional receiver detects 51.35 percent. Adding the atomic channel reaches 58.02 percent, a 6.67 point gain. A second independent conventional reference reaches 97.97 percent. False alarms below refer to the entire 128 second record, not each instant. We include missed events in the delay calculation. Degraded atomic coherence can reverse the benefit, and shared-path drift still mimics the source. These controls sharpen our conclusion: an atomic reference can add information in this model, but the conventional addition performs best. Apparatus resources are not fully matched.

**Stage cue:** Dillon explains the unknown onset and 32 second horizon before the percentages. Do not quote the earlier 86% known-time result here.

## Slide 12: The evidence changes our next experiment

**8:10–8:50**

In simulation, a 20 percent drive step gives only 3.71 percent detections within 32 bins and 6.84 percent false alarms per 96-bin stable record. Most amplitude-estimation gain comes from its prior, so this regime needs redesign. A separate phase simulation is promising: a charged hybrid reduces error from 0.00791 to 0.00637 radians at matched incident photons and ideal preparation. Loss and preparation time matter. Next, test a calibrated optical target with an independent reference. Computing also needs accurate answers at competitive total cost. Neither path has demonstrated a wafer benefit.

**Stage cue:** Nicholas states the negative amplitude result and the conditional phase opportunity. Save prior-control and ambiguity details for backups 25–26.

## Slide 13: Our contribution and what we learned

**8:50–9:20**

Our contribution is a queryable recurrent quantum model with fresh hardware tests and a joint-photon observation extension. Controls changed our conclusions: accuracy and cost both matter. Our documented team roles are here. The QRSM predates the event, and amplification is established. We used Claude originally and Codex with OpenAI models for the extensions. These results show what the computing method achieves and what optical experiments still need to test. Thank you.

**Stage cue:** Nicholas closes. Slides 14 onward are Q&A only. The planned 9: 20 finish leaves 40 seconds for handoffs or pauses. Rehearse to confirm the actual time.

## Numbers to defend in Q&A

- **What QRSM adds:** a physical hidden-state model that conditions its emitter/defect state on each observed bit, scores the record likelihood, and predicts later observations. Parameter fitting is classical. Classical hidden-state models also capture history, so physical structure must earn its value in comparisons.
- **Why defects matter for measurement:** hidden interactions can change state evolution before readout. Preparation and detector errors can also change counts. A validated dynamics/measurement model helps avoid misattributing those causes. This is not a shortcut to complete tomography or unique defect identification.
- **Fresh fitting evidence:** true synthetic coupling 0.65 was fitted as 0.069 when detector dead time was ignored and 0.706 when the blind-bin dynamics were modeled. The corrected model improves held-out likelihood, but other parameters remain biased or at a bound. Its advantage over a trained HMM is unresolved. This is synthetic inference, not discovery of a physical defect.
- **Click definition:** a measurement of 1 on the modeled output qubit in one dimensionless time step. Its optical interpretation is a detector event. IBM superconducting readout represents that role; the experiment did not detect optical photons.
- **Useful answer:** given step 3 = 1, the exact step-6 click probabilities are 4.6675% with the specified hidden defect and 10.1024% without it. These are known model alternatives, not an unknown physical defect discovered by the method.
- **Current QPU result:** the fresh precision follow-up gives 6,300/8,192 raw matches (76.904%) for local reflection versus 5,674/8,192 (69.263%) for full reflection, with the same steering, one round and common initial map prefix. Native CZ counts are 58 versus 125, and raw conditional-history TV is 0.1177 versus 0.1814. Routing, width and measurement context still differ. The 7.642-point acceptance difference has a marginal independent-shot interval [6.287, 8.993], excluding drift and calibration uncertainty. The follow-up was chosen after the first run. Do not pool it with the first 2,048-shot comparison or the older Kingston 86.06/78.49% result.
- **Continued query:** the new local-loop step-six rates are 8.794% with the programmed defect and 11.661% without, versus exact 4.667% and 10.102%. The difference has the intended sign and a shot interval excluding zero, but substantial bias remains. Plain, steered full and memory-only implementations reverse the contrast. This is not reliable diagnosis of an unknown physical defect.
- **Campaign breadth:** 10 completed IBM Marrakesh jobs, 207 science circuit executions plus 40 calibration circuits, 688,640 shots and 244 charged QPU seconds. Executions include repeats. Optical-source and atomic channels are digital emulations; the campaign did not operate an optical sensor or expose a wafer. Every job retains raw counts, physical measurement mapping and submitted ISA circuits.
- **Current sensor task:** a randomly signed 0.5 Hz source step with hidden onset between 48 and 96 seconds in a 128-second synthetic record. Detection must occur within 32 seconds; prealarms and misses are penalized. Full-record false alarms and timely detection have different denominators and meanings. This is not industrial pulse monitoring.

| Method | Detection within 32 s | 95% hierarchical interval | False alarms per 128 s record | Restricted delay |
|---|---:|---:|---:|---:|
| Conventional C | 51.35% | 44.48–57.92% | 5.42% | 22.14 s |
| C + atomic Q | 58.02% | 51.25–64.53% | 5.16% | 20.78 s |
| C + independent C | 97.97% | 96.72–98.96% | 4.06% | 9.06 s |

The paired atomic-addition gain is 6.67 percentage points, with hierarchical 95% interval 3.96–9.38. Eight independently calibrated pipelines and 96 held-out sessions support the resampling structure. There are 1,920 null and 1,920 source records per scenario. Intervals quantify finite simulation variation, not physical model error or universal calibration coverage. Restricted delay assigns the 32-second horizon to misses and prealarms.

A second conventional reference remains the stronger comparator. The simulator matches acquisition duration and task, with assumed source-photon allocation. It does not match total apparatus costs or establish quantum advantage. The atomic support optics and reference lasers require additional accounting.

- **New sensor failures:** C + Q false source alarms rise to 84.53% for a primary-reference step and 94.11% for a shared-path step. The older atomic-drift 80.10% result belongs to the earlier known-time experiment and must not be mixed with this study.
- **Drive-amplitude test:** a +20% field step yields 3.71% detections within 32 bins, alongside 6.84% stable-record false alarms over 96 bins. Its prior-only estimate already achieves RMSE 0.1136; observations improve that to just 0.1125 for this case and worsen the other four source-changing cases. The prior control was added after holdout inspection and is descriptive.
- **Phase opportunity:** at 20,000 mean photons incident before the object, 81% overall efficiency and ideal preparation, a charged 10% coherent / 90% NOON hybrid has full-phase RMSE 0.00637 rad versus 0.00791 rad for the declared coherent protocol. Both sample modes are charged. Pure NOON has a global π ambiguity. Loss and preparation time limit the benefit; this is not a claim against every classical design.
- **Circuit-cost result:** a complete 49-cell spatial query was constructed as two 389-qubit circuits with 2.87–3.38 million constructive generic CX upper bounds. Both QPY files round-trip. These are unoptimized bounds, not routed counts or 389-qubit statevector results. The original independent-cell probability is tractable classically.
- **Exposure result:** an assumed two-photon resist shows stronger NOON contrast, but its best tested pattern accuracy requires more dose. Loss, blur and linear background erase benefits in several cases. No measured material, printed feature, chip yield or dollar saving is established.
- **Dot lesson and engineering decision:** photonic operations rely on predictable interference. Equal counts and ideal multiphoton suppression do not ensure matching photons. In the pair-memory example, the same one-photon frequency distribution gives overlap 1.0 for shared offsets and 0.6 for independent offsets. This is classical environmental memory, not proof of a coherent hidden qubit. Engineers qualifying or tuning photon sources should measure interference alongside loss and check controls before assigning a cause. Lowering per-photon survival from 80% to 20% requires 16 times as many attempts per surviving pair.
- **Bridge back to QRSM:** a new retained-environment dot surrogate now implements the joint two-photon observation model and conditional state update. It embeds complex emitted-wavepacket overlaps and uses symmetry readout equivalent to balanced HOM. Independent bosonic calculations verify the observation maps. IBM circuits test the bounded digital representation. The original and new source dynamics are distinct, no real dot QRSM is fitted, and a physical calibration remains necessary. Grover cannot recover information that a detector never recorded.
- **Dot inference and controls:** 64 attempted pairs barely distinguish the specified hypotheses: 5.60% coherent flags versus 4.50% classical false flags. A separately selected control and ideal resets between four-pair blocks reach 79.75% versus 4.85% at 2,584 attempted pairs. Preserve the full six-budget curve. At 7,644 pairs, changed collection, overlap and readout produce 72%, 53.25% and 21.05% false flags. An 8-state HMM predicts as well within uncertainty; all 20 fit starts reach their iteration cap. This establishes conditional model information, not quantum-memory certification or source diagnosis.
- **Deep-query failure:** the two-bin all-click circuit returns 8/512 events, close to its 1.5466% ideal rate, while selected-data TV is 0.7604. Zero hits in the three-bin circuits alone are inconclusive at 512 shots, but their data marginals remain biased. The 1,024-entry nonsemantic cost circuit uses 98,680 native CZ gates and returns 46.58% marked outcomes versus 99.23% ideal. Acceptance must be checked alongside the answer distribution.
- **External GaAs measurements:** our separate peak-area reanalysis gives corrected HOM visibilities 0.8024, 0.8258 and 0.7724 at excitation separations 13.1, 26.2 and 39.4 ns. Conditional 95% intervals are [0.7943, 0.8113], [0.8181, 0.8344] and [0.7647, 0.7808]. These condition on counting/calibration assumptions and exclude normalization and other systematics. The co-only diagnostic gives 0.7938 for the last pair. The team did not collect these data, reproduce an exactly specified author pipeline or identify a microscopic defect.

## Backup slides

### 14. Hardware repeats and noise controls

The three current runs remain separate. Suppression used dynamical decoupling and twirling; it did not improve this pair in the observed run. The larger-shot follow-up was chosen after inspecting the first campaign and must not be described as a preselected independent confirmation of all hypotheses. Its 7.64 point yield difference has an independent-shot interval 6.29 to 8.99 points, excluding drift and calibration uncertainty. First-run ablations also include plain 6.74 percent, steering-only 24.07 percent and unsteered full three-round 48.73 percent. Conditional accuracy differs strongly. Earlier Kingston results 86.06/78.49 percent and 40/85 gates remain historical, with different layouts. None are pooled or interpreted as a universal noise advantage.

**Sources:** hardware_campaign/runs/original_plain_v2/analysis.json, original_suppressed_v1/analysis.json, original_precision_v1/analysis.json and hero_acceptance_contrast.json. All original43rows include the full earlier39circuit suite plus catalog repeats. Archived evidence research-validation/hardware_verification.json. Raw summaries primary; projected independent assignment inversion is a sensitivity analysis without calibration uncertainty.

### 15. Deep optical queries show large distribution errors

Both retained three-bin models pass exact branch and conditional-state checks before hardware. Native routing raises these queries to 26,749 and 54,998 CZ gates. Each returns zero selected shots out of 512. That alone is inconclusive: even ideal expected counts are below one. The measured data marginals have substantial total-variation error, while full data-plus-environment distributions deviate still more. The one-bin circuits can instead produce inflated acceptance with wrong conditional distributions. Better mathematical truncation therefore does not guarantee a more useful hardware answer. Classical recursion already solves these small models efficiently. Cavity-two is a deliberately truncated physical surrogate, and Z statistics do not establish full conditional-state fidelity.

**Sources:** hardware_campaign/runs/optical_dilation_plain_v2/analysis.json and raw.json, rows optical_3bin_0p03_all_r1 and optical_3bin_0p003_all_r1. Raw0/512, Wilson upper.7447%, versus ideal.127833/.127551%. DataZTV.436846/.384204. Underlying genericCX10,189/19,864 from multibin_followup/main/ideal_0p03.json and ideal_0p003.json. State approximation error versus cavity2 .02604/.01094 before hardware is a different quantity.

### 16. Sensor assumptions and resource accounting

The atomic response follows finite driven Bloch rotations with T1/T2 damping, preparation error, asymmetric readout error and binomial projection noise. Optical intensity changes the Rabi frequency and induces an assumed light shift during pulses. Conventional receivers include source-photon shot noise, electronics and reference drift. All methods see the same underlying source task and duration. The photon allocation is a declared assumption: atomic coupling and beam geometry are not specified from a real apparatus, and reference lasers plus atomic support optics are not included in a full cost comparison. Therefore this is not a resource-matched quantum advantage test.

**Sources:** laser_sensor_viability/results.json config and resource_ledger supply the unchanged physical model. New task: followup/README.md, protocol.json and main/results.json. Unknown source onset48–96s, eight independently trained/calibrated pipelines, held-out sessions. Whole-record alarm calibration, misses and prealarms charged32sin restricted delay. Bishof etal., PRL111093604, https://arxiv.org/abs/1303.6741 is physical precedent, not chosen device specifications.

### 17. Calibration failures can reverse the conclusion

These are the new unknown-onset results. Each cell gives timely detection followed by full-record false alarms. The target is source-frequency change, so a sensor/reference/path change can trigger a false source diagnosis. Shorter atomic coherence makes the fused channel worse than C alone. A separate agreement veto reduces the primary-reference failure but sacrifices sensitivity and still exceeds the nominal alarm target. Shared-path drift is structurally indistinguishable from source motion in this measurement model. Hierarchical pipeline/session intervals quantify finite simulation variation, not physical model error or calibrated universal coverage. None of the older known-midpoint rates belong in this table.

**Sources:** laser_sensor_viability/followup/main/results.json and README.md. New primary-reference CQFAR84.53%, common-path94.11%. Agreement rule15.57% and68.23%, respectively. Nominal CQgain6.67pp, shortcoherence−5.42pp. Eight pipelines and96test sessions per scenario.

### 18. Detector dead time can distort inferred coupling

After a click, the next recorded bit is forced to zero while the underlying system evolves unconditionally. Ignoring that readout process misattributes detector correlation to the hidden interaction. Including it improves held-out log likelihood by 0.4584 nats per 24-bin record, with paired conditional 95% interval 0.3978–0.5210. The fitted coupling moves closer to the known synthetic value, but dephasing reaches its upper bound and efficiency remains biased. A trained HMM captures the detector correlation too: the corrected physical model’s advantage over it is unresolved. Other physical parameters and the family remain known. This fresh result replaces the earlier truth-informed candidate-count example in the current deck.

**Sources:** qrsm_photon_poc/followup/README.md, inference_results/fixed_411101_dead1_fit0.json, fixed_411101_dead1_fit1.json, parameter_validation_v2/ and independent_review.json. The HMM difference interval for the corrected model is−.0067to+.0222nats/record.

### 19. Where the quantum component enters

A sensor can use quantum dynamics while a classical computer processes its readouts. We now compile the finite driven atomic channel, including dissipation, into an IBM digital circuit. That tests a bounded implementation on superconducting hardware, not an atom, physical optical coupling or a 128 second acquisition. Unknown-onset detection still runs as classical inference on synthetic records. The separate recurrent-model query uses coherent preparation and amplitude amplification. Connecting a calibrated full acquisition process to a competitive quantum algorithm remains further work. No end-to-end quantum advantage follows from executing a component.

**Sources:** hardware_campaign/optical_controls/README.md, models.py and hardware_integration_review.json. Canonical laser_sensor_viability/model.py. Independent Bloch versus Lindblad/Stinespring checks. LASER_DIAGNOSTICS_ROADMAP.md and hardware_campaign/coverage.json distinguish component, classical and physical requirements.

### 20. The transfer to lithography needs its own test

The distinction matters. A CO2 drive laser heats tin to create plasma, which emits EUV. Monitoring the drive is different from measuring EUV. A narrow-line 698 nm atomic benchmark does not automatically transfer to either of those signals or to a 193 nm broadband pulsed excimer source. Existing conventional monitoring measures relevant source quantities. Cymer and imec reported controlled wafer experiments correlating light-source changes with critical-dimension behavior. That motivates source metrology, not a quantitative yield claim for our sensor. Atomic laser-noise metrology is also established prior work, including Bishof and colleagues in 2013.

**Sources:** ASML: https://www.asml.com/en/technology/lithography-principles/light-and-lasers and https://www.asml.com/en/products/euv-lithography-systems. Cymer/imec2014: https://www.cymer.com/wp-content/uploads/2018/12/Cymer_SPIE_AdvancedLithography_2014.pdf. Bishof etal.: https://arxiv.org/abs/1303.6741.

### 21. The continued query separates models with bias

The selected precision follow-up uses 8192 shots per circuit. Its steered local implementation gives step-six rates 8.794 percent with the programmed defect and 11.661 percent without it. The raw contrast has the intended sign and a shot-based interval excluding zero. Both rates remain biased relative to 4.667 and 10.102 percent exact targets. Crucially, plain, steered full and memory-only implementations reverse the expected sign. The initial campaign also failed to resolve the small local contrast at its lower precision. We preserve these results rather than calling this reliable diagnosis. The effect distinguishes particular programmed circuits under particular conditions; it does not locate unknown defects in the IBM processor or a laser.

**Sources:** hardware_campaign/runs/original_precision_v1/loop_contrasts.json and analysis.json. Local step6counts538/6118 versus834/7152 accepted histories. Contrast−.0286735, independent-shot Wilson-based95%interval[−.0389321,−.0183558]. Intervals exclude drift, readout-calibration and model uncertainty. Original ideal target research-validation/original_after_click_verification.json. Earlier archived continued jobs remain separate historical evidence.

### 22. One step of the recurrent quantum model

The emitter rotates under a drive. A hidden qubit rotates under its detuning and exchanges excitation with the emitter. The emitter then exchanges with a fresh output qubit. The dynamic implementation measures and resets that output each step. The purified implementation retains it, so the environment and history required for reversal remain in the circuit. This trades extra qubits for reversibility. Model steps are dimensionless. The optical labels describe a model interpretation. These IBM circuits did not measure photon arrivals.

**Sources:** Original fig_circuit_hybrid.png, qrsm_grover/model.py and tests. QRSM defaults theta=.6,gamma=.2,phi=(.45,),zeta=(.3,).

### 23. Judging rubric and evidence map

This map follows the supplied Qiskit Fall Fest judging rubric. Exceptional performance asks for a specific stakeholder and realistic impact, a defensible quantum rationale that considers classical alternatives and hardware scale, reproducible Qiskit implementation, rigorous comparisons, a clear contribution relative to reused ideas, accessible delivery within the time limit, and shared understanding. The hardware bonus is a separate highest-tier item, not an additive sum of all tier values. We do not predict a judge score.

**Sources:** User-supplied Qiskit_Fall_Fest_Judging_Rubric.xlsx, extracted by root. FINALS_RUBRIC.md.

### 24. Contribution, prior work and AI assistance

The original README documents the team research timeline and Claude assistance. The team set the original direction and questions and reviewed the work. This finals revision uses Codex and OpenAI models to assist research review, reproduction, simulations, tests, application and presentation. Do not imply that every generated analysis has already received manual team verification. Amplitude amplification and Bayesian quantum inference are prior art. Atomic laser-noise spectroscopy is also prior art. The separate optical and sensing extensions test scoped feasibility questions and do not establish an end-to-end quantum computing advantage.

**Sources:** Original README PriorworkandAIhelp and Team. Brassardetal https://arxiv.org/abs/quant-ph/0005055. Lowetal https://arxiv.org/abs/1402.7359. Bishofetal https://arxiv.org/abs/1303.6741.

### 25. Drive amplitude: a useful negative result

The field-amplitude proxy is the drive parameter, not an incident-photon flux. A 20 percent field step would correspond to 44 percent intensity under fixed coupling. This low-count regime yields poor timely detection alongside substantial full-record false alarms. The physical filter, fitted HMM and count detector share the same bits; these are not independent engineered optical receivers. The post-holdout prior-only control exposes a weak constant-estimate comparison: for this step, using observations only slightly improves the prior estimate, and for the four other source-changing cases it makes estimation worse. Afterpulsing produces 10.55 percent false source alarms. The model needs a better operating regime and calibrated detector dynamics before a practical monitor claim.

**Sources:** qrsm_photon_poc/drive_diagnostics_followup/README.md; main/results.json, prior_only_estimation_control.json, independent_review.json, prior_only_independent_review.json. Four separately calibrated pipelines,13cases,128records per pipeline/case,96bins/cavity4. Stable FAR35/512 and step timely19/512 for physical QRSM. Prior-only MSE minus observed-data MSE .00025149, paired interval [.00007878,.00044596] for this step, a small conditional effect. Prior supplement is post-holdout descriptive, not another confirmatory test.

### 26. Phase inspection: benefit depends on the budget

A doubled fringe has a pi ambiguity. Pure NOON performs well locally around a shared calibrated working point, but fails to identify the full phase globally. A charged coherent pilot resolves that ambiguity in the tested hybrid. Both sample modes illuminate the object; the resource is 20,000 mean photons before object transmission, including reference-arm photons. The high-efficiency case has 90 percent object transmission and 90 percent detection, with ideal preparation. Lower transmission removes the precision benefit. At one-percent preparation, matching dose requires 100 times longer for pure NOON; at fixed clock time its precision is worse. Ideal number-resolving detection, a known phase reference and the declared classical protocol bound this result. It is not superiority over all classical designs or a measured feature-size benefit.

**Sources:** quantum_lithography_poc/phase_inspection_followup/README.md and results.json high_efficiency/equal_sample_photons. Pure NOON modulo-pi RMSE .0062646rad, full2piRMSE2.226739rad. Hybrid.00637086rad, coherent.007908rad,2000outcomes per protocol in each cohort. Zero errors gives95%Wilson upper bound.1917%. Global phases reused across methods; outcomes independently drawn. Separate equal-clock and equal-dose budgets.

### 27. The full spatial query is costly to construct

This is an actual constructed reversible 49-cell oracle, not an extrapolation from three cells. Four count qubits per cell encode a capped Poisson law,23 bits accumulate the weighted score, and 170 extra clean ancillas support explicit reversible gates. Both 389 qubit circuits pass QPY serialization and independent structural, arithmetic and uncomputation checks. The CX values are constructive generic decomposition upper bounds, including preparation and one complete amplification round; they are not a routed device compilation. Rounding and capped-tail bounds bracket the original event, with relative bracket width 0.2406 percent at dose 1.5 and 0.3526 percent at dose 1.8. Classical dynamic programming already solves this independent-cell distribution efficiently. Construction alone establishes neither computational advantage nor physical lithography feasibility.

**Sources:** finals-lithography/full_spatial_circuit/README.md, results.json, process_bounds.py, independent_review.json. Floor and ceiling clean circuits389qubits; CX bounds3,382,108/2,874,028 and U5,050,537/4,288,741. Dose1.5 original event bracket [.004226948015,.004237128599]; conservative conditionalTVbound.00482. Cap15 value change usesPoisson tailN>=16, encoded cap probabilityusesN>=15. Check row direction against event interval: floor weights admit an upper event; ceiling weights give a lower event.

### 28. Exposure: contrast trades against dose and loss

The response combines declared linear and two-photon activation coefficients, loss, phase jitter, finite pixel collection and post-activation blur. Activations are rare Poisson events, not direct photon probabilities. The NOON pattern has stronger mean contrast and higher best guard-cell accuracy under the nominal assumptions, but requires more incident photons at its best tested dose. The duty-cycle comparator concentrates equal average photons into ten-percent active time, giving higher peak intensity. It is one explicit classical competitor, not an optimum over all illumination. Loss, blur, linear leakage, background and low preparation success degrade the result. The 20 guard cells exclude boundary cells. This is a sensitivity study of an assumed resist, not a prediction for an available material or fabricated feature.

**Sources:** quantum_lithography_poc/exposure_followup/README.md and results.json finite_nominal. Table optimizes each method over tested doses, so it is not a single equal-dose operating point. G1/G2 supplement verifies spatial conservation and harmonic/per-photon accounting. 540,000Poisson realizations. Wavelength800nm, ±30degree modes, second harmonic400nm; period is not linewidth. Independent or fast phase jitter/mean-rate approximation excludes slow correlated phase drift.

### 29. Model accuracy is part of the resource budget

The original optical circuit uses only two cavity levels. Comparing its conditional predictions with a six-level reference reveals errors of several percentage points, especially under stronger drive. Increasing the cutoff reduces the discrepancy in these cases, but raises state and circuit costs. Six fresh joint-inference cases fit five parameters with source and detector controls. Fixed settings do not resolve performance versus an HMM; controlled settings give small held-out gains under shared known physics. Fixed-drive detuning sign remains structurally ambiguous. Controlled settings break that exact symmetry but do not establish reliable finite-data sign identification. Local curvature intervals fail near boundaries and are not global uncertainty guarantees. Thermal, multimode and non-Markovian effects remain future model families.

**Sources:** qrsm_photon_poc/followup/README.md, dynamics_results.json, inference_results/, parameter_validation_v2/ and independent_review.json. Max after-click error over tested later lags versus cavity dimension6. Master equation independently checked with QuTiP; trajectory statistics tested separately. Controlled model-HMM logscore gains .0574[.0158,.1014] and .0972[.0448,.1495]nats/24-binrecord under conditional bootstrap. This does not establish physical defect identification or a quantum computational speedup.

### 30. Equal photon counts can hide poor interference

Each photon separately has the same brightness and fifty-fifty frequency distribution. Shared versus independent offsets still change pair overlap from one to 0.6. A single-photon marginal misses information in the joint observation. This benchmark environment is entirely classical, and an HMM is a necessary competitor. The new sequential HOM instrument implements the broader hidden-state question using a different complete-emission source model. Its digital circuits also test these frozen pair controls. It does not turn this classical memory example into a coherent-defect witness. An engineer can use the distinction to select interference-sensitive source measurements alongside collection cost. At 80 percent survival, a pair takes 1.5625 attempts on average; at 20 percent, it takes 25. These are surviving pairs, not necessarily resolved coincidences.

**Sources:** quantum_dot_bridge/results.json classical_trap_pair_comparison endpoints p_switch=0 and.5, PROTOCOL.md and independent_review.json. Both marginals are(.5,.5), ideal g2(0)=0 and eta=.2. M1/.6 gives coincidence per attempted excitation pair0/.008 at a balanced beamsplitter. The classical state remains fixed within each wavepacket; the pair model does not infer a switching time. Other benchmark cases retain counts while giving overlap1/.5/.2/.25 from pure dephasing or detuning. Sixteen tests and independent density-kernel quadrature support the calculations. External GaAs histograms are separate and did not calibrate this illustrative model. No semiconductor defect, physical device setting, quantum advantage or lithography yield was identified.

### 31. External GaAs data: a conditional reanalysis

The real-data lesson is that a source-quality estimate depends on measurement controls. These are external Hong–Ou–Mandel histograms analyzed classically, not team measurements or a QRSM fit. We normalize central peaks to side peaks and apply published splitter and multiphoton corrections. The intervals exclude polarization, routing and drift systematics. At 39.4 nanoseconds, co-only normalization changes the estimate from 0.7724 to 0.7938. That discrepancy guides checks of polarization, alignment and normalization before assigning a cause. The new joint-photon instrument supplies a mathematical candidate model, but these aggregate histograms lack the sequential records and source calibration needed to fit and test it. Repeated time-tagged acquisitions and held-out comparisons remain necessary. No microscopic cause, monotonic decay, reproduced author pipeline or improved device performance follows.

**Sources:** quantum_dot_bridge/hom_analysis/results.json, PROTOCOL.md and independent review. Dataset https://doi.org/10.5281/zenodo.6337697, CC BY4.0, by Julian Munzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil. Paper https://arxiv.org/html/2203.08682v1 SectionIV Eqs3–4. Quoted paper V=.803(.005),.826(.004),.774(.004) remain separate. Our primary extraction uses half-open windows of half-width2ns, no background subtraction, reference cycle indices−2,−1,+1,+2 and200000Monte Carlo draws. R=.514±.007,g2=.016±.001, assumed independent but shared across separations. Data hashes verified against reference_hom/provenance_manifest.json. These aggregate histograms cannot provide original QRSM binary histories or uniquely identify charge traps.

### 32. The joint-photon QRSM observation model

The missing observation model is now implemented. A fully excited emitter decays into a photon whose exponential temporal mode depends on the environmental state. Complex Gram overlaps embed the finite mode family exactly. A controlled-SWAP parity measurement equals the balanced-HOM symmetry statistic, and tracing the photon modes produces a conditional environmental map. Independent bosonic calculations check probabilities and conditional coherences. The environment persists between pairs. Passive outcomes cannot separate these hypotheses. A calibrated shift introduces a small joint effect, but the 64 pair simulated study gives only 5.60 percent coherent flags versus 4.50 percent classical false flags. The separate selected four-pair IBM circuits use 22/29 qubits and 256/334 native CZ gates. Their raw flag distributions have TV.249/.286, so implementation noise remains substantial. They do not validate the optical assumptions or certify quantum memory.

**Sources:** quantum_dot_bridge/qrsm_hom_followup/README.md, physical_model.py, circuits.py, main/results.json and main/independent_review.json. Thirty thousand synthetic records replayed independently. Hardware current summary family_results.dot_selected_four_pair, selected_four_coherent and selected_four_classical,4096shots each. Distinct chosenθ3π/4,+2Γfour-pair control. Zconditional memory is not fullstate tomography. Main14circuit bundle uses earlierθπ/3. New source assumes full emission, fixed environment during each packet and controlled gaps. Original QRSM excitation-exchange dynamics are distinct. Measurement precedent Garcia-Escartin and Chamorro-Posada, https://arxiv.org/html/1303.6814v1.

### 33. More data helps only under trusted calibration

After preserving the negative main result, an exact 648 setting scan selected a new control and gap rotation. A separate prospective simulation uses ideal resets between four-pair blocks and independently calibrated thresholds at every budget. At 2584 attempted pairs, nominal flags reach 79.75 percent with 4.85 percent classical false flags. The full budget curve remains visible. This is a different preparation protocol, not a tuned replacement of the 64 pair study. At 7644 pairs, changes in collection, mode overlap or readout give 72,53.25 and 21.05 percent false flags from still-classical sources. The 8 state HMM differs from the calibrated physical predictor by only 0.0000092 nats per pair, with an interval spanning zero. All 20 HMM starts reached the iteration cap. More data cannot repair a wrong measurement model, and no classical impossibility or physical defect follows.

**Sources:** quantum_dot_bridge/qrsm_hom_followup/exploratory_design/README.md, design_results.json, VALIDATION_PROTOCOL.md, validation_run/results.json and independent_review.json. θ3π/4, second-emission shift+2Γ, eta.8, resetI/2 per4pair block. All lost pairs charged,2source excitations per pair. Independent20k training and20k predictive blocks,4/8state HMM10starts/200iterations. Rigorous simple-hypothesis bound1911blocks uses a different exact-model log4 threshold, not the empirical curves. No validated physical control/reset time.

### 34. Atomic and photon channels on IBM

The atomic adapter exponentiates the actual driven Lindblad evolution through finite pulses and free precession, constructs its complete channel and synthesizes a Stinespring isometry. It does not rotate a qubit directly to an analytic output probability. Independent affine-Bloch calculations verify the ideal response. IBM results show the response direction but retain material bias, especially at the outer detunings. Separate photon circuits prepare actual finite mode states, apply phases, recombine and encode loss. A coherent source is represented by its unnormalized Poisson sectors through N8; vacuum and the omitted tail remain charged. Raw occupancy moments include source failures. These are meaningful implementation tests, while acquisition, calibration and apparatus costs remain optical questions.

**Sources:** hardware_campaign/optical_controls/README.md, PROTOCOL.md, models.py, bundle_v2/manifest.json and hardware_integration_review.json. hardware_campaign/runs/optical_controls_plain_v1/analysis.json,33science rows. Atomic originalT1=100s,T2=.2s,2.5ms pulses,20ms dark interval,1% preparation error; physical optical2/4%readout assumptions not added as if hardware correction. Coherent mean2before object, tailN>8=.0002374473, source/detection/object losses declared. Independent compiled mapping and moments audit passed.

### 35. Hardware coverage and circuit limits

Ten completed jobs execute 207 science circuits and 40 calibration circuits, totaling 688640 shots and 244 charged QPU seconds. These are circuit executions including repeats, not 207 independent discoveries. The campaign covers the original suite and meaningful rungs of circuit-ready families. Independent 3/5/7 site contacts compare enumeration and clean counters. The 1024 entry seeded-diagonal stress circuit reaches 98,680 native CZ gates and 46.58 percent raw matches versus 99.23 percent ideal. It is distinct from semantic retrieval. Eight-step rounds and ten-step bounded rewinds test ingredients, not full adaptive BBHT. Four-pair dot circuits use 22/29 qubits and a declared 32 entry flag-memory marginal. The 389 qubit 49 cell construction cannot fit 156 qubits. Classical benchmarks, published optical data and real process calibration remain separate requirements.

**Sources:** hardware_campaign/results.json and RESULTS.md, all10job IDs with immutable plans/raw counts and exact ISAQPY. coverage.json and coverage.md; extensions/bundle_v1/manifest.json and independent_review.json; quantum_dot_bridge/qrsm_hom_followup/exploratory_design/HARDWARE_EXTENSION.md and hardware_bundle/manifest.json. Native counts differ from generic constructions. Z marginal checks are not full-state fidelity. Full49 results in finals-lithography/full_spatial_circuit/results.json.

## Rebuilding

The editable deck is authored by `.finals-deck-build/visual_build.mjs` with the bundled `@oai/artifact-tool` runtime. The root resolves relative to that file. `PRESENTATIONS_SKILL_DIR`, `RUNTIME_PYTHON`, `OUTPUT_PPTX` and `OUTPUT_RECEIPT` can override the authoring environment and output destinations. Link the build directory’s `node_modules` to the installed bundled Node packages. Use `--draft` for previews. Finalization intentionally refuses to overwrite an existing final PPTX or receipt; use new output filenames for a revision.

The build reads the verified original after-click evidence, frozen research results, current hardware campaign summary and its referenced analyses, archived hardware summary, two original circuit figures, optical cover asset and original-core app screenshot. It performs no hardware jobs. The renderer and finish scripts create the checked slide PNGs, static PDF, guide and manifest. Source hashes identify the evidence used. The immediately preceding deck is preserved in `archive/pre_hardware_2026-11-11/`; older decks remain in the other archive folders.
