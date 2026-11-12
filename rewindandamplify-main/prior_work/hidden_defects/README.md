> **This folder is the earlier half of the project, kept for the record.** It is the hidden-defect work from 31 Oct to 3 Nov, unchanged except that the large per-fit result files and the team pack are left out. Its scripts import older code (v5) that is not in this repository, so they will not run here, and some links below point to files that were not copied. The Grover fusion in the root of this repository is self-contained and needs none of it.

# Finding a quantum chip's hidden defects from its clicks

**FGCU Quantum Hackathon (IBM Qiskit Fall Fest), 30 Oct to about 6 Nov 2026.**

**The idea.** A quantum recurrent state machine (QRSM) learns a quantum device's hidden defect from the clicks of one qubit's readout. It is built and run as a Qiskit dynamic circuit, then compared head to head with two black-box learners: a free-unitary quantum model and a tuned LSTM.

**For the team:** [START_HERE.md](START_HERE.md). The `team/` folder has the same deck as an editable PowerPoint and as a PDF, a team guide (a checklist, who presents what, likely judges' questions, and a glossary), and every chart as a picture.

## What we found (1 November 2026)

![Experiment 2](results/2_who_finds/2_who_finds.png)

*Top: the perfect simulator. Left: how much of a memoryless guess's prediction error each learner leaves on 4,096 new records; below the dotted line counts as found. Middle: the same against the number of training records. Right: how many defects each learner's fits say there are. Bottom: the noisy IBM device simulator. Left: held-out loss above the best learner. Middle: how far the defect's numbers land from the truth, in standard deviations. Right: the device's noise as read from the clicks.*

**In short.**
- **The circuit is exactly the model.** In Qiskit, the step's matrices equal v5's exact model's (difference 0.0). The perfect simulator's clicks pass every test against v5's exact filter: the click rate per step, the gaps between clicks, and the likelihood at the truth.
- **Only the physics-shaped QRSM finds the hidden defect.**

  | learner | numbers | prediction error left (perfect / good detector) | finds the defect's numbers? |
  |---|---|---|---|
  | physics-shaped QRSM | 3 | 0.00% / 0.10% | yes, every number within 1.6 standard deviations |
  | free-unitary QRSM (contains the truth) | 128 | 53% / 40% (best of 6 runs each) | no: 0 of 12 runs found |
  | LSTM, tuned | 1,297-67,713 | 17% / 17% | no, and it has no physical numbers to read |

- **Structure is data efficiency.** With 256 training records the physics model predicts as well as the best LSTM does with 4,096. With 1,024 it is already found (0.65% left), while the LSTM leaves 32%.
- **On the noisy IBM device simulator, a slightly wrong model invents defects.**
  - **The physics shape alone counts wrong.** It sees 1 defect on the device with none, and 2 on the device with 1, and its drive comes out 12.7 standard deviations off.
  - **The device's noise is the cause.** The hidden qubits relax and dephase while the light is read out (about 2.5% per step here), and the gates add errors.
  - **Adding that noise to the model, as one or two numbers per qubit, fixes both:**

  | model on the noisy device | count, no-defect device | count, 1-defect device | defect's numbers, in standard deviations |
  |---|---|---|---|
  | physics shape only | 1 (wrong) | 2 (wrong) | +12.7, -3.9, -4.6 |
  | + relaxation and dephasing per qubit | 0 | 1 | +6.9, -3.5, -0.1 |
  | + a depolarizing chance per qubit and a fitted dark-count rate | 0 | 1 | +1.3, -0.4, -0.9 |

  - **The last model also predicts new device clicks best,** ahead of the LSTM (by 140 nats over 4,096 records) and the free unitary. The LSTM in turn beats the physics shape alone: a flexible black box beats a wrong physics model, and the right physics beats both.
- **ML lessons:**
  - **Inductive bias decides what is learnable.** The black box that contains the truth is never found, while the physics shape is found every time.
  - **Model selection is only as good as the model class.** Leaving the noise out made the count wrong.
  - **The fix was a few physical numbers, not a bigger black box.** In v5, a free channel of 64-512 numbers overfit.

**Against the expectations logged before the runs** ([results/design_log.md](results/design_log.md)):
- held: the physics search on ideal data, the free unitary's failure, the counting with decoherence, and every prediction about the gate-error model;
- wrong:
  - the LSTM, expected to leave 1-10%, left 17%;
  - at 256 records the physics fit was not found;
  - with decoherence alone the drive stayed biased;
  - the physics shape alone overcounted on both device datasets, the less likely branch each time.

**Caveats:**
- **The gate-error model was added after the first device results,** and was tested on the same device records. Fresh records, or real hardware, are the honest test.
- **The clicks don't pin how the device's noise splits** into relaxation, dephasing and gate errors. They pin the defect's coupling and detuning once that noise is in the model.
- **Coverage is thin:** one device snapshot (FakeMarrakesh), one dataset per case, and one LSTM seed per setting.
- **It is a simulation.** The hardware run is ready, but has not run yet.
- **The exact filter's cost grows 4 times with each hidden qubit,** so this approach handles a few defects, not many.

Full tables: [results/1_qrsm_circuit/checks.log](results/1_qrsm_circuit/checks.log) and [results/2_who_finds/summary.md](results/2_who_finds/summary.md).

## The question

Superconducting qubits are limited by microscopic two-level defects in their materials (for a review: Müller, Cole & Lisenfeld, Rep. Prog. Phys. 2019, cited from memory).
- A defect trades energy with a nearby qubit, but nobody can put a probe on it.
- What a lab does get is a qubit's readout record: click or no click, step after step.

So the question is: **can a learner tell that a defect is there, and measure it, from those clicks alone?** In machine-learning terms, this is system identification. A hidden state machine is learned from a binary time series, and its physical numbers are read off the fit.

## The system and the circuit

v5 experiment 4's system, built in Qiskit ([experiments/1_qrsm_circuit.py](experiments/1_qrsm_circuit.py)). There are three qubits:
- **the emitter,** which is driven and is never measured;
- **the defect,** hidden behind the emitter and never measured;
- **the light,** which is measured mid-circuit every step and then reset. Its bit is the click.

Each step:

| gate | what it does | true value |
|---|---|---|
| RY(theta) on the emitter | the drive | theta = 0.6 |
| RZ(zeta) on the defect | the defect's own rhythm (detuning) | zeta = 0.3 |
| a real Givens rotation between emitter and defect (CX, CRY(2 phi), CX) | they swap energy | phi = 0.45 |
| CRY(2 alpha), then CX, from the emitter into the light | emission, with sin(alpha)^2 = gamma | gamma = 0.2 |
| measure the light, then reset it | the click | |

```
         ┌─────────┐     ┌─────────┐                              ┌───┐
emitter: ┤ Ry(0.6) ├──■──┤ Ry(0.9) ├──■────────■──────────────────┤ X ├ ...
         ├─────────┤┌─┴─┐└────┬────┘┌─┴─┐      │       ┌─────────┐└─┬─┘
 defect: ┤ Rz(0.3) ├┤ X ├─────■─────┤ X ├──────┼───────┤ Rz(0.3) ├──┼── ...
         └─────────┘└───┘           └───┘┌─────┴──────┐└─────────┘  │      ┌─┐
  light: ────────────────────────────────┤ Ry(0.9273) ├─────────────■──────┤M├─|0>─ ...
                                         └────────────┘                    └╥┘
click: 64/══════════════════════════════════════════════════════════════════╩═══════
```

(The drawing shows one step and the start of the next; the full drawing is in [results/1_qrsm_circuit/circuit.txt](results/1_qrsm_circuit/circuit.txt).)

**Why this is a QRSM.** It is a recurrent model whose hidden state is quantum (the emitter and the defect), and whose output each step is one measured bit. To score a model, its exact Bayesian filter runs on density matrices. That is the quantum version of a hidden Markov model's forward pass, and it gives the likelihood of every click record.

## Ground rules

- **The earlier folders stay untouched.** v1-v6 are only read: Python runs with `-B`, and v5's code is imported by path.
- **Two environments, passing data as files.** Circuits run in v6's Qiskit environment (qiskit 2.6.1, qiskit-aer 0.18.2, qiskit-ibm-runtime 0.51.0; nothing was installed into it). Fitting runs in v1's environment, which has torch. The click records pass between them as `.npz` files.
- **Laptop limits:** at most two heavy jobs at once, single-threaded workers, and runs timed before anything over 30 minutes is started (after asking the user).
- **Expectations first:** they are logged in [results/design_log.md](results/design_log.md) before each run.
- **Fair comparisons:** classical baselines are tuned, and literature is marked "cited from memory" where it wasn't checked.
- **Hardware runs only on the user's own IBM Quantum account.** The user creates the account and keeps the key; it is never typed, read or handled here.

## Setup and how to run

From this folder, in PowerShell:

```powershell
$qiskit = "..\Quantum research v6\.venv-qiskit\Scripts\python.exe"
$torch  = "..\Quantum research\.venv\Scripts\python.exe"

& $qiskit -B experiments\1_qrsm_circuit.py          # circuits and click records (about 30 s)
& $torch  -B checks\1_circuit_checks.py             # the circuit against v5's exact filter (about 40 s)
& $torch  -B experiments\2_who_finds.py --piece search noise learners --report   # the fits (about 1 h, 5 cores)
& $torch  -B experiments\4_deck_figures.py          # single-chart figures for the deck
```

Every script takes `--quick` for a smoke test. Long runs go through Bash with `>` so that logs stay UTF-8.

The team pack (`team/`) and the zip (`export/`) are built by the scripts in `tools/`; [START_HERE.md](START_HERE.md) has the commands.

**Real hardware** ([experiments/3_hardware.py](experiments/3_hardware.py)).
1. Save your IBM Quantum account once, in your own terminal. The key is typed at a hidden prompt, so it never appears on screen or in any file here:

   ```powershell
   & "..\Quantum research v6\.venv-qiskit\Scripts\python.exe" -c "import getpass; from qiskit_ibm_runtime import QiskitRuntimeService as S; S.save_account(channel='ibm_quantum_platform', token=getpass.getpass('API key: '), instance=input('Instance CRN: '), set_as_default=True)"
   ```
2. `& $qiskit -B experiments\3_hardware.py --plan`: picks a device and prints the chosen qubits and the estimated QPU time. It uses no QPU time.
3. `& $qiskit -B experiments\3_hardware.py --submit`, then `--fetch`. This writes `hardware-k1` and `hardware-k0` beside the simulators' records.
4. `& $torch -B experiments\2_who_finds.py --piece search noise learners --only hardware-k1 hardware-k0 --report`

## Folders

- `START_HERE.md`: a short map of the folder for the team.
- `team/`: the PowerPoint and its PDF, the team guide, and the charts as pictures (`figures/`).
- `experiments/`:
  - `1_qrsm_circuit.py`: the circuit, and click records from the simulators;
  - `2_who_finds.py`: the four learners;
  - `2_report.py`: their tables and figure;
  - `3_hardware.py`: IBM hardware;
  - `4_deck_figures.py`: charts for the deck.
- `checks/1_circuit_checks.py`: the circuit against v5's exact filter.
- `results/`:
  - `1_qrsm_circuit/`: the records (`data/`), the checks and their figure;
  - `2_who_finds/`: every fit (`parts/`), `summary.md`, `results.json` and the figure;
  - `3_hardware/`: the hardware job;
  - `deck/`: the charts, and the deck's slide files (`source/`);
  - `design_log.md`: the plan, expectations and changes, in time order.
- `tools/`: builds the team pack (`build_team_deck.ps1` and `build_team_guide.ps1`, from `deck_text.json` and `team_guide.html`) and the zip (`make_export.py`).
- `export/`: the whole project as one zip, with short paths so that it extracts on Windows.

## Prior work and AI help (disclosed, as the rules allow)

**Before the event** (October 2026: the user's folders v1-v6, built with AI assistance from Claude):
- the QRSM idea, and why generic training fails on it (v1);
- the physics-shaped model of a watched emitter with hidden defects, its exact filter, the search that finds it through poor detectors, the free-unitary comparison and the grey box (v5, experiments 4-5);
- the quantum-neuron control (v6, experiments 1 and 1b).

**New during the event** (this folder, also with AI assistance from Claude):
- the model as a Qiskit dynamic circuit, and its checks;
- click records from a perfect simulator and a noisy IBM device model, with the readout calibrated;
- the hardware pipeline;
- the noise-aware model, which reads a hidden qubit's decay from the clicks;
- the head-to-head comparison with the free-unitary model and a tuned LSTM on the same records;
- the write-up, the deck, and the team pack.

## Sources

Cited from memory, not checked during the event:
- J. Müller, J. H. Cole and J. Lisenfeld, "Towards understanding two-level-systems in amorphous solids: insights from quantum circuits", Rep. Prog. Phys. 82, 124501 (2019).
- H.-Y. Huang et al., "Quantum advantage in learning from experiments", Science 376, 1182 (2022).
- E. M. Izhikevich, "Resonate-and-fire neurons", Neural Networks 14, 883 (2001), for v6's control.
