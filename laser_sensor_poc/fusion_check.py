"""Synthetic complementary readouts classified with a matched classical HMM."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from sensor_sim import DELTA, RECORD_LENGTH, SWITCH_PROB, click_prob, sample_record, wilson


SEED = 540072
N_RECORDS = 1200  # independent records per class, shared across sensor comparisons
P_QUBIT = click_prob(np.pi/2 + np.array([-DELTA, DELTA]))
P_CLASSICAL = np.array([.35, .65])  # hypothetical, uncalibrated response


def log_likelihood(readouts, probs, switch_probability):
    """Known-model HMM; sensors are independent conditional on each hidden state.

    readouts shape (time, sensors), probs shape (sensors, two hidden states).
    The hidden state is shared between sensors in both hypotheses, even when
    switching probability is .5 and hidden states are independent over time.
    """
    y = np.asarray(readouts)
    p = np.asarray(probs, dtype=float)
    if (y.ndim != 2 or not y.shape[0] or p.shape != (y.shape[1], 2)
            or not np.isin(y, [0, 1]).all() or not np.isfinite(p).all()
            or np.any((p < 0) | (p > 1)) or not 0 <= switch_probability <= 1):
        raise ValueError("invalid observations, emission probabilities or switching probability")
    alpha = np.array([.5, .5])
    trans = np.array([[1-switch_probability, switch_probability],
                      [switch_probability, 1-switch_probability]])
    total = 0.
    for i, row in enumerate(y):
        if i:
            alpha = alpha @ trans
        alpha *= np.prod(np.where(row[:, None] == 1, p, 1-p), axis=0)
        scale = float(alpha.sum())
        if scale == 0:
            return -math.inf
        total += math.log(scale)
        alpha /= scale
    return total


def sample_pair(rng, switch_probability, length=RECORD_LENGTH):
    """A shared hidden path, a reset qubit and a hypothetical classical readout."""
    states, q = sample_record(rng, length, switch_probability)
    c = (rng.random(length) < P_CLASSICAL[states]).astype(int)
    return states, np.column_stack((q, c))


def evaluate(n_records=N_RECORDS, seed=SEED):
    if n_records < 1:
        raise ValueError("n_records must be positive")
    designs = {"qubit_only": ([0], P_QUBIT[None, :]),
               "classical_only": ([1], P_CLASSICAL[None, :]),
               "joint": ([0, 1], np.stack([P_QUBIT, P_CLASSICAL]))}
    positive = {name: {"persistent": 0, "iid": 0} for name in designs}
    rate_sum = {"persistent": np.zeros(2), "iid": np.zeros(2)}
    streams = np.random.SeedSequence(seed).spawn(2)
    for label, switch, child in zip(("persistent", "iid"), (SWITCH_PROB, .5), streams):
        rng = np.random.default_rng(child)
        for _ in range(n_records):
            _, observations = sample_pair(rng, switch)
            rate_sum[label] += observations.mean(axis=0)
            for name, (columns, probs) in designs.items():
                y = observations[:, columns]
                llr = log_likelihood(y, probs, SWITCH_PROB) - log_likelihood(y, probs, .5)
                positive[name][label] += int(llr > 0)
    tests = {}
    for name, counts in positive.items():
        tp, fp = counts["persistent"], counts["iid"]
        tests[name] = {"true_positive_count": tp, "false_positive_count": fp,
                       "true_positive_rate": tp/n_records,
                       "false_positive_rate": fp/n_records,
                       "true_positive_wilson_95pct": wilson(tp, n_records),
                       "false_positive_wilson_95pct": wilson(fp, n_records)}
    return {"seed": seed, "records_per_hypothesis": n_records,
            "record_length": RECORD_LENGTH,
            "true_switch_probability_persistent": SWITCH_PROB,
            "true_switch_probability_iid": .5,
            "qubit_state_click_probabilities": P_QUBIT.tolist(),
            "classical_state_click_probabilities": P_CLASSICAL.tolist(),
            "same_records_for_all_sensor_comparisons": True,
            "independence_assumption": "readouts independent conditional on shared hidden state",
            "classifier": "matched known-parameter classical HMM, no fitting, fixed equal-prior zero LLR threshold",
            "mean_observed_readout_by_class_qubit_then_classical": {
                label: (rates/n_records).tolist() for label, rates in rate_sum.items()},
            "hypothesis_results": tests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).with_name("fusion_results.json")
    if path.exists() and not args.overwrite:
        raise FileExistsError("Result exists; use --overwrite to replace it")
    result = evaluate()
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
