"""Checks for the contact toy. No IBM account, no network: everything is recomputed from saved files."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "hardware_campaign"))

import analysis  # noqa: E402
import exposure  # noqa: E402
import forecast  # noqa: E402


def saved(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def given_a_failure(model: str, build: str) -> np.ndarray:
    """The outcome distribution of one circuit among the shots that carry the failure flag."""
    p = Statevector.from_instruction(exposure.circuit(model, build)).probabilities()
    flagged = ((np.arange(p.size) >> exposure.FLAG) & 1) == 1
    return p[flagged] / p[flagged].sum()


class TheModelByHand(unittest.TestCase):
    def test_bayes_rule_by_hand(self):
        """18% of cells are dark, a fifth of those fail: 3.6%. Five ninths of failures had a low dose."""
        t = exposure.truth("dose")
        self.assertAlmostEqual(t["neighbour_dark"], 0.18, places=12)
        self.assertAlmostEqual(t["fail"], 0.036, places=12)
        self.assertAlmostEqual(t["dose_low_given_fail"], 5 / 9, places=12)
        self.assertAlmostEqual(t["neighbour_dark_given_fail"], 29 / 90, places=12)

    def test_with_nothing_shared_a_failure_says_nothing_about_the_neighbour(self):
        t = exposure.truth("clean")
        self.assertAlmostEqual(t["fail"], exposure.truth("dose")["fail"], places=12)       # the same rare event
        self.assertAlmostEqual(t["neighbour_dark_given_fail"], t["neighbour_dark"], places=12)
        self.assertIsNone(t["dose_low_given_fail"])
        for build in exposure.BUILDS:                                                      # and its source qubit is never used
            p = Statevector.from_instruction(exposure.circuit("clean", build)).probabilities()
            self.assertLess(p[((np.arange(p.size) >> exposure.SOURCE) & 1) == 1].sum(), 1e-12)

    def test_every_circuit_gives_the_hand_answers_on_a_perfect_device(self):
        for model in exposure.MODELS:
            truth = exposure.truth(model)
            for build in exposure.BUILDS:
                got = exposure.ideal(model, build)
                for quantity in ("neighbour_dark_given_fail", "cell_dark_given_fail"):
                    self.assertAlmostEqual(got[quantity], truth[quantity], places=9, msg=f"{model}-{build} {quantity}")
                if model == "dose":
                    self.assertAlmostEqual(got["dose_low_given_fail"], truth["dose_low_given_fail"], places=9)
            # Only the plain circuit keeps the unflagged shots as they are, so only it shows how dark a typical cell is.
            self.assertAlmostEqual(exposure.ideal(model, "plain")["neighbour_dark"], truth["neighbour_dark"], places=9)

    def test_steering_and_rewinding_leave_the_failing_histories_alone(self):
        """Not only the two answers: the whole distribution among flagged shots is the same in all three builds."""
        for model in exposure.MODELS:
            plain = given_a_failure(model, "plain")
            np.testing.assert_allclose(given_a_failure(model, "steered"), plain, atol=1e-12)
            np.testing.assert_allclose(given_a_failure(model, "rewound"), plain, atol=1e-9)

    def test_what_each_move_does_to_the_rare_event(self):
        """Steering by five (0.2 to 1), then one round of amplification: sin^2(3 asin(sqrt(0.18)))."""
        for model in exposure.MODELS:
            self.assertAlmostEqual(exposure.ideal(model, "plain")["fail"], 0.036, places=12)
            self.assertAlmostEqual(exposure.ideal(model, "steered")["fail"], 0.18, places=12)
            self.assertAlmostEqual(exposure.ideal(model, "rewound")["fail"], np.sin(3 * np.arcsin(np.sqrt(0.18))) ** 2, places=9)
        self.assertAlmostEqual(exposure.ideal("dose", "rewound")["fail"], 0.9357, places=4)

    def test_counts_are_read_like_probabilities(self):
        p = Statevector.from_instruction(exposure.circuit("dose", "plain")).probabilities()
        rates = analysis.counted(np.round(p * 1e9), "dose")
        for quantity, value in exposure.answers(p, "dose").items():
            self.assertAlmostEqual(rates[quantity]["probability"], value, places=6, msg=quantity)
        self.assertIsNone(analysis.counted(np.round(p * 1e9), "clean")["dose_low_given_fail"])


class TheFrozenBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = saved("hardware_bundle/manifest.json")
        cls.predictions = saved("predictions.json")

    def test_the_campaign_tool_accepts_the_bundle(self):
        import campaign
        checked = campaign.verify_bundle(HERE / "hardware_bundle", self.manifest)
        self.assertIn("applied/contact/exposure.py", checked)
        self.assertIn("applied/contact/hardware_bundle/logical.qpy", checked)
        self.assertIn("rewindandamplify-main/qrsm_grover/amplify.py", checked)

    def test_the_bundle_is_what_the_builder_builds(self):
        built = exposure.experiments()
        self.assertEqual([item["name"] for item in built], [row["name"] for row in self.manifest["circuits"]])
        self.assertEqual(len(built), 8)
        self.assertEqual([row["num_qubits"] for row in self.manifest["circuits"]], [4] * 6 + [5, 7])
        for item, row in zip(built, self.manifest["circuits"]):
            self.assertEqual(item["metadata"], row["metadata"])
            self.assertEqual(item["reference"], row["reference"])

    def test_the_stored_exact_answers_are_the_hand_answers(self):
        stored = np.load(HERE / "hardware_bundle" / "ideal_probabilities.npz")
        for row in self.manifest["circuits"]:
            p = stored[row["ideal_probability_key"]]
            if row["metadata"]["kind"] == "echo":
                self.assertAlmostEqual(float(p[0]), 1.0, places=9)                    # an echo returns to zero
                continue
            got, truth = exposure.answers(p, row["metadata"]["model"]), row["reference"]["truth"]
            for quantity in ("neighbour_dark_given_fail", "cell_dark_given_fail", "dose_low_given_fail"):
                if truth[quantity] is not None:
                    self.assertAlmostEqual(got[quantity], truth[quantity], places=9, msg=f"{row['name']} {quantity}")

    def test_the_prediction_is_tied_to_the_frozen_files(self):
        for name, digest in self.predictions["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(set(self.predictions["rows"]), {row["name"] for row in self.manifest["circuits"]})
        self.assertTrue(self.predictions["made_before_the_job"])
        self.assertEqual(self.predictions["directions"], forecast.DIRECTIONS)
        self.assertEqual(set(self.predictions["claims"]["echo_scaled"]), set(forecast.CLAIMS))

    def test_the_compiled_circuits_are_small_and_still_exact(self):
        """On the assumed qubits: 6 two-qubit gates plain, 15 rewound. Without noise they give the hand answers."""
        rows = self.predictions["rows"]
        with open(forecast.ISA, "rb") as handle:
            compiled = qpy.load(handle)
        for row, isa in zip(self.manifest["circuits"], compiled):
            self.assertEqual(int(isa.count_ops().get("cz", 0)), rows[row["name"]]["two_qubit_gates"], row["name"])
        self.assertEqual([rows[f"dose-{build}"]["two_qubit_gates"] for build in exposure.BUILDS], [6, 5, 15])
        self.assertEqual([rows[f"clean-{build}"]["two_qubit_gates"] for build in exposure.BUILDS], [2, 1, 2])
        for key, value in self.predictions["claims"]["ideal"].items():
            if key.startswith("cause"):
                self.assertAlmostEqual(value, 5 / 9, places=9, msg=key)
            elif key.startswith("what follows"):
                self.assertAlmostEqual(value, 29 / 90 - 0.18, places=9, msg=key)
            elif key.startswith("check"):
                self.assertAlmostEqual(value, 1.0, places=9, msg=key)

    def test_the_prediction_expects_noise_to_cost_a_little_not_the_answer(self):
        """What was written down: every answer within eight points of the truth, and plain sampling the worst."""
        predicted, ideal = self.predictions["claims"]["echo_scaled"], self.predictions["claims"]["ideal"]
        for key in forecast.CLAIMS:
            if not key.startswith(("records", "check")):
                self.assertLess(abs(predicted[key] - ideal[key]), 0.08, key)
        cause = [predicted[f"cause: the dose was low, after a failure ({build})"] for build in exposure.BUILDS]
        self.assertEqual(cause, sorted(cause))                                            # plain < steered < rewound
        self.assertGreater(predicted["records: a failure is flagged, per shot (rewound)"],
                           20 * predicted["records: a failure is flagged, per shot (plain)"])

    def test_the_prediction_reproduces_from_its_saved_circuits(self):
        import study
        with open(forecast.ISA, "rb") as handle:
            compiled = qpy.load(handle)
        gap, where = study.worst_difference(forecast.build(compiled), self.predictions)
        self.assertLess(gap, 1e-6, where)

    def test_a_returned_job_is_read_against_its_prediction(self):
        """Feed the reader the exact distributions as if they were counts: it must give the exact answers back."""
        shots = 50_000_000
        stored = np.load(HERE / "hardware_bundle" / "ideal_probabilities.npz")
        rows = []
        for row in self.manifest["circuits"]:
            width = row["num_qubits"]
            whole = np.floor(stored[row["ideal_probability_key"]] * shots).astype(int)
            whole[int(np.argmax(whole))] += shots - whole.sum()
            rows.append({"kind": "science", "name": row["name"], "logical_qubits": width, "shots": shots, "gate_counts": {"cz": 1},
                         "counts": {format(i, f"0{width}b"): int(c) for i, c in enumerate(whole) if c}})
        rows.append({"kind": "calibration", "name": "cal_zero"})
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder) / "contact_test"
            folder.mkdir()
            (folder / "raw.json").write_text(json.dumps({"job_id": "none", "backend": "none", "retrieved_utc": "none",
                                                         "usage": 0, "rows": rows}), encoding="utf-8")
            (folder / "plan.json").write_text(json.dumps({"physical_patch": list(range(7))}), encoding="utf-8")
            fresh = analysis.job(folder)
        for key, claim in fresh["claims"].items():
            self.assertLess(abs(claim["measured"] - claim["exact"]), 2e-4, key)
            self.assertTrue(claim["exact_inside_interval"], key)
        # A perfect device has no false flags, so the fourth statement (rewound cleaner than plain) has nothing to show.
        self.assertEqual({key: direction["held"] for key, direction in fresh["directions"].items()},
                         {"cause": True, "what follows": True, "records": True, "check": False})
        self.assertAlmostEqual(fresh["flagged_shots_rewound_over_plain"]["ratio"], 0.9357 / 0.036, places=1)
        self.assertEqual(fresh["rows"]["echo-T3-x1"]["all_zero_return"]["successes"], shots)
        self.assertIsNone(analysis.job(Path("nowhere")))


class TheJobThatRan(unittest.TestCase):
    """The frozen job ran on IBM Marrakesh on 13 November 2026. These read its saved counts; nothing contacts IBM."""

    @classmethod
    def setUpClass(cls):
        cls.job = analysis.job()
        cls.predictions = saved("predictions.json")

    def test_the_counts_are_the_frozen_plan(self):
        folder = ROOT / "hardware_campaign" / "runs" / analysis.RUN
        plan, raw, job = (json.loads((folder / name).read_text(encoding="utf-8")) for name in ("plan.json", "raw.json", "job.json"))
        self.assertEqual(plan["bundle"], "applied/contact/hardware_bundle")
        self.assertEqual(raw["job_id"], job["job_id"])
        self.assertEqual(raw["status"], "DONE")
        self.assertFalse(raw["submitted_dry_run"])
        self.assertEqual(raw["plan_sha256"], hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest())
        self.assertEqual(plan["manifest_sha256"], self.predictions["sha256"]["applied/contact/hardware_bundle/manifest.json"])
        self.assertEqual(len([row for row in raw["rows"] if row["kind"] == "science"]), 8)
        self.assertEqual(len([row for row in raw["rows"] if row["kind"] == "calibration"]), 4)
        self.assertTrue(all(row["shots"] == 8192 for row in raw["rows"]))
        self.assertGreater(job["submitted_utc"], plan["created_utc"])
        self.assertEqual(self.job["physical_qubits"][:4], plan["physical_patch"][:4])

    def test_every_stated_direction_held(self):
        self.assertEqual({key: direction["held"] for key, direction in self.job["directions"].items()},
                         {"cause": True, "what follows": True, "records": True, "check": True})

    def test_most_predicted_sizes_missed_and_always_on_the_noisy_side(self):
        """Four of twelve predicted sizes are inside the measured intervals. Every miss is further from the truth than predicted."""
        claims = self.job["claims"]
        inside = [key for key, claim in claims.items() if claim["prediction_inside_interval"]]
        self.assertEqual(len(inside), 4)
        self.assertEqual(sum(key.startswith("what follows") for key in inside), 3)
        self.assertIn("check: the failed contact's own cell is dark (rewound)", inside)
        for key, claim in claims.items():
            if key not in inside:
                self.assertGreater(abs(claim["measured"] - claim["exact"]), abs(claim["predicted"] - claim["exact"]), key)

    def test_rewinding_reads_the_cause_closest_to_the_truth_and_still_short_of_it(self):
        cause = {build: self.job["rows"][f"dose-{build}"]["dose_low_given_fail"]["wilson95"] for build in exposure.BUILDS}
        self.assertGreater(cause["plain"][0], 0.2)                     # every record beats the 20% prior
        self.assertLess(cause["plain"][1], cause["steered"][0])
        self.assertLess(cause["steered"][1], cause["rewound"][0])
        self.assertLess(cause["rewound"][1], 5 / 9)                    # still biased: say so

    def test_the_neighbour_gap_comes_back_whole_while_each_level_reads_low(self):
        gap = self.job["claims"]["what follows: neighbour dark after a failure, shared source minus none (rewound)"]
        self.assertTrue(gap["exact_inside_interval"])
        self.assertGreater(gap["interval95"][0], 0.12)
        rows = self.job["rows"]
        self.assertLess(rows["dose-rewound"]["neighbour_dark_given_fail"]["wilson95"][1], 29 / 90)
        self.assertLess(rows["clean-rewound"]["neighbour_dark_given_fail"]["wilson95"][1], 0.18)

    def test_a_quarter_of_plain_failures_fail_the_models_own_check(self):
        rows = self.job["rows"]
        self.assertLess(rows["dose-plain"]["cell_dark_given_fail"]["wilson95"][1], 0.80)
        self.assertGreater(rows["dose-rewound"]["cell_dark_given_fail"]["wilson95"][0], 0.95)
        self.assertGreater(rows["dose-plain"]["fail"]["wilson95"][0], 0.05)        # flagged in over 5% of shots; the true rate is 3.6%
        self.assertGreater(rows["dose-rewound"]["fail"]["successes"], 14 * rows["dose-plain"]["fail"]["successes"])

    def test_the_check_bit_rescues_most_of_plain_sampling(self):
        """Looked at afterwards, and it cuts against the method: with the check as a filter, plain sampling's answer is
        no longer told apart from the rewound one. What is left is the number of records."""
        rows = self.job["filtered_by_the_check"]["rows"]
        plain, rewound = rows["dose-plain"]["dose_low"], rows["dose-rewound"]["dose_low"]
        self.assertGreater(plain["wilson95"][1], rewound["wilson95"][0])
        self.assertGreater(plain["probability"], self.job["rows"]["dose-plain"]["dose_low_given_fail"]["wilson95"][1])
        self.assertGreater(rewound["of"], 19 * plain["of"])

    def test_the_days_own_qubits_explain_plain_sampling_better_than_the_prediction_did(self):
        """Made after the job, so an explanation and not a prediction. It is still too hopeful about the rewound cause."""
        after = saved("results.json")["job"]["explained_afterwards"]
        self.assertTrue(after["made_after_the_job"])
        for key in ("records: a failure is flagged, per shot (plain)", "cause: the dose was low, after a failure (plain)",
                    "check: the failed contact's own cell is dark (plain)"):
            claim = self.job["claims"][key]
            self.assertLess(abs(after["claims"][key] - claim["measured"]), abs(claim["predicted"] - claim["measured"]), key)
        key = "cause: the dose was low, after a failure (rewound)"
        self.assertGreater(after["claims"][key], self.job["claims"][key]["interval95"][1])


class TheSavedResults(unittest.TestCase):
    def test_results_reproduce(self):
        gap, where, noisy_gap, noisy_where = analysis.compare(analysis.build(), saved("results.json"))
        self.assertLess(gap, 1e-9, where)
        self.assertLess(noisy_gap, 2e-3, noisy_where)


if __name__ == "__main__":
    unittest.main()
