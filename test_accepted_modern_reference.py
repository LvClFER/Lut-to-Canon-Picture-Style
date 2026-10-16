import struct
import unittest
from camera_install.accepted_modern_reference import dense_source, build_accepted_modern17


class AcceptedModernReferenceTests(unittest.TestCase):
    def test_dense_source_geometry_range_and_order(self):
        raw = struct.pack('<3H', 12,3,33) + struct.pack('<3H', 0,2048,4095) * 35937
        result = dense_source(raw)
        self.assertEqual(result.shape, (33,33,33,3))
        self.assertEqual(result[12,7,3].tolist(), [0,2048/4095,1])
        for changed in (raw[:-2], b'\0\0' + raw[2:], raw[:6] + b'\0\x10' + raw[8:]):
            with self.assertRaises(ValueError):
                dense_source(changed)

    def test_missing_inputs_or_unknown_descriptor_fail_before_compilation(self):
        for descriptor, extended in ((bytes(14796),True), (b'',True), (bytes(14796),1)):
            with self.assertRaises(ValueError):
                build_accepted_modern17({}, descriptor, (bytes(512),bytes(513)), extended=extended)
