# The rubric, and where we answer it (V3)

Updated 12 November 2026. The ten items below are the judging criteria published on the event's qualifying-round page. A judge at the qualifier told the team the finals would use the same or a similar rubric. Confirm with the organizers; nothing here promises a score.

| # | Criterion, as published | Points | Where the talk answers it | Where the repository answers it |
|---:|---|---:|---|---|
| 1 | Is there a clear, meaningful problem? Does the team explain who it affects and why it matters? | 15 | Slides 2, 4, 11 | README, "The problem"; Lab scenes 1 and 7 |
| 2 | Does the team understand WHY quantum might help here, and are they honest about today's limits (noise, qubit counts, no guaranteed speedup)? | 20 | Slides 5, 6, 9, 12 | README, "What we do not claim"; `reproduce.py` section 3 |
| 3 | Does the code run? Is Qiskit used appropriately (circuits, primitives, transpilation, algorithms)? | 20 | Slides 3, 7, 8, 10, 38 | `python reproduce.py`; `rewindandamplify-main/qrsm_grover/`; 434 Python and 41 JavaScript tests |
| 4 | Are results shown and interpreted? Is there a comparison to a classical baseline, expected values, or simulator vs. hardware? | 10 | Slides 4, 8, 9, 36 | README, "What we found"; `hardware_campaign/noise_model/`; `docs/EVIDENCE.md` |
| 5 | Is the idea or approach original, or a fresh take on a known problem? | 10 | Slides 7, 13, 24 | `rewindandamplify-main/docs/REPORT.md` |
| 6 | Can the team clearly articulate the problem, the solution and the results to both technical and non-technical audiences? | 15 | The whole deck; slide 10 | The Lab's plain and technical captions |
| 7 | Can the team answer questions? Do all members contribute? Can they describe what they learned and next steps? | 10 | Slides 12, 13; backups 14 to 38 | `FINALS_QA.md` |
| 8 | Bonus: ran on a local or cloud simulator (e.g. Aer, statevector) | 1 | Slides 7, 9 | `reproduce.py` sections 2 and 4 |
| 9 | Bonus: circuit executed on real IBM Quantum hardware; job results shown | 3 | Slide 8 | `hardware_campaign/RESULTS.md`, with job IDs |
| 10 | Bonus: ran on real hardware AND compared to simulator, analysed noise, or applied error suppression/mitigation | 5 | Slides 9, 14, 36 | `hardware_campaign/noise_model/README.md` |

## What each criterion needs from the speakers

**1. Problem.** Say who has the problem before any physics: quantum-chip teams, photon-source engineers, anyone interpreting a detector. Say why it matters in one line: guess the cause wrong and you fix the wrong thing. Do not open with the algorithm.

**2. Why quantum, and honesty.** Three sentences carry this. Rare events cost 1/p runs the ordinary way and about 1/√p with amplification. Two catches: it must run the model backwards, and it is deep. And today, at this size, a classical sampler is faster. Say the third sentence without being asked.

**3. Implementation.** Name what was built in Qiskit: the recurrent model as a circuit, the reversible version with a fresh qubit per step, the oracle (one Z gate for "a click at this step"), the inverse preparation, the ancilla-assisted reflection, steering, transpilation to IBM's CZ basis with a chosen layout, and the readout-calibration circuits in every job. If a judge asks whether the code runs, show slide 38 or run `python reproduce.py`.

**4. Results.** Always give the comparison, not a lone number: exact 4.67% and 10.10%; ideal simulator 96%; noise model 78.4% and 69.7%; hardware 76.9% and 69.3%; no amplification 6.7%. The classical baseline is the exact backward sampler, and it wins at this size.

**5. Originality.** Amplitude amplification is not ours. What is ours: seeing that a recurrent model with resets cannot be amplified, making it reversible, steering one gate so one round is enough, and trading a small known bias for half the gates. And the habit of checking the answer, not only the hit rate.

**6. Communication.** One name per idea (see `FINALS_TALK.md`). Define click, QRSM and "the lighter build" once and reuse them. Let the pictures carry the physics.

**7. Q&A and teamwork.** Every member presents a slide with a result on it and can defend it. Each should have one sentence ready on what they learned. `FINALS_QA.md` starts with twelve questions to rehearse.

**Bonus.** The three bonus items are separate lines on the published form. We have evidence for all three: Aer simulations, seventeen real IBM jobs with saved IDs and counts, and a noise analysis that includes a simulator comparison, echo circuits and a suppression test that did not help.

## Claims and their evidence

| Question | What we can say | What would be needed to say more |
|---|---|---|
| Did you detect a real defect? | No. Two programmed models give different predictions, and IBM qubits ran them. | Physical records, a calibrated detector model, competing explanations, blind validation |
| Is there a quantum advantage? | No. Ideal amplification changes the dependence on rarity from 1/p to about 1/√p; at this size a classical sampler is faster. | A model whose hidden memory is hard classically, with the full cost of preparation, oracle and noise counted |
| Did fewer gates cause the better result? | It is the leading explanation: a model with only gate and readout errors predicts the gap. Width and routing also differ. | The same comparison on matched layouts and repeated on other days |
| Does error suppression help? | Not here. Dynamical decoupling and twirling made the answer error worse on identical circuits. | A study of why, and of other suppression settings |
| Does this help chipmaking or photon sources? | Not shown. The follow-up studies are simulations and a reanalysis of published data, and one of them favours a conventional sensor. | Measurements on a real source with a conventional reference |

## The explanation every speaker should be able to give

"A hidden defect can change what a detector records. Our model, a quantum recurrent state machine, carries a hidden quantum memory from step to step and predicts the next click. To ask it about a rare event without wasting most runs, we made it reversible and used amplitude amplification. On IBM hardware our lighter build found the rare click more often and gave a closer answer than the textbook build, and a simple noise model explains why. It is not faster than a classical computer today."
