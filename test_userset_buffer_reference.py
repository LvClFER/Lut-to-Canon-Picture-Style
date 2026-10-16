import unittest
import struct

from camera_install.userset_buffer_reference import copy_userset_buffer, split_userset_buffer


class UsersetBufferReferenceTests(unittest.TestCase):
    def test_split_roundtrip(self):
        for size in (0, 1, 8488, 16712, 83036, 431576):
            header = struct.pack('<II', 1, size) + bytes(range(32))
            data = bytes(size)
            buffer = header + data
            actual_header, actual_data = split_userset_buffer(buffer)
            self.assertEqual((actual_header, actual_data), (header, data))
            self.assertEqual(copy_userset_buffer(actual_header, actual_data, size), buffer)

    def test_split_rejects_truncation_and_trailing_data(self):
        for buffer in (bytes(39), struct.pack('<II', 1, 2) + bytes(32),
                       struct.pack('<II', 1, 0) + bytes(33)):
            with self.assertRaises(ValueError):
                split_userset_buffer(buffer)

    def test_exact_copy_and_length(self):
        header = bytes(range(40))
        data = bytes(range(256)) * 65
        for size in (0, 1, 4, 8192, len(data)):
            output = copy_userset_buffer(header, data, size)
            self.assertEqual(output[:40], header)
            self.assertEqual(output[40:], data[:size])
            self.assertEqual(len(output), 40 + size)

    def test_invalid_evidence(self):
        for header, data, size in ((b'', b'', 0), (bytes(40), b'', -1),
                                   (bytes(40), b'a', 2), (bytes(40), b'a', True)):
            with self.assertRaises(ValueError):
                copy_userset_buffer(header, data, size)
        with self.assertRaises(TypeError):
            copy_userset_buffer(bytearray(40), b'', 0)


if __name__ == '__main__':
    unittest.main()
