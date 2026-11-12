# Current finals talk

Updated 11 November 2026. Use **finals-deck/Visual_Presenter_Guide.md** for the complete narration, sources and handoffs. The same notes are embedded in **Rewind_Amplify_Finals_Visual.pptx**.

The plan is **9 minutes 20 seconds**, including a **45-second original QRSM demo**, leaving 40 seconds before the ten-minute limit. Slides 1–13 form the main talk; slides 14–35 are backups. This is a timing plan, not a measured team rehearsal.

| Time | Topic |
|---|---|
| 0:00–0:15 | Rewind & Amplify |
| 0:15–1:00 | Hidden defects can change the state before readout |
| 1:00–1:35 | A click is one recorded measurement outcome |
| 1:35–2:35 | The QRSM connects each bit to a hidden-state model |
| 2:35–3:20 | Hidden memory changes what follows a click |
| 3:20–4:05 | Rare conditions waste ordinary samples |
| 4:05–5:00 | A reversible model makes amplification possible |
| 5:00–6:00 | More matching answers with fewer gates |
| 6:00–6:45 | The query returns a prediction about the next clicks |
| 6:45–7:25 | Quantum-dot source quality and the QRSM |
| 7:25–8:10 | The classical reference leads with unknown onset |
| 8:10–8:50 | The evidence changes our next experiment |
| 8:50–9:20 | Our contribution and what we learned |

The first nine slides explain the original quantum-computing project. Define the click, explain the QRSM hidden-state update and why detector errors can mislead defect inference, show the useful after-click prediction, then distinguish classical fitting from coherent amplification. A higher matching rate is valuable only when the conditional answer remains accurate.

The main sensor chart now uses unknown-onset monitoring: detect the first source event within 32 seconds of its unknown onset in a 128-second record. False alarms refer to the entire record. The earlier known-time experiment remains separately labeled in the app and must not supply rates, RMSEs or failure-case numbers for this chart.

Slide 10 explicitly connects the original QRSM question to semiconductor photon-source quality. The QRSM predicts observations conditioned on hidden dynamics; a dot supplies a possible physical emitter and environment to investigate. Our model shows why counts alone miss interference quality, and why correlations matter. The proposed practical use is qualifying or tuning sources for quantum photonic chips with calibrated measurements and a yield budget. The joint two-photon measurement model is now implemented and checked, including IBM digital emulation. It is not fitted to a physical source; the key lessons are acquisition cost, nuisance ambiguity and competitive classical predictors. Keep the memory comparison and external HOM extraction in backups 30–35. A lithography-laser diagnostic still needs a separate compatible interface and physical test.

The research decision slide includes the poor amplitude-monitor result and a conditional phase-inspection opportunity. Explain that most of the apparent amplitude-estimation gain came from the positive prior. Phase estimation at matched object-incident photons does not establish a printed-feature or wafer benefit. Keep the detailed budgets and controls for Q&A.

## Backup map

| Slide | Topic |
|---:|---|
| 14 | Hardware repeats and noise controls |
| 15 | Deep optical queries show large distribution errors |
| 16 | Sensor assumptions and resource accounting |
| 17 | Calibration failures can reverse the conclusion |
| 18 | Detector dead time can distort inferred coupling |
| 19 | Where the quantum component enters |
| 20 | The transfer to lithography needs its own test |
| 21 | The continued query separates models with bias |
| 22 | One step of the recurrent quantum model |
| 23 | Judging rubric and evidence map |
| 24 | Contribution, prior work and AI assistance |
| 25 | Drive amplitude: a useful negative result |
| 26 | Phase inspection: benefit depends on the budget |
| 27 | The full spatial query is costly to construct |
| 28 | Exposure: contrast trades against dose and loss |
| 29 | Model accuracy is part of the resource budget |
| 30 | Equal photon counts can hide poor interference |
| 31 | External GaAs data: a conditional reanalysis |
| 32 | The joint-photon QRSM observation model |
| 33 | More data helps only under trusted calibration |
| 34 | Atomic and photon channels on IBM |
| 35 | Hardware coverage and circuit limits |

The user confirmed the original README roles. Use the guide’s suggested handoffs and rehearse with all four presenters. Read **FINALS_QA.md** together and use **FINALS_RUBRIC.md** to check all seven supplied criteria. The new research is AI-assisted; do not assign its individual implementation work to a teammate without confirmation.

Test the final PPTX, PDF, offline application and MP4 videos on the actual presentation computer. Videos remain conceptual illustrations of the earlier optical extensions. Use the original-query screenshot if window switching is awkward. No API token or network access is needed.

The current Presenter Guide is authoritative for revised slide wording. New backups 32–35 cover the joint-photon instrument, calibrated-design power and failure modes, atomic/photon channel execution, and hardware coverage limits. Use the new Marrakesh first/precision-repeat numbers separately; retain Kingston figures only as labeled historical evidence.
