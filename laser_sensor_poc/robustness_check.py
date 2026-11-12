"""Held-out synthetic readout-noise stress test of a fixed HMM classifier."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from sensor_sim import (DELTA, RECORD_LENGTH, SWITCH_PROB, click_prob,
                        hmm_log_likelihood, sample_record, wilson)


SCENARIOS = [("ideal_control", 0.0), ("readout_flip_10pct", 0.10),
             ("readout_flip_25pct", 0.25)]
N_RECORDS = 1200  # per class and per scenario
BASE_SEED = 873104


def apply_bit_flips(rng, outcomes, flip_probability):
    """A symmetric binary readout channel, independent across readouts."""
    if not 0 <= flip_probability <= 1:
        raise ValueError("flip probability must be in [0,1]")
    y = np.asarray(outcomes)
    if y.ndim != 1 or not np.isin(y, [0, 1]).all():
        raise ValueError("outcomes must be a binary sequence")
    return np.bitwise_xor(y.astype(int), rng.random(len(y)) < flip_probability)


def pulse_area_probability(amplitude, duration):
    """Constant-drive area, in normalized units where coupling is one."""
    return float(click_prob(amplitude * duration))


def evaluate(n_records=N_RECORDS):
    if n_records < 1:
        raise ValueError("n_records must be positive")
    scenarios = []
    for index, (name, flip) in enumerate(SCENARIOS):
        # Independent reproducible streams by scenario; no fitting or retuning.
        seed = BASE_SEED + index
        rng = np.random.default_rng(seed)
        counts = {"persistent_positive": 0, "iid_positive": 0}
        mean = {}
        for label, switching in (("persistent", SWITCH_PROB), ("iid", .5)):
            readout_sum = 0
            for _ in range(n_records):
                _, y = sample_record(rng, RECORD_LENGTH, switching)
                y = apply_bit_flips(rng, y, flip)
                readout_sum += int(y.sum())
                # Fixed original ideal-readout likelihoods and zero threshold.
                llr = hmm_log_likelihood(y, SWITCH_PROB) - hmm_log_likelihood(y, .5)
                counts[label + "_positive"] += int(llr > 0)
            mean[label] = readout_sum / (n_records * RECORD_LENGTH)
        tp, fp = counts["persistent_positive"], counts["iid_positive"]
        scenarios.append({"name": name, "seed": seed,
                          "symmetric_readout_bit_flip_probability": flip,
                          "records_per_class": n_records,
                          "true_positive_count": tp, "false_positive_count": fp,
                          "true_positive_rate": tp / n_records,
                          "false_positive_rate": fp / n_records,
                          "true_positive_wilson_95pct": wilson(tp, n_records),
                          "false_positive_wilson_95pct": wilson(fp, n_records),
                          "sample_mean_readout": mean})
    pairs = [(math.pi/2, 1.0), (math.pi, 0.5), (math.pi/4, 2.0)]
    return {"record_length": RECORD_LENGTH, "angle_delta_radians": DELTA,
            "true_persistent_switch_probability": SWITCH_PROB,
            "true_iid_switch_probability": .5,
            "fixed_decision": "ideal known-model log-likelihood ratio > 0 means persistent",
            "models_retuned": False,
            "note": "Independent synthetic records; intervals conditional on scenario and known generative family.",
            "scenarios": scenarios,
            "equal_pulse_area_examples": [
                {"amplitude": a, "duration": t, "area": a*t,
                 "probability_one": pulse_area_probability(a, t)} for a, t in pairs]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).with_name("robustness_results.json")
    if path.exists() and not args.overwrite:
        raise FileExistsError("Result exists; use --overwrite to replace it")
    result = evaluate()
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
