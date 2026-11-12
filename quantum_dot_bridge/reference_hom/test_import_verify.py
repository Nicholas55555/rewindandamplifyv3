"""Format/identity checks; no visibility or device validation is asserted."""
import unittest
from import_verify import HERE, FILES, audit, read_histogram, read_histogram_bytes


class ImportTests(unittest.TestCase):
    def test_all_six_source_bytes_and_axes_match_inventory(self):
        result=audit()
        self.assertEqual(len(result['files']),6)
        self.assertTrue(result['all_axes_identical'])
        self.assertTrue(all(x['md5_matches_zenodo'] for x in result['files']))

    def test_wrong_checksum_rejected(self):
        with self.assertRaisesRegex(ValueError,'MD5 mismatch'):
            read_histogram(HERE/FILES[0][0],'0'*32)

    def test_units_change_rejected(self):
        content=(HERE/FILES[0][0]).read_bytes().replace(b'Time (ps)',b'Time (ns)',1)
        with self.assertRaisesRegex(ValueError,'header or units'):
            read_histogram_bytes(content)

    def test_negative_count_and_shifted_grid_rejected(self):
        content=(HERE/FILES[0][0]).read_bytes()
        for original,replacement in [(b'-125000,4',b'-125000,-4'),(b'-125000,4',b'-124999,4')]:
            with self.assertRaises(ValueError):
                read_histogram_bytes(content.replace(original,replacement,1))

    def test_histograms_are_not_labeled_rates_or_sequences(self):
        result=audit()
        self.assertFalse(result['compatibility']['normalization_reproduced'])
        self.assertTrue(all(x['duration_seconds'] is None for x in result['files']))


if __name__=='__main__':
    unittest.main()
