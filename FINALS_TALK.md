# The finals talk (V3)

Updated 12 November 2026. The complete narration, cues and sources are in [`finals-deck/Presenter_Guide_V3.md`](finals-deck/Presenter_Guide_V3.md), and the same notes are inside [`finals-deck/Rewind_Amplify_Finals_V3.pptx`](finals-deck/Rewind_Amplify_Finals_V3.pptx).

The plan is **9 minutes 25 seconds**, including a **70-second Lab demo**, which leaves 35 seconds before the ten-minute limit. Slides 1 to 13 are the talk. Slides 14 to 39 are backups. This is a plan, not a measured rehearsal: time it aloud.

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
| 6:45–8:00 | 10 | The Lab, running: the project in 41 seconds, then photons, lasers and chipmaking in 29 | Timofey |
| 8:00–8:20 | 11 | Those three tests, scored honestly, including the one that went against us | Dan |
| 8:20–8:55 | 12 | What we claim, what we do not, and the next experiment | Nicholas |
| 8:55–9:25 | 13 | Roles, three lessons, thank you | All four |

Speaker assignments are suggestions that give every member a part with a result in it. Change them freely. Each person should present something they can answer questions about.

## How the talk is built

The order follows the rubric: problem first, then why quantum and its limits, then what we built, then results against simulator and hardware, then who it is for.

One picture per slide. Most pictures are captures of the running Lab, so the talk, the demo and the repository show the same thing.

One name for each idea. Say **hidden defect** for the unseen two-level system, **click** for a recorded 1, **the lighter build** for steering plus local reflection, and **the textbook build** for steering plus full reflection. The deck uses the same words.

Say the limits out loud, at slide 6 and again at slide 12. The second judging criterion asks for exactly that.

## The demo

Slide 10 holds [`media/lab-tour.mp4`](media/lab-tour.mp4), a 70-second screen recording of the Lab, embedded as real video. Click it once to play. It is silent: narrate it with the words in the notes.

| Seconds | What is on screen | What to say |
|---|---|---|
| 0–12 | The laser, the emitter, the hidden defect, the detector | The model, and that the detector clicks |
| 12–19 | Rows of runs piling up | Most runs miss the rare click |
| 19–28 | Mark, rewind, reflect, replay | Rewind and amplify: 96 percent |
| 28–41 | Two futures, then the IBM result | One click, two futures; fewer gates won |
| 41–49 | Two photons at a beam splitter | Equally bright sources: only the pairs reveal the hidden memory |
| 49–57 | A laser, an ordinary receiver, a cloud of atoms | The atomic sensor helped a little; a second ordinary reference far more |
| 57–66 | Light printing stripes on a resist | Entangled pairs print cleaner stripes, and pay for it in photons |
| 66–70 | What we claim and do not claim | Hand over to slide 11 |

If it does not play, open `Rewind_Amplify_Lab.html` and press the tour button in the top right corner. The page does the same thing live.

**Short on time?** Stop the video when the IBM hardware scene ends, at 41 seconds. Or use the 45-second version, [`media/lab-tour-45s.mp4`](media/lab-tour-45s.mp4), which leaves the three research tabs to slide 11.

To do the demo live from the start, open the Lab before the talk, leave it on scene 1, and switch windows at slide 10. Budget the same 70 seconds. Keys **7**, **8** and **9** jump to the Photons, Lasers and Chipmaking tabs.

## The optional cold open

Slide 39 holds the team's 45-second cinematic cut with original music. To open with it, type **39** and **Enter** on the cover, play it, then type **2** and **Enter**.

The cinematic cut and the 70-second Lab video do not both fit in ten minutes. If you open with the cinematic cut, stop the Lab video at 41 seconds or show a short live look at the Lab instead, and rehearse the total.

## Backup map

Slide 14 is this map, inside the deck. Every backup's speaker note starts with the question that should bring it up.

| Slides | Topic | What is there |
|---:|---|---|
| 15–19 | On IBM hardware | What each move bought (15), three runs (16), the noise model circuit by circuit (17), deeper circuits that failed (18), what ran and where it stops (19) |
| 20–23 | Method and credit | One step in gates and maths (20), `python reproduce.py` (21), the rubric map (22), what is ours, prior work and AI (23) |
| 24–29 | Light: photons and detectors | Equally bright, not equally good (24), a real quantum dot reanalysed (25), the detector's blind time (26), a QRSM for photon pairs (27), more data against calibration (28), better model, more qubits (29) |
| 30–34 | Lasers | Monitors under stress (30), what the monitor assumes (31), the atomic channel on IBM (32), drive amplitude: a negative result (33), where the quantum part enters (34) |
| 35–38 | Chipmaking | Sharper lines for more photons (35), the 389-qubit question (36), reading a phase (37), real lithography light (38) |
| 39 | Video | The cinematic cut |
| 40–41 | Our machine, three fields | Our own machine asked the chipmaking, laser and photon question on IBM, plain sampling against rewound, both runs (40); the 12 November job, predicted and then measured (41) |

In PowerPoint's slide show, type a slide number and press Enter to jump to it.

**If a judge asks what the three follow-up studies have to do with the method**, go to slide 40. One sentence is enough on slide 11, where each card now ends with a green line: "And we asked each field's question of our own machine on IBM: plain sampling got the chip answer backwards, rewinding got it right." Say it only if rehearsal shows the 20 seconds on slide 11 can hold it.

## On the day

Test the PowerPoint, both videos and the Lab on the presentation computer. Videos embedded in a PowerPoint play in PowerPoint for Windows and Mac. They do not play in the PDF, and may not play in Google Slides or Keynote: if the venue uses one of those, use the loose MP4 files in [`media/`](media/) or run the Lab live.
