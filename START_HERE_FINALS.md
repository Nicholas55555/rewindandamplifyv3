# Rewind & Amplify finals handoff

Current presentation revision: **11 November 2026**, incorporating the research followups, joint-photon QRSM and 10 new real IBM jobs. Team: FGCU Qubits. Finals: Saturday 14 November at FAU. The team's speaking limit is ten minutes.

## Open these first

1. **Presentation:** finals-deck/Rewind_Amplify_Finals_Visual.pptx. Slides 1–13 are the main talk, followed by technical backups. Planned delivery is **9:20**, including a **45-second original QRSM demo**, with 40 seconds before the limit.
2. **Presenter guide:** finals-deck/Visual_Presenter_Guide.md. Use its current narration, timing, sources and handoffs. The same notes are embedded in the PowerPoint.
3. **Offline application:** [Rewind_Amplify_v2_Demo.html](Rewind_Amplify_v2_Demo.html) is the portable single-file v2 demo, including videos and downloadable evidence. Open it directly in Chrome or Edge. The editable alternative is laser-diagnostics-app/index.html; keep that folder together. Start on the original QRSM chapter and select **Focus view**. **Current research** supports questions. The earlier sensor study remains explicitly labeled.
4. **Fallbacks:** finals-deck/Rewind_Amplify_Finals_Visual.pdf and the MP4s in animations/. The PDF is a static visual fallback without notes. The two 12-second silent videos explain concepts from earlier optical/sensing extensions; they are not current benchmark evidence or laboratory recordings.
5. **Portable public pack:** Rewind_Amplify_v2_Public_Pack.zip. Extract before opening the app. Rebuild it with `python build_finals_pack.py --public` if needed. Older local presentation archives predate this revision and may contain private judging material; use the public pack for sharing. A separate Rewind_Amplify_Research_Followups.zip retains the earlier checked research snapshot and its full circuit artifacts.

No account, server, Wi-Fi or live quantum processor is needed. Native PowerPoint playback, the projector and actual speaking time still need a rehearsal on the presentation computer. Prior root support documents and the previous portable pack are preserved in finals-archive/2026-11-11-before-research-update/.

## The original quantum-computing story

A click is a detection recorded as one in a time bin. It does not label a defect. On IBM hardware, superconducting qubits represent the emitter, hidden memory and output of a model.

The **QRSM supplies a physical model to test**. Each observed bit conditions its hidden state, which predicts later outcomes. Record likelihoods allow classical fitting and comparison of interactions, noise and detector behavior. Hidden interactions can change a state before readout, while detector imperfections can change the reported outcome. Both matter when interpreting repeated measurements. This project does not perform arbitrary state tomography or establish discovery of an unknown physical defect.

The useful original query is: **given a click at step 3, what happens later under each candidate model?** The exact example predicts a step-6 click probability of **4.67% with the modeled hidden defect versus 10.10% without it**. All earlier histories are allowed. These are specified-model predictions, not a physical diagnosis.

Rejection sampling wastes model runs that miss the selected event. Retained history qubits make preparation reversible, allowing amplitude amplification to return matching histories more often. Full ideal amplification preserves the conditional answer. Local reflection saves gates but is approximate, so both matching rate and answer accuracy must be checked. Direct classical methods are faster at the tested scale.

The featured new Marrakesh precision repeat uses the same steering and one amplification round: local/full circuits returned 6,300/5,674 matches out of 8,192 shots, with 58/125 native two-qubit gates and raw conditional-history TV distances 0.1177/0.1814. Initial qubit mappings were shared, but routing, operations and drift still differ. These are biased sampled answers, not a diagnosed physical defect or measured dollar saving. Older Kingston results remain labeled historical evidence in FINALS_EVIDENCE.md.

## What the new research changes

| Finding | Meaning for the presentation |
|---|---|
| Detector-aware inference | Ignoring dead time gave coupling 0.069 for synthetic truth 0.65; including it gave 0.706 and better predictions. Other parameters remained uncertain. |
| Unknown-onset frequency monitor | Timely detection is 51.35% with the conventional baseline, 58.02% with an atomic addition and 97.97% with a second conventional reference. Full-record false alarms are 5.42%, 5.16% and 4.06%. |
| Effective-drive amplitude monitor | In 96 arbitrary-time bins, +20% field-step detection within 32 bins is only 3.71%, with 6.84% stable-source false alarms. Most estimation improvement over a constant comes from the assumed positive prior. |
| Optical phase inspection | A fully charged hybrid gives 0.00637 rad global RMSE versus 0.00791 for the specified coherent comparator at 20,000 mean object-incident photons, 81% transmission/detection efficiency and 100% modeled preparation success. This does not establish feature inspection or wafer yield. |
| Full process circuit | Explicit 389-qubit constructions have 2.87–3.38 million generic CX gates as constructive upper bounds. Components and serialized wiring were checked; the full state was not simulated. Strong classical methods already solve this model. |

The new frequency study searches an unknown onset and scores the first alarm within a delay budget. The earlier app study knows the event time and uses different windows and calibration. Its 85.98% detection, 0.161 Hz RMSE and 80.10% atomic-drift false alarms must stay labeled as earlier results.

For inspection, preparation failure costs time at equal dose. At 1% pair-source success, the pure NOON probe takes 100 times as long as the coherent reference to match dose; the 10/90 hybrid takes 90.1 times as long under its fixed photon allocation. The benefit disappears in the tested equal-time case. Greater loss can remove even the equal-dose precision benefit. Direct quantum-light exposure remains a separate sensitivity study with hypothetical material coefficients and no printed structures.

## Semiconductor connection

The original QRSM asks how hidden dynamics change later measurement outcomes. An optically active quantum dot gives that question a semiconductor setting: a confined optical transition emits photons whose usefulness depends on interference, as well as their count rate. Our model checks that equal counts and zero multiphoton emission can hide different overlap. It also checks that pair memory matters at fixed individual-photon frequency distributions. The **Quantum dots** app view and backups 30–35 explain these results and the calibration limits in published GaAs measurements.

The practical target is selecting and tuning photon sources for quantum photonic chips. A future diagnostic would compare counts, interference and pair yield under calibrated, controlled changes. Extending the QRSM requires a two-photon measurement model and suitable records; the joint instrument is now implemented, checked and digitally executed on IBM; a fit to a physical dot remains absent. The current dot calculations and reanalysis run classically. See quantum_dot_bridge/README.md for the explicit mapping and proposed engineer workflow.

The external histograms are the authors' measurements. Their exact extraction settings are not fully specified, and three aggregated photon-delay pairs cannot identify a microscopic defect. These are useful source-characterization lessons; a lithography-laser monitor still needs its own compatible physical interface and validation.

## Ten-minute delivery and judge questions

The first nine slides explain the original problem, click, QRSM update, conditional answer, reversible query and current Marrakesh hardware. Use the 45-second original-model demo, then return to the deck. The remaining four main slides motivate chipmaking diagnosis, present the current frequency comparison, explain the research decisions and close with documented contributions.

Stop at slide 13. Use backups and **Current research** for amplitude/prior controls, phase ambiguity, cutoff/identifiability, exposure, full-grid resources and quantum-dot photon quality. If switching windows is awkward, use the slide's static original-query screenshot. Videos are optional conceptual fallbacks.

The documented roles remain Nicholas Taylor (QRSM/Grover and experiments), Timofey Yudintsev (research and search idea), Dan Izquierdo (experiments), and Dillon Satria Sitepu (formatting/revision), as confirmed by the user. Do not assign new AI-assisted work to a person without confirming it. FINALS_QA.md supplies shared answers and FINALS_RUBRIC.md maps all seven supplied criteria.

Before Saturday, rehearse aloud with all handoffs and the actual computer. Confirm event start time, Q&A, submission format and any rubric changes with the organizers. The written schedule is a plan rather than a measured rehearsal.

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

## Evidence and next steps

Run **python check_finals.py --public** from this folder for presentation/package and offline-evidence checks. It does not replace rehearsal. RESEARCH_CURRENT.md indexes the earlier studies; quantum_dot_bridge/README.md indexes the later semiconductor exploration. Their protocols, raw results and independent checks remain in the research directories. The prior research snapshot's statement that the finals deck was unchanged describes that earlier handoff; this revision now incorporates its conclusions.

The new IBM campaign is saved and can be reviewed offline without an API key or another job. Hardware can test a justified shallow circuit; it cannot validate optical coupling, detector calibration or material response. A practical diagnostic claim needs a compatible monitoring point, a defined measurand/bandwidth, synchronized conventional reference data and blinded source/nuisance changes. A chipmaking claim additionally needs measured source-to-process and material-response data. No yield, downtime or financial savings have been measured.
