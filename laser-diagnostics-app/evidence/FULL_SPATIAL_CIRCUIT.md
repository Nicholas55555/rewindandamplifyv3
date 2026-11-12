# Full 7×7 coherent construction and resource study

This implements the **original 49-cell independent-Poisson spatial process** as an explicitly bounded finite quantum circuit. It does not substitute the separate correlated 2×2 example. It closes the construction gap; it does **not** establish a practical quantum advantage or validate wafer physics.

The original process remains Poisson counts on a 7×7 grid, Gaussian spreading with sigma 0.8 and zero exterior boundary, the central 3×3 mean response, and event `response < 0.8`. Its linear response weights come directly from the unchanged original forward function. The new approximation stores capped counts and integer weights with an explicit probability-error budget.

## What was actually built

There are two rounded-weight versions of the same process, using `K = 2^18 = 262,144` and integer weights `floor(K*w_i/0.8)` or `ceil(K*w_i/0.8)`.

1. **Compact construction:** 196 count-data qubits and 23 score qubits, **219 total**. It contains abstract exact multi-controlled-X operations, including a 195-control diffuser gate. These circuits were constructed in Qiskit, but the installed QPY reader rejects the 195-control instruction (`at most 31 are supported`). No working compact QPY is claimed. Files ending `.partial` are failed serialization artifacts, not usable circuit deliverables.
2. **Explicit clean-ancilla implementation:** the same 196 data and 23 score qubits, plus **170 additional clean qubits**, **389 total**. Every multi-controlled-X is represented by its exact ordinary-Toffoli compute/action/uncompute chain. The usable artifacts are `floor_clean_389q.qpy` and `ceil_clean_389q.qpy`. These are actual hierarchical Qiskit circuits with explicit gate definitions, not an assumed free oracle.

The 23 score qubits are occupied during weighted addition and cannot be borrowed as clean scratch then. The oracle uses up to 21 qubits from the separate 170-qubit clean pool. After weighted-sum uncompute, the score register is zero again. The 196-data-qubit reflection requires **193 clean ancillas**; it reuses those 23 clean score qubits plus all 170 extras. Populated count data are never treated as clean workspace.

The largest encoded score is 4,911,870 for floor weights and 4,912,605 for ceil weights, both below `2^23`. Positive additions therefore cannot overflow for any encoded count map. The threshold is a power of two, so the oracle checks only that the **five high score bits are all zero**. It does not enumerate 262,144 acceptable scores.

The complete one-round circuit is preparation, weighted predicate, inverse preparation, zero reflection, and preparation. The state-preparation calls and the diffuser are included in all cost totals.

## Count capping and relation to the original process

Each cell uses four qubits to encode `min(N,15)`. Categories 0 through 14 have their ordinary Poisson probabilities; category 15 contains the full `P(N>=15)` tail. A binary tree of controlled `RY` gates prepares the **exact finite categorical law**, with no assumed free state loader. The count value differs from the uncapped process only when `N>=16`.

For 49 independent cells, a coupling gives the conservative total-variation/error bound

`delta_cap <= 49 * P(Poisson(dose) >= 16)`.

This bounds the effect of count capping on any event. It is not the probability of merely entering the overflow category. Unlike the 2×2 event-specific cap, this cap is an approximation to the full process.

| Mean count per cell | `P(N>=15)` per cell | Bound on any changed count value |
|---|---:|---:|
| 1.5 | 8.2397×10⁻¹¹ | 3.7626×10⁻¹⁰ |
| 1.8 | 9.6004×10⁻¹⁰ | 5.2539×10⁻⁹ |

For uncapped counts, the ceil-weight event is a subset of the original event, which is a subset of the floor-weight event. A compound-Poisson recurrence computes those two bounding probabilities without truncating count tails. A separate finite dynamic program computes the exact capped/lattice event probabilities encoded by the constructed circuits. The finite/uncapped differences satisfy the cap bound; differences near floating-point precision are not interpreted as physically meaningful.

| Dose | Uncapped original-event bracket at this lattice | Finite floor probability | Finite ceil probability |
|---|---|---:|---:|
| 1.5 | [0.004226948015, 0.004237128599] | 0.004237128599302 | 0.004226948014950 |
| 1.8 | [0.0001803041795, 0.0001809410169] | 0.000180941016902 | 0.000180304179471 |

The brackets' relative widths are 0.2406% and 0.3526%. The earlier classical follow-up used a finer lattice and retains tighter reference brackets; the power-of-two lattice here simplifies the reversible predicate. All bounds are evaluated in floating point, not certified interval arithmetic.

The largest absolute event-probability errors consistent with these brackets are about `1.0181e-5` at dose 1.5 and `6.3684e-7` at dose 1.8. These are approximation bounds, not sampling confidence intervals. The finite quantum oracle does not exactly mark the original unrounded event.

A loose conditional-history bound can also be obtained without simulating the large state: let `epsilon = delta_cap + P(floor event) - P(ceil event)` for uncapped counts. Under the natural shared-count coupling, the finite/original record-and-event laws differ only when a count is capped or the rounded predicates disagree. Their joint TV is at most epsilon. Normalizing the accepted distributions gives the conservative bound `conditional TV <= min(1, 2*epsilon/lower_event_bound)`, approximately 0.00482 and 0.00713 for these two doses. This compares the ideal model distributions; it says nothing about a noisy processor.

Amplitude amplification's ideal formula predicts approximately 0.03770450 (floor) or 0.03761493 (ceil) after one round at dose 1.5. These are **analytic predictions from the finite classical probabilities**, not outcomes of a 389-qubit statevector simulation. Conditional relative amplitudes in each finite predicate are preserved ideally by the usual construction; actual large-circuit noisy fidelity was not evaluated.

## Complete gate resources, with a reproducible synthesis upper bound

An exact `c`-control X uses `c-2` clean ancillas and `2c-3` ordinary Toffoli gates for `c>=2`. These chains contain no relative-phase substitutions. Each exact Toffoli was independently compiled to six CX and nine `u` gates. The four-qubit cell preparation was independently compiled to 196 CX and 161 `u` gates. Concatenating those actual small decompositions gives a constructive upper bound for the full circuit; a whole-circuit optimizer may reduce it.

| Full one-round circuit | Qubits | Ordinary Toffolis | Direct CX outside preparation | Constructive generic CX upper bound | Constructive generic `u` upper bound |
|---|---:|---:|---:|---:|---:|
| Floor weights, explicit clean | 389 | 558,496 | 2,320 | 3,382,108 | 5,050,537 |
| Ceil weights, explicit clean | 389 | 473,852 | 2,104 | 2,874,028 | 4,288,741 |

For example, the floor CX count is `6*558496 + 2320 + 3*49*196`. The factor three includes both forward preparations and the inverse. The 387-Toffoli diffuser is already included. Preparation's raw X gates are not counted a second time in the generic `u` total.

These are **unoptimized constructive upper bounds**, not lower bounds, not full generic transpilation, and not routed device counts. The repeated controlled-constant-increment adder deliberately prioritizes explicit correctness over arithmetic optimization. Better adders, synthesis and count preparation could reduce costs. The result therefore does not prove that every useful implementation needs millions of CX gates. It does show that this specific complete implementation is far more expensive than treating an oracle call as free.

No routing, fault tolerance, angle precision budget, scheduling, calibration, gate noise, readout latency, energy or dollar cost is included. No physical gate error was assigned to the full circuit. The existing classical recurrence and finite DP already solve the probability task for this model; a quantum advantage has not been established.

## Bounded validation and failure records

Only the **four-qubit preparation and three-qubit Toffoli** were generically transpiled. No large circuit was submitted for blind generic compilation. No statevector or density matrix of the 219- or 389-qubit circuit was allocated.

Eight behavioral tests cover every four-bit preparation amplitude, exhaustive small clean-chain truth tables and representative 195-control edge cases, absence of hidden relative phases in a smaller superposition, exhaustive small controlled-carry arithmetic, no-overflow/ancilla ledger, actual small oracle uncompute, a small complete Grover round and finite-DP parity. The largest statevector used in these tests is ten qubits. These are compositional correctness checks, not an exhaustive simulation of the large circuit.

Large construction and QPY round-trip workers have a 120-second time guard. The final workers use a **1,536-MB sampled RSS termination guard**, requiring at least four times that amount of available system memory before launch. RSS is polled every 50 ms; this is a termination guard with possible transient overshoot, not an OS-enforced hard memory limit. Small compilation uses 30 seconds and 768 MB. Actual observed peaks and durations are saved per case.

QPY verification compares recursive operation semantics, all gate wiring, metadata and operation counts before saving and after reading. A successful structural round-trip verifies that the explicit construction survives serialization; it is not a hardware execution or an independent physical validation.

`archive/results.json`, `results_after_release.json`, and `results_after_reused_inverse.json` preserve earlier bounded attempts: compact MCX readback was unsupported and floor clean readback exceeded the initial 1,200-MB guard. The original graph was released before load and exact self-inverse subroutines were reused to reduce overhead. The final guard was increased only after checking more than 13 GB of free system memory. Failed/partial QPY files are retained transparently and must not be mistaken for verified deliverables.

## Files and reproduction

Use `results.json` for canonical approximation budgets, construction status, source hashes, QPY hashes, bounded-run diagnostics and synthesis counts. `validation.json` and the independent review receipt record the final checks. The two verified `*_clean_389q.qpy` files are the circuit artifacts. Compact forms remain constructible from source but are not supported by the installed QPY reader.

Run from this directory with the project's audit environment (Python 3.12, NumPy, SciPy, Qiskit 2.6.1 and psutil):

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
python -m unittest -v test_full_spatial.py
python run_construction.py --output my_construction_results.json
python validate_results.py
```

The runner refuses to overwrite its JSON output. It creates or refreshes the circuit artifact filenames in this directory. The probability-bound code imports the unchanged original spatial model and the existing classical follow-up's recurrence; the source hashes of both are included. Run within this repository, not as an isolated copied folder. The verified QPY files include their gate definitions and can be loaded independently with a compatible Qiskit version, using the documented [QPY format](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qpy).

This adds a finite coherent implementation and a defensible resource estimate for the original spatial model. Measured process calibration, stronger spatial physics, optimized arithmetic, practical error handling and an end-to-end comparison remain research work. It makes no claim about chip yield, printed resolution, entangled illumination or a photonic processor.
