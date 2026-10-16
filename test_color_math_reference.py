import math
import unittest
from camera_install.color_math_reference import decode_channel, forward_color, inverse_color
from camera_install.color_trace_validation import validate


class ColorTests(unittest.TestCase):
    def test_mode_ten_native_neutral_axis_addition_order(self):
        rgb=[0.17176470588235293]*3
        expected=['0x1.8a9ace9366befp-6','0x1.99418e9ccdc0fp-6','0x1.5198685acb360p-6']
        self.assertEqual([v.hex() for v in forward_color(rgb,10)],expected)

    def test_signed_transfer(self):
        for value in (.02, .1, .5, 1.2):
            self.assertAlmostEqual(decode_channel(-value), -decode_channel(value))
        self.assertEqual(decode_channel(0), 0)

    def test_mode_one_primary(self):
        self.assertEqual(forward_color([1, 0, 0], 1), [.4124, .2126, .0193])
        self.assertEqual(forward_color([0, 1, 0], 1), [.3576, .7152, .1192])

    def test_mode_twelve_forward_alias_only(self):
        self.assertEqual(forward_color([.2, .4, .8], 12), forward_color([.2, .4, .8], 1))

    def test_nonfinite_refused(self):
        with self.assertRaises(ValueError):
            decode_channel(math.nan)

    def test_negative_inverse_reports_clipping(self):
        output, rc = inverse_color([-1, -1, -1], 1)
        self.assertEqual(output, [0, 0, 0])
        self.assertEqual(rc, 0xffffffff)

    def test_empty_coverage_does_not_claim_validation(self):
        result = validate({"files": [{"model": "old", "payloadSize": 8528,
            "mlibCalls": {"counts": {}, "captures": []}}]})
        self.assertEqual(result["passed"], 0)
        self.assertFalse(result["cameraAcceptanceEstablished"])
