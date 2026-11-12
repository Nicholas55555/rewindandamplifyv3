# Start here: finals handoff (V3)

Team: FGCU Qubits. Finals: Saturday 14 November 2026 at FAU. Speaking limit: ten minutes. Revision: 12 November 2026.

Nothing here needs an account, a server, Wi-Fi or a live quantum processor.

## Open these four things

| | File | What it is |
|---|---|---|
| 1 | [`finals-deck/Rewind_Amplify_Finals_V3.pptx`](finals-deck/Rewind_Amplify_Finals_V3.pptx) | The talk: 13 main slides, planned 9:25, then 26 backups in the same style. Speaker notes are inside. Slide 10 holds a real, playable 70-second video. |
| 2 | [`Rewind_Amplify_Lab.html`](Rewind_Amplify_Lab.html) | The Lab: one file, opens in Chrome or Edge, works offline. This is the live demo and the fallback if the video will not play. |
| 3 | [`finals-deck/Presenter_Guide_V3.md`](finals-deck/Presenter_Guide_V3.md) | The same narration as the slide notes, with timing, cues and sources. |
| 4 | [`FINALS_QA.md`](FINALS_QA.md) | Twelve questions to rehearse, then longer answers. |

Fallbacks: [`finals-deck/Rewind_Amplify_Finals_V3.pdf`](finals-deck/Rewind_Amplify_Finals_V3.pdf) (static, no video), [`media/lab-tour.mp4`](media/lab-tour.mp4), its 45-second version [`media/lab-tour-45s.mp4`](media/lab-tour-45s.mp4) and [`media/cinematic-45s.mp4`](media/cinematic-45s.mp4) as loose files.

## The story in seven sentences

Every speaker should be able to say this without slides.

1. A detector records one bit per step, and a hidden defect can change the pattern without anyone seeing it.
2. We model that as a QRSM, a quantum recurrent state machine: two memory qubits that are never measured, one bit out per step.
3. The useful question is about a rare event: given a click at step 3, the chance of a click at step 6 is 10.10% with no defect and 4.67% with one.
4. Studying a rare event the ordinary way throws most runs away, and amplitude amplification could fix that, but it must run the machine backwards and a reset cannot be undone.
5. So we made the machine reversible, steered it, amplified with a lighter reflection, and on IBM Marrakesh the lighter build hit the click in 76.90% of shots against 69.26% for the textbook build, with 58 gates against 125.
6. There is no speedup today, no real defect was detected, and a simple noise model explains both the gap and the bias in the answers.
7. We asked the same question of photon sources, a laser monitor and chip printing. Those are simulations, and one of them went against us: an ordinary second reference beat our atomic sensor.

## The numbers to know cold

| Number | What it is | Where it comes from |
|---|---|---|
| 10.10% and 4.67% | Chance of a click at step 6 given one at step 3, without and with the defect. Exact. | `research-validation/original_after_click_verification.json` |
| 3.95% | Chance of the click at step 3 with the defect. About 25 runs per useful sample. | same |
| 27,495,891 | Runs to match one real 64-step record by rejection. 6,240 with steering. 125 machine calls with amplification on top. | `rewindandamplify-main/results/numbers.json` |
| 96.10% and 96.49% | Ideal simulator, local and full reflection, one round | `python reproduce.py` |
| **76.90% and 69.26%** | **Measured on IBM Marrakesh**: 6,300 and 5,674 of 8,192 shots | `hardware_campaign/runs/original_precision_v1/` |
| 58 and 125 | Native two-qubit gates, local and full | same |
| 0.118 and 0.181 | Error in the answer (TV distance), local and full. Lower is better. | same |
| 6.74% | The same chip with no amplification | `hardware_campaign/runs/original_plain_v2/` |
| 78.40% and 69.72% | Our noise model's prediction, fitted only on echo circuits | `hardware_campaign/noise_model/` |
| 1.54× | How much noisier the chip was than its calibration said | same |
| 8.79% and 11.66% | The two futures as measured with the lighter build: right order, biased | `hardware_campaign/runs/original_precision_v1/` |
| `dbqb1ifv5hds73dfo310` | The IBM job ID of the featured run | same |
| 0.0% and 0.8% | Photon pairs that split, for two sources of identical brightness. Simulated. | `quantum_dot_bridge/results.json` |
| 51%, 58%, 98% | Laser steps caught within 32 s: ordinary reference, plus atoms, two ordinary references. Simulated. | `laser_sensor_viability/followup/main/results.json` |
| 95% and 83% | Resist cells printed right: entangled pairs, best laser route, for 18 times the photons. Simulated. | `quantum_lithography_poc/exposure_followup/results.json` |
| 389 and 156 | Qubits our full chipmaking question needs, and qubits on the chip. Built and checked, not run. | `finals-lithography/full_spatial_circuit/results.json` |

## The demo, and what to do if it fails

Slide 10 plays a 70-second screen recording of the Lab. Click the video once. It is silent, so talk over it using the notes. The first 41 seconds are the project; the last 29 are the three research tabs: photons, lasers, chipmaking.

If the video will not play, switch to `Rewind_Amplify_Lab.html`, press the tour button in the top right corner, and say the same words. Useful keys in the Lab: arrows change scene, **1** to **9** and **0** jump to a scene, **T** switches plain and technical captions, **R** reveals the hidden defect, **D** removes it, space pauses.

Short on time: stop the video at 41 seconds, when the IBM hardware scene ends, and let slide 11 cover the research.

Optional cold open: slide 39 holds the team's cinematic cut with music. If you open with it, stop the Lab video at 41 seconds or use the 45-second version, or the talk will run over.

## Before Saturday

1. Rehearse aloud, all four speakers, with a timer. The plan is 9:25. Speaker assignments in the notes are suggestions.
2. Test the PowerPoint, both videos and the Lab on the actual presentation computer and projector. Check that sound is where you want it: the Lab video is silent, the cinematic cut has music.
3. Confirm with the organizers: start time, Q&A length, submission format, and any change to the rubric.
4. Keep a second copy of this folder on a USB stick.
5. Read [`FINALS_RUBRIC.md`](FINALS_RUBRIC.md) once together. It maps each criterion to a slide.

## What must not be said

- That we have a quantum speedup or advantage.
- That we detected a real defect, measured photons, or inspected a wafer.
- That amplitude amplification is our invention.
- That the 76.90% is an accuracy. It is how often the requested click showed up; the answer error is the separate number.
- That the laser-sensing or quantum-dot studies are measurements. They are simulations and a reanalysis of published data.

## Check the package

```bash
python check_finals.py --public
```

It verifies the deck (slide and note counts, the talk plan, the backups' notes and theme, both embedded videos), the Lab, and the hash of every saved result that a slide quotes. If it reports that a result changed since the deck was built, rebuild the deck: see [`finals-deck/README.md`](finals-deck/README.md).

## Where the detail lives

- Evidence for every headline number: [`docs/EVIDENCE.md`](docs/EVIDENCE.md)
- The IBM campaign: [`hardware_campaign/RESULTS.md`](hardware_campaign/RESULTS.md) and [`hardware_campaign/noise_model/README.md`](hardware_campaign/noise_model/README.md)
- The follow-up research and its negative results: [`RESEARCH_CURRENT.md`](RESEARCH_CURRENT.md), or open [`Rewind_Amplify_Research_Explorer.html`](Rewind_Amplify_Research_Explorer.html)
- The V2 handoff this replaces: [`finals-deck/v2/`](finals-deck/v2/) and the V2 repository
