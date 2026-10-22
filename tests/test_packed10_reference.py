import unittest
from camera_install.packed10_reference import pack10,packed_index,pack10_integer,decoded_payload_blocks,pack10_for_style
from unittest.mock import patch


class Packed10Tests(unittest.TestCase):
    def test_style_coefficient_branch(self):
        values = [220.] * 1000 + [85.] * 1000 + [16.] * 1000
        self.assertNotEqual(pack10(values, False), pack10(values, True))
        for style in (0x81, 0x82, 0x83, 0x84, 0x85, 0x88):
            for mode in (1, 2):
                self.assertEqual(pack10_for_style(values, style, mode),
                                 pack10(values, not (style in (0x81, 0x84) and mode == 1)))
        with self.assertRaises(ValueError): pack10_for_style(values, 0x86, 1)
        with self.assertRaises(ValueError): pack10_for_style(values, 0x84, 3)

    def test_black_and_padding(self):
        self.assertEqual(pack10([0.]*3000,True),bytes(4096))

    def test_index_bijection(self):
        used={packed_index(r,g,b) for r in range(10) for g in range(10) for b in range(10)}
        self.assertEqual(len(used),1000)
        self.assertTrue(min(used)>=0 and max(used)<1024)

    def test_invalid_input(self):
        with self.assertRaises(ValueError): packed_index(10,0,0)
        with self.assertRaises(ValueError): pack10([0.],True)

    def test_integer_field_order_and_mask(self):
        values=[-1]*1000+[1023]*1000+[0]*1000
        words=__import__('struct').unpack('<1024I',pack10_integer(values))
        self.assertEqual(words[packed_index(0,0,0)],(1023<<20)|1023)
        with self.assertRaises(ValueError): pack10_integer([0.]*3000)

    def test_modern_appended_compact_representation(self):
        payload=bytes(78980)+b'x'*4096
        with patch('camera_install.packed10_reference.decode',return_value=b'plain') as decoder:
            self.assertEqual(decoded_payload_blocks(payload,'keys'),[(78980,0xb8ed,b'plain')])
            decoder.assert_called_once_with(b'x'*4096,'keys',0xb8ed)
        self.assertEqual(decoded_payload_blocks(bytes(78980),'keys'),[])
