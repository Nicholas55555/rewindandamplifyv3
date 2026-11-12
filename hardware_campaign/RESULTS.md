# Real hardware campaign results

10 completed IBM Marrakesh jobs executed 207 science circuits and 40 calibration circuits, totaling 688,640 shots and 244 charged QPU seconds. The campaign used superconducting qubits to emulate the specified models; it did not operate an optical sensor or inspect a wafer.

## Original QRSM: useful sampling with measurable answer error

The fresh 8192-shot precision follow-up reused the same compiled circuits and physical mapping. It was chosen after the initial results and is reported separately, with no cross-job pooling.

| Quantity | Steered local reflection | Steered full reflection |
|---|---:|---:|
| Raw accepted trials | 6300/8192 | 5674/8192 |
| Raw acceptance | 76.904% | 69.263% |
| Native two-qubit gates | 58 | 125 |
| Selected-history TV from unsteered target | 0.1177 | 0.1814 |

Local minus full acceptance was 7.642 percentage points, with an independent-shot 95% interval of [6.287, 8.993] points. The interval excludes drift, calibration uncertainty and model error. The lower-gate circuit returned more selected outcomes in this query; different operations, routing and drift remain confounders. The selected distribution still differed from the ideal answer.

The earlier plain run and the exact-ISA DD/twirling repeat are retained in results.json. Suppression did not improve the headline conditional-history errors. A better result is not selected by silently pooling or discarding jobs.

## After-click fingerprint

In the fresh local-loop repeat, the programmed defect and no-defect models gave step 6 click probabilities 0.08794 and 0.11661, versus ideal 0.04667 and 0.10102. Their raw difference was -2.867 percentage points [-3.893, -1.836]. The expected ordering is visible in this implementation, but the values remain biased; other loop implementations reverse the ordering. This is not a validated unknown-defect detector.

## Other families and failures

- Quantum-dot circuits prepare nonorthogonal photon-mode states and perform joint symmetry measurements digitally. Raw overlap and conditional-memory errors remain visible; the selected four-pair model uses a declared flag/memory marginal, not a full 29-qubit reference.
- Atomic Ramsey and photon-interferometer controls test physical channel/interference constructions. Photon loss, source failures, coherent vacuum and omitted photon-number tails stay charged. They do not repeat the complete laser monitoring or finite-budget phase-estimation studies.
- Correlated spatial circuits show why acceptance alone is unsafe: an apparent event-rate match can coexist with a wrong selected count-map distribution and severe computed-workspace leakage.
- Deep retained-instrument circuits are genuine negative stress tests. The two-bin all-click case accepts 8/512 trials, close to its 1.5466% ideal rate, yet its selected-data TV is 0.7604. Both three-bin all-click cases return zero selected trials, so no conditional answer is invented.
- Coverage extensions retain the independent-site contact models, real 16-entry semantic reader, explicitly nonsemantic 1024-entry cost benchmark, longer fixed-round QRSM histories and approximate bounded rewind. Full 7×7 construction exceeds available device width.

## Evidence and interpretation

The scoped [coverage inventory](coverage.md) records completed evidence for 18 of 25 identified families. This includes component executions and one related distinct model; it does not mean that every study or apparatus was reproduced. Shared circuits support multiple families, so family counts are not independent experiment counts.

Every job keeps its immutable plan, exact submitted ISA QPY, raw counts, metrics, physical measurement mapping and calibration controls. Current per-run analysis paths and hashes are listed in [results.json](results.json). Statistical intervals are marginal shot-based intervals; full-Z TV has an explicit finite-shot sampling benchmark. Secondary readout inversion assumes independent stationary errors and uses biased nonnegative projection, with no confidence-interval claim.

| Run | Science / calibration circuits | Shots per circuit | QPU seconds | Job ID |
|---|---:|---:|---:|---|
| dots_plain_v1 | 14 / 4 | 4096 | 22 | `dbqas3pabdes73fnu5n0` |
| dots_selected_plain_v1 | 4 / 4 | 4096 | 11 | `dbqb5e6jjaos73agvij0` |
| dots_suppressed_v1 | 14 / 4 | 4096 | 23 | `dbqav0habdes73fnuaf0` |
| extensions_plain_v1 | 25 / 4 | 2048 | 34 | `dbqb4vujjaos73agvhq0` |
| optical_controls_plain_v1 | 33 / 4 | 2048 | 22 | `dbqat8nv5hds73dfnsig` |
| optical_dilation_plain_v2 | 13 / 4 | 512 | 15 | `dbqavpfv5hds73dfo0cg` |
| original_plain_v2 | 43 / 4 | 2048 | 29 | `dbqarvmjjaos73agv2u0` |
| original_precision_v1 | 12 / 4 | 8192 | 38 | `dbqb1ifv5hds73dfo310` |
| original_suppressed_v1 | 43 / 4 | 2048 | 32 | `dbqauf9abdes73fnu9pg` |
| spatial_plain_v1 | 6 / 4 | 4096 | 18 | `dbqatdpabdes73fnu7r0` |

IBM job retrieval requires appropriate access through the [Workloads portal](https://quantum.cloud.ibm.com/workloads); the [official retrieval documentation](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/save-jobs) explains job IDs. Local evidence remains available without a live connection.
