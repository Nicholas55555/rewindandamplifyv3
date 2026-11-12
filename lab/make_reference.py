"""Write lab/reference.json: Qiskit-side numbers that lab/test_engine.cjs holds the JavaScript engine to.

Everything here comes from the original package in rewindandamplify-main/qrsm_grover, with no new physics:
Kraus operators from qiskit.quantum_info.Operator, history probabilities from the exact filter, and the
amplified hit rates and conditional errors from the package's own fast simulator.

    python lab/make_reference.py            # rewrite lab/reference.json
    python lab/make_reference.py --check    # fail if the checked-in file no longer matches the package
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rewindandamplify-main"))

import numpy as np  # noqa: E402

from qrsm_grover import QRSM, click_at  # noqa: E402
from qrsm_grover.amplify import steered_gamma  # noqa: E402
from qrsm_grover.classical import conditional_distribution, total_variation  # noqa: E402
from qrsm_grover.fastsim import FastPurified, light_distribution, reflection_qubits  # noqa: E402
from qrsm_grover.queries import exact_after_click  # noqa: E402

OUTPUT = HERE / "reference.json"
MODELS = {"with_hidden_defect": QRSM(), "no_hidden_defect": QRSM(phi=(), zeta=())}
T0, TAU = 3, 3


def build() -> dict:
    out = {"schema": 1,
           "source": "rewindandamplify-main/qrsm_grover (Qiskit Operator, exact filter and fastsim)",
           "event": {"selected_step": T0, "lags": list(range(1, TAU + 1))},
           "models": {}}
    for name, model in MODELS.items():
        kraus = [[[[float(v.real), float(v.imag)] for v in row] for row in K] for K in model.kraus()]
        mask = click_at(T0).mask(T0)
        probs = model.history_probabilities(T0)
        p = float(probs[mask].sum())
        steer = steered_gamma(p, model.gamma)
        gammas = [None] * (T0 - 1) + [steer]
        target = conditional_distribution(probs, mask)
        steered = {}
        for kind in ("full", "memory+last-1", "memory"):
            machine = FastPurified(model, T0, gammas=gammas)
            for r, state in machine.amplify(mask, 1, reflect_on=reflection_qubits(model, T0, kind)):
                if r == 1:
                    dist = light_distribution(state, T0, machine.dim)
                    steered[kind] = {"hit": float(dist[mask].sum()),
                                     "tv": total_variation(conditional_distribution(dist, mask), target)}
        exact = exact_after_click(model, T0, TAU)
        out["models"][name] = {
            "parameters": {"theta": model.theta, "gamma": model.gamma, "phi": list(model.phi), "zeta": list(model.zeta)},
            "kraus": kraus,
            "history_probabilities_T3": [float(v) for v in probs],
            "history_probabilities_T6": [float(v) for v in model.history_probabilities(T0 + TAU)],
            "click_probability": p,
            "plain_click_rates": [float(v) for v in exact["plain"]],
            "conditional_click_rates": [float(v) for v in exact["conditional"]],
            "steered_gamma": float(steer),
            "steered_event_probability": float(model.history_probabilities(T0, gammas=gammas)[mask].sum()),
            "steered_r1": steered,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare with the checked-in file instead of writing it")
    args = parser.parse_args()
    fresh = build()
    if args.check:
        saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
        worst = 0.0

        def walk(a, b, where=""):
            nonlocal worst
            if isinstance(a, dict):
                assert a.keys() == b.keys(), where
                for key in a:
                    walk(a[key], b[key], f"{where}/{key}")
            elif isinstance(a, list):
                assert len(a) == len(b), where
                for i, (x, y) in enumerate(zip(a, b)):
                    walk(x, y, f"{where}[{i}]")
            elif isinstance(a, float) or isinstance(b, float):
                worst = max(worst, abs(a - b))
                assert abs(a - b) < 1e-12, f"{where}: {a} != {b}"
            else:
                assert a == b, f"{where}: {a!r} != {b!r}"

        walk(fresh, saved)
        print(json.dumps({"status": "verified", "file": "lab/reference.json", "largest_difference": worst}))
    else:
        OUTPUT.write_text(json.dumps(fresh, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": "written", "file": "lab/reference.json", "models": len(fresh["models"])}))


if __name__ == "__main__":
    main()
