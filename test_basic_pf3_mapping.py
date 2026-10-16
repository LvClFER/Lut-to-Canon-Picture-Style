import struct
import unittest
from canon_engine import modify_basic_0115, parse_basic_0115


class BasicPf3MappingTests(unittest.TestCase):
    def test_native_layout_not_just_roundtrip(self):
        raw = struct.pack('<8i', -2, 5, 1, -1, 19, 23, 2, 3)
        values = parse_basic_0115(raw)
        self.assertEqual(values['contrast'], -2)
        self.assertEqual(values['sharp_strength'], 5)
        result = modify_basic_0115(raw, -4, 2, 3, True, 7, 4, 5)
        self.assertEqual(struct.unpack('<8i', result), (-4, 7, 2, 3, 19, 23, 4, 5))

    def test_no_sharpness_override_preserves_actual_strength(self):
        raw = struct.pack('<8i', 0, 5, 0, 0, 0, 0, 2, 3)
        result = modify_basic_0115(raw, -2, 1, -1)
        self.assertEqual(struct.unpack('<8i', result), (-2, 5, 1, -1, 0, 0, 2, 3))

    def test_contrast_range_cannot_change_strength(self):
        for contrast in range(-4, 5):
            result = modify_basic_0115(struct.pack('<8i',0,3,0,0,0,0,2,3),contrast,0,0)
            self.assertEqual(struct.unpack_from('<2i', result), (contrast,3))

    def test_invalid_aggregate_size_rejected(self):
        with self.assertRaises(ValueError):
            parse_basic_0115(bytes(31))
        with self.assertRaises(ValueError):
            modify_basic_0115(bytes(31),0,0,0)


if __name__ == '__main__':
    unittest.main()
