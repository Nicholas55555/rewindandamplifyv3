# The finals talk (V3)

Updated 12 November 2026. The complete narration, cues and sources are in [`finals-deck/Presenter_Guide_V3.md`](finals-deck/Presenter_Guide_V3.md), and the same notes are inside [`finals-deck/Rewind_Amplify_Finals_V3.pptx`](finals-deck/Rewind_Amplify_Finals_V3.pptx).

The plan is **9 minutes 20 seconds**, including a **45-second Lab demo**, which leaves 40 seconds before the ten-minute limit. Slides 1 to 13 are the talk. Slides 14 to 38 are backups. This is a plan, not a measured rehearsal: time it aloud.

| Time | Slide | What the audience should take away | Suggested speaker |
|---|---:|---|---|
| 0:00–0:15 | 1 | Who we are, in one breath | Nicholas |
| 0:15–1:00 | 2 | Something hidden changes the signal, and three kinds of people have that problem | Dan |
| 1:00–1:50 | 3 | Our model: a recurrent machine whose memory is qubits (QRSM) | Nicholas |
| 1:50–2:35 | 4 | One click, two futures: 10.10% against 4.67% | Nicholas |
| 2:35–3:10 | 5 | The useful runs are rare, so ordinary sampling wastes almost all of them | Timofey |
| 3:10–4:05 | 6 | Why quantum might help, the two catches, and no speedup today | Timofey |
| 4:05–5:00 | 7 | Our four moves: purify, steer, amplify locally, verify | Nicholas |
| 5:00–6:00 | 8 | On IBM hardware the lighter build won: 76.90% against 69.26% | Dillon |
| 6:00–6:45 | 9 | A noise model predicts the gap; suppression did not help | Dillon |
| 6:45–7:35 | 10 | The Lab, running (45-second video, or live) | Timofey |
| 7:35–8:15 | 11 | Who could use this, scored honestly, including a result that went against us | Dan |
| 8:15–8:50 | 12 | What we claim, what we do not, and the next experiment | Nicholas |
| 8:50–9:20 | 13 | Roles, three lessons, thank you | All four |

Speaker assignments are suggestions that give every member a part with a result in it. Change them freely. Each person should present something they can answer questions about.

## How the talk is built

The order follows the rubric: problem first, then why quantum and its limits, then what we built, then results against simulator and hardware, then who it is for.

One picture per slide. Most pictures are captures of the running Lab, so the talk, the demo and the repository show the same thing.

One name for each idea. Say **hidden defect** for the unseen two-level system, **click** for a recorded 1, **the lighter build** for steering plus local reflection, and **the textbook build** for steering plus full reflection. The deck uses the same words.

Say the limits out loud, at slide 6 and again at slide 12. The second judging criterion asks for exactly that.

## The demo

Slide 10 holds [`media/lab-tour.mp4`](media/lab-tour.mp4), a 45-second screen recording of the Lab, embedded as real video. Click it once to play. It is silent: narrate it with the words in the notes.

If it does not play, open `Rewind_Amplify_Lab.html` and press **45 s tour**. The page does the same thing live.

To do the demo live from the start, open the Lab before the talk, leave it on scene 1, and switch windows at slide 10. Budget the same 45 seconds.

## The optional cold open

Slide 37 holds the team's 45-second cinematic cut with original music. To open with it, type **37** and **Enter** on the cover, play it, then type **2** and **Enter**.

Two 45-second videos do not fit in ten minutes. If you open with the cinematic cut, replace the video on slide 10 with a short live look at the Lab (20 seconds on scenes 1 and 4), and rehearse the total.

## Backup map

| Slide | Topic |
|---:|---|
| 14 | Hardware repeats and noise controls: all three runs of 11 November |
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
| 36 | The noise model, circuit by circuit |
| 37 | The cinematic cut (video) |
| 38 | Anyone can rerun it: `python reproduce.py` |

In PowerPoint's slide show, type a slide number and press Enter to jump to it.

## On the day

Test the PowerPoint, both videos and the Lab on the presentation computer. Videos embedded in a PowerPoint play in PowerPoint for Windows and Mac. They do not play in the PDF, and may not play in Google Slides or Keynote: if the venue uses one of those, use the loose MP4 files in [`media/`](media/) or run the Lab live.
