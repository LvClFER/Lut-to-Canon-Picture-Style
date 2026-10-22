import unittest
from camera_install.envelope_version_research import header_variant


class EnvelopeVersionTests(unittest.TestCase):
    def test_changes_only_four_version_bytes(self):
        raw = bytes.fromhex('00004000') + b'PSP\0' + bytes(4) + b'opaque'
        for version in (0x2000, 0x2001, 0x3000, 0x4000):
            variant = header_variant(raw, version)
            self.assertEqual(variant[4:], raw[4:])
            self.assertEqual(int.from_bytes(variant[:4], 'big'), version)
            self.assertEqual(len(variant), len(raw))

    def test_unknown_version_or_envelope_rejected(self):
        with self.assertRaises(ValueError):
            header_variant(bytes(12), 0x3000)
        with self.assertRaises(ValueError):
            header_variant(bytes(4) + b'PSP\0' + bytes(4), 0xffff)
