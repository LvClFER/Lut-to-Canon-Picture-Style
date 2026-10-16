import unittest
from camera_install.compiler_regression import decode
from camera_install.payload_region_research import regions, prove_regions


class PayloadRegionTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(regions(8528), [(336, 4096), (4432, 4096)])
        self.assertEqual(regions(16752)[0], (368, 4096))
        self.assertEqual(regions(83076)[-1], (78980, 4096))
        self.assertEqual(regions(431616), [(372, 215622), (215994, 215622)])

    def test_full33_is_plain_not_xor(self):
        block = bytes([17]) * 215622
        observations = [dict(stage='compile', rc=0, property='1f03', callerRva='test', dataHex=block.hex())]
        proof = prove_regions(bytes(372) + block + bytes(215622), observations, (bytes(512), bytes(513)))
        self.assertEqual(proof['records'][0]['exactOutputRegions'], [dict(offset=372, seed=None)])

    def test_exact_and_missing_records(self):
        keys = (bytes(range(256)) * 2, bytes(range(256)) * 2 + b'\x01')
        block = bytes([123]) * 4096
        payload = bytes(336) + decode(block, keys, 0xb8ed) + bytes(4096)
        observations = [dict(stage='compile', rc=0, property='1022', callerRva='0x550eb', dataHex=block.hex()),
                        dict(stage='compile', rc=0, property='102a', callerRva='0x5510e', dataHex=bytes(4096).hex())]
        proof = prove_regions(payload, observations, keys)
        self.assertEqual(proof['records'][0]['exactOutputRegions'], [dict(offset=336, seed='0xb8ed')])
        self.assertEqual(proof['records'][1]['exactOutputRegions'], [])

    def test_no_false_unmapped_success(self):
        proof = prove_regions(bytes(100), [], (bytes(512), bytes(513)))
        self.assertFalse(proof['geometryMapped'])
        self.assertEqual(proof['records'], [])


if __name__ == '__main__':
    unittest.main()
