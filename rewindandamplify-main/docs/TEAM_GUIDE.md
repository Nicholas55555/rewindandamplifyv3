# Team guide

Everything you need to record the video and answer questions, in one place. You don't need to read any code for this.

## Before 8:00 a.m. ET on Friday 6 November

- [x] Add the team's names: cover slide, last slide, and the Team section of the README.
- [x] Each person's part is on the last slide.
- [x] Run the hardware job. Done on 5 November: seven jobs on two real IBM chips.
- [ ] Record the video: 15 minutes or less. Aim for 14. Everyone speaks (section 2).
- [x] Publish the GitHub repository: https://github.com/Nicholas55555/rewindandamplify. It's on the last slide. Put it in DeepStation too.
- [ ] On DeepStation, submit the video and the GitHub link. It's the only submission platform.
- [ ] 1:30 p.m. Friday, SRHM 114: present at the ceremony. Certificates need both submitting and presenting.

## The project in one minute

**The problem.** The useful events in a quantum system are rare, and rare means expensive. Matching one real 64-step click record from our model takes about 27 million runs, because you throw away every run that doesn't match.

**The idea.** Grover's algorithm makes rare answers common, using about the square root of the work. But it has to run the machine backwards, and our machine resets a qubit every step. You can't Grover what you can't rewind.

**What we did.** We made the machine reversible, then redesigned Grover around noise, in four moves:

1. **Purify.** A fresh qubit replaces every reset. The whole run becomes one reversible circuit, holding every possible history at once.
2. **Steer.** Part of the rarity is just one gate angle. Tune it, and the event gets common for free, with the answer still exact.
3. **Amplify locally.** One iteration, with a reflection on 3 qubits instead of every qubit.
4. **Verify.** The click is measured, so a failed shot shows itself and is dropped.

**The result.** 3 to 5 times fewer two-qubit gates than textbook Grover, and better answers on all five IBM device models we tested. It held up on real IBM chips: on ibm_kingston, 87% against 59%, with 40 gates against 213. No speedup today, and we say so plainly. The point is the architecture, and where it could matter on future machines.

## Who presents what

This is a suggestion, so swap it around. Everyone speaking helps: the rubric asks whether all members contribute.

| time | slides | suggested speaker |
|---|---|---|
| 0:00 | 1-5: the problem, the real-world problems, the model and its circuit, the wall | Nicholas |
| 4:10 | 6-8: Grover in one minute, its circuit, why it won't bolt on | Dan |
| 6:16 | 9-10: purify, it works, and why partly coherent and partly reversible | Nicholas |
| 8:46 | 11-14: the resilient architecture and its results | Nicholas |
| 11:57 | 15: the physics fingerprint | Nicholas or Timofey |
| 12:56 | 16-17: keyword search and the demo | Timofey |
| 14:29 | 18-20: real chips, what they taught us, honest limits | Dillon |
| 17:13 | 21-22: potential, what we learned | Dillon, then all |

The real-world problems slide comes straight after slide 2, and the partly coherent slide straight after slide 10. Neither has a page number, so the other slides keep theirs. Slide 23 is a backup for questions: the QRSM family, and where ours sits. It isn't part of the talk.

The speaker notes on each slide are written to be read aloud. They add up to about 18.7 minutes at a relaxed 140 words a minute, or about 17.5 at a natural 150, and the submission limit is 15. So time one run-through. The easiest cuts: slide 17 down to the raster clip, the search on slide 16, and the second half of the notes on slide 12.

## Recording the video

**The easiest way:** open `deck/Rewind_and_Amplify_deck_with_notes.pptx` in PowerPoint. Use Slide Show › Record, read your notes, then File › Export › Create a Video. Each person can record their own slides on their own laptop, and you can join the clips afterwards.

**For the demo slide,** either record your screen running `python demo/demo.py`, or show `results/figures/raster.mp4` and the interactive lab (`demo/index.html`).

**A fallback:** `tools/make_video.py` makes a complete narrated draft with a computer voice, 14:27 long, leaving out the backup slide. It's useful for checking pace, or if time runs out. Your own voices will score better on communication.

**Submitting:** check the Submission tab on DeepStation, after signing in, to see whether it wants a file or a link. If it wants a link, an unlisted YouTube video or a Google Drive file set to "anyone with the link" both work. Test the link in a private window.

## Questions judges may ask

**Isn't this just known amplitude amplification?**
The core is, and we cite it: Low, Yoder and Chuang did amplified rejection sampling on Bayesian networks in 2014. What's ours is mapping it onto hidden quantum models, solving the reset problem, and the noise-resilient design: steering, the local reflection and its leak diagnostic, and an honest test across five device models.

**Why not just use a classical computer?**
At this size you should. An exact classical sampler gives a sample in about a millisecond. Its cost grew about 6 times per hidden qubit in our tests, and it took 10 minutes just to set up at 11 hidden qubits. So quantum could only matter for large hidden memories, and we can't test that today.

**Then where could quantum help?**
Two places. When the hidden memory is too big to simulate, running the circuit is the only way to sample it, and Grover then cuts the cost of conditioning from 1/p to 1/√p. And our estimate says that regime fits inside IBM's published 2029 target: 50 hidden qubits and 150 steps in 200 logical qubits, where the memory alone would be about 18 petabytes classically. That's an estimate, not a result.

**You can't rewind a real chip, so what's the use?**
Right, and we say so. We rewind a model of the chip, the QRSM, which was learned from its clicks. A physical defect can't be run backwards. So this is for querying a learned model, not the device.

**Doesn't the oracle need to know the answer?**
No. It checks a property of a history you could verify by eye, such as "there's a click at step 3". What you want is the distribution of everything else given that. In the keyword search it's different: the oracle is compiled from the catalogue, so classical code has already read every entry. That's why that demo has no speedup.

**Isn't steering just importance sampling?**
Yes, and it's classical. It gets most of the gain on the 64-step record: 4,400 times, against about 50 times from Grover on top. We count it in the baseline to be fair. It's exact here because a click's operator has a single non-zero singular value, so scaling it scales every matching history equally.

**Why does the local reflection work?**
One iteration gives exactly (1 - 4p)|psi> + 2|g> - 4A|l>, where |l> is the leak: the part of a rewound marked history with the memory back at zero but a light still on. Watching the question's light removes the largest term. What's left needs an earlier click as well, so it's second order. That's why it drifts on long records, where earlier clicks are likely.

**How do you know p, if the event is rare?**
You don't need it precisely. Steering is forgiving: anything from p' = 0.18 to 0.32 gives a hit rate above 0.94. With p unknown altogether, the standard BBHT schedule costs about 2 times more, and it still scales as the square root.

**What about noise, really?**
It's the central problem, and we made it a design constraint. Noise floors can fool you: "any click" at 3 steps scores 87.5% from pure noise, so we report the conditional distribution and hidden-state fidelity too. For very rare events, plain sampling on a noisy device reads about 3 times too high, because false clicks swamp true ones.

**Has this found a real defect on a real chip?**
No, and we say so on the slide. We've found defects in simulated click records, and we've run the circuits on two real chips. The next step is to read a real chip's clicks and check the answer against a direct measurement of its defects. The nearest thing so far is our echo circuits, which caught a bad patch of qubits on Marrakesh, but that doesn't tell us what was wrong with them.

**Who would actually use this?**
People who build and calibrate quantum chips, teams designing error correction around bad qubits, and anyone paying for device time to study rare events. The same click-correlation signals are used on single-photon sources. All of that is potential, not a product: today's version runs small cases, and a classical sampler still wins at this size.

**Why not make the machine fully coherent?**
Because then it can't forget. On the task "does this sequence end with A", a fully coherent machine scored 51%, which is chance, and the hybrid scored 100%. Forgetting is what lets a recurrent model track the recent past. Purifying doesn't change that: it runs the same hybrid inside a bigger reversible circuit, and the click statistics stay the same.

**What does partly reversible mean?**
There are three options. Read and reset, which is cheap and can't be undone. Purify, which rewinds everything for one extra qubit per step. Or rewind only the recent past, which is enough when the machine forgets: 8 steps held a hit rate of 0.80 to 0.87 out to 18. That last one was tested without noise, and it distorts history older than its horizon.

**Did this really run on hardware?**
Yes. Seven jobs on two 156-qubit IBM Heron chips, ibm_kingston and ibm_marrakesh, on 5 November: 337 seconds of device time on the free plan. No circuit used more than 11 qubits. The job IDs are in section 13 of the report, and the predictions were committed before the first job.

**Which QRSM is this?**
The constrained hybrid, in emitter form: coherent memory, and a fresh ancilla that swaps partly with it and is reset. It isn't the trainable or free-unitary hybrid. Purifying defers the resets, so the circuit Grover runs on is fully coherent.

**Why was the chip worse than its noise model?**
The model has gate errors, relaxation during gates and readout errors. It has no crosstalk and no decay on idle qubits. Fidelity fell about 3 times faster per gate than in the model. It still ranked the circuits well, with a rank correlation of 0.95, so it's good for comparing builds and optimistic about how they'll do.

**Did error suppression help?**
Barely. Two identical plain jobs differ, circuit by circuit, about as much as a suppressed job differs from plain, so we don't claim much. Median fidelity on deep circuits rose from 0.50 to 0.53 to 0.55. Textbook Grover at its best reached 0.63. The resilient build got 0.87 with no suppression at all. Cutting gates mattered more.

**Why did dynamical decoupling erase the fingerprint?**
We don't know, and we got it wrong: we predicted twirling was the cause. One untested idea is that fresh light qubits wait in |0>, where idling does them no harm, while DD keeps pulsing them.

**What went wrong on Marrakesh?**
The compiler chose the qubits with the best reported errors, and they did far worse than the others we used: 1.5% to 3.4% per gate in our echoes, against about 0.2% reported. We don't know why. Moving off those five qubits recovered the result.

**Isn't avoiding those qubits cherry-picking?**
It's post-hoc, and we label it so. We picked them from the echo circuits, not from the answers we wanted, and logged the prediction first. The bad run stays in every table.

**Why do you need a fresh qubit for every step?**
Reversibility needs the history kept somewhere. That costs T extra qubits. A dynamic circuit with reset needs only one light, but it can't be rewound. It's a real trade: qubits for invertibility.

**Why a QRSM, and not any other circuit?**
The recurrent structure is what the design uses. The memory is a bottleneck, so a reflection can watch only that and the question's light. The physics-shaped click operator is what makes steering exact. A free-unitary model has neither, and at about 136 two-qubit gates a step it would be far too deep.

**What would you do next?**
Run bigger cases on real hardware, echo-check layouts before trusting them, extend steering to learned models, add error detection, and rewind only as far as the memory reaches.

## Running on real IBM hardware

1. In a terminal in this folder, run `python tools/save_ibm_account.py` and paste your API key at the hidden prompt. Your key is stored by Qiskit in your home folder, never in this repository.
2. `python experiments/run_ibm.py --plan` picks a device, compiles everything and estimates QPU time. It uses no QPU time.
3. `python experiments/run_ibm.py --predict` simulates those exact circuits with the device's noise model, one small circuit at a time. It uses no QPU time. Never give a simulator a circuit compiled for the whole device: that appears to have crashed a laptop.
4. `python experiments/run_ibm.py --submit` sends two jobs: one plain, one with dynamical decoupling and twirling.
5. `python experiments/run_ibm.py --fetch` waits and saves the results. IBM's queue can take minutes or hours.
6. `python experiments/analyse_hardware.py`, then `python experiments/make_figures.py`, make the tables and the charts.

We've done this. The results and all seven job IDs are in section 13 of the report, and the raw counts are in `results/hardware/`. Real hardware is worth up to 8 bonus points, so have a job ID ready if a judge asks.

## Glossary

- **Amplitude.** A qubit state's weight. Its square is a probability, and it can be negative, which is how interference works.
- **Amplitude amplification.** Grover's algorithm in its general form: any starting state, any marked set.
- **CZ.** The two-qubit gate on IBM Heron chips. Two-qubit gates cause most of the errors, so we count these.
- **Conditioning.** Asking "what is this, given that?" For a sampler, that means keeping only the runs where "that" happened.
- **Dynamic circuit.** A circuit that measures and resets in the middle. Ours did, before purifying.
- **Hit rate.** The chance a shot has the event you asked about.
- **Oracle.** The part of Grover that marks the answers you want, by flipping their sign.
- **Purify.** Replace each reset with a fresh qubit, so the whole run is reversible.
- **QRSM.** Quantum recurrent state machine: a recurrent model whose hidden state is quantum.
- **Reflection.** The second half of a Grover iteration: flip everything about the start state.
- **Steering.** Changing one gate so the event is common, in a way that keeps the conditional answer exact.
- **TVD.** Total variation distance: how far a distribution is from the right one. 0 is perfect, 1 is as wrong as possible.
