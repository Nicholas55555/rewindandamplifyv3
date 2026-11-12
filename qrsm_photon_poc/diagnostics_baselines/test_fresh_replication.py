"""Checks for fresh-data replication and the rate-matched classical baseline."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

if __package__:
    from .fresh_replication import compare_seed, run, train_rate_matched_markov
    from .compare import markov_scores
else:
    from fresh_replication import compare_seed, run, train_rate_matched_markov
    from compare import markov_scores


class FreshReplicationTests(unittest.TestCase):
    def test_markov_stationary_rate_and_training_optimum(self):
        data = np.array([[0, 0, 1, 1, 1, 0], [0, 1, 0, 0, 1, 1],
                         [1, 1, 1, 0, 0, 0], [0, 0, 0, 1, 0, 1]], dtype=np.uint8)
        fit = train_rate_matched_markov(data)
        pi, matrix = fit['initial'], fit['transition']
        np.testing.assert_allclose(pi@matrix, pi, atol=1e-12)
        self.assertAlmostEqual(float(pi[1]), float(data.mean()))
        np.testing.assert_allclose(matrix.sum(axis=1), 1, atol=1e-12)
        self.assertAlmostEqual(fit['training_log_likelihood'], float(markov_scores(data,pi,matrix).sum()))

    def test_fresh_run_uses_independent_seeds_and_explicit_mismatch(self):
        result = compare_seed(99, n_train=12, n_test=6, bins=8, starts=2, max_iter=15, bootstrap=40)
        self.assertEqual((result['seed'],result['test_seed']), (99,1000099))
        self.assertNotEqual(result['train_binary_array_sha256'],result['test_binary_array_sha256'])
        self.assertEqual(len(result['per_record_log_likelihoods']),6)
        known = result['known_nuisance_fit']['fixed_nuisance']
        wrong = result['mismatched_nuisance_fit']['fixed_nuisance']
        self.assertEqual((known['detector_eta'], known['dark_rate']), (.68,.018))
        self.assertEqual((wrong['detector_eta'], wrong['dark_rate']), (.54,.035))
        self.assertNotIn('g_defect',known)
        self.assertEqual(result['paired_differences']['known_physical_minus_hmm3']['n_heldout_records'],6)

    def test_repeated_seeds_rejected(self):
        with self.assertRaises(ValueError):
            run([12,12],n_train=2,n_test=2,bins=2,starts=1,max_iter=1,bootstrap=2)

    def test_cli_works_with_windows_legacy_console_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'result.json'
            env=dict(os.environ, OPENBLAS_NUM_THREADS='1', PYTHONIOENCODING='cp1252')
            command=[sys.executable,'fresh_replication.py','--seeds','121','--train','12',
                     '--test','6','--bins','8','--starts','1','--max-iter','3',
                     '--bootstrap','20','--output',str(output)]
            completed=subprocess.run(command,cwd=Path(__file__).resolve().parent,env=env,
                                     text=True,capture_output=True,timeout=60)
            self.assertEqual(completed.returncode,0,completed.stderr)
            data=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(data['replicates']),1)


if __name__=='__main__':
    unittest.main()
