import unittest

from camera_install.high_bank_research import byte_difference, compact_snapshots


class HighBankResearchTests(unittest.TestCase):
    def test_same_size_change_reports_exact_offsets(self):
        result = byte_difference(b'abcde', b'axcye')
        self.assertEqual(result['changedByteCount'], 2)
        self.assertEqual(result['firstChangedOffset'], 1)
        self.assertEqual(result['lastChangedOffset'], 3)
        self.assertFalse(result['identical'])

    def test_length_only_difference_is_not_identical(self):
        result = byte_difference(b'abc', b'abcd')
        self.assertFalse(result['sameSize'])
        self.assertFalse(result['identical'])
        self.assertEqual(result['changedByteCount'], 1)
        self.assertEqual(result['firstChangedOffset'], 3)

    def test_snapshot_hash_preserves_distinction_without_retaining_grid(self):
        result = {'before': {'40009011': {'dataHex': '01000000'}}}
        compact_snapshots(result)
        item = result['before']['40009011']
        self.assertNotIn('dataHex', item)
        self.assertEqual(item['prefixHex'], '01000000')
        self.assertEqual(len(item['sha256']), 64)
