# Finals preparation plan (V3)

Revision: 12 November 2026. Finals: Saturday 14 November 2026 at FAU. Speaking limit: ten minutes.

[`START_HERE_FINALS.md`](START_HERE_FINALS.md) lists the files to open. This page is the checklist.

## What changed from V2

V2 had the science and the evidence. Its weak points were the ones a talk depends on: a text-heavy main deck, six studies competing for ten minutes, no picture of what the model does, and a "demo" slide that was a screenshot.

V3 keeps every V2 result and adds:

- **The Lab**, a live simulation of the model that shows the laser, the emitter, the hidden defect and the detector, and then the rewind-and-amplify steps on real amplitudes.
- **A rebuilt main talk** in the order the rubric asks its questions, one picture per slide, with a playable 45-second video.
- **A simulator-against-hardware study** of the exact circuits that ran on IBM, which answers "why did the lighter build win?" with a number.
- **`python reproduce.py`**, so "does the code run?" has a ten-second answer.

The follow-up research (detector dead time, quantum dots, laser monitoring, phase inspection, circuit costs) moved from the main talk to one slide and the backups. It is still all here, in the research explorer and in [`RESEARCH_CURRENT.md`](RESEARCH_CURRENT.md).

## Done

- [x] Lab built, with an engine tested against Qiskit to 10⁻¹² and displayed numbers tested against the saved IBM counts
- [x] Noise-model study run, tested and written up
- [x] Deck rebuilt; opens in PowerPoint without repair; both videos register as embedded movies
- [x] Presenter guide, Q&A, rubric map and evidence map rewritten for V3
- [x] All V2 checks still pass: 114 core tests, 311 research tests, artifact hashes, hardware verification

## To do before Saturday (the team)

1. **Rehearse aloud with a timer**, all four speakers, at least twice. Target 9:20. The speaker assignments in the notes are suggestions.
2. **Confirm roles on slide 13 and in the README.** The video credit was added in V3: check that it is right.
3. **Decide the opening.** Either start on the cover, or play the cinematic cut on slide 37 first. If you play it, demo the Lab live on slide 10 instead of playing the second video.
4. **Test on the presentation computer**: the PowerPoint, both videos, sound, and the Lab in its browser.
5. **Confirm with the organizers**: start time, Q&A length, submission format, any rubric change, and what must be disclosed about AI assistance.
6. **Each member**: prepare one sentence on what you learned and one limitation you can explain.
7. **Turn on GitHub Pages** for the repository (Settings, Pages, deploy from branch `main`, folder `/`), so the "Open the Lab" link in the README and the QR code on the slides open the live page.

## If something breaks on the day

| Problem | Do this |
|---|---|
| The video on slide 10 will not play | Open `Rewind_Amplify_Lab.html`, press **45 s tour**, say the same words |
| No PowerPoint on the venue computer | Present `Rewind_Amplify_Finals_V3.pdf` and run the Lab in a browser for the demo |
| Running long | Cut slide 11 to one sentence and go to slide 12. Do not cut the limits on slides 6 and 12. |
| A question nobody can answer | "We did not test that." Then say what you would test. |

## After the finals

The next experiment is on slide 12: fit candidate models to held-out, calibrated device records and compare with a strong classical hidden-Markov baseline. The open research questions are listed at the end of [`RESEARCH_CURRENT.md`](RESEARCH_CURRENT.md).
