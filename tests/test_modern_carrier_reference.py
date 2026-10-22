import unittest
from camera_install.modern_carrier_reference import build_observed_modern17


class ModernCarrierReferenceTests(unittest.TestCase):
    def test_unknown_descriptor_or_extension_flag_rejected_before_build(self):
        for descriptor, extended in ((b'', False), (bytes(14796), 1), (bytes(14795), True)):
            with self.assertRaises(ValueError):
                build_observed_modern17({}, descriptor, (bytes(512), bytes(513)), extended=extended)
