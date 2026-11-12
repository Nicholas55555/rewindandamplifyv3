# Experiment 2: who finds the hidden defect?

Click records from the Qiskit circuit (experiment 1): an emitter driven by RY(0.6), one hidden defect (exchange phi = 0.45, detuning zeta = 0.3) and a light qubit (emission 0.2) read mid-circuit and reset every step. 4,096 training records of 64 steps, 512 validation records, and 4,096 held-out counting records on which everything below is scored. 'ideal': the perfect simulator, with a perfect detector or v5's good one (efficiency 0.5, dark counts 0.005 per step) applied afterwards. 'device': the FakeMarrakesh noise model on the transpiled, scheduled circuit, with its readout calibrated as the detector. k0: no defect, the controls.

## Predicting held-out clicks

Loss per step (nats) of each learner at the true number of defects; the black boxes' run is the one chosen on the validation records. Gap: to the best learner on the dataset, in nats over all 4,096 counting records' mean per record (paired standard error). Share left (ideal data only): the loss above the truth's, as a share of a memoryless predictor's; under 5% counts as found.

| data | memoryless | physics-shaped QRSM | physics-shaped QRSM + decoherence | + decoherence + gate errors | free-unitary QRSM (black box) | LSTM (black box) |
|---|---|---|---|---|---|---|
| ideal-k1-perfect | 0.27894 | 0.26697 (gap 0.000 +- 0.000), share -0.03% | 0.26697 (gap 0.000 +- 0.000), share -0.03% | 0.26697 (gap 0.000 +- 0.000), share -0.05% | 0.27331 (gap 0.406 +- 0.013), share 52.95% | 0.26901 (gap 0.131 +- 0.008), share 17.01% |
| ideal-k1-good | 0.18206 | 0.18046 (gap 0.000 +- 0.000), share 0.10% | 0.18046 (gap 0.000 +- 0.000), share 0.10% | - | 0.18110 (gap 0.041 +- 0.004), share 40.08% | 0.18073 (gap 0.018 +- 0.003), share 17.38% |
| ideal-k0-good | 0.21704 | 0.21380 (gap 0.000 +- 0.000), share -0.01% | 0.21380 (gap 0.000 +- 0.000), share -0.01% | - | - | - |
| device-k1 | 0.30534 | 0.30324 (gap 0.170 +- 0.009) | 0.30069 (gap 0.007 +- 0.002) | 0.30058 (gap 0.000 +- 0.000) | 0.30168 (gap 0.071 +- 0.007) | 0.30111 (gap 0.034 +- 0.005) |
| device-k0 | 0.34856 | 0.33160 (gap 0.098 +- 0.008) | 0.33019 (gap 0.007 +- 0.002) | 0.33008 (gap 0.000 +- 0.000) | - | 0.33022 (gap 0.009 +- 0.003) |

## Every black-box run

Free unitary: v5's FreeHybrid at the true memory size, Adam from random starts with v5's short-to-long schedule. LSTM: hidden size, learning rate and seed; early stopping on the validation records.

| data | learner | settings | numbers | validation loss per step | held-out loss per step | share left |
|---|---|---|---|---|---|---|
| ideal-k1-perfect | free unitary | lr 0.01, seed 0 | 128 | 0.28036 | 0.27494 | 66.53% |
| ideal-k1-perfect | free unitary | lr 0.01, seed 1 | 128 | 0.28387 | 0.27789 | 91.22% |
| ideal-k1-perfect | free unitary | lr 0.01, seed 2 | 128 | 0.28084 | 0.27528 | 69.40% |
| ideal-k1-perfect | free unitary | lr 0.03, seed 0 | 128 | 0.27905 | 0.27331 | 52.95% |
| ideal-k1-perfect | free unitary | lr 0.03, seed 1 | 128 | 0.28027 | 0.27485 | 65.80% |
| ideal-k1-perfect | free unitary | lr 0.03, seed 2 | 128 | 0.28026 | 0.27467 | 64.29% |
| ideal-k1-perfect | LSTM | hidden 16, lr 0.003, seed 0, stopped at 4000 | 1297 | 0.27636 | 0.27088 | 32.61% |
| ideal-k1-perfect | LSTM | hidden 16, lr 0.01, seed 0, stopped at 4000 | 1297 | 0.27576 | 0.27056 | 29.94% |
| ideal-k1-perfect | LSTM | hidden 64, lr 0.003, seed 0, stopped at 3150 | 17473 | 0.27386 | 0.26901 | 17.01% |
| ideal-k1-perfect | LSTM | hidden 64, lr 0.01, seed 0, stopped at 2650 | 17473 | 0.27402 | 0.26979 | 23.54% |
| ideal-k1-perfect | LSTM | hidden 128, lr 0.003, seed 0, stopped at 2450 | 67713 | 0.27416 | 0.26919 | 18.53% |
| ideal-k1-good | free unitary | lr 0.01, seed 0 | 128 | 0.18430 | 0.18115 | 43.18% |
| ideal-k1-good | free unitary | lr 0.01, seed 1 | 128 | 0.18436 | 0.18116 | 43.52% |
| ideal-k1-good | free unitary | lr 0.01, seed 2 | 128 | 0.18445 | 0.18126 | 49.96% |
| ideal-k1-good | free unitary | lr 0.03, seed 0 | 128 | 0.18436 | 0.18112 | 41.08% |
| ideal-k1-good | free unitary | lr 0.03, seed 1 | 128 | 0.18434 | 0.18112 | 41.64% |
| ideal-k1-good | free unitary | lr 0.03, seed 2 | 128 | 0.18425 | 0.18110 | 40.08% |
| ideal-k1-good | LSTM | hidden 16, lr 0.003, seed 0, stopped at 3500 | 1297 | 0.18398 | 0.18098 | 32.40% |
| ideal-k1-good | LSTM | hidden 16, lr 0.01, seed 0, stopped at 2300 | 1297 | 0.18397 | 0.18073 | 17.38% |
| ideal-k1-good | LSTM | hidden 64, lr 0.003, seed 0, stopped at 3150 | 17473 | 0.18399 | 0.18089 | 27.12% |
| ideal-k1-good | LSTM | hidden 64, lr 0.01, seed 0, stopped at 850 | 17473 | 0.18407 | 0.18091 | 28.19% |
| device-k1 | free unitary | lr 0.01, seed 0 | 128 | 0.29788 | 0.30212 | - |
| device-k1 | free unitary | lr 0.01, seed 1 | 128 | 0.29785 | 0.30204 | - |
| device-k1 | free unitary | lr 0.01, seed 2 | 128 | 0.29838 | 0.30252 | - |
| device-k1 | free unitary | lr 0.03, seed 0 | 128 | 0.29754 | 0.30176 | - |
| device-k1 | free unitary | lr 0.03, seed 1 | 128 | 0.29754 | 0.30168 | - |
| device-k1 | free unitary | lr 0.03, seed 2 | 128 | 0.29743 | 0.30168 | - |
| device-k1 | LSTM | hidden 16, lr 0.003, seed 0, stopped at 3750 | 1297 | 0.29675 | 0.30120 | - |
| device-k1 | LSTM | hidden 16, lr 0.01, seed 0, stopped at 3750 | 1297 | 0.29666 | 0.30106 | - |
| device-k1 | LSTM | hidden 64, lr 0.003, seed 0, stopped at 1750 | 17473 | 0.29674 | 0.30119 | - |
| device-k1 | LSTM | hidden 64, lr 0.01, seed 0, stopped at 1300 | 17473 | 0.29672 | 0.30120 | - |
| device-k1 | LSTM | hidden 128, lr 0.003, seed 0, stopped at 1300 | 67713 | 0.29665 | 0.30111 | - |
| device-k0 | LSTM | hidden 16, lr 0.003, seed 0, stopped at 3750 | 1297 | 0.32764 | 0.33020 | - |
| device-k0 | LSTM | hidden 16, lr 0.01, seed 0, stopped at 2000 | 1297 | 0.32759 | 0.33014 | - |
| device-k0 | LSTM | hidden 64, lr 0.003, seed 0, stopped at 1650 | 17473 | 0.32762 | 0.33026 | - |
| device-k0 | LSTM | hidden 64, lr 0.01, seed 0, stopped at 1650 | 17473 | 0.32753 | 0.33022 | - |

## Counting the defects

Experiment 5's rule on the counting records: the smallest number of defects whose loss is within 2 paired standard errors, or 1 nat in total, of the lowest. Gaps in nats over all 4,096 records (standard errors).

| data | true | physics: gaps | physics count | + decoherence: gaps | + decoherence count | + gate errors: gaps | + gate errors count |
|---|---|---|---|---|---|---|---|
| ideal-k1-perfect | 1 | 0: 9138.1 (58.9), 1: lowest, 2: 2.2 (1.3) | 1 | - | - | - | - |
| ideal-k1-good | 1 | 0: 1074.2 (26.8), 1: lowest, 2: 0.0 (0.5) | 1 | - | - | - | - |
| ideal-k0-good | 0 | 0: lowest, 1: 1.2 (0.9) | 0 | 0: 0.4 (0.6), 1: lowest | 0 | - | - |
| device-k1 | 1 | 0: 6334.5 (48.7), 1: 295.7 (10.3), 2: lowest | 2 | 0: 842.7 (19.5), 1: 1.5 (1.3), 2: lowest | 1 | 1: lowest, 2: 5.9 (2.1) | 1 |
| device-k0 | 0 | 0: 288.8 (10.2), 1: lowest | 1 | 0: lowest, 1: 0.0 (0.4) | 0 | 0: 0.0 (0.3), 1: lowest | 0 |

## The hidden defect's numbers

Errors after the symmetries (theta, phi, zeta), against Cramer-Rao standard deviations at each fit from all 4,096 training records (z = error / sd). For the noise-aware fit, the relaxation and dephasing chances per step of the emitter and the defect, against what the device's T1 and T2 give over one step; with gate errors also the depolarizing chance per step of each and the fitted dark-count rate (the calibration's in brackets).

| data | learner | errors (rad) | sd | z | relaxation per step: emitter, defect (device) | dephasing per step: emitter, defect (device) | depolarizing per step; dark counts |
|---|---|---|---|---|---|---|---|
| ideal-k1-perfect | physics | -0.0006, -0.0002, +0.0045 | 0.0017, 0.0016, 0.0032 | -0.4, -0.1, +1.4 | - | - | - |
| ideal-k1-perfect | + decoherence | -0.0006, -0.0002, +0.0045 | 0.0017, 0.0016, 0.0032 | -0.4, -0.1, +1.4 | 0.0000 +- nan, 0.0000 +- nan | 0.0002 +- nan, 0.0001 +- nan | - |
| ideal-k1-perfect | + decoherence + gate errors | -0.0013, +0.0003, +0.0043 | 0.0018, 0.0017, 0.0032 | -0.7, +0.2, +1.3 | 0.0000 +- nan, 0.0000 +- nan | 0.0000 +- nan, 0.0000 +- nan | 0.0000 +- nan, 0.0000 +- nan; 0.0003 +- 0.0003 (0.0000) |
| ideal-k1-good | physics | +0.0076, +0.0019, +0.0067 | 0.0048, 0.0056, 0.0113 | +1.6, +0.3, +0.6 | - | - | - |
| ideal-k1-good | + decoherence | +0.0076, +0.0019, +0.0067 | 0.0048, 0.0056, 0.0113 | +1.6, +0.3, +0.6 | 0.0000 +- nan, 0.0000 +- nan | 0.0000 +- nan, 0.0000 +- nan | - |
| device-k1 | physics | +0.0312, -0.0092, -0.0209 | 0.0025, 0.0024, 0.0046 | +12.7, -3.9, -4.6 | - | - | - |
| device-k1 | + decoherence | +0.0313, -0.0111, -0.0009 | 0.0046, 0.0032, 0.0064 | +6.9, -3.5, -0.1 | 0.0318 +- 0.0080, 0.0000 +- nan (0.0214, 0.0247) | 0.0001 +- nan, 0.0858 +- 0.0114 (0.0076, 0.0351) | - |
| device-k1 | + decoherence + gate errors | +0.0082, -0.0013, -0.0059 | 0.0063, 0.0035, 0.0065 | +1.3, -0.4, -0.9 | 0.0069 +- 0.0135, 0.0001 +- nan (0.0214, 0.0247) | 0.0001 +- nan, 0.0312 +- 0.0251 (0.0076, 0.0351) | 0.0020 +- 0.0090, 0.0184 +- 0.0054; 0.0080 +- 0.0008 (0.0042) |

## Data efficiency (ideal-k1-good)

The same held-out records; fewer training records (the first 256 or 1,024 of the 4,096). The LSTM's configuration is chosen on the same 512 validation records at each size.

| training records | physics: share left | LSTM, chosen on validation: share left | LSTM, best of all runs on held-out | LSTM numbers |
|---|---|---|---|---|
| 256 | 17.14% | 37.27% | 37.27% | 17473 |
| 1024 | 0.65% | 31.53% | 31.53% | 1297 |
| 4096 | 0.10% | 17.38% | 17.38% | 1297 |

## Cost

- free: 18 runs, median 3.3 min, total 63 worker-minutes
- lstm: 26 runs, median 4.9 min, total 202 worker-minutes
- noise: 14 runs, median 5.0 min, total 68 worker-minutes
- one: 7 runs, median 12.8 min, total 85 worker-minutes
- two: 3 runs, median 30.0 min, total 90 worker-minutes
