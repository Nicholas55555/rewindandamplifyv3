# QRSM → Emitter–Defect–Photon: runnable simulation companion

**Status:** Executed synthetic-data proof of concept, not an industrial diagnostic or a quantum-advantage claim.

This standalone Python experiment extends the physics *represented* by the team's hybrid QRSM with an explicit finite-dimensional **bosonic cavity mode**, Lindblad loss/dephasing, photon detection inefficiency, and dark counts. It is designed as a companion experiment to [Rewind & Amplify](https://github.com/Nicholas55555/rewindandamplify), **not a replacement for or an integrated patch to that repository**. We examined the published README and the 23-page deck but did not directly import the repository's implementation.

## Install and reproduce

Python 3.10+; no quantum hardware or Qiskit account required.

Install `requirements.txt` in a virtual environment. First run a small end-to-end check:

```bash
python qrsm_photon.py
python test_model.py
python -m unittest -v test_reproduction.py
python experiment.py --quick --outdir generated/quick
python evaluate.py --data-dir generated/quick
```

The quick run uses 24 records of 16 bins and is a software check, **not** the bundled 600-record result. To reproduce the saved experiment and its held-out analysis in a separate directory, use:

```bash
python experiment.py --records 600 --steps 40 --seed 77 --outdir generated/full
python evaluate.py --data-dir generated/full
```

The defaults are also 600 records, 40 bins, and seed 77, with outputs under `generated/`; `--records`, `--steps`, and `--seed` are explicit to make the documented run unambiguous. Evaluator input and outputs now use the named directory, rather than silently evaluating a different record file. The saved output JSON includes a SHA-256 digest of the input records. The original bundled CSVs, figure, and JSON files at the top level are preserved; writing there is rejected. Existing generated output is protected unless `--overwrite` is explicitly supplied. If replacing an experiment with `--overwrite`, rerun the evaluator with `--overwrite` too; otherwise its previous evaluation pertains to the earlier input (the digest can be used to check). These commands do not install or use quantum hardware.

On systems with a highly threaded BLAS, setting `OPENBLAS_NUM_THREADS=1` before Python may improve runtime; for PowerShell use `$env:OPENBLAS_NUM_THREADS = '1'`. With numeric-library or platform changes, small floating-point differences can occur; verify reproduced data and results rather than assuming bitwise equality.

Generated files: `poc_results.png`, `results.json`, `synthetic_click_records.csv`, `no_defect_control.csv`, and `heldout_evaluation.json` inside the chosen directory.

### Experimental question

**Can a hidden defect–emitter coupling be inferred from noisy binned photon-detection histories without directly measuring the defect?**

The simulated experiment answers a limited version of this question **yes**, under a known generative family and fixed nuisance parameters. It's not yet a demonstrated advantage over the best classical diagnostics.

## Physical model

Tensor order: **defect TLS** \(D\) × **emitter TLS** \(E\) × **cavity** truncated to photon Fock states \(|0\rangle,|1\rangle,|2\rangle\). Default Hilbert space dimension = 2×2×3 = 12. All parameters use **arbitrary internally consistent angular-frequency/time units**; do not interpret them as a calibrated particular optical device.

Rotating-frame Hamiltonian (ℏ=1):

\[
H = \Delta_d\sigma_d^+\sigma_d^- + \Delta_c a^\dagger a
+ \frac{\Omega}{2}(\sigma_e^++\sigma_e^-)
+ g_{de}(\sigma_d^+\sigma_e^-+\sigma_e^+\sigma_d^-)
+ g_{ec}(\sigma_e^+a+\sigma_e^-a^\dagger).
\]

* Emitter drive **Ω** represents a laser-like coherent field in an optical realization, or microwave excitation in a superconducting circuit.
* Defect coupling **g_de** is the parameter estimated from photon clicks.
* Emitter–cavity coupling **g_ec** coherently transfers excitations to a bosonic photon mode.
* Cavity leakage **κ** represents photons escaping the optical/microwave mode. A fraction **η** is registered by the detector.
* Emitter/defect relaxation and pure dephasing are separate *unmonitored* Lindblad channels.
* A separate Poisson dark-count rate represents detector false positives.

The density matrix obeys the Lindblad equation

\[
\dot\rho=-i[H,\rho]+\sum_j \mathcal D[L_j]\rho,
\qquad \mathcal D[L]\rho=L\rho L^\dagger - \tfrac12\{L^\dagger L,\rho\}.
\]

The recorded event `1` means **at least one registered cavity-leak photon in that bin**, or a detector dark count. For bin duration `dt`, the code computes two exact finite-bin, completely positive instruments for the stated Markovian model:

* `E_total = exp(dt L_total)` — trace-preserving evolution after summing over all outcomes.
* `E_0 = exp(-dark_rate × dt) exp(dt (L_total − J_detected))` — zero observed clicks.
* `E_1 = E_total − E_0` — one or more observed clicks.

The post-measurement emitter/defect/cavity density matrix is kept and propagated into the next bin: **hidden memory is not reset.** The code uses `vec(rho)` column-vectorization and ordinary SciPy matrix exponentials. It does not approximate the cavity as a new measured qubit reset on every time step.

**Convergence caveat:** truncating the cavity Fock space changes the photon dynamics. At the default parameters the maximum occupancy of the top `|2⟩` Fock level is about 1.74%. The steady measured click rate shifts from ~0.20933 at cutoff 3 to ~0.21197 at cutoff 4 and ~0.21223 at cutoff 5. Use cutoff 4+ and recheck convergence for serious physical estimates.

## Results from the bundled run

Synthetic experiment, seed=77:

| Quantity | Outcome |
| --- | ---: |
| Observations | 600 independent sequences × 40 time bins |
| True defect–emitter coupling | 0.65 |
| Recovered coupling, fixed other parameters | **0.65** |
| No-defect synthetic control, inferred coupling | **0.00** |
| Simulated detector efficiency | 68% |
| Defect-data mean registered click fraction | 20.26% |
| Holdout split | 420 train / 180 test sequences |
| Rate-matched no-defect drive (trained) | 0.8143 |
| Holdout log-likelihood improvement over brightness-matched no-defect model | **+33.13 nats** |
| Holdout log-likelihood improvement over fitted first-order Markov baseline | **+27.43 nats** |

**Interpretation:** the model can recover a coupling and detect temporal differences that are not reducible to click frequency in this synthetic setting. This is not a significance test for a physical defect; the fitted physical parameters have no reported confidence intervals. The QRSM candidate is evaluated with its other physical parameters already known, so it enjoys a strong modeling advantage. The first-order Markov model is deliberately simple; see the stronger HMM comparison below. A later separate stress test deliberately used incorrect detector efficiency and dark rate on three fresh synthetic datasets, but broad misspecification and real-data validation remain open.

### Stronger classical comparisons

`diagnostics_baselines/` contains a subsequent comparison against trained two- and three-state binary hidden Markov models on the **same reused** synthetic 420/180 split. The fixed-nuisance physical model's held-out log-likelihood lead over the three-state HMM was **5.69 nats in total**, or **0.0316 ± 0.0159 nats per record** (paired standard error), substantially narrower than its earlier 27.43-nat lead over observed-bit Markov-1. The selected fits converged, but most random starts did not meet the stated tolerance within the iteration cap. This exploratory result is conditional on the fitted models, and the physical model knew its generating family and all nuisance parameters. Follow-on fresh-data simulations included one deliberate detector-mismatch setting; they remain from the same synthetic generating family and do not cover broad misspecification. The reused holdout in the original comparison, optimization uncertainty, limited stress tests and lack of real data preclude a general advantage claim. Reproduction, convergence details and conditional bootstrap intervals are in `diagnostics_baselines/README.md`.

## Relation to existing Rewind & Amplify

| Existing hackathon implementation | This companion experiment |
| --- | --- |
| Driven emitter qubit (RY rotation per step) | Continuously driven two-level emitter |
| Defect qubit with phase detuning (RZ rotation) | Two-level defect with Hamiltonian detuning |
| iSWAP-like defect–emitter exchange | Exchange coupling in the Hamiltonian |
| iSWAP-like emitter–light ancilla interaction | Jaynes–Cummings emitter–cavity coupling |
| Binary light qubit measured and reset | Continuous cavity leakage resolved into time-bin click/no-click instrument |
| Purified circuit for coherent Grover-style rewinding | A separate cavity-2 **two-bin** approximate, coherent model with a click-history oracle and one amplification round now runs in an ideal Qiskit simulator. It is not imported into the main package or run on hardware. Actual emission into an open environment is not directly unitary-reversible. |

To connect the ideas, a discretized channel and its click instrument must be **dilated into a reversible circuit including environment ancillas**, under resource limits. The numerical isometry below provides a finite-dimensional construction; the later two-bin experiment demonstrates one ideal Qiskit query of a heavily simplified approximation. This is a standalone research bridge, not a patch integrated into the original repository. You cannot just apply the existing inversion routine to a lossy measurement. The existing repository supports history-based click questions; these CSV files can serve as test histories after checking required order/format. Do not assume exact API interoperability without testing.

### Numerical test of a coherent dilation

`dilation_feasibility.py` is a first mathematical bridge. It converts each finite-bin `E_0`, `E_1` superoperator into a Choi matrix using the simulator's column-vectorization convention, diagonalizes the Choi matrices into Kraus operators, and arranges them into an isometry with an outcome flag and an environment. Choi eigenvalues below an **absolute** cutoff are discarded; the remaining Kraus operators are right-normalized to restore trace preservation, which changes the outcome maps slightly. The program measures both errors rather than treating the approximation as exact.

At the default cavity cutoff of 3, the emitter–defect–cavity space has dimension 12 and is padded to dimension 16 (four system qubits). With absolute Choi cutoff `1e-12`, this run retains **137 no-click** and **133 click** Kraus components. This explicit construction uses **one outcome flag plus eight environment qubits**, or **13 qubits total for one time bin**. It constructs an 8192×16 isometry, not an 8192×8192 unitary. Its completeness error is about `3.1e-15` in spectral norm; the maximum conditional-state Frobenius error across eight seeded pure/mixed inputs and both nonzero branches is about `3.0e-13`. The test suite also checks known complex unitary and amplitude-damping channels and two-step photon histories.

The resource figure applies only to this particular retained approximation and this flagged construction. Exact Choi rank lower-bounds the environment dimension needed to represent an exact channel, and the sum of the two outcome Choi ranks lower-bounds the **combined flag-plus-environment** dimension for an exact flagged representation of that instrument. Here, however, the numerical eigenvalues span many orders of magnitude. At cutoff `1e-10` the retained ranks are 123 and 120, requiring 12 total qubits in this construction; at `1e-12` they are 137 and 133, requiring 13. These are tolerance-dependent numerical results, not certified exact ranks or universal lower bounds for all approximations. Other approximations and structured channel constructions can use different resources. The reported superoperator and sample-state errors are Frobenius norms and are not a certified worst-case operational or diamond-norm error bound.

Reproduce the check without overwriting reference files:

```bash
python dilation_feasibility.py --states 8 --output generated/dilation_new.json
python -m unittest -v test_dilation.py
```

Choose a fresh output path; the script refuses to overwrite an existing file. For highly threaded BLAS, setting `OPENBLAS_NUM_THREADS=1` before launching Python can make the small matrix calculations faster. The saved checked result is `generated/dilation_feasibility_normalized.json`.

A Stinespring isometry can be extended to a unitary mathematically, but we **have not synthesized or compiled that cavity-3 unitary**, estimated its gate count, or implemented it on a photonic processor. The branch flag represents the simulator's binary detected-click outcome, including its dark-count model; it does not directly simulate an optical device. Extending this generic construction over many bins would require keeping the appropriate environment and outcome information coherent before reversal; reusing the same initialized ancillas without uncomputing would not establish reversibility. More compact, physically structured dilations remain an open research question.

### A smaller synthesized circuit

`dilation_synthesis.py` performs a separate, bounded Qiskit isometry synthesis for the **smaller cavity-dimension-2 model** (an 8-dimensional system). It drops Choi components below an intentionally coarse cutoff, applies the trace-preserving normalization described above, embeds a click flag and environment, and transpiles to a generic `u,cx` basis. It checks the whole clean-ancilla isometry on all eight input basis states with a common global phase, verifies the compiled inverse on six input states, and compares both flagged output states against the original simulator for those states.

| Choi cutoff | Retained no-click / click | Total qubits | Generic CX / depth | Original no-click / click superoperator Frobenius error | Largest tested conditional-state error |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.03 | 7 / 4 | 7 | 1,051 / 2,080 | 0.0932 / 0.0851 | 0.0478 |
| 0.003 | 14 / 8 | 8 | 2,086 / 4,142 | 0.0161 / 0.0100 | 0.0164 |

The retained isometries themselves match their compiled circuits to better than `6e-13` in common-phase-aligned spectral norm; the inverse checks are below `8e-15`. That is **circuit synthesis fidelity relative to the retained approximation**. The script checks the retained isometry, synthesized circuit, inverse, and retained flagged branches against a `1e-8` numerical implementation tolerance and exits nonzero if those checks fail. The last two columns separately show that the approximation changes the original channel; they are reported without applying the implementation tolerance. They are not worst-case operational or diamond-norm error bounds; the conditional-state maximum is only over six chosen inputs.

These counts cover one model time-bin isometry, not the full prepare–oracle–reverse–reflect–replay algorithm. They exclude hardware connectivity and noise, multiple time bins, measurements, repetitions, and error correction. They do not establish the cost of the cavity-3 model, a converged optical model, or an experimental photonic processor. Inversion applies to the synthetic circuit and retained coherent environment, not to a measured photon. The separate two-bin query below includes the other stages.

In a virtual environment, install the companion requirements, the tested Qiskit version, and on Windows `pywin32` for the enforced process memory cap. `qiskit` and `pywin32` are optional for the ordinary photon simulator; they are required for this bounded synthesis on Windows:

```bash
python -m pip install -r requirements.txt
python -m pip install qiskit==2.6.1
python -m pip install pywin32
```

Then run:

```bash
python dilation_synthesis.py --cutoff 0.03 --timeout 90 --memory-mb 1024 --max-qubits 7 --output generated/synthesis_new.json
python -m unittest -v test_dilation.py test_dilation_synthesis.py
```

Each synthesis runs in a subprocess with a wall-time limit and per-process memory limit; failure to enforce the memory limit aborts synthesis. The output path must be new. Checked results with the implementation guard are `generated/dilation_synthesis_coarse_validated.json` and `generated/dilation_synthesis_8q_validated.json` (the latter uses `--cutoff 0.003 --max-qubits 8`). Earlier unguarded outputs are retained for provenance. A first setup attempt that failed before computation remains in `generated/dilation_synthesis_coarse.json` as a diagnostic.

### Coherent two-bin rare-click experiment

`two_bin_amplification.py` goes one step further for the **synthetic cavity-2 model**. It uses the normalized Choi-truncated instrument with absolute cutoff `0.03`, prepares two consecutive time bins with separate coherent flags and environment registers, marks either a click in the second bin or clicks in both bins, and applies one full amplitude-amplification round. All environment registers remain coherent so that the circuit can reverse its own preparation. The statevector result is compared with direct two-step channel evolution, including the conditioned hidden emitter–defect–cavity density matrix after the chosen record.

For the checked two-click query, the original cavity-2 instrument assigns probability **0.0017848**; the coarsely approximated instrument assigns **0.0017264**. The actual ideal Qiskit circuit yields the latter before amplification and **0.0154661** after one round. Its selected hidden-state trace distance from the retained model is about `5.1e-13`; the retained versus original selected hidden-state trace distance is **0.0174** for this input and record. These are different checks: the first tests the quantum algorithm against the *retained* approximation; the second shows the approximation changes the *original* channel. They are not worst-case error bounds.

The compiled one-round, two-bin circuit uses **11 circuit qubits, 6,663 generic CX gates and depth 12,672** with the tested Qiskit 2.6.1 generic `u,cx` compiler configuration. Counts include two-bin preparation, marking, inverse preparation, full reflection and replay; they exclude routing, hardware noise, physical photon generation and error correction. The example has not been executed on a QPU. The cavity-2 model is not a converged optical model, and a coarse Choi cutoff was selected to keep the circuit small. No end-to-end speed advantage or physical defect diagnosis is demonstrated. The original `poc_results.png` was generated before this additional standalone experiment and its “no Grover integration” text is a historical snapshot.

To reproduce with Qiskit installed and without overwriting the checked result:

```bash
python two_bin_amplification.py --event double --output generated/two_bin_new.json
python -m unittest -v test_two_bin_amplification.py
```

The checked data are `generated/two_bin_double.json`, and `generated/two_bin_summary.png` is generated from those data using `python plot_two_bin.py`. Use `--event last` to mark a click in the second bin regardless of the first; the tests check that relative selected-history probabilities and the selected system state are preserved in the retained model. This experiment implements amplitude amplification locally in the companion project; it does **not** yet integrate a general arbitrary-time open-system instrument into the original `qrsm_grover` package.

## Key next experiments

1. **Parameter identifiability:** jointly fit coupling, detuning, dephasing, detection efficiency, and drive, with uncertainty intervals; distinguish genuinely recoverable parameters from degeneracies.
2. **Counterfactuals:** extend the initial two- and three-state HMM analysis to independent datasets, a *rate-matched* classical telegraph-noise model, and more flexible classical SSMs.
3. **Time dependence:** use controlled pulse sequences and detuning scans to amplify coherent fingerprints rather than brightness changes.
4. **Model robustness:** test omitted physics—spectral diffusion, multimode cavity, thermal photons, detector dead time, non-Markovian loss, cavity Fock cutoff.
5. **Rare-event conditioning:** extend the two-bin cavity-2 check to additional bins, better-controlled approximations and realistic noise; account for how retaining environment registers and synthesizing oracles scale. Verify a useful crossover against direct classical inference before claiming any advantage.
6. **Applications:** only after these checks, fit fiber-optic or lithography-related **observable** data with appropriate readout (e.g., phase/intensity instead of individual quantum photon counts). Without ground truth, don't claim microscopic defect identification.

## Reference pointers

- Hackathon repository: https://github.com/Nicholas55555/rewindandamplify
- QuTiP 5 dynamics solvers (an alternative future implementation with `mcsolve`): https://qutip.readthedocs.io/en/latest/apidoc/solver.html
- QuTiP photon-counting trajectories: https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-monte.html

The companion is intentionally built with NumPy/SciPy and requires no QuTiP installation. A verified QuTiP cross-check with `mcsolve` is recommended, but **has not been performed** in this environment.
