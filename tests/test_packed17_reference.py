import struct
import unittest
from camera_install.packed17_reference import pack17, pack17_for_style


class Packed17Tests(unittest.TestCase):
    def test_black(self):
        self.assertEqual(pack17([0.]*(17**3*3)),bytes(17**3*4))

    def test_white_and_reserved_bits(self):
        result=struct.unpack('<4913I',pack17([255.75]*(17**3*3)))
        self.assertTrue(all(v>>30==0 for v in result))
        self.assertTrue(all((v>>20)==1023 for v in result))

    def test_reject_bad_grid(self):
        with self.assertRaises(ValueError): pack17([0.])
        with self.assertRaises(ValueError): pack17([float('nan')]*(17**3*3))

    def test_axis_order(self):
        n=17**3; values=[0.]*(n*3)
        values[(2*17+3)*17+4]=100
        words=struct.unpack('<4913I',pack17(values))
        self.assertEqual([i for i,v in enumerate(words) if v],[(4*17+3)*17+2])

    def test_internal_style_and_table_jointly_select_matrix(self):
        n = 17**3
        values = [25.]*n+[150.]*n+[220.]*n
        standard, alternate = pack17(values), pack17(values, True)
        self.assertNotEqual(standard, alternate)
        for style in (0, 0x80, 0x81, 0x82, 0x84, 0xffff):
            for selector in (0, 1, 2, 0xffffffff):
                with self.subTest(style=style, selector=selector):
                    expected = alternate if style in (0x81, 0x84) and selector == 1 else standard
                    self.assertEqual(pack17_for_style(values, style, selector), expected)

    def test_matrix_selector_rejects_ambiguous_types(self):
        values = [0.]*(17**3*3)
        for style in (True, '129', 129., -1, 65536):
            with self.assertRaises(ValueError):
                pack17_for_style(values, style, 1)
        for selector in (True, '1', 1., -1, 2**32):
            with self.assertRaises(ValueError):
                pack17_for_style(values, 0x81, selector)
        with self.assertRaises(ValueError):
            pack17(values, 1)
