# Photon model verification and joint inference

This followup tests whether the photon model's predictions survive numerical approximation and uncertain model parameters. It uses fresh synthetic records. All parameters retain the original arbitrary units; no lithography laser or physical defect was measured. The original companion and finals evidence remain unchanged.

## Independent dynamics and cavity cutoff

QuTiP 5.3.1 independently rebuilds the Hamiltonian and jump operators and integrates the master equation with an ODE solver. For cavity dimensions 2, 3 and 4, its density matrices agree with the original matrix-exponential implementation to within 2.0×10⁻⁹ in Frobenius norm over 40 bins. A separate 6,000-trajectory quantum-jump calculation includes monitored photon events and independent dark counts, then coarsens them to the same binary bins. All 21 specified unconditional/joint statistics lie within the simultaneous approximate 99% binomial intervals; the largest individual standardized discrepancy is 2.88. These checks compare two implementations of the same assumed physics.

The cavity cutoff does affect the answer. The table gives the largest absolute discrepancy in later-click probability conditioned on a step-3 click, across 40-bin calculations. Dimension 6 is a larger numerical reference, not the exact infinite-dimensional model.

| Cavity dimension | Default | Higher drive | Higher coupling |
|---|---:|---:|---:|
| 2 | 2.7643 percentage points | 7.0829 pp | 1.6457 pp |
| 3 | 0.5378 pp | 0.9097 pp | 0.3533 pp |
| 4 | 0.0494 pp | 0.1118 pp | 0.0309 pp |
| 5 | 0.00281 pp | 0.01102 pp | 0.00181 pp |

The smaller original models remain well-defined finite systems, but their numerical agreement with their own circuits does not establish convergence of a physical cavity. The new inference experiment uses dimension 4 for its generator and fitting, then evaluates the already-selected fit at dimension 5 as a sensitivity check. It does not fit real or dimension-6 data. The convergence check covers the declared settings, not every possible fitted parameter combination.

Sources: `dynamics_results.json`, `verify_dynamics.py`, and `cavity_cutoff.png`. Independent solver documentation: [QuTiP master-equation solver](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-master.html) and [quantum-jump solver](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-monte.html).

## Fresh inference design

The frozen configuration in `inference_results/protocol.json` specifies two independent repetitions, each with 240 training and 240 held-out 24-bin records. Joint fitting estimates defect coupling, defect detuning, emitter dephasing, detection efficiency and drive. All other parameters and the generative family remain known. Three randomly initialized bounded L-BFGS-B fits use training likelihood only. An additional known-nuisance coupling fit measures the cost of estimating the other parameters; it is an oracle comparator with information unavailable in a normal experiment.

The fixed protocol uses one drive and zero emitter-detuning control. The controlled protocol allocates the same number of records equally across three known settings. The squared drive multipliers average to one, and emitter detunings are −0.5, 0 and +0.5. This balances record/bin counts and this drive-strength proxy; it is not a matched apparatus or optical photon budget. The controls tune the modeled emitter, not the unknown defect.

Each control label gets a separately trained three-state HMM and a stationary two-state classical telegraph comparator. The HMM uses five EM starts followed by training-only local refinement. The telegraph model matches the training click rate and fits its switching and contrast. The physical model shares parameters across controls, while each HMM receives fewer records and has its own free parameters. That known physical structure is an information advantage, not proof of quantum computational superiority. Every method is calculated classically.

Held-out likelihood differences are paired by record. Bootstrap intervals hold the control allocation fixed and resample within each control. They describe test-record variability conditional on the fitted models, not training uncertainty or the global quality of optimization.

### What the completed fits show

The generator's coupling is 0.65, defect detuning 0.20, emitter dephasing 0.035, efficiency 0.68 and drive 1.30. Recovering one approximately correct parameter does not establish that the other mechanisms have been identified.

| Protocol / seed | Fitted coupling | Fitted dephasing | Fitted efficiency | Physical-model minus HMM held-out score, nats per 24-bin record | Conditional 95% interval |
|---|---:|---:|---:|---:|---|
| Fixed / 411001 | 0.642 | 0.107 | 0.808 | +0.0169 | −0.0131 to +0.0462 |
| Fixed / 411002 | 0.729 | 0.001, lower bound | 0.654 | +0.0065 | −0.0225 to +0.0355 |
| Controlled / 411001 | 0.674 | 0.169 | 0.790 | +0.0574 | +0.0158 to +0.1014 |
| Controlled / 411002 | 0.648 | 0.001, lower bound | 0.688 | +0.0972 | +0.0448 to +0.1495 |

The fixed-setting tests do not resolve a predictive improvement over the fitted HMM. The controlled tests favor the shared physical model in this correctly specified synthetic family. They do not establish superiority over every classical inference method: the physical likelihood itself is evaluated classically, and its known cross-control structure is helpful prior information. The variation and boundary fits in dephasing show that useful predictions can coexist with uncertain physical attribution.

## Identifiability and parameter uncertainty

Exact enumeration of eight-bin histories shows a global ambiguity: with the fixed control, positive and negative defect detuning give the same distribution. Controlled emitter detuning breaks that symmetry. A full-rank local Fisher matrix therefore cannot by itself establish unique physical identification. Fisher matrices use explicitly scaled coordinates and are local short-record diagnostics.

A coarse coupling profile reoptimizes nuisance parameters at seven fixed couplings. It uses one start and a finite evaluation budget at each point. It is a diagnostic of competing explanations, not a confidence or identified set.

Breaking the exact sign symmetry does not mean this finite experiment confidently identifies the detuning sign. For example, the first controlled fit's local approximate detuning interval is −0.050 to +0.457; it crosses zero. Its dephasing and efficiency intervals extend outside physical or search bounds. These are warnings about weak identification and the local approximation, not plausible negative dephasing or efficiency above one.

`parameter_diagnostics.py` independently regenerates training records, verifies their hashes and reproduces the saved likelihood. It compares central Hessians at two explicit step sizes and reports local normal approximate 95% parameter intervals only for interior solutions with stable positive curvature. Global sign aliases, physical-model mismatch and optimizer uncertainty remain outside those intervals. Boundary solutions do not receive a misleading regular-normal interval. The canonical audit in `parameter_validation_v2/` also flags intervals that extend outside search bounds or physical values such as efficiency between zero and one. Such widths expose weak identification and an inadequate global Gaussian approximation; they are not calibrated physical confidence sets. Earlier audits remain in `parameter_validation/`.

The live optimizer used `jac=None`, so SciPy's default absolute finite-difference step applied. Its supplied `finite_diff_rel_step` option did not take effect. The separate central-derivative audit does not silently refit the experiment. See the [official SciPy L-BFGS-B documentation](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html).

## Detector dead time

A separate fresh cohort has a one-bin readout dead time: after a registered click, the next recorded bit is necessarily zero. The physical system still evolves under its unconditional channel during that blind bin. Correct and omitted-dead-time fits receive exactly the same records. Independent tests verify total probability, forbidden adjacent detections, unconditional blind-bin evolution and sampling frequencies. This discrete surrogate does not model a calibrated detector's nanosecond response.

Omitting that blind bin drives the fitted coupling to **0.069**, far from the generator's **0.65**. Including it moves coupling to **0.706** and improves held-out log likelihood by **0.4584 nats per record** (paired conditional bootstrap 95% interval **0.3978–0.5210**). The same-record three-state HMM also captures this detector-induced correlation: the omitted physical model scores 0.4506 nats below it, while the corrected model's +0.0078 difference has an interval spanning zero (−0.0067 to +0.0222).

The corrected fit still puts dephasing at its upper bound of 0.20 and efficiency at 0.871. Thus accounting for readout dynamics prevents one severe misattribution and improves prediction, but does not uniquely recover all physical parameters. This is directly relevant to defect analysis: a change in recorded correlations can come from the detector as well as the modeled hidden interaction. A click alone is not a defect label.

All six cases and their canonical parameter audits are saved. Nine focused tests pass (`test_results.txt`). The independent review checks regenerated training/test data hashes, saved score vectors, conditional bootstrap intervals and source provenance; no experimental data or IBM execution is involved.

## Reproduction

Use the Python and package versions recorded in the results, with one BLAS thread:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
python -m unittest discover -s qrsm_photon_poc/followup -p 'test_*.py' -v
python qrsm_photon_poc/followup/verify_dynamics.py --output another_dynamics_run.json
python qrsm_photon_poc/followup/run_inference.py
python qrsm_photon_poc/followup/parameter_diagnostics.py
python qrsm_photon_poc/followup/plot_dynamics.py
```

The inference runner resumes only completed cases under an identical source/configuration manifest. It never reads held-out scores to select fitted parameters. Completed outputs and earlier results are retained. No IBM credentials or jobs are used.

## Remaining physical questions

Slow spectral diffusion is a particularly relevant next counterfactual: classical emitter-frequency drift could be misattributed to a coherent hidden defect. A convincing test needs calibrated model-selection error across fresh generator settings and explicit drift alternatives. Thermal photons, additional cavity modes and non-Markovian environments are also untested here. Completing these numerical checks does not establish robustness to all omitted physics or replace independent source/detector calibration.
