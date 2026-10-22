import struct
import unittest
from camera_install.descriptor_capability_reference import capability_word


class DescriptorCapabilityTests(unittest.TestCase):
    def test_compact_and_modern_strides(self):
        for modern,size,offset in [(False,0x1d44,4984),(True,0x39cc,7888)]:
            data=bytearray(size);struct.pack_into('<H',data,offset,1)
            self.assertEqual(capability_word(data,modern,3,1),dict(offset=offset,word=1,enabled=True))
            struct.pack_into('<H',data,offset,2)
            self.assertFalse(capability_word(data,modern,3,1)['enabled'])

    def test_raw_sizes_and_unknown_selectors_refused(self):
        with self.assertRaises(ValueError):capability_word(bytes(15076),True,3,1)
        with self.assertRaises(ValueError):capability_word(bytes(0x39cc),True,6,1)
        with self.assertRaises(ValueError):capability_word(bytes(0x39cc),True,3,3)
