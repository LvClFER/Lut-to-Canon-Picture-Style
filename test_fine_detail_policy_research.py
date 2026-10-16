import struct
import unittest
from camera_install.fine_detail_policy_research import rejection_ids, require_base88


class FineDetailPolicyTests(unittest.TestCase):
    def test_base88_evidence_required(self):
        require_base88({'before': {'114': dict(rcGet=0, length=4, prefixHex='88000000')}})
        for row in ({}, {'before': {'114': dict(rcGet=0, length=4, prefixHex='84000000')}}):
            with self.assertRaises(ValueError):
                require_base88(row)

    def test_bounded_switch_mapping_and_explicit_ids(self):
        def reader(raw, address, size):
            if size == 8:
                return struct.pack('<2I', 0x100574c9, 0x100574c4)
            return bytes([1]) + bytes(size - 1)
        ids = rejection_ids(b'', reader)
        self.assertTrue({0x80000215, 0x80000250, 0x80000288, 0xc0000250} <= ids)
        self.assertNotIn(0x80000216, ids)

    def test_unknown_table_rejected(self):
        with self.assertRaises(ValueError):
            rejection_ids(b'', lambda raw, address, size: bytes(size))
