# Rewind & Amplify: the report

**FGCU Quantum Hackathon, IBM Qiskit Fall Fest, November 2026.** For a plain-English version, see the [one-pager](ONE_PAGER.md). For the order things happened in, and what was predicted before each run, see the [design log](design_log.md). Every number below is in [`results/numbers.json`](../results/numbers.json).

## Summary

We fused Grover's algorithm with a quantum recurrent state machine (QRSM), and redesigned it around noise.

- **The obstacle is reversibility.** Grover has to run the machine backwards, and a QRSM resets a qubit every step. Replacing each reset with a fresh qubit makes the run one unitary A, with A|0> = sum over y of |m_y>|y>: every click history at once, with weight sqrt(P(y)). This changes no statistic (largest amplitude error @@AMP@@).
- **Grover then conditions exactly.** On real Qiskit circuits it follows sin^2((2r+1) theta) within @@CURVE@@, and it leaves the conditional distribution and the hidden state exact.
- **Rarity splits in two.** A click is rare because the memory must be excited, and because it must emit. The second factor is one gate angle, and tuning it is exact and free. Grover is only needed for the first. On a real 64-step record, the cost per conditioned sample goes from 27,495,891 runs, to 6,240 by steering, to 125 calls with Grover on top.
- **The reflection needs far less than every qubit.** Watching the hidden memory and the light the question reads is nearly exact on short records, at 3 qubits for any length. Watching only the memory, our first idea, scrambles the hidden state.
- **Under noise, the resilient build beats textbook Grover.** Across five IBM device snapshots it used @@RATIOMIN@@ to @@RATIOMAX@@ times fewer two-qubit gates, with a higher hit rate in @@HITWINS@@ and a lower distribution error in @@TVDWINS@@ of cells.
- **It held up on real chips.** On ibm_kingston, steer + local won @@HWWINS@@ comparisons across five jobs. In the first job it hit a rare event @@HWFIRSTR@@ of the time on 40 two-qubit gates, against @@HWFIRSTB@@ for textbook Grover on 213. The after-click fingerprint came through at about 6 standard errors in three unsuppressed jobs on two chips. The chips also showed what simulation couldn't: depth costs about 3 times more per gate than the noise model says, and the calibration data can hide a bad patch of qubits.
- **There is no speedup today.** An exact classical sampler gives a sample in about a millisecond at this size, and beats all of this. The core idea, amplified rejection sampling, is from 2014.

## 1. The machine

The QRSM is the one from our [hidden-defect project](../prior_work/hidden_defects/README.md): an emitter, driven by RY(theta), and a defect that turns by RZ(zeta) and exchanges energy with it by phi. The emitter emits into a light with chance gamma = sin^2(alpha). The defaults are theta = 0.6, gamma = 0.2, phi = 0.45 and zeta = 0.3. Each step costs 4 CZ on IBM Heron. Two hidden qubits hold the memory, and the light's measured bit is the click.

In the terms of our circuit diagrams it is the constrained hybrid, in emitter form: a fresh ancilla, the light, swaps partly with memory 1, the emitter, and is reset, and memory 2, the defect, never meets it. It is not the trainable hybrid or the free-unitary hybrid. Purifying it (section 2) defers the resets, so the circuit Grover runs on is fully coherent, which is what lifts the limit our Grover memory-access note put on hybrids.

![One step of the hybrid QRSM as a circuit: drive, detune, exchange, emit, read and reset](../results/figures/fig_circuit_hybrid.png)

As a model it is a hidden quantum Markov model (Monras, Beige and Wiesner). Its step has two Kraus operators, K_0 and K_1, and P(y) = ||K_{y_T} ... K_{y_1} |0>||^2.

**Why condition at all?** Fitting to a recorded sequence, predicting the next click, and asking what follows a rare event are all conditional questions. On hardware, a generator answers them by rejection: keep the runs that match. That costs 1/p runs. Our own circuit diagrams note already flagged this as the wall.

## 2. Why Grover doesn't drop in

Our [research note](../README.md) gave three warnings, and each needed an answer.

| warning | answer |
|---|---|
| A reset can't be inverted | Purify: fresh lights, nothing measured until the end (section 3) |
| A hidden state isn't addressable memory | Search what the state really holds: its click histories, not stored records |
| A query speedup isn't a time speedup | Count machine calls and two-qubit gates throughout, and redesign around them (sections 6 to 9) |

## 3. Move 1: purify (E1)

By the deferred-measurement principle, swapping each reset for a fresh light can't change the click statistics. The pass marks were fixed before the run.

| check | result | pass mark |
|---|---|---|
| A\|0> against the Kraus branches, 0 to 2 defects, T up to 12 | largest amplitude error @@AMP@@ | 1e-12 |
| dynamic circuit against purified circuit on Aer, 1,000,000 shots each | chi-square p = @@CHI@@ | above 0.001 |
| A then A-inverse | returns to the start with probability 1.000000000000 | |

## 4. Grover on the histories (E2)

One iteration is Q = A R₀ A† O. The oracle O flips the sign of matching histories, and for a click at one step it is a single Z gate. A† rewinds the machine, R₀ flips the sign of all zeros (X gates, a multi-controlled Z, X gates), and A replays it. So each iteration costs two machine calls.

![The Grover circuit: A, then the oracle, A dagger, R zero and A, repeated r times, then measurement](../results/figures/fig_circuit_grover.png)

With Qiskit's `grover_operator`, A as the state preparation and a phase oracle on the click register, on six questions at T = 6:

| check | worst over all questions and iterations | pass mark |
|---|---|---|
| hit rate against sin^2((2r+1) theta) | @@CURVE@@ | 1e-9 |
| distribution inside the marked set against P(y given marked) | @@CONDTVD@@ | 1e-9 |
| hidden-qubit populations against the exact filter | @@POP@@ | 1e-9 |

![Grover's curve on three questions](../results/figures/fig_curve.png)

**Amplification reweights, and does not reshape.** Inside the marked set the relative amplitudes never change. So an amplified shot is an exact conditional sample, hidden memory included.

**Recurrent oracles.** A question read by a small automaton can be marked by a reversible reader that keeps a running count. That is a coherent QRSM in the oracle slot. For "at least 2 clicks", a lookup-table oracle takes 2^T - 2 two-qubit gates, while the reader's cost grows about linearly in T. It costs more up to about T = 10, and less after: 864 against 4,094 at T = 12. The tests check that it marks the same histories and leaves its counter clean.

## 5. Scaling, and the classical baseline (E3)

Exact simulation at T = 18, out to p = 3e-7:

| method | slope of log(calls) against log(p) | predicted |
|---|---|---|
| plain sampling | @@SLOPE_R@@ | -1.00 |
| Grover, p known | @@SLOPE_A@@ | -0.50 +- 0.02 |
| Grover, p unknown (BBHT) | @@SLOPE_B@@ | -0.5 +- 0.1 |

Each iteration counts as two machine calls. With p unknown, BBHT costs a median of @@BBHT@@ times the known-p cost.

![Calls per conditioned sample against rarity](../results/figures/fig_wall.png)

**The strongest classical baseline wins here.** A backward sampler uses an operator-valued message B[t][s], the sum over accepted futures of K-dagger K, to draw exact conditional samples with no rejection at all. It takes about a millisecond per sample at n = 2 hidden qubits. Its set-up time grew @@GROWTH@@ times per hidden qubit at the largest sizes we ran (8 in theory), reaching @@N11@@ s at n = 11. Every quantum number in this report is beaten by this at this size. It matters only because it runs out.

## 6. Noise: what goes wrong

**Hit rate alone is a trap.** "Any click" at T = 3 scores 87.5% from pure noise, since 7 of 8 random bitstrings qualify. So every noisy result here also reports the conditional distribution's distance from the truth (TVD), and we use overshoot, the hit rate falling past the peak, as a coherence check that noise alone can't fake.

**Rare events hide under the noise floor.** At p = 0.00105, plain sampling on the FakeMarrakesh noise model reads 0.0029: 2.8 times too high, from false clicks.

**Textbook depth is expensive.** A 5-qubit multi-controlled Z costs 49 CZ on heavy-hex, or 27 with clean ancillas. Textbook Grover at T = 5 compiles to 456 CZ. At 0.2% error per gate, about 40% of those runs finish with no gate error.

## 7. Move 2: steer

A click's Kraus operator is K_1(gamma) = sin(alpha) |0><1| on the emitter, times the rest of the step. So the click operator at any emission strength is a constant multiple of the machine's own: K_1(gamma') = sqrt(gamma'/gamma) K_1(gamma). Changing the emission at step t therefore scales **every** history that clicks at t by the same constant. Conditional distributions and hidden states can't change, and p rises to p gamma'/gamma.

We found this by accident. Rewinding one step and watching one light gave TVD 0.000 and fidelity 1.000 at every T, with a boost of 4.8. An exact result from a crude cut needs an explanation, and that is it: K_1 has a single non-zero singular value, so amplifying it is perfectly uniform, and r iterations simply turn alpha into (2r + 1) alpha. No Grover is needed for that part.

So rarity has two factors: an **emission factor**, which a gate angle removes exactly, and a **population factor**, which is Grover's real job. This is the idea in section 07 of our research note: concentrate useful probability first, and use interference only for the rest.

**Tune p to 1/4 and one iteration gives certainty,** since sin^2(3 pi/6) = 1. At T = 5 to 14: hit 1.000, TVD 0, fidelity 1.000, in one iteration where textbook needs 2 or 3. At T = 3 and 4, full steering reaches p' = 0.20, and one iteration gives 0.965 and 0.972. It is forgiving: p' from 0.18 to 0.32 gives at least 0.94, so a rough estimate of p is enough.

**On a real record.** Over 4,096 held-out 64-step records of the hidden-defect machine, with a median of 5 clicks:

| build | calls per conditioned sample | two-qubit gates, as a scale estimate |
|---|---|---|
| plain sampling | 27,495,891 | |
| steering every clicked step | 6,240 | |
| Grover alone | 8,237 (r = 4,118) | about 2.7 million |
| steering, then Grover | 125 (r = 62) | about 40,000 |

**Credit where it's due.** Steering is classical importance sampling. It gives about 4,400 times, and Grover about 50 times on top. A fair baseline must include it, so this table does.

**Limits.** It is exact for clicks at known steps. "Any click" can't be steered exactly, because no-click steps have a non-uniform operator. And it relies on the physics-shaped model: a free-unitary QRSM has no such structure.

## 8. Move 3: amplify locally (E4, E4b)

The textbook reflection flips the sign of |0...0> over every qubit. We asked what happens if it looks at only some of them. One iteration of Q' = -A S' A-dagger S_f from A|0> gives exactly

    Q'|psi> = (1 - 4p)|psi> + 2|g> - 4 A|l>

where |g> is the marked part of |psi>, and the **leak** |l> is the part of the rewound marked state that the reflection can't see, with the |0> component removed. The tests check this formula. The leak predicts the damage: across 40 cells, its Spearman correlation with the share of the gain lost at r = 1 is @@SPEARMAN@@.

**Memory only: our first idea, and its flaw.** Watching the 2 memory qubits costs 1 CZ, and it kept a median of @@KEPT@@ of the gain for single-event questions, with the worst TVD at @@WORSTTVD@@. On noisy devices at r >= 2 it had a lower TVD than textbook in @@MEMTVD@@ of cells, and a higher hit rate in @@MEMHIT@@. It lost the hit rate almost everywhere at r = 1 (it won @@MEMHIT1@@). For rare multi-click questions it fails: at p = 0.001 the peak is 0.28, not 1.

**Then E5 caught something hit rate could not.** Run past a click, the memory-only build gave conditional click rates of [0.091, 0.029, 0.009] where the truth is [0.018, 0.058, 0.101]. It keeps roughly the right histories and scrambles the hidden state they leave. Mean memory fidelity is only 0.70 to 0.89.

**The fix: watch the question's light too.** The biggest leak term is the light the question marks. With that watched, what's left needs an earlier click as well, so it is second order in the click rate. For "a click at step t" this is 3 qubits, whatever T is. Conditional click rates agree to 1e-4 at t = 3, and memory fidelity is at least 0.997 for T up to 4.

![What each reflection keeps](../results/figures/fig_reflection_map.png)

As predicted, it degrades on long records, where earlier clicks become likely. At T = 12 and r = 3 its TVD reaches 0.30. For long records, watching all the lights does better (hit 0.945 at T = 12, steered), but that gate grows with T.

**The saving exists only for local questions.** "Any click" reads every light, so its question-local reflection is the full one.

**On noisy devices,** against textbook at r >= 2 and T up to 5: @@LOCALAGAINSTFULL@@. Against memory only: @@LOCALAGAINSTMEM@@.

## 9. The resilient build (E7)

Purify, steer to p' = 1/4, one iteration with the local reflection, and verify by measuring. On five IBM device snapshots, none of them the one the idea was developed on, compiled and scheduled for each device, 32,768 shots per cell:

@@HEROTABLE@@

![The resilient build against textbook Grover](../results/figures/fig_resilience.png)

Against textbook, in @@CELLS@@ cells: a median of @@RATIO@@ times fewer two-qubit gates (range @@RATIOMIN@@ to @@RATIOMAX@@, the lowest at T = 6, where textbook needs only r = 2), a higher hit rate in @@HITWINS@@, and a lower TVD in @@TVDWINS@@. Plain sampling has the lowest distortion of all, but keeps only 5 to 9% of its shots.

**A cheaper, slightly wrong circuit beats the exact one,** because the error it adds is smaller than the noise it avoids. On a much less noisy machine that stops being true, and textbook wins.

**What better hardware does.** The five snapshots span a 3-fold range of two-qubit error. At T = 5 the resilient build's lead in hit rate is @@LEADWORST@@ on the noisiest device and @@LEADBEST@@ on the best.

![T = 5 on five devices, ordered by two-qubit error](../results/figures/fig_device_trend.png)

## 10. Grover inside the loop (E5)

Section 06 of our research note asks to insert retrieval at selected timesteps. So: amplify "a click at step t", then keep running on fresh lights. Each surviving shot is a sample of what the machine does after that event.

That query is physical. P(click at t + tau | click at t), divided by the plain rate, is the correlation g2(tau). A two-level emitter can't click twice at once, so g2 starts low. With no defect, a click wipes the machine, so the clicks that follow simply restart the run: the conditional rates are exactly the start-of-run rates. A hidden defect remembers across the click.

![The fingerprint of hidden memory](../results/figures/fig_fingerprint.png)

With the full reflection the circuit gives the filter's answer to @@E5WORST@@. On noisy devices at 4,096 shots (click at step 3, tau = 1 to 3):

| | plain sampling | steer + local, r = 1 |
|---|---|---|
| usable shots, one defect | @@KEPTP1@@ | @@KEPTA1@@ |
| RMSE of the click rates, one defect | @@RMSEP1@@ | @@RMSEA1@@ |
| RMSE of the click rates, no defect | @@RMSEP0@@ | @@RMSEA0@@ |
| separation of defect from no defect at tau = 3, in standard errors | **@@SEPP@@** | **@@SEPA@@** |

![Click rates after a click on noisy devices](../results/figures/fig_after_click.png)

Both estimates are biased upward by false clicks, the amplified one less so. At tau = 1 the truth is below the noise floor for both, and the separation there is weak. This is the clearest case where the design pays today, in simulation: at equal shots it answers a question that plain sampling can't.

## 11. The other slot: a reader QRSM as the oracle (E6)

Amplitude amplification has two slots: what to search over, and what counts as a match. So far a QRSM has filled the first. Timofey's idea, retrieving data from a vague human search, fills the second.

1. **Classical.** A vague request becomes catalogue keywords, by stop words and a synonym table. A real system would use an embedding model here.
2. **Reader QRSM.** The index register holds every entry at once. Each token applies one diagonal step, which turns the phase of each entry containing it. This is the phase-layer QRSM from our circuit notes. It can't reset, and doesn't need to.
3. **Grover.** A full match reaches phase pi, a normal mark. A partial match gets a partial phase, and the first iteration multiplies its probability by about 5 - 4 cos(phase). So one circuit ranks partial matches, which is what makes a vague search possible.

![Keyword search](../results/figures/fig_catalog.png)

| measure | result |
|---|---|
| top-1 accuracy, 20 vague requests, 16 entries | 19 of 20, the same as the classical score. The one miss is the tokeniser, which maps "month" to "monthly" |
| ranked by score at r = 1 | 20 of 20 |
| median probability on the right entry | @@MEDIANTARGET@@ |
| noisy, 8 entries, ideal 0.945 at r = 2 | @@CATNOISE@@ across five snapshots |

**There is no speedup, and the reason is structural.** The oracle is compiled from the catalogue, so classical code has already read every entry, and at N entries a diagonal costs up to N - 2 two-qubit gates:

![Cost against a plain scan](../results/figures/fig_catalog_cost.png)

At 1,024 entries that is 32,800 gates against a 1,024-step scan. Grover's square root needs an oracle cheaper than reading the data.

## 12. Bounded rewinding (E7)

A hybrid QRSM forgets. So an iteration may only need to rewind the last w steps, not the whole history, which would make its cost independent of T. With the reflection on those w lights, at r = 2:

![Hit rate at a fixed rewind depth](../results/figures/fig_horizon.png)

| rewind | hit rate, T = 10, 12, 14, 16, 18 | TVD | memory fidelity |
|---|---|---|---|
| 6 steps | @@H6@@ | @@H6T@@ | @@H6F@@ |
| 8 steps | @@H8@@ | @@H8T@@ | @@H8F@@ |
| 10 steps | @@H10@@ | @@H10T@@ | @@H10F@@ |

The hit rate stays roughly flat as T grows, and the hidden state stays good. But TVD grows, because history older than the horizon isn't reweighted. So this helps for questions about the recent past. We tested it noiselessly only.

## 13. Real hardware

**It ran.** On 5 November 2026 we ran the 39 circuits on two IBM Heron chips: @@HWJOBS@@ jobs at 4,096 shots per circuit, @@HWSECONDS@@ seconds of device time on the free plan. No circuit used more than 11 of a chip's 156 qubits. Before the first job, we committed our predictions, the code that scores them, the compiled circuits and a simulation of those circuits with the device's own noise model (commit `2059f36`). That model has gate errors, relaxation during gates and readout errors. It has no crosstalk and no decay on idle qubits. Hit rates here are readout-corrected.

We chose ibm_kingston on that day's calibration: median two-qubit error @@HWCZ@@, T1 @@HWT1@@ µs, T2 @@HWT2@@ µs.

### The resilient build won on Kingston

The first pair of jobs, one plain and one with DD + twirling:

@@HWHEROTABLE@@

![The chance of a rare event on ibm_kingston, build by build, against the noise model and the noiseless answer](../results/figures/fig_hw_builds.png)

Across all five Kingston jobs, steer + local won @@HWWINS@@ comparisons:

| | steer + local | its rival |
|---|---|---|
| T = 3, hit rate | @@HWT3R@@, on 40 gates | @@HWT3B@@, textbook r = 3, on 213 gates |
| T = 3, TVD | @@HWT3RT@@ | @@HWT3BT@@ |
| T = 5, hit rate | @@HWT5R@@, on 88 gates | @@HWT5B@@, the same steer with the textbook reflection, on 171 gates |
| T = 5, TVD | @@HWT5RT@@ | @@HWT5BT@@ |

The chip punished depth more than its noise model did, so the lead at T = 3 came out at @@HWLEADREAL@@ in the first job, against @@HWLEADMODEL@@ predicted. Textbook Grover at its best, with DD, reached @@HWBESTBOOK@@. That's still far behind steer + local with no suppression at all. Cutting gates mattered more than any suppression we tried.

### Every job, side by side

@@HWRUNSTABLE@@

The last column is in standard errors, and it's positive when no defect sits above defect, as the exact answer has it.

![Every real job side by side: hit rates at T = 3 and T = 5, and the after-click separation](../results/figures/fig_hw_runs.png)

**It repeats.** A second plain job on the same compiled circuits gave @@HWAGAINR@@ and @@HWAGAINB@@, against @@HWFIRSTR@@ and @@HWFIRSTB@@ in the first.

### Noise analysis

**Interference survives.** With no defect, the hit rate should rise and then fall as r grows. Noise can't make that shape, because it pushes "any click" towards 0.875. The chip gave @@HWCURVE@@, against @@HWCURVEIDEAL@@ noiseless. Falling well below 0.875 at r = 3 is interference, after 147 two-qubit gates.

![Textbook Grover's hit rate against r: noiseless, noise model and real device](../results/figures/fig_hardware.png)

**Depth costs more than the model says.** Fidelity with the noiseless answer fell by about @@HWSLOPE@@ per two-qubit gate, against @@HWSLOPEMODEL@@ in the noise model. The echoes agree: run forwards and back, the all-in error came to @@HWECHO@@ per gate on Kingston, against @@HWECHOMODEL@@ in the model and @@HWCZ@@ reported for the gate alone. The device fell below its model on @@HWBELOW@@ of circuits with an ideal hit rate of 0.5 or more. The model still ranked the circuits well, with a rank correlation of @@HWRANK@@. So it's useful for comparing builds, and optimistic about how they'll do.

![Fidelity against gate count, and predicted against measured hit rate](../results/figures/fig_hw_noise.png)

**Suppression did little.** Two identical plain jobs differ, circuit by circuit, about as much as a suppressed job differs from plain: the plain repeat "improved" TVD on @@HWTVDAGAIN@@ of circuits, and the three suppressed jobs on @@HWTVDMODES@@. So those shares are run-to-run noise, and H5's 50% tells us nothing. What does show is small: median fidelity on circuits with 100 or more gates went from @@HWDEEPPLAIN@@ to @@HWDEEP@@, and the slope of fidelity with depth eased from @@HWSLOPE@@ to @@HWSLOPEMODES@@. Against that, steer + local lost a little at T = 3, and DD erased the fingerprint.

**A bad patch on Marrakesh.** The first Marrakesh job went badly. At T = 3, steer + local got @@HWBADT3@@ against @@HWBADT3B@@, where the model said TVD 0.05. At T = 5 it narrowly lost on hit rate: @@HWBADT5@@ against @@HWBADT5B@@. Nearly all of the damage sat on one cluster of qubits, 5, 6, 7, 8 and 17. The compiler chose them for 31 of the 39 circuits, because the reported error rates made them look like the best on the chip. Echoes on them showed @@HWBADECHO@@ per gate, against about 0.2% reported for those gates. Circuits that landed elsewhere on that chip did about as well as on Kingston.

So we recompiled to stay off those five qubits, and logged what we expected first. Echoes fell to @@HWMOVEDECHO@@. Steer + local won all four comparisons: @@HWMOVEDT3@@ against @@HWMOVEDT3B@@ at T = 3, and @@HWMOVEDT5@@ against @@HWMOVEDT5B@@ at T = 5. We don't know what was wrong with those qubits. We picked them after seeing the data, so this job tests the explanation, and it isn't a clean replication. The practical lesson is cheap: run a short echo on a layout before trusting it.

### The fingerprint on real chips

![The click rate after a click on real chips, with and without a defect, against the exact answer](../results/figures/fig_hw_after_click.png)

Telling a defect from none at τ = 3 means telling 0.047 from 0.101. With no suppression, steer + local read that difference at @@HWZFIRST@@ and @@HWZAGAIN@@ standard errors on Kingston, and @@HWZMOVED@@ on Marrakesh off the bad qubits. Plain sampling, from the same jobs, reached @@HWZPLAIN@@. That's close to the simulated 7.1 against 2.4.

It's fragile, though. DD took it to @@HWZDD@@, twirling to @@HWZTWIRL@@, and both together to @@HWZBOTH@@. We predicted twirling was to blame, and that missed. Every suppressed job raised the defect circuit's click rate at τ = 3, from about 0.065 to between 0.10 and 0.13. One possible reason, untested: fresh light qubits wait in |0>, where idling does them no harm, while DD keeps pulsing them. τ = 1 and τ = 2 don't separate reliably on either chip. And the two circuits differ in depth, with the deeper defect circuit getting more false clicks. That works against the separation, so it doesn't explain it away.

### What we predicted

These came before the jobs, and were scored by calculation: **@@HWTALLY@@.** H6 scored "held" because it says "in either job", and the suppressed job on its own would not have passed. F6 and F7 test a post-hoc explanation.

@@HWSCORE@@

## 14. What we predicted, and what happened

Expectations were logged before each run. The full list is in the [design log](design_log.md). The hardware predictions have their own table in section 13.

@@SCORE@@

## 15. Limits

- **No speedup.** A classical sampler beats everything here at this size.
- **No quantum advantage shown.** A crossover at large hidden memories is plausible, and we can't test it.
- **Most results are simulation.** That includes the IBM noise models, which are snapshots. The real-chip runs are small: @@HWJOBS@@ jobs on two chips in one evening, at most 11 qubits and 5 steps. At T = 5 the distribution error is still @@HWT5RT@@ on Kingston.
- **We rewind a model of a chip, never a chip.** A physical defect can't be run backwards. This queries what was learned from clicks.
- **Steering** is classical, exact only for clicks at known steps, and needs a rough p.
- **The local reflection** is an approximation, it drifts on long records, and it saves nothing for questions that read every light.
- **Bounded rewinding** is noiseless and distorts older history.
- **T qubits are the price of reversibility,** one per step.
- **Coverage.** One machine (theta 0.6, gamma 0.2, phi 0.45, zeta 0.3), one defect in most runs, five device snapshots, one seed per noisy cell.
- **We did not run** the research note's beat_20 benchmark, or any large-scale retrieval.

## 16. Why it could still matter, and what's next

A classical computer's cost grows exponentially with the hidden memory. A circuit's cost doesn't. IBM's [published target](https://www.ibm.com/quantum-computing/roadmap) for 2029 is 200 logical qubits and 100 million gates. As a rough estimate, a machine with 50 hidden qubits and a 150-step record fits in 200 logical qubits, while just holding that memory as a classical state vector takes about 18 petabytes. Conditioning on a 64-step record takes about 2.7 million gates as textbook Grover and about 40,000 once steered, so the design moves the job about 66 times closer to reach.

![Gates per sample as records grow](../results/figures/fig_future.png)

Next: run the hardware job; steering for learned models, where a click operator isn't uniform and steering becomes a training problem; error detection from what the machine conserves; rewinding set by the memory's own horizon; and testing the reader oracle on data with structure a compact oracle can use.

## References

See the [README](../README.md#references). The hidden-defect work this builds on is in [prior_work](../prior_work/hidden_defects/README.md).
