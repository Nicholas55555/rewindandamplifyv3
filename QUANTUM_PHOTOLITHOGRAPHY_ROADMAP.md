# Quantum photonics and chip making: evidence and next experiments

**Secondary direction.** The team's primary clarified photonics vision is a quantum sensor for monitoring a lithography light source; see `LASER_DIAGNOSTICS_ROADMAP.md` and `laser_sensor_poc/`. This note explores the different questions of quantum-light exposure and patterned-structure inspection.

## The opportunity

There are two different questions. The existing Qiskit missing-contact example uses a quantum computer to study a **classical model** of an exposure defect. Quantum photolithography instead asks whether specially prepared **quantum light** interacting with an optical system and a material can help write or inspect chip features. The first does not establish the second. The team's photon-emitter model is also a synthetic source/defect model, not a demonstrated lithography light source.

The most credible near-term connection is **optical measurement or inspection of patterned structures**, with photon budget, loss and resolution measured against a strong classical instrument. A longer-term research direction is **direct exposure of a suitable multiphoton resist**. Neither an inspection advantage nor a manufacturable exposure follows automatically from entanglement. These approaches complement the quantum-computing work; they are not results it has already established.

## What has actually been demonstrated

- D'Angelo, Chekhova and Shih observed a two-photon diffraction/interference pattern with a factor-of-two narrower modulation under the experiment's conditions. This was a coincidence-detection proof of principle, not a reported semiconductor wafer printed with a production resist. [Physical Review Letters, 2001](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.87.013602); [full paper](https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevLett.87.013602/fulltext).
- Tsang's analysis shows that a NOON state's multiphoton absorption rate can be **lower** than that of an otherwise matched classical state, despite finer fringes, and analyzes a resolution/rate tradeoff. This conclusion is scoped to the states and assumptions in that analysis; it is not a universal claim about every quantum source or material. [Physical Review A, 2007](https://www.ece.nus.edu.sg/stfpage/tmk/papers/tsang_quantum_lithography_PRA.pdf).
- Optical quantum metrology has produced experimental improvements under stated resource accounting; for example, an unconditional photonic phase-measurement experiment reports a result beyond its shot-noise benchmark. This motivates inspection research, but it is not a result on semiconductor production-line inspection or photoresist exposure. [Nature Photonics, 2017](https://www.nature.com/articles/s41566-017-0011-5).

## Completed first probe in this workspace

`quantum_lithography_poc/fringe_compare.py` compares a two-photon NOON state with two coherent input fields. Both have **two mean incident photons per trial**; their photon-number distributions differ. With the same normalized two-mode output and independent equal arm transmission `eta`, it calculates the normally ordered two-photon moment `G2 = <c†²c²>`, not a resist response or a count of printed features. Its tests independently check the Fock-space calculation and loss scaling. See `quantum_lithography_poc/README.md` and the generated `fringe_comparison.png` for reproduction and assumptions.

At unit transmission, the NOON moment is `(1 + cos(2 phi))/2`; the coherent reference is `(1 + cos(phi))²`. Both have a second harmonic; only the NOON curve in this comparison lacks the fundamental harmonic. The coherent reference reaches a higher peak: 4 versus 1 in the model's units. Equal arm loss multiplies both moments by `eta²`, so `eta = 0.5` leaves one quarter of the ideal value. These numbers are properties of the stated, idealized comparison, not a universal ranking of quantum and classical light. The phase axis has not been calibrated to an optical system or feature size. No wafer, photoresist, experiment, quantum advantage, or manufacturing throughput was demonstrated.

## Why a fine fringe is not yet a chip-making process

1. **Material response and dose.** A two-photon correlation can write a pattern only if the material has an appropriate local two-photon response, at useful brightness, within its relevant coherence and absorption times. A linear-response resist is governed by the first-order intensity rather than automatically reproducing the two-photon curve. Absorption cross-sections, chemistry, development, blur and defect statistics all need measurement or validated modeling.
2. **Loss and useful events.** In this model, independent photon transmission suppresses the two-photon moment quadratically. Real source generation, coupling, optics, sample absorption and detection have separate losses; reported coincidences must be accompanied by unconditioned trials and source-preparation overhead. Postselecting surviving pairs alone hides the cost. Brightness and exposure time matter as much as visibility.
3. **Fair classical comparison.** Classical nonlinear optics can also produce higher harmonics, as the existing coherent comparator illustrates. Compare at fixed wavelength, optical bandwidth/numerical aperture, sample photon budget, exposure time, noise, and material response. A single coherent reference is useful but does not establish the optimal classical limit.
4. **Real-world translation.** A two-mode phase fringe is not a patterned resist, wafer process, or production EUV tool. Wavelength, optics, photon energy, material response and throughput must be specified before comparing a quantum-light proposal to chip fabrication.

## Next low-risk simulation: from correlation to a testable dose budget

Extend the current **classical numerical quantum-optics calculation**, without claiming it is a physical experiment or quantum-computer speedup:

1. Add first-order intensity `G1` and an incoherent two-photon mixture as a control. Retain the coherent comparison and add other classical illumination strategies when justified. Plot both `G1` and `G2` for the same input photon budget. A mixed toy response `D = k1 G1 + k2 G2` can illustrate how a linear background changes contrast; label `k1` and `k2` as arbitrary, uncalibrated parameters and do not call `D` a real resist dose.
2. Sweep `eta`, phase jitter, background and source-success probability; count **all** source attempts. Distinguish photons incident on the sample from photons spent preparing the state and from detected coincidences. Use the same geometry, total incident mean photon number, integration time and noise assumptions for the reference; explicitly show where identical incident dose and identical wall-clock time cannot both be achieved without changing source brightness.
3. Report first and second harmonic amplitudes, fringe visibility, average and peak `G2` per input photon, and expected events or integration time only after specifying a weak-response coefficient and trial rate. Include finite-count uncertainty if sampling is added. Check analytical formulas, positivity, loss limits and an independent numerical Fock-space calculation. A successful investigation can identify regimes in which the quantum curve loses; the success criterion is a reproducible, matched-resource comparison, not a presumed advantage.
4. For a real feasibility estimate, replace arbitrary coefficients with measured wavelength-dependent resist response, optical geometry, photon-pair brightness, propagation/detection loss and development data. Define a relevant feature and compare predicted dose, stochastic defects and wafer area per unit time with a credible classical exposure or inspection baseline. If those parameters are unavailable, stop at a sensitivity study and state the missing inputs.

For inspection, a separate follow-on experiment could estimate a known phase or geometry parameter of a patterned test sample using quantum and classical probes at the same **sample-incident photon dose**. Compare estimation error, confidence intervals and acquisition time with a realistic classical optical measurement while accounting for preparation and detection losses. This is an inspection study; it does not demonstrate writing.

## A responsible finals statement

“Our quantum-computing prototype studies rare modeled defects. Separately, we explored whether quantum photon correlations could connect to the optics used in chip making. Our first simulation reproduces a finer two-photon fringe, but also shows that a classical field can produce higher-order structure and a stronger signal in this comparison. Turning correlations into useful chip patterns requires a suitable resist, enough photons, and a fair test against classical optics.”

The figure is suitable as a **research-direction or backup slide** with those caveats, not as a claim of printed features or a result from the team's hardware.
