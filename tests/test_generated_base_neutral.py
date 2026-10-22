import struct
import unittest
from canon_engine import generated_pf3_properties, PICTURE_STYLE_IDS


class GeneratedNeutralBaseTests(unittest.TestCase):
    def test_all_styles_have_identity_post_lut_processing(self):
        for style, identifier in PICTURE_STYLE_IDS.items():
            props=generated_pf3_properties(style)
            self.assertEqual(int.from_bytes(props[0x114],'little'),identifier)
            for prop in (0x40001021,0x40001029):
                words=struct.unpack('<60i',props[prop])
                self.assertEqual([i for i,w in enumerate(words) if w], [0,21,42])
                self.assertEqual([words[i] for i in (0,21,42)],[65536]*3)
            for prop in (0x40001018,0x40001019,0x40001065):
                for channel in range(3):
                    curve=struct.unpack('<25I',props[prop][channel*100:(channel+1)*100])
                    self.assertEqual(curve[:5],(2,0,0,255,255))
                    self.assertEqual(curve[5:],(0,)*20)
            for prop in (0x40001061,0x40001062):
                self.assertEqual(struct.unpack_from('<2I',props[prop]),(2,0))
