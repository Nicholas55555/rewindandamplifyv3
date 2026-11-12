# Design log: FGCU Quantum Hackathon project

Newest entries at the bottom. Expectations are written before the runs they predict.

## 31 Oct 2026, 18:00: the plan

**The request** (approved by the user: "Yes, go ahead"; finalised in this session). Build the hackathon project: a quantum recurrent state machine (QRSM) that learns a quantum device's hidden defects from its detector clicks, built and run in Qiskit.
1. v5 experiment 4's system as a Qiskit dynamic circuit, checked against v5's exact filter.
2. Click records from the perfect simulator, a noisy IBM device simulator, and later real IBM hardware (only with the user's own account).
3. "Who finds the hidden defect?": v5's physics-shaped search, the free-unitary black box and an LSTM.
4. A write-up and a short deck for AI/ML judges.

**The user's answers (31 Oct, 18:02):**
- the deadline is about a week from the 30 Oct kickoff, so about 6 Nov;
- prior work and AI help are allowed if disclosed;
- they have teammates;
- they already have an IBM Quantum account.

**Ground rules kept:**
- v1-v6 are only read: Python runs with `-B`, and v5's code is imported by path.
- Circuits run in v6's Qiskit environment (qiskit 2.6.1, qiskit-aer 0.18.2, qiskit-ibm-runtime 0.51.0); nothing was installed into it. Fitting runs in v1's environment (torch). Data pass between them as `.npz` files.

## 31 Oct, 18:10: experiment 1, the circuit

**The circuit** ([experiments/1_qrsm_circuit.py](../experiments/1_qrsm_circuit.py)). Three qubits: emitter, defect, light. Each step:
- RY(0.6) on the emitter;
- RZ(0.3) on the defect;
- v5's exchange, a real Givens rotation by phi = 0.45, built as CX, CRY(2 phi), CX;
- the emission: CRY(2 alpha) then CX, with sin(alpha)^2 = 0.2 (the Givens rotation's first CX never acts, since the light was just reset);
- measure the light into the step's click bit, then reset it.

**The pass marks were fixed in the check script before it ran** ([checks/1_circuit_checks.py](../checks/1_circuit_checks.py)):
- the step's Kraus operators equal v5's to 1e-12;
- for the perfect simulator: no step's click rate more than 3.5 standard errors from the exact one, a gap-distribution chi-square p above 0.001, and the mean log-likelihood at the truth within 3 standard errors of its value on records drawn from v5's exact filter.

**The noisy device:**
- FakeMarrakesh, a 156-qubit Heron r2 snapshot from qiskit-ibm-runtime, chosen because open-plan accounts run on Heron devices;
- transpiled at optimization level 3 (seed 7) and scheduled ALAP, so idle qubits get delays;
- Aer's noise model from the backend adds T1/T2 relaxation to those delays, as well as gate and readout errors.

**The readout is calibrated the way a lab would, not read from the backend's tables.** A 64-step circuit with the experiment's timing prepares the light in a known pattern, measures it and resets it, over 1,024 shots.

**Results (18:12-18:14):**
- **The step matches v5 exactly:** the Kraus operators differ by 0.0.
- **The perfect simulator's clicks pass every test,** with 0 and 1 defects and with a perfect or good detector:
  - largest step z: 2.1-2.5;
  - gap p-values: 0.17-0.87;
  - likelihood z: +0.3 to +1.1.
- **The noisy device's clicks fail all three, as they should:**
  - device-k1: likelihood z +26, gap chi-square 454 on 21 degrees of freedom, and a click rate of 0.091 against the ideal 0.084;
  - device-k0: z +16.
- **The transpiled step:**
  - 4 CZ for 1 defect: 2 for the exchange and 2 for the emission;
  - 5.6 microseconds per step, almost all of it the light's measurement and reset.
- **The transpiler chose physical qubits 13 (emitter), 12 (defect) and 14 (light).**
  - Over a step's 5.6 microseconds, their T1 and T2 imply relaxation chances of 2.1% (emitter) and 2.5% (defect), and coherence factors of 0.985 and 0.970.
  - So the device's own noise makes, by itself, v5 experiment 4's "slightly wrong model": relaxing defects, at almost v5's 2% per step. It adds dephasing and gate errors on top.
- **Readout calibration:** P(1|0) = 0.0042 and P(0|1) = 0.0041, which is efficiency 0.996 and dark counts 0.0042 per step in v5's terms.
- **Cost:** 29 s for all the records, and 36 s for the checks.

## 31 Oct, 18:35: experiment 2, "who finds the hidden defect?", expectations before the full run

**Datasets** (8,704 records of 64 steps each: 4,096 training, 512 validation, 4,096 counting):
- ideal-k1-perfect;
- ideal-k1-good: v5's good detector, efficiency 0.5 and dark counts 0.005, applied afterwards;
- ideal-k0-good: no defect, the control for counting;
- device-k1;
- device-k0: no defect on the noisy device, the control for false defects.

**Learners:**
- **The physics-shaped QRSM** with v5 experiment 5's search, called unchanged: 0, 1 and 2 defects, gamma and the detector known.
- **The physics shape plus decoherence:** a relaxation and a dephasing chance per step for the emitter and each defect, started from the search's fit of each size and polished with full-batch L-BFGS.
- **The free-unitary black box** (v5's FreeHybrid, D = 4: 128 numbers), trained as v5 trained it: 2 learning rates and 3 seeds.
- **An LSTM** next-click predictor: hidden sizes 8, 32 and 128, learning rates 0.003 and 0.01, 2 seeds each. The configuration is chosen on the validation records, with early stopping.

**Data efficiency:** the physics search and the LSTM also train on 256 and 1,024 records of ideal-k1-good.

**Scoring** (all on the 4,096 counting records):
- **log loss;**
- **"share left":** the loss above the truth's, as a share of a memoryless predictor's loss above the truth. This needs the truth, so it is for the ideal data only; under 5% counts as found, as in v5;
- **counting:** experiment 5's rule, the smallest size within 2 standard errors (or 1 nat) of the lowest loss;
- **errors** against Cramer-Rao standard deviations.

**Expectations, written before the full run:**
1. **Ideal data, physics search:** found on ideal-k1-perfect and ideal-k1-good, every number within 3 sd, and the count right on all three ideal datasets. v5 experiment 5 found these 6 of 6 on fresh copies, so I'm confident (90%).
2. **The free unitary:** found in 0 of 18 runs, with share left above 20%. v5 found it in 0 of 48.
3. **The LSTM, ideal data, 4,096 records:** the best configuration leaves 1-10% on ideal-k1-perfect. It predicts fairly well but not as well as the physics fit (v5's fits left 0.01-0.5%), and it gives no physical numbers.
4. **Data efficiency on ideal-k1-good:**
   - at 1,024 records, the physics search is still found and the LSTM leaves at least 3 times as much;
   - at 256 records, the LSTM leaves 20-60%, and the physics search is about even odds to be found.
5. **Device data, physics only:**
   - **device-k1:** at least one number more than 3 sd off. v5's relaxing defects at 2% gave 2-3 sd; here dephasing and gate errors come on top. The count is 1 (60%) or 2 (40%): extra noise can make a second defect look worthwhile.
   - **device-k0:** count 0 (70%). The emitter's own decoherence might be taken for a defect (30%).
6. **Device data, physics plus decoherence:**
   - every shape number within 3 sd (65%);
   - the count right on both device datasets (70%);
   - the fitted relaxation per step within a factor of 2 of the device's T1 value, 0.021 for the emitter (75%) and 0.025 for the defect, which is seen only through the emitter (55%).
7. **Physics plus decoherence on ideal data:** fitted noise under 0.005 per step, and no gain on held-out records beyond 2 standard errors.
8. **Prediction on device data:**
   - the LSTM predicts held-out device-k1 clicks better than the physics-only fit (70%), since a flexible black box beats a wrong physics model at prediction;
   - the noise-aware physics fit ties or beats the LSTM (60%).

**Timing:**
- The quick pilot's search took about 5.5 minutes on 5 workers, because the polish always uses all 4,096 training records.
- From v5's timings, the full search should take about 8 minutes per dataset for 0-1 defects and 20 more for 2. That's about 110 worker-minutes, or 25-30 minutes on 5 workers.
- The full timing is pending the pilot's other pieces.

## 1 Nov, 13:07: the full run of experiment 2 starts (the user: "Run both (~1 hour)")

**Changed after the quick pilot, before the full run:**
- **The noise-aware polish is slimmer.** It was 2 starts of 120 L-BFGS evaluations each; it is now one start at 0.02 per step, with 60 evaluations (40 at 2 defects).
  - One full-batch evaluation takes about 2 s at 1 defect and about 15 s at 2. The pilot's 2-defect noise-aware fits would have taken about an hour each.
  - The 2-defect noise-aware fit runs only on device-k1, where the counting needs it.
  - Cramer-Rao standard deviations are computed only at the true size.
- **The LSTM grid is set by timing.**
  - One run at hidden size 128 took 8.5 min on one core and stopped at step 2,450. It reached 0.2692 nats per step on ideal-k1-perfect's held-out records. Hidden size 8 took 39 s and reached 0.2719, still improving at the 4,000-step cap.
  - The grid is now hidden sizes 16 and 64, at learning rates 0.003 and 0.01, with 1 seed, on ideal-k1-perfect, ideal-k1-good (and its 256- and 1,024-record subsets), device-k1 and device-k0.
  - Hidden size 128 at 0.003 runs on ideal-k1-perfect and device-k1 only.
  - The LSTM is dropped on ideal-k0-good, since the counting control doesn't need it.
- **That timing run already bears on expectation 3.** The truth's loss on these records is about 0.266 and the memoryless one about 0.279. So the hidden-128 LSTM leaves roughly 20-25%, not the 1-10% I expected. Expectation 3 stands as logged, but it was seen to be off before the full run.

**Estimated:** search about 30 min, then noise-aware fits, the free unitary and the LSTM about 30 min, on 5 workers.

## 1 Nov, 14:05: first results of the search and noise-aware pieces, and a diagnosis (logged while the learners run)

**The search piece took 43 minutes, not 30:** the 2-defect searches took 30 minutes each under full load.

**Physics only:**
- **The perfect simulator:** the physics shape finds the truth on every dataset.
  - Errors are 0.0002-0.0045 rad with the perfect detector and 0.002-0.008 rad with the good one.
  - From only 256 records the errors are 0.04-0.10 rad.
  - 2 defects tie 1 on both 1-defect datasets.
- **device-k0 (no defect):** the 1-defect fit invents a weak defect (phi = 0.064) and wins by about 290 nats on the counting records, so the count would be 1 where the truth is 0.
- **device-k1:** the drive is 0.031 rad high, and a weak second defect (phi = 0.066) wins by about 300 nats, so the count would be 2 where the truth is 1.

**Physics plus decoherence (relaxation and dephasing per memory qubit):**
- **The counting is fixed on both device datasets.**
  - device-k0: 0 and 1 defect tie, and the extra defect's phi goes to 0.000.
  - device-k1: 1 and 2 defects tie, and the second defect's phi goes to -0.006.
- **On ideal data,** no noise is invented (at most 0.0003 per step) and nothing is gained. Expectation 7 holds.
- **device-k1's errors in standard deviations:**
  - physics only: theta +12.5, phi -3.8, zeta -4.5;
  - with decoherence: theta +6.9, phi -3.5, zeta -0.1.
- **So zeta is fixed and the drive stays 0.031 rad high.** The worker's own standard deviations were all nan, because noise chances at zero make the full Hessian singular. They were recomputed in the report with those chances held at zero.
- **The fitted noise doesn't match the device's.**
  - Relaxation: emitter 0.032 against the device's 0.021; defect 0.000 against 0.025.
  - Dephasing: emitter 0.000 against 0.008; defect 0.086 against 0.035.

**Diagnosis.** Scored on device-k1, "the true angles plus the device's own T1/T2 noise" is worse than the fit by 149 nats on the training records and 156 on the counting records. So this is not a search failure: the model is missing a noise process, and the drive's bias stands in for it.
- **The candidate is the CZ gate errors:** 0.10-0.12% per gate on these qubits, 4 per step. An error in the exchange or the emission can flip the emitter. An error in the emission can also flip the light, which acts as an extra dark count or a missed click.
- **The readout calibration can't see that,** because its circuit has no CZ.

**Expectations for a third noise-aware model,** with one depolarizing chance per memory qubit added and the dark-count rate fitted instead of fixed by the calibration, warm-started from the decoherence fit:
- it beats the decoherence fit on the counting records by more than 20 nats (60%);
- theta comes within 3 sd of the truth (50%);
- the counts stay right on device-k0 and device-k1 (80%);
- on ideal-k1-perfect, it invents no depolarizing or extra dark counts (under 0.001) (85%).

## 1 Nov, 15:10: experiment 2's results against the expectations

**Cost:**
- The main run took 106 min against the estimated hour, and the gate-error fits 14 min more.
- The 2-defect searches took 30 min each, not 20, and the hidden-128 LSTMs took 22-31 min under load, against 8.5 min alone.
- The report was rerun separately, because the running job's copy of the experiment-2 code predated the gate-error model.

**Against the expectations:**
1. **Ideal data, physics search: holds.**
   - Found on both 1-defect datasets, with share left 0.00% (perfect detector) and 0.10% (good detector).
   - Every number is within 1.6 sd.
   - The count is right on all three ideal datasets.
2. **The free unitary: holds.** It was found in 0 of 12 runs on ideal data, with share left 40-91%.
3. **The LSTM at 1-10% left: wrong.** The best configuration, chosen on validation, leaves 17.0% (perfect detector) and 17.4% (good detector). The best of all runs on held-out is the same.
4. **Data efficiency: holds at 1,024 records. At 256, the physics fit was not found.**
   - At 1,024 records the physics fit is found (0.65%), while the LSTM leaves 31.5%, about 48 times as much.
   - At 256 records the LSTM leaves 37% (inside the expected 20-60%). The physics fit leaves 17%: not found, against even odds.
   - The physics fit with 256 records predicts as well as the LSTM with 4,096.
5. **Device, physics only:**
   - device-k1: theta is +12.7 sd off, and the count is 2. That was the 40% branch.
   - device-k0: the count is 1, a false defect. That was the 30% branch.
6. **Device, plus decoherence:**
   - the counts are right on both: holds;
   - every number within 3 sd: fails (theta +6.9 sd, phi -3.5 sd);
   - emitter relaxation within a factor of 2: holds (0.032 against 0.021);
   - defect relaxation within a factor of 2: fails (0.000 against 0.025, with dephasing taking its place).
7. **Ideal data, plus decoherence: holds.** The noise comes out at 0.0002 per step at most, with no gain.
8. **Prediction on the device: both hold.**
   - The LSTM beats physics only: gaps to the best learner of 0.034 against 0.170 nats per record.
   - The noise-aware physics fits beat the LSTM: 0.007 with decoherence, and 0 with gate errors (the best learner).
   - The free unitary sits at 0.071.

**The gate-error model** (expectations logged at 14:05): all four hold.
- It beats the decoherence fit by 29 nats on the counting records (gap 0.007 +- 0.002 per record).
- device-k1's errors are theta +0.0082, phi -0.0013 and zeta -0.0059 rad, which is +1.3, -0.4 and -0.9 sd.
- The counts are right on both device datasets.
- On ideal-k1-perfect it invents nothing: depolarizing 0.0000, and dark counts 0.0003 per step against a truth of 0.
- The fitted dark-count rate is 0.0080 +- 0.0008, against the calibration's 0.0042. That fits gate errors flipping the light during the emission, which the calibration circuit can't see.

**Not pinned:** how the device's noise splits.
- The defect's dephasing comes out at 0.031 against the device's 0.035, but its 2-sd interval is 0-0.08.
- The defect's relaxation appears as depolarizing (0.018) instead of relaxation (0.000).
- Emitter relaxation is 0.007 +- 0.013, against 0.021.
- So the clicks pin the defect's coupling and detuning once the noise is in the model, but not the noise's own parts.

**Caveats:**
- The gate-error model was added after seeing the device results and was tested on the same device records. Fresh device records, or real hardware, are the honest test.
- One device snapshot (FakeMarrakesh), one dataset per case, and one LSTM seed per configuration.

## 3 Nov, 13:30: a team pack and a tidier folder (no results changed)

The user asked for a better-organized folder, with a PowerPoint and other resources for the team.
- **Added:**
  - `START_HERE.md`, a map of the folder;
  - `team/`: the deck as an editable PowerPoint with the same speaker notes, its PDF, a team guide, and the charts as pictures;
  - `tools/`, the scripts that build all of these and the zip.
- **How:**
  - the PowerPoint is built by driving the laptop's own PowerPoint, so nothing was installed;
  - the guide's PDF is printed by Edge, because Word stopped at a hidden prompt when saving;
  - the PowerPoint uses Arial and Calibri, since the online deck's fonts aren't on this laptop.
- **Unchanged:** the experiments, the checks and the results. The code folders kept their places, since the scripts find their data by path.
- **The zip** now has short paths: the fit files' long names went past Windows' 260-character limit.
