# Small optical and atomic controls for the hardware campaign

The validated logical bundle is **`bundle_v2/`**: 33 circuits, 3–17 encoded qubits, and at most 11 generic CX gates per circuit. It contains no hardware results by itself. Native device compilation, layout, calibration, execution and raw counts belong to the parent campaign. These circuits emulate specified optical dynamics on superconducting qubits; they do not generate optical photons, operate an atomic laser sensor, inspect a chip or expose a material.

The original scientific files and all earlier results are unchanged. [PROTOCOL.md](PROTOCOL.md) specifies the comparison before this export. Twelve focused tests pass. A separate reviewer independently checked all 33 QPY circuits, measurement wiring, Bloch/Fock/multinomial predictions and Poisson accounting; the receipt is `../feasibility/optical_controls_independent_review.json`.

## Atomic finite-pulse dynamics, not a loaded output probability

Nine circuits implement the finite-pulse Ramsey model from `laser_sensor_viability/model.py`. For each parameter setting, three Lindblad matrix exponentials describe the first pulse, free evolution and quadrature final pulse. The resulting complete quantum channel is converted to a Choi matrix, all its Kraus components are retained, and a Stinespring isometry acts on arbitrary input states. A fourth qubit purifies the specified 1% preparation error.

The channel includes the original 2.5 ms pulse duration, 20 ms free evolution, T1=100 s, nominal T2=0.2 s and power-dependent pulse light shift. Those are modeled optical parameters. They are not the superconducting processor's coherence or execution time. The 698 nm wavelength and optical coupling are not tested by this circuit.

The exported cases are Z readout at detuning −5, −0.5, 0, +0.5 and +5 Hz; a short-T2=0.02 s case; a 10% intensity change; and X/Y readouts at +0.5 Hz. An independent affine Bloch exponential checks six input-state directions, in addition to the initial mixed state. The exact channel also agrees with the canonical 16-substep pulse calculation to its declared numerical tolerance. The complete circuit checks include coherence, not just a single excited-state probability.

Computational **0 is the excited state** and **1 is ground**, matching the canonical Bloch ground z=−1. Circuit output is the Born probability. The original 2%/4% synthetic optical readout error is reported separately in metadata and is **not injected into QPU readout**, which has its own calibration. Preparation/channel environment qubits are retained and then ignored for system observables.

## Photon paths, interference and loss

Eight two-photon circuits compare NOON and incoherent-mixture inputs under actual path-phase and balanced-beamsplitter operations. The encoding is first quantized: each photon has a path qubit and a survival/loss qubit, with physical observables obtained by aggregating mode occupations. Identical one-particle transformations preserve the symmetric bosonic subspace. The NOON input is `(aa+bb)/sqrt(2)`; the incoherent control retains a purifying environment.

A lost photon's path remains in its corresponding environment mode. Nothing is postselected away when calculating number outcomes, including failed source preparations. Symmetric arm losses commute with the passive interferometer, which permits the combined object/detection loss to appear after the final beamsplitter. This construction does not cover unequal-arm loss without changing the channel. Hardware noise can also break the ideal encoded symmetry; aggregated count agreement alone is not full optical-state tomography.

An independent second-quantized Fock calculation builds the beamsplitter using the bosonic square-root occupation factors, then applies binomial thinning. All six number-resolved outcomes, total surviving photons, G1 and factorial G2 agree with the circuits. The primitive measures one normalized output mode. To relate its moments to the exposure study's 32-cell geometry requires the separate spatial normalization; repeating phase points cannot duplicate the allowed illumination dose. There is no resist coefficient, chemical activation or physical blur in this circuit.

The settings include phases 0, 0.35, pi/4 and 0.35+pi, total efficiencies 0.81 and 0.48, and preparation success 0.1. Both optical input arms illuminate the hypothetical sample and are charged before object transmission. The phase pair exposes the NOON measurement's pi ambiguity. No unknown physical phase is estimated merely by running known phase settings.

## Coherent reference without hiding the photon tail

The original classical reference has a product of coherent inputs with total mean photon number two. Global optical phase is irrelevant to this number-preserving interferometer and phase-insensitive photon-counting/loss measurement. It can therefore be represented, for these observables, by a Poisson(mean 2) mixture of total-number sectors. A fixed-N sector is the symmetric product of N photons in the same delocalized input mode, not N separately populated input modes.

Sixteen shallow circuits implement sectors N=1 through 8 at phases 0.35 and 0.35+pi, with total efficiency 0.81. Each photon actually undergoes input preparation, phase rotation, recombination and loss. The N=0 sector is explicitly charged as deterministic vacuum. The unmeasured N>8 tail is retained as missing probability mass:

| Quantity omitted above N=8 | Exact Poisson value |
|---|---:|
| Probability | 0.0002374473 |
| First photon moment | 0.002193438 |
| Second factorial photon moment | 0.01813522 |

The first number bounds the error in any aggregate-count event probability; it does not by itself bound unbounded moments. Survival scales the displayed first/second moment bounds by eta and eta². Sector weights are **never renormalized to sum to one**. If the campaign omits a requested sector, its weight is separately reported as missing. Per-sector hardware shots are a stratified measurement allocation, not a claim of a working coherent light source or matched optical acquisition time.

The optical relationships are established physics. See [van Enk's coherent-state and beamsplitter derivation](https://pages.uoregon.edu/svanenk/solutions/NotesBS.pdf), and the canonical study's [phase-estimation references](../../quantum_lithography_poc/phase_inspection_followup/README.md). Isometry synthesis uses Qiskit's implementation of [Iten et al., PRA93,032318](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.93.032318), documented in the [IBM circuit library](https://quantum.cloud.ibm.com/docs/en/api/qiskit/circuit_library). The contribution here is the validated, resource-small adapter and honest measurement/accounting comparison, not a newly discovered interference effect.

## Bundle and raw-count analysis

- `bundle_v2/logical.qpy`: generic unitary decompositions plus one `meas` register; qubit j maps to classical bit j.
- `bundle_v2/manifest.json`: ordered cases, physical settings, register meanings, full source hashes, independent number/Bloch targets and generic costs.
- `bundle_v2/ideal_probabilities.npz`: every circuit's complete computational-basis distribution, indexed by the manifest's `ideal_probability_key`.
- `analyze_counts.py`: `score_counts(counts,row)` returns raw atomic expectation/probability intervals or decoded photon moments, shot errors and number-distribution discrepancy. `aggregate_coherent_sector_scores` combines measured sectors without filling or conditioning away missing mass.
- `validation.json`: local verification receipt. Hardware results must remain separately labeled and linked after the parent retrieves them.

Counts are never postselected on a good source flag or surviving pair. Photon-count TV is shot-noise biased and does not certify state fidelity. Atomic intervals are Wilson intervals for raw measurement probabilities. Weighted sector standard errors assume independent shot allocations and exclude device drift, calibration and model uncertainty.

The first `bundle_v1/` is a preserved failed serialization attempt: Qiskit2.6.1 could not reload an opaque Isometry instruction. No job used it. The final bundle first decomposes that instruction to unitary `u,cx` operations and checks QPY round-trip probabilities, preserving the physical channel.

From the repository root with the recorded Qiskit/NumPy/SciPy environment:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest discover -s hardware_campaign/optical_controls -p 'test_*.py' -v
python hardware_campaign/optical_controls/verify_bundle.py
python hardware_campaign/optical_controls/export_bundle.py --out hardware_campaign/optical_controls/new_bundle
```

The exporter refuses an existing output directory. No account, credential, Runtime service or submission is imported. Unknown-onset monitoring, full finite-shot optical phase estimation and industrial transfer remain separate experiments.
