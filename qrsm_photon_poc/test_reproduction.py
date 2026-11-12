"""Tests for safe, consistent command-line reproduction and record provenance."""
import inspect
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

import numpy as np

import evaluate
import experiment
from qrsm_photon import Parameters, sample_records


class ReproductionTests(unittest.TestCase):
    def test_default_run_matches_documented_full_configuration(self):
        params=inspect.signature(experiment.run).parameters
        self.assertEqual((params['n_records'].default, params['steps'].default,
                          params['seed'].default), (600, 40, 77))

    def test_bundled_seeded_records_match(self):
        path=Path(__file__).resolve().parent/'synthetic_click_records.csv'
        expected=np.loadtxt(path,delimiter=',',dtype=np.uint8,ndmin=2)
        sampled=sample_records(Parameters(),n_records=600,steps=40,seed=77)
        np.testing.assert_array_equal(sampled,expected)

    def test_output_guards_preserve_reference_and_existing_data(self):
        with self.assertRaises(ValueError):
            experiment.prepare_output(experiment.ROOT,True)
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'run'
            out.mkdir()
            result=out/'results.json'
            result.write_text('keep',encoding='utf-8')
            with self.assertRaises(FileExistsError):
                experiment.prepare_output(out,False)
            self.assertEqual(result.read_text(encoding='utf-8'),'keep')

    def test_evaluator_rejects_nonbinary_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)
            (out/'synthetic_click_records.csv').write_text('0,1\n1,0\n0.5,1\n1,1\n',encoding='utf-8')
            with self.assertRaises(ValueError):
                evaluate.run(data_dir=out)
            self.assertFalse((out/'heldout_evaluation.json').exists())

    def test_generated_evaluation_records_input_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)
            records=out/'synthetic_click_records.csv'
            records.write_text('0,1\n1,0\n0,0\n1,1\n',encoding='utf-8')
            with redirect_stdout(io.StringIO()):
                evaluate.run(data_dir=out)
            result=json.loads((out/'heldout_evaluation.json').read_text(encoding='utf-8'))
            self.assertEqual(result['input_records_sha256'],hashlib.sha256(records.read_bytes()).hexdigest())


if __name__=='__main__':
    unittest.main()
