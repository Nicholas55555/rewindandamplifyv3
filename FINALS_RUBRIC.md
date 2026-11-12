# Finals rubric and speaking coverage

This checklist uses the supplied `Qiskit_Fall_Fest_Judging_Rubric.xlsx`, sheet `Rubric`, rows 5–11 and 16–18. These are the supplied judging criteria, not a claim that the organizers have confirmed unchanged finals rules. The workbook allows organizer changes. Its single hardware tier differs from the three bonus columns in `results.csv`; do not add those schemes together or promise a score.

Updated 11 November 2026 after the research followups. The talk plans **13 main slides in 9:20**, including a 45-second demonstration of the original quantum-model query. Forty seconds remain for transitions and timing variation. Actual rehearsal is still required. Backups are for questions. Current evidence replaces older headline results where the task changed; it does not relabel historical experiments.

| Criterion | Weight | What the judges should understand | Main evidence and delivery |
|---|---:|---|---|
| Problem Definition & Relevance | 15% | Hidden interactions can alter a qubit's evolution and complicate interpretation of measurements. Device researchers need models that distinguish possible causes. Rare conditioning events also waste ordinary model samples. | Slides 1–5 explain state-inference relevance, clicks, the QRSM's contribution and the after-click prediction. Slides 10 and 12 connect semiconductor photon quality and source metrology to device usefulness, exposure consistency and the cost of false alarms. |
| Quantum Rationale & Understanding of Potential | 20% | The QRSM encodes physical quantum dynamics. Coherent amplification can reduce dependence on event rarity relative to rejection sampling, given reversible preparation. Current examples are easier classically. | Slides 4 and 6–7 distinguish physical modeling, classical fitting and coherent querying, with classical alternatives and limitations. Slides 8 and 12 address noise, gate cost and the unproven crossover. |
| Technical Implementation (Qiskit) | 20% | The team implemented a recurrent model, retained fresh history qubits, constructed a condition oracle, inverted preparation, tested steering/local reflections, transpiled and saved real-device results. | Slides 4 and 7–9 show the model update, reversible construction, compiled results and application. Archived jobs and reproduction scripts support Q&A. The app visualizes saved results; it does not submit a live quantum job. |
| Results & Validation | 10% | More matching outcomes are useful only when their conditional behavior remains accurate. The conclusions have explicit baselines and failure cases. | Slide 4 adds a fresh detector-misidentification example. Slide 5 gives the exact conditional prediction. Slide 8 gives real-device counts, gates and conditional error. Slide 11 uses the new unknown-onset sensor comparison. Slide 12 and backups preserve poor amplitude detection, the prior-only control and the conditional phase-inspection result. |
| Innovation & Creativity | 10% | Conditional quantum models, amplitude amplification and atomic spectroscopy are established. The contribution is the recurrent-model mapping, investigation of noise-sensitive implementations and tested research extension. | Slides 4 and 6–8 distinguish physical structure, established algorithms and team engineering. The app's memory-only control tests answer quality. New conventional and prior-only controls show how the research changed the conclusions. |
| Presentation & Communication | 15% | A click is a detection record, a history is a time sequence, and the QRSM predicts outcomes under candidate hidden dynamics. The audience understands the problem before seeing a circuit. | Slides 1–5 establish these meanings in plain language. The 45-second demo reinforces the same example. Rehearse to the planned 9:20 to remain within ten minutes. |
| Q&A, Teamwork & Learning Journey | 10% | Each member can describe their contribution, a limitation, a lesson and the next test. | Slide 13 uses the documented roles confirmed by the user. `FINALS_QA.md` supplies shared answers. Assign speaking handoffs and rehearse together; the files cannot establish live teamwork or question-answering performance. |

The supplied workbook's highest hardware tier is **+5 for real device execution plus noise analysis**, selected as one tier. The project has saved real-device results and simulator/noise comparisons to show in support of that tier. Awarding it is the judges' decision.

## The explanation every speaker should be able to give

“Hidden defects can change how a quantum system evolves and what we measure. Our QRSM models those interactions, updates its hidden state after each recorded outcome, and predicts the next observations. Comparing candidate models can support defect analysis. We then make a specified model reversible so amplification returns more histories matching a chosen condition. On IBM hardware, we check both the matching rate and the accuracy of those answers.”

A click means the output bit is one during a time bin. In the optical interpretation, that is an on/off detector registering a detection. On IBM hardware, a superconducting qubit represents that output. A click alone does not establish a defect or identify its cause. The model retains quantum memory; the measured output history is a binary record, not a complete readout of its hidden state.

The original after-click question conditions on **a click at step 3**, allowing any earlier outcomes. An illustrative record such as `0 0 1` shows how to read a history, but the benchmark does not condition on that whole prefix. The useful answer is the probability of clicks at steps 4, 5 and 6 under each specified model. It is not a claim to recover the unique hidden cause of a measured event.

The QRSM's contribution to diagnosis is a physical model whose outcome probabilities can score observed records. Classical fitting compares candidate interactions and noise, then tests predictions on unused data. Hidden Markov models also represent memory, so the comparison must test the value of the proposed physical structure. All defect/inference fits here use synthetic records; archived IBM experiments encode known settings. Amplification queries an existing model and does not create extra physical measurements.

The fresh dead-time example makes the diagnostic issue concrete: omitting a blind detector bin gave coupling 0.069 for truth 0.65, while accounting for it gave 0.706 and better held-out predictions. Other parameters remained biased or at bounds. This supports checking detector assumptions, rather than claiming that fitting one approximately correct coupling proves the physical cause.

Defect analysis matters to state inference because hidden interactions can change the state before readout, while readout errors can change the reported outcome. Ignoring either can bias the interpretation of repeated observations. General state reconstruction needs sufficient preparations and measurement settings; this project does not perform complete tomography. See [Schlör et al.](https://www.nist.gov/publications/correlating-decoherence-transmon-qubits-low-frequency-noise-single-fluctuators) for physical fluctuator/coherence context and [Keith et al.](https://www.nist.gov/publications/joint-quantum-state-and-measurement-tomography-incomplete-measurements) for measurement-model uncertainty in state inference. These motivate the problem, not validation of this surrogate.

## Cost and value in terms the audience can assess

For the current Marrakesh precision repeat, both circuits use steering and one amplification round, with the same compiled circuits as the initial run:

| Quantity | Local reflection | Full reflection |
|---|---:|---:|
| Native two-qubit gates per shot | 58 | 125 |
| Raw matching shots | 6,300 / 8,192 | 5,674 / 8,192 |
| Observed matching rate | 76.90% | 69.26% |
| Raw selected-history TV distance (smaller is closer) | 0.1177 | 0.1814 |
| Two-qubit gate executions per accepted shot | 75.42 | 180.47 |

The last row is `gates per shot × all shots / accepted shots`. It is an accounting proxy, not elapsed time, money or proof of equal-quality answers. It excludes calibration, one-qubit operations, readout, compilation and infrastructure. A shared initial physical placement reduces one confounder, but routing, operations and drift still prevent isolating gate count as the sole cause. The local approximation also changes the ideal conditional law. Source: [new hardware results](hardware_campaign/RESULTS.md). The older Kingston 40/85-gate comparison remains separately labeled in FINALS_EVIDENCE.md.

Less noisy qubits are valuable because the algorithm needs coherence and interference to preserve its answer. At the same circuit and task, reduced error can make more executions informative and permit useful longer circuits. Extra shots reduce sampling uncertainty, but cannot by themselves remove systematic bias. Our contribution is also to reduce the number of error opportunities through circuit design. A gate count or a published calibration alone is insufficient: evaluate the actual task, layout and conditional accuracy. No currency saving or current computational advantage is established here.

The full 49-cell construction makes the resource issue visible. Our explicit 389-qubit implementations have constructive generic CX upper bounds of 2.87–3.38 million per round, including preparation, inversion, predicate and reflection. These are unoptimized implementation costs, not lower bounds. The full quantum state was not simulated, and the positive additive process already has strong classical solutions. The result prevents presenting a supposedly free oracle as a complete cost estimate.

For chipmaking, the proposed user is the source-monitoring or process engineer. Source variation can affect exposure and printed dimensions; attributing that variation can inform investigation or maintenance. Potential value includes avoiding further out-of-spec exposure, unnecessary intervention and associated rework or downtime. These are motivations, not measured benefits of our prototype. False alarms have costs too: a sensor that falsely blames the source can trigger unnecessary stops.

Cymer/imec's controlled wafer study supports the link between source parameters and printed dimensions: [Alagna et al., SPIE 2014](https://www.cymer.com/wp-content/uploads/2018/12/Cymer_SPIE_AdvancedLithography_2014.pdf). It does not establish performance of our atomic channel. Our 698 nm laboratory surrogate needs a distinct physical interface and validation before transfer to a 193 nm excimer source, a CO₂ drive laser or the EUV emission itself.

Measurement resources matter as well. Under the unknown-onset sensor's assumed serial timing, calibration and training amount to 16.73 hours per pipeline, excluding apparatus setup. Those are simulated acquisition requirements, not hours spent operating a real sensor. In the optical inspection model, 1% pair-preparation success makes pure NOON take 100 times as long as coherent light to match dose; the 10/90 hybrid takes 90.1 times as long. At equal time the favorable result disappears. Pump/herald light, cooling, reference optics and apparatus costs remain uncalibrated, so no financial return is inferred.

## What should be claimed, and what still needs evidence

| Question | Supported answer | Further evidence required |
|---|---|---|
| Does the original project detect a real light-source defect? | It computes and samples different conditional behavior for specified hidden-memory models. The IBM processor represents those models. | Independent physical records, calibrated detector/source models, competing causes and prospective validation. |
| Is the original quantum algorithm useful in principle? | It implements reversible conditional sampling and tests the cost/accuracy tradeoff on present hardware. Ideal amplitude amplification reduces rejection-query dependence from order `1/p` to order `1/sqrt(p)` under its assumptions. | Complete preparation/oracle/measurement costs and a crossover against the strongest classical methods for larger, independently justified models. |
| Does the frequency sensor add information? | In the unknown-onset study, timely detection increases from 51.35% to 58.02%; a second conventional reference reaches 97.97%. Actual full-record false alarms and drift failures accompany those rates. | Real synchronized measurements, reference stability, full resources and blinded source/nuisance changes. |
| Does the emitter model diagnose changing laser amplitude? | The tested 96-bin regime fails useful prompt detection. Most source-case estimation gain over a constant comes from the positive prior; detector changes can cause false source alarms. | A justified operating point or acquisition budget, richer nuisance alternatives and independent physical calibration. |
| Does optical inspection show a benefit? | A charged hybrid gives lower phase RMSE than the specified coherent comparator at high efficiency and equal sample dose. Greater loss or poor preparation at equal time can remove it. | Calibrated phase-object data, loss/reference uncertainty, realistic detection and a strong physical conventional comparator. |
| Does this improve chip yield or make less noisy qubits? | Neither is demonstrated. Those are possible downstream motivations for validated diagnosis and engineering. | Measurements connecting a correct diagnosis to a controlled process change and better device outcomes. |

Theory sources: [Brassard et al., amplitude amplification](https://arxiv.org/abs/quant-ph/0005055) and [Low, Yoder and Chuang, quantum inference](https://arxiv.org/abs/1402.7359). The known query improvement is not the team's invention and is not a blanket advantage over direct classical conditional sampling.

## Team rehearsal

Use the contributions in the original repository README, confirmed for this plan by the user: Nicholas Taylor (QRSM/Grover and experiments), Timofey Yudintsev (research and search idea), Dan Izquierdo (experiments), and Dillon Satria Sitepu (formatting and revision). The qualifier CSV uses shortened names. Do not turn those roles into unsupported claims about who wrote or validated each new extension.

Each person should be able to explain click versus defect, model versus physical device, raw hits versus conditional accuracy, why classical methods win at this size, and why the sensing result does not establish quantum advantage. The documented original project used Claude assistance; this revision and research extension used Codex/OpenAI assistance. Follow the event's disclosure requirements and describe the actual human decisions and checks honestly.

Each person should also explain one changed conclusion: a conventional reference beat the atomic addition, a weak amplitude monitor did not become useful merely by fitting a quantum model, or a prior-only control explained most of an apparent estimation gain. The detailed research is backup material; the main talk remains centered on the original QRSM query and its hardware implementation.

## Semiconductor connection in the current revision

Slide 10 explicitly maps the QRSM's hidden-state prediction question to semiconductor photon-source characterization; backups 30–35 and the app hold the detail. The checked dot model separates brightness and multiphoton suppression from interference quality, and shows pair memory at fixed individual-photon frequency distributions. External GaAs data expose calibration/normalization sensitivity. Together these identify what an extended observation model must measure and control. The proposed engineering decision is selecting or tuning sources for a quantum photonic chip using both quality and pair yield.

For quantum rationale and learning, distinguish the original binary instrument from the now-implemented joint-photon instrument. Its conditional memory states, passive negative control, synthetic inference and actual IBM circuits are checked. No physical dot fit or uniquely identified defect follows. Strong classical HMMs remain competitive, and calibration failures persist at large budgets. The work defines a testable semiconductor source-quality application without claiming computational advantage.

This strengthens problem relevance, quantum understanding and validation coverage only within that scope. The 16-fold excitation-attempt example charges independent collection loss; it does not claim a device cost saving. The analysis does not identify a microscopic defect or demonstrate a lithography-laser sensor. Each speaker should distinguish our simulation, our reanalysis of published data, the authors' experiment and a future device test. Original team contributions and AI disclosures above still apply.

## Current campaign evidence for the criteria

Problem/impact: usable conditional answers and semiconductor photon-source quality. Quantum rationale: retained states, joint observation and reversible queries. Implementation: measured IBM circuits with saved mappings and raw counts. Evaluation: repeats, classical predictors, nuisance controls and failure cases. Innovation: this scoped model/query integration and its measured limits, distinct from established optics. Presentation: 13 main slides, planned 9:20. Teamwork: documented roles and disclosed AI assistance; backups through slide 35.
