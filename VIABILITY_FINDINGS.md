# Rewind & Amplify: application and viability findings

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

This is a working research note for the 14 November 2026 finals. It separates observed hardware results, toy simulations, an independent published optical measurement, and open research questions. It does not claim an industrial deployment or quantum advantage.

The current finals story and cost definitions are in `START_HERE_FINALS.md` and `FINALS_RUBRIC.md`. The original after-click question now has an independent reproduction in `research-validation/original_after_click_verification.json`: its two specified models predict 4.67% versus 10.10% for a step-6 click given a step-3 click. This is a model prediction, not an unknown physical-defect diagnosis. The later, more realistic sensing study is in `laser_sensor_viability/README.md`; it finds incremental information relative to one conventional baseline, while a second independent conventional reference performs better. Earlier toy findings below remain distinct from that study.

## What we have established

### 1. Quantum recurrent-model hardware

For the saved IBM Kingston click-at-step-3 experiment, the closer one-round, steered comparison yielded **3,525/4,096 = 86.06%** raw hits for the local-reflection circuit and **3,215/4,096 = 78.49%** for the full-reflection circuit. The respective hardware-compiled two-qubit gate counts were 40 and 85; the saved readout-corrected rates were 87.36% and 79.29%. The corrected conditional-history TVDs were approximately 0.055 and 0.069. The circuits use different layouts, so this does not isolate the reflection as the sole cause. See `FINALS_EVIDENCE.md`.

This is a small IBM gate-model implementation of a surrogate emitter and hidden memory. It did not diagnose an unknown physical defect or reverse a measured photon. Current classical simulation is faster at this scale.

### 2. A quantum circuit for a toy lithography question

The five-site model in `finals-lithography/` has independent binary absorption events with probability 0.8 and calls a contact missing if fewer than two sites absorb. Exact enumeration gives failure probability **0.00672**. One ideal Qiskit amplitude-amplification round gives **0.059401**, while preserving the exact conditional probabilities in this small model. A generic `u,cx` compilation contains **252 CX gates**, at depth 449, on five circuit qubits. It explicitly marks each of six failing histories and does not include hardware routing or noise.

There is an even stronger classical baseline for this particular model: the exact conditional distribution has a closed form, so a classical sampler can draw a matching history directly without rejecting whole trials. This relies on independent, identical sites and does not solve the separate spatial example. It means that comparing only against naive rejection would substantially overstate the toy circuit's practical case. See `finals-lithography/VIABILITY_COST_README.md`.

In the same family with 3–7 sites and one round, `finals-lithography/scaling_results.json` records generic CX counts **30, 84, 252, 656, 1,098**. This tests one implementation and one compiler configuration; it is not a fundamental scaling bound. A better oracle or different number of rounds may change the results. The ideal hit rate is not a fair runtime comparison; preparation, marking, repetitions and strong classical methods all count.

We tested one alternative: a reversible counter marks whether the number of absorptions is below two and then uncomputes its workspace. All data-basis inputs for 3–7 sites were checked. In this compiler configuration, the 5-site circuit uses **221 CX and eight qubits** rather than 252 CX and five qubits; the 7-site circuit uses **317 CX and ten qubits** rather than 1,098 CX and seven qubits. For three and four sites, the enumerated implementation used fewer CX gates. These are exact toy-predicate alternatives in an ideal simulation, not hardware results or a general scaling law.

In a further **synthetic** 10-qubit line-topology noise-model pilot, the 7-site enumerated/counter circuits compiled to 2,751/830 CX gates, respectively. Only 16 and 4 matching outcomes appeared in 256 shots, and conservative finite-shot bounds on conditional-distribution error span the entire 0–1 range. The larger raw hit rate for the enumerated circuit was 6.25%, equal to the matching fraction of a uniform seven-bit output, so noise-generated hits are a plausible explanation. Different layouts and this limited sample prevent ranking the quality of the algorithms. See `finals-lithography/oracle_noise_pilot_results.json` and its README for the exact synthetic target and assumptions; no IBM job was submitted.

To remove shot-sampling uncertainty within that same synthetic noise model, we also ran deterministic density-matrix simulations with the target's independent readout errors applied analytically. For seven sites, the enumerated/counter outputs had event probabilities **0.0527/0.0139** and conditional-history TVDs **0.128/0.072**; the ideal event probability was **0.00334**. Thus, in this particular model the counter output was closer to the intended conditional distribution even though the enumerated output had more matching bitstrings. Both noisy event rates were elevated above ideal. This is not a real-device result or a clean causal isolation: the compiled layouts and qubit counts differ, and the synthetic local-noise model does not include all hardware effects. See `finals-lithography/oracle_density_n7.json` and `finals-lithography/oracle_density_pilot.py`.

A follow-on counter-oracle sweep for seven sites increased the number of amplification rounds from zero to three. In the same synthetic noise model, raw matching probability increased from **0.000387 to 0.117720**, while conditional-history TVD increased from **0.0024 to 0.1310** and routed CX count rose from **0 to 2,598** per circuit. Zero CX does not mean zero total execution cost. The target and layouts limit generalization; the experiment shows why raw matches alone cannot establish useful accuracy. Data, cost proxies and the special-case classical sampler are in `finals-lithography/viability_cost_n7.json` and `finals-lithography/VIABILITY_COST_README.md`.

### 3. A larger classical spatial toy model

The separate 7×7 model uses Poisson photon counts, a Gaussian spread, and a central contact threshold in arbitrary units. On the checked 50,000-map run, direct sampling estimated **0.004040 ± 0.000284** and weighted importance sampling **0.004193 ± 0.000107**, where the uncertainty is one estimated standard error, not model uncertainty. The proposal's 15,790 raw failures are not the physical/target failure rate. The saved `finals-lithography/dose_sweep.png` shows a decrease in this toy failure rate as its input count is increased; it does not model the many other practical effects of dose.

This shows how a rare-event workflow could be applied to a chip-making question. It does not show that the process is a calibrated EUV simulator, and there is no quantum circuit for this spatial model. A fair next comparison requires relevant process models or open data, stronger domain baselines, uncertainty under model changes, and actual state-preparation/oracle accounting.

### 4. Photon-emitter inference and a reversible bridge

The separately reproduced photon companion simulates a driven emitter, a hidden two-level system and lossy cavity, and derives click histories. On its reused synthetic 180-record holdout, the correctly specified fixed-nuisance physical model's lead narrowed from **27.43 nats total** over an observed-bit Markov model to **5.69 nats** over a trained three-state binary HMM. The paired difference was **0.0316 ± 0.0159 nats per record** by standard error. The correct physical family and nuisance parameters were supplied to the physical model, the HMM optimization was finite, and the dataset and holdout have been used before. This is exploratory, not evidence of general quantum or physical advantage. Full method and convergence diagnostics are in `qrsm_photon_poc/diagnostics_baselines/README.md`.

Three additional independently generated synthetic train/holdout pairs gave correctly specified physical-minus-HMM differences of **0.0632, 0.0264 and 0.0352 nats per held-out record**; bootstrap intervals included zero in the latter two cases. Deliberately miscalibrating detection efficiency and dark counts shifted the fitted coupling from the true **0.65 to 0.45** and produced differences of **0.0296, 0.0101 and −0.0156** nats per record. These fits are exploratory: the selected HMM EM fits hit the iteration cap and later local refinement reached parameter bounds, so optimization and broader coverage remain unresolved. The miscalibration test is not real detector data.

`qrsm_photon_poc/dilation_feasibility.py` constructs and tests a finite-dimensional **flagged isometry** of the model's detected/no-detected channel. In the default three-level cavity example, a cutoff-dependent numerical approximation yields a construction using four padded system qubits, one outcome flag and eight environment qubits for one modeled time bin. A looser numerical cutoff changes that construction's environment requirement. This default construction remains classical matrix analysis and has not been synthesized into gates.

We separately synthesized a **smaller two-level cavity approximation** using Qiskit. With absolute Choi cutoff 0.03 the one-bin circuit used **7 qubits and 1,051 generic CX gates**; cutoff 0.003 used **8 qubits and 2,086 CX gates**. After normalizing the truncated channels, the respective maximum conditional-state discrepancies versus the original two-level-cavity model over six selected states were about **0.048 and 0.016** in Frobenius norm. An independent reconstruction checked the synthesized circuits against the retained maps, and the inverse was tested. These are coarse, cutoff-dependent approximations, not certified worst-case operational error bounds, a gate estimate for the original three-level-cavity model, a hardware run, or proof of a minimal real-device cost. They exclude routing, noise, multiple time bins, and amplification; keeping the environment coherent across bins raises additional resource questions.

We have now also built an **ideal two-bin Qiskit circuit** around that coarse two-level-cavity instrument: it coherently retains two outcome and environment registers, marks a click in both bins, reverses the preparation, reflects, and replays. The original open-system model gives this record probability **0.0017848**; the retained approximation gives **0.0017264**, which one ideal amplification round increases to **0.0154661**. The amplified selected system state agrees with the retained-model conditional state to about `5.1e-13` trace distance, while the retained and original conditional states differ by **0.0174** for this particular initial state and record. The compiled two-bin query uses **11 circuit qubits and 6,663 generic CX gates**, depth 12,672, with no routing, noise, or hardware included. This is a direct proof of concept connecting the two *ideas* in the standalone photon companion, not an integration into the original package or a demonstrated advantage. Source, assumptions and tests: `qrsm_photon_poc/two_bin_amplification.py` and `qrsm_photon_poc/generated/two_bin_double.json`.

### 5. An independent measured photon example

`photon_reference/` includes published processed correlation data and the original authors' fit from a laser-driven hBN quantum emitter, by Fournier et al. It is included to show the kind of measurement motivating optical diagnostics. It is **not** measured by the FGCU team, does not contain raw click histories in the selected files, and has not been fit by the team's model. Source: https://doi.org/10.1103/PhysRevB.107.195304 and https://doi.org/10.5281/zenodo.7938744 (CC BY 4.0).

## What would meaningfully test the opportunity next

1. **Photon diagnostics:** obtain suitable independently measured time-tagged records, document the detector and drive, fit nuisance parameters rather than assuming the truth, and compare with matched classical HMM/telegraph and correlation models on a genuinely new holdout.
2. **Physical-to-quantum bridge:** build a structured reversible approximation of the open-system instrument, account for environment and history registers, synthesize it to a target gate set, and measure the accuracy/cost tradeoff as the number of bins grows.
3. **Lithography:** use an independently documented process or measured dataset, include material and detector/measurement assumptions, and compare exact/small-system results, classical importance sampling, and any quantum algorithm on the same quantity and total-cost basis.
4. **Competition readiness:** prioritize a timed, reproducible ten-minute explanation over adding an unvalidated claim. Use the optical trace as attributed context, the lithography process as an explicit toy prototype, and the saved IBM experiment as the team's hardware result.
