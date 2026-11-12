# Presentation source and verification

Open the PPTX to present or edit text, charts and tables. Building from source is optional. The PDF preserves the slide appearance as images and does not contain notes.

The source files are in `../.finals-deck-build/`:

- `visual_build.mjs` builds the editable presentation using the Codex bundled `@oai/artifact-tool` library and validates the package, layout, fonts, native charts/workbooks and tables.
- `visual_render_final.mjs` imports the exported PPTX and renders all slides.
- `visual_finish.py` creates the image-based PDF, presenter guide and artifact manifest.
- `visual_notes.json` preserves the narration and timing cues.
- `visual_validation_ibm_campaign_v8.json` is the receipt for the current PowerPoint. `visual_review.json` records final-render/PDF checks and visual inspection.

Rebuilding requires the Codex presentation runtime and presentation skill utilities used for authoring; those libraries are not redistributed in this portable pack. In Codex, use `load_workspace_dependencies` to locate its current Node/Python runtime and libraries. Make `@oai/artifact-tool` resolvable from `.finals-deck-build/` (the original workspace uses a local node_modules junction to the bundled packages). Set `PRESENTATIONS_SKILL_DIR`, `RUNTIME_PYTHON`, and `RUNTIME_NODE_MODULES` to the corresponding installed locations when they differ from the authoring defaults.

The current presentation contains 13 main slides and 22 backups. Its planned duration is 9:20, including a 45-second original-model demonstration. The first nine main slides explain why defect analysis matters, what the QRSM adds to interpreting measurement records, and the separate quantum query. The source reads `research-validation/original_after_click_verification.json` for the native conditional-prediction chart and `laser-diagnostics-app/app-core-query.jpg` for the static demonstration fallback.

This research revision replaces the main sensor benchmark with the unknown-onset study and adds fresh joint-inference, drive-amplitude, phase-inspection, exposure and full-spatial-circuit evidence. Main slide 4 and backup 18 use new synthetic dead-time fits, replacing the historical candidate-count example. Frozen JSON files, source notes and `visual_manifest.json` identify the exact evidence. The current app separates **Current research** from **Earlier sensor study**. Do not mix the earlier known-midpoint sensor results with the new task. The prior PPTX, PDF, guide and manifest are preserved in `archive/pre_research_2026-11-11/`.

The current revision incorporates the completed IBM campaign. Main slide 8 uses the separately reported 8,192-shot precision follow-up with raw conditional accuracy and native CZ costs. Main slide 10 explains the now-implemented joint-photon observation model and its semiconductor-source qualification purpose. The new source surrogate differs from the original QRSM dynamics. No real dot has been fitted. Backups 32–35 cover the observation model, the prospective control/budget study and its classical competitors, digital atomic/photon channel results, and the campaign's coverage limits. Existing backups preserve external GaAs attribution, synthetic results and the distinction between physical experiments and digital emulation. The immediately preceding artifacts are preserved in `archive/pre_hardware_2026-11-11/`, with older versions in the other archive folders.

`hardware_campaign/results.json` identifies the completed jobs and current versioned per-run analysis files. The builder reads those paths instead of silently substituting earlier analysis snapshots. Original archived Kingston rates remain historical context. They are not pooled with the new Marrakesh results. Source hashes in the final manifest identify the actual research and hardware inputs.

From the workspace root, using that configured runtime, export a revision to unused paths. The finalizer deliberately refuses to overwrite an existing PPTX or validation receipt:

```powershell
$env:OUTPUT_PPTX = "$PWD/.finals-deck-stage/reviewed-revision.pptx"
$env:OUTPUT_RECEIPT = "$PWD/.finals-deck-build/visual_validation_next.json"
node .finals-deck-build/visual_build.mjs
```

Inspect every new slide PNG. After the validation receipt passes and the slides are approved, preserve the previous canonical artifacts and copy the validated revision to `finals-deck/Rewind_Amplify_Finals_Visual.pptx`. Then render and package that canonical file:

```powershell
node .finals-deck-build/visual_render_final.mjs
python .finals-deck-build/visual_finish.py
```

Review the rendered slides before distributing a rebuild. Source images, research JSON and archived hardware summaries are included in the pack at the paths referenced by the builder. `visual_manifest.json` identifies the current artifact hashes, evidence hashes, source assets and validation receipt. Native Microsoft PowerPoint playback and actual team timing still need a rehearsal on the presentation computer.
