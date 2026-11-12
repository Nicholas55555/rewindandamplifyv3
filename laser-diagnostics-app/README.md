# Rewind & Amplify: offline audience demo

**Portable v2 HTML:** the repository root contains `Rewind_Amplify_v2_Demo.html`. Copy that one file to another computer and open it in Chrome or Edge. It includes all chapters, the six current research views, both MP4s and byte-exact evidence downloads. Evidence links save files with their original names; external citations and IBM portal links still require internet. It uses the same frozen data and controls as this folder version.

Build it from the repository root with `python laser-diagnostics-app/build_standalone.py`. Verify the checked-in export with `python laser-diagnostics-app/build_standalone.py --check`. The accompanying `standalone_manifest.json` records every source hash and the generated HTML hash. Optional isolated Chrome QA: `python laser-diagnostics-app/check_standalone_browser.py --output .publication-audit/standalone-demo` (requires Playwright and installed Chrome).

Open **index.html** in Chrome or Edge. The app needs no installation, internet, account or running Python process. Keep the entire `laser-diagnostics-app` folder together. All JavaScript, evidence and animations are local. To present, select **Focus view**, maximize the browser and use its full-screen command. The regular layout also works on a narrow screen.

## A 45-second finals walkthrough: the original quantum project

This accompanies the revised 13-main-slide, 9:20 presentation. The app opens **Rewind the model** first. Use `index.html?focus=1#rewind` for the stage view and keep the separate two-bin extension collapsed. Only the quoted lines below are spoken; the remaining text gives operating instructions.

1. **0–8 s, name the QRSM's role.** “The QRSM updates a hidden-state estimate from the click history, then predicts the next observations.” Briefly point to **What the QRSM adds**. This is inference within candidate physical models, not direct access to an unknown quantum state.
2. **8–15 s, define the query.** “A click is a recorded one. Here we select only step three, leaving earlier bits free.” Point to `? ? 1 ? ? ?`. Each question mark allows 0 or 1; the condition does **not** require the earlier prefix 001.
3. **15–27 s, keep more useful histories.** Keep **Coupled hidden memory** selected and change **Plain sampling** to **Steering + full amplification**. “Steering and full amplification keep more useful runs while preserving the future pattern in this ideal test.” Acceptance changes from 3.95% to 96.49%. This is the combined design, not a gain attributed to Grover alone, and the app reads frozen verified results.
4. **27–38 s, compare hypotheses.** Toggle **Emitter only**, then back to **Coupled hidden memory**. “These programmed models predict different patterns: about ten percent versus five percent at step six.” The exact displayed values are 10.10% and 4.67%; these are known model alternatives, not an unknown physical defect discovered by the app.
5. **38–45 s, explain the requirement for useful inference.** “Testing defects requires many records and calibrated noise. More hits alone do not establish the right answer.” Point to the future-answer accuracy check, then return to the presentation. The exact classical sampler still wins at this small scale.

## What the QRSM contributes to defect analysis

For each candidate physical model, the QRSM carries a hidden quantum-state estimate between steps. Each observed bit conditions that estimate through the modeled measurement update, including measurement backaction. With imperfect readout, the update must allow for possible underlying outcomes instead of treating every recorded bit as infallible. The result is a probability distribution for later observations. Classical fitting can compare candidate interaction-and-noise models on many records and evaluate predictions on records not used for fitting.

Hidden interactions and detector/readout errors can both change measured statistics. Misattributing one to the other can bias the inferred state or coupling, so defect analysis needs independent calibration, suitable alternative models and controls. The proposed value here is the physical structure of the quantum-state model. Classical sequence models can also represent memory; quantum-state notation alone does not establish computational advantage.

Earlier parameter-fitting demonstrations used synthetic records. The current IBM circuits encode known, deliberately programmed models. A single click does not identify a defect, and the hidden-state estimate is not a direct state measurement or a nondestructive tomography result.

For a useful Q&A control, choose **Emitter only** and **Memory-only reflection control**. It accepts about 74.29% of ideal runs but predicts about 0.84% at step 6 instead of 10.10%. This demonstrates why an attractive hit rate alone does not establish a useful result. Reset to **Coupled hidden memory** and **Plain sampling** afterward. The local-reflection design shown separately has its own, smaller approximation error in this case.

## Current research: completed followups

The second chapter, **Current research**, is the current research entry point. Open `index.html?focus=1#research` for a focused Q&A view. The app still defaults to **Rewind the model** for the original 45-second demonstration. The updated deck has 13 main slides, 35 total slides and a 9:20 main talk.

Choose one of six study buttons. All selectors display exact saved outputs or unchanged external histogram counts; they do not rerun a sensor, fit a model, change a threshold or submit a quantum job.

- **Frequency monitoring:** a hidden-onset, causal task. Default nominal detection within 32 seconds is 51.35%, 58.02% and 97.97% for the receiver, receiver-plus-atom and two coherent references. Each bar also shows whole-128-second-record false alarms on a separate frequency-null population. Six conditions and both frozen fusion/agreement rules are available. The hypothetical 698 nm platform, substantial dead time and unmatched apparatus resources remain visible.
- **Drive amplitude:** all 13 frozen source/detector conditions. Source-case bars use eligible event records and display premature alarms and restricted delay; source-stable bars show false source alarms. The telegraph denominator excludes records without activation or sufficient follow-up and states their counts. The units are 96 arbitrary-time bins, not seconds. Three algorithms analyze the same bits; this is not a contest between three physical sensors.
- **The prior control stays visible:** every amplitude case compares observation-based RMSE, the same fitted prior without per-record bits, and the fitted constant baseline. On +20% steps the prior already gives 0.1136 versus 0.1125 with observations. The other four source-change cases worsen when the record is incorporated. This post-holdout descriptive check prevents the positive source prior from being mistaken for useful measurement information.
- **Phase inspection:** seven optical cases and two resource budgets. The view reports global full-2π error, within-π error, branch errors, photon dose and attempt time together. The hybrid's efficient-case RMSE is 0.00637 rad versus the specified coherent comparator's 0.00791 rad. Pure NOON's global ambiguity, loss sensitivity, charged pilots and nonzero upper branch-error bound remain visible. This is phase estimation, not object-defect classification.
- **Models & circuit cost:** a synthetic dead-time modeling example and the actual full-49-cell circuit construction. The latter uses 389 qubits and constructive generic CX upper bounds of 2,874,028–3,382,108 per complete round. The full state was not simulated; component/wiring/readback checks do not establish noisy execution or advantage.
- **Quantum dots:** a semiconductor-to-photon-quality bridge. The four frozen toy cases have the same imposed brightness and ideal `g⁽²⁾(0)=0`, but photon overlaps of 100%, 50%, 20% and 25%. A separate selector changes prescribed classical trap-pair correlations while preserving each photon's frequency marginal. Another shows the collection cost: pair yield is η², so moving from 80% to 20% per-photon survival costs 16 times as many attempts per expected surviving pair. These are known quantum-optics calculations with illustrative parameters, not a device fit.

The quantum-dot view separately displays six **published GaAs HOM histograms by Münzberg and colleagues (2022)**, CC BY 4.0, Zenodo 6337697. Choose excitation separations of 13.1, 26.2 or 39.4 ns, and the full or central display window. Every histogram retains all 5,000 original integer bins; only the horizontal display unit changes from ps to ns. The coincidence-time axis is distinct from excitation separation. Raw counts are not rates or exposure-normalized comparisons. The paper-reported 80.3%, 82.6% and 77.4% visibilities remain explicitly attributed published values, separate from the illustrative model.

Below the raw plots, **our side-peak-normalized reanalysis** displays corrected values of 80.24%, 82.58% and 77.24%. Its 95% intervals condition on independent Poisson counts and shared beamsplitter/multiphoton calibration; they exclude normalization, drift, polarization, routing and timing-response systematics. The separate min–max range across 70 protocol variants is sensitivity, not a confidence interval. A co-only estimate and cross-polarized central/reference ratio make the normalization concern visible. The analysis uses the same published observations and calibration, not an independent experimental replication or the authors' exact pipeline. It does not fit a microscopic defect or trap rate.

For a short quantum-dot Q&A: select **Phase noise**, point to unchanged brightness and `g⁽²⁾(0)` but 50% overlap; change trap probability from 0% to independent 50% and explain the unchanged marginal frequencies; then show the external histograms as the kind of measurement a physical model would need. A reduction in HOM interference does not uniquely diagnose a trap, laser fluctuation or semiconductor defect. The direct chip connection is semiconductor quantum-light-source and photonic-device characterization; DUV/EUV lithography compatibility is untested.

### The explicit connection to our original QRSM

The opening **What this adds to Rewind & Amplify** panel makes three lessons concrete. Equal brightness and `g⁽²⁾(0)` can hide 20–100% overlap in the toy model. Identical single-photon frequency marginals can hide different pair memory, changing overlap from 100% to 60%. In the external 39.4 ns data, changing normalization changes the corrected result from 77.24% to 79.38%, so the measurement model matters as well as the source model.

The original QRSM asks how an emitter and its hidden environment change future observations. A proposed semiconductor extension maps the **emitter** to one selected quantum-dot optical transition, **hidden memory** to candidate local environmental dynamics, and the **observed bit record** to an explicit model of the detectors and acquisition protocol. A purely classical trap can be represented by a hidden Markov model (HMM); quantum-state notation alone is not an advantage. HOM requires additional optical information to be acquired. The separate joint-photon extension now implements emitted mode preparation, a two-photon HOM observation instrument and conditional environmental updates. It is a full-emission surrogate with different physical assumptions from the original driven QRSM. No quantum-dot QRSM has been fitted to these histograms or validated on a physical device.

The practical target is a quality-check workflow for a semiconductor quantum-light source: vary bias or excitation in controlled trials; measure counts, multiphoton suppression `g⁽²⁾(0)`, HOM overlap and usable-pair yield; compare calibrated candidate-model predictions on unused records; then choose the next alignment/tuning control or deeper source investigation. This would guide engineering tests without claiming unique fault attribution. Applying such a sensor to a lithography laser remains a separate question of compatible wavelength, coupling and calibrated response.

**Judge explanation:** “Our original model asks how hidden device memory changes later observations. The dot work taught us which observations matter: equally bright single-photon sources can interfere very differently, and normalization can change the apparent diagnosis. We now implement the joint observation model, but passive data can reveal nothing and acquisition errors can imitate the controlled signal. A strong classical HMM stays competitive. The practical target is a calibrated quality check for semiconductor photon sources; a real device fit is still ahead.”

For a short Q&A sequence: show **Frequency monitoring → Reduced atomic coherence**, then **Drive amplitude → +20% field step** and its prior-only control. Finish with **Phase inspection → 1% preparation success** and compare equal photons with equal attempt clocks. These are distinct studies, not interchangeable headline percentages. The current integrated status index is copied to `evidence/RESEARCH_CURRENT.md`. `evidence/RESEARCH_RESULTS.md` preserves the earlier frozen research snapshot.

## Implemented joint-photon model and honest viability limits

The quantum-dot view now includes the actual forward observation model: emitted exponential wavepackets depend on a retained environment, a joint HOM instrument predicts bunching/coincidence, and each observed result conditions the environmental state. Exact complex mode overlaps and bosonic/CP-map checks support the digital circuit encoding. This is a new full-emission surrogate, not a microscopic device fit or simply a rotation chosen to return a desired final probability.

The frozen main study stays visible: passive measurements give identical laws for the chosen coherent/dephased hypotheses; the controlled 64-pair test flags 5.60% versus 4.50% of nominal classical records. The model is implemented, but that operating point is not useful discrimination.

A separate, explicitly exploratory 648-setting exact scan selected a new control. A prospective validation then used ideal resets between four-pair blocks. The budget selector exposes all six points: 64 through 7,644 attempted pairs per inference record. At 2,584 pairs nominal detection is 79.75% with 4.85% false flags. At 7,644 pairs, lower collection, mode mismatch and readout drift on still-classical sources cause 72.00%, 53.25% and 21.05% false flags. More data do not cure an incorrect observation model. Conditional Wilson intervals exclude physical-model and calibration-drift uncertainty.

The stronger 8-state HMM differs from the given-physics predictor by only −0.0000092 nats per pair; its paired 95% interval includes zero. The learned models share 20,000 training blocks, but the physical predictor knows source parameters. Every HMM start reaches its 200-iteration cap; global optimality is not claimed. The exact classical categorical oracle reproduces the finite-block law. No uniquely quantum-memory diagnosis or predictive advantage is established.

The app copies the complete new evidence tree under `evidence/joint-hom/`, keeping source, protocol, results, independent reviews and scientific README links intact. The current 14-circuit original instrument bundle and separate 4-pair selected-design bundle remain distinct. The latter uses 22/29-qubit circuits and only a declared flag/memory marginal reference, not a full 29-qubit reference. The browser displays frozen outputs only.

## Real IBM hardware: acceptance, answer error and resources

The sixth study, **IBM hardware**, reads the complete current `hardware_campaign/results.json`: 10 jobs, 207 science and 40 calibration circuit executions, 688,640 shots and 244 charged QPU seconds. This is actual QPU usage, not elapsed wall time or a price. The hardware is IBM Marrakesh; these superconducting circuits digitally emulate optical and other models. They do not measure an optical source, a semiconductor dot, a lithography laser, a resist or a wafer.

The original-query hero reports the fresh 8,192-shot precision follow-up separately from earlier runs. It reuses each circuit’s prior compiled form and mapping; the local/full circuits have different widths and routing. Steered local reflection accepts 6,300/8,192 trials (76.90%) using 58 native two-qubit gates; full reflection accepts 5,674/8,192 (69.26%) using 125. Conditional-history TV errors remain 0.1177 and 0.1814. The local-minus-full acceptance difference is 7.64 percentage points, with a conditional independent-shot 95% interval [6.29,8.99]. Those errors and costs remain beside acceptance; the app never calls acceptance alone a correct answer or advantage.

Seven component families can be inspected, including all dot histories, compiled gate counts and conditional-memory measurements in the declared basis. The deep all-click two-bin example accepts 8/512 trials, near its ideal event rate, but has selected-data TV 0.7604. Zero-hit three-bin cases explicitly have no conditional estimate. TV includes shot noise and is not quantum-state fidelity. The four-pair dot reference covers only the declared marginal. Component circuits do not reproduce complete long-record optical classification or monitoring studies.

Every displayed job has an exact ID, verified IBM Workloads portal link and local raw-count/plan links. The portal requires the user's IBM access; the app performs no login or network request. All canonical analysis/raw/plan hashes are checked before copying. Raw measurements are the primary view; no independent-readout inversion is presented as corrected truth. The complete campaign report and coverage limitations are copied to `evidence/hardware/`.

## Earlier laser-sensing experiment

**Earlier sensor study** preserves the original known-onset batch experiment. Its detector is told that the event starts at 64 seconds; its detection rates must not be presented as unknown-onset monitoring performance. A visible link returns to the current frequency study. Move the frequency-offset slider to about +5 Hz to illustrate a phase-sensitive response with unchanged ideal power. The slider uses the labelled instantaneous-pulse Ramsey limit and does not rerun either benchmark. The saved traces and original percentages are unchanged.

A lithography engineer cares about stable illumination and repeatable exposure. This proposed diagnostic route would first need a physically compatible laboratory sensor and synchronized conventional references. The current 698 nm surrogate has not measured a lithography source, demonstrated a wafer-yield improvement or established financial savings.

## Video fallbacks

Open **Check the evidence** and scroll to the two visible video players. Each MP4 runs for 12 seconds and has native play, pause, seek and full-screen controls. Playback starts only when you choose it. The players use local PNG posters and do not autoplay.

- **Same power. Different frequency.** `assets/laser-diagnostic-lenses.mp4` illustrates the proposed sensing lens and atomic-reference drift using the labelled analytical Ramsey example. It contains no laboratory measurements.
- **Prepare, mark, rewind and amplify.** `assets/rewind-amplify.mp4` explains the **separate two-bin photon extension** using its saved ideal Qiskit probabilities. It is not a video of the original step-3 query or IBM hardware.

Each player also has **Open MP4**, **Download video** and **Still image** links. If the embedded player is unavailable in a viewer, open the MP4 directly in Chrome, Edge or a compatible local video player. The readable visual explanations below the players describe their content without animation. The authoring GIFs remain in the workspace's `animations/` directory for provenance; the app no longer relies on GIF playback.

The videos use H.264 in an MP4 container, with no audio. Their 1200 × 676 frames preserve the original 1200 × 675 scientific graphic and add one padding row for video encoding. `assets/video_manifest.json` records conversion metadata and source/output hashes.

## What is live and what is frozen?

- **Live analytical calculation:** the instantaneous-pulse Ramsey limit, with 20 ms dark time, selected coherence time, and asymmetric 2%/4% readout errors. The finite-pulse benchmark is more detailed. The slider does not claim to rerun its 4,000-record evaluations.
- **Live analytical calculation:** ideal full-amplitude-amplification probability, starting at the saved coarse model's exact event probability. Only one round has an independently saved Qiskit statevector result in this experiment. Higher rounds in the explorer are a formula, not additional Qiskit executions.
- **Frozen original QRSM query:** model toggles and the sampling-circuit selector read `research-validation/original_after_click_verification.json`. Its ideal Qiskit results were checked against exact filtering and its long-query IBM counts against archived records. Only step 3 is conditioned; later steps 4–6 remain outcomes. The long query kept 290 plain versus 3,354 amplified histories in the first archived coupled-model run. These are different circuits from the short-query 3,525-versus-3,215 comparison.
- **Frozen sensing evidence:** all scenario traces and performance estimates in `data.js` come directly from `laser_sensor_viability/results.json` and `example_traces.json`. The importer includes hashes and copies full evidence to `evidence/`. Charts do not substitute a random animation for data.
- **Frozen current research:** `research-data.js` contains exact JSON objects from fourteen selected canonical outputs: unknown-onset frequency, drive, prior-only estimation, phase, full spatial construction, the two paired dead-time fits, the quantum-dot benchmark, the external HOM provenance manifest, conditional histogram reanalysis, joint-photon main study, exact design exploration, fresh selected-design validation and current IBM campaign. `provenance` records canonical paths, copied evidence paths and SHA-256 hashes. Embedded histogram arrays preserve each of the six copied CSVs' 5,000 original time/count pairs. This is a separate bundle from the historical known-onset sensor data. Numerical results, study READMEs, external attribution and selected validation/review receipts are local in `evidence/`.
- **Archived QPU evidence:** 3,525/4,096 versus 3,215/4,096 raw event hits from the two steered, one-round IBM Kingston circuits. Different compiled circuits and placements prevent isolating a single cause. These are not optical-sensor measurements.

The sensing comparison controls acquisition duration and source realizations. Its photon allocations are **assumed bookkeeping**, not a validated equality of total physical resources. Atomic support optics, independent local oscillators and hardware cost are unmatched. A second independent conventional reference can outperform the atomic addition in this model. No practical quantum advantage, industrial compatibility or wafer outcome is established.

## Reproduce and verify

From the workspace root, using Python with the standard library, the completed research outputs, and the verified original after-click JSON:

```powershell
python laser-diagnostics-app/import_results.py
node --test laser-diagnostics-app/test_model.cjs
python laser-diagnostics-app/check_package.py
```

The import script does not run or tune the scientific models. It packages exact saved values deterministically. Sixteen tests check the analytical controls, original query/hardware separation, historical rates/traces, all fourteen current-source JSON copies and canonical hashes, unknown-onset denominators, the prior-only control, global phase ambiguity, complete circuit costs, the quantum-dot assumptions/pair costs, all 30,000 external histogram rows and the reanalysis's corrections/protocol ranges. Canonical-source checks run when the surrounding workspace is present; copied-evidence checks also work in the standalone app folder. `check_package.py` checks local dependencies, evidence hashes, external license/source identity, required review receipts, player controls, and actual MP4 container/AVC headers, dimensions, duration and frame count against the conversion manifest. It does not merely trust the filename extension. These are separate from visual and interaction checks.

Optional repeatable browser QA, when Python Playwright and Chrome are already installed:

```powershell
python laser-diagnostics-app/check_browser.py
```

This uses an isolated headless Chrome profile and the standalone `file://` app. It checks every current-research selector, all six new dot acquisition budgets, all seven hardware family selectors and their dot flag histories, the explanatory QRSM-to-dot bridge, the original model controls, keyboard navigation, mobile overflow, reduced motion and both videos. It writes `research_browser_validation.json` and focused `preview-research-*.png` screenshots, including focused quantum-dot bridge/model/data panels. Historical deck screenshots remain unchanged. Prior receipts and research screenshots are archived under `validation-history/pre-quantum-dots/`, `validation-history/before-qrsm-dot-bridge/` and `validation-history/before-joint-hom-and-hardware/`; their hashes describe those earlier revisions. The current check uses the previously established installed-Chrome fallback directly: earlier QA found the in-app browser unavailable and older bundled Chromium lacked H.264 decoding. No browser installation, user account or personal browser profile is required by this check.

Optional local preview:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory laser-diagnostics-app
```

Open `http://127.0.0.1:8765/index.html?focus=1#rewind`. Stop the server with Ctrl+C after use. A server is not needed for ordinary offline use.

Keyboard: Tab reaches controls; arrow keys change sliders and move between chapter tabs. Home/End select the first/last chapter from the tab list. Playback can be paused. Figures are labelled and numeric results remain readable as text.
