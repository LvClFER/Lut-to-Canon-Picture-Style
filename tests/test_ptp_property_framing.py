import struct
import unittest
from camera_install.ptp_capture import build_canon_property_packet, parse_canon_property_packet


class PropertyFramingTests(unittest.TestCase):
    def test_synthetic_roundtrip_without_camera(self):
        for code in (0, 0xD163, 0xD170, 0xffffffff):
            for value in (b"x", bytes(range(256))):
                self.assertEqual(parse_canon_property_packet(build_canon_property_packet(code, value)), (code, value))

    def test_each_length_is_checked(self):
        packet = build_canon_property_packet(0xD170, b"synthetic")
        for offset in (0, 8):
            bad = bytearray(packet)
            struct.pack_into("<I", bad, offset, 999)
            with self.assertRaises(ValueError):
                parse_canon_property_packet(bad)

    def test_truncated_and_extra_data_rejected(self):
        packet = build_canon_property_packet(0xD163, b"synthetic")
        for bad in (b"", packet[:12], packet[:-1], packet+b"x"):
            with self.assertRaises(ValueError):
                parse_canon_property_packet(bad)
