import struct
import unittest

from camera_install.control_section_reference import build_control_plain


class ControlSectionReferenceTests(unittest.TestCase):
    def test_empty(self):
        value = build_control_plain({})
        self.assertEqual(len(value), 252)
        self.assertEqual(value[:16], struct.pack('<HHIHHI', 0x2fff, 65535, 0, 65535, 65535, 0))
        self.assertEqual(value[16:], bytes(236))

    def test_order_and_typed_suffix(self):
        records = {0x100d: (3, b'\x12\x34\xff'), 0x100a: (1, b'ab')}
        value = build_control_plain(records)
        self.assertEqual(value[8:18], struct.pack('<HHI', 0x100a, 1, 2) + b'ab')
        self.assertEqual(value[18:29], struct.pack('<HHI', 0x100d, 3, 3) + b'\x12\x34\0')
        self.assertEqual(value[29:37], struct.pack('<HHI', 65535, 65535, 0))
        self.assertEqual(records[0x100d][1], b'\x12\x34\xff')

    def test_capacity(self):
        self.assertEqual(len(build_control_plain({0x100a: (2, b'x' * 228)})), 252)
        with self.assertRaises(ValueError):
            build_control_plain({0x100a: (2, b'x' * 229)})

    def test_rejections(self):
        for records in ({0x115: (1, b'x')}, {0x100a: (True, b'x')},
                        {0x100a: (1, bytearray(b'x'))}, {0x100a: (1, b'')}):
            with self.assertRaises(ValueError):
                build_control_plain(records)
        for size in (True, 15, 4097, 252.0):
            with self.assertRaises(ValueError):
                build_control_plain({}, size)


if __name__ == '__main__':
    unittest.main()
