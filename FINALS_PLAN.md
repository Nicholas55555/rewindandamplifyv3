# Finals preparation plan (V3)

Revision: 12 November 2026. Finals: Saturday 14 November 2026 at FAU. Speaking limit: ten minutes.

[`START_HERE_FINALS.md`](START_HERE_FINALS.md) lists the files to open. This page is the checklist.

## What changed from V2

V2 had the science and the evidence. Its weak points were the ones a talk depends on: a text-heavy main deck, six studies competing for ten minutes, no picture of what the model does, and a "demo" slide that was a screenshot.

V3 keeps every V2 result and adds:

- **The Lab**, a live simulation of the model that shows the laser, the emitter, the hidden defect and the detector, and then the rewind-and-amplify steps on real amplitudes. Three more tabs animate the follow-up research: photons at a beam splitter, a laser monitor with an atomic sensor, and light printing stripes on a resist.
- **A rebuilt main talk** in the order the rubric asks its questions, one picture per slide, with a playable 70-second video.
- **Backups in the same style**: 28 of them, grouped by question, each marked with the kind of evidence it shows.
- **A simulator-against-hardware study** of the exact circuits that ran on IBM, which answers "why did the lighter build win?" with a number.
- **`python reproduce.py`**, so "does the code run?" has a ten-second answer.
- **One question, three fields** ([`applied/`](applied/)): our own machine asked what chipmaking, lasers and photon sources need to know, on IBM hardware, with one job predicted before it ran. It is the green line on each research tab and on slide 11, and backups 40 and 41.

The follow-up research (detector dead time, quantum dots, laser monitoring, phase inspection, circuit costs) is in the last 29 seconds of the demo, on slide 11 and in the backups. It is still all here, in the Lab's research tabs, the research explorer and [`RESEARCH_CURRENT.md`](RESEARCH_CURRENT.md).

## Done

- [x] Lab built, with an engine tested against Qiskit to 10⁻¹² and displayed numbers tested against the saved IBM counts
- [x] Noise-model study run, tested and written up
- [x] Deck rebuilt, backups included; opens in PowerPoint without repair; both videos register as embedded movies
- [x] Research tabs built, with their formulas and numbers tested against the studies' saved files
- [x] Repository public, CI green, and the Lab live at https://nicholas55555.github.io/rewindandamplifyv3/
- [x] Presenter guide, Q&A, rubric map and evidence map rewritten for V3
- [x] All V2 checks still pass: 114 core tests, 311 research tests, artifact hashes, hardware verification
- [x] Our own machine asked the three fields' question on IBM Marrakesh (12 November, job `dbr51dhabdes73fpaum0`), with predictions written before the run; 27 more tests

## To do before Saturday (the team)

1. **Rehearse aloud with a timer**, all four speakers, at least twice. Target 9:25. The speaker assignments in the notes are suggestions.
2. **Confirm roles on slide 13 and in the README.** The video credit was added in V3: check that it is right.
3. **Decide the opening.** Either start on the cover, or play the cinematic cut on slide 39 first. If you play it, stop the Lab video on slide 10 at 41 seconds, or use the 45-second version.
4. **Test on the presentation computer**: the PowerPoint, both videos, sound, and the Lab in its browser.
5. **Confirm with the organizers**: start time, Q&A length, submission format, any rubric change, and what must be disclosed about AI assistance.
6. **Each member**: prepare one sentence on what you learned and one limitation you can explain.
7. **Try the QR code** on slides 10 and 13 with a phone: it opens the repository, whose first link opens the live Lab.
8. **Read backups 40 and 41 together**, and decide whether slide 11's speaker adds one sentence about the green lines: "we asked each field's question of our own machine on IBM; plain sampling got the chip answer backwards and rewinding got it right." Add it only if the timer allows. Read [`applied/README.md`](applied/README.md) for what did not repeat.

## If something breaks on the day

| Problem | Do this |
|---|---|
| The video on slide 10 will not play | Open `Rewind_Amplify_Lab.html`, press the tour button, say the same words |
| No PowerPoint on the venue computer | Present `Rewind_Amplify_Finals_V3.pdf` and run the Lab in a browser for the demo |
| Running long | Stop the slide 10 video at 41 seconds, cut slide 11 to one sentence and go to slide 12. Do not cut the limits on slides 6 and 12. |
| A question nobody can answer | "We did not test that." Then say what you would test. |

## After the finals

The next experiment is on slide 12: fit candidate models to held-out, calibrated device records and compare with a strong classical hidden-Markov baseline. The open research questions are listed at the end of [`RESEARCH_CURRENT.md`](RESEARCH_CURRENT.md).
