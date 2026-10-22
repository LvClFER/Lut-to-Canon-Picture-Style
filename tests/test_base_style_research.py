import unittest
from camera_install.base_style_research import compare_records,native_blocks


class BaseStyleResearchTests(unittest.TestCase):
    def test_record_comparison_requires_matching_property_sets(self):
        self.assertEqual(compare_records({'a':b'x'},{'a':b'x'}),[])
        self.assertEqual(compare_records({'a':b'y'},{'a':b'x'})[0]['id'],'a')
        with self.assertRaises(ValueError):compare_records({'a':b'x'},{'b':b'x'})

    def test_only_observed_native_layouts_are_accepted(self):
        self.assertEqual(list(map(len,native_blocks(bytes(16752)))),[4096]*4)
        self.assertEqual(list(map(len,native_blocks(bytes(83076)))),[19652]*4+[4096])
        self.assertEqual(list(map(len,native_blocks(bytes(431616)))),[215622]*2)
        with self.assertRaises(ValueError):native_blocks(bytes(16751))


if __name__=='__main__':unittest.main()
