# Stronger classical baselines for synthetic photon records

This is a new, independent analysis of the existing `../synthetic_click_records.csv`. It asks how a known-family, fixed-nuisance physical model compares with flexible **classical** binary hidden Markov models (HMMs) on held-out click sequences. It does not alter the bundled data, run quantum hardware, or demonstrate a quantum advantage.

## Data and fairness

- The same split as the companion evaluation: first 420 of 600 independent simulated records for training and the final 180 for evaluation, with 40 binary time bins each. No held-out records are used for fitting or selecting a restart in this analysis. **The holdout was already evaluated in the earlier companion experiment; it is not a newly untouched test set**, and design choices were made with knowledge of the preceding analysis.
- The physical model is a classical numerical likelihood calculation for the same open quantum model family that generated the data. It is given **the correct value of every nuisance parameter** and fits only the coupling, using the pre-existing 26-point grid. This is a strong and deliberate information advantage.
- Each HMM has 2 or 3 hidden states, a learned initial distribution, transition matrix, and Bernoulli emission probability per state. All parameters are learned from the training data by numerically scaled forward-backward expectation maximization, from multiple random starts. The restart with the highest **training** likelihood is chosen. There are 5 free probabilities for the 2-state model and 11 for the 3-state model.
- We additionally include an IID Bernoulli baseline and a first-order observed-bit Markov model, both trained on the same data. The Markov baseline uses Laplace pseudocounts as in the original evaluator.
- The HMMs are useful baselines, not an exhaustive set of classical methods; finite random restarts and finite optimization iterations do not guarantee a global optimum. A fitted HMM can outperform these results if optimized better or changed in structure.

## Reproduce

Python 3.10+ with the `../requirements.txt` dependencies. From this directory:

```bash
python -m unittest -v test_compare.py
python compare.py --starts 12 --max-iter 1200 --output heldout_hmm_results_extended.json
```

The output JSON contains every held-out sequence's log likelihood for each model, all training-start scores and convergence flags, the selected parameters, seed, input data hash, and the paired comparisons. It refuses to replace an existing output unless `--overwrite` is passed. For this Windows laptop, setting `OPENBLAS_NUM_THREADS=1` before Python can improve performance.

Tests check the forward-backward output against exhaustive enumeration of all hidden paths in a tiny problem, verify that per-record physical likelihood sums to the existing aggregate implementation, check EM reproducibility and likelihood monotonicity, and verify paired uncertainty calculations.

## Results on this particular split

The table uses `heldout_hmm_results_extended.json` (12 starts per HMM, up to 1,200 iterations each). Higher held-out log likelihood is better. Differences are physical model minus baseline, and the uncertainty is across the 180 held-out sequences.

| Baseline | Held-out total log likelihood, nats | Physical minus baseline, nats/record | Paired SE | Percentile bootstrap 95% interval, nats/record |
|---|---:|---:|---:|---:|
| IID Bernoulli | -3605.919 | 0.3161 | 0.0418 | 0.2341 to 0.3961 |
| Observed-bit Markov-1 | -3576.450 | 0.1524 | 0.0285 | 0.0949 to 0.2066 |
| 2-state binary HMM | -3564.936 | 0.0884 | 0.0292 | 0.0308 to 0.1452 |
| 3-state binary HMM | -3554.714 | 0.0316 | 0.0159 | 0.0010 to 0.0633 |

The physical model's held-out total is **-3549.022 nats**. The 3-state baseline narrows the difference from the previously reported +27.43 nats against Markov-1 to **+5.69 nats across 180 records**. This is a small difference on a reused synthetic holdout, and the bootstrap interval is conditional on the selected models; it should not be read as proof of a general physical or quantum advantage.

The chosen 2-state fit met the stated convergence tolerance at iteration 402, and the chosen 3-state fit at iteration 1,193. Overall, **5 of 12 two-state starts and 1 of 12 three-state starts met that strict tolerance** within the cap. The other starts remain valid candidate fits but do not establish that the global optimum was found. `heldout_hmm_results.json` is an earlier 300-iteration exploratory run and should not be confused with the extended result.

## How to interpret the uncertainty

For each held-out record, subtract the baseline's log likelihood from the physical model's. A positive difference favors the physical model's prediction. Report its mean in nats per record, the sample standard error across records, and a percentile bootstrap interval from 5,000 independent record resamples with a fixed seed. The total difference sums the same values across all 180 held-out records.

These intervals describe variation across held-out records **conditional on the particular fitted models**. They do not account for a different training sample, optimization/model-selection uncertainty, multiple comparisons, different physical parameter settings, model misspecification, or whether the family describes a real emitter. These are exploratory comparisons on one synthetic dataset and one split; stronger validation needs repeated independent datasets and generator-parameter changes, nuisance-parameter fitting, detector confounders and real photon records.

## Fresh synthetic replication and detector mismatch

`fresh_replication.py` draws new independent train and held-out record sets for three random seeds; these are not the reused 600 records above. Each replicate uses 400 training and 150 held-out 40-bin records, all from the same synthetic physical generator and fixed parameter setting. It compares:

1. A physical fit that is given the correct model family and nuisance parameters, fitting only coupling on a grid.
2. The same fit with deliberately wrong detector efficiency 0.54 (true 0.68) and dark rate 0.035 (true 0.018), again fitting coupling. This is a chosen stress test, not a real detector calibration or uncertainty distribution.
3. A first-order observed-bit Markov model whose stationary rate is constrained to the training-set click fraction, with the transition persistence fit on training records.
4. A three-hidden-state Bernoulli HMM with six random training starts and at most 800 EM iterations per start; select by training likelihood only.

Each seed reports held-out per-record likelihoods and paired differences, with standard errors and 2,000-replicate percentile bootstrap intervals conditional on the trained fits. The JSON records seeds, generated-array hashes, fitted parameters, all HMM-start convergence flags, and software versions. Even the new holdouts remain synthetic samples from one family and one physical parameter setting. Detector mismatch is not fitted away except by adjusting the coupling, so a flexible HMM can be favored in a way a properly calibrated physical model might not be. These are exploratory stress tests, not measurements of a physical device.

```bash
python -m unittest -v test_fresh_replication.py
python fresh_replication.py --output fresh_replication_results.json
python -m unittest -v test_refine_replication.py
python refine_replication.py --input fresh_replication_results.json --output fresh_replication_refined.json
```

Use `OPENBLAS_NUM_THREADS=1` for this laptop. The default run executes sequentially and may take several minutes. An existing output is not overwritten without `--overwrite`. The first full run produced and saved all numerical results, but exited during its final Windows console summary because the console could not encode a Unicode minus sign. The source print was changed to ASCII and a regression test now covers a CP1252 console; the saved file contains an `execution_note` recording this. Its fitted coupling is recorded separately from the fixed nuisance parameters.

The `refine_replication.py` step re-creates both datasets for each seed and checks their hashes. It takes each seed's best **training-selected** EM restart and performs a training-only L-BFGS-B local optimization with analytic forward-backward gradients. It keeps the original EM fit if the new candidate reduces training likelihood. The test suite checks those gradients against finite differences. Only the selected restart receives this polish, so the procedure still does not establish a global optimum.

### Fresh-run results

The table uses `fresh_replication_refined.json`. Values are mean paired held-out log-likelihood differences in nats per 40-bin record, with one paired standard error. Positive means the first model predicts better on that simulated holdout.

| Synthetic seed | Known-nuisance physical minus HMM | Mismatched-detector physical minus HMM | HMM minus rate-matched Markov |
|---|---:|---:|---:|
| 31001 | +0.0632 ± 0.0217 | +0.0296 ± 0.0244 | +0.2067 ± 0.0562 |
| 31002 | +0.0264 ± 0.0182 | +0.0101 ± 0.0191 | +0.2182 ± 0.0407 |
| 31003 | +0.0352 ± 0.0219 | −0.0156 ± 0.0254 | +0.2704 ± 0.0496 |

The 95% conditional bootstrap intervals for known-nuisance physical minus HMM were [0.0214, 0.1078], [−0.0088, 0.0628], and [−0.0066, 0.0795] nats per record. For the deliberately mismatched physical model minus HMM they were [−0.0133, 0.0822], [−0.0260, 0.0474], and [−0.0597, 0.0378]. The fitted coupling was 0.65 for all correctly specified fits and 0.45 for all deliberately mismatched fits, compared with the synthetic true value of 0.65.

All selected EM fits reached the 800-iteration cap without meeting the strict EM stopping tolerance. The subsequent L-BFGS-B optimizations reported success based on small relative objective change and improved training likelihood by 0.08–0.28 nats, but **all three reached a logit bound of ±20**. A boundary and a local optimizer's success flag are not evidence of a globally optimal HMM. The uncertainty intervals reflect held-out sequences conditional on these particular fits and do not include additional optimization uncertainty or independent changes in the generating physics.
