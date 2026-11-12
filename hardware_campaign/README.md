# IBM hardware campaign — November 11, 2026

This campaign executes the project's feasible gate-model circuits on real IBM
Quantum hardware. It also tests digital representations of specified atomic,
photonic and semiconductor-pattern models. A superconducting processor does
not replace a laser, quantum-dot source, photon detector, resist or fabricated
wafer. Those apparatus claims require separate physical measurements.

The campaign completed **10 real jobs: 207 science and 40 calibration circuit
executions,688,640 shots and 244 quantum seconds**. Read the [results](RESULTS.md)
and [coverage ledger](coverage.md) for the separate scopes and failure cases.
A prepared circuit is not a submitted job, and a submitted job is not a
completed experiment. The authoritative evidence is each
`runs/<label>/job.json`, `status.json`, `raw.json` and its immutable `plan.json`.

## Execution and analysis contract

- Use the saved IBM Quantum Platform account only after verifying its active
  instance is Open Plan. Never copy credentials or instance identifiers here.
- Each submitted plan has `dry_run: false`, a real backend, fixed shots,
  compiled QPY, exact logical references, source hashes, measurement mappings,
  a unique remote tag, and an explicit quantum-time cap.
- Preserve an exclusive submission intent before making the API call. After
  an interrupted call, reconcile the tag; never blindly submit it again.
  A campaign-wide lock prevents concurrent quota reservations.
- Quota checks reserve other unfinished campaign jobs at their full caps and
  retain a five-second buffer. Calibrated duration estimates exclude service
  overhead; the configured cap remains authoritative.
- Select a connected device patch using published calibration errors before
  seeing outcomes. Use the same logical-to-physical prefix within each bundle.
  Paired plain/suppressed jobs reuse the **identical compiled QPY**. Routing
  can still change final measurement placement between different circuits;
  each actual classical-bit-to-physical-qubit map is recorded.
- Include all-zero, all-one and two alternating preparation patterns. These
  measure preparation/readout errors and expose some correlations; they do
  not establish a perfect independent-noise model. Raw counts are primary.
  Any independent-readout correction is a secondary sensitivity analysis.
- Randomize PUB ordering using seed 20261111. Record actual hardware usage,
  backend, job ID and timestamps. No hardware calls run in tests or CI.
- Compare raw event rates **and** conditional answer distributions. Noise can
  increase a selected-event rate while making its answer wrong. Report kept
  counts, zero-acceptance cases and dirty workspace; do not silently discard
  dirty ancillas. Z-basis agreement is not full quantum-state fidelity.
- Binomial intervals quantify finite-shot uncertainty in individual observed
  rates. They do not include calibration drift, model error or simultaneous
  testing. All comparisons are exploratory unless a source study explicitly
  declares a separate held-out protocol.

These written notes were assembled after the first two jobs were submitted;
the timestamped per-job plans are the evidence for choices made beforehand.
The logical synthetic studies have their own separately frozen protocols.

## Families and reproducibility

`coverage.json` and `coverage.md` track every research family, including
classical-only studies, partial hardware representations, width limits and
missing physical measurements. A component run never silently replaces the
full original experiment.

- `original_bundle_v2`: original QRSM suite plus full/memory-only loop controls.
- `feasibility/bundle_v1`: small optical instrument and correlated 2×2 pattern
  circuits, including expensive constructions retained as noise stress tests.
- `optical_controls/bundle_v2`: complete finite-pulse qubit channels, NOON and
  incoherent-mixture controls, and finite coherent-state photon sectors.
- `../quantum_dot_bridge/qrsm_hom_followup/hardware_bundle_v2`: sequential
  emitter/environment and joint-photon measurement circuits, plus the frozen
  classical pair-memory benchmark. These prepare actual model states and
  measurement interactions rather than loading a final success probability.
- `extensions/bundle_v1`: independent-site counter/enumerated oracles,
  actual 16-entry semantic reader, separately labeled 1,024-entry random-diagonal
  cost benchmark, fixed-round 8-step histories and 10-step bounded rewinding.
- `../quantum_dot_bridge/qrsm_hom_followup/exploratory_design/hardware_bundle`:
  four-pair controlled and passive circuits, up to 29 qubits. Sparse declared
  flag/memory marginals were checked against the full actual compiled circuits
  using MPS simulation; no 2^29 probability vector is required for analysis.

Failed local export attempts are retained as development evidence and are not
hardware results. The original v1 QRSM metadata used a contiguous history-bit
assumption for loop circuits; v2 explicitly maps around any work qubits. The
v1 plan was never submitted.

The unsubmitted optical-dilation v1 ISA file is preserved locally. Its v2 plan
contains a lossless gzip copy for public distribution, with both compressed
and original byte hashes. This storage change leaves every circuit unchanged.
All 10 submitted jobs finished; there are no unresolved submission intents or
pending jobs in this campaign. 332 seconds remained in the Open Plan at the
final fetch (November 11, 18:25 UTC); 24 seconds had been consumed before this work.

Example (requires the project's scientific environment and saved account):

```powershell
python hardware_campaign/campaign.py prepare --bundle hardware_campaign/original_bundle_v2 --label my_run --shots 2048 --cap 90
python hardware_campaign/campaign.py submit --label my_run
python hardware_campaign/campaign.py fetch --label my_run
```

Existing labels are immutable. The `clone` subcommand creates a paired plan
from the exact ISA circuits; it does not submit a job.

IBM's current Open Plan provides 10 minutes in a rolling 28-day window; the
campaign checks the live allowance rather than assuming a monthly reset.
Sources: [instances](https://quantum.cloud.ibm.com/docs/en/guides/instances),
[maximum execution time](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time),
[job usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time).
