import itertools
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as m


class ScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = m.Parameters(n_cavity=2)

    def test_all_histories_normalize_for_latent_step_and_telegraph(self):
        bits = np.array(list(itertools.product([0, 1], repeat=4)), dtype=np.uint8)
        for kind in ('step', 'telegraph'):
            ll, prob = m.forward(bits, self.base, .2, kind, switch=.3, first=1, last=2)
            self.assertAlmostEqual(float(np.exp(ll[:, -1]).sum()), 1., places=11)
            self.assertTrue(np.all((prob >= -1e-12) & (prob <= 1+1e-12)))

    def test_forward_matches_explicit_source_path_marginalization(self):
        bits = np.array(list(itertools.product([0, 1], repeat=4)), dtype=np.uint8)
        for kind in ('step', 'telegraph'):
            actual = np.exp(m.forward(bits, self.base, .2, kind, switch=.3, first=1, last=2)[0][:, -1])
            expected = []
            for record in bits:
                total = 0.
                for path in itertools.product([0, 1], repeat=4):
                    weight = 1.
                    previous = 0
                    rho = m.init_state(self.base)
                    for t, (source, bit) in enumerate(zip(path, record)):
                        weight *= m.schedule_transition(kind, t, .3, 1, 2)[previous, source]
                        rho = m.maps(self.base, .2*source)[bit] @ rho
                        previous = source
                    total += weight*np.trace(rho.reshape((8, 8), order='F')).real
                expected.append(total)
            np.testing.assert_allclose(actual, expected, atol=2e-12)

    def test_step_retains_physical_state_instead_of_resetting(self):
        bits = np.zeros((1, 6), np.uint8)
        actual = np.exp(m.forward(bits, self.base, .2, 'step', first=3, last=3)[0][0, -1])
        rho0 = m.init_state(self.base)
        a, b = m.maps(self.base, 0.)[0], m.maps(self.base, .2)[0]
        first = np.linalg.matrix_power(a, 3) @ rho0
        trace = lambda r: np.trace(r.reshape((8, 8), order='F')).real
        retained = trace(np.linalg.matrix_power(b, 3) @ first)
        reset = trace(first)*trace(np.linalg.matrix_power(b, 3) @ rho0)
        self.assertAlmostEqual(actual, retained, places=12)
        self.assertGreater(abs(actual-reset), .01)

    def test_zero_drive_difference_has_identical_likelihood(self):
        bits = np.array([[0, 1, 0, 0, 1, 1], [0, 0, 1, 0, 0, 0]], np.uint8)
        a = m.forward(bits, self.base, 0., 'baseline')[0]
        for kind in ('step', 'telegraph'):
            b = m.forward(bits, self.base, 0., kind, first=1, last=2)[0]
            np.testing.assert_allclose(a, b, atol=1e-12)

    def test_afterpulse_readout_is_cause_mixture(self):
        no, yes, full = m.maps(self.base)
        q0, q1 = m.readout_maps(no, yes, True, afterpulse=.1)
        np.testing.assert_allclose(q0+q1, full, atol=1e-13)
        np.testing.assert_allclose(q1, yes+.1*no, atol=1e-13)
        rho = m.init_state(self.base)
        self.assertGreater(np.trace((q1@rho).reshape((8, 8), order='F')).real,
                           np.trace((yes@rho).reshape((8, 8), order='F')).real)

    def test_dead_time_blind_channel_and_forbidden_adjacent_bits(self):
        no, yes, full = m.maps(self.base)
        q0, q1 = m.readout_maps(no, yes, True, afterpulse=.1, dead=True)
        np.testing.assert_allclose(q0, full, atol=1e-13)
        self.assertEqual(np.linalg.norm(q1), 0.)
        sample = m.generate(self.base, 128, 64, 713, {'nuisance': {'dead_bins': 1}}, schedule_seed=714, nuisance_seed=715)
        records = sample['records']
        for row, onset in zip(records, sample['nuisance_onset']):
            self.assertFalse(np.any(row[onset-1:-1] & row[onset:]))

    def test_hmm_prefix_matches_bruteforce_paths(self):
        initial = np.array([.7, .3]); transition = np.array([[.8, .2], [.4, .6]]); emission = np.array([.1, .7])
        bits = np.array(list(itertools.product([0, 1], repeat=3)), np.uint8)
        actual = np.exp(m.hmm_prefix(bits, initial, transition, emission)[:, -1])
        expected = []
        for row in bits:
            total = 0.
            for path in itertools.product(range(2), repeat=3):
                p = initial[path[0]]
                for t, state in enumerate(path):
                    if t: p *= transition[path[t-1], state]
                    p *= emission[state] if row[t] else 1-emission[state]
                total += p
            expected.append(total)
        np.testing.assert_allclose(actual, expected, atol=1e-14)

    def test_threshold_strict_ties_conservative(self):
        samples = np.arange(100.)
        cut = m.threshold(samples)
        self.assertEqual(cut, 95.)
        self.assertEqual(np.sum(samples > cut), 4)
        self.assertEqual(np.sum(np.ones(100) > m.threshold(np.ones(100))), 0)

    def test_count_contrast_is_causal(self):
        records = np.zeros((1, 64), np.uint8); records[:, 32:] = 1
        score = m.count_contrast(records)
        self.assertTrue(np.all(score[0, :32] == 0))
        self.assertEqual(score[0, 47], 1.)
        altered = records.copy(); altered[:, 48:] = 0
        np.testing.assert_equal(m.count_contrast(altered)[:, :48], score[:, :48])

    def test_all_main_random_streams_have_unique_explicit_namespaces(self):
        import run_study as study
        table = study.all_seed_namespaces(study.MAIN, list(study.CASES))
        values = [item['seed'] for item in table]
        self.assertEqual(len(values), len(set(values)))
        self.assertGreater(len(values), 200)
        self.assertTrue(any('schedule' in x['purpose'] for x in table))
        self.assertTrue(any('nuisance' in x['purpose'] for x in table))
        self.assertEqual(table, study.all_seed_namespaces(study.MAIN, list(study.CASES)))


if __name__ == '__main__':
    unittest.main()
