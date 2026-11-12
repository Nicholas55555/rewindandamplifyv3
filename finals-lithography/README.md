# Missing-via rare-event demonstration

This is a **synthetic, uncalibrated teaching model** of one manufacturing question: what histories might lead a contact or via to fail to print? It is a bridge from Rewind & Amplify's rare click histories to rare process histories. It is not a realistic EUV resist simulator, industrial tool, measured photon experiment, or evidence of quantum advantage.

## Model

Five independent sites each have absorption probability `p = 0.8`. The contact fails when fewer than two sites absorb. The two-outcome rule and parameters are deliberately chosen for an inspectable 32-history example; they are not calibrated to a specific resist, wavelength, dose, or manufacturing process. Real lithography also involves correlated absorption, secondary electrons, resist chemistry, blur and processing. Here the exact failure probability is `0.00672`.

The script compares equal numbers of independent records:

* **Direct Monte Carlo:** sample from the original model, count failures.
* **Importance sampling:** sample from a lower absorption probability `q = 0.3`; weight every sampled failure by `(p/q)^k * ((1-p)/(1-q))^(5-k)`. This produces an unbiased estimate of failure probability when `0 < p,q < 1`; self-normalized conditional history estimates are consistent but generally biased at finite sample size.
* **Exact enumeration:** calculate the failure probability and conditional history distribution. Report total variation distance for the two observed conditional histograms and standard errors of probability estimates (one standard error, not a confidence interval). A case with no sampled failures has no conditional estimate. The JSON standard error is `null` when all sampled contributions are equal, including zero observed failures: a zero sample variance in such a case does not establish that the true uncertainty is zero.

The importance proposal is selected in advance for this teaching example. A fair real benchmark must count proposal design, model costs, tuning, and uncertainty, compare against strong domain baselines, and test where assumptions fail.

## Run

Python 3.10+; the classical portion uses only the standard library.

```bash
python lithography.py
python lithography.py --json
python -m unittest -v test_lithography.py
```

Optionally, install Qiskit in a virtual environment and run `python lithography.py --quantum`. This builds and simulates a real **ideal, noiseless Qiskit circuit**, using five qubits and a phase oracle that explicitly marks each of the six failing patterns. The JSON report includes numbers of preparation, inverse-preparation, oracle and zero-reflection calls, the event probability before and after amplification, conditional-distribution error, and circuit depth and CX count after transpilation to a generic `u,cx` basis. Counts are compiler- and basis-dependent and are **not hardware performance**. This enumeration-based oracle does not scale to realistic process sizes. Qiskit is optional; the classical demonstration is available without it.

Use `python lithography.py --quantum --iterations 1` to inspect one round or `--iterations 0` for the preparation alone. By default, the demonstration chooses the integer number of rounds closest to the first ideal amplification peak; this is not a claim that no later peak could be higher. The compiled circuit is device-independent: it does not include physical connectivity constraints, noise, measurements, repetitions, error correction, or a hardware runtime estimate. Counts cover the circuit's preparation, all marking and reflections, and the final preparation in the selected number of rounds.

The quantum demonstration amplifies **conditional examples** of failure. It does not estimate a real process's failure probability, and the circuit does not load real wafer data. No optical photonic quantum processor, hardware advantage, or reduced manufacturing defect rate has been shown. Comparing classical and quantum runtime fairly would include preparation, oracle construction, repetitions, error correction, and computational resources.

JSON output includes `model`, `exact`, `direct_monte_carlo`, `importance_sampling`, and (with `--quantum`) `qiskit_statevector`. `conditional_histories` maps a bit string to its probability. String position `i` corresponds to site/qubit `i`.

**A stronger exact classical baseline:** `viability_cost_study.py` derives the conditional distribution for this particular independent, identical-site threshold and samples matching histories directly, without rejecting whole trials. Its synthetic noise-model round sweep also shows that a higher matching-bit rate can coincide with more biased conditional histories. See `VIABILITY_COST_README.md` and `viability_cost_tradeoff.png` for the derivation, routed costs and scope. This exact shortcut is special to the simple binary toy and is not an implementation for the 7×7 spatial process.

## One-round circuit-size experiment

`scaling_study.py` varies the number of independent binary sites from 3 to 7, keeps the per-site absorption probability at 0.8 and the failure rule at fewer than two absorptions, and simulates **one** ideal Grover round in each case. The circuit explicitly marks each failing history. Regenerate the results with Qiskit installed:

```bash
python scaling_study.py --output scaling_results.json
python -m unittest -v test_scaling_study.py
```

The checked run used Qiskit 2.6.1 and transpiled to a generic `u,cx` basis at optimization level 1:

| Sites | Original failure probability | Ideal probability after one round | Generic CX gates | Generic depth |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 10.400% | 69.441% | 30 | 55 |
| 4 | 2.720% | 22.737% | 84 | 157 |
| 5 | 0.672% | 5.940% | 252 | 449 |
| 6 | 0.160% | 1.434% | 656 | 809 |
| 7 | 0.0371% | 0.3337% | 1,098 | 1,162 |

For these settings a fixed single round does not keep the event common as the original probability shrinks, while the tested compiled circuits get larger. This is a small demonstration, **not a general scaling law or a physical feasibility conclusion**. Different rounds, efficient oracles, compiler versions, hardware topology, and noise can change the result. The explicit oracle, state preparation, sampling repetitions, layout, hardware errors, and eventual error correction all matter. The JSON records ideal expected shots and preparation/inverse-preparation calls per accepted event as query-accounting examples; they are not measured runtimes and do not compare fairly against optimized classical methods on their own.

### A structured failure oracle

`oracle_comparison.py` asks whether the earlier oracle's explicit enumeration of each failing history is necessary for this particular toy threshold. Its second construction coherently counts absorptions into a clean binary counter, flips the phase if the count is 0 or 1, then **uncomputes the counter**. This marks the same histories, without listing each one separately. The complete one-round circuits are compared after compilation using the same Qiskit generic `u,cx` basis and optimization settings; every data-basis input is checked with the work register initialized to zero.

| Sites | Enumerated: CX / depth / qubits | Counter: CX / depth / qubits |
| ---: | ---: | ---: |
| 3 | 30 / 55 / 3 | 42 / 71 / 5 |
| 4 | 84 / 157 / 4 | 175 / 302 / 7 |
| 5 | 252 / 449 / 5 | 221 / 379 / 8 |
| 6 | 656 / 809 / 6 | 269 / 465 / 9 |
| 7 | 1,098 / 1,162 / 7 | 317 / 549 / 10 |

For these small examples, the counter version needs fewer compiled CX gates for 5–7 sites and more for 3–4 sites; it also needs extra work qubits. Both implementations reproduce the ideal marked probabilities and conditional distributions within numerical precision. These are device-independent simulator results with a particular decomposition, not hardware results, a general scaling theorem, or an end-to-end quantum advantage. They do **not** implement the different spatial Poisson/blur model below.

```bash
python oracle_comparison.py --output oracle_comparison_results_new.json
python -m unittest -v test_oracle_comparison.py
```

The script refuses to overwrite an existing output file; the checked data is `oracle_comparison_results.json`. Routing, noise, measurements, repetitions, error correction, and strong classical comparisons remain outside these counts.

### Target-aware synthetic-noise pilot

`oracle_noise_pilot.py` repeats the two one-round constructions for 5 and 7 sites, after compiling both against the **same synthetic 10-qubit line target**. The target is Qiskit's seeded `GenericBackendV2`; its properties are randomly generated from historical ranges, and Aer builds a noise model from those properties. This is **not a real IBM device snapshot or a QPU run**. The two circuits can receive different layouts and use different numbers of physical qubits, so changing the oracle does not isolate the effect of a single variable.

The checked run uses 256 shots per circuit and gives raw, uncorrected output:

| Sites | Oracle | Routed CX | Depth | Accepted shots | Conditional-history TV |
| ---: | --- | ---: | ---: | ---: | ---: |
| 5 | Enumerated | 565 | 729 | 17 / 256 | 0.409 |
| 5 | Counter | 554 | 710 | 14 / 256 | 0.214 |
| 7 | Enumerated | 2,751 | 3,047 | 16 / 256 | 0.265 |
| 7 | Counter | 830 | 1,061 | 4 / 256 | 0.552 |

Only 4–17 accepted shots are available per case. The conservative 95% finite-shot bounds for all four conditional-TV estimates span `[0, 1]`, so this pilot cannot establish which oracle gives a more accurate conditional distribution. The seven-site enumerated hit rate is 6.25%, exactly the fraction of uniformly random 7-bit strings that meet the predicate; noise-induced hits could therefore explain the observed frequency. A larger hit rate on its own is not evidence of correct amplification. The JSON records per-case counts, raw hit-rate Wilson intervals, layout, active qubits, seeds and error-bound assumptions. Its intervals cover independent simulation-shot uncertainty only, not noise-model mismatch, real hardware drift, or calibration uncertainty.

```bash
python oracle_noise_pilot.py --shots 256 --output oracle_noise_pilot_results_new.json
python -m unittest -v test_oracle_noise_pilot.py
```

The script refuses to overwrite an existing output file. The checked result is `oracle_noise_pilot_results.json`. Depending on the machine, this stochastic trajectory simulation can take several minutes. The separate generic ideal comparison remains the appropriate place to inspect exact oracle behavior.

### Deterministic analysis of that same synthetic noise model

`oracle_density_pilot.py` uses Aer density-matrix evolution on the **same seeded synthetic target and compiled circuits**, so it calculates probabilities without shot sampling. It compacts the circuit to the physical qubits actually used, remaps their local gate errors, and then applies the target's independent readout matrices to the saved data-qubit probabilities. Its compaction and noise mapping were checked against Aer built directly from a small complete target. The resulting measures still depend entirely on this synthetic noise model and the differing compiler-selected layouts.

| Sites | Oracle | Routed CX | Raw modeled hit probability | Modeled conditional-history TV |
| ---: | --- | ---: | ---: | ---: |
| 5 | Enumerated | 565 | 8.684% | 0.0924 |
| 5 | Counter | 554 | 5.398% | 0.0743 |
| 7 | Enumerated | 2,751 | 5.268% | 0.1277 |
| 7 | Counter | 830 | 1.386% | 0.0722 |

The ideal one-round hit probabilities are 5.940% at 5 sites and 0.3337% at 7 sites. In this particular noisy model, the seven-site observed hit probabilities are far above the ideal values; many marked outputs can therefore arise through error, and a higher hit rate should not be read as better amplification. The two counter circuits have lower modeled conditional TV here, but this is **one synthetic target and compilation**, not evidence that they win on actual hardware. No finite-shot interval is needed for the density-matrix values; this does not quantify model, calibration, compiler, or hardware uncertainty.

```bash
python oracle_density_pilot.py --sites 5 --timeout 45 --memory-mb 512 --output density_n5_new.json
python oracle_density_pilot.py --sites 7 --timeout 45 --memory-mb 512 --output density_n7_new.json
python -m unittest -v test_oracle_density_pilot.py
```

The saved results are `oracle_density_n5.json` and `oracle_density_n7.json`. Each case runs in a subprocess with a wall-time limit; an incomplete case is labeled and the command exits nonzero. The memory setting limits Aer's internal allocation, not total operating-system memory. The script refuses to overwrite an existing result.

## A separate spatial application example

`spatial_model.py` is a second, **classical** toy model: it draws independent Poisson absorption counts on a 7×7 grid, spreads them with a Gaussian kernel, then compares the average response in a central 3×3 contact with a threshold. The blur is a crude mathematical proxy for spreading, not a calibrated electron cascade or resist-chemistry model. The Gaussian filter treats the area beyond the finite grid as zero, so the boundary can affect responses near the edge. All parameters are arbitrary dimensionless quantities. It does not model real wafer data, a photonic quantum processor, or a quantum circuit for the 7×7 case.

To regenerate the checked figure and its numerical source, install NumPy, SciPy, and Matplotlib, then run:

```bash
python spatial_model.py --shots 50000 --seed 77 --json-output spatial_results.json --figure spatial_demo.png
python -m unittest -v test_spatial_model.py
```

At the default synthetic parameters, the checked run gives a direct failure estimate of **0.004040 ± 0.000284** (one estimated standard error) and a weighted importance-sampling estimate of **0.004193 ± 0.000107**. Each method draws 50,000 maps. The proposal intentionally draws more low-dose histories in the central region and corrects them by the exact Poisson likelihood ratio. Its 15,790 unweighted proposal failures are **not** the failure probability of the target model; the event-weight effective sample size is about 1,490. The reported uncertainties are estimated from the sampled contributions and do not include model error or the cost of designing a proposal. A sample with identical contributions (including no observed failures) reports the standard error as unavailable rather than zero.

The spatial model and the five-site circuit above are **different models**. A coherent state preparation and reversible oracle for the spatial example have not been constructed. An important research question is whether the additional physics can be represented and queried at an acceptable cost, while comparing against validated process simulators and strong classical rare-event methods.

### Check run-to-run variation

Importance weights can vary substantially, so a single run's estimated standard error should not be treated as guaranteed accuracy. The command `python replication_check.py` performs a descriptive diagnostic: 60 independent runs of 10,000 maps per method, using seeds `1000 + 2*i` for `i = 0..59`. In this fixed synthetic experiment the direct estimates have run-to-run standard deviation **0.000614** (mean reported SE **0.000653**); the weighted estimates have run-to-run standard deviation **0.000382** (mean reported SE **0.000305**). The event-weight effective sample size ranges from about **44 to 453**. These values illustrate variability and a need for repeat runs; they do not establish confidence-interval coverage or calibrate a physical model. Run `python replication_check.py --help` to change the number of runs, samples, or initial seed.

### Synthetic dose sweep

`dose_sweep.py` changes the mean Poisson counts per grid cell while retaining the same arbitrary threshold, blur, and fixed proposal multiplier. It compares ten repeated direct and importance-sampling estimates at each setting, each with 20,000 simulated maps per method. The saved figure `dose_sweep.png` uses a logarithmic vertical axis; error bars are the standard error of the ten-run mean based on between-run variation, not physical-model uncertainty or an established confidence interval. Reproduce the saved inputs and result with:

```bash
python dose_sweep.py --shots 20000 --repeats 10 --seed 1000 --json-output dose_sweep_results.json --figure dose_sweep.png
python -m unittest -v test_dose_sweep.py
```

In the toy model, estimated failure frequency decreases as the mean input count increases. At 1.8 arbitrary count units, the means across ten runs are about **0.000160** for direct sampling and **0.000198** for weighted importance sampling. These are stochastic estimates, not rates measured in a fab. The process omits other effects and tradeoffs of changing dose, proposal tuning cost and real process physics. This experiment is classical; the larger spatial model does not have a quantum implementation.

## Background

* [IBM Research: stochastic variation in EUV patterning](https://research.ibm.com/publications/fundamental-characterization-of-stochastic-variation-for-improved-single-expose-extreme-ultraviolet-patterning-at-aggressive-pitch)
* [Siemens: importance sampling for a missing-via stochastic model](https://resources.sw.siemens.com/sl-SI/technical-paper-importance-sampling-in-gaussian-random-field-euv-stochastic-model-for/)
* [IBM Research: why efficient quantum state preparation matters](https://research.ibm.com/publications/efficient-state-preparation-for-quantum-amplitude-estimation)
