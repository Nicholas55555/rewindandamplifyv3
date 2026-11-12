"""Checks for the calibration-based noise simulation. Offline, about half a minute.

    python -m unittest discover -s hardware_campaign/noise_model -p "test_*.py" -v
"""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_study  # noqa: E402
from simulate import CAMPAIGN, ROOT, Run, apply_readout, compact, marginal, observables, simulate  # noqa: E402

RUN = Run.load(run_study.RUN)
SAVED = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
LOCAL, FULL = run_study.HERO["local"], run_study.HERO["full"]


class CompiledCircuits(unittest.TestCase):
    def test_noise_free_simulation_reproduces_the_stored_ideal_probabilities(self):
        ideal = np.load(ROOT / RUN.plan["bundle"] / "ideal_probabilities.npz", allow_pickle=False)
        for name in (LOCAL, FULL, "loop-defect-r1", "echo-T3-x1"):
            got = simulate(RUN, name, 0.0, None)
            want = ideal[RUN.manifest[name]["ideal_probability_key"]]
            self.assertLess(float(np.abs(got - want).max()), 1e-12, name)

    def test_compacting_keeps_every_gate_and_the_reported_gate_count(self):
        for name in (LOCAL, FULL):
            index, pub = RUN.pub(name)
            small, active, measured = compact(RUN.circuits[index])
            counts = small.count_ops()
            self.assertEqual(counts["cz"], pub["gate_counts"]["cz"])
            self.assertEqual(counts["sx"], pub["gate_counts"]["sx"])
            self.assertEqual(len(measured), pub["logical_qubits"])
            self.assertEqual(sorted(active), sorted(set(active)))
        self.assertEqual(RUN.pub(LOCAL)[1]["gate_counts"]["cz"], 58)
        self.assertEqual(RUN.pub(FULL)[1]["gate_counts"]["cz"], 125)


class Measurements(unittest.TestCase):
    def test_measured_observables_equal_the_campaign_analysis(self):
        analysis = json.loads((CAMPAIGN / "runs" / RUN.name / "analysis.json").read_text(encoding="utf-8"))
        rows = {row["name"]: row["observables"] for row in analysis["rows"]}
        for name in list(run_study.HERO.values()) + run_study.LOOPS:
            mine = observables(RUN, name, RUN.counts(name)[0])
            self.assertAlmostEqual(mine["hit_rate"], rows[name]["selected"]["probability"], places=12)
            self.assertAlmostEqual(mine["answer_error_tv"], rows[name]["selected_history_tv_to_unsteered_target"], places=9)
            if "later_click_rates" in mine:
                theirs = [f["raw_or_secondary_conditional"]["probability"] for f in rows[name]["future_clicks_after_selected_click"]]
                np.testing.assert_allclose(mine["later_click_rates"], theirs, atol=1e-12)
        self.assertEqual(round(observables(RUN, LOCAL, RUN.counts(LOCAL)[0])["hit_rate"] * 8192), 6300)
        self.assertEqual(round(observables(RUN, FULL, RUN.counts(FULL)[0])["hit_rate"] * 8192), 5674)

    def test_job_readout_errors_equal_the_campaign_calibration_estimates(self):
        analysis = json.loads((CAMPAIGN / "runs" / RUN.name / "analysis.json").read_text(encoding="utf-8"))
        for qubit, rates in analysis["calibration"]["independent_bit_error_estimates"].items():
            read1_given0, read0_given1 = RUN.readout_errors(int(qubit), "job")
            self.assertAlmostEqual(read1_given0, rates["e01"]["probability"], places=12)
            self.assertAlmostEqual(read0_given1, rates["e10"]["probability"], places=12)

    def test_readout_model_is_a_stochastic_map(self):
        qubits = RUN.pub(LOCAL)[1]["measurement_physical_qubits"]
        for start in range(4):
            p = np.zeros(1 << len(qubits)); p[start * 7 % p.size] = 1.0
            out = apply_readout(RUN, p, qubits)
            self.assertAlmostEqual(float(out.sum()), 1.0, places=12)
            self.assertTrue((out >= 0).all())
        # a perfect all-zeros state is misread on each bit at exactly that qubit's P(read 1 | prepared 0)
        zero = np.zeros(1 << len(qubits)); zero[0] = 1.0
        out = apply_readout(RUN, zero, qubits)
        for bit, qubit in enumerate(qubits):
            self.assertAlmostEqual(float(marginal(out, [bit])[1]), RUN.readout_errors(qubit)[0], places=12)


class Predictions(unittest.TestCase):
    def test_more_noise_never_helps_the_echo(self):
        returns = [observables(RUN, "echo-T3-x1", simulate(RUN, "echo-T3-x1", s))["all_zero_return"] for s in (0.5, 1.0, 2.0, 3.0)]
        self.assertEqual(returns, sorted(returns, reverse=True))

    def test_saved_featured_pair_matches_a_fresh_simulation(self):
        scale = SAVED["echo_fit"]["scale"]
        for key, name in run_study.HERO.items():
            fresh = observables(RUN, name, simulate(RUN, name, scale))
            saved = SAVED["featured_pair"][key]["echo_scaled"]
            self.assertAlmostEqual(fresh["hit_rate"], saved["hit_rate"], places=6)
            self.assertAlmostEqual(fresh["answer_error_tv"], saved["answer_error_tv"], places=6)

    def test_the_stated_conclusions_hold_in_the_saved_numbers(self):
        pair, gap = SAVED["featured_pair"], SAVED["hit_rate_gap_local_minus_full"]
        self.assertGreater(SAVED["echo_fit"]["scale"], 1.2)          # the device was noisier than its calibration said
        self.assertLess(SAVED["echo_fit"]["scale"], 2.2)
        for key in ("local", "full"):
            row = pair[key]
            # calibration alone is optimistic; the echo-fitted scale lands within 2 points of the measurement
            self.assertGreater(row["calibration"]["hit_rate"], row["measured"]["hit_rate"] + 0.04)
            self.assertLess(abs(row["echo_scaled"]["hit_rate"] - row["measured"]["hit_rate"]), 0.02)
            self.assertLess(row["echo_scaled"]["answer_error_tv"], row["measured"]["answer_error_tv"])
        # ideal circuits are tied; every noisy prediction and the hardware favour the lighter circuit
        self.assertLess(abs(gap["ideal"]), 0.01)
        for label in ("calibration", "echo_scaled", "measured"):
            self.assertGreater(gap[label], 0.05)
        # the lighter build's biased after-click answers are predicted in the right order and within one point
        loops = {row["circuit"]: row for row in SAVED["after_click"]}
        predicted = [loops[n]["echo_scaled"]["later_click_rates"][2] for n in ("loop-defect-r1", "loop-nodefect-r1")]
        measured = [loops[n]["measured"]["later_click_rates"][2] for n in ("loop-defect-r1", "loop-nodefect-r1")]
        self.assertLess(predicted[0], predicted[1]); self.assertLess(measured[0], measured[1])
        for p, m in zip(predicted, measured):
            self.assertLess(abs(p - m), 0.01)

    def test_saved_file_records_its_inputs(self):
        self.assertEqual(SAVED["job_id"], "dbqb1ifv5hds73dfo310")
        self.assertEqual(SAVED["backend"], "ibm_marrakesh")
        import hashlib
        for rel, digest in SAVED["source_sha256"].items():
            if rel.endswith(("simulate.py", "run_study.py")):
                continue                                             # these may be reformatted without changing numbers
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)


if __name__ == "__main__":
    unittest.main()
