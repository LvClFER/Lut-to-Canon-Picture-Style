import math
import struct
import unittest
from camera_install.packed9_reference import pack9, pack9_observed_overshoot, pack9_dense9, quantize


class PackedNineTests(unittest.TestCase):
    def test_dense9_explicit_domain(self):
        for value in (0, 286, 300, 311, 320):
            result = pack9_dense9([value] * 2187)
            self.assertEqual(set(struct.unpack('<729I', result)), {quantize(value,value,value)})
        for value in (-1, 320.01, math.inf, math.nan):
            with self.assertRaises(ValueError):
                pack9_dense9([value] * 2187)

    def test_black_white_and_integer_rounding(self):
        self.assertEqual(pack9([0.] * 2187), bytes(2916))
        self.assertEqual(set(struct.unpack('<729I', pack9([255.] * 2187))), {510 << 20})
        self.assertEqual(quantize(100, 0, 0), (58 << 20) | (988 << 10) | 100)
        self.assertEqual(quantize(100.75, 0, 0), quantize(100, 0, 0))

    def test_bgr_traversal(self):
        values = [0.] * 2187
        r, g, b = 3, 2, 1
        values[(r * 9 + g) * 9 + b] = 100
        packed = struct.unpack('<729I', pack9(values))
        self.assertEqual(packed[(b * 9 + g) * 9 + r], quantize(100, 0, 0))
        self.assertEqual(sum(value != 0 for value in packed), 1)

    def test_reject_unverified_values(self):
        for value in (-1, 256, math.inf, math.nan):
            values = [0.] * 2187
            values[0] = value
            with self.assertRaises(ValueError):
                pack9(values)
        with self.assertRaises(ValueError):
            pack9([0.] * 2186)

    def test_explicit_observed_overshoot_is_not_clipped(self):
        for value in (256, 267, 282, 286):
            result = pack9_observed_overshoot([value] * 2187)
            self.assertEqual(set(struct.unpack('<729I', result)), {quantize(value,value,value)})
            self.assertNotEqual(result, pack9([255.] * 2187))
        for value in (-1, 286.01, math.inf, math.nan):
            with self.assertRaises(ValueError):
                pack9_observed_overshoot([value] * 2187)


if __name__ == '__main__':
    unittest.main()
