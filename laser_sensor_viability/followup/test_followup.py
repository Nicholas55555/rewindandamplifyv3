"""Checks for causality, alarm accounting, independent calibration and controls."""
import json
from pathlib import Path
import unittest
import numpy as np
from run_followup import (Config, response_calibration, contrasts, first_alarms,
                          event_metrics, threshold_order, fit_models, score_series,
                          session_parameters, rng_for, seed, generate, hierarchical_ci)


class CausalDetectorTests(unittest.TestCase):
    def test_no_lookahead(self):
        rng = np.random.default_rng(83)
        x = rng.normal(size=(4, 128, 5))
        future_changed = x.copy(); future_changed[:, 80:] += 1e4
        a, b = contrasts(x, 16), contrasts(future_changed, 16)
        np.testing.assert_array_equal(a[:, :49], b[:, :49]) # endpoints32..80
        self.assertTrue(np.any(a[:, 49:] != b[:, 49:]))

    def test_step_appears_only_after_measurement_and_peaks_after_one_window(self):
        x = np.zeros((1, 128, 1)); x[:, 48:] = 1
        d = contrasts(x, 16)[0, :, 0]
        np.testing.assert_array_equal(d[:17], 0) # endpoints32..48
        self.assertEqual(d[17], 1/16) # first changed sample ends49
        self.assertEqual(d[32], 1.) # full changed window ends64
        self.assertEqual(d[48], 0.) # both windows changed at80

    def test_early_alarm_never_counts_as_detection(self):
        m = event_metrics(np.array([48, 49, 70, -1, 100]), np.full(5, 48), 32)
        np.testing.assert_array_equal(m["pre_onset_alarm"], [1, 0, 0, 0, 0])
        np.testing.assert_array_equal(m["detection_within_32s"], [0, 1, 1, 0, 0])
        np.testing.assert_array_equal(m["restricted_delay_s"], [32, 1, 22, 32, 32])

    def test_first_alarm_and_strict_threshold(self):
        s = {"a": np.array([[1, 2, 4], [0, 1, 2], [0, 0, 0.]])}
        np.testing.assert_array_equal(first_alarms(s, {"a": 2}, 16)["a"], [34, -1, -1])

    def test_maximum_calibration_controls_record_not_pointwise_false_alarms(self):
        rng = np.random.default_rng(48)
        cal = np.abs(rng.normal(size=(3000, 97)))
        test = np.abs(rng.normal(size=(5000, 97)))
        threshold = threshold_order(cal.max(axis=1), .05)
        record_fpr = np.mean(test.max(axis=1) > threshold)
        self.assertGreater(record_fpr, .03); self.assertLess(record_fpr, .07)
        pointwise_threshold = np.quantile(cal, .95)
        self.assertGreater(np.mean(test.max(axis=1) > pointwise_threshold), .98)

    def test_fusion_unit_response_and_agreement_veto(self):
        rng = np.random.default_rng(4)
        models = fit_models([rng.normal(size=(100, 20, 5))])
        for key, model in models.items():
            if key == "power_only" or key.endswith("agreement"): continue
            response = np.array([0 if c == 0 else 1 for c in model["columns"]])
            self.assertAlmostEqual(np.dot(model["weights"], response), 1)
        model = {"classical_quantum_agreement": {"columns": [2, 3], "center": [0, 0], "standard_deviation": [1, 2]}}
        x = np.zeros((1, 2, 5)); x[0, :, 2] = [3, 3]; x[0, :, 3] = [4, -4]
        np.testing.assert_array_equal(score_series(x, model)["classical_quantum_agreement"], [[2, 0]])

    def test_cluster_bootstrap_retains_pipeline_variation(self):
        cells = np.repeat(np.array([0., 0., 1., 1.])[:, None], 12, axis=1)
        ci = hierarchical_ci(cells, 51, 1000)
        self.assertLessEqual(ci[0], .25); self.assertGreaterEqual(ci[1], .75)


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads((Path(__file__).parent/"protocol.json").read_text())
        cls.c = Config()
        cls.response = response_calibration(cls.c, 9001, 16)
        cls.session = session_parameters(rng_for(108, 1), cls.c, cls.p)

    def test_frequency_event_does_not_change_power_observation(self):
        x0, h0 = generate(4, seed(68), self.c, self.response, self.session, self.p)
        x1, h1 = generate(4, seed(68), self.c, self.response, self.session, self.p, .5)
        np.testing.assert_array_equal(x0[:, :, 0], x1[:, :, 0])
        expected = .5*(np.arange(128)[None, :] >= h0["onset_cycle"][:, None])
        np.testing.assert_allclose(h1["source_frequency_hz"]-h0["source_frequency_hz"], expected, atol=1e-15)

    def test_onset_nuisance_independence_and_session_reproducibility(self):
        _, h = generate(100, seed(91), self.c, self.response, self.session, self.p)
        self.assertTrue(np.all((h["onset_cycle"] >= 48) & (h["onset_cycle"] <= 96)))
        self.assertTrue(np.any(h["onset_cycle"] != h["nuisance_onset_cycle"]))
        self.assertEqual(self.session, session_parameters(rng_for(108, 1), self.c, self.p))
        self.assertNotEqual(self.session, session_parameters(rng_for(108, 2), self.c, self.p))


if __name__ == "__main__": unittest.main()
