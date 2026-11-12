# External GaAs quantum-dot HOM reference

This folder imports six **external experimental histograms**, unchanged, for a bounded data-compatibility audit. The measurements are by **Julian Münzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil**. They are not FGCU team measurements or a new fit of a physical source.

Source: [Zenodo dataset 6337697](https://doi.org/10.5281/zenodo.6337697), published 17 March 2022, **CC BY 4.0**. The [paper, arXiv:2203.08682v1](https://arxiv.org/html/2203.08682v1), describes the two-photon interference experiment in Section IV and Figure 4. See [attribution and license](DATA_LICENSE.md).

## Exactly what was imported

The unmodified [source mapping README](source_readme.md) associates these files with Figure 4:

| Panel / excitation separation | Co-polarized file | Cross-polarized file |
|---|---|---|
| 4a / 13.1 ns | `HOM_QD5_resonant_photon1+2_17-39-23.csv` | `HOM_QD5_resonant_photon1+2_dist_17-42-16.csv` |
| 4b / 26.2 ns | `HOM_QD5_resonant_photon1+3_17-50-06.csv` | `HOM_QD5_resonant_photon1+3_dist_17-52-41.csv` |
| 4c / 39.4 ns | `HOM_QD5_resonant_photon1+4_17-57-10.csv` | `HOM_QD5_resonant_photon1+4_dist_18-00-48.csv` |

All six files match both the pinned published MD5 values and the saved [Zenodo API inventory](zenodo_record.json). Each has header `Time (ps),Counts`, **5,000 rows**, an identical grid from **−125,000 to 124,950 ps** at **50 ps spacing**, and nonnegative integer counts. The [provenance manifest](provenance_manifest.json) records sizes, MD5, SHA-256, shape, axis checks and count totals. Those totals are descriptive sums, not exposure-normalized rates.

The histogram x-axis is a **coincidence-time difference**. The 13.1/26.2/39.4 ns labels describe the separation of excitation pulses for the compared photons; they are not three positions on that histogram axis. These files contain neither a sequence of individual pulse outcomes nor underlying emitter-state trajectories.

## Published values are not a new estimate

Section IV reports corrected HOM visibilities **0.803(5), 0.826(4), 0.774(4)** for the three separations. The paper describes approximately constant indistinguishability and discusses possible polarization-systematic error in the last pair. This import makes no monotonic-decay claim. Its correction uses a measured splitter ratio and finite multiphoton probability. [Paper, Section IV](https://arxiv.org/html/2203.08682v1#S4)

**No visibility is recalculated here.** The CSVs and mapping README do not supply acquisition duration or a complete per-run normalization recipe. Reproduction would require verified central/reference integration conventions, relative normalization, background treatment, calibration association and uncertainty propagation. A ratio of two raw center-bin heights would not reproduce that analysis.

## Compatibility and limits

These co/cross histograms are suitable reference observations for an explicitly calibrated two-photon interference measurement model. They are not interchangeable with the project's one-second integrated count CSV or binary QRSM histories. A forward comparison would need the actual timing response, pulse/routing structure and nuisance parameters before any source-parameter inference. Agreement with one contrast would not uniquely identify charge noise, a microscopic defect or laser instability.

This task establishes source identity, format and observable compatibility only. It does not validate a QRSM, diagnose a new device, provide lithography data or demonstrate quantum advantage.

![Raw external HOM histograms, with no exposure normalization or visibility fit](raw_hom_histograms.png)

The optional plot preserves every count and the source grid; it converts ps to ns for display. Counts from separate acquisitions are overlaid **without** an established relative exposure normalization. The central panels are display windows, not fitted or integrated peaks. [PDF version](raw_hom_histograms.pdf) · [plot provenance](plot_manifest.json).

## Reproduce the audit

From the repository root, using standard Python:

```bash
python quantum_dot_bridge/reference_hom/import_verify.py
python -m unittest discover -s quantum_dot_bridge/reference_hom -p test_import_verify.py -v
```

To retrieve missing source files, add `--download`. Existing files are never replaced. A fresh copy of the import tool can create its first manifest with `--download --write-manifest`; it refuses to overwrite a saved manifest. The downloader uses only public Zenodo endpoints.

Replot with Matplotlib installed:

```bash
python quantum_dot_bridge/reference_hom/plot_raw.py
```

The saved checks distinguish data integrity from physics validation. The original source files, their license and reported paper values remain separate from project-authored code and derived plots.
