import struct
import unittest
from camera_install.control_section_reference import build_control_plain
from camera_install.modern_header_reference import build_modern17_prefix, build_full33_prefix


class ModernHeaderTests(unittest.TestCase):
    def test_full33_envelope_and_strict_controls(self):
        control = build_control_plain({})
        expected = bytearray(build_modern17_prefix(self.fields(), control, 78980))
        for offset in (4, 40): struct.pack_into('<I', expected, offset, 431576)
        self.assertEqual(build_full33_prefix(self.fields(), control), bytes(expected))
        fields = self.fields()
        del fields[0x1034]
        with self.assertRaises(ValueError): build_full33_prefix(fields, control)

    def fields(self):
        result = {i: (4, struct.pack('<I', 3)) for i in range(0x1030, 0x1036)}
        result.update({0x1002: (2, b'test\0'), 0x1009: (3, b'\x81\0'),
                       0x100c: (3, b'\x12\0')})
        return result

    def test_sizes_names_and_markers(self):
        for size in (78980, 83076):
            value = build_modern17_prefix(self.fields(), build_control_plain({}), size)
            self.assertEqual(len(value), 372)
            self.assertEqual(struct.unpack_from('<II', value), (1, size - 40))
            self.assertEqual(struct.unpack_from('<I', value, 40)[0], size - 40)
            self.assertEqual(value[8:40], value[46:78])
            self.assertEqual(struct.unpack_from('<IIHH', value, 96), (0xdeadbeef, 0xdeadbeef, 3, 0))
            self.assertEqual(value[368:], b'\x12\0\0\0')

    def test_clamps(self):
        fields = self.fields()
        for identifier, numeric in ((0x1030, 100), (0x1034, 0), (0x1035, 99)):
            fields[identifier] = (4, struct.pack('<I', numeric))
        value = build_modern17_prefix(fields, build_control_plain({}), 78980)
        self.assertEqual([struct.unpack_from('<I', value, i)[0] for i in (84, 104, 108)], [7, 1, 5])

    def test_missing_and_bad_layout(self):
        fields = self.fields()
        del fields[0x1031]
        with self.assertRaises(ValueError):
            build_modern17_prefix(fields, build_control_plain({}), 78980)
        for size in (True, 16752, 83076.0):
            with self.assertRaises(ValueError):
                build_modern17_prefix(self.fields(), build_control_plain({}), size)

    def test_opt_in_group_defaults(self):
        for style in (0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0xffff):
            for missing in range(0x1030, 0x1034):
                fields = self.fields()
                fields[0x1009] = (3, struct.pack('<H', style))
                del fields[missing]
                value = build_modern17_prefix(fields, build_control_plain({}), 83076,
                                              allow_missing_controls=True)
                self.assertEqual(struct.unpack_from('<IIII', value, 80),
                                 (0, 0 if style == 0x84 else 3, 0, 0))
                self.assertEqual(struct.unpack_from('<II', value, 104), (3, 3))

    def test_opt_in_detail_defaults(self):
        for style, expected in ((0x81, (2, 3)), (0x82, (2, 4)), (0x83, (2, 3)),
                                (0x84, (2, 2)), (0x85, (2, 2)), (0x86, (2, 3)),
                                (0x87, (2, 3)), (0x88, (1, 1)), (0xffff, (2, 3))):
            for missing in (0x1034, 0x1035):
                fields = self.fields()
                fields[0x1009] = (3, struct.pack('<H', style))
                del fields[missing]
                value = build_modern17_prefix(fields, build_control_plain({}), 78980,
                                              allow_missing_controls=True)
                self.assertEqual(struct.unpack_from('<II', value, 104), expected)

    def test_missing_required_still_rejected(self):
        fields = self.fields()
        del fields[0x1009]
        with self.assertRaises(ValueError):
            build_modern17_prefix(fields, build_control_plain({}), 78980,
                                  allow_missing_controls=True)
        with self.assertRaises(ValueError):
            build_modern17_prefix(self.fields(), build_control_plain({}), 78980,
                                  allow_missing_controls=1)
