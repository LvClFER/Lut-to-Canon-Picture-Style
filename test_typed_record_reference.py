import unittest
from camera_install.typed_record_reference import copy_record, output_record


class TypedRecordReferenceTests(unittest.TestCase):
    def test_output_preserves_incomplete_tail(self):
        self.assertEqual(output_record(b'abcde', 3, b'12345', 0x4d4d), b'badc5')
        self.assertEqual(output_record(b'abcde', 4, b'12345', 0x4d4d), b'dcba5')
        self.assertEqual(output_record(b'a', 4, b'z'), b'z')

    def test_output_span_rules(self):
        self.assertEqual(output_record(b'ab', 2, b'1234'), b'ab34')
        self.assertIsNone(output_record(b'ab', 1, b'1234'))
        self.assertEqual(output_record(b'abcd', 4, b'123'), b'123')
        self.assertEqual(output_record(b'abcd', 3, b'123'), b'ab3')

    def test_element_order_and_incomplete_tail(self):
        self.assertEqual(copy_record(b'abcde', 3, 0x4d4d), b'badc\0')
        self.assertEqual(copy_record(b'abcde', 4, 0x4d4d), b'dcba\0')
        self.assertEqual(copy_record(b'abcde', 4, 0x4949), b'abcd\0')

    def test_expected_size_rules(self):
        for kind in (1, 3, 4, 65535):
            self.assertIsNone(copy_record(b'ab', kind, expected_size=4))
        self.assertEqual(copy_record(b'ab', 2, expected_size=4), b'ab\0\0')
        self.assertIsNone(copy_record(b'abcdef', 2, expected_size=4))

    def test_raw_types_ignore_order(self):
        for kind in (1, 2, 65535):
            self.assertEqual(copy_record(b'abcde', kind, 0x4d4d), b'abcde')

    def test_reject_unmapped_inputs(self):
        for args in ((b'a', 5), (b'', 1)):
            with self.assertRaises(ValueError):
                copy_record(*args)

    def test_complete_element_swap_is_involution(self):
        for kind, width in ((3, 2), (4, 4)):
            for count in (1, 3, 17):
                data = bytes((i * 37 + 11) % 256 for i in range(width * count))
                with self.subTest(kind=kind, count=count):
                    changed = copy_record(data, kind, 0x4d4d)
                    self.assertEqual(copy_record(changed, kind, 0x4d4d), data)

    def test_legacy_fixed_sizes(self):
        for kind, size in ((3, 1460), (4, 300), (4, 240)):
            data = bytes((i * 37 + 11) % 256 for i in range(size))
            with self.subTest(kind=kind, size=size):
                self.assertEqual(copy_record(data, kind, expected_size=size), data)
                self.assertIsNone(copy_record(data[:-2], kind, expected_size=size))
                self.assertIsNone(copy_record(data + b'xx', kind, expected_size=size))


if __name__ == '__main__':
    unittest.main()
