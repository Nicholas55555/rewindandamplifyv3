# Hardware feasibility and faithful logical adapters

These are **digital model experiments on superconducting qubits**. The retained
optical circuit represents an emitter–defect–cavity instrument; it is not an
optical sensor, a physical photon detector, or a laser reversed in the laboratory.
The spatial circuit samples a defined correlated exposure model; it does not
manufacture or inspect a wafer. No hardware is submitted from this folder.

## What the ladder implements

| Model / circuit | Logical qubits | Generic CX, plain / one round | Meaning |
|---|---:|---:|---|
| Optical1bin, Choi cutoff.03 | 7 | 1,051 / 3,269 | Smallest retained physical-instrument dilation |
| Optical1bin, cutoff.003 | 8 | 2,086 / 6,422 | More retained Kraus components |
| Optical2bin, cutoff.03 | 11 | 2,102 / approximately6,663 | Actual system memory reused across bins |
| Optical3bin, cutoff.03 | 15 | 3,153 / 10,183(last),10,189(all) | Three flags and three fresh environments |
| Optical3bin, cutoff.003 | 18 | 6,258 / 19,858(last),19,864(all) | Finer retained instrument; very deep noise stress |
| Spatial2×2, enumerated oracle | 9 | 144 / 988 | Shared latent dose and four conditional Poisson cells |
| Spatial2×2, computed sum oracle | 14 | 144 / 1,052 | Reversible integer addition, threshold phase, uncompute |
| Full original7×7 construction | 219compact / 389explicit-clean | Millions | Exceeds the156qubits reported available; no submission |

The table records the existing generic all-to-all u/CX synthesis, before actual
device routing. Exported manifest counts are authoritative for each actual
circuit. Spatial second-round circuits are also exported:1,832CX enumerated and
1,960CX computed. Plain counter controls are padded to14qubits so the same
logical data/workspace roles can use one physical layout.

All optical cases reuse the frozen `multibin_followup/model.py`: exact finite
Lindblad time-bin maps → Choi truncation → completeness normalization → flagged
isometry → actual repeated channel dilation. The inverse retains every flag and
environment register. A free rotation fitted only to one event probability is
not used. The cutoff is an approximation to the cavity-2 model, which itself has
a finite cavity cutoff; these physical approximation errors remain visible in
metadata and are separate from quantum hardware errors.

Spatial state preparation is an explicit controlled-rotation tree for the joint
latent-dose/count distribution. Its cells are correlated through a shared dose
variable. Capping each count at3 preserves `weighted_score < 3` and every
accepted map exactly, while changing the unconditional count distribution and
moments. The computed oracle really adds weights `[1,2,2,4]`, marks scores0–2,
then uncomputes. The enumerated oracle is a smaller fixed-predicate comparison,
not a scalable replacement. The original7×7 model remains distinct; its existing
219/389-qubit construction and rigorous approximation bounds are not relabeled
as this2×2 experiment.

## Export and verify without an account

Use the established research environment (Qiskit2.6.1, Aer0.18.2, NumPy2.3.1,
SciPy1.18.1; see the root research requirements). Set BLAS/OMP threads to1.

```powershell
python -m unittest discover -s hardware_campaign/feasibility -p test_adapters.py -v
python hardware_campaign/feasibility/export_adapters.py --output hardware_campaign/feasibility/bundle_v1 --timeout 900
```

The output directory must be new. The exporter runs in a child process with a
3GiB memory limit and a900-second deadline. It leaves logs and a status receipt
on failure. Statevectors are capped at18qubits; there is no large density-matrix
simulation or hardware service initialization. The19-circuit bundle contains:

- `logical.qpy`: ordered logical u/CX circuits, each measured into one `meas`
  register, `q[i] → meas[i]`. No physical layout is assigned.
- `ideal_probabilities.npz`: exact full computational-basis probabilities,
  indexed by each row's reference key. Array index is the little-endian logical
  bit integer; displayed counts are `q[n−1]…q[0]`.
- `manifest.json`: schema `ra-hardware-bundle-v1`, ordered `circuits` rows with
  `name`, `index`, `metadata`, `reference` and `validation`; source/artifact hashes,
  physical-model parameters, register roles, original-versus-retained errors and
  an independent compact target distribution.
- `build.log`, `build_status.json`, `progress.json`: local execution evidence.

The statevector marginal is checked against independent channel-branch recursion
or the exact spatial Poisson/DP law. QPY is loaded back and compared instruction
for instruction, including classical measurement wiring. NPZ roundtrip is exact.

## Hardware campaign handoff

The campaign owner loads QPY, fixes a physical layout within each matching
family/width, compiles against the actual backend target, records transpiler seed
and backend calibration time, and saves the exact submitted ISA QPY. The same
logical bit-to-classical bit mapping must survive transpilation. Use matched
all-zero/all-one readout controls on the measured physical qubits, and preserve
raw counts before any correction. Independent readout inversion is an additional
approximate analysis, not a replacement for raw data. Report calibration shots,
queue/run times and actual QPU usage separately from model gate accounting.

`adapters.score_counts(counts, metadata, target_data_z_marginal)` accepts those
raw logical-register counts. It returns raw accepted shots, event probability
with Wilson95% interval, full data-Z TV, selected data-Z TV and dirty-workspace
frequency. **Workspace is never silently postselected away.** No accepted shots
returns a null conditional estimate. Measured optical environments are not
expected clean: they contain the physical channel's purification information.

Raw acceptance can rise because noise populates the marked subspace. A useful
comparison therefore asks whether the conditional answer remains close to the
retained-model target, not simply whether more records pass the predicate.
Computational-basis distribution agreement alone cannot certify density-state
fidelity or preserved coherence. Conditional TV is also positively biased by
finite accepted-shot sampling; report counts and uncertainty rather than calling
any small discrepancy a hardware error floor.

At4,096shots the spatial plain event probability.0037066 yields only about15
accepted trials (one round.0330302 yields about135). The three-bin all-click event
is even rarer: approximately.000142 plain and.001278 after one round. These
histograms cannot support precise high-dimensional conditional conclusions at
that shot budget. Three-bin **last-click** events, approximately.161 plain and.895
after amplification, are more informative for a fixed small shot budget. The
all-click circuits are still meaningful explicit depth/rare-event stress tests.

The deepest routed circuits may be uninformative or may fail backend constraints.
Save those exact resource limits or negative observations. Do not replace their
channel dynamics by shallow fitted output rotations and label that a successful
replication. The classical channel recursion and exact spatial DP are strong,
cheap baselines here; no quantum computational advantage is established.

## Other families

The original QRSM already has a distinct hardware runner and remains the campaign
owner's responsibility. A faithful quantum-dot overlap circuit, a finite-Fock
interferometer for phase inspection, or an atomic Ramsey channel can be separate
digital kernel validations if constructed and checked against their actual
state/channel models. They do not automatically reproduce full optical device,
resource-budget, time-series inference or semiconductor performance studies.
This folder's adapter bundle covers only the optical retained-instrument and
spatial families above.
