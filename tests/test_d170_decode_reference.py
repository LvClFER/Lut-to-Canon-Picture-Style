import struct
import unittest
from camera_install.d170_decode_reference import decode_701d0


class D170ReferenceTests(unittest.TestCase):
    def test_size_includes_prefix_branch(self):
        self.assertEqual(decode_701d0(struct.pack("<II", 12, 1)+b"abcd"), struct.pack("<II", 1, 4)+b"abcd")

    def test_size_is_payload_branch(self):
        payload = struct.pack("<H", 10)+bytes(8)
        self.assertEqual(decode_701d0(struct.pack("<II", 10, 1)+payload), struct.pack("<II", 1, 10)+payload)

    def test_invalid_state_zeroes_tail(self):
        self.assertEqual(decode_701d0(struct.pack("<II", 12, 0)+b"abcd"), bytes(12))

    def test_inconsistent_lengths_rejected(self):
        for data in (b"", struct.pack("<II", 12, 1)+b"abc", struct.pack("<II", 12, 1)+b"abcde"):
            with self.assertRaises(ValueError):
                decode_701d0(data)

    def test_types_and_preallocation_bounds(self):
        for value in (12,True,None,'data',[0]*12,memoryview(bytes(1024*1024+9))):
            with self.assertRaises(ValueError):decode_701d0(value)

    def test_all_truncations_and_snapshot(self):
        original=struct.pack('<II',12,1)+b'abcd'
        for length in range(len(original)):
            with self.assertRaises(ValueError):decode_701d0(original[:length])
        source=bytearray(original)
        decoded=decode_701d0(memoryview(source))
        source[-1]=0
        self.assertEqual(decoded,struct.pack('<II',1,4)+b'abcd')
