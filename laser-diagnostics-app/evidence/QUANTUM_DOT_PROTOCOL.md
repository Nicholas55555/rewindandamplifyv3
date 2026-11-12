# Bounded quantum-dot coherence benchmark

Design recorded 11 November 2026 before running this local benchmark. This reproduces known quantum-optics relationships to test a measurement choice; it is not a preregistered discovery study or a fit to a real dot.

## Question and scope

Can two ideal pulsed semiconductor-emitter models have the same photon-number statistics and collection probability, yet yield different two-photon interference? Can correlations between successive frequency offsets change that interference while leaving the single-photon frequency distribution unchanged?

Represent one selected optical transition as a radiatively decaying two-level system. Condition on ideal preparation of one excitation. Treat fast phase noise as independent Markov pure dephasing and the optional frequency offset as fixed throughout each emitted wavepacket. Compute the emitted single-photon density operator and the overlap of two photons at a balanced beamsplitter. No Qiskit execution, semiconductor band-structure calculation, physical defect fit, industrial laser model or new laboratory measurement is part of this test.

## Fixed illustrative comparisons

Use radiative lifetime `T1 = 1 ns`, population decay rate `Gamma = 1/T1`, pure-coherence decay rate `gamma_star`, and equal per-photon survival/detection probability `eta = 0.2`. Frequencies in Hz are converted to angular frequencies with `2*pi`; decay rates are inverse seconds, without that conversion.

| Case | gamma_star / Gamma | Differential angular detuning / Gamma |
|---|---:|---:|
| Ideal reference | 0 | 0 |
| Pure dephasing | 0.5 | 0 |
| Frequency mismatch | 0 | 2 |
| Both effects | 0.5 | 2 |

For an illustrative symmetric classical two-state environment, use offsets `+/- Gamma/(2*pi)` Hz. The offset is fixed during each photon; a selected pair has opposite offsets with probability `p_switch`. Compare `p_switch = 0, 0.02, 0.1, 0.5`. The last case corresponds to two independent fair draws. This is a joint-pair model, not a measured switching time or a simulation of switching within a photon wavepacket. Start the first state fairly so every case has the same single-photon offset distribution.

Vary collection probability separately, including `eta = 0.8` and `0.2`. Keep the excitation-pair budget explicit. Do not interpret a high conditional overlap as a high photon-pair delivery rate.

## Measurements and checks

- Report single-photon collection probability, ideal photon-number `g2(0)`, conditional photon overlap/HOM visibility, conditional two-output coincidence probability, and coincidence probability per attempted excitation pair.
- Equal brightness and `g2(0)=0` are imposed by one-photon preparation and frequency-independent collection, not discovered by the simulation. Finite-duration or spectrally selective excitation could change brightness in a real device.
- Evaluate the density kernels by numerical quadrature independently of the analytic overlap formula. Check normalization, Hermiticity, positivity, pure-state and fully distinguishable limits, common frequency-shift invariance, and probability bounds.
- Verify the classical two-state mixture with bounded seeded sampling and explicitly reported numerical/statistical error. No Monte Carlo agreement is evidence for a microscopic charge-trap model.
- Record parameter values, source hashes and package versions. Do not overwrite an existing result without an explicit option; do not change any prior project's frozen evidence.

## Interpretation rules

Reduced interference may reflect phase noise, differential detuning, polarization/mode mismatch, timing jitter, detector artifacts or imperfect preparation. This benchmark cannot identify their physical cause uniquely. Classical spectroscopic and hidden-state baselines remain necessary. Amplifying a model cannot recover coherence information absent from the measured record.

Published HOM histograms, if imported, remain a separately attributed external reference. They are not used to tune these illustrative parameters. No monotonic delay trend, fit or performance validation will be claimed for those data without a measurement-specific analysis with normalization and uncertainty.
