# Laser diagnostics research and finals delivery plan

The research question is whether an optical quantum sensor contributes useful information alongside existing laser diagnostics. The audience should see the physical interaction, the observations, and the distinct role of quantum computation. The finals presentation remains a ten-minute talk anchored in the team's archived IBM hardware experiment.

## Evidence already reviewed

`WORKSPACE_AUDIT.md` records the complete text review of the supplied research documents and the coverage of source, data, figures, PDFs, and prior conversations. The user's complementary-sensor idea appears in the reconstructed photonics conversation on pages 8, 11–12, and 17–18. The earlier `laser_sensor_poc` illustrates temporal information but does not provide a physical conventional comparator or equal-resource evidence. Preserve it as a first exploratory model.

## Research experiment

Use a narrow-line optical laboratory surrogate. Model a laser-frequency perturbation, an optical atomic Ramsey sensor, a power monitor, and coherent frequency measurements against external references. Include finite interrogation and reset time, decoherence, measurement errors, source noise, and drift of the references. Explicitly identify hypothetical parameters and cite physical precedent.

Compare conventional diagnostics alone, the same diagnostics plus an atomic sensor, and conventional diagnostics plus an independent coherent receiver. Hold the observation interval and allocated signal tap budget fixed where the model supports that comparison. Report unmatched apparatus, atom, local-oscillator, preparation, and fluorescence-readout resources. A resource ledger does not by itself establish equal engineering cost.

Choose a diagnostic task before evaluating results. Calibrate thresholds and nuisance parameters on independent data, then report detection, false alarms, estimation error or conditional predictive information on held-out simulations. Include amplitude-only and sensor-reference drift controls, degraded readout/coherence, and changes to noise assumptions. Retain unfavorable results and distinguish simulation uncertainty from uncertainty about the physical model.

Atomic-reference laser-noise spectroscopy is established prior work. [Bishof et al., Physical Review Letters 111, 093604 (2013)](https://arxiv.org/abs/1303.6741) demonstrated this principle. Our research explores reproducible diagnostic comparisons and their relationship to the project's model-based history queries. A visible or near-infrared surrogate does not establish compatibility with a CO₂ drive laser, DUV exposure light, or emitted EUV.

## Audience experience

Build a local application that works without Wi-Fi or a live QPU. A short guided walkthrough should show a source perturbation, synchronized diagnostic responses, the held-out benchmark and its controls, then the separate prepare, mark, rewind, and amplify calculation. Controls must execute documented calculations or select clearly labeled saved simulations.

Provide animated GIFs and static fallbacks for the sensor interaction and quantum-history query. Preserve generators and provenance. The application and deck must clearly distinguish archived hardware measurements, simulated quantum circuits, simulated sensor measurements, and proposed future experiments.

## Presentation

Preserve the previous deck and deliver a new visual edition with ten main slides, technical backups, speaker notes, and a PDF fallback. Aim for approximately nine minutes of prepared delivery plus demonstration/transition margin. Keep the original quantum-computing contribution central. Use a short sensor demonstration to explain the future application rather than crowding the talk with all exploratory projects.

## Completion evidence

| Requirement | Evidence needed |
|---|---|
| More realistic sensor simulation | Documented equations, physical units, numerical checks, finite timing and nonidealities |
| Incremental diagnostic information | Independent calibration and held-out comparisons, strong classical alternatives, uncertainty and negative controls |
| Reproducibility | Saved parameters, seeds, results, source, dependency instructions and passing relevant tests |
| Working application | Offline launch, observed interaction checks, responsive readable layouts and accurate result labels |
| Visual demos and GIFs | Actual playable GIF files, inspected frames, static fallbacks and model provenance |
| Strong finals presentation | All slides rendered and visually inspected, source-traceable claims, ten-minute pacing guide and presenter notes |
| Portable delivery | Updated entry document, file verification, archive hashes and clear current artifact names |

Team rehearsal and a check on the actual venue computer remain human preparation steps. Competitive placement depends on the judges and other teams; the deliverable standard is a coherent, convincing, technically defensible entry with a reliable demonstration.
