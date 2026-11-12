# An external experimental photon-correlation reference

This folder contains a small, openly licensed *third-party* experimental dataset for scientific context. It is **not** a measurement by the FGCU team, not a test of the team's simulator, and not photolithography data.

The data are the processed short-time second-order photon-correlation trace and the original authors' fit for Fig. 3a of:

Clarisse Fournier, Kenji Watanabe, Takashi Taniguchi, Julien Barjon, Stéphanie Buil, Jean-Pierre Hermier, and Aymeric Delteil, “Investigating the fast spectral diffusion of a quantum emitter in hBN using resonant excitation and photon correlations,” *Physical Review B* **107**, 195304 (2023), https://doi.org/10.1103/PhysRevB.107.195304.

Dataset: https://doi.org/10.5281/zenodo.7938744, CC BY 4.0, https://creativecommons.org/licenses/by/4.0/. The copied source files are unmodified:

| File | Source data | Published MD5 |
|---|---|---|
| `fig3a.dat` | normalized measured correlation vs delay | `b2049ca3bac8ea3179204e8f8795c985` |
| `fig3a_fit.dat` | original authors' model fit vs delay | `86f6cbcf601d03f794d21be0b3230a40` |

`published_photon_correlation.png` is a new plot of those two files, not a reproduction of the published figure image. Generate it with `python plot_reference.py` using NumPy and Matplotlib. We did not fit parameters or compute error bars. The dataset supplies processed correlations, not raw event timestamps in these files; one cannot infer individual click histories or claim the team's quantum model reproduces the data from this plot alone.

The paper reports resonant optical excitation and photon correlations from an hBN color center. The authors interpret the measurements using a model that accounts for spectral diffusion. A correlation trace alone does not uniquely identify a hidden physical defect: calibration, control experiments, detector effects, and alternative explanations matter. A real validation of our model would need compatible time-tagged records or a measurement model for the supplied correlations, appropriate calibration and comparisons, and held-out evaluation.

## A possible next raw-data source

Thomay et al. have released [time-tagged Photon-HDF5 data from quantum dots](https://doi.org/10.5061/dryad.1rn8pk15f) under CC0. The described experiment uses quantum dots in plant leaves and a four-detector setup; it is a different physical setting from the hBN trace above and from our emitter–defect model. It may be useful for building a real timestamp ingestion and baseline workflow, subject to checking binning, detector channels, laser timing, drift, and whether a particular physical model is appropriate. The smallest listed data archive is about 130 MB. The public download endpoint returned HTTP 403 in this environment, so the raw files were not obtained or analyzed here; the repository description is a lead, not validation.
