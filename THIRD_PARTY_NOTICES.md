# License and attribution

Project-authored code and documentation continue the original project's MIT license; see [LICENSE](LICENSE). Third-party datasets retain their own licenses. Including them here does not imply that their authors endorse this project.

## Original Rewind & Amplify project

`rewindandamplify-main/` contains the original FGCU team's project and saved IBM results, with its MIT notice preserved. Source: [Nicholas55555/rewindandamplify](https://github.com/Nicholas55555/rewindandamplify). The v2 repository preserves that directory layout for reproducibility; it does not replace the original repository's Git history.

## Experimental photon-correlation reference

`photon_reference/fig3a.dat` and `fig3a_fit.dat` are unmodified source data by Clarisse Fournier, Kenji Watanabe, Takashi Taniguchi, Julien Barjon, Stéphanie Buil, Jean-Pierre Hermier and Aymeric Delteil, from “Investigating the fast spectral diffusion of a quantum emitter in hBN using resonant excitation and photon correlations,” *Physical Review B* **107**, 195304 (2023).

- [Dataset, DOI 10.5281/zenodo.7938744](https://doi.org/10.5281/zenodo.7938744)
- [Publication](https://doi.org/10.1103/PhysRevB.107.195304)
- [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/)

`published_photon_correlation.png` is a new plot of those data and the authors' fit. See [the reference README](photon_reference/README.md) for checksums and interpretation limits. These are third-party measurements, not measurements or validation of our model by the FGCU team.

## GaAs quantum-dot count data

`external_data/gaas_qd5/QD5_countrates_18-06-15.csv` and `readme.md` are unmodified data/documentation by Julian Münzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil, from “Fast and efficient demultiplexing of single photons from a GaAs quantum dot with resonantly enhanced electro-optic modulators,” *APL Photonics* **7**, 070802 (2022).

- [Dataset, DOI 10.5281/zenodo.6337697](https://doi.org/10.5281/zenodo.6337697)
- [Publication](https://doi.org/10.1063/5.0091867)
- [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/)

`assessment.json` and `data_assessment.png` are derived analyses/plots; source values are unchanged. See [DATA_USE.md](external_data/gaas_qd5/DATA_USE.md). Integrated counts do not supply the individual photon arrival times required by several proposed diagnostics.

The six unmodified HOM histogram CSVs and `source_readme.md` in `quantum_dot_bridge/reference_hom/` come from the same authors and dataset under **CC BY 4.0**. The separate [data notice](quantum_dot_bridge/reference_hom/DATA_LICENSE.md) and [provenance manifest](quantum_dot_bridge/reference_hom/provenance_manifest.json) identify exact source files and checksums. Their derived raw plots convert the timing axis from ps to ns without fitting visibility or normalizing acquisitions. These experimental files are separate from our synthetic quantum-dot benchmark.

## Presentation and software dependencies

The conceptual cover image was generated with OpenAI image generation; it is not experimental evidence. AI assistance is disclosed in the project README and presenter guide. Referenced papers are cited, rather than redistributed as source PDFs. The supplied judging workbook, competitors' scores and private conversation exports are not part of this public repository.

Qiskit, Qiskit Aer, QuTiP, NumPy, SciPy, Matplotlib and other dependencies are installed separately under their respective licenses. The proprietary presentation authoring runtime is not redistributed; the editable PPTX, PDF, authoring source and final verification receipts are included.
