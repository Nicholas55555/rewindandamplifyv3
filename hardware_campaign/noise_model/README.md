# Simulator against hardware: what a noise model predicts for the circuits we ran

Added in V3. Offline: it reads the saved campaign files, submits nothing, and needs no IBM account.

**Question.** On 11 November 2026 the lighter build (local reflection, 58 two-qubit gates) returned the requested click in 76.90% of shots on IBM Marrakesh, and the textbook build (full reflection, 125 gates) in 69.26%. Without noise the two are tied at 96%. Is that gap what the device's own error rates predict, or something else?

**Method.** For every job, the campaign saved the exact compiled circuits that were submitted, the device's calibration snapshot, and the raw counts. [`simulate.py`](simulate.py) rebuilds each submitted circuit on only the qubits it used and simulates it as a density matrix with:

| Operation | Error in the model |
|---|---|
| `sx`, `x` | one-qubit depolarizing error at the reported average gate infidelity |
| `cz` | two-qubit depolarizing error at the reported average gate infidelity |
| `rz` | none (a virtual frame change) |
| readout | each qubit's P(read 1 \| prepared 0) and P(read 0 \| prepared 1), measured by the all-zeros and all-ones circuits **inside the same job** |
| not modelled | idle decoherence, crosstalk, leakage, drift |

Probabilities are read out exactly, so the predictions carry no shot noise and are identical on every machine.

Three predictions are compared with the measurement:

- **ideal**: no noise.
- **calibration**: gate errors exactly as reported.
- **echo-scaled**: every gate error multiplied by one number, fitted **only** to the two echo circuits (run the machine forwards, then backwards; a perfect device returns all zeros). The science circuits are then predicted without having been seen.

## Result

The echo circuits put the device at **1.54 times** its reported gate errors: 0.53% to 0.63% lost per two-qubit gate, against 0.37% to 0.44% in the calibration-only model.

| Featured circuit | Two-qubit gates | Ideal | Calibration | Echo-scaled prediction | **Measured** (8,192 shots) |
|---|---:|---:|---:|---:|---:|
| Steer + local reflection | 58 | 96.10% | 83.15% | 78.40% | **76.90%** |
| Steer + full reflection | 125 | 96.49% | 76.29% | 69.72% | **69.26%** |
| Local minus full | | −0.39 points | 6.86 | 8.68 | **7.64** |

| Answer error (TV distance of accepted histories from exact) | Calibration | Echo-scaled prediction | **Measured** |
|---|---:|---:|---:|
| Steer + local reflection | 0.070 | 0.089 | **0.118** |
| Steer + full reflection | 0.111 | 0.165 | **0.181** |

The after-click answer at step 6 (exact: 4.67% with the defect, 10.10% without):

| Build | Two-qubit gates (defect / none) | Echo-scaled prediction (defect / none) | **Measured** (defect / none) | Order |
|---|---:|---:|---:|---|
| Plain sampling | 88 / 15 | 12.52% / 12.11% | **13.41% / 10.06%** | predicted nearly tied, measured reversed |
| Steer + local | 98 / 32 | 8.44% / 11.29% | **8.79% / 11.66%** | predicted right, measured right |
| Steer + full | 182 / 56 | 10.36% / 11.39% | **12.90% / 10.87%** | predicted barely right, measured reversed |
| Memory-only control | 93 / 23 | 8.43% / 3.26% | **8.46% / 3.97%** | wrong by design, in both |

## What this supports

1. **The gap is what gate errors predict.** With no noise the two builds are tied. A model that contains only gate and readout errors opens a gap of 7 to 9 points, and the hardware shows 7.64. That is evidence that the gate count is the main driver. It is not proof: the two circuits also differ in width, routing and which qubit reads the click.
2. **Calibration data alone is optimistic.** Reported gate errors over-predict both hit rates by about 6 to 7 points. One scale factor fitted on separate echo circuits brings both predictions within 1.5 points of the measurement.
3. **The biased answers are understood for the lighter build.** The local build's after-click answers (8.79% and 11.66% instead of 4.67% and 10.10%) are predicted within 0.4 points. The bias is noise that this model captures, which is the first step toward correcting it.
4. **Rare events are fragile.** For plain sampling the model predicts that the defect model's answer rises from 4.67% to about 12.5%, because false clicks swamp a 3.95% event. That is what the hardware shows, and it is the reason the unamplified circuits give the wrong order.

## Limits

- One scale factor stands in for everything the model leaves out. It is a summary of this device on this day, not a physical constant.
- The model under-predicts the damage to the deepest circuit (182 gates): 10.36% predicted, 12.90% measured. Depolarizing noise is too kind to long circuits.
- Predicted answer errors are below the measured ones for both featured circuits. The hardware has structure in its errors that uniform depolarizing does not.
- The echo circuits and the science circuits ran in the same job on overlapping qubits. The fit is out of sample in circuits, not in time or in qubits.
- Readout rates come from all-zeros and all-ones circuits, so they include state-preparation error.
- Nothing here changes the headline measurements, and nothing here is a claim of quantum advantage.

## Run it

```bash
python hardware_campaign/noise_model/run_study.py            # about 20 seconds; rewrites results.json
python hardware_campaign/noise_model/run_study.py --check    # recompute and compare with the saved file
python -m unittest discover -s hardware_campaign/noise_model -p "test_*.py" -v
```

The tests confirm that the noise-free simulation of each compiled circuit reproduces the campaign's stored ideal probabilities to 10⁻¹², and that the measured quantities recomputed here from raw counts equal the campaign's own analysis.

Inputs: [`runs/original_precision_v1/`](../runs/original_precision_v1/) (job `dbqb1ifv5hds73dfo310`). Output: [`results.json`](results.json), with the SHA-256 of every input.
