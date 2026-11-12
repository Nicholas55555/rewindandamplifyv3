# Lithography and laser diagnostics research continuation

The current objective is to complete the postponed simulations that can be supported by this workspace, test relevant extensions, and identify a defensible stopping point. The central application is complementary laser diagnosis. Direct quantum-light exposure and quantum sampling of process histories remain distinct studies. The finals package is a fixed reference while these followups run.

## Experiment scope

| Study | Question and planned work | Evidence needed before concluding |
|---|---|---|
| Spatial process sampling | Move beyond independent binary sites to a correlated spatial exposure model. Construct and verify a tractable coherent preparation and failure oracle. Also construct a bounded finite approximation of the full original 49-cell model, with explicit count-tail and weight-rounding error. Compare with exact conditional sampling and strong classical rare-event estimators, including proposal cost and uncertainty. | Truth-table and distribution checks, ideal small-circuit reproduction, actual full-model construction and component verification, gate/resource costs, repeated classical estimates, explicit limits on full-system simulation. |
| Quantum-light exposure | Extend the two-photon comparison with first-order response, an incoherent control and phase-cycled classical light. Sweep loss, jitter, blur, linear background and source success; separate equal sample dose from equal acquisition time. | Independent Fock-space checks, finite-count uncertainty, source-attempt accounting, and response assumptions. These are sensitivity studies until measured material parameters exist. |
| Optical inspection | Test phase estimation with equal sample photon dose and explicit source/detection losses. Compare with an appropriate classical optical measurement, including phase ambiguities. | Estimation errors over repeated records, resource accounting and a clearly specified prior or phase range. This does not establish pattern writing. |
| Laser sensing | Replace the known-onset detector with causal detection of an unknown onset. Hold out entire simulated sessions, vary nuisance calibration, and compare the atomic addition with a second conventional reference. | Full-record false alarms, detection delay with missed events accounted for, session-level uncertainty and drift controls. |
| Driven emitter diagnostics | Apply baseline, offset and switching drive-amplitude schedules to the emitter–cavity model while retaining its hidden state between bins. Distinguish drive changes from detector changes with held-out calibration and classical comparisons. | Normalized time-varying instruments, fresh independent records, explicit schedule/onset assumptions, detection and false-alarm uncertainty, and nuisance counterfactuals. |
| QRSM inference | Test cavity-cutoff convergence and an independent solver, jointly fit coupling and nuisance parameters, examine identifiability, and test detector dead time. Explore controlled input settings where justified. | Independent numerical checks, fresh train/test records, optimization diagnostics, parameter uncertainty and strong classical prediction baselines. |
| Reversible optical histories | Assess additional history bins and approximation/noise costs beyond the two-bin demonstration, using exact classical conditional inference as a comparator. | Preserved conditional distributions, explicit discarded-channel error and circuit/register costs. A numerically manageable subcase cannot establish full-scale feasibility. |

Detailed protocols and seeds will be saved before held-out evaluation in each new study directory. Existing archived results and the frozen finals app data will not be overwritten by these studies. Scientific code, configurations, results, plots and tests will be retained with a final synthesis identifying positive, negative and inconclusive findings.

## API and physical-data decisions

All first-stage calculations run locally. IBM access is useful only if a small, sufficiently shallow circuit survives ideal and noisy validation and a hardware comparison would answer a remaining question. Before any submission, specify the circuits, qubits, shots, calibration design, estimated usage and result interpretation. A QPU run validates a circuit implementation; it does not validate a laser sensor, optical source or resist model.

No API key is needed yet. If hardware is justified, use a local credential configuration without putting the token in source files, reports or chat. The exact setup and usage request will be provided at that point.

Actual lithography-source compatibility, resist coefficients, exposure geometry and laboratory sensor calibration require measured external inputs. Where those are unavailable, complete the sensitivity study and resource bounds, then identify the specific measurement needed. Do not replace missing material data with a numerical claim about wafer yield or industrial throughput.

## Stopping-point audit

For each study above, inspect the implemented equations, outputs and applicable independent tests. Record whether its planned local calculation is complete, contradicted by evidence, or limited by a named external input. Reconcile all numbered next-experiment items in the existing roadmaps. Keep unresolved work explicit. The final report should state what changed the project's research decisions and whether an IBM run or physical measurement is the next useful step.
