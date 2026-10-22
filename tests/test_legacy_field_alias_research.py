import unittest
from camera_install.legacy_field_alias_research import swap32,check_aliases
from camera_install.compiler_regression import decode


class LegacyAliasTests(unittest.TestCase):
    def test_swap32_requires_aligned_input(self):
        self.assertEqual(swap32(b'abcdefgh'),b'dcbahgfe')
        with self.assertRaises(ValueError):
            swap32(b'abc')

    def test_aliases_in_both_observed_layouts(self):
        fields = {0x1018:b'abcd'*75,0x1029:b'efgh'*60}
        keys = (bytes(512),bytes(513))
        for size,offset in ((8164,0x600),(8168,0x700)):
            payload = bytearray(size)
            payload[offset:offset+300] = swap32(fields[0x1018])
            payload[offset+300:offset+540] = decode(swap32(fields[0x1029]),keys,0x3f194)
            result = check_aliases(payload,fields,keys)
            self.assertTrue(result['legacy1004EqualsSource1018'])
            self.assertTrue(result['legacy1005EqualsSource1029'])
            payload[offset+300] ^= 1
            self.assertFalse(check_aliases(payload,fields,keys)['legacy1005EqualsSource1029'])

    def test_reject_unknown_payload_layout(self):
        with self.assertRaises(ValueError):
            check_aliases(b'',{},(b'',b''))
