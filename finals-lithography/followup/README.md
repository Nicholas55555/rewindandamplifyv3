# Spatial exposure follow-up: actual circuits and stronger classical checks

This isolated follow-up closes two different gaps. It implements a coherent preparation and a reversible spatial predicate for a **new correlated 2×2 Poisson model**, and it checks uncertainty and improves importance sampling on the **existing independent 7×7 model**. Neither is calibrated to a resist, laser, wafer, or manufacturing process. No QPU or cloud service was used, and the original demonstrations and presentation files are unchanged.

The useful result is a reproducible bridge from spatial process assumptions to a complete small circuit, together with evidence that strong classical methods remain essential. **There is no demonstrated quantum advantage.** The exact classical solver is the appropriate baseline for the 2×2 model; a deterministic probability bracket is now also available for the 7×7 model.

## Files to use

| File | Purpose |
|---|---|
| `correlated_spatial_results.json` | Canonical 2×2 exact, sampling, circuit, and noisy-density results |
| `spatial_coverage_refined_results.json` | Canonical original-7×7 reference bounds, pilot choices, and all held-out runs |
| `correlated_spatial_bridge.png` | Spatial correlation, actual circuit probabilities, and conditional error |
| `spatial_coverage.png` | Run-to-run estimates and interval coverage on the original process |
| `model.py`, `quantum.py`, `run_study.py` | Correlated process, exact DP baseline, actual circuits and bounded noise runs |
| `spatial_coverage.py` | Deterministic compound-Poisson reference and independently tuned classical proposal |
| `test_followup.py`, `test_spatial_coverage.py` | Behavioral checks of mathematics, circuits, sampling, and reference computation |
| `validation.json`, `audit_manifest.json` | Executed checks, current artifact hashes, original files reviewed and preserved |

`archive/results.json` is the first successful 2×2 run; the canonical rerun changes dependency-hash scoping only. `archive/spatial_coverage_results.json` is the preliminary reference at a coarser lattice. `archive/spatial_coverage_refined_results.json` precedes a fix to the exposed nondefault-threshold argument in pilot tuning. The default 0.8 results are unaffected and were rerun with the same seeds after that fix. These earlier files are retained for provenance. Use the canonical files above for numerical claims. No preliminary result was substituted for a final result in the figures.

## 1. Correlated spatial exposure, not independent absorption bits

One latent exposure state is shared by four cells: low dose with probability 0.2 and Poisson mean 1.5 counts per cell; high dose with probability 0.8 and mean 2.5. Counts are independent **conditional on** that state. Marginally, different cells have covariance 0.16 counts² and mean 2.3 counts. This models a simple common source fluctuation. These levels and prior are illustrative assumptions, not measured laser statistics.

The response to a count map is

`R = (N00 + 2 N01 + 2 N10 + 4 N11) / 9`.

These weights are the Gaussian response at the bottom-right corner, with sigma `1/sqrt(2 ln 2)` cells, truncated and normalized over this four-cell patch. Contributions outside the patch are excluded. The arbitrary low-response event is `R < 1/3`, equivalently integer score `S < 3`. This is a response surrogate; it does not model chemistry, electron cascades, nonlinear development, optical imaging, or an actual missing contact.

The independent control gives each cell the **same mixed-Poisson marginal distribution**, but draws its dose state independently. Thus its mean and individual-cell distribution match; its spatial dependence does not.

| Exact quantity | Result |
|---|---:|
| Event probability, shared dose | 0.003706565981 (0.3706566%) |
| Event probability, independent cells with identical marginals | 0.001420913206 (0.1420913%) |
| Shared / independent probability | 2.60858× |
| Probability of low-dose state before conditioning | 20% |
| Probability of low-dose state given the low-response event | 88.6089% |

The conditional shift illustrates how an assumed source fluctuation can contribute to low-response histories. It is inference **inside a known model**, not discovery of a real laser fault or causal attribution from wafer data.

### What the finite count encoding preserves

Each cell stores `min(N,3)` in two qubits. The value 3 means “3 or more,” with its exact Poisson tail probability. Every spatial weight is at least 1, so a cell with three or more counts already makes `S >= 3`. Consequently this encoding preserves the chosen event probability, **every accepted original count map**, and the latent-dose posterior given that event exactly. Accepted maps never contain the overflow category.

It does **not** preserve the unconditional distribution above two counts, unconditional mean/variance, or arbitrary other observables. It is an event-specific exact coarse encoding. A different threshold or signed/nonlinear response requires a new argument and generally more state space.

### Strong classical baseline

For each dose component, backward dynamic-program messages evaluate `B[i,b] = P(sum of remaining weighted counts < b)`. The latent state is then drawn from its event-conditioned posterior, followed by four sequential conditional count draws. This samples the exact conditional law **without rejected complete histories**. Setup is `O(number of cells × threshold² × number of mixture components)` for this direct implementation; output is linear in cell count for a fixed threshold. It exploits additive positive weights and conditional independence.

The result agrees with enumeration and, independently, the closed-form component probability

`P(S<3 | lambda) = exp(-4 lambda) × (1 + 3 lambda + lambda²/2)`.

A 20,000-draw sampler check and a separate 40-repeat direct/importance comparison are saved. The importance proposal is prespecified (rates multiplied by 0.35, unchanged latent prior), uses exact uncapped Poisson likelihood weights, and consumes no tuning data. These Monte Carlo methods are supplementary; they do not replace the stronger DP baseline.

### Actual coherent preparation and reversible predicate

The circuit prepares one latent-dose qubit and two count qubits per cell. Controlled `RY` trees load the conditional capped-Poisson probabilities explicitly. No generic amplitude-vector loader or assumed free state-preparation oracle is used.

The structured oracle computes the weighted score into five clean work qubits, marks scores 0, 1, and 2, and reverses the arithmetic. The maximum encoded score is 27, below the five-bit limit. All 512 data components are checked with distinct complex amplitudes to detect phases, permutations, or dirty workspace. A separate test verifies every populated adder mapping. Preparation agrees with all 512 target amplitudes.

The comparator explicitly marks the five accepted count patterns on eight count qubits, leaving the latent qubit unrestricted. It uses nine total qubits but is an enumerated construction that is not a scalable general solution. In this tiny example it is cheaper than the weighted-sum implementation; the result is reported rather than assuming structured arithmetic must win.

| Circuit | Total qubits | Full generic CX count | Ideal event probability |
|---|---:|---:|---:|
| Preparation only | 9 | 144 | 0.00370657 |
| Weighted sum, one round | 14 | 1,052 | 0.03303018 |
| Weighted sum, two rounds | 14 | 1,960 | 0.08994482 |
| Enumerated, one round | 9 | 988 | 0.03303018 |
| Enumerated, two rounds | 9 | 1,832 | 0.08994482 |

All ideal conditional joint distributions agree with the original event-conditioned law within numerical precision (TV below `1e-11`). Counts include preparation, inverse preparation, predicate and reflection; component gate counts cannot simply be added because whole-circuit synthesis can choose different decompositions and use available work qubits. Compilation is Qiskit 2.6.1, `u,cx`, optimization level 1, seed 13, generic connectivity. Counts exclude routing, calibration, reset/readout latency and error correction. The near-peak round estimate in JSON is an analytic formula only; that larger circuit was not executed or compiled.

### Finite noise exposes a fidelity cost

All nine density-matrix cases completed, each under a 90-second subprocess limit and a 256-MB Aer internal memory limit. The exact density simulation uses the full **nine-qubit enumerated circuit**, including preparation. Fourteen-qubit noisy arithmetic was not simulated. Each CX has hypothetical depolarizing parameter `p2`, each `u` gate `p2/10`; independent symmetric bit flips model readout. These are parameters of an assumed channel, not measured gate infidelities or an IBM calibration.

| CX depolarizing parameter / readout flip | Rounds | Raw matching probability | Conditional joint TV |
|---|---:|---:|---:|
| 0 / 0 | 2 | 0.08994482 | approximately 0 |
| 0.0001 / 0.001 | 0 | 0.00461703 | 0.09944 |
| 0.0001 / 0.001 | 1 | 0.03305419 | 0.03834 |
| 0.0001 / 0.001 | 2 | 0.08079012 | 0.02566 |
| 0.001 / 0.01 | 0 | 0.01190763 | 0.32503 |
| 0.001 / 0.01 | 1 | 0.03132490 | 0.19749 |
| 0.001 / 0.01 | 2 | 0.03853294 | 0.18101 |

Noise can create low-count matches, so a higher raw rate is not a higher rate of faithful answers. In these settings, extra rounds improve conditional fidelity relative to noisy preparation alone, while the stronger-noise two-round distribution remains substantially biased. Error is not assumed to grow monotonically with rounds. The reported CX per raw match is narrow gate accounting; it excludes all other costs and does not correct bias. There is no fair runtime, energy, price or quantum-versus-classical advantage claim.

## 2. Resolve the original 7×7 uncertainty gap

This study imports the unchanged `../spatial_model.py`. It retains 49 independent Poisson counts, Gaussian sigma 0.8 with zero boundaries, the central 3×3 mean, and threshold 0.8. It is **not** the correlated four-cell process above. The coherent circuit for the full 7×7 process remains unimplemented.

Because this particular blur/mean is linear, its response is a positive weighted sum of counts. Applying the original forward function to 49 impulse maps gives those weights. Random-map comparison reproduces the original response within `8.9e-16`.

Rounding each positive response weight down or up to an integer lattice bounds the event probability. A compound-Poisson generating-function recurrence computes each bound without truncating any photon-count tail. Four refinements end at response step `4e-7` (two million bins). An independent FFT inversion checks the recurrence on a coarser lattice, agreeing within `1e-15`; Chernoff bounds make FFT wraparound negligible. The final brackets are mathematical discretization bounds evaluated in double precision, **not** certified interval-arithmetic bounds on floating-point error.

| Mean count per cell | Final probability bracket | Relative bracket width |
|---|---|---:|
| 1.5 | [0.004230478068, 0.004231811465] | 0.0315% |
| 1.8 | [0.000180524977, 0.000180608372] | 0.0462% |

The original fixed proposal reduces every central-5×5 rate by 0.6, including cells with very different response weights. The new exponential proposal uses `q_i = dose × exp(-t × weight_i)`, concentrating changes where they affect the response. Full Poisson likelihood ratios keep estimates targeted at the original distribution.

For each dose, a deterministic root first matches the proposal mean response to the threshold. Four fixed multiples of that root (0.75, 1, 1.25, 1.5) each use 10,000 independent pilot maps. The lowest pilot second moment selects the frozen proposal. **All 40,000 pilot maps per dose are counted**; pilot data are excluded from evaluation. One selected proposal per dose is then assessed with 100 independent 20,000-map runs per method. The full study uses 12 million evaluation maps plus 80,000 pilot maps. Re-running for reference refinement reuses the same seeds and is not additional independent statistical evidence.

Direct sampling uses a Wilson binomial interval, including zero-hit runs. Importance sampling uses a nominal normal 95% interval from weighted sample variance; no general finite-sample coverage guarantee is asserted. Coverage counts initially allow for reference-bracket ambiguity; the final refined bounds give identical lower and upper counts below. Wilson uncertainty on the coverage fraction itself is also saved.

| Dose | Method | Empirical SD across runs | Mean estimated SE | Coverage of nominal 95% interval |
|---|---|---:|---:|---:|
| 1.5 | Direct | 0.0004164 | 0.0004548 | 97/100 |
| 1.5 | Original fixed tilt | 0.0002160 | 0.0002035 | 93/100 |
| 1.5 | Pilot-tuned exponential tilt | 0.00004953 | 0.00004832 | 94/100 |
| 1.8 | Direct | 0.0001029 | 0.00009139 | 95/100 |
| 1.8 | Original fixed tilt | 0.00001795 | 0.00001512 | 86/100 |
| 1.8 | Pilot-tuned exponential tilt | 0.000002450 | 0.000002263 | 93/100 |

The fixed proposal's undercoverage at dose 1.8 confirms the earlier concern: the finite-repeat Wilson 95% interval for its coverage is about 77.9–91.5%, below nominal 95%. The tuned proposal reduces empirical SD by 4.36× and 7.32× relative to fixed tilt at these settings, with the extra pilot budget included explicitly. Its 94%/93% observed coverage is compatible with 95% within the uncertainty of 100 repeats; it is **not proof of universal calibration**. Evaluation is conditional on the frozen pilot choice. Additional independent pilot selections, dose settings, and misspecified physics would be needed for broader claims.

## What remains open

The 2×2 process has only one shared mixture variable and an additive response. The 7×7 process has no exposure correlation. Neither includes measured spatial laser covariance, a validated lithography transfer function, chemistry, material layers, or real failure labels. The new circuits do not model light interacting physically with a sensor qubit, and they do not implement entangled illumination or quantum lithography. Those are separate research questions.

For a larger circuit, `n` cells with `b` count bits need at least `n*b` data qubits, latent-state storage, a score register of `ceil(log2(maximum score+1))` bits, and reversible arithmetic. More mixture components and a general conditional probability table increase preparation cost; arbitrary spatial covariance need not retain this compact preparation. General kernels need quantized weights or more arithmetic. Coarse count caps must be re-proved against the chosen predicate. Generic amplitude-loading and oracle calls cannot be assumed free.

The next useful physics step is to replace the one common dose state with independently measured source and local-process statistics, while retaining a strong exact or importance-sampling baseline. A quantum case becomes scientifically interesting only if the validated model becomes hard for those baselines **and** coherent preparation, reversible physics, error and total resources remain competitive. No wafer-yield improvement follows from these toy results.

## Reproduce

The recorded environment is Python 3.12.10, NumPy 2.3.1, SciPy 1.18.1, Qiskit 2.6.1 and Qiskit Aer 0.18.2. Matplotlib is needed only for figures. The audit interpreter used was `C:\Users\nicho\AppData\Local\Temp\rewind_audit_bh37e7ud\venv\Scripts\python.exe`.

From this directory, with that environment active:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
python -m unittest discover -p 'test_*.py' -v
python run_study.py --output my_correlated_rerun.json --timeout 90
python spatial_coverage.py --output my_coverage_rerun.json
python plot_results.py
python validate_artifacts.py
```

Numerical runners refuse to overwrite their output. All density simulations are bounded subprocesses; timeouts/errors are recorded as unavailable, never invented numbers. Plots use only the canonical saved JSON. Simulator timings are descriptive local run times, not hardware benchmarks or fair algorithm timing comparisons.

## Literature context, not parameter calibration

Real EUV photon, absorption and chemical fluctuations motivate studying rare process outcomes; the IBM paper does not validate this model or its numbers. [Church et al., stochastic variation in EUV patterning](https://research.ibm.com/publications/fundamental-characterization-of-stochastic-variation-for-improved-single-expose-extreme-ultraviolet-patterning-at-aggressive-pitch).

Importance sampling is an established competitor for rare missing-via outcomes in more developed stochastic models. Our exponential tilt is a simple independent-Poisson construction and is not a reproduction of the cited Gaussian random-field method. [Pan et al., importance sampling for EUV vias](https://resources.sw.siemens.com/sl-SI/technical-paper-importance-sampling-in-gaussian-random-field-euv-stochastic-model-for/).

State-preparation cost can erase a Monte Carlo-style quantum query advantage; explicit construction and whole-circuit counts are therefore part of this experiment. We use amplitude amplification for conditional samples, not quantum amplitude estimation of a failure rate. [Carrera Vazquez and Woerner, efficient state preparation](https://research.ibm.com/publications/efficient-state-preparation-for-quantum-amplitude-estimation).
