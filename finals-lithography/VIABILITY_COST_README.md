# Conditional sampling: rounds, quality and costs

This experiment extends the five- and seven-site **synthetic** independent-Bernoulli missing-contact model. It is not wafer data, a realistic resist model, a real QPU run or a quantum-advantage result. It addresses two questions that are easy to miss when showing a higher event-hit rate: **are the accepted histories still correct, and how much circuit work is involved?**

## A strong exact classical baseline for this particular toy

Let each of `n` sites independently absorb with probability `p`; the failure event is zero or one absorption. Conditional on failure:

```
P(all zero | failure) = (1-p) / ((1-p) + n*p)
P(each specific one-hot history | failure) = p / ((1-p) + n*p)
```

`exact_conditional_draw` samples that law by first choosing zero versus one absorption, then selecting a uniform site for a one-hot history. It outputs one conditionally distributed history without rejecting complete histories, with O(n) output size. The formula and implementation are special to the independent, equal-probability threshold model. They do not solve the separate 7×7 spatial simulator or general lithography. Its derivation and any process-model setup cost are not timed.

At the five-site default, exact enumeration confirms the all-zero probability is 1/21 and each one-hot history has probability 4/21. A classical computer can compute the event probability and generate matching examples directly. Therefore this toy cannot by itself support a practical quantum speedup claim.

## Noisy quantum-circuit round sweep

`viability_cost_study.py` constructs the complete prepare/mark/rewind/reflect circuits using the reversible counter oracle. It routes every circuit to the **same seeded synthetic 10-qubit line target** used by the earlier pilot and simulates its target-derived local gate noise with Aer density matrices, then analytically applies independent readout errors. Different circuits can have different physical layouts. Numbers are exact only within this noise model, not real-device outcomes. Gate counts include all gates in the routed circuit, not just a named oracle. No QPU was submitted.

| Sites | Rounds | Ideal matching probability | Noisy raw matching probability | Noisy conditional-history TV | Routed CX per circuit |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0 | 0.00672 | 0.00691 | 0.0022 | 0 |
| 5 | 1 | 0.05940 | 0.05398 | 0.0743 | 554 |
| 5 | 2 | 0.15914 | 0.16440 | 0.1183 | 1,138 |
| 5 | 3 | 0.29528 | 0.24382 | 0.1507 | 1,716 |
| 7 | 0 | 0.000371 | 0.000387 | 0.0024 | 0 |
| 7 | 1 | 0.003337 | 0.013857 | 0.0722 | 830 |
| 7 | 2 | 0.009252 | 0.061002 | 0.0964 | 1,711 |
| 7 | 3 | 0.018081 | 0.117720 | 0.1310 | 2,598 |

TV is the total-variation distance between the observed matching-bit distribution and the exact conditional history law; lower is better. In these examples, more rounds increase the raw matching-bit rate, but the conditional distribution gets more biased and the routed circuits get longer. At seven sites all three noisy matching rates after amplification are above the ideal values, so treating raw matches as valid quantum-amplified samples would be misleading. Zero CX gates at round zero does **not** imply a free experiment: preparation uses single-qubit gates and each shot still incurs measurement and execution costs.

`expected_routed_cx_per_raw_match = CX per circuit / noisy match probability` and the analogous SX quantity are included in the JSON as simple geometric expectations for repeated independent shots in the fixed model. These quantities do not include full wall time, one-qubit gates beyond the separately counted SX gates, input preparation effort, latency, calibration, fault tolerance, rejected-sample processing, or the cost of correcting biased conditional output. They are not a fair total-cost or speed comparison against a classical algorithm, and more biased matches are not equivalent to more accurate samples.

## Reproduce and verify

With Qiskit 2.6.1, Aer 0.18.2, NumPy and SciPy installed:

```bash
python -m unittest -v test_viability_cost_study.py
python viability_cost_study.py --sites 5 --rounds 0 1 2 3 --output viability_cost_n5_new.json
python viability_cost_study.py --sites 7 --rounds 0 1 2 3 --output viability_cost_n7_new.json
python plot_viability_cost.py
```

The study refuses to overwrite existing JSON. `plot_viability_cost.py` uses the saved `viability_cost_n5.json` and `viability_cost_n7.json`; it replaces only its own generated figure. The results record routed instruction counts, depth, placement, noisy conditional probabilities and software versions. Tests compare the classical closed form to exhaustive enumeration, test sampled histories, check every reported ideal round against the amplitude-amplification formula, and check the one-round circuit against the earlier implementation. The five-site one-round noisy probabilities independently match the previously saved density-pilot output.

Only one target, compiler seed and model family have been studied. The study does not compare the circuit fairly against optimized importance sampling on wall time or estimation accuracy and does not establish how these findings generalize to device hardware or realistic photolithography.
