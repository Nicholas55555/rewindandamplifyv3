import tempfile
import unittest
from pathlib import Path

import numpy as np

from assess_data import COLUMNS, assess, read_counts


class DataAssessmentTests(unittest.TestCase):
    def test_real_source_integrity_and_single_count_saturation(self):
        t, counts, md5 = read_counts()
        result = assess(t, counts, md5)
        self.assertEqual(len(t), 51421)
        self.assertEqual(result['channels']['Ch1']['number_zero'], 0)
        self.assertEqual(result['channels']['Ch1']['number_positive'], len(t))
        self.assertGreater(result['channels']['Coin_1234']['number_zero'], 0)
        self.assertLess(result['channels']['Coin_1234']['number_zero'], len(t))

    def test_invalid_header_and_nonmonotonic_times_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.csv'
            path.write_text('invalid,header\n0,1\n1,2\n', encoding='utf-8')
            with self.assertRaises(ValueError): read_counts(path, verify_checksum=False)
            header = ','.join(COLUMNS)
            row = ','.join(['0'] * 15)
            path.write_text(f'{header}\n2,{row}\n1,{row}\n', encoding='utf-8')
            with self.assertRaises(ValueError): read_counts(path, verify_checksum=False)

    def test_assessment_proportions(self):
        t = np.array([10., 11.1, 12.2])
        counts = np.zeros((3, 15))
        counts[:, 0] = [3, 0, 4]
        result = assess(t, counts, 'test')
        self.assertEqual(result['channels']['Ch1']['number_positive'], 2)
        self.assertAlmostEqual(result['channels']['Ch1']['fraction_positive'], 2/3)


if __name__ == '__main__':
    unittest.main()
