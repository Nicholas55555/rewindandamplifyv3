# A small chipmaking toy, on IBM hardware

Added on 13 November 2026, the day before the finals. One IBM Marrakesh job, with its answers predicted and committed before it was submitted. Everything here re-runs offline from saved files.

**Read this first.** This is a toy with four qubits. Bayes' rule answers it by hand, so nothing here is a speedup, and nothing here is a real scanner, resist, mask or wafer. It exists because the repository's full-size chipmaking question ([`finals-lithography/`](../../finals-lithography/), 49 cells) needs 389 qubits and, as built, up to about 3.4 million two-qubit gates per round. No device today can run that. This is the same kind of question at a size that fits, asked with the same four moves as the main project, to see what today's hardware does with it.

It is not in the talk or the deck.

## The model

One contact, exposed once. Four qubits in a line.

| Part | What it does |
|---|---|
| **Source** (hidden) | The dose is low with probability 0.2. Nothing downstream shows it directly. |
| **Cell** | The contact's cell comes out dark with probability 0.1 at normal dose and 0.5 at low dose. |
| **Failure flag** | A dark cell fails to print with probability 0.2. This is the rare event: **3.6% of exposures**. |
| **Neighbour** | The next cell is exposed by the same source, with the same probabilities. |

Two questions about the rare failures, both answered by hand:

| Question | After a failure | Without knowing of the failure |
|---|---:|---:|
| **The cause.** Was the dose low? | 55.6% (five ninths) | 20% |
| **What follows.** Is the neighbouring cell dark? | 32.2% | 18% |

A second model, "clean", gives every cell the same 18% chance of being dark with nothing shared behind them. There a failure says nothing about the neighbour: 18%. So failures that come with dark neighbours point at the source.

## The four moves, on this model

| Move | Here |
|---|---|
| **Purify** | Nothing is measured until the end, so one exposure is one reversible circuit. |
| **Steer** | For the amplified step a dark cell fails with certainty instead of with probability 0.2. Every failing history is multiplied by the same factor, so the answers about failures do not change. The event goes from 3.6% to 18% of shots. |
| **Amplify** | One round, built by the main project's own function. On a perfect device 18% becomes 93.6%. |
| **Verify** | The failure flag is measured and shots without it are dropped. A failed contact must be a dark cell, so the cell bit is a second check that needs no knowledge of the right answer. |

Three builds of each model ran: **plain** (the model as it is), **steered** (no amplification) and **rewound** (steered, then one round). On a perfect device all three give the hand answers exactly; the tests check that.

## What IBM Marrakesh returned

Job `dbrl5iujjaos73aj81r0`, 13 November 2026: 8 science and 4 calibration circuits, 8,192 shots each, 28 seconds of processor time, on qubits 35, 34, 33 and 39. Raw counts, no correction. 95% intervals in brackets. "Predicted" is the noise model's answer, written before the job.

**The rare event, and the check on it.** The check: among flagged shots the cell must read dark. On a perfect device that is 100%.

| Build | Two-qubit gates | Flagged shots: perfect device | Predicted | IBM | Check passes: predicted | IBM |
|---|---:|---:|---:|---:|---:|---:|
| Plain | 6 | 3.6% | 4.3% | 5.9% [5.4, 6.4], 481 shots | 88.2% | **74.4%** [70.3, 78.1] |
| Steered | 5 | 18.0% | 18.6% | 21.0% [20.2, 21.9], 1,722 shots | 96.4% | 91.8% [90.4, 93.0] |
| Rewound | 15 | 93.6% | 88.7% | 87.9% [87.1, 88.5], 7,197 shots | 96.6% | **96.4%** [96.0, 96.8] |

Plain sampling flagged a failure in 5.9% of shots where the model's rate is 3.6%, and a quarter of those flagged shots fail the check: the device's false flags are not much rarer than the real event. After rewinding, the flag is on seven shots in eight and 96% of them pass.

**The cause: was the dose low?** By hand: 55.6% after a failure, 20% beforehand.

| Build | Predicted | IBM | Records |
|---|---:|---:|---:|
| Plain | 48.6% | 37.6% [33.4, 42.0] | 481 |
| Steered | 52.4% | 45.9% [43.5, 48.2] | 1,722 |
| Rewound | 52.8% | **50.6%** [49.5, 51.8] | 7,197 |

Every record says the dose was low more often than the 20% prior, and none reaches 55.6%. Plain sampling comes out about halfway back to the prior. The rewound record is five points short.

**What follows: is the neighbouring cell dark?**

| | Shared source | Nothing shared | Difference, in points | Predicted difference |
|---|---:|---:|---:|---:|
| By hand | 32.2% | 18.0% | +14.2 | |
| Plain | 27.0% [23.3, 31.2] | 16.8% [13.7, 20.5] | +10.2 [4.9, 15.4] | +11.8 |
| Steered | 28.2% [26.1, 30.3] | 16.1% [14.4, 18.0] | +12.1 [9.3, 14.9] | +13.6 |
| Rewound | 30.2% [29.2, 31.3] | 16.2% [15.4, 17.0] | **+14.0** [12.7, 15.4] | +13.8 |

The rewound difference is the hand answer to within its interval. Each of its two levels reads about two points low, so it is the difference that survives, not the levels.

## What was predicted, and how it did

[`predictions.json`](predictions.json) holds four statements in words and twelve numbers, tied by hash to the frozen circuits in [`hardware_bundle/`](hardware_bundle/).

**All four statements held**, each with its 95% interval wholly on the stated side:

1. After a failure the dose reads low more often than its 20% prior, in all three records.
2. After a failure the neighbour reads dark more often with the shared source than without it, in all three records.
3. The rewound circuit flags a failure in more than half of its shots, the plain circuit in fewer than one in ten.
4. The failed contact's own cell reads dark more often in the rewound record than in the plain one.

**Only four of the twelve predicted numbers are inside the measured intervals:** the three neighbour differences and the rewound check. The other eight all miss on the same side: the device was noisier than the model said, most of all for the plain and steered circuits. The model expected 88% of plain flagged shots to pass the check; 74% did.

Read this with three cautions.

- The prediction assumed the qubits and calibration that the 12 November job met (qubits 18, 31, 32, 33). On the day the campaign tool chose qubits 35, 34, 33 and 39.
- Run again afterwards with the job's own qubits, calibration and echo circuits, the same model puts eight of the twelve inside, some only just. It now explains the plain record (5.7% flagged against 5.9% measured; 70.6% passing the check against 74.4%). It is still too hopeful about the cause in the rewound record, 54.0% against 50.6%. A model with only gate and readout errors does not capture everything.
- The prediction was committed at 18:10:46 UTC (commit `4e000f4`) and the job was submitted at 18:11:23 UTC, in one working session. It was not published anywhere first. This is our own record, not an independent preregistration.

## Looked at afterwards: the check as a filter

This was not predicted. The check turned out to matter, so we asked what happens if it is used to filter: keep a shot only if the flag is set **and** the cell reads dark.

| Build | Records kept, of 8,192 | Dose was low | Neighbour: shared source minus none |
|---|---:|---:|---:|
| Plain | 358 | 46.6% [41.5, 51.8] | +17.7 [11.4, 23.7] |
| Steered | 1,581 | 48.4% [45.9, 50.9] | +12.6 [9.6, 15.5] |
| Rewound | 6,939 | 51.2% [50.0, 52.3] | +14.3 [12.9, 15.6] |

With the filter, plain sampling's answer about the cause rises from 37.6% to 46.6% and can no longer be told apart from the rewound one. So in this toy most of plain sampling's bias is false flags, and a check the model already provides removes most of it. What rewinding still adds is records: 6,939 usable shots against 358 from the same 8,192, nineteen times as many, and an interval about four times tighter.

## What this shows, and what it does not

- **It shows** the main project's four moves working on a second, differently shaped model on real hardware: a 3.6% event became the outcome of 88% of shots, and the records gave the neighbour difference at full size and the cause five points short.
- **It does not show a speedup.** The model has four qubits and is solved by hand. Nothing at this size can be faster on a quantum computer.
- **It does not show that plain sampling fails.** With the model's own check as a filter, plain sampling gets nearly the same answers here, from fewer records.
- **It is not lithography.** The cells are dark or bright. There are no photon counts, no blur, no resist chemistry, no mask and no wafer, and nothing here describes a real scanner.
- **Rewinding runs a model** inside a quantum computer. It cannot rewind a real exposure.
- **The distance to a useful size is very large.** A model worth asking this way is one too large to compute classically. The 49-cell circuit in this repository needs 389 qubits and, as built, up to about 3.4 million two-qubit gates per round. This job's largest toy circuit has 15, and at 15 the device already cost five points on one answer. Closing that gap needs many qubits with far lower error rates, in practice error-corrected ones. That hardware does not exist today, and "could work on such hardware" is not "works now".
- One job on one device. The intervals are shot noise only and leave out drift and calibration.

## How the job was run

```bash
python applied/contact/exposure.py --freeze
python applied/contact/forecast.py
python hardware_campaign/campaign.py prepare --bundle applied/contact/hardware_bundle --label contact_v1 --shots 8192 --cap 60
python applied/run_on_ibm.py submit --label contact_v1
python applied/run_on_ibm.py fetch --label contact_v1
python applied/contact/analysis.py
```

`prepare`, `submit` and `fetch` read or spend an IBM account's monthly time, so they are the account owner's decision. They are a record of what was done, not a step in reproducing the results. The first two commands refuse to run again: the bundle and the prediction are written once. [`exposure.py`](exposure.py) is recorded by hash in the bundle, so it is not edited after the job. Everything saved for the job is in [`../../hardware_campaign/runs/contact_v1/`](../../hardware_campaign/runs/contact_v1/).

## Reproduce

```bash
python applied/contact/exposure.py           # the hand answers and each circuit on a perfect device
python applied/contact/analysis.py --check   # the model, the recount and the noise model against results.json
python applied/contact/forecast.py --check   # the prediction against its saved compiled circuits
python -m unittest discover -s applied/contact -p "test_*.py"
```

23 tests, with no IBM account and no network. Among them: every circuit gives the hand answers on a perfect device; steering and rewinding leave the whole distribution of failing histories unchanged; the counts belong to the frozen plan; every stated direction held; most predicted sizes missed, always on the noisy side; and the filter result that cuts against the method is pinned.
