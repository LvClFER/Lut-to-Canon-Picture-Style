import unittest
from camera_install.legacy_resource_reference import legacy_1007_resource_id


class LegacyResourceTests(unittest.TestCase):
    def test_four_groups_of_six(self):
        ids = []
        for selector, base in ((0x80000213, 102), (0x80000232, 108),
                               (0x80000234, 114), (0x80000236, 120)):
            for style in range(0x81, 0x87):
                actual = legacy_1007_resource_id(selector, style)
                self.assertEqual(actual, base + style - 0x81)
                ids.append(actual)
        self.assertEqual(ids, list(range(102, 126)))

    def test_no_unknown_camera_or_fine_detail_fallback(self):
        for selector, style in ((0x80000212, 0x81), (0x80000214, 0x81),
                                (0x80000487, 0x81), (0x80000213, 0x80),
                                (0x80000213, 0x87), (0x80000213, -1)):
            with self.assertRaises(ValueError):
                legacy_1007_resource_id(selector, style)
        for selector, style in ((True, 0x81), (0x80000213, True), ('5D', 0x81)):
            with self.assertRaises(TypeError):
                legacy_1007_resource_id(selector, style)
