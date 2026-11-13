# One question, three fields

Added in V3, two days before the finals. Two IBM Marrakesh runs: the saved counts of 11 November 2026, recounted, and a new job on 12 November whose answers were predicted before it ran. Everything here re-runs offline from saved files.

The three follow-up studies (photon sources, laser monitoring, chipmaking) each built a model of their own. That left a fair question: what do they have to do with **our** machine and **our** method? This study answers it by going the other way. It keeps the main project's machine, an emitter with one hidden defect, and asks it the question those three fields share:

> A rare event has just happened. Was it a one-off, or is something hidden remembering?

In the machine that is two readings taken right after a rare click (a click at step 3, which happens in 3.95% of runs):

| Reading | What is measured |
|---|---|
| **What follows** | the chance of another click in the next three steps |
| **The cause** | where the hidden defect was at the moment of the click |

Each field reads the same record in its own words.

| Field | How it reads the record | The exact answer |
|---|---|---|
| **Chipmaking** | A two-photon resist prints on *pairs* of photons. From one emitter, the pair dose is P(first photon) × P(a second soon after). | A second photon follows **8.50%** of the time with the hidden defect and **17.37%** without. Pairs arrive once in 298 runs instead of once in 57: **5.2 times rarer**. |
| **Laser monitoring** | The hidden defect has a frequency. Step it (0.3 to 0.6 radians per step) and the after-click record moves. | A second click follows **8.50%** of the time before the step and **14.22%** after it. |
| **Photon sources** | The after-click rate divided by the plain click rate is g⁽²⁾, the correlation every photon lab measures. | Right after a click, g⁽²⁾ = **0.24** with the defect and **0.13** without. Three steps on: 0.58 and 0.70. |

And the cause, which all three want: after a click the hidden defect holds the energy **8.46%** of the time, against **29.27%** at a typical moment. A click says the defect was probably empty.

## Why the rare event is the problem

All of these answers are conditional on a click that happens once in 25 runs. Sampling the model the plain way throws 24 runs in 25 away. Rewind and amplify makes that click the outcome of 96% of runs on a perfect device, and the answers survive: the rewound circuits give 8.49% where the truth is 8.50%.

On a real device there is a second, sharper reason. The true click rate is 3.95%, and the device adds false clicks at about the same rate or more: it reported the click in 7.6% to 9.8% of plain shots. So half or more of the "rare events" that plain sampling keeps are not events at all. The model gives a direct check: emission empties the emitter, so after a real click the emitter is never excited. IBM found it excited after 27% of plain clicks, in both runs.

## What IBM Marrakesh returned

Raw counts, no correction, nothing pooled between runs. 8,192 shots per circuit unless stated. 95% intervals in brackets.

**Chipmaking reading: a second click within three steps of the first.**

| | With the hidden defect | With nothing hidden | Nothing hidden minus defect |
|---|---:|---:|---:|
| Exact | 8.50% | 17.37% | **+8.9 points** |
| Plain sampling, 11 Nov | 38.6% [34.9, 42.5] | 25.7% [23.2, 28.5] | **−12.9** [−17.6, −8.2] |
| Plain sampling, 12 Nov | 47.3% [43.8, 50.7] | 34.2% [31.6, 36.8] | **−13.1** [−17.4, −8.8] |
| Rewound, 11 Nov | 19.9% [18.9, 20.9] | 22.9% [21.9, 23.9] | **+3.0** [+1.6, +4.4] |
| Rewound, 12 Nov | 16.8% [15.9, 17.8] | 21.0% [20.1, 22.0] | **+4.2** [+2.8, +5.6] |

Plain sampling gets the order **backwards** in both runs: it says the hidden defect makes pairs more likely. Rewinding gets the order right in both runs, with a third to a half of the true gap. Records of the rare click behind those rows: 619 and 806 plain, 6,118 and 5,894 rewound (with the defect).

A caution about the comparison. The machine with the defect has one more qubit and is the deeper circuit: 98 two-qubit gates against 32 when rewound, and 70 to 88 against 15 when sampled plainly. Its click is also the rarer one, 3.95% against 10.10%. Both push its answer up more than the other machine's, in both arms. Plain sampling does not survive that. Rewinding gets the order right in spite of it.

**Laser reading: the same number, before and after a frequency step.** First run on hardware, 12 November.

| | Before the step | After the step | After minus before |
|---|---:|---:|---:|
| Exact | 8.50% | 14.22% | **+5.8 points** |
| Plain sampling | 47.3% [43.8, 50.7] | 45.0% [41.5, 48.5] | −2.3 [−7.2, +2.6] |
| Rewound | 16.8% [15.9, 17.8] | 21.0% [20.0, 22.1] | **+4.2** [+2.8, +5.6] |

Rewinding sees the step, at about three quarters of its true size. Plain sampling cannot tell it from nothing.

**The cause: how often the defect holds the energy after a click.** Exact: 8.46% after a click, 29.27% at a typical moment.

| | 11 Nov | 12 Nov | Emitter still excited (must be zero) |
|---|---:|---:|---:|
| Plain sampling | 24.6% [18.2, 32.5], from 138 clicks in 2,048 shots | 24.7% [21.5, 28.2], from 644 clicks | 27.5%, 26.7% |
| Steered only | 18.3% [15.1, 21.9] | 21.8% [20.1, 23.7] | 5.9%, 6.4% |
| Rewound | 15.9% [15.0, 16.8], from 6,300 clicks | 17.2% [16.3, 18.2], from 6,090 clicks | 3.9%, 9.0% |

The rewound answer sits between the truth and the typical value in both runs. The plain answer stays close to "a typical moment".

**Photon reading: g⁽²⁾ at one, two and three steps after a click.**

| | +1 step | +2 steps | +3 steps |
|---|---:|---:|---:|
| Exact, defect / nothing hidden | 0.24 / 0.13 | 0.56 / 0.39 | 0.58 / 0.70 |
| 11 Nov, defect | 0.44 [0.39, 0.50] | 0.77 [0.70, 0.85] | 0.57 [0.52, 0.63] |
| 11 Nov, nothing hidden | 0.35 [0.31, 0.39] | 0.52 [0.48, 0.58] | 0.75 [0.69, 0.81] |
| 12 Nov, defect | 0.54 [0.47, 0.61] | 0.47 [0.42, 0.52] | 0.69 [0.62, 0.78] |
| 12 Nov, nothing hidden | 0.32 [0.28, 0.36] | 0.46 [0.41, 0.51] | 0.71 [0.66, 0.78] |

What held in both runs: g⁽²⁾ is below 1 at every step, so a second photon is always less likely than usual (the emitter is a single emitter), and right after a click the machine with the defect reads higher than the one without, as it should. The values there are about twice too high. **What did not hold:** three steps on, the first run told the two machines apart and matched the exact values; the second run did not tell them apart. g⁽²⁾ divides a number from one circuit by a number from another, which makes it the most fragile reading here.

## Is the bias the device's noise?

[`../hardware_campaign/noise_model/`](../hardware_campaign/noise_model/) fitted one noise scale to two echo circuits from 11 November. It was never shown the answers below, which are from the same day.

| A second click follows | Noise model | IBM measured, 11 Nov |
|---|---:|---:|
| Defect, plain | 35.6% | 38.6% |
| Defect, rewound | 21.1% | 19.9% |
| Nothing hidden, plain | 24.1% | 25.7% |
| Nothing hidden, rewound | 22.4% | 22.9% |
| Defect holds the energy, rewound | 16.3% | 15.9% |
| Emitter still excited, rewound | 3.9% | 3.9% |

The device's reported gate and readout errors, with that one scale, give every one of these to within three points, including the backwards order of plain sampling. So the bias is the hardware's error rate, and it shrinks as the error rate does.

## Predicted, then measured

That model was then used to predict a job that had not run. [`hardware_bundle/`](hardware_bundle/) froze 13 circuits and their exact answers: the three machines, plain and rewound, and two echoes. [`predictions.json`](predictions.json) is what the model said IBM would return, tied by hash to the bundle and to the compiled circuits in `predictions_isa.qpy`. The job ran on 12 November 2026 as `dbr51dhabdes73fpaum0`: 13 science and 4 calibration circuits, 8,192 shots each, 39 seconds of processor time.

| | Exact | Predicted | Measured | Prediction inside the interval? |
|---|---:|---:|---:|---|
| Chipmaking, rewound: nothing hidden minus defect | +8.9 | +1.3 | **+4.2** [+2.8, +5.6] | no: right direction, too cautious |
| Chipmaking, plain sampling | +8.9 | −8.3 | **−13.1** [−17.4, −8.8] | no: backwards as predicted, and worse |
| Frequency step, rewound: after minus before | +5.8 | +3.7 | **+4.2** [+2.8, +5.6] | yes |
| Frequency step, plain sampling | +5.7 | +1.3 | −2.3 [−7.2, +2.6] | yes |
| Defect holds the energy after a click, rewound | 8.5% | 16.3% | **17.2%** [16.3, 18.2] | yes |

Differences are in percentage points. **Every predicted direction held**, including the uncomfortable one, and three of the five predicted sizes are inside the measured intervals.

Read this with three cautions.

- The predictions assumed the qubits and calibration of 11 November (qubits 112 to 127). On the day, the campaign tool chose qubits 18 to 55.
- The model was too hopeful about the device. It predicted the rare click in 78.4% of rewound shots; IBM returned 74.3%. Re-running the same model afterwards with the job's own qubits, calibration and echo circuits gives almost the same scale (1.544 against 1.542) and does not close that gap: it says +1.8, −15.8, +4.0 and +1.1 points for the four differences. A model with only gate and readout errors does not capture everything about those qubits.
- The predictions were written at 23:38 UTC and the job was submitted at 23:50 UTC, in one working session. They were not published anywhere first. This is our own record, not an independent preregistration.

## How the job was run

```bash
python hardware_campaign/campaign.py prepare --bundle applied/hardware_bundle --label applied_v1 --shots 8192 --cap 90
python applied/run_on_ibm.py submit --label applied_v1
python applied/run_on_ibm.py fetch --label applied_v1
python applied/study.py
```

These spend an IBM account's monthly time, so they are the account owner's decision. They are a record of what was done, not a step in reproducing the results. `prepare` only reads the device and the remaining quota. [`run_on_ibm.py`](run_on_ibm.py) exists because the campaign tool asks IBM for the status of every earlier job before it submits, and the account used on 12 November cannot see the 11 November jobs. The wrapper answers that one question from the saved counts and leaves the other safeguards as they are: the Open Plan check, the quota check, the 90-second cap and one submission per plan. Everything saved for the job is in [`../hardware_campaign/runs/applied_v1/`](../hardware_campaign/runs/applied_v1/).

## Reproduce

```bash
python applied/study.py --check        # the model, both recounts and the noise model against results.json
python applied/predict.py --check      # the predictions against the saved compiled circuits
python -m unittest discover -s applied -p "test_*.py"
```

27 tests, with no IBM account and no network. Among them: the main project's own numbers come back; the recount agrees count for count with the campaign's analysis; plain sampling's interval lies below zero and the rewound interval above it, in both runs; every predicted direction held; and the g⁽²⁾ reading that did not repeat is pinned as not repeating.

## Limits

- The machine is a toy with two memory qubits. An exact classical filter answers every question here, and is the reference all the circuits are checked against. No speedup is claimed.
- Rewinding runs a **model** inside a quantum computer. It cannot rewind a real laser, quantum dot or wafer. What it offers those fields is a way to ask a model about its rare events and their hidden causes.
- No photon, laser, resist or wafer was measured. IBM qubits played a programmed machine, and no unknown defect was diagnosed.
- "Pair dose" is our reading of a click record, not a resist model. The resist in the chipmaking study is an assumed one.
- The frequency step is a step in the hidden defect's detuning, a number in our machine. It is not the 0.5 Hz step of the laser study.
- A rewound run uses about three times the gates of a plain run. On IBM the answers keep their order and lose half or more of their gap.
- Two runs on one device are two runs. The intervals are shot noise only and leave out drift and calibration.
