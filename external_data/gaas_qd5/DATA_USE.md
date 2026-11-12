# Compatibility check: published GaAs quantum-dot photon counts

The file in this folder is an **independent external experiment**, not data collected by the FGCU team and not data from a semiconductor lithography process. We use it to test whether a documented measurement is suitable for the existing photon-click-record interface, not to claim that we inferred a quantum defect or validated the model.

## Original source and license

Julian Münzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil, “Fast and efficient demultiplexing of single photons from a GaAs quantum dot with resonantly enhanced electro-optic modulators,” *APL Photonics* **7**, 070802 (2022), https://doi.org/10.1063/5.0091867.

Original data and authors' README: https://doi.org/10.5281/zenodo.6337697. Dataset license: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/. The original authors' README is preserved unmodified as `readme.md`.

| File | Published MD5 | Meaning |
|---|---|---|
| `QD5_countrates_18-06-15.csv` | `c348c2a0c228222469fae33e8113d852` | Timestamps and per-channel/coincidence counts, each from a **1-second integration**. |
| `readme.md` | `c96c377de1642b00591b717586874e08` | The original authors' description of columns and related article figures. |

The team-generated `data_assessment.png` and `assessment.json` are derived from this dataset. The plotting code and numeric analysis are in `assess_data.py`. We changed no values in the source file.

## What this file can and cannot do

The authors describe a resonantly excited GaAs quantum dot whose photons are routed into four modes. The CSV has 51,421 records, Unix timestamps, four singles channels, and two-, three-, and four-channel coincidence counts. The source README states that each count is accumulated over one second. The actual timestamp spacing varies (median about 1.059 seconds), so the spacing should not be silently treated as the exposure duration.

All **51,421 of 51,421** values for `Ch1` are positive; the same holds for `Ch2`–`Ch4`. Mapping a one-second singles count to a binary bit using `count ≥ 1` therefore produces an all-one sequence. It cannot reveal the fine-time click/no-click patterns assumed by the project's binned-emission model. One cannot recover discarded within-bin arrival times from integrated counts.

`Coin_1234` is zero in about 84% of these one-second records, but it denotes a **four-channel coincidence count**, not a single detector's click stream. Its apparently useful binary variation is a different observable and should not be substituted into the emitter model without an appropriate multiphoton/detector forward model.

This finding is a measurement-compatibility check, **not** a negative result for the project. A meaningful real-data test would need suitable time-tagged records or a model that predicts the actual aggregate counts, channel mapping, integration/readout behavior, and confounders, followed by independent held-out checks and strong classical baselines. The measurement parameters needed to identify a microscopic hidden defect are not established by this file.

## Reproduce the assessment

Python 3.10+, NumPy and Matplotlib. The script verifies the source file's published MD5 before processing it; it will refuse to overwrite existing output files. From this directory:

```powershell
python -m unittest -v test_assess_data.py
python assess_data.py --json assessment_new.json --figure data_assessment_new.png
```

`assessment.json` records per-column ranges and positive counts, source DOI, checksum, and timestamp-spacing summary. No data fitting or significance testing has been performed.
