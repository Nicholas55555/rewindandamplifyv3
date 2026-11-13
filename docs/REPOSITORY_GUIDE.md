# Repository guide

This guide maps the public continuation of [Rewind & Amplify](https://github.com/Nicholas55555/rewindandamplify). Start with the [homepage](../README.md) for the scientific question and selected results. Paths below are relative to the repository root unless stated otherwise.

## What V3 added

V3 keeps every V2 research directory byte for byte, because their results are pinned by hash, and adds a presentation layer beside them:

| Addition | Where | Checked by |
|---|---|---|
| The Lab: a live, exact simulation of the model in the browser | [`lab/`](../lab/), and the single file [`Rewind_Amplify_Lab.html`](../Rewind_Amplify_Lab.html) | `node --test lab/test_engine.cjs lab/test_data.cjs lab/test_research.cjs`, `python lab/build.py --check`, `python lab/make_data.py --check`, `python lab/make_reference.py --check` |
| A noise-model simulation of the circuits that ran on IBM | [`hardware_campaign/noise_model/`](../hardware_campaign/noise_model/) | its unit tests, and `python hardware_campaign/noise_model/run_study.py --check` |
| One-command reproduction of the headline numbers | [`reproduce.py`](../reproduce.py) | run it |
| One question, three fields: our own machine asked the follow-up studies' question on IBM, with one job predicted before it ran | [`applied/`](../applied/), and the job's files in [`hardware_campaign/runs/applied_v1/`](../hardware_campaign/runs/applied_v1/) | `python applied/study.py --check`, `python applied/predict.py --check`, its unit tests |
| The V3 deck, with embedded video | [`finals-deck/`](../finals-deck/) | `python check_finals.py --public` |
| Videos and screenshots | [`media/`](../media/) | `python lab/capture.py` regenerates the Lab ones |
| An evidence map for the headline numbers | [`docs/EVIDENCE.md`](EVIDENCE.md) | |

The V2 single-file demo is now called the research explorer: [`Rewind_Amplify_Research_Explorer.html`](../Rewind_Amplify_Research_Explorer.html), built from [`laser-diagnostics-app/`](../laser-diagnostics-app/). The V2 deck is kept in [`finals-deck/v2/`](../finals-deck/v2/). The sections below were written for V2 and still describe the research directories accurately.

## Choose a starting point

| Goal | Start here |
|---|---|
| Understand the original quantum project | [Original one-pager](../rewindandamplify-main/docs/ONE_PAGER.md), then [full report](../rewindandamplify-main/docs/REPORT.md) |
| Try the demonstration | Open [the Lab](../Rewind_Amplify_Lab.html) locally. For the follow-up studies, open [the single-file research explorer](../Rewind_Amplify_Research_Explorer.html), or keep [its editable app folder](../laser-diagnostics-app/index.html) together |
| Present the current work | [PPTX](../finals-deck/Rewind_Amplify_Finals_V3.pptx), [PDF](../finals-deck/Rewind_Amplify_Finals_V3.pdf), [timed guide](../finals-deck/Presenter_Guide_V3.md). The V2 deck: [PPTX](../finals-deck/v2/Rewind_Amplify_Finals_Visual.pptx), [guide](../finals-deck/v2/Visual_Presenter_Guide.md) |
| Check the actual IBM comparison | [Evidence note](../FINALS_EVIDENCE.md), [raw hardware directory](../rewindandamplify-main/results/hardware/), [reproduction receipt](../research-validation/hardware_verification.json) |
| Read the completed local research | [Research findings](../RESEARCH_RESULTS.md), then the relevant study README below |
| Explore the semiconductor connection | [Quantum-dot bridge](../quantum_dot_bridge/README.md): checked findings, explicit QRSM mapping and missing two-photon instrument, proposed source-qualification workflow, and external HOM reference |
| See what remains open | The final sections of [Research findings](../RESEARCH_RESULTS.md) and the [bounded-program completion audit](../research-validation/completion_audit.json) |

The V3 presentation contains **13 main slides and 28 backups**, all in one style, with a planned **9:25** main talk including a **70-second Lab demo**. The V2 presentation contained 13 main slides and 22 backups. This is a rehearsal plan, not measured delivery time. The PPTX has speaker notes and editable text/charts/tables. The PDF is a static image fallback without notes. Exported slides and package structure were checked; native PowerPoint playback still needs testing on the presentation machine.

## Current results versus historical snapshots

The directory layout preserves the development history:

- `rewindandamplify-main/` contains the original project. Its README/report describe their own snapshot and sometimes use a broader hardware headline than the closer pair featured in the current evidence note.
- `RESEARCH_RESULTS.md` summarizes the completed followups. Its delivery section was written before those findings were integrated into the current deck and app. The current presentation links above already include the new research.
- `quantum_dot_bridge/` is a later, separate exploration. Its results and per-study verification preserve the earlier 285-file research snapshot. The current deck and app now include the semiconductor connection. Its README distinguishes the illustrative calculation, imported experimental histograms and the subsequent bounded HOM reanalysis.
- The `followup/`, `drive_diagnostics_followup/`, `multibin_followup/`, `exposure_followup/`, `phase_inspection_followup/` and `full_spatial_circuit/` directories contain newer work. Earlier roadmaps may still describe these as proposed.
- `laser_sensor_viability/results.json` is the **earlier known-onset** batch experiment. `laser_sensor_viability/followup/main/results.json` is the **newer unknown-onset** experiment. Their tasks, calibration and headline rates differ. The app labels them separately.
- An `archive/`, `smoke/`, preliminary or failed-attempt record documents development. It is not automatically canonical evidence or an additional independent experiment. Each study README identifies its final outputs.

The full-grid circuit was constructed after earlier documents described it as missing. The actual 389-qubit QPY artifacts were read back and checked compositionally; the 389-qubit quantum state was **not** simulated. The compact construction has a separate serialization limitation. Use the [full construction README](../finals-lithography/full_spatial_circuit/README.md) for these distinctions.

## Three different uses of “quantum”

| Layer | What runs | Evidence boundary |
|---|---|---|
| Physical model | Quantum-state evolution and a measurement model | Numerical prediction under declared physics; fitting often runs classically |
| Quantum query | Coherent preparation, predicate, inverse and amplification | Ideal/noisy Qiskit simulation and selected archived IBM circuits |
| Optical sensing or illumination | Atoms, emitters or quantum light interacting with a signal/sample | Our device models are synthetic. The separately attributed GaAs HOM histograms are published external measurements; we collected no new optical data. |

A click is a recorded measurement outcome. A fitted hidden state is an estimate conditioned on a model and record; it is not direct access to an arbitrary unknown state. A larger accepted-event rate is useful only if the accepted distribution or state remains accurate. A sensing benefit does not establish a computing speedup, and a fine optical fringe does not establish printed resolution.

## Reproduce the original package

Create a virtual environment using your platform's normal Python tools. With Python 3.10 or later, from the repository root:

```bash
cd rewindandamplify-main
python -m pip install -e ".[test]"
python -m pytest
python demo/demo.py
```

This runs local software. The original `experiments/run_ibm.py` also contains an explicit submission route, but it is not required by these commands or by the current research. Never add account configuration or tokens to the repository.

The original [package README](../rewindandamplify-main/README.md) explains individual experiments. Avoid blindly rerunning every script: some write to canonical result locations, and hardware submission is a separate action. Use saved evidence first and fresh output paths where a runner supports them.

## Check the offline application

Open `Rewind_Amplify_Research_Explorer.html` in Chrome or Edge for the single-file edition, or open `laser-diagnostics-app/index.html` with its folder intact. No server or dependency installation is required for normal use. Both contain the same interactive results and videos; the single-file version downloads its embedded evidence when those links are selected. Rebuild it with `python laser-diagnostics-app/build_standalone.py`, then verify with `python laser-diagnostics-app/build_standalone.py --check`. From the root, the folder app's software checks are:

```bash
node --test laser-diagnostics-app/test_model.cjs
python laser-diagnostics-app/check_package.py
python check_finals.py --public
```

The import script packages existing research outputs; it does not conduct the experiments. Optional browser QA requires the dependencies documented in the [app README](../laser-diagnostics-app/README.md). The short MP4s are explanatory animations, not recordings of an optical laboratory or quantum processor.

`check_finals.py --public` uses standard Python to check the public presentation/evidence package, including the current manifest, notes and source hashes. The `--public` flag accounts for the intentionally omitted local rubric workbook. It is an integrity check, not a scientific test or a PowerPoint rehearsal.

To create a portable public bundle locally:

```bash
python build_finals_pack.py --public
```

The output is `Rewind_Amplify_v3_Public_Pack.zip`. The command creates a local archive; it does not upload or publish it. Use the public flag for this repository. Historical delivery archives from the private working directory are not the public distribution.

## Reproduce the research studies

The recorded followup environment used **Python 3.12.10**. In a separate environment, install:

```bash
python -m pip install -r research-validation/research_requirements.txt
```

For recorded bounded runs, set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` **before** starting Python. In PowerShell use `$env:OPENBLAS_NUM_THREADS='1'` and `$env:OMP_NUM_THREADS='1'`; in a POSIX shell use `export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`.

Run study suites in separate Python processes. Several folders intentionally use local names such as `model.py` and `test_model.py`; one repository-wide discovery process can mix unrelated modules.

| Study and documentation | Focused test command from the root |
|---|---|
| [Spatial process and classical comparison](../finals-lithography/followup/README.md) | `python -m unittest discover -s finals-lithography/followup -p "test_*.py" -v` |
| [Full-grid circuit construction](../finals-lithography/full_spatial_circuit/README.md) | `python -m unittest discover -s finals-lithography/full_spatial_circuit -p test_full_spatial.py -v` |
| [Unknown-onset frequency monitoring](../laser_sensor_viability/followup/README.md) | `python -m unittest discover -s laser_sensor_viability/followup -p test_followup.py -v` |
| [Changing-drive diagnosis](../qrsm_photon_poc/drive_diagnostics_followup/README.md) | `python -m unittest discover -s qrsm_photon_poc/drive_diagnostics_followup -p test_model.py -v` |
| [Numerical dynamics and joint inference](../qrsm_photon_poc/followup/README.md) | `python -m unittest discover -s qrsm_photon_poc/followup -p "test_*.py" -v` |
| [Three-bin coherent query](../qrsm_photon_poc/multibin_followup/README.md) | `python -m unittest discover -s qrsm_photon_poc/multibin_followup -p test_model.py -v` |
| [Quantum-light exposure](../quantum_lithography_poc/exposure_followup/README.md) | `python -m unittest discover -s quantum_lithography_poc/exposure_followup -p test_model.py -v` |
| [Optical phase inspection](../quantum_lithography_poc/phase_inspection_followup/README.md) | `python -m unittest discover -s quantum_lithography_poc/phase_inspection_followup -p test_phase_model.py -v` |

These eight suites passed **79 focused tests** in the recorded fresh-extraction check. That count describes the research delivery, not the original package or app suite. It checks defined numerical behavior; it is not physical-device validation. Full study regeneration can cost much more than these tests. Follow each study's README for its runner, resource guards, seeds, dependencies and output policy. Do not attempt a full statevector simulation of the 389-qubit construction.

## Reproduce the later quantum-dot work

The later semiconductor study has separate source/data hashes. Its illustrative coherence model, the unmodified external GaAs histograms and their conditional HOM reanalysis have distinct provenance:

```bash
python -m unittest discover -s quantum_dot_bridge -p "test_*.py" -v
python quantum_dot_bridge/verify_results.py
python -m unittest discover -s quantum_dot_bridge/reference_hom -p "test_*.py" -v
python quantum_dot_bridge/reference_hom/import_verify.py
python -m unittest discover -s quantum_dot_bridge/hom_analysis -p "test_*.py" -v
```

Use [the analysis README](../quantum_dot_bridge/hom_analysis/README.md) for a fresh-output reproduction and its read-only verifier. The full CI research group runs each suite in its own process through `.github/scripts/run_tests.py --group research`. It does not overwrite the frozen experiments or submit hardware jobs.

## How to read the evidence

Prefer the full chain: **question → protocol → model/code → saved records → result summary → verification**.

- Canonical JSON files contain numerical settings and results. NPZ files retain selected underlying records, distributions or matrices. QPY files contain serialized circuits.
- Hash manifests verify which source and data files a result used. Matching hashes establish integrity, not correctness of the physical assumptions.
- Independent numerical checks use separate implementations or review paths. They are not external peer review or independent laboratory replication.
- Statistical intervals have a defined scope. They do not automatically include model mismatch, calibration drift, optimizer uncertainty or all systematic errors.
- Some studies were deliberately bounded by time, memory and candidate-model choices. Unrun noise cases and ambiguous parameters are limitations, not implicit passes.
- The drive study's prior-only comparison was added after inspecting the holdout results. It is a **descriptive control**, explicitly separated from the original evaluation.

The [hardware evidence note](../FINALS_EVIDENCE.md) and [research report](../RESEARCH_RESULTS.md) are the main cross-study indexes. Study-specific READMEs contain exact provenance and explain superseded attempts. Historical local receipts can contain author-machine paths; use repository-relative paths and documented commands for reproduction.

## Scope of this public repository

The public project preserves code, authored documentation, results and the files needed to inspect or reproduce the declared studies. Local working material such as raw AI conversation exports, private judging CSVs, the supplied rubric workbook, third-party source PDFs/archives, the workspace audit, old local delivery archives, caches and credentials is not part of the public release. The authored rubric map remains available, but the supplied workbook is not redistributed. References should be followed through their original sources. Excluding local working material does not turn a hypothetical model into measured evidence.

To extend the work, keep old evidence intact, state the new question and comparator before evaluation, use separate calibration/training/test data, charge all relevant acquisition or circuit resources, and preserve negative results. The strongest next physical step is a calibrated optical measurement with synchronized conventional references and independent source-versus-detector interventions. More model families and stronger classical baselines remain worthwhile local research too.

## November 11 hardware and joint-photon continuation

[New IBM evidence](../hardware_campaign/README.md) and its [25-family ledger](../hardware_campaign/coverage.json) separate complete circuit runs, component emulation and physical/resource limits. [Joint-photon QRSM research](../quantum_dot_bridge/qrsm_hom_followup/README.md) includes explicit conditional instruments, fresh calibration/holdouts, strong classical controls and negative findings. Run `python hardware_campaign/verify_campaign.py` to check saved job provenance and counts offline. The expanded `.github/scripts/run_tests.py` exercises the new mathematics and mock submission safeguards without account access.
