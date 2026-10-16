import unittest

from camera_install.high_bank_roundtrip import compare_records


class HighBankRoundtripTests(unittest.TestCase):
    def test_banks_remain_independently_compared(self):
        before = {'0x1032': {'sha256': 'a'}, '0x9032': {'sha256': 'b'}}
        after = {'0x1032': {'sha256': 'a'}, '0x9032': {'sha256': 'c'}}
        self.assertEqual(compare_records(before, after), dict(removed=[], added=[], changed=['0x9032']))

    def test_missing_bank_is_not_a_scalar_change(self):
        self.assertEqual(compare_records({'0x9032': {}}, {}),
                         dict(removed=['0x9032'], added=[], changed=[]))
