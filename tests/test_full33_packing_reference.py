import unittest
from camera_install.full33_packing_reference import pack_full33, source_full33_table, encode_app_dense_full33
import struct


class Full33PackingTests(unittest.TestCase):
    def test_app_dense_policy_all_12bit_values_and_channel_order(self):
        values = [component for node in range(35937)
                  for component in (node % 4096, 4095-node % 4096, 0)]
        raw = struct.pack('<3H',12,3,33)+struct.pack('<107811H',*values)
        actual = struct.unpack('<107811H',encode_app_dense_full33(raw))
        for node in range(35937):
            for channel in range(3):
                self.assertEqual(actual[channel*35937+node],
                                 (values[node*3+channel]*32768+2047)//4095)
        self.assertEqual((actual[0],actual[4095]),(0,32768))

    def test_app_dense_policy_rejects_invalid_sources(self):
        raw = struct.pack('<3H',12,3,33)+bytes(215622)
        for changed in (bytearray(raw),raw[:-2],b'\0\0'+raw[2:],raw[:6]+b'\0\x10'+raw[8:]):
            with self.assertRaises(ValueError): encode_app_dense_full33(changed)

    def test_source_mode_guard(self):
        for mode in (0, 3, True, 1.0, '1'):
            with self.assertRaises(ValueError): source_full33_table({}, mode)

    def test_exact_word_storage(self):
        values=[32768.]*(33**3*3)
        self.assertEqual(pack_full33(values),b'\x00\x80'*(33**3*3))

    def test_reject_nonintegral_unbounded_or_short(self):
        for v in (.5,-1,32769,float('nan')):
            with self.assertRaises(ValueError): pack_full33([v]*(33**3*3))
        with self.assertRaises(ValueError): pack_full33([0.])
