# Exploratory quantum-light fringe comparison

This standalone calculation addresses a different research question from the
project's Qiskit model of a missing contact: **what correlations could
two-photon quantum light produce at a hypothetical nonlinear detector?** It
does not simulate photoresist chemistry, EUV lithography, physical wafers,
actual losses in a manufacturing tool, or a real experiment.

We compare a two-mode, two-photon NOON state
`(|2,0> + |0,2>)/sqrt(2)` with two coherent inputs with complex amplitudes
`1` and `1`. Both have total *mean* incident photon number two, but their
photon-number statistics differ. For relative phase `phi` at one normalized
output `c=(a+exp(i phi)b)/sqrt(2)`, the figure shows the normally ordered
two-photon moment `<c†² c²>`: `0.5 (1+cos 2phi)` for NOON and
`(1+cos phi)²` for the coherent reference, at unit transmission. A spatial
interference phase can vary with position, but phase here is not a calibrated
coordinate or optical point-spread model.

The NOON curve has a doubled phase frequency; the coherent signal also has a
second harmonic and reaches a larger peak in this particular equal-mean-input
comparison. Identical independent arm transmission `eta` multiplies both
two-photon moments by `eta²`. This is only an ideal correlation model: it
does not determine resist dose, throughput, resolution after development, or
whether either light source is better under realistic experimental budgets.
In particular, a doubled fringe frequency alone is not proof of a quantum
advantage or a manufacturable printed feature. Compare experimentally relevant
classical fields, photon flux, absorption cross-section, optics, calibration,
damage and exposure time before drawing a practical conclusion.

Reproduce with NumPy and Matplotlib installed:

```powershell
python -m unittest -v test_fringe_compare.py
python fringe_compare.py
```

The script refuses to overwrite an existing figure. The tests independently
construct truncated Fock-space annihilation operators and verify the NOON
moment, limiting values and the equal-loss scaling. Background and proposed
next steps are in `../QUANTUM_PHOTOLITHOGRAPHY_ROADMAP.md`.
