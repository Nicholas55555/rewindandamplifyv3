# Fresh validation of the selected exact design

This protocol is saved after deterministic design selection and before generating any samples below. It is a prospective check of an **exploratorily selected model design**, not retroactive registration of the original study. The design-results hash is recorded in the run receipt. No new samples feed back into control selection. Main results and hardware bundles remain unchanged.

## Frozen design and independent resources

Use theta=3*pi/4 and control +2*Gamma on the second emission of each pair, for four consecutive attempted pairs. Retain the environment within each four-pair block; reset to I/2 between blocks. Parameters otherwise equal the earlier nominal values. A full three-outcome block has81 possible records. The exact CP-model probabilities can be sampled as a categorical distribution because blocks are explicitly independent. This accelerates the same finite model; it does not replace wavepacket preparation by a fitted final probability.

The master seed is20261112047, distinct from the main study. SeedSequence namespaces: (1,i) for independent20,000-opportunity e01/e10/eta calibration; (2,) for20,000 coherent training blocks; (3,) for20,000 separate coherent predictive-evaluation blocks; (4,j) for each budget's2,000 classical-null calibration records; (5,j,k) for each budget/case's2,000 held-out records; (6,states,start) for HMM initializations. Save all sampled raw block records and independent-block count vectors. Check namespace uniqueness before evaluation. No main records enter this stage.

## Prospective power and nuisance checks

Evaluate budgets16,64,256,646,1024,1911 independent four-pair blocks per inference record. These cost64,256,1024,2584,4096,7644 attempted pairs; there are2 source excitations per pair. Resets, calibrated shifts and gap rotations are additional resources whose time, energy and imperfect implementation are unpriced. The two larger unusual budgets came from the exact normal estimate and sufficient bound, not a tuned sample.

Score the fixed nominal coherent/dephased model log-likelihood ratio using the independently estimated e01/e10/eta. The test is against only this specified null, not all classical explanations. Independently calibrate each budget's threshold to the1901st order statistic from2,000 classical-null records, declaring a flag only for a strictly larger score. Report actual false flags; ties can be conservative. The null calibration assumes a trusted classical-null reference is available; this is supplied synthetically here.

Held-out cases: nominal coherent; nominal classical; classical readout change e01=.05/e10=.03; classical collection eta=.5; classical mode overlap=.85; coherent partial gap dephasing=.25; classical gap angle shifted+0.1radian. These are specified counterfactuals, not inferred defects. Record Wilson95% intervals conditional on this single detector calibration and selected model. At each budget, separately report the exact-model bound threshold log4, under true known nominal parameters, to validate the mathematical guarantee without conflating it with finite-calibration inference. The bound's stated5%/80% guarantee covers only nominal simple hypotheses and exact resets, not nuisance cases.

## Strong classical prediction controls

Fit ordinary4-state and8-state HMMs to the same20,000 coherent blocks, using10 independent starts each, at most200 EM iterations/start and training convergence tolerance1e-7 nats per pair. One observed context is used here, with a shared transition and three-outcome emissions. Select starts only by training likelihood. Save every start's final score and convergence length. Also fit the unrestricted81-outcome classical block distribution with symmetric Dirichlet pseudocount1/2; it learns the full joint four-pair law without quantum states. An exact classical categorical oracle equals the physical block distribution by construction, illustrating that the bounded observation law does not certify quantum memory.

Compare all predictors on the same20,000 separate coherent blocks, with paired per-block log-score intervals. Physical predictors receive the specified source parameters and either calibrated or true detector parameters; this gives them prior information unavailable to fitted HMMs. Disclose it. Training data are matched across the learned classical models, but parameter counts, optimization and computation are not equal; no algorithmic advantage follows. Stronger starts/tolerance do not prove global HMM optimality. Do not discard or retune a classical model after inspecting held-out performance.

## Checks and interpretation

Verify vector count scoring against explicit block-record likelihoods, exact multinomial resource counts, strict threshold indexing, seed disjointness and trained model normalization. Save sources/protocol hashes before sampling. Independent review must check the selected-control distribution and reset assumption. All uncertainty is conditional simulation uncertainty. This stage may establish model-based power at a much larger and differently prepared acquisition budget; it cannot establish a microscopic quantum defect, practical dot-control feasibility, empirical semiconductor performance or quantum computational advantage.
