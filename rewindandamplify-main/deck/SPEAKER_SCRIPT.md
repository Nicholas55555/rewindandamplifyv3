# Speaker script

Generated from the slides by `tools/render_deck.py`. Times assume 140 words a minute with a short pause per slide.

## 1. Rewind & Amplify  (0:00)

Hi, we’re presenting Rewind and Amplify. In the next fifteen minutes: how we fused Grover’s algorithm with a quantum recurrent model, what broke when we tried, the noise-resilient design that came out of it, and how that design did on real IBM chips. The orange tick in this click record is the kind of rare event this talk is about.

## 2. Rare events hold the answers, and cost the most to see  (0:27)

Quantum chips are held back by tiny hidden defects. You can’t put a probe on one. What engineers get is one qubit’s readout: click or no click, step after step, and the defect’s fingerprint is hiding in rare patterns of those clicks. Rare means expensive. Matching one real 64-step record from our model takes about 27 million runs. To learn what a chip does around a rare event, you pay for all the runs where it didn’t happen. That hits the people who calibrate chips, and anyone paying for quantum time.

## 3. The real-world problems this work is for  (1:08)

So why does this matter outside a hackathon? Four real problems. First, microscopic defects drift in and out of resonance with qubits, and they’re the leading explanation for the biggest swings in qubit lifetime. Second, calibration data can miss them. In our own runs, the qubits that looked best on one IBM chip were several times worse than reported, and a short echo circuit caught it. Third, error correction can quarantine a bad qubit, but something has to detect it first. Fourth, studying rare events costs real money: at IBM’s rate, matching one record by brute force is about twelve thousand dollars. The same signals appear in single-photon sources too. To be clear about where we stand: we’ve found defects in simulation. We haven’t yet read a real defect from a real chip.

## 4. Our model: a quantum recurrent state machine  (2:07)

Here’s the model. A QRSM is a recurrent network whose hidden state is quantum. Ours is the hybrid kind: coherent memory, and a fresh qubit that carries information away. Each step, an emitter is driven, a hidden defect turns, the two swap energy, and the emitter may give off light. We read the light, click or no click, then reset it. Earlier this week we showed this model can find a hidden defect from clicks alone, leaving under a tenth of a percent of the error, where a tuned LSTM leaves seventeen percent. But a model like this only generates. To ask it a question, all you can do is run it and throw runs away.

## 5. One step of the hybrid QRSM, as a circuit  (2:59)

Here’s that same step as a circuit, on three qubits. The emitter and the defect are the memory, and they’re never measured. RZ turns the defect, RY drives the emitter, and two partial swaps move energy: between defect and emitter, then from emitter to light. Then the light is read and reset. That reset is what makes this a hybrid: information leaves, so the memory can forget. Keep an eye on that reset. It’s about to matter.

## 6. Asking it a question means throwing runs away  (3:34)

This is the wall. Conditioning on a record means keeping only the runs that match. That costs one over p runs, and every extra step multiplies it. The grey line is plain sampling, climbing into the tens of millions by 64 steps. The blue line is what Grover’s algorithm promises: the square root of that. So our team’s idea was simple to say: use Grover to search the machine’s own histories. The question was whether that could work at all.

## 7. Grover’s algorithm in one minute  (4:10)

Here’s Grover’s algorithm for anyone who hasn’t met it. A quantum computer can hold every possible answer at once, each with a weight. Step two: flip the sign of the answers you want. That changes nothing you could measure yet. Step three is the clever part: flip every weight around the average. The one you marked jumps up, and the others shrink. That’s interference doing the work. Repeat a few times, and a ten percent chance becomes nearly certain in just two rounds. Searching N things takes about the square root of N rounds. One warning: go too far and it overshoots.

## 8. Grover’s algorithm, as a circuit  (4:56)

Here’s the same thing as a circuit, with the same three steps across the top. A prepares every answer at once. The oracle marks the ones we want, and for a click at one step that’s a single Z gate. The reflection about the average is really three pieces: rewind with A-dagger, flip the sign of all zeros, and replay with A. That’s one iteration, and you repeat it r times before measuring. Now look at that A-dagger. The machine has to run backwards.

## 9. You can’t Grover what you can’t rewind.  (5:34)

So can we just bolt Grover on? No, and our own research note said why. First, every Grover round runs the machine backwards, and our machine resets a qubit every step. A reset throws information away, so it has no inverse. You can’t Grover what you can’t rewind. Second, a hidden quantum state is not a database. It’s a compressed memory, with no records to look up. Third, fewer queries doesn’t mean less time, because rewinding and reflecting cost gates, and on real chips gates cost errors. Each of these needs a real answer.

## 10. Move 1: Purify. A fresh qubit replaces every reset  (6:16)

Here’s the first move, and the key to everything else. Instead of reusing one light qubit and resetting it, we give every step a fresh light, and measure nothing until the end. By the deferred measurement principle the click statistics can’t change. But now the whole run is one reversible circuit, and that state holds every possible click history at once, each with an amplitude equal to the square root of its probability. So Grover’s search space is the machine’s own past. We checked: amplitudes match the exact model to ten to the minus sixteen, and the two circuits click alike over a million shots each.

## 11. Grover now searches the machine’s histories  (7:04)

And it works. These dots are real Qiskit circuits, using Qiskit’s grover operator on the purified machine, and they sit right on Grover’s curve for all six questions we tried. The more important thing is on the right. Amplification doesn’t just find an answer, it reweights. Inside the matching histories, the relative odds never change. So every shot is an honest sample of the conditional distribution, with the hidden qubits right too. That’s conditioning. And it scales: at a one in a million event, it takes 725 times fewer machine calls, counting every rewind.

## 12. Why a partly coherent, partly reversible QRSM  (7:46)

Why build something only partly coherent, and only partly reversible? Look at the extremes. A fully coherent machine can’t forget: on a simple task, does this sequence end with A, it scored 51 percent, which is chance. A fully measured machine is just a classical automaton. The hybrid sits between them, and it learned that task perfectly. The same goes for reversibility. Forward only, Grover can’t run. Purifying rewinds everything, at one qubit per step. But a machine that forgets may only need its recent past rewound: eight steps held up out to eighteen, in noiseless tests, though older history gets distorted. That’s why this matters. It’s where three fields meet: a probability model with quantum memory, a sequence model with three physical numbers, and an open quantum system that becomes reversible once you add qubits.

## 13. Noise punishes depth, so we redesigned around it  (8:46)

Now the honest problem. Grover is famously fragile, because every iteration rewinds the whole history and checks every qubit. Compiled for an IBM chip, the textbook version at five steps needs 456 two-qubit gates. At today’s error rates, most of those runs have a mistake in them. We don’t need this to be practical on today’s chips. But it made us ask a better question: what would a version built around noise look like? We ended up with four moves. Purify you’ve seen. Steer, and amplify locally, are new, and they’re the next two slides.

## 14. Move 2: Steer. Part of the rarity is free to remove  (9:29)

We found this one by accident, chasing why a crude approximation gave an exact answer. A click is rare for two reasons. Was the emitter excited? And did it emit? The second is just one gate angle. Turn it up, and every history that clicks there scales by the same number, so the conditional answer stays exactly right. For a real 64-step record, that takes 27 million runs down to about six thousand. Then Grover takes what’s left down to 125 calls. To be clear on the credit: steering is classical importance sampling. And if you tune the chance to exactly a quarter, a single Grover iteration gives certainty.

## 15. Move 3: Reflect only where the question looks  (10:18)

Move three attacks the most expensive gate in Grover: the reflection, which has to check every qubit. So we asked how much it really needs to look at. Watching only the two memory qubits looked great. The hit rate held up. Then a harder test showed the hidden state was scrambled, on the right here in yellow. Hit rate alone would never have shown that. The maths said why: what’s missed is the light the question marks. So watch that too. That’s the green line: three qubits, whatever the record length, and almost exact on short records. It does drift on long ones, and we’ll say so.

## 16. Across five IBM device models: fewer gates, better answers  (11:05)

Here’s the test, on five IBM device snapshots, none of them the one we developed the idea on, with circuits compiled for each device and simulated with its noise model. Left: two-qubit gates, with textbook Grover in blue and the resilient build in orange, three to five times fewer. Middle: the chance of getting the event. Right: how far the distribution is from the exact answer. In all 20 combinations of device and length, orange beat textbook on both. So a cheaper, slightly approximate circuit beats the exact one, because the error it adds is smaller than the noise it avoids. Grey has the least distortion, but it throws away over 90 percent of its shots.

## 17. Now it can answer a physics question  (11:57)

So what can you do with this? Here’s a real physics question: what happens right after a rare click? This curve is g-two, the correlation optics labs measure. With no defect, a click wipes the machine clean, so what follows simply restarts the run. With a hidden defect the curve differs from the very first step, because the defect remembers across the click. That’s a fingerprint of hidden memory, and you can only read it by conditioning. So we amplify the click and keep running: Grover inside the recurrent loop. On noisy device models, at the same 4,096 shots, that lifts the separation between defect and no defect from 2.4 to 7 standard errors. And on real chips, in three runs without suppression, we measured about 6, where plain sampling never passed 2.

## 18. The other slot: a QRSM as the oracle  (12:56)

Timofey’s idea fits the other half of the architecture. Grover has two slots: what to search over, and what counts as a match. So far a QRSM has filled the first. Here a reader QRSM fills the second. It reads a vague request one token at a time, and each token turns the phase of every table that contains it. A full match gets a normal Grover mark, and a partial match gets a partial boost, which is what makes a vague search possible. It found the right table for 19 of 20 requests, and on a real chip, 8 entries gave the right one about 85 percent of the time. The honest part: the oracle is compiled from the catalogue, so this shows the architecture, not a speedup.

## 19. Demo: real circuits, about a minute, no account needed  (13:53)

Here’s all of that running: one script, real Qiskit circuits, about a minute, no account needed. First, a rare click: plain sampling gets 8 percent usable shots, and steering plus one Grover iteration gets all of them. Second, what follows the click: the amplified answers match the exact filter, with and without a defect. Third, Timofey’s search lands on the right table. The repository also has an interactive lab, where you can watch runs change as you switch builds.

## 20. On a real IBM chip, fewer gates won  (14:29)

This isn’t only simulation. We ran the same 39 circuits on IBM’s Kingston chip, using at most 11 of its 156 qubits, and we committed our predictions before spending any device time. Same rare click, three steps. Plain sampling hits it 6 percent of the time. Textbook Grover, with 213 two-qubit gates, gets 59 percent. The resilient build, with 40 gates, gets 87. Its answers are better too: distribution error 0.06, against 0.26. A repeat run gave almost the same numbers. Across five jobs and both record lengths, it won all 20 comparisons. And look at the diamonds: the chip was harsher on depth than its own noise model, so the gap came out twice as wide as simulation said.

## 21. What only the real chips could teach us  (15:23)

Here’s what only real chips could teach us. Each row is one job. First, fidelity fell about three times faster per gate than the device’s own noise model said, which is why cutting gates matters so much. Second, error suppression isn’t free. Dynamical decoupling helped textbook Grover a little, but it erased the physics fingerprint, which two plain runs read at about 6 sigma. We predicted twirling was the cause, and we were wrong. Third, on our second chip, the compiler chose the qubits that looked best in the calibration data, and they turned out to be the worst we ran on. Our echo circuits caught it. Moving off those five qubits brought the result back, fingerprint included. We don’t know the cause. And we chose those qubits after seeing the data, so that job tests the explanation. It isn’t a clean replication.

## 22. What we don’t claim  (16:26)

We want to be straight about the limits. No speedup today: a classical sampler gives an exact answer in about a millisecond. We rewind a model of the chip, never the chip, because a physical defect can’t run backwards. Steering is classical, and exact only for clicks at known steps. The local reflection is an approximation that drifts on long records. Our hardware runs are small: at most 11 qubits and 5 steps. And the core idea isn’t new: amplified rejection sampling was published in 2014. What’s ours is applying it to hidden quantum models, and the design work to make it survive noise.

## 23. Why it has potential: where the classical baseline runs out  (17:13)

So why does this have potential, when today it loses to a laptop? Because of where each side runs out. Conditioning on a 64-step record takes about 2.7 million gates as textbook Grover, and about 40,000 once steered. Not today’s hardware. But IBM’s published target for 2029 is 200 logical qubits and 100 million gates. That would fit a machine with 50 hidden qubits and a 150-step record, and just holding that memory classically takes about 18 petabytes. That’s a rough estimate, not a result, but it’s where our classical baseline stops working.

## 24. What we learned, and who did what  (17:55)

Three things we’ll take away. Reversibility is a design choice: one reset decides whether Grover is possible at all. Exact isn’t always best: on noisy hardware, a cheaper, slightly wrong circuit beat the exact one. And test what you can’t see: our hit rate looked perfect while the hidden state was scrambled, and the calibration favoured a chip’s bad qubits. To be open: the QRSM model existed before the event, the Grover fusion is new this week, and we built this with AI assistance from Claude. The code, tests and every result are in the repository. Thanks for listening.

## 25. Backup: the QRSM family, and where ours sits  (18:39)



**Total: about 18.7 minutes.**
