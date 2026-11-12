# Presenter guide: finals deck V3

**13 main slides, planned 9:20 including a 45-second Lab demo. The limit is 10:00.** The narration below is 1,119 words, about 130 words a minute outside the demo.

Speaker assignments are suggestions: change them to suit the team, and rehearse aloud with a timer.

The same notes are inside the PowerPoint. Slides 14 onward are backups for questions.

| Slide | Time | Speaker | Title |
|---:|---|---|---|
| 1 | 0:00–0:15 | Nicholas | Rewind & Amplify |
| 2 | 0:15–1:00 | Dan | Something is hidden inside the signal. |
| 3 | 1:00–1:50 | Nicholas | A recurrent machine whose memory is quantum. |
| 4 | 1:50–2:35 | Nicholas | One click. Two futures. |
| 5 | 2:35–3:10 | Timofey | The useful runs are the rare ones. |
| 6 | 3:10–4:05 | Timofey | Grover makes rare answers common. Two catches. |
| 7 | 4:05–5:00 | Nicholas | You can’t amplify what you can’t rewind. |
| 8 | 5:00–6:00 | Dillon | On IBM hardware, fewer gates won. |
| 9 | 6:00–6:45 | Dillon | A simple noise model predicts the gap. |
| 10 | 6:45–7:35 | Timofey | The Lab: our model, live in a browser. |
| 11 | 7:35–8:15 | Dan | Three places hidden memory matters. Honestly scored. |
| 12 | 8:15–8:50 | Nicholas | What we claim, and what we don’t. |
| 13 | 8:50–9:20 | All four | What we built, and what we learned. |

## Main talk

### 1. Rewind & Amplify

*0:00–0:15 · Nicholas*

We are Qubits, from Florida Gulf Coast University. A quantum device can hide a defect that changes what it does next. We built a model of that, and a way to ask the model about its rarest events. Then we ran it on IBM hardware.

**Cue.** One breath, then move on. Optional cold open: type 37 and Enter to play the 45-second cinematic cut first, then 2 and Enter. If you use it, drop the video on slide 10 and demo the Lab live instead, or you will run over.

**Sources.** README.md. Cover art from the V2 deck.

### 2. Something is hidden inside the signal.

*0:15–1:00 · Dan*

Picture a tiny light source driven by a laser. A detector records one bit per time step: click, or no click. That record is all anyone sees. But out of sight, a defect can trade energy with the source and quietly change the pattern. Teams building quantum chips have this problem: hidden defects drain their qubits between calibrations. So do engineers who build single-photon sources. And it is easy to get wrong, because a faulty detector can look exactly like a defect. Guess the cause wrong, and you fix the wrong thing.

**Cue.** Point at the hatched box: that is the thing nobody can measure. Say who has the problem before any physics. The picture is our model; on IBM hardware superconducting qubits play these roles.

**Sources.** Physical context: Schlör et al. 2019 (two-level fluctuators and transmon coherence); Keith et al. 2018 (measurement-model uncertainty). Synthetic dead-time example: qrsm_photon_poc/followup/README.md.

### 3. A recurrent machine whose memory is quantum.

*1:00–1:50 · Nicholas*

So we built a model of it. We call it a QRSM, a quantum recurrent state machine. Think of a recurrent neural network whose memory is qubits. Every time step repeats the same four gates: drive the emitter, let the defect turn, let the two swap energy, and emit into a light qubit that we measure. The memory, two qubits, is never looked at. Only one bit comes out. And each recorded bit updates the hidden state, which is how the model predicts what comes next. This picture is a live simulation of our Qiskit circuit, and a test holds it to Qiskit.

**Cue.** Say the acronym once, slowly. Trace the circuit left to right with the pointer. If asked: K1 = sin(alpha)|0><1| on the emitter, so a click empties the emitter and leaves the defect conditioned.

**Sources.** rewindandamplify-main/qrsm_grover/model.py; lab/engine.js and lab/test_engine.cjs (agreement with Qiskit to 1e-12).

### 4. One click. Two futures.

*1:50–2:35 · Nicholas*

Here is the question we ask it. Given a click at step three, what happens next? With no defect, a click empties the source and the machine simply starts over: the chance of another click three steps later is 10.1 percent. With a hidden defect, something remembers, and that chance drops to 4.7 percent. One click, two futures. The pattern after a rare click is a fingerprint of hidden memory. These are exact predictions of two models we programmed. They are not a diagnosis of a real device.

**Cue.** Read the two big numbers, then the caveat. Only step 3 is fixed; earlier bits can be anything.

**Sources.** research-validation/original_after_click_verification.json: 0.046675 and 0.101024. Recomputed live by lab/engine.js and by python reproduce.py.

### 5. The useful runs are the rare ones.

*2:35–3:10 · Timofey*

But there is a cost. The click we asked about happens in only 4 percent of runs. To study what follows it the ordinary way, you run the machine 25 times and throw 24 away. For one real 64-step record from our first project, it would take 27 million runs. The useful runs are the rare ones.

**Cue.** Each row on the left is one run; the amber column is the click we asked about. Let the 27 million land.

**Sources.** P(click at step 3) = 0.039542. 64-step record: rewindandamplify-main/results/numbers.json, wall.rejection_runs = 27,495,891.

### 6. Grover makes rare answers common. Two catches.

*3:10–4:05 · Timofey*

This is where a quantum computer might help. Grover's algorithm, in its general form called amplitude amplification, makes rare answers common at about the square root of the cost. For that 64-step record, 27 million runs become about a hundred calls of the machine. But there are two catches. First, it has to run the machine backwards, and our machine resets a qubit every step. A reset cannot be undone. Second, it is deep, and on today's hardware every extra gate adds noise. And we want to be honest: at this size there is no speedup. A classical sampler answers in a fraction of a millisecond. Quantum could matter only when the hidden memory gets large.

**Cue.** Say 'no speedup today' plainly; the rubric rewards it. The three bars are exact calculations for the same record, not hardware runs. Steering, the middle bar, is classical.

**Sources.** numbers.json wall: 27,495,891 runs; 6,240 steered; 125 calls. e3.classical_growth_per_qubit = 5.73. Brassard, Hoyer, Mosca, Tapp 2002; Low, Yoder, Chuang 2014.

### 7. You can’t amplify what you can’t rewind.

*4:05–5:00 · Nicholas*

Our project is about those two catches. You can't amplify what you can't rewind. So first we purify: a fresh qubit replaces every reset, and the whole run becomes one reversible circuit with the same click statistics. Second, we steer: we tune one gate so the rare click is less rare, which leaves the answer unchanged. Third, we amplify locally: one round, with a reflection on three qubits instead of all five, about half the gates. Fourth, we verify: the click is measured directly, so a failed shot shows itself. In an ideal simulator the click goes from 4 percent to 96 percent, and the answer stays right to within a small, known bias.

**Cue.** Four moves, one sentence each. What is ours: the mapping onto a hidden-memory model and the noise-aware build. Amplitude amplification itself is prior work.

**Sources.** qrsm_grover/amplify.py, fastsim.py, hardware.py. Ideal: 96.49% full (error 0), 96.10% local (TV 0.0353). 114 tests on the core package.

### 8. On IBM hardware, fewer gates won.

*5:00–6:00 · Dillon*

Then we ran it on real hardware: IBM Marrakesh, a 156-qubit processor, 8,192 shots per circuit. Without amplification, the click shows up in under 7 percent of shots. With the textbook build, full reflection, 125 two-qubit gates: 69 percent. With our lighter build, 58 gates: 77 percent. Fewer gates won, by 7.6 points, and the lighter build's answer was also closer to the exact one: an error of 0.12 against 0.18. These are raw counts with no error mitigation. Both are below the ideal 96 percent. And we cannot prove gate count is the only cause, because the two circuits also differ in width and routing.

**Cue.** Read the bars bottom to top: 6.7, 69, 77. The solid tick is the ideal simulator; the dashed tick is our noise model, next slide. Job ID is on the slide for anyone who asks.

**Sources.** hardware_campaign/runs/original_precision_v1 (job dbqb1ifv5hds73dfo310): 6,300 and 5,674 of 8,192; 58 and 125 native CZ; TV 0.1177 and 0.1814; difference 7.64 points [6.29, 8.99]. Plain: 138 of 2,048 in original_plain_v2.

### 9. A simple noise model predicts the gap.

*6:00–6:45 · Dillon*

So we checked it against a simulator. With no noise the two builds tie. Using the chip's own calibration data, a noise model predicts 83 and 76 percent: the right order, but too optimistic. Our echo circuits, which run the machine forwards and then backwards, show the chip was about one and a half times noisier than its calibration said. With that one number, fitted only on the echoes, the model predicts 78 and 70. The chip gave 77 and 69. We also tried error suppression, dynamical decoupling and twirling, and it did not help. And the answers on hardware are biased, in a way this model predicts.

**Cue.** This is the 'compared to simulator, analysed noise, tried suppression' bonus. Point at the four rows top to bottom. If asked what the model leaves out: idle decoherence, crosstalk, leakage, drift.

**Sources.** hardware_campaign/noise_model/README.md and results.json: scale 1.54; 83.15/76.29 calibration; 78.40/69.72 echo-scaled; measured 76.90/69.26. Suppression: original_suppressed_v1, TV 0.145/0.244 against 0.107/0.201 plain.

### 10. The Lab: our model, live in a browser.

*6:45–7:35 · Timofey*

Here it is running. This is the Lab: our model, live in a browser, with no install. The laser drives the emitter, the hidden defect trades energy with it, and the detector clicks. Every run is a row. The amber column is the rare click, and most rows miss it. Now rewind and amplify: mark the click, run the film backwards, flip the blank start, run forward, and the click is 96 percent. One click, two futures. And the IBM result, with our noise model beside it.

**Cue.** Click the video once to play; it is 45 seconds and silent, so talk over it. If the video will not play, switch to Rewind_Amplify_Lab.html, press the 45 s tour button, and say the same words. Do not apologise, just switch.

**Sources.** media/lab-tour.mp4, recorded frame by frame from lab/index.html by lab/capture.py with a fixed seed. It is a screen recording of the running page, not an animation.

### 11. Three places hidden memory matters. Honestly scored.

*7:35–8:15 · Dan*

Who could use this? Quantum hardware teams, to compare explanations for a drifting qubit instead of guessing. Photon-source engineers: we showed that sources with the same brightness can have photon overlap anywhere from 20 to 100 percent. And we tested laser metrology, where our own research changed our mind. An added atomic reference helped a little, 58 percent detection. A second ordinary reference reached 98. We report that too.

**Cue.** The chips on each card say what kind of evidence it is. The third card is a negative result on purpose: say it with confidence.

**Sources.** Dead time: 0.069 against true 0.65, 0.706 once modelled (qrsm_photon_poc/followup). Overlaps 1.00/0.50/0.20/0.25 (quantum_dot_bridge). Unknown-onset monitor 51.35/58.02/97.97% (laser_sensor_viability/followup).

### 12. What we claim, and what we don’t.

*8:15–8:50 · Nicholas*

So here is what we claim. A recurrent quantum model, made reversible. Amplification that preserves the answer. A lighter build that beat the textbook build on real IBM hardware. And every number traceable to saved counts and tests. What we do not claim: no speedup today, no real defect detected, no photons or wafers measured. Next, we want to fit these models to real, calibrated device records, against a strong classical baseline.

**Cue.** Left column fast, right column slow. End on the next experiment.

**Sources.** FINALS_EVIDENCE.md, FINALS_RUBRIC.md, hardware_campaign/RESULTS.md.

### 13. What we built, and what we learned.

*8:50–9:20 · All four*

Nicholas led the model and the Grover fusion. Timofey, the research and the search idea. Dan, the experiments and our video. Dillon, the figures and the revising. What we learned: more hits is not more truth, so check the answer. On today's hardware the lighter circuit wins. And report the result that goes against you. Thank you. We would love your questions.

**Cue.** Each person says their own line. Stop at 9:20. Backups from slide 14: hardware repeats 14, rubric map 23, prior work and AI 24, noise model detail 36, cinematic cut 37, reproduce 38.

**Sources.** Roles as listed in the original README and confirmed for V2; the video credit follows the team's cinematic kit. AI assistance: Claude for the original project and V3, Codex with OpenAI models for the V2 research extensions.

## Backups

| Slide | Title |
|---:|---|
| 14 | Hardware repeats and noise controls |
| 15 | Deep optical queries show large distribution errors |
| 16 | Sensor assumptions and resource accounting |
| 17 | Calibration failures can reverse the conclusion |
| 18 | Detector dead time can distort inferred coupling |
| 19 | Where the quantum component enters |
| 20 | The transfer to lithography needs its own test |
| 21 | The continued query separates models with bias |
| 22 | One step of the recurrent quantum model |
| 23 | Judging rubric and evidence map |
| 24 | Contribution, prior work and AI assistance |
| 25 | Drive amplitude: a useful negative result |
| 26 | Phase inspection: benefit depends on the budget |
| 27 | The full spatial query is costly to construct |
| 28 | Exposure: contrast trades against dose and loss |
| 29 | Model accuracy is part of the resource budget |
| 30 | Equal photon counts can hide poor interference |
| 31 | External GaAs data: a conditional reanalysis |
| 32 | The joint-photon QRSM observation model |
| 33 | More data helps only under trusted calibration |
| 34 | Atomic and photon channels on IBM |
| 35 | Hardware coverage and circuit limits |
| 36 | The same noise model, circuit by circuit. |
| 37 | The cinematic cut. 45 seconds. |
| 38 | Anyone can rerun it. One command. |

### 14. Hardware repeats and noise controls

The three current runs remain separate. Suppression used dynamical decoupling and twirling; it did not improve this pair in the observed run. The larger-shot follow-up was chosen after inspecting the first campaign and must not be described as a preselected independent confirmation of all hypotheses. Its 7.64 point yield difference has an independent-shot interval 6.29 to 8.99 points, excluding drift and calibration uncertainty. First-run ablations also include plain 6.74 percent, steering-only 24.07 percent and unsteered full three-round 48.73 percent. Conditional accuracy differs strongly. Earlier Kingston results 86.06/78.49 percent and 40/85 gates remain historical, with different layouts. None are pooled or interpreted as a universal noise advantage.

PRESENTER CUE: 

SOURCES: hardware_campaign/runs/original_plain_v2/analysis.json, original_suppressed_v1/analysis.json, original_precision_v1/analysis.json and hero_acceptance_contrast.json. All original43rows include the full earlier39circuit suite plus catalog repeats. Archived evidence research-validation/hardware_verification.json. Raw summaries primary; projected independent assignment inversion is a sensitivity analysis without calibration uncertainty.

### 15. Deep optical queries show large distribution errors

Both retained three-bin models pass exact branch and conditional-state checks before hardware. Native routing raises these queries to 26,749 and 54,998 CZ gates. Each returns zero selected shots out of 512. That alone is inconclusive: even ideal expected counts are below one. The measured data marginals have substantial total-variation error, while full data-plus-environment distributions deviate still more. The one-bin circuits can instead produce inflated acceptance with wrong conditional distributions. Better mathematical truncation therefore does not guarantee a more useful hardware answer. Classical recursion already solves these small models efficiently. Cavity-two is a deliberately truncated physical surrogate, and Z statistics do not establish full conditional-state fidelity.

PRESENTER CUE: 

SOURCES: hardware_campaign/runs/optical_dilation_plain_v2/analysis.json and raw.json, rows optical_3bin_0p03_all_r1 and optical_3bin_0p003_all_r1. Raw0/512, Wilson upper.7447%, versus ideal.127833/.127551%. DataZTV.436846/.384204. Underlying genericCX10,189/19,864 from multibin_followup/main/ideal_0p03.json and ideal_0p003.json. State approximation error versus cavity2 .02604/.01094 before hardware is a different quantity.

### 16. Sensor assumptions and resource accounting

The atomic response follows finite driven Bloch rotations with T1/T2 damping, preparation error, asymmetric readout error and binomial projection noise. Optical intensity changes the Rabi frequency and induces an assumed light shift during pulses. Conventional receivers include source-photon shot noise, electronics and reference drift. All methods see the same underlying source task and duration. The photon allocation is a declared assumption: atomic coupling and beam geometry are not specified from a real apparatus, and reference lasers plus atomic support optics are not included in a full cost comparison. Therefore this is not a resource-matched quantum advantage test.

PRESENTER CUE: 

SOURCES: laser_sensor_viability/results.json config and resource_ledger supply the unchanged physical model. New task: followup/README.md, protocol.json and main/results.json. Unknown source onset48–96s, eight independently trained/calibrated pipelines, held-out sessions. Whole-record alarm calibration, misses and prealarms charged32sin restricted delay. Bishof etal., PRL111093604, https://arxiv.org/abs/1303.6741 is physical precedent, not chosen device specifications.

### 17. Calibration failures can reverse the conclusion

These are the new unknown-onset results. Each cell gives timely detection followed by full-record false alarms. The target is source-frequency change, so a sensor/reference/path change can trigger a false source diagnosis. Shorter atomic coherence makes the fused channel worse than C alone. A separate agreement veto reduces the primary-reference failure but sacrifices sensitivity and still exceeds the nominal alarm target. Shared-path drift is structurally indistinguishable from source motion in this measurement model. Hierarchical pipeline/session intervals quantify finite simulation variation, not physical model error or calibrated universal coverage. None of the older known-midpoint rates belong in this table.

PRESENTER CUE: 

SOURCES: laser_sensor_viability/followup/main/results.json and README.md. New primary-reference CQFAR84.53%, common-path94.11%. Agreement rule15.57% and68.23%, respectively. Nominal CQgain6.67pp, shortcoherence−5.42pp. Eight pipelines and96test sessions per scenario.

### 18. Detector dead time can distort inferred coupling

After a click, the next recorded bit is forced to zero while the underlying system evolves unconditionally. Ignoring that readout process misattributes detector correlation to the hidden interaction. Including it improves held-out log likelihood by 0.4584 nats per 24-bin record, with paired conditional 95% interval 0.3978–0.5210. The fitted coupling moves closer to the known synthetic value, but dephasing reaches its upper bound and efficiency remains biased. A trained HMM captures the detector correlation too: the corrected physical model’s advantage over it is unresolved. Other physical parameters and the family remain known. This fresh result replaces the earlier truth-informed candidate-count example in the current deck.

PRESENTER CUE: 

SOURCES: qrsm_photon_poc/followup/README.md, inference_results/fixed_411101_dead1_fit0.json, fixed_411101_dead1_fit1.json, parameter_validation_v2/ and independent_review.json. The HMM difference interval for the corrected model is−.0067to+.0222nats/record.

### 19. Where the quantum component enters

A sensor can use quantum dynamics while a classical computer processes its readouts. We now compile the finite driven atomic channel, including dissipation, into an IBM digital circuit. That tests a bounded implementation on superconducting hardware, not an atom, physical optical coupling or a 128 second acquisition. Unknown-onset detection still runs as classical inference on synthetic records. The separate recurrent-model query uses coherent preparation and amplitude amplification. Connecting a calibrated full acquisition process to a competitive quantum algorithm remains further work. No end-to-end quantum advantage follows from executing a component.

PRESENTER CUE: 

SOURCES: hardware_campaign/optical_controls/README.md, models.py and hardware_integration_review.json. Canonical laser_sensor_viability/model.py. Independent Bloch versus Lindblad/Stinespring checks. LASER_DIAGNOSTICS_ROADMAP.md and hardware_campaign/coverage.json distinguish component, classical and physical requirements.

### 20. The transfer to lithography needs its own test

The distinction matters. A CO2 drive laser heats tin to create plasma, which emits EUV. Monitoring the drive is different from measuring EUV. A narrow-line 698 nm atomic benchmark does not automatically transfer to either of those signals or to a 193 nm broadband pulsed excimer source. Existing conventional monitoring measures relevant source quantities. Cymer and imec reported controlled wafer experiments correlating light-source changes with critical-dimension behavior. That motivates source metrology, not a quantitative yield claim for our sensor. Atomic laser-noise metrology is also established prior work, including Bishof and colleagues in 2013.

PRESENTER CUE: 

SOURCES: ASML: https://www.asml.com/en/technology/lithography-principles/light-and-lasers and https://www.asml.com/en/products/euv-lithography-systems. Cymer/imec2014: https://www.cymer.com/wp-content/uploads/2018/12/Cymer_SPIE_AdvancedLithography_2014.pdf. Bishof etal.: https://arxiv.org/abs/1303.6741.

### 21. The continued query separates models with bias

The selected precision follow-up uses 8192 shots per circuit. Its steered local implementation gives step-six rates 8.794 percent with the programmed defect and 11.661 percent without it. The raw contrast has the intended sign and a shot-based interval excluding zero. Both rates remain biased relative to 4.667 and 10.102 percent exact targets. Crucially, plain, steered full and memory-only implementations reverse the expected sign. The initial campaign also failed to resolve the small local contrast at its lower precision. We preserve these results rather than calling this reliable diagnosis. The effect distinguishes particular programmed circuits under particular conditions; it does not locate unknown defects in the IBM processor or a laser.

PRESENTER CUE: 

SOURCES: hardware_campaign/runs/original_precision_v1/loop_contrasts.json and analysis.json. Local step6counts538/6118 versus834/7152 accepted histories. Contrast−.0286735, independent-shot Wilson-based95%interval[−.0389321,−.0183558]. Intervals exclude drift, readout-calibration and model uncertainty. Original ideal target research-validation/original_after_click_verification.json. Earlier archived continued jobs remain separate historical evidence.

### 22. One step of the recurrent quantum model

The emitter rotates under a drive. A hidden qubit rotates under its detuning and exchanges excitation with the emitter. The emitter then exchanges with a fresh output qubit. The dynamic implementation measures and resets that output each step. The purified implementation retains it, so the environment and history required for reversal remain in the circuit. This trades extra qubits for reversibility. Model steps are dimensionless. The optical labels describe a model interpretation. These IBM circuits did not measure photon arrivals.

PRESENTER CUE: 

SOURCES: Original fig_circuit_hybrid.png, qrsm_grover/model.py and tests. QRSM defaults theta=.6,gamma=.2,phi=(.45,),zeta=(.3,).

### 23. Judging rubric and evidence map

This map follows the supplied Qiskit Fall Fest judging rubric. Exceptional performance asks for a specific stakeholder and realistic impact, a defensible quantum rationale that considers classical alternatives and hardware scale, reproducible Qiskit implementation, rigorous comparisons, a clear contribution relative to reused ideas, accessible delivery within the time limit, and shared understanding. The hardware bonus is a separate highest-tier item, not an additive sum of all tier values. We do not predict a judge score.

PRESENTER CUE: 

SOURCES: User-supplied Qiskit_Fall_Fest_Judging_Rubric.xlsx, extracted by root. FINALS_RUBRIC.md.

### 24. Contribution, prior work and AI assistance

The original README documents the team research timeline and Claude assistance. The team set the original direction and questions and reviewed the work. This finals revision uses Codex and OpenAI models to assist research review, reproduction, simulations, tests, application and presentation. Do not imply that every generated analysis has already received manual team verification. Amplitude amplification and Bayesian quantum inference are prior art. Atomic laser-noise spectroscopy is also prior art. The separate optical and sensing extensions test scoped feasibility questions and do not establish an end-to-end quantum computing advantage.

PRESENTER CUE: 

SOURCES: Original README PriorworkandAIhelp and Team. Brassardetal https://arxiv.org/abs/quant-ph/0005055. Lowetal https://arxiv.org/abs/1402.7359. Bishofetal https://arxiv.org/abs/1303.6741.

### 25. Drive amplitude: a useful negative result

The field-amplitude proxy is the drive parameter, not an incident-photon flux. A 20 percent field step would correspond to 44 percent intensity under fixed coupling. This low-count regime yields poor timely detection alongside substantial full-record false alarms. The physical filter, fitted HMM and count detector share the same bits; these are not independent engineered optical receivers. The post-holdout prior-only control exposes a weak constant-estimate comparison: for this step, using observations only slightly improves the prior estimate, and for the four other source-changing cases it makes estimation worse. Afterpulsing produces 10.55 percent false source alarms. The model needs a better operating regime and calibrated detector dynamics before a practical monitor claim.

PRESENTER CUE: 

SOURCES: qrsm_photon_poc/drive_diagnostics_followup/README.md; main/results.json, prior_only_estimation_control.json, independent_review.json, prior_only_independent_review.json. Four separately calibrated pipelines,13cases,128records per pipeline/case,96bins/cavity4. Stable FAR35/512 and step timely19/512 for physical QRSM. Prior-only MSE minus observed-data MSE .00025149, paired interval [.00007878,.00044596] for this step, a small conditional effect. Prior supplement is post-holdout descriptive, not another confirmatory test.

### 26. Phase inspection: benefit depends on the budget

A doubled fringe has a pi ambiguity. Pure NOON performs well locally around a shared calibrated working point, but fails to identify the full phase globally. A charged coherent pilot resolves that ambiguity in the tested hybrid. Both sample modes illuminate the object; the resource is 20,000 mean photons before object transmission, including reference-arm photons. The high-efficiency case has 90 percent object transmission and 90 percent detection, with ideal preparation. Lower transmission removes the precision benefit. At one-percent preparation, matching dose requires 100 times longer for pure NOON; at fixed clock time its precision is worse. Ideal number-resolving detection, a known phase reference and the declared classical protocol bound this result. It is not superiority over all classical designs or a measured feature-size benefit.

PRESENTER CUE: 

SOURCES: quantum_lithography_poc/phase_inspection_followup/README.md and results.json high_efficiency/equal_sample_photons. Pure NOON modulo-pi RMSE .0062646rad, full2piRMSE2.226739rad. Hybrid.00637086rad, coherent.007908rad,2000outcomes per protocol in each cohort. Zero errors gives95%Wilson upper bound.1917%. Global phases reused across methods; outcomes independently drawn. Separate equal-clock and equal-dose budgets.

### 27. The full spatial query is costly to construct

This is an actual constructed reversible 49-cell oracle, not an extrapolation from three cells. Four count qubits per cell encode a capped Poisson law,23 bits accumulate the weighted score, and 170 extra clean ancillas support explicit reversible gates. Both 389 qubit circuits pass QPY serialization and independent structural, arithmetic and uncomputation checks. The CX values are constructive generic decomposition upper bounds, including preparation and one complete amplification round; they are not a routed device compilation. Rounding and capped-tail bounds bracket the original event, with relative bracket width 0.2406 percent at dose 1.5 and 0.3526 percent at dose 1.8. Classical dynamic programming already solves this independent-cell distribution efficiently. Construction alone establishes neither computational advantage nor physical lithography feasibility.

PRESENTER CUE: 

SOURCES: finals-lithography/full_spatial_circuit/README.md, results.json, process_bounds.py, independent_review.json. Floor and ceiling clean circuits389qubits; CX bounds3,382,108/2,874,028 and U5,050,537/4,288,741. Dose1.5 original event bracket [.004226948015,.004237128599]; conservative conditionalTVbound.00482. Cap15 value change usesPoisson tailN>=16, encoded cap probabilityusesN>=15. Check row direction against event interval: floor weights admit an upper event; ceiling weights give a lower event.

### 28. Exposure: contrast trades against dose and loss

The response combines declared linear and two-photon activation coefficients, loss, phase jitter, finite pixel collection and post-activation blur. Activations are rare Poisson events, not direct photon probabilities. The NOON pattern has stronger mean contrast and higher best guard-cell accuracy under the nominal assumptions, but requires more incident photons at its best tested dose. The duty-cycle comparator concentrates equal average photons into ten-percent active time, giving higher peak intensity. It is one explicit classical competitor, not an optimum over all illumination. Loss, blur, linear leakage, background and low preparation success degrade the result. The 20 guard cells exclude boundary cells. This is a sensitivity study of an assumed resist, not a prediction for an available material or fabricated feature.

PRESENTER CUE: 

SOURCES: quantum_lithography_poc/exposure_followup/README.md and results.json finite_nominal. Table optimizes each method over tested doses, so it is not a single equal-dose operating point. G1/G2 supplement verifies spatial conservation and harmonic/per-photon accounting. 540,000Poisson realizations. Wavelength800nm, ±30degree modes, second harmonic400nm; period is not linewidth. Independent or fast phase jitter/mean-rate approximation excludes slow correlated phase drift.

### 29. Model accuracy is part of the resource budget

The original optical circuit uses only two cavity levels. Comparing its conditional predictions with a six-level reference reveals errors of several percentage points, especially under stronger drive. Increasing the cutoff reduces the discrepancy in these cases, but raises state and circuit costs. Six fresh joint-inference cases fit five parameters with source and detector controls. Fixed settings do not resolve performance versus an HMM; controlled settings give small held-out gains under shared known physics. Fixed-drive detuning sign remains structurally ambiguous. Controlled settings break that exact symmetry but do not establish reliable finite-data sign identification. Local curvature intervals fail near boundaries and are not global uncertainty guarantees. Thermal, multimode and non-Markovian effects remain future model families.

PRESENTER CUE: 

SOURCES: qrsm_photon_poc/followup/README.md, dynamics_results.json, inference_results/, parameter_validation_v2/ and independent_review.json. Max after-click error over tested later lags versus cavity dimension6. Master equation independently checked with QuTiP; trajectory statistics tested separately. Controlled model-HMM logscore gains .0574[.0158,.1014] and .0972[.0448,.1495]nats/24-binrecord under conditional bootstrap. This does not establish physical defect identification or a quantum computational speedup.

### 30. Equal photon counts can hide poor interference

Each photon separately has the same brightness and fifty-fifty frequency distribution. Shared versus independent offsets still change pair overlap from one to 0.6. A single-photon marginal misses information in the joint observation. This benchmark environment is entirely classical, and an HMM is a necessary competitor. The new sequential HOM instrument implements the broader hidden-state question using a different complete-emission source model. Its digital circuits also test these frozen pair controls. It does not turn this classical memory example into a coherent-defect witness. An engineer can use the distinction to select interference-sensitive source measurements alongside collection cost. At 80 percent survival, a pair takes 1.5625 attempts on average; at 20 percent, it takes 25. These are surviving pairs, not necessarily resolved coincidences.

PRESENTER CUE: 

SOURCES: quantum_dot_bridge/results.json classical_trap_pair_comparison endpoints p_switch=0 and.5, PROTOCOL.md and independent_review.json. Both marginals are(.5,.5), ideal g2(0)=0 and eta=.2. M1/.6 gives coincidence per attempted excitation pair0/.008 at a balanced beamsplitter. The classical state remains fixed within each wavepacket; the pair model does not infer a switching time. Other benchmark cases retain counts while giving overlap1/.5/.2/.25 from pure dephasing or detuning. Sixteen tests and independent density-kernel quadrature support the calculations. External GaAs histograms are separate and did not calibrate this illustrative model. No semiconductor defect, physical device setting, quantum advantage or lithography yield was identified.

### 31. External GaAs data: a conditional reanalysis

The real-data lesson is that a source-quality estimate depends on measurement controls. These are external Hong–Ou–Mandel histograms analyzed classically, not team measurements or a QRSM fit. We normalize central peaks to side peaks and apply published splitter and multiphoton corrections. The intervals exclude polarization, routing and drift systematics. At 39.4 nanoseconds, co-only normalization changes the estimate from 0.7724 to 0.7938. That discrepancy guides checks of polarization, alignment and normalization before assigning a cause. The new joint-photon instrument supplies a mathematical candidate model, but these aggregate histograms lack the sequential records and source calibration needed to fit and test it. Repeated time-tagged acquisitions and held-out comparisons remain necessary. No microscopic cause, monotonic decay, reproduced author pipeline or improved device performance follows.

PRESENTER CUE: 

SOURCES: quantum_dot_bridge/hom_analysis/results.json, PROTOCOL.md and independent review. Dataset https://doi.org/10.5281/zenodo.6337697, CC BY4.0, by Julian Munzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil. Paper https://arxiv.org/html/2203.08682v1 SectionIV Eqs3–4. Quoted paper V=.803(.005),.826(.004),.774(.004) remain separate. Our primary extraction uses half-open windows of half-width2ns, no background subtraction, reference cycle indices−2,−1,+1,+2 and200000Monte Carlo draws. R=.514±.007,g2=.016±.001, assumed independent but shared across separations. Data hashes verified against reference_hom/provenance_manifest.json. These aggregate histograms cannot provide original QRSM binary histories or uniquely identify charge traps.

### 32. The joint-photon QRSM observation model

The missing observation model is now implemented. A fully excited emitter decays into a photon whose exponential temporal mode depends on the environmental state. Complex Gram overlaps embed the finite mode family exactly. A controlled-SWAP parity measurement equals the balanced-HOM symmetry statistic, and tracing the photon modes produces a conditional environmental map. Independent bosonic calculations check probabilities and conditional coherences. The environment persists between pairs. Passive outcomes cannot separate these hypotheses. A calibrated shift introduces a small joint effect, but the 64 pair simulated study gives only 5.60 percent coherent flags versus 4.50 percent classical false flags. The separate selected four-pair IBM circuits use 22/29 qubits and 256/334 native CZ gates. Their raw flag distributions have TV.249/.286, so implementation noise remains substantial. They do not validate the optical assumptions or certify quantum memory.

PRESENTER CUE: 

SOURCES: quantum_dot_bridge/qrsm_hom_followup/README.md, physical_model.py, circuits.py, main/results.json and main/independent_review.json. Thirty thousand synthetic records replayed independently. Hardware current summary family_results.dot_selected_four_pair, selected_four_coherent and selected_four_classical,4096shots each. Distinct chosenθ3π/4,+2Γfour-pair control. Zconditional memory is not fullstate tomography. Main14circuit bundle uses earlierθπ/3. New source assumes full emission, fixed environment during each packet and controlled gaps. Original QRSM excitation-exchange dynamics are distinct. Measurement precedent Garcia-Escartin and Chamorro-Posada, https://arxiv.org/html/1303.6814v1.

### 33. More data helps only under trusted calibration

After preserving the negative main result, an exact 648 setting scan selected a new control and gap rotation. A separate prospective simulation uses ideal resets between four-pair blocks and independently calibrated thresholds at every budget. At 2584 attempted pairs, nominal flags reach 79.75 percent with 4.85 percent classical false flags. The full budget curve remains visible. This is a different preparation protocol, not a tuned replacement of the 64 pair study. At 7644 pairs, changes in collection, mode overlap or readout give 72,53.25 and 21.05 percent false flags from still-classical sources. The 8 state HMM differs from the calibrated physical predictor by only 0.0000092 nats per pair, with an interval spanning zero. All 20 HMM starts reached the iteration cap. More data cannot repair a wrong measurement model, and no classical impossibility or physical defect follows.

PRESENTER CUE: 

SOURCES: quantum_dot_bridge/qrsm_hom_followup/exploratory_design/README.md, design_results.json, VALIDATION_PROTOCOL.md, validation_run/results.json and independent_review.json. θ3π/4, second-emission shift+2Γ, eta.8, resetI/2 per4pair block. All lost pairs charged,2source excitations per pair. Independent20k training and20k predictive blocks,4/8state HMM10starts/200iterations. Rigorous simple-hypothesis bound1911blocks uses a different exact-model log4 threshold, not the empirical curves. No validated physical control/reset time.

### 34. Atomic and photon channels on IBM

The atomic adapter exponentiates the actual driven Lindblad evolution through finite pulses and free precession, constructs its complete channel and synthesizes a Stinespring isometry. It does not rotate a qubit directly to an analytic output probability. Independent affine-Bloch calculations verify the ideal response. IBM results show the response direction but retain material bias, especially at the outer detunings. Separate photon circuits prepare actual finite mode states, apply phases, recombine and encode loss. A coherent source is represented by its unnormalized Poisson sectors through N8; vacuum and the omitted tail remain charged. Raw occupancy moments include source failures. These are meaningful implementation tests, while acquisition, calibration and apparatus costs remain optical questions.

PRESENTER CUE: 

SOURCES: hardware_campaign/optical_controls/README.md, PROTOCOL.md, models.py, bundle_v2/manifest.json and hardware_integration_review.json. hardware_campaign/runs/optical_controls_plain_v1/analysis.json,33science rows. Atomic originalT1=100s,T2=.2s,2.5ms pulses,20ms dark interval,1% preparation error; physical optical2/4%readout assumptions not added as if hardware correction. Coherent mean2before object, tailN>8=.0002374473, source/detection/object losses declared. Independent compiled mapping and moments audit passed.

### 35. Hardware coverage and circuit limits

Ten completed jobs execute 207 science circuits and 40 calibration circuits, totaling 688640 shots and 244 charged QPU seconds. These are circuit executions including repeats, not 207 independent discoveries. The campaign covers the original suite and meaningful rungs of circuit-ready families. Independent 3/5/7 site contacts compare enumeration and clean counters. The 1024 entry seeded-diagonal stress circuit reaches 98,680 native CZ gates and 46.58 percent raw matches versus 99.23 percent ideal. It is distinct from semantic retrieval. Eight-step rounds and ten-step bounded rewinds test ingredients, not full adaptive BBHT. Four-pair dot circuits use 22/29 qubits and a declared 32 entry flag-memory marginal. The 389 qubit 49 cell construction cannot fit 156 qubits. Classical benchmarks, published optical data and real process calibration remain separate requirements.

PRESENTER CUE: 

SOURCES: hardware_campaign/results.json and RESULTS.md, all10job IDs with immutable plans/raw counts and exact ISAQPY. coverage.json and coverage.md; extensions/bundle_v1/manifest.json and independent_review.json; quantum_dot_bridge/qrsm_hom_followup/exploratory_design/HARDWARE_EXTENSION.md and hardware_bundle/manifest.json. Native counts differ from generic constructions. Z marginal checks are not full-state fidelity. Full49 results in finals-lithography/full_spatial_circuit/results.json.

### 36. The same noise model, circuit by circuit.

Backup. The same noise model, fitted only on the echo circuits, applied to all eight after-click circuits. It predicts the lighter build's biased answers within half a point and explains why plain sampling reverses the order: on a 4 percent event, false clicks swamp the true ones. It under-predicts the damage to the 182-gate circuit.

SOURCES: hardware_campaign/noise_model/results.json, after_click.

### 37. The cinematic cut. 45 seconds.

Backup or optional cold open. The team's problem-first video with original music. It is a cinematic explainer, not a screen recording of the product. Click once to play.

SOURCES: media/cinematic-45s.mp4, from the team's cinematic kit. Numbers shown match hardware_campaign/RESULTS.md.

### 38. Anyone can rerun it. One command.

Backup for 'does the code run?'. One command, about ten seconds, no IBM account: the exact model, the Qiskit circuits on Aer, the classical baseline, the noise model and the recounted IBM results.

SOURCES: reproduce.py; docs/reproduce_output.txt.
