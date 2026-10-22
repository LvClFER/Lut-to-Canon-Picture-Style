import unittest
from camera_install.format_context_reference import constructor_selection, file_constructor_selection


class FormatContextReferenceTests(unittest.TestCase):
    def test_file_open_preserves_version_and_maps_extra_family(self):
        self.assertEqual(file_constructor_selection(0x2000), ('baseFormatContext', 0x2000))
        self.assertEqual(file_constructor_selection(0x3000), ('pf3FormatContext', 0x3000))
        self.assertEqual(file_constructor_selection(0x4001), ('pf3FormatContext', 0x4001))
        self.assertIsNone(file_constructor_selection(0xffff))

    def test_observed_versions_and_mask(self):
        self.assertEqual(constructor_selection(0x2000), ('baseFormatContext', 0x2001))
        self.assertEqual(constructor_selection(0x3000), ('pf3FormatContext', 0x3000))
        self.assertEqual(constructor_selection(0x30ff), ('pf3FormatContext', 0x30ff))

    def test_branch_does_not_assert_file_validity(self):
        self.assertEqual(constructor_selection(0xffff), ('baseFormatContext', 0x2001))
        for value in (-1, 0x10000, True, '0x3000'):
            with self.assertRaises(ValueError):
                constructor_selection(value)
