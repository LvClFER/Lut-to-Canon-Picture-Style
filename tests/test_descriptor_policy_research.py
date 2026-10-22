import struct
import unittest
from camera_install.descriptor_policy_research import policy_ids


class DescriptorPolicyTests(unittest.TestCase):
    def test_jump_tables_select_only_explicit_small_targets(self):
        def read(_,rva,size):
            if size==8: return struct.pack('<2I',0x1004c488,0x1004c491)
            return bytes([1])+bytes(size-1)
        result=policy_ids(b'',read)
        for identifier in (0x80000215,0x80000250,0x80000288,0x80000404):
            self.assertIn(identifier,result)
        self.assertNotIn(0x80000216,result)
        self.assertNotIn(1042,result)

    def test_unknown_jump_target_is_rejected(self):
        def read(_,rva,size):
            return struct.pack('<2I',0,1) if size==8 else bytes(size)
        with self.assertRaises(ValueError): policy_ids(b'',read)
