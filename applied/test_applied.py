"""Checks for the applied study. No IBM account, no network: everything is recomputed from saved files."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "hardware_campaign"))

import bundle  # noqa: E402
import study  # noqa: E402


def saved(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


class TheExactMachine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exact = study.exact()

    def test_the_main_projects_numbers_come_back(self):
        """The main result asks P(click at 6 | click at 3): 4.67% with the defect and 10.10% without."""
        self.assertAlmostEqual(self.exact["defect"]["truth"]["event"], 0.0395418, places=6)
        self.assertAlmostEqual(self.exact["defect"]["truth"]["after"][2], 0.0466750, places=6)
        self.assertAlmostEqual(self.exact["clean"]["truth"]["after"][2], 0.1010243, places=6)

    def test_a_pair_is_a_first_event_times_a_second(self):
        for machine in study.MACHINES:
            t = self.exact[machine]["truth"]
            self.assertAlmostEqual(t["pair"], t["event"] * t["another"], places=12)
            self.assertLessEqual(max(t["after"]), t["another"])
            self.assertLessEqual(t["another"], sum(t["after"]))

    def test_a_click_empties_the_emitter(self):
        """Emission resets the emitter, so after a real click it is never excited. Hardware can be held to this."""
        for machine in study.MACHINES:
            self.assertLess(self.exact[machine]["truth"]["emitter_after_event"], 1e-12)

    def test_with_nothing_hidden_a_click_restarts_the_machine(self):
        clean = study.MACHINES["clean"]
        start = clean.history_probabilities(study.WINDOW)
        from_scratch = [float(start[study.bit(np.arange(start.size), j)].sum()) for j in range(study.WINDOW)]
        np.testing.assert_allclose(self.exact["clean"]["truth"]["after"], from_scratch, atol=1e-12)

    def test_the_hidden_defect_makes_pairs_about_five_times_rarer(self):
        r = study.readings(self.exact)["chipmaking"]
        self.assertAlmostEqual(r["second_given_first"]["defect"], 0.0849952, places=6)
        self.assertAlmostEqual(r["second_given_first"]["clean"], 0.1736970, places=6)
        self.assertAlmostEqual(r["defect_makes_pairs_rarer_by"], 5.2212, places=3)
        self.assertAlmostEqual(r["defect_holds_the_energy"]["after_a_photon"], 0.0846427, places=6)
        self.assertAlmostEqual(r["defect_holds_the_energy"]["typically"], 0.2927065, places=6)

    def test_rewinding_keeps_the_answers_on_a_perfect_device(self):
        """The circuits' own bias, before any noise: under a quarter of a point on every answer."""
        for machine in study.MACHINES:
            truth, circuits = self.exact[machine]["truth"], self.exact[machine]["ideal_circuits"]
            self.assertGreater(circuits["window"]["rewound"]["event"], 0.96)
            self.assertLess(abs(circuits["window"]["rewound"]["another"] - truth["another"]), 0.001)
            np.testing.assert_allclose(circuits["window"]["rewound"]["after"], truth["after"], atol=0.001)
            self.assertAlmostEqual(circuits["window"]["plain"]["another"], truth["another"], places=10)
            if machine != "clean":
                self.assertLess(abs(circuits["cause"]["rewound"]["defect_after_event"] - truth["defect_after_event"]), 0.0025)

    def test_a_frequency_step_moves_the_record(self):
        lasers = study.readings(self.exact)["lasers"]
        self.assertAlmostEqual(lasers["second_given_first"]["after"] - lasers["second_given_first"]["before"], 0.0571976, places=6)
        self.assertEqual(lasers["records_needed_per_side"], 797)
        self.assertGreater(lasers["model_runs_needed"]["plain"], 20 * lasers["model_runs_needed"]["rewound"])
        zetas = [row["zeta"] for row in lasers["sweep"]]
        self.assertEqual(zetas, sorted(zetas))


class TheSavedIbmRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ibm = study.ibm()
        cls.campaign = json.loads((ROOT / "hardware_campaign" / "results.json").read_text(encoding="utf-8"))

    def test_the_recount_agrees_with_the_campaigns_own_analysis(self):
        curves = self.campaign["afterclick_precision"]["curves"]
        for circuit, key in (("loop-defect-r1", "window/defect/rewound"), ("loop-defect-r0", "window/defect/plain"),
                             ("loop-nodefect-r1", "window/clean/rewound"), ("loop-nodefect-r0", "window/clean/plain")):
            row = self.ibm["rows"][key]
            self.assertEqual(row["event"]["successes"], curves[circuit]["selected"]["successes"])
            for mine, theirs in zip(row["after"], curves[circuit]["future"]):
                self.assertEqual(mine["successes"], theirs["raw_or_secondary_conditional"]["successes"])
        hero = self.campaign["headline_original"]["local"]
        self.assertEqual(self.ibm["rows"]["cause/defect/rewound"]["event"]["successes"], hero["accepted"])
        self.assertEqual(self.ibm["rows"]["cause/defect/rewound"]["two_qubit_gates"], hero["native_two_qubit_gates"])

    def test_plain_sampling_gets_the_order_backwards_and_rewinding_gets_it_right(self):
        """Truth: a second event is likelier with nothing hidden. Both intervals exclude zero, on opposite sides."""
        plain = self.ibm["clean_minus_defect_another"]["plain"]["interval95"]
        rewound = self.ibm["clean_minus_defect_another"]["rewound"]["interval95"]
        self.assertLess(plain[1], 0)
        self.assertGreater(rewound[0], 0)

    def test_rewinding_gives_ten_times_the_records_and_cleaner_ones(self):
        rows = self.ibm["rows"]
        self.assertGreater(rows["window/defect/rewound"]["event"]["successes"], 9 * rows["window/defect/plain"]["event"]["successes"])
        self.assertLess(rows["cause/defect/rewound"]["emitter_after_event"]["probability"], 0.05)
        self.assertGreater(rows["cause/defect/plain"]["emitter_after_event"]["probability"], 0.2)

    def test_three_steps_after_a_click_g2_agrees_with_the_exact_value(self):
        exact = study.exact()
        for machine in ("defect", "clean"):
            low, high = self.ibm["g2"][machine][2]["interval95"]
            self.assertLess(low, exact[machine]["truth"]["g2"][2])
            self.assertGreater(high, exact[machine]["truth"]["g2"][2])
        self.assertLess(self.ibm["g2"]["defect"][2]["interval95"][1], self.ibm["g2"]["clean"][2]["interval95"][0])

    def test_intervals(self):
        low, high = study.wilson(50, 100)
        self.assertAlmostEqual(low, 0.4038, places=3)
        self.assertAlmostEqual(high, 0.5962, places=3)
        same = study.difference(study.rate(50, 100), study.rate(50, 100))
        self.assertAlmostEqual(same["difference"], 0.0)
        self.assertLess(same["interval95"][0], 0)
        self.assertGreater(same["interval95"][1], 0)
        self.assertAlmostEqual(study.ratio(study.rate(50, 100), study.rate(25, 100))["ratio"], 2.0)


class TheFrozenJob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = saved("hardware_bundle/manifest.json")
        cls.predictions = saved("predictions.json")

    def test_the_campaign_tool_accepts_the_bundle(self):
        import campaign
        checked = campaign.verify_bundle(HERE / "hardware_bundle", self.manifest)
        self.assertIn("applied/bundle.py", checked)
        self.assertIn("applied/hardware_bundle/logical.qpy", checked)

    def test_the_bundle_is_what_the_builder_builds(self):
        built = bundle.experiments()
        self.assertEqual([item["name"] for item in built], [row["name"] for row in self.manifest["circuits"]])
        self.assertEqual(len(built), 13)
        self.assertEqual(max(row["num_qubits"] for row in self.manifest["circuits"]), 8)
        for item, row in zip(built, self.manifest["circuits"]):
            self.assertEqual(item["metadata"], row["metadata"])
            self.assertEqual(item["reference"], row["reference"])

    def test_stored_exact_answers_match_the_study(self):
        exact = study.exact()
        stored = np.load(HERE / "hardware_bundle" / "ideal_probabilities.npz")
        for row in self.manifest["circuits"]:
            meta, reference = row["metadata"], row["reference"]
            if meta["kind"] != "applied":
                self.assertAlmostEqual(float(stored[row["ideal_probability_key"]][0]), 1.0, places=9)   # an echo returns to zero
                continue
            got = study.answers(study.tally(stored[row["ideal_probability_key"]], reference["chronological_history_qubits"],
                                            reference["memory_qubits"], meta["tau"]))
            want = exact[meta["machine"]]["ideal_circuits"][meta["reading"]][meta["how"]]
            gap, where = study.worst_difference(got, want)
            self.assertLess(gap, 1e-9, f"{row['name']}: {where}")

    def test_predictions_are_tied_to_the_frozen_files(self):
        import hashlib
        for name, digest in self.predictions["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(set(self.predictions["rows"]), {row["name"] for row in self.manifest["circuits"]})
        self.assertTrue(self.predictions["made_before_the_job"])

    def test_the_predicted_job_keeps_the_campaigns_gate_counts(self):
        """Same qubits, same compiler settings: the two circuits that ran on 11 November compile to the same size."""
        rows = self.predictions["rows"]
        self.assertEqual(rows["site-defect-rewound"]["two_qubit_gates"], 58)
        self.assertEqual(rows["window-defect-rewound"]["two_qubit_gates"], 98)
        self.assertEqual(rows["window-clean-rewound"]["two_qubit_gates"], 32)

    def test_the_noise_model_already_explains_the_saved_answers(self):
        """Not fitted to them, and within three points on every answer the rewound circuits gave."""
        results = saved("results.json")
        for key in ("window/defect/rewound", "window/clean/rewound"):
            self.assertLess(abs(results["noise_model"]["rows"][key]["another"] - results["ibm"]["rows"][key]["another"]["probability"]), 0.03)
        key = "cause/defect/rewound"
        self.assertLess(abs(results["noise_model"]["rows"][key]["defect_after_event"]
                            - results["ibm"]["rows"][key]["defect_after_event"]["probability"]), 0.03)

    def test_a_returned_job_is_read_against_its_predictions(self):
        """Feed the reader the exact distributions as if they were counts: it must give the exact answers back."""
        shots = 50_000_000
        rows = []
        for row in self.manifest["circuits"]:
            width = row["num_qubits"]
            if row["metadata"]["kind"] == "echo":
                counts = {"0" * width: shots}
            else:
                # the exact distribution keeps this test free of the simulator
                p = np.load(HERE / "hardware_bundle" / "ideal_probabilities.npz")[row["ideal_probability_key"]]
                whole = np.floor(p * shots).astype(int)
                whole[int(np.argmax(whole))] += shots - whole.sum()
                counts = {format(i, f"0{width}b"): int(c) for i, c in enumerate(whole) if c}
            rows.append({"kind": "science", "name": row["name"], "logical_qubits": width, "shots": shots,
                         "gate_counts": {"cz": 1}, "counts": counts})
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder) / "applied_test"
            folder.mkdir()
            (folder / "raw.json").write_text(json.dumps({"job_id": "none", "backend": "none", "retrieved_utc": "none",
                                                         "usage": 0, "rows": rows}), encoding="utf-8")
            (folder / "plan.json").write_text(json.dumps({"physical_patch": list(range(8))}), encoding="utf-8")
            fresh = study.new_job(folder)
        for key, value in fresh["comparisons"].items():
            self.assertLess(abs(value["difference"] - value["exact"]), 2e-4, key)
            self.assertIn("predicted", value)
        self.assertEqual(set(fresh["g2"]), {"defect", "clean", "stepped"})
        self.assertIsNone(study.new_job(Path("nowhere")))


class TheJobThatRan(unittest.TestCase):
    """The frozen job ran on IBM Marrakesh on 12 November 2026. These read its saved counts; nothing contacts IBM."""

    @classmethod
    def setUpClass(cls):
        cls.job = study.new_job()
        cls.predictions = saved("predictions.json")

    def test_the_counts_are_the_frozen_plan(self):
        folder = ROOT / "hardware_campaign" / "runs" / study.NEW_RUN
        plan, raw, job = (json.loads((folder / name).read_text(encoding="utf-8")) for name in ("plan.json", "raw.json", "job.json"))
        self.assertEqual(plan["bundle"], "applied/hardware_bundle")
        self.assertEqual(raw["job_id"], job["job_id"])
        self.assertEqual(raw["status"], "DONE")
        self.assertFalse(raw["submitted_dry_run"])
        import hashlib
        self.assertEqual(raw["plan_sha256"], hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest())
        self.assertEqual(plan["manifest_sha256"], self.predictions["sha256"]["applied/hardware_bundle/manifest.json"])
        science = [row for row in raw["rows"] if row["kind"] == "science"]
        self.assertEqual(len(science), 13)
        self.assertTrue(all(row["shots"] == 8192 for row in raw["rows"]))
        self.assertGreater(job["submitted_utc"], plan["created_utc"])

    def test_every_predicted_direction_held(self):
        for key, value in self.job["comparisons"].items():
            low, high = value["interval95"]
            inside = low <= value["predicted"] <= high
            self.assertTrue(inside or value["predicted"] * value["difference"] > 0, key)

    def test_rewinding_has_the_chip_answer_the_right_way_round_again(self):
        rewound = self.job["comparisons"]["chipmaking: second event, clean minus defect (rewound)"]
        plain = self.job["comparisons"]["chipmaking: second event, clean minus defect (plain)"]
        self.assertGreater(rewound["interval95"][0], 0)
        self.assertLess(plain["interval95"][1], 0)
        self.assertLess(plain["predicted"], 0)                  # backwards, as the noise model said it would be

    def test_the_frequency_step_is_seen_and_was_predicted(self):
        step = self.job["comparisons"]["lasers: second event, stepped minus defect (rewound)"]
        self.assertGreater(step["interval95"][0], 0)
        self.assertLess(step["interval95"][0], step["predicted"])
        self.assertLess(step["predicted"], step["interval95"][1])
        plain = self.job["comparisons"]["lasers: second event, stepped minus defect (plain)"]
        self.assertLess(plain["interval95"][0], 0)              # plain sampling cannot tell the step from nothing
        self.assertGreater(plain["interval95"][1], 0)

    def test_the_cause_reading_moves_towards_the_truth(self):
        exact = study.exact()["defect"]["truth"]
        plain, rewound = (self.job["cause"][how]["measured"] for how in ("plain", "rewound"))
        self.assertLess(rewound["wilson95"][1], plain["wilson95"][0])
        self.assertLess(exact["defect_after_event"], rewound["wilson95"][0])     # still biased: say so
        self.assertLess(rewound["wilson95"][1], exact["defect_typical"])

    def test_what_did_not_replicate_is_on_record(self):
        """Three steps after a click, g2 told the two machines apart on 11 November and did not on 12 November."""
        old, new = study.ibm()["g2"], self.job["g2"]
        self.assertLess(old["defect"][2]["interval95"][1], old["clean"][2]["interval95"][0])
        self.assertGreater(new["defect"][2]["interval95"][1], new["clean"][2]["interval95"][0])
        for run in (old, new):                                   # one step after, the order is right in both runs
            self.assertGreater(run["defect"][0]["ratio"], run["clean"][0]["ratio"])
            for machine in ("defect", "clean"):                  # and a second photon is always less likely than usual
                self.assertTrue(all(g["interval95"][1] < 1 for g in run[machine]))


class TheSavedResults(unittest.TestCase):
    def test_results_reproduce(self):
        gap, where, noisy_gap, noisy_where = study.compare(study.build(), saved("results.json"))
        self.assertLess(gap, 1e-9, where)
        self.assertLess(noisy_gap, 2e-3, noisy_where)

    def test_predictions_reproduce_from_their_saved_circuits(self):
        import predict
        from qiskit import qpy
        with open(predict.ISA, "rb") as handle:
            compiled = qpy.load(handle)
        gap, where = study.worst_difference(predict.build(compiled), saved("predictions.json"))
        self.assertLess(gap, 1e-6, where)


if __name__ == "__main__":
    unittest.main()
