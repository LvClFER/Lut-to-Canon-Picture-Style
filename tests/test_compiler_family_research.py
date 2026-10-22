import unittest
from camera_install.compiler_family_research import classify, EXPLICIT


class CompilerFamilyTests(unittest.TestCase):
    def test_explicit_and_default(self):
        rules = {'tables': []}
        for identifier, expected in EXPLICIT.items():
            self.assertEqual(classify(identifier, rules), expected)
        for identifier in (0, 1042, 0xffffffff):
            self.assertEqual(classify(identifier, rules), 7)

    def test_table_boundaries(self):
        rules = {'tables': [{'base': 100, 'classes': [8, 9, 10]}]}
        self.assertEqual([classify(i, rules) for i in range(99, 104)], [7, 8, 9, 10, 7])

    def test_invalid_ids(self):
        for identifier in (-1, 0x100000000, True, '1042', 1.0):
            with self.assertRaises(ValueError):
                classify(identifier, {'tables': []})


if __name__ == '__main__':
    unittest.main()
