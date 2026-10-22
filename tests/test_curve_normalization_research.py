import struct
import unittest
from camera_install.curve_normalization_research import normalize_curve, verify_trace


class NormalizationTests(unittest.TestCase):
    def test_identity_and_controlled_change(self):
        for endpoint in (255, 230):
            data, domain = normalize_curve(struct.pack("<5I", 2, 0, 0, 255, endpoint))
            self.assertEqual(struct.unpack("<4d", data), (0., 0., 1., endpoint / 255))
            self.assertEqual(domain, 256)

    def test_default_domain(self):
        data, domain = normalize_curve(struct.pack("<5I", 2, 0, 0, 300, 300))
        self.assertEqual(domain, 301)
        self.assertEqual(struct.unpack("<4d", data), (0., 0., 1., 1.))

    def test_invalid_inputs_refused(self):
        for data in (b"", struct.pack("<I", 13), struct.pack("<3I", 1, 0, 10)):
            with self.assertRaises(ValueError):
                normalize_curve(data)

    def test_mismatch_is_not_validated(self):
        row = {"model": "test", "source": "test", "cameraId": 1, "mlibCalls": {"captures": [
            {"functionRva": "0xf490", "inputPairsHex": struct.pack("<5I", 2, 0, 0, 255, 230).hex()},
            {"functionRva": "0x1dc90", "normalizedPairsFloat64Hex": bytes(32).hex(), "domainSize": 256}]}}
        self.assertFalse(verify_trace(row)["exactForAllCapturedInputs"])
