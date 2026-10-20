import struct
import unittest
from nikon_np3 import decode


def record(tag,payload):return struct.pack('>II',tag,len(payload))+payload
def document(extra=b''):
    return b'NCP\0'+record(0x100,b'0310')+record(0x200,b'Synthetic'+bytes(11))+record(0x300,b'\0 ')+extra+bytes(4)


class Np3Tests(unittest.TestCase):
    def test_tone_curve_keeps_all_257_native_samples_and_rejects_overflow(self):
        values=tuple(round(index*32767/256) for index in range(257))
        style=decode(document(record(2,bytes(64)+struct.pack('>257H',*values))))
        self.assertEqual(style.tone_curve_samples,values)
        self.assertIsNone(decode(document()).tone_curve_samples)
        invalid=values[:-1]+(32768,)
        with self.assertRaisesRegex(ValueError,'15-bit'):
            decode(document(record(2,bytes(64)+struct.pack('>257H',*invalid)))).tone_curve_samples

    def test_color_values_handle_neutral_sentinels_and_fractional_rounding(self):
        blender=bytearray([128]*24+[1,1,1,0]);blender[:2]=bytes((125,131));blender[24:26]=bytes((2,2))
        grading=bytes.fromhex('80008080800080808000808001010100b2018001')
        style=decode(document(record(0x1900,b'\xff\x00')+record(0x1f00,bytes(blender))+record(0x2000,grading)))
        values=style.color_values
        self.assertEqual(len(values),41)
        self.assertEqual(values[:6],(0,)*6)
        self.assertEqual(values[6:9],(-1,1,0))
        self.assertEqual(values[30:39],(0,)*9)
        self.assertEqual(values[-2:],(50,0))
        invalid=bytearray(blender);invalid[24]=0
        with self.assertRaisesRegex(ValueError,'zero divisor'):
            decode(document(record(0x1f00,bytes(invalid))+record(0x2000,grading))).color_values
        with self.assertRaisesRegex(ValueError,'extension blocks'):decode(document()).color_values

    def test_reader_preserves_encoded_controls_and_color_blocks(self):
        raw=document(record(0x600,b'\x88\x04')+record(0x1f00,bytes(range(28))))
        style=decode(raw)
        self.assertEqual(style.name,'Synthetic')
        self.assertEqual(style.encoded_controls,{'sharpness':b'\x88\x04'})
        self.assertEqual(style.block(0x1f00),bytes(range(28)))
        self.assertNotIn('8888',repr(style))

    def test_every_truncation_and_invalid_record_are_rejected(self):
        raw=document(record(0x600,b'\x88\x04'))
        for length in range(len(raw)):
            with self.subTest(length=length),self.assertRaises(ValueError):decode(raw[:length])
        for extra in (record(0x100,b'0310'),record(0x600,b'x'),record(0x7777,b''),struct.pack('>II',0x600,0xffffffff)):
            with self.subTest(extra=extra),self.assertRaises(ValueError):decode(document(extra))
        with self.assertRaises(ValueError):decode(raw.replace(b'0310',b'0300',1))


if __name__=='__main__':unittest.main()
