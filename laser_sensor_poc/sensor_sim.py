"""Synthetic qubit readout for a drifting laser pulse area; no hardware model."""
from pathlib import Path
import argparse
import json
import math
import numpy as np


SEED = 1945
N_TRIALS = 2000  # independent records under each equally likely hypothesis
RECORD_LENGTH = 128
SWITCH_PROB = 0.02
DELTA = 0.4  # radians about pi/2


def click_prob(theta):
    """Born probability of |1> after Ry(theta)|0>, with ideal readout."""
    return np.sin(np.asarray(theta) / 2.0) ** 2


def sample_record(rng, length, switch_prob, delta=DELTA):
    """Stationary binary hidden state and one reset/readout per time step."""
    if length < 1 or not 0 <= switch_prob <= 1:
        raise ValueError("length must be positive and switch probability in [0,1]")
    state = int(rng.integers(2))
    outcomes = np.empty(length, dtype=int)
    states = np.empty(length, dtype=int)
    p = click_prob(np.pi / 2 + np.array([-delta, delta]))
    for i in range(length):
        if i and rng.random() < switch_prob:
            state = 1 - state
        states[i] = state
        outcomes[i] = rng.random() < p[state]
    return states, outcomes


def hmm_log_likelihood(outcomes, switch_prob, delta=DELTA):
    """Exact forward likelihood with known parameters, scaled each step."""
    y = np.asarray(outcomes)
    if y.ndim != 1 or len(y) == 0 or not np.isin(y, [0, 1]).all():
        raise ValueError("outcomes must be a nonempty binary sequence")
    if not 0 <= switch_prob <= 1:
        raise ValueError("switch probability must be in [0,1]")
    p = click_prob(np.pi / 2 + np.array([-delta, delta]))
    transition = np.array([[1-switch_prob, switch_prob],
                           [switch_prob, 1-switch_prob]])
    alpha = np.array([0.5, 0.5])
    result = 0.0
    for i, observation in enumerate(y):
        if i:
            alpha = alpha @ transition
        alpha *= p if observation else 1-p
        scale = alpha.sum()
        if scale == 0:
            return -math.inf
        result += math.log(scale)
        alpha /= scale
    return result


def wilson(success, count):
    """Two-sided approximately 95% binomial Wilson interval."""
    z = 1.959963984540054
    q = success / count
    denom = 1 + z*z/count
    center = (q + z*z/(2*count)) / denom
    half = z * math.sqrt(q*(1-q)/count + z*z/(4*count*count)) / denom
    return [center-half, center+half]


def run(n_trials=N_TRIALS, record_length=RECORD_LENGTH, seed=SEED):
    rng = np.random.default_rng(seed)
    scores = {"persistent": [], "iid": []}
    rates = {"persistent": [], "iid": []}
    example = None
    for name, switch in [("persistent", SWITCH_PROB), ("iid", 0.5)]:
        for _ in range(n_trials):
            hidden, y = sample_record(rng, record_length, switch)
            if example is None:
                example = (hidden, y)
            scores[name].append(hmm_log_likelihood(y, SWITCH_PROB)
                                - hmm_log_likelihood(y, 0.5))
            rates[name].append(float(y.mean()))
    tp = sum(s > 0 for s in scores["persistent"])
    tn = sum(s <= 0 for s in scores["iid"])
    summary = {
        "seed": seed, "records_per_hypothesis": n_trials,
        "record_length": record_length, "angle_center_radians": math.pi/2,
        "angle_delta_radians": DELTA, "persistent_switch_probability": SWITCH_PROB,
        "iid_switch_probability": 0.5, "state_emission_probabilities": click_prob(
            np.pi/2 + np.array([-DELTA, DELTA])).tolist(),
        "decision": "persistent if exact log likelihood ratio > 0; iid otherwise",
        "persistent_correct": tp, "iid_correct": tn,
        "persistent_accuracy": tp/n_trials, "iid_accuracy": tn/n_trials,
        "persistent_accuracy_95pct_wilson": wilson(tp, n_trials),
        "iid_accuracy_95pct_wilson": wilson(tn, n_trials),
        "balanced_accuracy": (tp+tn)/(2*n_trials),
        "mean_readout_rate_persistent": float(np.mean(rates["persistent"])),
        "mean_readout_rate_iid": float(np.mean(rates["iid"])),
    }
    return summary, scores, example


def main():
    import matplotlib.pyplot as plt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="replace existing results")
    args = parser.parse_args()
    out = Path(__file__).parent
    targets = [out / "results.json", out / "laser_sensor_results.png"]
    if not args.overwrite and any(path.exists() for path in targets):
        raise FileExistsError("Result already exists; use --overwrite to replace it")
    summary, scores, (hidden, y) = run()
    (out / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    t = np.arange(len(y))
    axes[0].step(t, hidden, where="mid", label="Synthetic hidden drift", color="#af542c")
    axes[0].scatter(t, y, s=6, alpha=.32, label="Binary sensor readout", color="#19729d")
    axes[0].set(xlabel="Pulse index", ylabel="State / outcome", yticks=[0, 1],
                title="One simulated record (hidden state shown only for illustration)")
    axes[0].legend(loc="upper right")
    axes[1].hist(scores["persistent"], bins=45, alpha=.65, label="Persistent drift", color="#af542c")
    axes[1].hist(scores["iid"], bins=45, alpha=.65, label="Matched-rate IID", color="#19729d")
    axes[1].axvline(0, color="black", linestyle="--", label="Equal-prior decision")
    axes[1].set(xlabel="log P(record | persistent) - log P(record | IID)",
                ylabel="Number of records", title="Known-model likelihood ratio on independent records")
    axes[1].legend()
    fig.savefig(out / "laser_sensor_results.png", dpi=160)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
