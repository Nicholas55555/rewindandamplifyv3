# Finals preparation plan

## November 11: new real IBM execution and photon-memory research

The [hardware campaign](hardware_campaign/README.md) now contains newly submitted
and retrieved real IBM jobs, immutable circuits, raw counts, calibrations and
[analysis](hardware_campaign/RESULTS.md). Its [25-family coverage ledger](hardware_campaign/coverage.json)
distinguishes complete gate-model executions, component emulations, classical
studies and physical/resource limits. A component run does not reproduce an
entire online diagnostic or optical apparatus.

The [joint-photon QRSM extension](quantum_dot_bridge/qrsm_hom_followup/README.md)
is implemented and checked: sequential emission retains an environment state,
then a joint two-photon measurement conditions that state. Passive observations
can contain no information about the tested memory. At the initial controlled
64-pair budget, detection was 5.60% versus 4.50% null flags. A separately selected
and freshly validated control design reached 79.75% versus 4.85% at **2,584
attempted pairs**, with perfect reset/control assumptions. Strong classical HMMs
predicted equally well within uncertainty. At larger budgets, detector, mode or
collection changes produced severe false diagnoses. No physical dot was fitted
or diagnosed, and no quantum computational advantage was established.

Real superconducting circuits now test these specified models. They do not
establish optical coupling, wavelength compatibility, detector calibration,
resist response, manufacturing yield or economic savings. The available devices
have 156 qubits; the full 219/389-qubit spatial constructions cannot fit.

Current revision: 11 November 2026. Deliverables are the **Visual** presentation and notes, PDF fallback, offline application with current research views, MP4 conceptual fallbacks and portable presentation pack. START_HERE_FINALS.md identifies the files. Finals are Saturday 14 November at FAU; the team reports a ten-minute limit.

## The ten-minute story

Slides 1–9 retain the original quantum-computing centerpiece: why hidden interactions matter for state inference, what a click records, how the QRSM updates a hidden state, what the after-click prediction means, why rare conditioning wastes model runs, how the reversible Qiskit query works, and the new Marrakesh hardware cost/accuracy comparison. A fresh dead-time example makes misattribution of measurement statistics concrete. The 45-second app demo uses the original selected-click query.

Slides 10–13 connect semiconductor quantum-dot photon quality and laser diagnostics to device applications, use the new unknown-onset frequency comparison, explain the poor amplitude-monitor result and conditional phase-inspection opportunity, and close with contributions and lessons. The main talk contains 13 slides and a planned 9:20 of delivery. Backups hold the longer control, resource and numerical-validation discussions. Use finals-deck/Visual_Presenter_Guide.md for exact wording and handoffs.

The new frequency result retains its own task: unknown onset in a 128-second record, first alarm within 32 seconds, full-record false alarms and independent simulated sessions. The earlier known-time result remains labeled historical in the app. The amplitude model measures effective field drive in arbitrary units; the phase model estimates relative phase, not printed features.

## Completed technical and research work

- Reviewed the supplied documents and original archives as recorded in WORKSPACE_AUDIT.md.
- Reproduced the original after-click prediction and featured archived IBM comparison, including conditional accuracy and gate costs.
- Completed the continuation in RESEARCH_CURRENT.md: independent dynamics, joint inference/dead time, coherent histories, spatial sampling and full 49-cell construction, unknown-onset frequency monitoring, changing drive, quantum-light exposure and phase inspection.
- Preserved unfavorable outcomes and added a prior-only control explaining most of the amplitude estimator's apparent gain over a constant.
- Updated the presentation, evidence/Q&A/rubric notes and offline research views while retaining the original demonstration.
- Added a semiconductor quantum-dot study separating photon counts, single-photon purity, interference quality and collection cost. Published GaAs HOM histograms remain separately attributed external evidence; the bounded reanalysis has its own protocol and uncertainty limits.

Ten new IBM jobs executed model circuits on real superconducting hardware. No optical laser or wafer experiment was performed. Source models, weak material response, apparatus resources and reference stability remain assumptions. The phase result is conditional; poor drive detection constrains the tested regime. The full 389-qubit construction is not a full-state simulation or a minimum-cost proof.

## Team preparation before Saturday

1. Use the original documented roles confirmed by the user. Every speaker should explain the problem, contribution, result, cost, limitation and one changed conclusion.
2. Rehearse all 13 main slides aloud with the app switch and handoffs. Finish by 9:20; trim examples before removing essential scope labels.
3. Test the PPTX, PDF, offline app and MP4s on the actual computer/projector. Keep the static original-query screenshot ready.
4. Confirm event start time, Q&A, submission format, rubric and disclosure requirements with the organizers.
5. Extract and test one current portable pack, and keep a second local copy. The demonstration needs neither an API token nor internet access.

## Research after this presentation

Physical validation needs a compatible optical platform, a defined measurand/bandwidth, characterized detector/reference behavior and synchronized conventional observations under blinded perturbations. Calibrated phase-object measurements could test the favorable inspection regime. Chipmaking translation requires a distinct DUV, CO₂-drive or EUV interface and measured process consequences.

Further local research includes different operating points and acquisition budgets, decreased drive, slow spectral diffusion, richer classical state-space methods and optimized synthesis. These are separate hypotheses, not findings to imply on stage. No IBM key is needed for the present presentation or checked research.
