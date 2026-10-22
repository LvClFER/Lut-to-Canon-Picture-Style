import struct
import unittest

from camera_install.compiler_regression import decode
from camera_install.legacy_source_inventory import inspect_source


class LegacySourceInventoryTests(unittest.TestCase):
    keys = (bytes(512), bytes(513))

    def fixture(self, payload=bytes(1460), corrupt_checksum=False):
        prefix = struct.pack('>HHI', 0x1007, 3, len(payload)) + payload
        checksum = sum(prefix) + int(corrupt_checksum)
        body = prefix + struct.pack('>HHII', 0xfffe, 4, 4, checksum)
        body += struct.pack('>HHI', 0xffff, 0xffff, 0)
        return bytes(4) + b'PSP\0' + struct.pack('>I', len(body)) + decode(body, self.keys, 12)

    def test_genuine_serialized_record_is_distinguished_from_api_alias(self):
        result = inspect_source(self.fixture(), self.keys)
        self.assertTrue(result['validated'])
        self.assertEqual(result['legacyRecords'][0]['id'], '0x1007')
        self.assertEqual(result['legacyRecords'][0]['size'], 1460)

    def test_damaged_checksum_does_not_validate_source(self):
        self.assertFalse(inspect_source(self.fixture(corrupt_checksum=True), self.keys)['validated'])

    def test_truncated_envelope_does_not_count_as_absent_legacy_record(self):
        result = inspect_source(self.fixture()[:-1], self.keys)
        self.assertFalse(result['validated'])
        self.assertEqual(result['reason'], 'body-size-mismatch')

    def test_pf2_without_checksum_keeps_structural_and_integrity_results_separate(self):
        body = struct.pack('>HHI', 0x1002, 2, 4) + b'test'
        body += struct.pack('>HHI', 0xffff, 0xffff, 0)
        raw = bytes.fromhex('00002000') + b'PSP\0' + struct.pack('>I',len(body))
        raw += decode(body,self.keys,12)
        result = inspect_source(raw,self.keys)
        self.assertTrue(result['structurallyDecoded'])
        self.assertFalse(result['checksumPresent'])
        self.assertFalse(result['validated'])

    def test_observed_pf2_2001_zero_trailer_is_retained_without_repair(self):
        body=struct.pack('>HHI',0xffff,0xffff,0)
        raw=bytes.fromhex('00002001')+b'PSP\0'+struct.pack('>I',len(body))
        raw+=decode(body+bytes(4),self.keys,12)
        result=inspect_source(raw,self.keys)
        self.assertTrue(result['structurallyDecoded'])
        self.assertEqual(result['envelopeTrailerDecodedHex'],'00000000')
        self.assertFalse(result['validated'])

    def test_high_bit_records_are_not_merged_with_counterpart(self):
        body=struct.pack('>HHIH',0x1009,3,2,0x84)
        body+=struct.pack('>HHIH',0x9009,3,2,0x81)
        body+=struct.pack('>HHII',0xfffe,4,4,sum(body))
        body+=struct.pack('>HHI',0xffff,0xffff,0)
        raw=bytes(4)+b'PSP\0'+struct.pack('>I',len(body))+decode(body,self.keys,12)
        result=inspect_source(raw,self.keys)
        self.assertTrue(result['validated'])
        self.assertIn('0x1009',result['recordIds'])
        self.assertIn('0x9009',result['recordIds'])
        self.assertEqual(result['highBitRecords'][0]['counterpartId'],'0x1009')
        pair=result['highBitCounterpartComparisons'][0]
        self.assertTrue(pair['counterpartPresent'])
        self.assertTrue(pair['sameType'])
        self.assertTrue(pair['sameSize'])
        self.assertFalse(pair['sameData'])


if __name__ == '__main__':
    unittest.main()
