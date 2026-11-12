# Rewind & Amplify, on one page

Code, results and raw hardware counts: https://github.com/Nicholas55555/rewindandamplify

**FGCU Quantum Hackathon, IBM Qiskit Fall Fest, November 2026**

## The problem

The most useful events in a quantum system are often rare. A chip's hidden defects show up in rare patterns of clicks from one qubit's readout. To study what happens around a rare event, you normally run the system again and again and throw away every run where it didn't happen.

That gets expensive fast. Matching one real 64-step record from our model takes about **27 million runs**.

## The idea

Grover's algorithm is a famous quantum method that makes rare answers common, using about the square root of the work. We wanted to use it on our model, a **quantum recurrent state machine (QRSM)**: a small quantum circuit that behaves like a recurrent neural network.

It doesn't just bolt on. Grover has to run the machine backwards, and our machine resets a qubit at every step. A reset can't be undone. **You can't Grover what you can't rewind.**

## What we built

Grover is also fragile, because noise punishes deep circuits. So we made the machine reversible, then redesigned Grover around noise. The result is four moves:

| move | what it does | why it matters |
|---|---|---|
| **1. Purify** | a fresh qubit replaces every reset | the whole run can now be rewound, and it holds every possible history at once |
| **2. Steer** | tune one gate so the event is common | part of the rarity disappears for free, and the answer stays exact |
| **3. Amplify locally** | one Grover round, checking 3 qubits instead of all of them | far fewer gates, so far less noise |
| **4. Verify** | the event is measured directly | a failed run shows itself and is dropped |

## What we found

- **It works exactly.** On real Qiskit circuits with no noise, Grover’s curve matched theory to 14 decimal places, and the conditional answers were exactly right.
- **The cost falls dramatically.** Conditioning on a real 64-step record went from 27 million runs, to 6,240 with steering, to 125 with Grover on top. Most of that gain comes from steering, which is a classical trick. Grover adds about 50 times on top.
- **The resilient build beat textbook Grover on noise.** Across five IBM device models it used **3 to 5 times fewer** two-qubit gates, and gave better answers.
- **It held up on real IBM chips.** On ibm_kingston, the resilient build hit a rare event **87%** of the time with 40 two-qubit gates. Textbook Grover managed **59%** with 213. Across five jobs it won all 20 comparisons. The chip punished long circuits about 3 times harder per gate than its own noise model said.
- **It can answer a real physics question:** what happens right after a rare click? With no defect, a click wipes the machine clean. A hidden defect remembers across the click, and that shows up as a fingerprint. On real chips it came through at about 6 standard errors, where plain sampling never passed 2.
- **The chips taught us something simulation couldn't.** On our second chip, the qubits that looked best in the calibration data did far worse than the others we used. Our noise checks caught it, and moving off them recovered the result. That's the problem this project starts from: trouble that only shows up in the clicks.
- **A teammate's idea became the other half of the design.** A QRSM can also read a vague request word by word and mark the matching entries. It found the right table for 19 of 20 vague requests.

## What we don't claim

**There is no speedup today.** At this size an ordinary computer gets an exact answer in about a millisecond. Our real-chip runs are small, at most 11 qubits and 5 steps, and the rest of the results are simulation, including the IBM noise models. Amplifying a rare event like this was published in 2014. We rewind a model of a chip, never a real chip. The keyword search has no speed advantage at all.

## Why it could still matter

A classical computer's cost grew about 6 times with each hidden qubit in our tests. A quantum circuit's cost grows slowly. IBM's published target for 2029, 200 logical qubits and 100 million gates, would by our rough estimate fit a machine with 50 hidden qubits, whose memory alone would take about 18 petabytes to hold classically. That's the regime this design is built for, and the resilience work makes the job about 66 times smaller.
