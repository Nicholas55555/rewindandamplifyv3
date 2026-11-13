# Presenter guide: finals deck V3

**13 main slides, planned 9:25 including a 70-second Lab demo. The limit is 10:00.** The narration below is 1,145 words, about 122 words a minute overall.

Speaker assignments are suggestions: change them to suit the team, and rehearse aloud with a timer.

The same notes are inside the PowerPoint. Slides 14 onward are backups for questions: slide 14 is a map of them, and each one's note says when to show it.

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
| 10 | 6:45–8:00 | Timofey | The Lab: our model, live in a browser. |
| 11 | 8:00–8:20 | Dan | Beyond qubits: three tests. Honestly scored. |
| 12 | 8:20–8:55 | Nicholas | What we claim, and what we don’t. |
| 13 | 8:55–9:25 | All four | What we built, and what we learned. |

## Main talk

### 1. Rewind & Amplify

*0:00–0:15 · Nicholas*

We are Qubits, from Florida Gulf Coast University. A quantum device can hide a defect that changes what it does next. We built a model of that, and a way to ask the model about its rarest events. Then we ran it on IBM hardware.

**Cue.** One breath, then move on. Optional cold open: type 39 and Enter to play the 45-second cinematic cut first, then 2 and Enter. If you use it, play the 45-second Lab video instead of the 70-second one on slide 10 (media/lab-tour-45s.mp4), or demo the Lab live, or you will run over.

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

*6:45–8:00 · Timofey*

Here it is running. This is the Lab: our model, live in a browser, with no install. The laser drives the emitter, the hidden defect trades energy with it, and the detector clicks. Every run is a row. The amber column is the rare click, and most rows miss it. Now rewind and amplify: mark the click, run the film backwards, flip the blank start, run forward, and the click is 96 percent. One click, two futures. And the IBM result, with our noise model beside it. Then we asked the same question of other light. Two photon sources, equally bright: only the pairs reveal the hidden memory. A drifting laser: our atomic sensor helped a little, a second ordinary reference far more. And chip printing: entangled pairs draw cleaner stripes, and pay for it in photons.

**Cue.** Click the video once to play. It is 70 seconds and silent, so talk over it: the first 41 seconds are the project, the last 29 are the three research tabs. If the video will not play, switch to Rewind_Amplify_Lab.html, press the tour button, and say the same words. Short on time: stop the video when the IBM hardware scene ends, at 41 seconds. Do not apologise, just switch.

**Sources.** media/lab-tour.mp4, recorded frame by frame from lab/index.html by lab/capture.py with a fixed seed. It is a screen recording of the running page, not an animation. The three research tabs are held to the studies' saved files by lab/test_research.cjs.

### 11. Beyond qubits: three tests. Honestly scored.

*8:00–8:20 · Dan*

So, honestly scored. Photon sources: our simulation, plus published data we reanalysed. Laser monitoring: a negative result for our quantum add-on, and we keep it. Chipmaking: cleaner stripes for more light, and our full question would need 389 qubits. The chip we used has 156.

**Cue.** Twenty seconds: one sentence per card, then move on. The chip on each card says what kind of evidence it is. The second card is a negative result on purpose: say it with confidence. Backups 24 to 38 cover each study.

**Sources.** Photons: 0.0% and 0.8% coincidences at overlap 1.00 and 0.60 (quantum_dot_bridge/results.json). Lasers: 51.35, 58.02 and 97.97% caught within 32 s (laser_sensor_viability/followup/main/results.json). Chipmaking: 95.16, 78.28 and 83.29% of cells right (quantum_lithography_poc/exposure_followup/results.json); 389 qubits (finals-lithography/full_spatial_circuit/results.json).

### 12. What we claim, and what we don’t.

*8:20–8:55 · Nicholas*

So here is what we claim. A recurrent quantum model, made reversible. Amplification that preserves the answer. A lighter build that beat the textbook build on real IBM hardware. And every number traceable to saved counts and tests. What we do not claim: no speedup today, no real defect detected, no photons or wafers measured. Next, we want to fit these models to real, calibrated device records, against a strong classical baseline.

**Cue.** Left column fast, right column slow. End on the next experiment.

**Sources.** FINALS_EVIDENCE.md, FINALS_RUBRIC.md, hardware_campaign/RESULTS.md.

### 13. What we built, and what we learned.

*8:55–9:25 · All four*

Nicholas led the model and the Grover fusion. Timofey, the research and the search idea. Dan, the experiments and our video. Dillon, the figures and the revising. What we learned: more hits is not more truth, so check the answer. On today's hardware the lighter circuit wins. And report the result that goes against you. Thank you. We would love your questions.

**Cue.** Each person says their own line. Stop at 9:25. Backups start at slide 14, which is a map of them: hardware 15 to 19, method and credit 20 to 23, light 24 to 29, lasers 30 to 34, chipmaking 35 to 38, cinematic cut 39.

**Sources.** Roles as listed in the original README and confirmed for V2; the video credit follows the team's cinematic kit. AI assistance: Claude for the original project and V3, Codex with OpenAI models for the V2 research extensions.

## Backups

| Slide | Title |
|---:|---|
| 14 | Backups, by the question asked. |
| 15 | What each move bought, measured on the chip. |
| 16 | Three runs. The lighter build led every time. |
| 17 | The same noise model, circuit by circuit. |
| 18 | Deeper circuits returned noise. We kept them. |
| 19 | What ran on IBM, and where it stops. |
| 20 | One step of the machine, in gates and in maths. |
| 21 | Anyone can rerun it. One command. |
| 22 | The rubric, and where each point is answered. |
| 23 | What is ours, what is prior work, and where AI helped. |
| 24 | Equally bright. Not equally good. |
| 25 | A real quantum dot: published data, reanalysed. |
| 26 | Ignore the detector’s blind time, and the fit is wrong. |
| 27 | A QRSM for photon pairs: memory between pairs. |
| 28 | More data helps only if the calibration holds. |
| 29 | A better model costs more qubits. |
| 30 | A calibration slip can reverse the conclusion. |
| 31 | The laser monitor: what we assumed. |
| 32 | The atomic channel, run as a circuit on IBM. |
| 33 | Drive amplitude: a negative result we keep. |
| 34 | Where the quantum part actually enters. |
| 35 | Sharper lines, paid for in photons. |
| 36 | The full question needs 389 qubits. We have 156. |
| 37 | Reading a phase: the benefit depends on the budget. |
| 38 | Lithography light is not our laboratory laser. |
| 39 | The cinematic cut. 45 seconds. |
| 40 | Our machine, asked three fields’ question. |
| 41 | Written down first: every direction held. |

### 14. Backups, by the question asked.

**Show this when.** You need a backup and do not remember its number.

The backups are grouped by topic: what ran on IBM, method and credit, light and detectors, lasers, chipmaking. In a slide show, type a slide number and press Enter to jump straight to it.

**Sources.** Built from the deck itself by finals-deck/v3_backups.py, so the numbers cannot drift.

### 15. What each move bought, measured on the chip.

**Show this when.** “How much did each part of your method contribute?” or “Why not just run Grover?”

These five circuits ran in the first job, 2,048 shots each. Plain sampling found the click in 6.7 percent of shots. The ideal is 3.95, so on a rare event noise adds false clicks. Steering one gate costs no extra two-qubit gates and raised it to 24 percent. Textbook amplification without steering needs three rounds and 345 gates, and stalled at 49 percent. Steering plus one round reached 64 percent with the full reflection and 77 percent with our lighter one. This is one run of each circuit. Only the last two were repeated.

**Sources.** hardware_campaign/runs/original_plain_v2/analysis.json, rows click3-full-r0, click3-steered-full-r0, click3-full-r3, click3-steered-full-r1 and click3-steered-memory+last-1-r1. Job dbqarvmjjaos73agv2u0.

### 16. Three runs. The lighter build led every time.

**Show this when.** “Was that one lucky run?” or “Did error suppression help?”

The same two compiled circuits ran three times, and the runs are never pooled. The lighter build led by 13.1 points in the first run, 14.5 with suppression, and 7.6 in the 8,192-shot repeat. Suppression means dynamical decoupling plus twirling. It did not improve the answer error: for the local build it went from 0.107 to 0.145. The larger repeat was chosen after we saw the first run, so call it a follow-up, not a preregistered confirmation. Its interval, 6.29 to 8.99 points, is shot noise only and leaves out drift and calibration. Earlier results on IBM Kingston, 86.06 and 78.49 percent with 40 and 85 gates, are historical and used different layouts.

**Sources.** hardware_campaign/runs/original_plain_v2/analysis.json, original_suppressed_v1/analysis.json, original_precision_v1/analysis.json and hero_acceptance_contrast.json. Archived Kingston evidence: research-validation/hardware_verification.json.

### 17. The same noise model, circuit by circuit.

**Show this when.** “Does a simulator explain the hardware?” or “Is the after-click answer right on hardware?”

This is the noise model from slide 9, applied to the eight after-click circuits. Each pair is the chance of a click at step 6: with the programmed defect, then without it. The exact values are 4.67 and 10.10 percent. Only the steer-plus-local build returned the right order on the chip, 8.8 against 11.7 percent, and both numbers are biased. Plain sampling, the full reflection and the memory-only control reverse the order. The model, fitted only on the echo circuits, predicts the local build's values within about half a point. It under-predicts the damage to the 182-gate circuit. This separates two programmed circuits under these conditions. It does not locate an unknown defect in the IBM processor.

**Sources.** hardware_campaign/noise_model/results.json (after_click). hardware_campaign/runs/original_precision_v1/loop_contrasts.json: local build, step 6: 538 of 6,118 and 834 of 7,152 accepted histories; difference −0.0287, interval −0.0389 to −0.0184 (shot noise only).

### 18. Deeper circuits returned noise. We kept them.

**Show this when.** “What happens with deeper circuits?” or “Did anything fail?”

We also compiled a three-bin optical model for the chip. Routing raised it to 26,749 and 54,998 two-qubit gates. Each returned zero accepted shots out of 512. That alone proves little, because even a perfect chip would expect less than one hit. But the measured distribution is far from the target, with errors of 0.44 and 0.38. A mathematically better truncation did not give a more useful hardware answer, and a classical recursion already solves these small models. We keep the result because it marks where today's hardware stops.

**Sources.** hardware_campaign/runs/optical_dilation_plain_v2/analysis.json, rows optical_3bin_0p03_all_r1 and optical_3bin_0p003_all_r1: 0 of 512, Wilson upper bound 0.74%, ideal 0.1278% and 0.1276%, data-register TV 0.4368 and 0.3842. Z statistics are not a state fidelity.

### 19. What ran on IBM, and where it stops.

**Show this when.** “What exactly ran on real hardware?”

Ten jobs on IBM Marrakesh: 207 science circuits and 40 calibration circuits, 688,640 shots, 244 seconds of processor time. Those are circuit executions including repeats, not 207 separate findings. The original query ran in full and was repeated. The quantum-dot, atomic and photon models ran as digital circuits, with no optical setup involved. Deeper stress circuits showed that a high hit rate can hide a wrong answer. The full 49-cell exposure circuit needs 389 qubits and cannot fit a 156-qubit device. Every research family has a written ledger of what was shown and what is missing.

**Sources.** hardware_campaign/results.json, RESULTS.md and coverage.json (25 families). Job IDs, plans, raw counts and compiled circuits: hardware_campaign/runs/.

### 20. One step of the machine, in gates and in maths.

**Show this when.** “How does the model work, exactly?” or “How did you make it reversible?”

The emitter rotates under the drive. The hidden qubit rotates under its detuning and exchanges one excitation with the emitter. Then the emitter partly swaps into a light qubit. In the dynamic version that light qubit is measured and reset every step. In the purified version we keep each step's light in a fresh qubit and measure at the end, so the whole run is one reversible circuit with the same click statistics. That trades qubits for reversibility: two memory qubits plus one per step. A click applies K1, which empties the emitter and leaves the defect conditioned on the record. That back-action is the recurrent update.

**Sources.** rewindandamplify-main/qrsm_grover/model.py and its tests. Defaults θ = 0.6, γ = 0.2, φ = 0.45, ζ = 0.3. lab/engine.js is a gate-for-gate port, tested against Qiskit to 1e-12.

### 21. Anyone can rerun it. One command.

**Show this when.** “Does the code run?” or “Can we check your numbers?”

One command, about ten seconds, no IBM account. It prints the exact model, the Qiskit circuits on an Aer simulator, the classical baseline, the noise-model prediction and the IBM results recounted from the saved raw counts. Continuous integration runs it on every push, on Linux and Windows.

**Sources.** reproduce.py; docs/reproduce_output.txt; .github/workflows/ci.yml.

### 22. The rubric, and where each point is answered.

**Show this when.** A judge asks where a criterion is addressed.

This map follows the published judging criteria. For each one it names the slides that answer it. The hardware bonus is the highest tier reached, not a sum of tiers. We do not predict a score.

**Sources.** FINALS_RUBRIC.md, which quotes the criteria published on the event page.

### 23. What is ours, what is prior work, and where AI helped.

**Show this when.** “What is original here?” or “How did you use AI?”

Amplitude amplification and amplified conditional inference are prior work, and so is atomic laser-noise spectroscopy. The QRSM idea and its exact filter came before the event. The hackathon project is the Qiskit build, the fusion with Grover, steering, the local reflection and the experiments. The finals work added model audits, the joint-photon model, the IBM Marrakesh campaign, the noise model and the Lab. The original project and V3 were built with Claude, and the V2 research extensions with Codex and OpenAI models. The team set the questions and reviewed the results. Do not say that every generated analysis was checked line by line by hand.

**Sources.** README.md, section “Team, prior work and AI assistance”. Brassard et al., arXiv:quant-ph/0005055. Low, Yoder and Chuang, arXiv:1402.7359. Bishof et al., arXiv:1303.6741.

### 24. Equally bright. Not equally good.

**Show this when.** “Can’t you just count photons?” or “What does hidden memory mean for a photon source?”

Each photon on its own has the same brightness and the same fifty-fifty mix of two colours. If the hidden environment holds still between the two photons, they match, and at a beam splitter they always leave together. If it switches, they can differ, and sometimes one goes each way. The overlap falls from 1 to 0.6, and coincidences rise from zero to 0.8 percent of attempts. So a single-photon measurement misses what the pair measurement sees. The environment here is classical, so a hidden-Markov model is a fair competitor: this is not a witness of quantum memory. The same two cases ran as five-qubit circuits on IBM and gave overlaps of 0.81 and 0.52, against ideal values of 1 and 0.6. At 20 percent survival it takes 25 attempts to get one surviving pair; at 80 percent, about 1.6.

**Sources.** quantum_dot_bridge/results.json: classical_trap_pair_comparison, endpoints p = 0 and 0.5; collection_loss_sweep. PROTOCOL.md and independent_review.json. IBM: hardware_campaign/results.json, family_results.dot_frozen, run dots_plain_v1, 4,096 shots, 21 two-qubit gates. lab/research.js restates the formulas and lab/test_research.cjs holds them to these files.

### 25. A real quantum dot: published data, reanalysed.

**Show this when.** “Do you have any real optical data?”

These are external measurements, not ours: Hong-Ou-Mandel histograms of a GaAs quantum dot, published by Münzberg and colleagues under CC BY 4.0. We normalized central peaks to side peaks and applied the published splitter and multiphoton corrections. The visibilities are 0.80, 0.83 and 0.77 at the three delays. At 39.4 nanoseconds a different normalization gives 0.794 instead of 0.772, a shift larger than the counting interval. The lesson is that a source-quality number depends on the measurement controls. The intervals leave out polarization, routing and drift. We did not fit a QRSM to these histograms: they are aggregates, without the sequential records a fit would need. No microscopic cause is claimed.

**Sources.** quantum_dot_bridge/hom_analysis/results.json and PROTOCOL.md. Dataset doi:10.5281/zenodo.6337697, CC BY 4.0, by Julian Münzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil. Paper: APL Photonics 7, 070802 (2022). Their own quoted values, 0.803, 0.826 and 0.774, are kept separate.

### 26. Ignore the detector’s blind time, and the fit is wrong.

**Show this when.** “Could a detector artefact look like a defect?”

After a click the detector is blind for one step while the system keeps evolving. If the model leaves that out, it blames the hidden interaction for a correlation the detector made. On fresh synthetic records with a true coupling of 0.65, the fit gives 0.069 with the blind time ignored and 0.706 with it modelled. Prediction improves by 0.458 nats per 24-bin record. The corrected fit is still biased: dephasing sits at its upper bound and the efficiency is off. A trained hidden-Markov model captures the detector correlation too, so the corrected physical model’s edge over it is unresolved. This is synthetic inference, not a diagnosis of a real device.

**Sources.** qrsm_photon_poc/followup/README.md; inference_results/fixed_411101_dead1_fit0.json and fit1.json; independent_review.json. Paired interval for the 0.458 gain: 0.398 to 0.521. Corrected model against the HMM: −0.007 to +0.022 nats per record.

### 27. A QRSM for photon pairs: memory between pairs.

**Show this when.** “Did you build a model for the photon-pair case?”

Yes. Each photon is emitted into a shape that depends on the environment’s state. A controlled-swap parity check plays the role of the beam splitter. The environment is kept between pairs, so a record carries memory. Passive observation alone cannot separate a coherent environment from a classical one. With a calibrated control, the 64-pair simulation flags 5.6 percent of coherent records against 4.5 percent false flags, which is barely a difference. Four-pair circuits ran on IBM with 22 and 29 qubits. Their flag distributions were off by 0.25 and 0.29, so implementation noise is still large. None of this validates the optical assumptions or certifies quantum memory.

**Sources.** quantum_dot_bridge/qrsm_hom_followup/README.md, physical_model.py, circuits.py, main/results.json (regimes[1]) and main/independent_review.json. IBM: hardware_campaign/results.json, family_results.dot_selected_four_pair, 4,096 shots each, 256 and 334 native CZ gates.

### 28. More data helps only if the calibration holds.

**Show this when.** “Would more data fix it?”

Partly. With a selected control and resets between four-pair blocks, the share of coherent records flagged climbs from 12 percent at 64 pairs to 80 percent at 2,584 and 99.8 percent at 7,644, with about 5 percent false flags. That is a different preparation protocol from the 64-pair study, not a tuned replacement for it. But at 7,644 pairs a still-classical source is flagged 72 percent of the time if the collection efficiency changed, 53 percent if the mode overlap changed and 21 percent if the readout changed. An eight-state classical model predicts as well as the physical one, within uncertainty. More data cannot repair a wrong model of the measurement.

**Sources.** quantum_dot_bridge/qrsm_hom_followup/exploratory_design/README.md, VALIDATION_PROTOCOL.md and validation_run/results.json (power_trials). 2,000 records per cell. No validated physical control or reset time.

### 29. A better model costs more qubits.

**Show this when.** “How accurate is the model itself?”

The optical circuit keeps only two levels of its cavity. Against a six-level reference, its after-click predictions are off by up to 2.8 points, and 7.1 at stronger drive. Four levels cut that to 0.05 and five to 0.003. So more physics is available, at the price of more qubits and gates, and the cheap circuit answers a slightly different question. Six levels is a larger numerical reference, not the exact infinite model. The dynamics were cross-checked against QuTiP.

**Sources.** qrsm_photon_poc/followup/dynamics_results.json (cutoff: default and high_drive, max_conditional_difference_vs_dimension6) and README.md.

### 30. A calibration slip can reverse the conclusion.

**Show this when.** “Did the quantum sensor help?” or “What could go wrong with that monitor?”

The task is to catch a half-hertz step in a laser’s frequency within 32 seconds, without knowing when it happens. An ordinary reference alone caught 51 percent. Adding the atomic sensor raised that to 58. A second ordinary reference reached 98. Atoms alone caught under 8 percent. So the quantum add-on helped a little, and the ordinary route helped far more. Under stress it gets worse. With atoms that lose coherence sooner, adding them made the monitor worse than the reference alone. If the first reference itself steps, the first two monitors raise false alarms about 90 percent of the time. If the shared path steps, all three do, because that looks exactly like the laser moving. All of this is simulation.

**Sources.** laser_sensor_viability/followup/main/results.json and README.md: scenarios unseen_nominal_sessions, unseen_short_coherence, primary_reference_changes and common_sampled_path_changes; methods classical, classical_quantum, two_classical and quantum. 1,920 quiet and 1,920 faulty records per scenario, eight calibrated pipelines. The Lab’s Lasers tab replays one stored record of each (example_traces.json).

### 31. The laser monitor: what we assumed.

**Show this when.** “What did you assume about the atomic sensor?”

The atomic response follows driven Bloch rotations with decay, preparation error, readout error and projection noise for 64 independent atoms. Each one-second cycle gives one reading: two 2.5 millisecond pulses around a 20 millisecond dark time, then dead time. The conventional receivers include shot noise, electronics noise and reference drift. All monitors see the same task for the same duration. What is not matched is the equipment: reference lasers, cooling, trapping and readout are not costed. So this is not a resource-matched advantage test.

**Sources.** laser_sensor_viability/results.json (config, resource_ledger), model.py and README.md. Precedent for atomic laser-noise spectroscopy: Bishof et al., Phys. Rev. Lett. 111, 093604 (2013), arXiv:1303.6741.

### 32. The atomic channel, run as a circuit on IBM.

**Show this when.** “Did any of the sensing work run on a quantum computer?”

The atomic channel did, as a circuit. We built the full noisy evolution of the model atom, with its pulses, dark time and decay, and compiled it to four qubits and 22 two-qubit gates. IBM Marrakesh ran it with 2,048 shots per setting. The response goes the right way: 32, 48 and 73 percent measured, against 21, 50 and 79 percent in the model. It is biased, most at the outer settings. Superconducting qubits imitated the model. No atoms, no optical coupling and no 128-second monitor were tested. A separate two-photon circuit gave an occupation error of 0.033.

**Sources.** hardware_campaign/optical_controls/README.md, PROTOCOL.md and models.py; hardware_campaign/runs/optical_controls_plain_v1/analysis.json (job dbqat8nv5hds73dfnsig), rows atomic_d-5_Z, atomic_d+0_Z, atomic_d+5_Z and noon_phi0.35. Intervals are Wilson, shot noise only.

### 33. Drive amplitude: a negative result we keep.

**Show this when.** “Can the click record detect a change in the drive?”

Not in the regime we tested. We simulated 96-bin click records with a 20 percent jump in drive strength at an unknown time, and read the same bits three ways. The physical model caught 3.7 percent of jumps in time, a classical hidden-Markov model 3.1 and a simple count comparison 1.8. Each raised more false alarms than that on steady records. The amplitude estimate barely beats a guess that ignores the data: an error of 0.1125 against 0.1136. A 20 percent field step is a 44 percent intensity step, so this is a hard regime with few counts. The model needs a better operating point and calibrated detector dynamics before any monitoring claim.

**Sources.** qrsm_photon_poc/drive_diagnostics_followup/README.md; main/results.json (cases source_step_20pct and stable_source); main/prior_only_estimation_control.json; independent_review.json. 512 records per case, 6,656 in all. The prior-only control was added after the holdout and is descriptive.

### 34. Where the quantum part actually enters.

**Show this when.** “Where exactly is the quantum computer in the sensing story?”

In three different places, with different evidence. The sensor’s dynamics are quantum, and we ran that channel as a circuit on IBM. The diagnosis, turning readings into an alarm, is classical inference on synthetic records. The rare-history query is the quantum algorithm of the main talk, run on IBM. Running one component on a quantum computer does not make the whole pipeline quantum, and a sensing benefit would not be a computing speedup.

**Sources.** hardware_campaign/optical_controls/README.md and hardware_integration_review.json; laser_sensor_viability/model.py; LASER_DIAGNOSTICS_ROADMAP.md; hardware_campaign/coverage.json.

### 35. Sharper lines, paid for in photons.

**Show this when.** “How does this connect to making chips?” or “Is quantum lithography better?”

We simulated a strip of resist that needs two photons at once, under crossed beams. The fine stripes appear for laser light too. Entangled pairs give them about twice the contrast: 43 percent against 21 to 25. At each light’s best dose, pairs print 95 percent of scored cells correctly, two shifted laser exposures 78 and short laser pulses 83. Pairs also use the most light: 14.9 million photons against 0.84 million for the pulsed laser. Loss, a leakier resist, background or an unreliable pair source reverse the result. This is a sensitivity study of an assumed resist, not a prediction for any real material or printed feature.

**Sources.** quantum_lithography_poc/exposure_followup/README.md, model.py and results.json (case finite_nominal, best_threshold_accuracy). 800 nm beams at ±30 degrees: the 400 nm figure is a period, not a linewidth. lab/research.js reproduces the three rows to nine decimal places (lab/test_research.cjs).

### 36. The full question needs 389 qubits. We have 156.

**Show this when.** “Could your algorithm run on this problem today?”

No, and this slide says why. The rare event is a contact failing to print in a 49-cell exposure model, which happens in 0.42 percent of exposures. We built the reversible circuit that would amplify it: 196 qubits to count photons, 23 for the score and 170 spare, 389 in all. The device we used has 156. The gate count is an upper bound of about 3.4 million for one round. Both circuit files load back and pass structural checks, but the circuit was never simulated in full or run. Classical dynamic programming already solves this model. Building the circuit shows neither an advantage nor that the process works.

**Sources.** finals-lithography/full_spatial_circuit/README.md, results.json, process_bounds.py and independent_review.json. Floor and ceiling weights bracket the event: 0.004227 to 0.004237. Small versions that did run on IBM (hardware_campaign, family spatial) returned high hit rates with wrong answers.

### 37. Reading a phase: the benefit depends on the budget.

**Show this when.** “What about using quantum light to inspect rather than print?”

We simulated measuring one optical phase with 20,000 photons, charging every photon sent. Entangled pairs alone see a signal that repeats every half turn, so they pick the wrong half about half the time. Spending 10 percent of the photons on ordinary laser light fixes that, and the hybrid is slightly more precise than laser light alone: 0.0064 against 0.0079 radians. The benefit needs high efficiency. If the pair source succeeds 1 percent of the time, matching the dose takes 100 times longer. The comparison assumes ideal photon counting and a known reference, and it is not a claim over every classical design.

**Sources.** quantum_lithography_poc/phase_inspection_followup/README.md and results.json (case high_efficiency, budget equal_sample_photons; case one_percent_preparation). 2,000 outcomes per protocol; zero errors gives a 95% upper bound of 0.19%.

### 38. Lithography light is not our laboratory laser.

**Show this when.** “Does this apply to real lithography machines?”

Not directly, and we should say so. In an EUV machine a carbon-dioxide laser heats tin into a plasma, and the plasma emits the 13.5 nanometre light that exposes the wafer. Deep-ultraviolet machines use a 193 nanometre excimer laser. Our sensor study uses a narrow 698 nanometre laboratory line that atoms can read. None of the industrial sources is represented in our model. Conventional source monitoring already exists, and Cymer and imec have linked source changes to feature sizes on wafers. That motivates source metrology in general. It is not a yield claim for our sensor.

**Sources.** LASER_DIAGNOSTICS_ROADMAP.md. ASML: asml.com/en/technology/lithography-principles/light-and-lasers. Cymer and imec, SPIE Advanced Lithography 2014. Bishof et al., arXiv:1303.6741.

### 39. The cinematic cut. 45 seconds.

**Show this when.** You want the optional cold open, or a judge asks to see the video.

The team's problem-first video with original music. It is a cinematic explainer, not a screen recording of the product. Click once to play. If you open the talk with it, stop the Lab video on slide 10 at 41 seconds, or use the 45-second version.

**Sources.** media/cinematic-45s.mp4, from the team's cinematic kit. Numbers shown match hardware_campaign/RESULTS.md.

### 40. Our machine, asked three fields’ question.

**Show this when.** “What do the three follow-up studies have to do with your method?” or “Did anything about chipmaking run on real hardware?”

We asked our own machine the question those fields share: after a rare event, is it a one-off, or is something hidden remembering? In the machine that is two readings after a rare click: does a second click follow within three steps, and where was the hidden defect. A two-photon resist prints on pairs of photons, so the first reading is its pair dose: exactly 8.5 percent with the hidden defect and 17.4 without, which makes pairs 5.2 times rarer. On IBM, plain sampling of the rare click got that order backwards in both runs, 47 against 34 percent on 12 November, because half or more of its rare events were noise. Rewinding made the click three shots in four and got the order right in both runs: 16.8 against 21.0 percent. The gap is about half the true one. For lasers we stepped the hidden defect’s frequency: the second click rose from 16.8 to 21.0 percent, against an exact 8.5 to 14.2. For photons, g2 right after a photon read 0.54 against 0.32: the right order, about twice too high. Be straight about the limits: this is a toy with two memory qubits that a classical filter solves exactly, rewinding runs a model inside a quantum computer and cannot rewind a real laser or wafer, and the photon g2 three steps on told the machines apart on 11 November but not on 12 November.

**Sources.** applied/results.json and applied/README.md. Raw counts in hardware_campaign/runs/original_precision_v1, original_plain_v2 and applied_v1. Tests: applied/test_applied.py.

### 41. Written down first: every direction held.

**Show this when.** “How do you know the hardware bias is noise and not your method?” or “Did you predict anything before you ran it?”

Before the 12 November job we froze its thirteen circuits and wrote down what IBM should return, using a noise model fitted only to two echo circuits from 11 November. Every predicted direction held, including the uncomfortable one: plain sampling would get the chip answer backwards. We predicted minus 8.3 points and measured minus 13.1. For the frequency step we predicted plus 3.7 points and measured plus 4.2, inside the interval. For the rewound chip gap we predicted plus 1.3 and measured plus 4.2: right direction, too cautious. Three of the five predicted sizes are inside their intervals. Two honest caveats. The predictions assumed the qubits and calibration of 11 November, and the job ran on different qubits. And they were written twelve minutes before submission in the same working session, not published anywhere first, so this is our own record and not an independent preregistration.

**Sources.** applied/predictions.json (hash-tied to applied/hardware_bundle and predictions_isa.qpy), hardware_campaign/runs/applied_v1/, applied/results.json under new_job.
